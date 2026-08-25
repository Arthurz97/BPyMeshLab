from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_apply_coord_cubic_stylization(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_cubic_stylization"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    prefer_ply_disk = True

    # Controles de Arquitetura
    batch_support = True

    # --- PARÂMETROS DA INTERFACE ---
    lcubeness: FloatProperty(
        name="Cubeness parameter (λ)",
        description="Control the cubeness of the mesh. Generally, the higher the cubeness parameter, the more cubic the mesh is. λ ∈ [0, 1]",
        default=0.2,
        min=0.0,
        max=1.0,
    )
    applyef: BoolProperty(
        name="Apply edge flipping",
        description="Apply edge flip optimization on cubic stylization.",
        default=False,
    )
    applycol: BoolProperty(
        name="Colorize by vertex Quality",
        description="Color vertices depending on their cubization energy.",
        default=False,
    )
