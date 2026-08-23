from bpy.types import PropertyGroup
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_convex_hull(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_convex_hull"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "JOIN"
