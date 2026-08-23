from bpy.types import PropertyGroup
from bpy.props import IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_tri_to_quad_by_4_8_subdivision(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_tri_to_quad_by_4_8_subdivision"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    batch_support = True
    global_mode = "NONE"

    @classmethod
    def pre_process_parameters(cls, params, props):
        if "iterations" in params:
            params.pop("iterations")

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        for _ in range(props.iterations - 1):
            ms.apply_filter(cls.pymeshlab_filter, **params)

    iterations: IntProperty(
        name="Iterations",
        description="Number of times the model is subdivided.",
        default=1,
        min=1,
    )
