from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_edge_flip_by_planar_optimization(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_edge_flip_by_planar_optimization"
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
        if "selectedonly" in params:
            params["selection"] = params.pop("selectedonly")

        params["planartype"] = int(props.planartype)

    selectedonly: BoolProperty(
        name="Update selection",
        description="Apply edge flip optimization on selected faces only.",
        default=False,
    )

    # Propriedade de ângulo espelhada no padrão de create_sphere_cap
    pthreshold: FloatProperty(
        name="Planar threshold (°)",
        description="Angle threshold for planar faces (degrees).",
        default=1.0,
        min=0.0,
        max=180.0,
        precision=1,
        step=10,
    )
    planartype: EnumProperty(
        name="Planar metric",
        description="Choose a metric to define the planar flip operation.",
        items=[
            ("0", "area/max side", ""),
            ("1", "inradius/circumradius", ""),
            ("2", "mean ratio", ""),
            ("3", "delaunay", ""),
            ("4", "topology", ""),
        ],
        default="0",
    )
    iterations: IntProperty(
        name="Post optimization relax iter",
        description="Number of a planar laplacian smooth iterations that have to be performed after every run.",
        default=1,
        min=0,
    )
