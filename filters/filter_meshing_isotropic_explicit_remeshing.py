from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_isotropic_explicit_remeshing(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_isotropic_explicit_remeshing"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["quality", "texture_u", "texture_v", "sharp_face", "Col"]
    prefer_ply_disk = True
    percentage_parameters = ["targetlen", "maxsurfdist"]
    angle_parameters = ["featuredeg"]

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        if hasattr(super(), "is_property_disabled") and super().is_property_disabled(
            key, context
        ):
            return True
        if key == "selectedonly":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        return False

    iterations: IntProperty(
        name="Iterations",
        description="Number of iterations of the remeshing operations to repeat on the mesh.",
        default=10,
        min=0,
    )
    adaptive: BoolProperty(
        name="Adaptive remeshing",
        description="Toggles adaptive isotropic remeshing.",
        default=False,
    )
    selectedonly: BoolProperty(
        name="Remesh only selected faces",
        description="If checked the remeshing operations will be applied only to the selected faces.",
        default=False,
    )
    targetlen: FloatProperty(
        name="Target Length",
        description="Sets the absolute target length for the remeshed mesh edges.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.1,
        min=0.0001,
        soft_min=0.01,
    )
    featuredeg: FloatProperty(
        name="Crease Angle (°)",
        description="Minimum angle between faces of the original to consider the shared edge as a feature to be preserved.",
        default=30.0,
        min=0.0,
        max=180.0,
        precision=1,
        step=10,
    )
    checksurfdist: BoolProperty(
        name="Check Surface Distance",
        description="If toggled each local operation must deviate from original mesh by [Max. surface distance].",
        default=False,
    )
    maxsurfdist: FloatProperty(
        name="Max. Surface Distance",
        description="Maximal absolute surface deviation allowed for each local operation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    splitflag: BoolProperty(
        name="Refine Step",
        description="If checked the remeshing operations will include a refine step.",
        default=True,
    )
    collapseflag: BoolProperty(
        name="Collapse Step",
        description="If checked the remeshing operations will include a collapse step.",
        default=True,
    )
    swapflag: BoolProperty(
        name="Edge-Swap Step",
        description="If checked the remeshing operations will include a edge-swap step, aimed at improving the vertex valence of the resulting mesh.",
        default=True,
    )
    smoothflag: BoolProperty(
        name="Smooth Step",
        description="If checked the remeshing operations will include a smoothing step, aimed at relaxing the vertex positions in a Laplacian sense.",
        default=True,
    )
    reprojectflag: BoolProperty(
        name="Reproject Step",
        description="If checked the remeshing operations will include a step to reproject the mesh vertices on the original surface.",
        default=True,
    )
