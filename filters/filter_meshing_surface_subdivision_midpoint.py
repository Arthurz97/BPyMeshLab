from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_surface_subdivision_midpoint(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_surface_subdivision_midpoint"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    percentage_parameters = ["threshold"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        if key == "selectedonly":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        return super().is_property_disabled(key, context)

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Swap da chave de seleção para a exigência do PyMeshLab (selected)
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

    iterations: IntProperty(
        name="Iterations",
        description="Number of time the model is subdivided.",
        default=3,
        min=0,
    )
    threshold: FloatProperty(
        name="Edge Threshold",
        description="All the edges longer than this threshold will be refined. Setting this value to zero will force an uniform refinement.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.0,
    )
    selectedonly: BoolProperty(
        name="Affect only selected faces",
        description="If selected the filter affect only the selected faces",
        default=False,
    )
