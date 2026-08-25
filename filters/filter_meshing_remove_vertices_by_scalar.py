from bpy.types import PropertyGroup
from bpy.props import FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_remove_vertices_by_scalar(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_remove_vertices_by_scalar"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_ram_memory = True
    percentage_parameters = ["maxqualitythr"]

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    maxqualitythr: FloatProperty(
        name="Delete all vertices with quality under:",
        description="Delete all the vertices with a quality lower smaller than the specified constant.",
        default=0.0,
    )
