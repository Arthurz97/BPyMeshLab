from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_stratified_triangle(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_stratified_triangle"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    samplenum: IntProperty(
        name="Number of samples",
        description="The desired number of samples. It can be smaller or larger than the mesh size, and according to the chosen sampling strategy it will try to adapt.",
        default=100000,
        min=0,
    )
    sampling: EnumProperty(
        name="Element to sample",
        description="Similar Triangle: each triangle is subdivided into similar triangles and the internal vertices of these triangles are considered. This sampling leave space around edges and vertices for separate sampling of these entities.\nDual Similar Triangle: each triangle is subdivided into similar triangles and the internal vertices of these triangles are considered. \nLong Edge Subdiv each triangle is recursively subdivided along the longest edge. \nSample Edges Only the edges of the mesh are uniformly sampled. \nSample NonFaux Edges Only the non-faux edges of the mesh are uniformly sampled.",
        items=[
            ("Similar Triangle", "Similar Triangle", ""),
            ("Dual Similar Triangle", "Dual Similar Triangle", ""),
            ("Long Edge Subdiv", "Long Edge Subdiv", ""),
            ("Sample Edges", "Sample Edges", ""),
            ("Sample NonFaux Edges", "Sample NonFaux Edges", ""),
        ],
        default="Similar Triangle",
    )
    random: BoolProperty(
        name="Random Sampling",
        description="if true, for each (virtual) face we draw a random point, otherwise we pick the face midpoint.",
        default=False,
    )
