import bpy, os, tempfile, gc, math
import bmesh
import pymeshlab
import mathutils
import numpy as np
import time
from . import utils


class MeshLabSmoothProp:
    blender_smooth: bpy.props.BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )


def get_blender_batch(self):
    # Se o filtro não suportar Global, a UI força o botão a ficar marcado (True)
    mode = (
        self.__class__.get_global_mode(self)
        if hasattr(self.__class__, "get_global_mode")
        else getattr(self.__class__, "global_mode", "NONE")
    )
    if mode == "NONE":
        return True
    return self.get("blender_batch", False)


def set_blender_batch(self, value):
    self["blender_batch"] = value


class MeshLabPreserveTransformsProp:
    blender_preserve_transforms: bpy.props.BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )

    def is_property_disabled(self, key, context):
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False


class MeshLabBatchOnlyProp:
    blender_batch: bpy.props.BoolProperty(
        name="Batch Process",
        description="If checked, processes each selected object individually. If unchecked, generates a single global volume englobing all objects.",
        get=get_blender_batch,
        set=set_blender_batch,
    )

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            mode = (
                self.__class__.get_global_mode(self)
                if hasattr(self.__class__, "get_global_mode")
                else getattr(self.__class__, "global_mode", "NONE")
            )
            if mode == "NONE":
                return True
            return len(context.selected_objects) <= 1

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False


# A classe original que os 17 filtros já usam.
# A ordem das classes na herança faz o Blender ler o Batch por último e desenhá-lo em cima na UI.
class MeshLabBatchGlobalProps(MeshLabPreserveTransformsProp, MeshLabBatchOnlyProp):
    pass


