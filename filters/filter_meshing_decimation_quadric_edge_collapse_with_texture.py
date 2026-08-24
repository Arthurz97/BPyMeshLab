import bpy
from bpy.types import PropertyGroup
from bpy.app.handlers import persistent
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_decimation_quadric_edge_collapse_with_texture(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_decimation_quadric_edge_collapse_with_texture"
    is_processing = False
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_uv_disk = True  # Força a Classe Mestra a usar OBJ para I/O
    # NOTA: prefer_ply_disk = True NÃO está declarado.
    # O fallback (False) forçará o motor C++ a devolver a malha em .obj, preservando as UVs.
    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        if key == "selectedonly":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        if key == "targetfacenum":
            return getattr(self, "blender_batch", False)

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

        if "targetperc" in params:
            params["targetperc"] = params["targetperc"] / 100.0

        if "targetfacenum" in params and params["targetfacenum"] == 0:
            params.pop("targetfacenum")

    @classmethod
    def apply_filter(cls, context, props):
        cls.is_processing = True
        try:
            is_batch = getattr(props, "blender_batch", False)
            target_perc = getattr(props, "targetperc", 0.0)

            if is_batch and target_perc == 0.0:
                return (
                    "CANCELLED",
                    "Erro: No modo Batch, a Porcentagem de Redução (Percentage reduction) deve ser maior que 0%.",
                )

            # TRAVA DE SEGURANÇA UV
            original_objs = [
                obj for obj in context.selected_objects if obj.type == "MESH"
            ]
            for obj in original_objs:
                if not obj.data.uv_layers:
                    return (
                        "CANCELLED",
                        f"Filtro abortado: A malha '{obj.name}' não possui um UV Map (Coordenadas de Textura).",
                    )

            return super().apply_filter(context, props)
        finally:
            cls.is_processing = False

    targetfacenum: IntProperty(
        name="Target number of faces",
        description="Target number of faces:",
        default=6,
        min=0,
    )
    targetperc: FloatProperty(
        name="Percentage reduction",
        description="If non zero, this parameter specifies the desired final size of the mesh as a percentage of the initial mesh.",
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
    extratcoordw: FloatProperty(
        name="Texture Weight",
        description="Additional weight for each extra Texture Coordinates for every (selected) vertex.",
        default=1.0,
    )
    preserveboundary: BoolProperty(
        name="Preserve Boundary of the mesh",
        description="The simplification process tries not to destroy mesh boundaries.",
        default=False,
    )
    boundaryweight: FloatProperty(
        name="Boundary Preserving Weight",
        description="The importance of the boundary during simplification. Default (1.0) means that the boundary has the same importance of the rest. Values greater than 1.0 raise boundary importance and has the effect of removing less vertices on the border. Admitted range of values (0,+inf).",
        default=1.0,
        min=0.0,
    )
    optimalplacement: BoolProperty(
        name="Optimal position of simplified vertices",
        description="Each collapsed vertex is placed in the position minimizing the quadric error. It can fail (creating bad spikes) in case of very flat areas. If disabled edges are collapsed onto one of the two original vertices and the final mesh is composed by a subset of the original vertices.",
        default=True,
    )
    preservenormal: BoolProperty(
        name="Preserve Normal",
        description="Try to avoid face flipping effects and try to preserve the original orientation of the surface.",
        default=False,
    )
    planarquadric: BoolProperty(
        name="Planar Simplification",
        description="Add additional simplification constraints that improves the quality of the simplification of the planar portion of the mesh.",
        default=False,
    )
    selectedonly: BoolProperty(
        name="Simplify only selected faces",
        description="The simplification is applied only to the selected set of faces. Take care of the target number of faces!.",
        default=False,
    )


_last_selected_mesh_names = set()
_last_active_filter = ""


@persistent
def update_targetfacenum_with_texture_handler(scene, depsgraph):
    global _last_selected_mesh_names, _last_active_filter

    if MESHLAB_PG_decimation_quadric_edge_collapse_with_texture.is_processing:
        return

    ui_state = getattr(scene, "meshlab_ui_state", None)
    if not ui_state:
        return

    current_filter = ui_state.filter_name

    if current_filter != "meshing_decimation_quadric_edge_collapse_with_texture":
        _last_active_filter = current_filter
        return

    selected_meshes = [
        obj for obj in bpy.context.selected_objects if obj.type == "MESH"
    ]
    current_names = {obj.name for obj in selected_meshes}

    if (
        current_names != _last_selected_mesh_names
        or current_filter != _last_active_filter
    ):
        _last_selected_mesh_names = current_names
        _last_active_filter = current_filter

        props = getattr(
            scene, "ml_meshing_decimation_quadric_edge_collapse_with_texture", None
        )

        if props and not getattr(props, "blender_batch", False):
            total_tris = 0
            for obj in selected_meshes:
                obj.data.calc_loop_triangles()
                total_tris += len(obj.data.loop_triangles)

            props.targetfacenum = max(0, total_tris // 2)


if (
    update_targetfacenum_with_texture_handler
    not in bpy.app.handlers.depsgraph_update_post
):
    bpy.app.handlers.depsgraph_update_post.append(
        update_targetfacenum_with_texture_handler
    )
