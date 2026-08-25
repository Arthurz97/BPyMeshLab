from bpy.types import PropertyGroup
from bpy.props import EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_meshing_repair_non_manifold_edges(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_repair_non_manifold_edges"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    requires_polygons_disk = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    method: EnumProperty(
        name="Method",
        description="Selects whether to remove non manifold edges by removing faces or by splitting vertices.",
        items=[
            ("Remove Faces", "Remove Faces", ""),
            ("Split Vertices", "Split Vertices", ""),
        ],
        default="Remove Faces",
    )
