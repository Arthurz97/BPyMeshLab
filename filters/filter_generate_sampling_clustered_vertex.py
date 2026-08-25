from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_clustered_vertex(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_clustered_vertex"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["threshold"]

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        if key == "selectedonly":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Swap da chave de seleção para a exigência do PyMeshLab
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

    threshold: FloatProperty(
        name="Cell Size",
        description="The size of the cell of the clustering grid. Smaller the cell finer the resulting mesh. For obtaining a very coarse mesh use larger values.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    sampling: EnumProperty(
        name="Representative Strategy",
        description="Average: for each cell we take the average of the sample falling into. The resulting point is a new point.\nClosest to center: for each cell we take the sample that is closest to the center of the cell. Chosen vertices are a subset of the original ones.",
        items=[
            ("Average", "Average", ""),
            ("Closest to center", "Closest to center", ""),
        ],
        default="Closest to center",
    )
    selectedonly: BoolProperty(
        name="Only on Selection",
        description="If true only for the filter is applied only on the selected subset of the mesh.",
        default=False,
    )
