from bpy.types import PropertyGroup
from bpy.props import FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_merge_close_vertices(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_merge_close_vertices"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    percentage_parameters = ["threshold"]
    prefer_ply_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    threshold: FloatProperty(
        name="Merging distance",
        description="All the vertices that closer than this threshold are merged together. Use very small values, default values is 1/10000 of bounding box diagonal.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0001,
        min=0.0,
    )
