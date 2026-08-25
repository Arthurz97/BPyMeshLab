from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_remove_t_vertices(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_remove_t_vertices"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Converte o Enum da interface (string "0" ou "1") para o inteiro esperado no C++
        params["method"] = int(props.method)

    method: EnumProperty(
        name="Method",
        description="Selects whether to remove t-vertices by edge collapse or edge flip.",
        items=[
            ("0", "Edge Collapse", ""),
            ("1", "Edge Flip", ""),
        ],
        default="0",
    )
    threshold: FloatProperty(
        name="Ratio",
        description="Detects faces where the base/height ratio is lower than this value.",
        default=40.0,
        min=0.0,
    )
    repeat: BoolProperty(
        name="Iterate until convergence",
        description="Iterates the algorithm until it reaches convergence.",
        default=True,
    )
