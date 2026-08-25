from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_montecarlo(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_montecarlo"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    samplenum: IntProperty(
        name="Number of samples",
        description="The desired number of samples. It can be smaller or larger than the mesh size, and according to the chosen sampling strategy it will try to adapt.",
        default=8,
        min=0,
    )
    weighted: BoolProperty(
        name="Quality Weighted Sampling",
        description="Use per vertex quality to drive the vertex sampling. The number of samples falling in each face is proportional to the face area multiplied by the average quality of the face vertices.",
        default=False,
    )
    perfacenormal: BoolProperty(
        name="Per-Face Normal",
        description="If true for each sample we take the normal of the sampled face, otherwise the normal interpolated from the vertex normals.",
        default=False,
    )
    radiusvariance: FloatProperty(
        name="Radius Variance",
        description="The radius of the disk is allowed to vary between r/var and r*var. If this parameter is 1 the sampling is the same of the Poisson Disk Sampling.",
        default=1.0,
    )
    exactnum: BoolProperty(
        name="Exact Sample Number",
        description="If the required total number of samples is not a strict exact requirement we can exploit a different algorithmbased on the choice of the number of samples inside each triangle by a random Poisson-distributed number with mean equal to the expected number of samples times the area of the triangle over the surface of the whole mesh.",
        default=True,
    )
    edgesampling: BoolProperty(
        name="Sample CreaseEdge Only",
        description="Restrict the sampling process to the crease edges only. Useful to sample in a more accurate way the feature edges of a mechanical mesh.",
        default=False,
    )