class MeshLabFilterBase:
    pymeshlab_filter = ""
    requires_selection = False
    ignore_selection_count = False
    shade_flat = False
    remove_attributes = []

    # Controles de Arquitetura (Batch/Global)
    batch_support = False
    global_mode = "NONE"  # Pode ser "BOOLEAN", "JOIN" ou "NONE"

    @classmethod
    def apply_filter(cls, context, props):
        current_global_mode = (
            cls.get_global_mode(props)
            if hasattr(cls, "get_global_mode")
            else cls.global_mode
        )

        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]

        # Se não requer seleção (ex: Primitivas), pula orquestração e vai direto para a criação
        if not cls.requires_selection:
            return cls._execute_core_filter(context, props, original_objs)

        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        # Trava de Segurança Múltipla Original (Mantida para filtros que não suportam Batch/Global)
        if (
            len(original_objs) > 1
            and not cls.batch_support
            and current_global_mode == "NONE"
            and not getattr(cls, "ignore_selection_count", False)
        ):
            return (
                "CANCELLED",
                "Múltiplas seleções não são suportadas. Selecione apenas 1 objeto.",
            )

        is_batch = getattr(props, "blender_batch", False)
        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # --- MODO BATCH ou OBJETO ÚNICO ---
        if (
            is_batch
            or len(original_objs) == 1
            or (not is_batch and current_global_mode == "NONE")
        ):
            for obj in original_objs:
                bpy.ops.object.select_all(action="DESELECT")

                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                context.collection.objects.link(new_obj)

                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                bpy.ops.object.convert(target="MESH")

                original_matrix = new_obj.matrix_world.copy()
                original_rotation = new_obj.rotation_euler.copy()
                original_scale = new_obj.scale.copy()
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )

                status, msg = cls._execute_core_filter(context, props, [new_obj])

                if preserve and status == "FINISHED" and context.active_object:
                    temp_matrix = mathutils.Matrix.Translation(
                        original_matrix.translation
                    )
                    context.active_object.data.transform(
                        original_matrix.inverted() @ temp_matrix
                    )
                    context.active_object.matrix_world = original_matrix
                    context.active_object.rotation_euler = original_rotation
                    context.active_object.scale = original_scale

                if status != "FINISHED":
                    overall_status = status
                    error_msg = msg

                if new_obj.name in bpy.data.objects:
                    bpy.data.objects.remove(new_obj, do_unlink=True)

                if status == "FINISHED" and context.active_object:
                    base_name = obj.name.split("_bpymeshlab")[0]
                    context.active_object.name = f"{base_name}_bpymeshlab"

            prefs.global_prev_mesh_action = original_action

            if overall_status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if overall_status != "FINISHED":
                return overall_status, error_msg

            msg_end = (
                "Batch Process concluído"
                if len(original_objs) > 1
                else "Filtro concluído"
            )
            return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

        # --- MODO GLOBAL (BOOLEAN OU JOIN) ---
        else:
            active_idx = 0
            if context.active_object in original_objs:
                active_idx = original_objs.index(context.active_object)

            bpy.ops.object.select_all(action="DESELECT")

            temp_objs = []
            temp_col = None

            if current_global_mode == "BOOLEAN":
                temp_col = bpy.data.collections.new("Temp_Boolean_Collection")
                context.scene.collection.children.link(temp_col)

            for obj in original_objs:
                new_obj = obj.copy()
                new_obj.data = obj.data.copy()

                if current_global_mode == "BOOLEAN":
                    temp_col.objects.link(new_obj)
                else:
                    context.collection.objects.link(new_obj)

                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                bpy.ops.object.convert(target="MESH")
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )
                temp_objs.append(new_obj)

            host_obj = None

            if current_global_mode == "JOIN":
                bpy.ops.object.select_all(action="DESELECT")
                for obj in temp_objs:
                    obj.select_set(True)
                context.view_layer.objects.active = temp_objs[active_idx]
                bpy.ops.object.join()
                host_obj = context.active_object

            elif current_global_mode == "BOOLEAN":
                host_mesh = bpy.data.meshes.new("Host_Mesh")
                host_obj = bpy.data.objects.new("Host_Obj", host_mesh)
                context.collection.objects.link(host_obj)

                bpy.ops.object.select_all(action="DESELECT")
                host_obj.select_set(True)
                context.view_layer.objects.active = host_obj

                active_orig = original_objs[active_idx]
                host_obj.location = active_orig.location.copy()

                bool_mod = host_obj.modifiers.new(name="Global_Union", type="BOOLEAN")
                bool_mod.operation = "UNION"
                bool_mod.operand_type = "COLLECTION"
                bool_mod.collection = temp_col
                bool_mod.solver = "MANIFOLD"

                bpy.ops.object.modifier_apply(modifier=bool_mod.name)

                if len(host_obj.data.polygons) == 0:
                    bpy.data.objects.remove(host_obj, do_unlink=True)
                    for obj in temp_objs:
                        bpy.data.objects.remove(obj, do_unlink=True)
                    bpy.data.collections.remove(temp_col)
                    return (
                        "CANCELLED",
                        "A união falhou. O modo Global Booleano exige que as malhas cruzadas sejam fechadas (Manifold).",
                    )

                for obj in temp_objs:
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(temp_col)

                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )

                # --- LIMPEZA DE COSTURA BOOLEANA (WELD) ---
                bm = bmesh.new()
                bm.from_mesh(host_obj.data)
                bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.00001)
                bm.to_mesh(host_obj.data)
                bm.free()
                host_obj.data.update()

            # OVERRIDE TEMPORÁRIO PARA BOOLEANOS DE FILTROS QUE USAM SELECTEDONLY
            original_selectedonly = getattr(props, "selectedonly", False)
            if original_selectedonly and current_global_mode == "BOOLEAN":
                props.selectedonly = False

            status, msg = cls._execute_core_filter(context, props, [host_obj])

            # Permite que os filtros chamem ganchos (ex: recalculo de normais)
            if (
                hasattr(cls, "post_process_mesh")
                and status == "FINISHED"
                and context.active_object
            ):
                cls.post_process_mesh(context, context.active_object)

            if original_selectedonly and current_global_mode == "BOOLEAN":
                props.selectedonly = True

            if host_obj:
                try:
                    if host_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(host_obj, do_unlink=True)
                except ReferenceError:
                    pass

            if current_global_mode == "JOIN":
                for obj in temp_objs:
                    try:
                        if obj.name in bpy.data.objects:
                            bpy.data.objects.remove(obj, do_unlink=True)
                    except ReferenceError:
                        pass

            if status == "FINISHED" and context.active_object:
                base_name = original_objs[active_idx].name.split("_bpymeshlab")[0]
                context.active_object.name = f"{base_name}_bpymeshlab"

            prefs.global_prev_mesh_action = original_action

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if status != "FINISHED":
                return status, msg

            return status, f"Processamento Global ({current_global_mode}) concluído."

    @classmethod
    def _execute_core_filter(cls, context, props, current_objs):
        # SEGURANÇA DE MODO: Garante que o Blender esteja no modo Objeto.
        # Evita crashes caso o usuário tente rodar o filtro de dentro do Edit Mode.
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_obj = context.active_object
        has_mesh = original_obj and original_obj.type == "MESH"
        original_selected_objs = current_objs

        # TRAVA DE MULTI-SELEÇÃO: O PyMeshLab em scripts simples pode se perder com múltiplos inputs.
        # Esta trava garante que a lógica de nomeação e matriz funcione perfeitamente sobre 1 único alvo.
        if len(original_selected_objs) > 1 and not getattr(
            cls, "ignore_selection_count", False
        ):
            return (
                "CANCELLED",
                "Múltiplas seleções não são suportadas. Selecione apenas 1 objeto.",
            )

        # TRAVA DE SEGURANÇA: Evita crash caso o usuário tente rodar um filtro de edição em um objeto malha fantasma (sem vértices).
        if cls.requires_selection and has_mesh and len(original_obj.data.vertices) == 0:
            return (
                "CANCELLED",
                "A malha selecionada está vazia. Este filtro exige geometria pré-existente.",
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

        # Trava de Segurança: Força o uso de DISCO para filtros que exigem polígonos, UVs ou disco exclusivo
        if (
            getattr(cls, "requires_polygons_disk", False)
            or getattr(cls, "requires_uv_disk", False)
            or getattr(cls, "forces_disk_only", False)
        ):
            engine = "DISK"

        # Trava de Segurança: Força o uso de RAM para filtros que dependem de injeção direta (ex: Scalar/Quality)
        if getattr(cls, "requires_ram_memory", False):
            engine = "MEMORY"

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
                    if cls.requires_selection and has_mesh:
                        # Extrai vértices, faces, matriz de seleção, escalar e normais
                        vertices, faces, v_colors, v_scalars, v_normals = (
                            utils.blender_to_numpy(
                                original_obj,
                                extract_selection=is_selected_only,
                                extract_quality=True,
                            )
                        )

                        mesh_kwargs = {"vertex_matrix": vertices, "face_matrix": faces}

                        if is_selected_only and v_colors is not None:
                            mesh_kwargs["v_color_matrix"] = v_colors

                        if v_scalars is not None:
                            mesh_kwargs["v_scalar_array"] = v_scalars

                        if v_normals is not None:
                            mesh_kwargs["v_normals_matrix"] = v_normals

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
                        req_poly_flag = getattr(cls, "requires_polygons_disk", False)
                        req_uv_flag = getattr(cls, "requires_uv_disk", False)

                        ext = "obj" if (req_poly_flag or req_uv_flag) else "ply"
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

                        # INÍCIO DA INJEÇÃO DE COR PARA SELEÇÃO (Unificado para OBJ e PLY)
                        if is_selected_only:
                            # USAMOS POINT (Vértices) para garantir a leitura no PyMeshLab
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

                        # Flags dinâmicas para evitar o rasgo de vértices (Vertex Splitting) no disco
                        req_normals = getattr(cls, "requires_normals_disk", False)
                        req_uv = getattr(cls, "requires_uv_disk", False)
                        requires_poly = getattr(cls, "requires_polygons_disk", False)

                        if ext == "obj":
                            # ROTA OBJ: Preserva Quads, N-gons OU transporta UV Maps com malha já triangulada
                            export_kwargs = {
                                "filepath": input_path,
                                "export_selected_objects": True,
                                "export_normals": req_normals,
                                "export_uv": req_uv,
                                "export_colors": is_selected_only,  # O exportador OBJ usa Booleano
                                "export_materials": False,  # Evita poluição de arquivos .mtl
                                "export_triangulated_mesh": not requires_poly,
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
                                "export_colors": (
                                    "SRGB" if is_selected_only else "NONE"
                                ),  # O exportador PLY usa Enum
                                "forward_axis": "Y",
                                "up_axis": "Z",
                            }

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
                    # Permite que o filtro execute outros algoritmos na memória C++ ANTES do filtro principal
                if hasattr(cls, "pre_invoke_filters"):
                    cls.pre_invoke_filters(ms, params, props)

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
                generated_objs = []
                extract_multi = getattr(cls, "extract_multiple_layers", False)

                # Feature Flag: Se for múltiplo, extrai as camadas geradas. Se não, extrai apenas a malha atual (default).
                target_ids = (
                    list(range(1, ms.mesh_number()))
                    if (extract_multi and ms.mesh_number() > 1)
                    else [-1]
                )
                layer_mapping = getattr(cls, "layer_mapping", {})

                for idx, m_id in enumerate(target_ids):
                    if m_id != -1:
                        ms.set_current_mesh(m_id)

                    # Proteção CRÍTICA: Ignora malhas vazias (ex: Poisson zerado pelo motor C++)
                    # Impede o importador do Blender de tentar ler arquivos PLY/OBJ sem vértices.
                    if ms.current_mesh().vertex_matrix().shape[0] == 0:
                        continue

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
                                    used_verts = len(
                                        np.unique(np.concatenate(poly_list))
                                    )
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

                        out_normals = None
                        try:
                            # O PyMeshLab não possui um booleano de checagem para normais na API atual.
                            # Extraímos diretamente com try/except para evitar falhas caso a matriz não exista.
                            out_normals = out_mesh.vertex_normal_matrix()
                        except Exception:
                            pass

                        # Constrói o novo objeto no Blender sem tocar no disco
                        temp_name = original_obj.name if original_obj else "Mesh"
                        new_obj = utils.numpy_to_blender(
                            out_vertices,
                            out_faces,
                            temp_name,
                            vertex_quality=out_quality,
                            vertex_normals=out_normals,
                        )

                        # Linka o objeto gerado na cena atual e o define como ativo
                        context.collection.objects.link(new_obj)

                        if idx == 0:
                            bpy.ops.object.select_all(action="DESELECT")
                        new_obj.select_set(True)
                        context.view_layer.objects.active = new_obj

                    elif engine == "DISK":
                        # Resgata a flag localmente para evitar erro de escopo no Pylance
                        use_ply = getattr(cls, "prefer_ply_disk", False)

                        # Evita sobrescrever o mesmo arquivo no loop de múltiplas extrações
                        loop_output = (
                            output_path.replace(".ply", f"_{m_id}.ply").replace(
                                ".obj", f"_{m_id}.obj"
                            )
                            if m_id != -1
                            else output_path
                        )

                        # Salva o resultado temporariamente no disco
                        if use_ply:
                            ms.save_current_mesh(loop_output)
                        else:
                            # Força a API C++ a preservar Quads/Ngons ao invés de triangular no OBJ
                            ms.save_current_mesh(
                                loop_output,
                                save_polygonal=True,
                                save_wedge_texcoord=True,
                            )

                        if not os.path.exists(loop_output):
                            continue  # Pula se falhou no disco silenciosamente

                        # IMPORTAÇÃO DA MALHA PROCESSADA via importador nativo correspondente
                        # O uso explícito de Y Forward e Z Up desativa a conversão automática de eixos do Blender.
                        # Isso impede que o importador adicione rotações escondidas de 90 graus na matrix_world,
                        # garantindo que as matrizes de primitivas, planos e subdivisões funcionem perfeitamente.
                        if use_ply:
                            bpy.ops.wm.ply_import(
                                filepath=loop_output, forward_axis="Y", up_axis="Z"
                            )
                        else:
                            bpy.ops.wm.obj_import(
                                filepath=loop_output, forward_axis="Y", up_axis="Z"
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
                            continue

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
                            # Se for filtro múltiplo, busca o nome no dicionário layer_mapping usando a ID da malha
                            if extract_multi:
                                suffix = layer_mapping.get(m_id, f"Layer_{m_id}")
                                new_obj.name = f"{base_name}_{suffix}"
                            else:
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

                    generated_objs.append(new_obj)

                # LIMPEZA DA MEMÓRIA C++ (Realizada de forma garantida após o loop de extração)
                # Também isolada do loop para não deletar a memória antes das outras extrações.
                try:
                    ms.clear()
                    del ms
                    gc.collect()
                except Exception:
                    pass

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
