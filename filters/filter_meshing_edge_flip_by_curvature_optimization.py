from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_edge_flip_by_curvature_optimization(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_edge_flip_by_curvature_optimization"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    # Inclusão da propriedade na lista de ângulos para tratamento matemático da classe base
    angle_parameters = ["pthreshold"]

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Mapeia a propriedade 'selectedonly' (da nossa interface) para 'selection' (do PyMeshLab)
        if "selectedonly" in params:
            params["selection"] = params.pop("selectedonly")

        # Converte a seleção da interface (String) para Inteiro
        params["curvtype"] = int(props.curvtype)

    # --- PARÂMETROS DA INTERFACE ---

    selectedonly: BoolProperty(
        name="Update selection",
        description="Apply edge flip optimization on selected faces only.",
        default=False,
    )
    pthreshold: FloatProperty(
        name="Angle Thr (deg) (°)",
        description="To avoid excessive flipping/swapping we consider only couple of faces with a significant diedral angle (e.g. greater than the indicated threshold).",
        default=1.0,
        min=0.0,
        max=180.0,
        precision=1,
        step=10,
    )
    curvtype: EnumProperty(
        name="Curvature metric",
        description="Choose a metric to compute surface curvature on vertices\nH = mean curv, K = gaussian curv, A = area per vertex\n\n1: Mean curvature = H\n2: Norm squared mean curvature = (H * H) / A\n3: Absolute curvature:\nif(K >= 0) return 2 * H\nelse return 2 * sqrt(H ^ 2 - A * K)",
        items=[
            ("0", "mean", ""),
            ("1", "norm squared", ""),
            ("2", "absolute", ""),
        ],
        default="0",
    )
