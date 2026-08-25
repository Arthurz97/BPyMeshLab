from bpy.types import PropertyGroup
from bpy.props import IntProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_element(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_element"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    sampling: EnumProperty(
        name="Element to sample",
        description="Choose what mesh element has to be used for the subsampling. At most one point sample will be added for each one of the chosen elements.",
        items=[
            ("Vertex", "Vertex", ""),
            ("Edge", "Edge", ""),
            ("Face", "Face", ""),
        ],
        default="Vertex",
    )
    samplenum: IntProperty(
        name="Number of samples",
        description="The desired number of elements that must be chosen. Being a subsampling of the original elements if this number should not be larger than the number of elements of the original mesh.",
        default=0,
        min=0,
    )
