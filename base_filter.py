import bpy, os, tempfile, gc, math
import pymeshlab
import numpy as np
import time
from . import utils


class MeshLabFilterBase:
    pymeshlab_filter = ""
    requires_selection = False
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
        if len(original_selected_objs) > 1:
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

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, "output.ply")
                ms = pymeshlab.MeshSet()

                # ==========================================================
                # CAMINHO 1: PROCESSAMENTO EM MEMÓRIA (NumPy) - ALTA PERFORMANCE
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
                # CAMINHO 2: PROCESSAMENTO EM DISCO (I/O) - FALLBACK DE SEGURANÇA
                # ==========================================================
                elif engine == "DISK":
                    if cls.requires_selection and has_mesh:
                        input_path = os.path.join(tmpdir, "input.ply")
                        bpy.ops.object.select_all(action="DESELECT")
                        original_obj.select_set(True)

                        # Sincroniza a memória do Blender
                        context.view_layer.update()
                        original_obj.data.update()

                        # ---- 1. PROTEÇÃO DE CORES E TRANSFERÊNCIA DE SELEÇÃO ----
                        temp_color = None
                        export_kwargs = {
                            "filepath": input_path,
                            "export_selected_objects": True,
                            "ascii_format": False,  # Força explicitamente o formato Binário
                        }

                        if is_selected_only:
                            # USAMOS POINT (Vértices) porque o PLY C++ garante essa exportação
                            temp_color = original_obj.data.color_attributes.new(
                                name="Col", type="BYTE_COLOR", domain="POINT"
                            )
                            original_obj.data.attributes.active_color = temp_color

                            # Extrai a seleção diretamente dos vértices
                            colors = [
                                val
                                for v in original_obj.data.vertices
                                for val in (
                                    (1.0, 1.0, 1.0, 1.0)
                                    if v.select
                                    else (0.0, 0.0, 0.0, 1.0)
                                )
                            ]
                            temp_color.data.foreach_set("color", colors)
                            export_kwargs["export_colors"] = "SRGB"

                        # Exporta dinamicamente passando os parâmetros seguros
                        bpy.ops.wm.ply_export(**export_kwargs)

                        # Limpeza imediata para manter seu objeto original intacto
                        if temp_color:
                            original_obj.data.color_attributes.remove(temp_color)

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
                # RECUPERAÇÃO DA GEOMETRIA: MEMÓRIA vs DISCO
                # ==========================================================
                new_obj = None

                if engine == "MEMORY":
                    # Extrai as matrizes processadas diretamente da memória RAM
                    out_mesh = ms.current_mesh()
                    out_vertices = out_mesh.vertex_matrix()
                    out_faces = out_mesh.face_matrix()

                    # Libera a memória C++ imediatamente após extrair as matrizes
                    ms.clear()
                    del ms
                    gc.collect()

                    # Constrói o novo objeto no Blender sem tocar no disco
                    temp_name = original_obj.name if original_obj else "Mesh"
                    new_obj = utils.numpy_to_blender(out_vertices, out_faces, temp_name)

                    # Linka o objeto gerado na cena atual e o define como ativo
                    context.collection.objects.link(new_obj)
                    bpy.ops.object.select_all(action="DESELECT")
                    new_obj.select_set(True)
                    context.view_layer.objects.active = new_obj

                elif engine == "DISK":
                    # Salva o resultado temporariamente no disco
                    ms.save_current_mesh(output_path)

                    # SEGURANÇA DE FALHA E LIMPEZA DE MEMÓRIA (C++)
                    ms.clear()
                    del ms
                    gc.collect()

                    if not os.path.exists(output_path):
                        return (
                            "CANCELLED",
                            "O motor C++ falhou silenciosamente e nenhuma malha foi gerada no disco.",
                        )

                    # IMPORTAÇÃO DA MALHA PROCESSADA via importador nativo
                    bpy.ops.wm.ply_import(filepath=output_path)

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
                    new_obj.data.transform(original_obj.matrix_world.inverted())
                    new_obj.matrix_world = original_obj.matrix_world.copy()

                    # NOMEAÇÃO AUTOMÁTICA (Filtros de edição):
                    base_name = original_obj.name.split("_pymeshlab")[0]
                    new_obj.name = f"{base_name}_pymeshlab"
                else:
                    # NOMEAÇÃO AUTOMÁTICA E ROTAÇÃO PARA PRIMITIVAS (Filtros de Criação)
                    obj_name = cls.pymeshlab_filter.replace("create_", "").title()
                    new_obj.name = f"{obj_name}_pymeshlab"
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

                # SHADE FLAT: Aplicável a primitivas criadas ou malhas onde normais suaves causem artefatos visuais.
                if cls.shade_flat:
                    bpy.ops.object.shade_flat()

                # PÓS-PROCESSAMENTO BLENDER: Converte triângulos em quads se ativado na UI
                if getattr(props, "blender_quad", False):
                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.select_all(action="SELECT")
                    bpy.ops.mesh.tris_convert_to_quads()

                    # DESMARCA TUDO ANTES DE SAIR DO MODO DE EDIÇÃO
                    bpy.ops.mesh.select_all(action="DESELECT")

                    bpy.ops.object.mode_set(mode="OBJECT")

                    # DESMARCA TUDO ANTES DE SAIR DO MODO DE EDIÇÃO
                    bpy.ops.mesh.select_all(action="DESELECT")

                    bpy.ops.object.mode_set(mode="OBJECT")

                # PÓS-PROCESSAMENTO BLENDER: Reconstrói Ngons via Decimate Planar se ativado na UI
                if getattr(props, "blender_ngon", False):
                    mod = new_obj.modifiers.new(name="Planar_Decimate", type="DECIMATE")
                    mod.decimate_type = "DISSOLVE"
                    mod.angle_limit = math.radians(5.0)
                    bpy.ops.object.modifier_apply(modifier=mod.name)

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
        from .filters import filters_create, filters_meshing, filters_generate

        # Mapeamento estrito das classes de filtro ativadas pelo Menu UI
        mapping = {
            "create_cube": (
                filters_create.MESHLAB_PG_create_cube,
                context.scene.ml_create_cube,
            ),
            "create_sphere": (
                filters_create.MESHLAB_PG_create_sphere,
                context.scene.ml_create_sphere,
            ),
            "create_sphere_cap": (
                filters_create.MESHLAB_PG_create_sphere_cap,
                context.scene.ml_create_sphere_cap,
            ),
            "create_torus": (
                filters_create.MESHLAB_PG_create_torus,
                context.scene.ml_create_torus,
            ),
            "create_annulus": (
                filters_create.MESHLAB_PG_create_annulus,
                context.scene.ml_create_annulus,
            ),
            "create_cone": (
                filters_create.MESHLAB_PG_create_cone,
                context.scene.ml_create_cone,
            ),
            "create_dodecahedron": (
                filters_create.MESHLAB_PG_create_dodecahedron,
                context.scene.ml_create_dodecahedron,
            ),
            "create_dodecahedron_sym": (
                filters_create.MESHLAB_PG_create_dodecahedron_sym,
                context.scene.ml_create_dodecahedron_sym,
            ),
            "create_icosahedron": (
                filters_create.MESHLAB_PG_create_icosahedron,
                context.scene.ml_create_icosahedron,
            ),
            "create_octahedron": (
                filters_create.MESHLAB_PG_create_octahedron,
                context.scene.ml_create_octahedron,
            ),
            "create_tetrahedron": (
                filters_create.MESHLAB_PG_create_tetrahedron,
                context.scene.ml_create_tetrahedron,
            ),
            "meshing_isotropic_explicit_remeshing": (
                filters_meshing.MESHLAB_PG_meshing_isotropic_explicit_remeshing,
                context.scene.ml_meshing_isotropic_explicit_remeshing,
            ),
            "generate_resampled_uniform_mesh": (
                filters_generate.MESHLAB_PG_generate_resampled_uniform_mesh,
                context.scene.ml_generate_resampled_uniform_mesh,
            ),
        }

        if self.filter_id not in mapping:
            self.report({"ERROR"}, "Filtro mapeado não existe na arquitetura.")
            return {"CANCELLED"}

        cls_def, props = mapping[self.filter_id]

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
                f"\n[PyMeshLab Integrator] Operação concluída: {elapsed_time:.3f} segundos | Motor: {engine_used}\n"
            )

            return {"FINISHED"}
        else:
            self.report({"ERROR"}, msg)
            return {"CANCELLED"}
