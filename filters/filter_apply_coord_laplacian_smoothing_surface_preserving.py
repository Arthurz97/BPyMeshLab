from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    # Dinamiza as flags da Classe Mestra em tempo real ao clicar no checkbox
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_laplacian_smoothing_surface_preserving(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_laplacian_smoothing_surface_preserving"
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
        if key == "selectedonly":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        if key == "blender_polygonal":
            return False

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Swap da chave de seleção do Blender para a exigência do PyMeshLab neste filtro ('selection')
        if "selectedonly" in params:
            params["selection"] = params.pop("selectedonly")

    # --- PARÂMETROS DA INTERFACE ---
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    selectedonly: BoolProperty(
        name="Update selection",
        description="Apply laplacian smooth on selected faces only.",
        default=False,
    )
    angledeg: FloatProperty(
        name="Max Normal Dev (deg)",
        description="Maximum mean normal angle displacement (degrees) from old to new faces.",
        default=0.5,
        min=0.0,
    )
    iterations: IntProperty(
        name="Iterations",
        description="Number of laplacian smooth iterations in every run.",
        default=1,
        min=0,
    )
