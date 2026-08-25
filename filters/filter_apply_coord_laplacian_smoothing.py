from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_laplacian_smoothing(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_laplacian_smoothing"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

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
        # Swap da chave de seleção para a exigência do PyMeshLab
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

    # --- PARÂMETROS DA INTERFACE ---
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    stepsmoothnum: IntProperty(
        name="Smoothing steps",
        description="The number of times that the whole algorithm (normal smoothing + vertex fitting) is iterated.",
        default=3,
        min=0,
    )
    boundary: BoolProperty(
        name="1D Boundary Smoothing",
        description="Smooth boundary edges only by themselves (e.g. the polyline forming the boundary of the mesh is independently smoothed). This can reduce the shrinking on the border but can have strange effects on very small boundaries.",
        default=True,
    )
    cotangentweight: BoolProperty(
        name="Cotangent weighting",
        description="Use cotangent weighting scheme for the averaging of the position. Otherwise the simpler umbrella scheme (1 if the edge is present) is used.",
        default=True,
    )
    selectedonly: BoolProperty(
        name="Affect only selection",
        description="If checked the filter is performed only on the selected area.",
        default=False,
    )
