import bpy
import mathutils
import bmesh
from bpy.app.handlers import persistent
from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_meshing_decimation_quadric_edge_collapse(
    PropertyGroup, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_decimation_quadric_edge_collapse"
    is_processing = False
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key in ["blender_preserve_transforms", "selectedonly"]:
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        # Esmaece e bloqueia o número de faces se o Batch estiver ativo
        if key == "targetfacenum":
            return getattr(self, "blender_batch", False)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Swap da chave de seleção para a exigência do PyMeshLab
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

        # Converte a barra visual do Blender (0 a 100) para o padrão C++ (0.0 a 1.0)
        if "targetperc" in params:
            params["targetperc"] = params["targetperc"] / 100.0

        # Remove a chave se for 0, permitindo que a API do PyMeshLab acione seu próprio fallback
        if "targetfacenum" in params and params["targetfacenum"] == 0:
            params.pop("targetfacenum")

    @classmethod
    def apply_filter(cls, context, props):
        cls.is_processing = True
        try:
            return cls._execute_filter(context, props)
        finally:
            cls.is_processing = False

    @classmethod
    def _execute_filter(cls, context, props):
        is_batch = getattr(props, "blender_batch", False)
        target_perc = getattr(props, "targetperc", 0.0)

        # Trava de Segurança Crítica para Batch Process
        if is_batch and target_perc == 0.0:
            return (
                "CANCELLED",
                "Erro: No modo Batch, a Porcentagem de Redução (Percentage reduction) deve ser maior que 0%.",
            )

        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # MODO BATCH ou MODO ÚNICO
        if is_batch or len(original_objs) == 1:
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

                status, msg = super().apply_filter(context, props)

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
                "Batch Quadric Edge Collapse concluído"
                if len(original_objs) > 1
                else "Quadric Edge Collapse concluído"
            )
            return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

        # MODO GLOBAL (BOOLEAN MANIFOLD VIA COLLECTION)
        else:
            bpy.ops.object.select_all(action="DESELECT")

            temp_col = bpy.data.collections.new("Temp_Boolean_Collection")
            context.scene.collection.children.link(temp_col)

            temp_objs = []
            for obj in original_objs:
                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                temp_col.objects.link(new_obj)

                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                bpy.ops.object.convert(target="MESH")
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )
                temp_objs.append(new_obj)

            host_mesh = bpy.data.meshes.new("Host_Mesh")
            host_obj = bpy.data.objects.new("Host_Obj", host_mesh)
            context.collection.objects.link(host_obj)

            bpy.ops.object.select_all(action="DESELECT")
            host_obj.select_set(True)
            context.view_layer.objects.active = host_obj

            active_orig = (
                context.active_object
                if context.active_object in original_objs
                else original_objs[0]
            )
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
                    "A união falhou. O modo Global exige que as malhas cruzadas sejam fechadas (Manifold).",
                )

            for obj in temp_objs:
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(temp_col)

            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            # --- LIMPEZA DE COSTURA BOOLEANA (WELD) ---

            bm = bmesh.new()
            bm.from_mesh(host_obj.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.00001)
            bm.to_mesh(host_obj.data)
            bm.free()
            host_obj.data.update()

            # OVERRIDE TEMPORÁRIO: Desliga o selectedonly para evitar falha matemática na superfície recém unida
            original_selectedonly = getattr(props, "selectedonly", False)
            if original_selectedonly:
                props.selectedonly = False

            status, msg = super().apply_filter(context, props)

            # Restaura a opção original da interface
            if original_selectedonly:
                props.selectedonly = True

            if host_obj:
                try:
                    if host_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(host_obj, do_unlink=True)
                except ReferenceError:
                    pass

            if status == "FINISHED" and context.active_object:
                base_name = active_orig.name.split("_bpymeshlab")[0]
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

            return status, "Global Quadric Edge Collapse gerado com sucesso."

    blender_batch: BoolProperty(
        name="Batch Process",
        description="If checked, processes each selected object individually. If unchecked, generates a single global volume englobing all objects.",
        default=False,
    )
    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )
    targetfacenum: IntProperty(
        name="Target number of faces",
        description="The desired final number of faces.",
        default=0,
        min=0,
    )
    targetperc: FloatProperty(
        name="Percentage reduction",
        description="If non zero, this parameter specifies the desired final size of the mesh as a percentage of the initial size.",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE",
    )
    qualitythr: FloatProperty(
        name="Quality threshold",
        description="Quality threshold for penalizing bad shaped faces.The value is in the range [0..1] 0 accept any kind of face (no penalties), 0.5 penalize faces with quality.",
        default=0.3,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    preserveboundary: BoolProperty(
        name="Preserve Boundary of the mesh",
        description="The simplification process tries to do not affect mesh boundaries during simplification.",
        default=False,
    )
    boundaryweight: FloatProperty(
        name="Boundary Preserving Weight",
        description="The importance of the boundary during simplification. Default (1.0) means that the boundary has the same importance of the rest. Values greater than 1.0 raise boundary importance and has the effect of removing less vertices on the border. Admitted range of values (0,+inf).",
        default=1.0,
        min=0.0,
    )
    preservenormal: BoolProperty(
        name="Preserve Normal",
        description="Try to avoid face flipping effects and try to preserve the original orientation of the surface.",
        default=False,
    )
    preservetopology: BoolProperty(
        name="Preserve Topology",
        description="Avoid all the collapses that should cause a topology change in the mesh (like closing holes, squeezing handles, etc). If checked the genus of the mesh should stay unchanged.",
        default=False,
    )
    optimalplacement: BoolProperty(
        name="Optimal position of simplified vertices",
        description="Each collapsed vertex is placed in the position minimizing the quadric error. It can fail (creating bad spikes) in case of very flat areas. If disabled edges are collapsed onto one of the two original vertices and the final mesh is composed by a subset of the original vertices.",
        default=True,
    )
    planarquadric: BoolProperty(
        name="Planar Simplification",
        description="Add additional simplification constraints that improves the quality of the simplification of the planar portion of the mesh, as a side effect, more triangles will be preserved in flat areas (allowing better shaped triangles).",
        default=False,
    )
    planarweight: FloatProperty(
        name="Planar Simp. Weight",
        description="How much we should try to preserve the triangles in the planar regions. If you lower this value planar areas will be simplified more.",
        default=0.001,
    )
    qualityweight: BoolProperty(
        name="Weighted Simplification",
        description="Use the Per-Vertex quality as a weighting factor for the simplification. The weight is used as a error amplification value, so a vertex with a high quality value will not be simplified and a portion of the mesh with low quality values will be aggressively simplified.",
        default=False,
    )
    autoclean: BoolProperty(
        name="Post-simplification cleaning",
        description="After the simplification an additional set of steps is performed to clean the mesh (unreferenced vertices, bad faces, etc).",
        default=True,
    )
    selectedonly: BoolProperty(
        name="Simplify only selected faces",
        description="The simplification is applied only to the selected set of faces. Take care of the target number of faces!.",
        default=False,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )


_last_selected_mesh_names = set()
_last_active_filter = ""


@persistent
def update_targetfacenum_handler(scene, depsgraph):
    global _last_selected_mesh_names, _last_active_filter

    if MESHLAB_PG_meshing_decimation_quadric_edge_collapse.is_processing:
        return

    ui_state = getattr(scene, "meshlab_ui_state", None)
    if not ui_state:
        return

    current_filter = ui_state.filter_name

    # Se o filtro atual não for este, apenas gravamos qual é e abortamos
    if current_filter != "meshing_decimation_quadric_edge_collapse":
        _last_active_filter = current_filter
        return

    selected_meshes = [
        obj for obj in bpy.context.selected_objects if obj.type == "MESH"
    ]
    current_names = {obj.name for obj in selected_meshes}

    # Recalcula se a seleção de objetos mudou OU se o usuário acabou de abrir este filtro na UI
    if (
        current_names != _last_selected_mesh_names
        or current_filter != _last_active_filter
    ):
        _last_selected_mesh_names = current_names
        _last_active_filter = current_filter

        props = getattr(scene, "ml_meshing_decimation_quadric_edge_collapse", None)

        # Só atualiza a matemática se existir propriedades e se o Batch estiver desligado
        if props and not getattr(props, "blender_batch", False):
            total_tris = 0
            for obj in selected_meshes:
                # Usa a função nativa do Blender para calcular os triângulos exatos
                obj.data.calc_loop_triangles()
                total_tris += len(obj.data.loop_triangles)

            # Preenche a interface instantaneamente com a metade
            props.targetfacenum = max(0, total_tris // 2)


# Garante que o handler não seja duplicado em memória quando você recarregar o script no Blender
if update_targetfacenum_handler not in bpy.app.handlers.depsgraph_update_post:
    bpy.app.handlers.depsgraph_update_post.append(update_targetfacenum_handler)
