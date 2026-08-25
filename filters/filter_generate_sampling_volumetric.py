from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_volumetric(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_volumetric"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["samplesurfradius", "poissonradius"]

    # Feature Flag: Avisa a Classe Mestra para extrair todas as camadas geradas (Montecarlo, Poisson e Surface)
    extract_multiple_layers = True
    layer_mapping = {1: "Montecarlo", 2: "Poisson", 3: "Surface"}

    batch_support = True
    global_mode = "BOOLEAN"

    # PARÂMETROS DO FILTRO VOLUMETRIC SAMPLING
    samplesurfradius: FloatProperty(
        name="Surface Sampling Radius",
        description="Surface Sampling is used only as an optimization.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.003464,
        min=0.0,
    )
    samplevolnum: IntProperty(
        name="Volume Sample Num.",
        description="Number of volumetric samples scattered inside the mesh and used for choosing the voronoi seeds and performing the Lloyd relaxation for having a centroidal voronoi diagram.",
        default=200000,
        min=0,
    )
    poissonfiltering: BoolProperty(
        name="Poisson Filtering",
        description="If true the base montecarlo sampling of the volume is filtered to get a poisson disk volumetric distribution.",
        default=True,
    )
    poissonradius: FloatProperty(
        name="Poisson Radius",
        description="Number of voxel per side in the volumetric representation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.017321,
        min=0.0,
    )
