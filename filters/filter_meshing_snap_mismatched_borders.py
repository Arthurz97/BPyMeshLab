from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_snap_mismatched_borders(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_snap_mismatched_borders"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    edgedistratio: FloatProperty(
        name="Edge Distance Ratio",
        description="Collapse edge when the edge / distance ratio is greater than this value. E.g. for default value 1000 two straight border edges are collapsed if the central vertex dist from the straight line composed by the two edges less than a 1/1000 of the sum of the edges length. Larger values enforce that only vertices very close to the line are removed.",
        default=0.01,
    )
    unifyvertices: BoolProperty(
        name="UnifyVertices",
        description="if true the snap vertices are weld together.",
        default=True,
    )
