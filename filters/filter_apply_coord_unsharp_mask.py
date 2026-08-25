from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    # Dinamiza as flags da Classe Mestra em tempo real ao clicar no checkbox
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_unsharp_mask(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_unsharp_mask"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Estados iniciais sincronizados com o default=True do checkbox blender_polygonal
    requires_polygons_disk = True
    prefer_ply_disk = False

    # Controles de Arquitetura
    batch_support = True

    def is_property_disabled(self, key, context):
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

    weight: FloatProperty(
        name="Unsharp Weight",
        description="the unsharp weight wu in the unsharp mask equation: \nwoorig + wu (orig - lowpass)",
        default=0.3,
    )
    weightorig: FloatProperty(
        name="Original Weight",
        description="How much the original signal is used, e.g. the weight wo in the above unsharp mask equation\nUsually you should not need to change the default 1.0 value.",
        default=1.0,
    )
    iterations: IntProperty(
        name="Smooth Iterations",
        description="number of iterations of laplacian smooth in every run.",
        default=5,
        min=0,
    )
