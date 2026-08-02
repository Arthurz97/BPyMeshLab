import bpy, os, tempfile, gc, math
import bmesh
import pymeshlab
import mathutils
import numpy as np
import time
from . import utils


class MeshLabFilterBase:
    pymeshlab_filter = ""
    requires_selection = False
    ignore_selection_count = False
    shade_flat = False
    remove_attributes = []

    @classmethod
    def apply_filter(cls, context, props):
        # SEGURANÇA DE MODO: Garante que o Blender esteja no modo Objeto.
        # Evita crashes caso o usuário tente rodar o filtro de dentro do Edit Mode.
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_obj = context.active_object
        has_mesh = original_obj and original_obj.type == "MESH"
        original_selected_objs = context.selected_objects[:]

        # TRAVA DE MULTI-SELEÇÃO: O PyMeshLab em scripts simples pode se perder com múltiplos inputs.
        # Esta trava garante que a lógica de nomeação e matriz funcione perfeitamente sobre 1 único alvo.
        if len(original_selected_objs) > 1 and not getattr(
            cls, "ignore_selection_count", False
        ):
            return (
                "CANCELLED",
                "Múltiplas seleções não são suportadas. Selecione apenas 1 objeto.",
            )

        if cls.requires_selection and (not original_selected_objs or not has_mesh):
            return (
                "CANCELLED",
                "This filter requires exactly one active mesh selection.",
            )

        # ---- TRAVA DE SEGURANÇA (ANTES DA EXPORTAÇÃO) ----
        # Bloqueia a execução imediatamente se a caixa estiver marcada mas a seleção estiver vazia.
        is_selected_only = getattr(props, "selectedonly", False)
        if is_selected_only and has_mesh:
            # Checa os polígonos. Como o Object Mode é forçado no início da função, p.select está sempre atualizado.
            has_selection = any(p.select for p in original_obj.data.polygons)
            if not has_selection:
                return (
                    "CANCELLED",
                    "Opção 'Remesh only selected faces' ativa, mas nenhuma face está selecionada no Edit Mode.",
                )

        prefs = context.scene.meshlab_prefs
        apply_prev_mesh_action = prefs.global_prev_mesh_action
        engine = prefs.processing_engine

        # Trava de Segurança: Força o uso de DISCO para filtros que exigem polígonos
        if getattr(cls, "requires_polygons_disk", False):
            engine = "DISK"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Checa a preferência do filtro para definir o formato de saída do motor C++
                use_ply = getattr(cls, "prefer_ply_disk", False)

                if use_ply:
                    output_path = os.path.join(tmpdir, "output.ply")
                else:
                    output_path = os.path.join(tmpdir, "output.obj")

                ms = pymeshlab.MeshSet()

                # ==========================================================
                # CAMINHO 1: PROCESSAMENTO EM MEMÓRIA (NumPy)
                # ==========================================================
                if engine == "MEMORY":
                    if has_mesh:
                        # Extrai vértices, faces e matriz de seleção/cores (se exigido)
                        vertices, faces, v_colors = utils.blender_to_numpy(
                            original_obj, extract_selection=is_selected_only
                        )

                        mesh_kwargs = {"vertex_matrix": vertices, "face_matrix": faces}

                        if is_selected_only and v_colors is not None:
                            mesh_kwargs["v_color_matrix"] = v_colors

                        # Injeção direta na memória C++ do PyMeshLab
                        m = pymeshlab.Mesh(**mesh_kwargs)
                        ms.add_mesh(m)

                        # Traduz a cor para seleção nativa no PyMeshLab
                        if is_selected_only and v_colors is not None:
                            # A cor branca na nossa matriz numpy significa selecionado
                            ms.compute_selection_by_condition_per_vertex(
                                condselect="(r > 127)"
                            )
                            ms.compute_selection_transfer_vertex_to_face()

                # ==========================================================
                # CAMINHO 2: PROCESSAMENTO EM DISCO (I/O)
                # ==========================================================
                elif engine == "DISK":
                    if cls.requires_selection and has_mesh:
                        ext = (
                            "obj"
                            if getattr(cls, "requires_polygons_disk", False)
                            else "ply"
                        )
                        input_path = os.path.join(tmpdir, f"input.{ext}")

                        # --- PREPARAÇÃO TOPOLÓGICA (BMESH) PARA DISCO ---
                        # Cria uma cópia temporária da malha para não destruir a geometria original do usuário na Viewport
                        temp_mesh = original_obj.data.copy()

                        bm = bmesh.new()
                        bm.from_mesh(temp_mesh)

                        # Se o filtro exigir polígonos (como o Catmull-Clark), ignoramos a triangulação destrutiva
                        if not getattr(cls, "requires_polygons_disk", False):
                            # Garante triangulação perfeita (Beauty) dos N-gons antes de enviar para o arquivo C++
                            bmesh.ops.triangulate(
                                bm,
                                faces=bm.faces[:],
                                quad_method="FIXED",
                                ngon_method="BEAUTY",
                            )
                        bm.to_mesh(temp_mesh)
                        bm.free()

                        # Cria um objeto temporário descartável para hospedar a malha e exportar
                        temp_obj = bpy.data.objects.new("Temp_Export", temp_mesh)
                        context.collection.objects.link(temp_obj)
                        temp_obj.matrix_world = original_obj.matrix_world.copy()

                        bpy.ops.object.select_all(action="DESELECT")
                        temp_obj.select_set(True)
                        context.view_layer.objects.active = temp_obj

                        # Sincroniza a memória do Blender com a nova malha triangulada
                        context.view_layer.update()
                        temp_mesh.update()

                        # ---- 1. EXPORTAÇÃO DINÂMICA (OBJ vs PLY) E TRANSFERÊNCIA DE SELEÇÃO ----
                        temp_color = None
                        # Flags dinâmicas para evitar o rasgo de vértices (Vertex Splitting) no disco
                        req_normals = getattr(cls, "requires_normals_disk", False)
                        req_uv = getattr(cls, "requires_uv_disk", False)
                        requires_poly = getattr(cls, "requires_polygons_disk", False)

                        if requires_poly:
                            # ROTA OBJ: Preserva Quads, N-gons, UVs e Normais nativamente.
                            export_kwargs = {
                                "filepath": input_path,
                                "export_selected_objects": True,
                                "export_normals": req_normals,
                                "export_uv": req_uv,
                                "export_materials": False,  # Evita poluição de arquivos .mtl
                                "export_triangulated_mesh": False,  # A chave-mestra para manter os Quads
                                "forward_axis": "Y",
                                "up_axis": "Z",
                            }
                            bpy.ops.wm.obj_export(**export_kwargs)
                        else:
                            # ROTA PLY (Trilho Padrão): Triângulos e suporte a Vertex Colors (Seleção).
                            export_kwargs = {
                                "filepath": input_path,
                                "export_selected_objects": True,
                                "ascii_format": False,  # Força explicitamente o formato Binário
                                "export_normals": req_normals,
                                "export_uv": req_uv,
                                "forward_axis": "Y",
                                "up_axis": "Z",
                            }

                            if is_selected_only:
                                # USAMOS POINT (Vértices) porque o PLY C++ garante essa exportação
                                temp_color = temp_mesh.color_attributes.new(
                                    name="Col", type="BYTE_COLOR", domain="POINT"
                                )
                                temp_mesh.attributes.active_color = temp_color

                                # Extrai a seleção diretamente dos vértices da malha temporária
                                colors = [
                                    val
                                    for v in temp_mesh.vertices
                                    for val in (
                                        (1.0, 1.0, 1.0, 1.0)
                                        if v.select
                                        else (0.0, 0.0, 0.0, 1.0)
                                    )
                                ]
                                temp_color.data.foreach_set("color", colors)
                                export_kwargs["export_colors"] = "SRGB"
                            else:
                                # Evita que Vertex Colors residuais causem separação da malha
                                export_kwargs["export_colors"] = "NONE"

                            # Exporta dinamicamente a malha temporária passando os parâmetros seguros
                            bpy.ops.wm.ply_export(**export_kwargs)

                        # Limpeza imediata dos dados temporários após exportar
                        bpy.data.objects.remove(temp_obj, do_unlink=True)
                        bpy.data.meshes.remove(temp_mesh, do_unlink=True)

                        ms.load_new_mesh(input_path)

                        # ---- 2. TRADUÇÃO DA SELEÇÃO NO PYMESHLAB ----
                        if is_selected_only:
                            # Seleciona os vértices pintados de branco (r > 127)
                            ms.compute_selection_by_condition_per_vertex(
                                condselect="(r > 127)"
                            )
                            # Propaga a seleção dos vértices para as faces
                            ms.compute_selection_transfer_vertex_to_face()

                # --- LEITURA DE PARÂMETROS ---
                params = {}
                perc_params = getattr(cls, "percentage_parameters", [])

                # Calcula a diagonal para conversões (evitando divisão por zero)
                diag = (
                    original_obj.dimensions.length
                    if (original_obj and original_obj.type == "MESH")
                    else 1.0
                )
                diag = diag if diag > 0 else 1.0

                for key in cls.__annotations__.keys():
                    if key.startswith("blender_") or key.startswith("ui_"):
                        # Ignora variáveis exclusivas de interface ou do Blender
                        continue

                    val = getattr(props, key)

                    if key in perc_params:
                        # Envia o valor absoluto real direto para o motor C++, usando a classe atualizada da API
                        params[key] = pymeshlab.PureValue(float(val))
                    else:
                        params[key] = getattr(props, key)

                # Permite que o filtro intercepte, injete ou altere parâmetros antes de enviar ao motor C++
                if hasattr(cls, "pre_process_parameters"):
                    cls.pre_process_parameters(params, props)

                # EXECUÇÃO: Aplica o filtro com os parâmetros mapeados
                ms.apply_filter(cls.pymeshlab_filter, **params)

                # ==========================================================
                # PÓS-PROCESSAMENTO NATIVO (C++) - Controle de Malha (Quad/Tri)
                # ==========================================================
                # Permite que cada filtro defina sua própria lógica baseada no estado do checkbox
                if hasattr(props, "blender_quad"):
                    if props.blender_quad:
                        if (
                            hasattr(cls, "post_filter_on_true")
                            and cls.post_filter_on_true
                        ):
                            ms.apply_filter(cls.post_filter_on_true)
                    else:
                        if (
                            hasattr(cls, "post_filter_on_false")
                            and cls.post_filter_on_false
                        ):
                            ms.apply_filter(cls.post_filter_on_false)

                # ==========================================================
                # RECUPERAÇÃO DA GEOMETRIA: MEMÓRIA vs DISCO
                # ==========================================================
                new_obj = None

                if engine == "MEMORY":
                    # Extrai as matrizes processadas diretamente da memória RAM
                    out_mesh = ms.current_mesh()
                    out_vertices = out_mesh.vertex_matrix()

                    # O método polygonal_face_list() retorna a lista real de Quads/Ngons nativa do PyMeshLab.
                    # Extração Inteligente: Avalia se usa Ngons ou Triângulos nativos
                    out_faces = []
                    use_polygons = False

                    if hasattr(out_mesh, "polygonal_face_list"):
                        try:
                            poly_list = out_mesh.polygonal_face_list()
                            if isinstance(poly_list, list) and len(poly_list) > 0:
                                # Checa se os polígonos englobam TODOS os vértices.
                                # Se sobrar vértice de fora (como os centros do Dodecaedro Sym), aborta os ngons.
                                used_verts = len(np.unique(np.concatenate(poly_list)))
                                if used_verts == len(out_vertices):
                                    out_faces = poly_list
                                    use_polygons = True
                        except Exception:
                            pass

                    # Alternativa de segurança para a matriz de triângulos bruta
                    if not use_polygons:
                        out_faces = out_mesh.face_matrix()

                    out_quality = None
                    if out_mesh.has_vertex_scalar():
                        out_quality = out_mesh.vertex_scalar_array()

                    # Libera a memória C++ imediatamente após extrair as matrizes
                    ms.clear()
                    del ms
                    gc.collect()

                    # Constrói o novo objeto no Blender sem tocar no disco
                    temp_name = original_obj.name if original_obj else "Mesh"
                    new_obj = utils.numpy_to_blender(
                        out_vertices, out_faces, temp_name, vertex_quality=out_quality
                    )

                    # Linka o objeto gerado na cena atual e o define como ativo
                    context.collection.objects.link(new_obj)
                    bpy.ops.object.select_all(action="DESELECT")
                    new_obj.select_set(True)
                    context.view_layer.objects.active = new_obj

                elif engine == "DISK":
                    # Resgata a flag localmente para evitar erro de escopo no Pylance
                    use_ply = getattr(cls, "prefer_ply_disk", False)

                    # Salva o resultado temporariamente no disco
                    if use_ply:
                        ms.save_current_mesh(output_path)
                    else:
                        # Força a API C++ a preservar Quads/Ngons ao invés de triangular no OBJ
                        ms.save_current_mesh(output_path, save_polygonal=True)
                    ms.clear()
                    del ms
                    gc.collect()

                    if not os.path.exists(output_path):
                        return (
                            "CANCELLED",
                            "O motor C++ falhou silenciosamente e nenhuma malha foi gerada no disco.",
                        )

                    # IMPORTAÇÃO DA MALHA PROCESSADA via importador nativo correspondente
                    # O uso explícito de Y Forward e Z Up desativa a conversão automática de eixos do Blender.
                    # Isso impede que o importador adicione rotações escondidas de 90 graus na matrix_world,
                    # garantindo que as matrizes de primitivas, planos e subdivisões funcionem perfeitamente.
                    if use_ply:
                        bpy.ops.wm.ply_import(
                            filepath=output_path, forward_axis="Y", up_axis="Z"
                        )
                    else:
                        bpy.ops.wm.obj_import(
                            filepath=output_path, forward_axis="Y", up_axis="Z"
                        )

                    if context.selected_objects:
                        new_obj = context.selected_objects[0]

                        # Limpa a seleção da malha vinda do disco também
                        if new_obj.type == "MESH":
                            m_data = new_obj.data

                            # FORÇA O BLENDER A CALCULAR AS ARESTAS DO PLY ANTES DA LIMPEZA
                            m_data.update(calc_edges=True)

                            m_data.vertices.foreach_set(
                                "select", np.zeros(len(m_data.vertices), dtype=bool)
                            )
                            m_data.polygons.foreach_set(
                                "select", np.zeros(len(m_data.polygons), dtype=bool)
                            )
                            m_data.edges.foreach_set(
                                "select", np.zeros(len(m_data.edges), dtype=bool)
                            )

                            # SALVA O ESTADO LIMPO
                            m_data.update()
                    else:
                        return "CANCELLED", "Failed to import the processed mesh."

                if cls.requires_selection and has_mesh:
                    # RESTAURAÇÃO DE MATRIZ: Se o objeto original tinha escala ou rotação aplicadas em Object Mode,
                    # a exportação/importação bagunça isso. Esse bloco injeta a World Matrix exata do original.

                    preserve = getattr(props, "blender_preserve_transforms", False)

                    if preserve:
                        new_obj.data.transform(original_obj.matrix_world.inverted())
                        new_obj.matrix_world = original_obj.matrix_world.copy()
                        # Força o Blender a manter os mesmos números limpos na UI
                        new_obj.rotation_euler = original_obj.rotation_euler.copy()
                        new_obj.scale = original_obj.scale.copy()
                    else:
                        loc = original_obj.matrix_world.translation
                        new_matrix = mathutils.Matrix.Translation(loc)
                        new_obj.data.transform(new_matrix.inverted())
                        new_obj.matrix_world = new_matrix

                    # NOMEAÇÃO AUTOMÁTICA (Filtros de edição ou geração):
                    if hasattr(cls, "custom_name") and cls.custom_name:
                        new_obj.name = f"{cls.custom_name}_bpymeshlab"
                    else:
                        base_name = original_obj.name.split("_bpymeshlab")[0]
                        new_obj.name = f"{base_name}_bpymeshlab"
                else:
                    # NOMEAÇÃO AUTOMÁTICA E ROTAÇÃO PARA PRIMITIVAS (Filtros de Criação)
                    obj_name = cls.pymeshlab_filter.replace("create_", "").title()
                    new_obj.name = f"{obj_name}_bpymeshlab"
                    new_obj.location = context.scene.cursor.location

                    # Aplicação da Rotação Corrigida Positiva para compensar o eixo Y-up gerado pelo PyMeshLab
                    new_obj.rotation_euler = (math.radians(90), 0, 0)
                    new_obj.scale = (1, 1, 1)

                    # RESET: Apply Transform (Rotate & Scale) para resetar a orientação base no Blender
                    context.view_layer.objects.active = new_obj
                    new_obj.select_set(True)
                    bpy.ops.object.transform_apply(
                        location=False, rotation=True, scale=True
                    )

                new_obj.data.update()

                # CONFIGURAÇÃO DE ATIVIDADE: Define o recém-criado como ativo na cena.
                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                # LIMPEZA DE ATRIBUTOS: O PyMeshLab/PLY pode gerar sujeira como normais travadas ou UVs residuais.
                if new_obj.type == "MESH" and new_obj.data:
                    for attr in cls.remove_attributes:
                        if attr in new_obj.data.attributes:
                            new_obj.data.attributes.remove(
                                new_obj.data.attributes[attr]
                            )

                # SHADE FLAT / SMOOTH: Controle de suavização das normais no Blender.
                if getattr(props, "blender_smooth", False):
                    bpy.ops.object.shade_smooth(keep_sharp_edges=True)
                elif cls.shade_flat:
                    bpy.ops.object.shade_flat()

                # AÇÃO SOBRE O OBJETO ANTERIOR (Keep, Hide, Delete)
                if apply_prev_mesh_action in ["HIDE", "DELETE"]:
                    for obj in original_selected_objs:
                        if obj:
                            if apply_prev_mesh_action == "HIDE":
                                obj.hide_set(True)
                            elif apply_prev_mesh_action == "DELETE":
                                bpy.data.objects.remove(obj, do_unlink=True)

            return "FINISHED", f"Filter '{cls.pymeshlab_filter}' applied successfully!"

        except Exception as e:
            return "CANCELLED", f"Error applying filter: {str(e)}"


