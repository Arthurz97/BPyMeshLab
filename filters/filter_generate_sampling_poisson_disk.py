import bpy
import pymeshlab
from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty, PointerProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps
from .. import utils


class MESHLAB_PG_generate_sampling_poisson_disk(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_poisson_disk"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["radius"]

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        # Cascata de esmaecimento baseada nas opções escolhidas
        if key == "refinemesh_object":
            return not self.refineflag
        if key == "bestsamplepool":
            return not self.bestsampleflag
        if key == "exactnumtolerance":
            return not self.exactnumflag

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Removemos o PointerProperty do Blender antes de enviar ao C++
        if "refinemesh_object" in params:
            del params["refinemesh_object"]

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        # Injeção dinâmica da malha secundária em RAM caso a flag seja verdadeira
        if props.refineflag and props.refinemesh_object:
            target_obj = props.refinemesh_object
            vertices, faces, _, v_scalars, v_normals = utils.blender_to_numpy(
                target_obj, extract_selection=False, extract_quality=True
            )
            mesh_kwargs = {"vertex_matrix": vertices, "face_matrix": faces}
            if v_scalars is not None:
                mesh_kwargs["v_scalar_array"] = v_scalars
            if v_normals is not None:
                mesh_kwargs["v_normals_matrix"] = v_normals

            m = pymeshlab.Mesh(**mesh_kwargs)
            ms.add_mesh(m)

            # Como a malha primária está no index 0, injetamos o ID 1 como alvo para o refinamento
            params["refinemesh"] = 1
        else:
            params["refinemesh"] = 0

    samplenum: IntProperty(
        name="Number of samples",
        description="The desired number of samples. The ray of the disk is calculated according to the sampling density.",
        default=1000,
        min=0,
    )
    radius: FloatProperty(
        name="Explicit Radius",
        description="If not zero this parameter override the previous parameter to allow exact radius specification.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0,
        min=0.0,
    )
    montecarlorate: IntProperty(
        name="MonterCarlo OverSampling",
        description="The over-sampling rate that is used to generate the initial Montecarlo samples (e.g. if this parameter is K means thatK x poisson sample points will be used). The generated Poisson-disk samples are a subset of these initial Montecarlo samples. Larger this number slows the process but make it a bit more accurate.",
        default=20,
        min=1,
    )
    savemontecarlo: BoolProperty(
        name="Save Montecarlo",
        description="If true, it will generate an additional Layer with the montecarlo sampling that was pruned to build the poisson distribution.",
        default=False,
    )
    approximategeodesicdistance: BoolProperty(
        name="Approximate Geodesic Distance",
        description="If true Poisson Disc distances are computed using an approximate geodesic distance, e.g. an euclidean distance weighted by a function of the difference between the normals of the two points.",
        default=False,
    )
    subsample: BoolProperty(
        name="Base Mesh Subsampling",
        description="If true the original vertices of the base mesh are used as base set of points. In this case the SampleNum should be obviously much smaller than the original vertex number.\nNote that this option is very useful in the case you want to subsample a dense point cloud.",
        default=False,
    )
    refineflag: BoolProperty(
        name="Refine Existing Samples",
        description="If true the vertices of the below mesh are used as starting vertices, and they will utterly refined by adding more and more points until possible.",
        default=False,
    )
    refinemesh_object: PointerProperty(
        type=bpy.types.Object,
        name="Samples to be refined",
        description="Used only if the above option is checked. Mesh object used as starting vertices.",
    )
    bestsampleflag: BoolProperty(
        name="Best Sample Heuristic",
        description="If true it will use a simple heuristic for choosing the samples. At a small cost (it can slow a bit the process) it usually improve the maximality of the generated sampling.",
        default=True,
    )
    bestsamplepool: IntProperty(
        name="Best Sample Pool Size",
        description="Used only if the Best Sample Flag is true. It control the number of attempt that it makes to get the best sample. It is reasonable that it is smaller than the Montecarlo oversampling factor.",
        default=10,
        min=1,
    )
    exactnumflag: BoolProperty(
        name="Precise sample number",
        description="If requested it will try to do a dicotomic search for the best poisson disk radius that will generate the requested number of samples with the below specified tolerance. Obviously it will takes much longer.",
        default=False,
    )
    exactnumtolerance: FloatProperty(
        name="Precise sample number tolerance",
        description="If a precise number of sample is requested, the sample number will be matched with the precision specified here. Precision is specified as a fraction of the sample number. so for example a precision of 0.005 over 1000 samples means that you can get 995 or 1005 samples.",
        default=0.005,
        min=0.0,
    )
    radiusvariance: FloatProperty(
        name="Radius Variance",
        description="The radius of the disk is allowed to vary between r and r*var. If this parameter is 1 the sampling is the same of the Poisson Disk Sampling.",
        default=1.0,
        min=0.0,
    )
