from bpy.types import PropertyGroup
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_tri_to_quad_by_smart_triangle_pairing(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_tri_to_quad_by_smart_triangle_pairing"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    batch_support = True
    global_mode = "NONE"