class MESHLAB_OT_apply_filter(bpy.types.Operator):
    bl_idname = "meshlab.apply_filter"
    bl_label = "Apply MeshLab Filter"
    bl_description = "Apply the selected filter using PyMeshLab."
    bl_options = {"REGISTER", "UNDO"}

    # options={'HIDDEN'} esconde a variável interna do painel "Adjust Last Operation" do Blender
    filter_id: bpy.props.StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == "VIEW_3D"

    def execute(self, context):
        # A nova arquitetura busca a classe e as propriedades mapeadas dinamicamente
        prop_name = f"ml_{self.filter_id}"
        if not hasattr(context.scene, prop_name):
            self.report(
                {"ERROR"}, f"Filtro '{self.filter_id}' não existe no registro dinâmico."
            )
            return {"CANCELLED"}

        props = getattr(context.scene, prop_name)
        cls_def = type(props)  # Recupera a classe mestra/filtro instanciada no Blender

        # ---- INÍCIO DO CRONÔMETRO ----
        start_time = time.perf_counter()

        # O desempacotamento extrai o status e a mensagem da classe base
        status, msg = cls_def.apply_filter(context, props)

        # ---- FIM DO CRONÔMETRO ----
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        if status == "FINISHED":
            # Formata a mensagem para mostrar o tempo e o motor usado
            engine_used = context.scene.meshlab_prefs.processing_engine
            final_msg = f"{msg} (Tempo: {elapsed_time:.3f} segundos via {engine_used})"

            # Mostra na interface (rodape do Blender) e imprime no console System
            self.report({"INFO"}, final_msg)
            print(
                f"\n[BPyMeshLab] Operação concluída: {elapsed_time:.3f} segundos | Motor: {engine_used}\n"
            )

            return {"FINISHED"}
        else:
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}
