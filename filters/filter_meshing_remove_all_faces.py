from bpy.types import PropertyGroup
from bpy.props import BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_meshing_remove_all_faces(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "meshing_remove_all_faces"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = False
    prefer_ply_disk = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Controles de Arquitetura
    batch_support = True
    global_mode = "BOOLEAN"

    # --- PARÂMETROS DA INTERFACE ---
    alllayers: BoolProperty(
        name="Apply to all visible Layers",
        description="If selected, the filter will be applied to all visible mesh Layers.",
        default=False,
        options={"HIDDEN"},
    )
