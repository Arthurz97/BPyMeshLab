from bpy.types import PropertyGroup
from bpy.props import EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_tri_to_quad_dominant(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_tri_to_quad_dominant"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    batch_support = True
    global_mode = "NONE"

    @classmethod
    def pre_process_parameters(cls, params, props):
        params["level"] = int(props.level)

    level: EnumProperty(
        name="Optimize For",
        description="Choose any of three different greedy strategies.",
        items=[
            ("0", "Fewest triangles", ""),
            ("1", "(in between)", ""),
            ("2", "Better quad shape", ""),
        ],
        default="0",
    )
