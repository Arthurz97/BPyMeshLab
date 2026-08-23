from bpy.types import PropertyGroup
from bpy.props import FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_decimation_clustering(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_decimation_clustering"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["threshold"]

    batch_support = True
    global_mode = "BOOLEAN"

    threshold: FloatProperty(
        name="Cell Size",
        description="The size of the cell of the clustering grid. Smaller the cell finer the resulting mesh. For obtaining a very coarse mesh use larger values.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
