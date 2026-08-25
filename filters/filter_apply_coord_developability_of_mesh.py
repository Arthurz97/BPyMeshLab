import math
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_developability_of_mesh(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_developability_of_mesh"

    # Controles de Arquitetura
    batch_support = True
    global_mode = "NONE"

    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    requires_polygons_disk = True
    prefer_ply_disk = False

    angle_parameters = ["anglethreshold"]

    def is_property_disabled(self, key, context):
        if key in ["minstepsize", "tau", "m1"]:
            return self.optmethod == "[F] Fixed stepsize"
        if key == "blender_polygonal":
            return False

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    # --- PARÂMETROS DA INTERFACE ---
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )
    optmethod: EnumProperty(
        name="Gradient method",
        description="The gradient method optimization algorithm to use.",
        items=[
            ("[B] Backtracking line search", "[B] Backtracking line search", ""),
            ("[F] Fixed stepsize", "[F] Fixed stepsize", ""),
        ],
        default="[B] Backtracking line search",
    )
    maxfunevals: IntProperty(
        name="Max function evaluations",
        description="The maximum number of function evaluation. Once reached, the optimization stops.",
        default=400,
        min=1,
    )
    eps: FloatProperty(
        name="Stop threshold",
        description="Optimization stops when the squared norm of the gradient is less than or equal to the accuracy.",
        default=1e-05,
        precision=5,
    )
    stepsize: FloatProperty(
        name="Initial step size",
        description="The initial step size of the opt method, fixed when using [F] optimizer.",
        default=0.01,
        precision=4,
    )
    minstepsize: FloatProperty(
        name="Min step size (B only)",
        description="The minimum step size for the backtracking line search opt method.",
        default=1e-10,
        precision=8,
    )
    tau: FloatProperty(
        name="Tau (B only)",
        description="Scaling factor of the step size for the backtracking line search opt method.",
        default=0.8,
        precision=3,
    )
    m1: FloatProperty(
        name="Armijo constant (B only)",
        description="The constant of the Armijo condition of the backtracking line search opt method.",
        default=0.0001,
        precision=4,
    )
    edgeflips: BoolProperty(
        name="Apply edge flips",
        description="Whether or not to apply edge flips when necessary during optimization.",
        default=True,
    )
    edgecollapses: BoolProperty(
        name="Apply edge collapses",
        description="Whether or not to apply edge collapses when necessary during optimization.",
        default=True,
    )
    # Subtype 'ANGLE' habilita a interface nativa do Blender (Graus) processando em radianos nos bastidores
    anglethreshold: FloatProperty(
        name="Post-processing angle threshold",
        description="The maximum angle under which an edge flip or an edge collapse must be performed during optimization.",
        default=math.radians(18),
        subtype="ANGLE",
    )
