from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_voronoi(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_voronoi"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    # Feature Flag: Avisa a Classe Mestra para extrair a malha original processada + as 2 camadas extras (Mesh e Polyline)
    extract_multiple_layers = True
    layer_mapping = {1: "Voronoi_Mesh", 2: "Voronoi_Polyline"}

    batch_support = True
    global_mode = "BOOLEAN"

    @classmethod
    def pre_process_parameters(cls, params, props):
        # O PyMeshLab recebe as opções de ENUM como Inteiros neste filtro
        params["colorstrategy"] = int(props.colorstrategy)
        params["distancetype"] = int(props.distancetype)
        params["relaxtype"] = int(props.relaxtype)

    def is_property_disabled(self, key, context):
        # Cascata de Esmaecimento: Desativa os parâmetros dependentes se o Preprocessing estiver desligado
        if key in ["refinefactor", "perturbprobability", "perturbamount"]:
            return not getattr(self, "preprocessflag", False)

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    # PARÂMETROS DO FILTRO VORONOI SAMPLING
    iternum: IntProperty(
        name="Iteration",
        description="Number of iterations.",
        default=10,
        min=0,
    )
    samplenum: IntProperty(
        name="Sample Num.",
        description="Number of samples.",
        default=10,
        min=1,
    )
    radiusvariance: FloatProperty(
        name="Radius Variance",
        description="The distance metric will vary along the surface between 1/x and x, linearly according to the scalar field specified by the quality.",
        default=1.0,
        min=0.0,
    )
    colorstrategy: EnumProperty(
        name="Color Strategy",
        description="Select the coloring strategy for the samples.",
        items=[
            ("0", "None", ""),
            ("1", "Seed Distance", ""),
            ("2", "Border Distance", ""),
            ("3", "Region Area", ""),
        ],
        default="1",
    )
    distancetype: EnumProperty(
        name="Distance Type",
        description="Select the distance type.",
        items=[
            ("0", "Euclidean", ""),
            ("1", "Quality Weighted", ""),
            ("2", "Anisotropic", ""),
        ],
        default="0",
    )
    preprocessflag: BoolProperty(
        name="Preprocessing",
        description="Enable/Disable preprocessing.",
        default=False,
    )
    refinefactor: IntProperty(
        name="Refinement Factor",
        description="To ensure good convergence the mesh should be more complex than the voronoi partitioning. This number affect how much the mesh is refined according to the required number of samples.",
        default=10,
        min=1,
    )
    perturbprobability: FloatProperty(
        name="Perturbation Probability",
        description="To ensure good convergence the mesh should be more complex than the voronoi partitioning. This number affect how much the mesh is refined according to the required number of samples.",
        default=0.0,
        min=0.0,
        max=1.0,
    )
    perturbamount: FloatProperty(
        name="Perturbation Amount",
        description="To ensure good convergence the mesh should be more complex than the voronoi partitioning. This number affect how much the mesh is refined according to the required number of samples.",
        default=0.001,
        min=0.0,
    )
    randomseed: IntProperty(
        name="Random seed",
        description="To ensure repeatability you can specify the random seed used. If 0 the random seed is tied to the current clock.",
        default=0,
        min=0,
    )
    relaxtype: EnumProperty(
        name="Relax Type",
        description="At each relaxation step we search for each voronoi region the new position of the seed.",
        items=[
            (
                "0",
                "Geodesic",
                "The seed is placed onto the vertex that maximize the geodesic distance from the border of the region.",
            ),
            (
                "1",
                "Squared Distance",
                "The seed is placed in the vertex that minimize the squared sum of the distances from all the pints of the region.",
            ),
            (
                "2",
                "Restricted",
                "The seed is placed in the barycenter of current voronoi region. Even if it is outside the surface. During the relaxation process the seed is free to move off the surface in a continuous way. Re-association to vertex is done at the end.",
            ),
        ],
        default="1",
    )
