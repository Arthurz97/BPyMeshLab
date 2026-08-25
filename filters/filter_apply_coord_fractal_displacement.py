from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    # Dinamiza as flags da Classe Mestra em tempo real ao clicar no checkbox
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_fractal_displacement(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_fractal_displacement"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    percentage_parameters = ["maxheight"]

    batch_support = True
    global_mode = "NONE"

    # Estados iniciais sincronizados com o default=True do checkbox blender_polygonal
    requires_polygons_disk = True
    prefer_ply_disk = False

    def is_property_disabled(self, key, context):
        if key == "blender_polygonal":
            return False

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Converte o Enum da interface do Blender para o Int exigido pelo C++
        params["algorithm"] = int(props.algorithm)

    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    maxheight: FloatProperty(
        name="Max height (abs and %)",
        description="Defines the maximum height for the perturbation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0346,
        min=0.0,
    )
    scale: FloatProperty(
        name="Scale factor",
        description="Scales the fractal perturbation in and out. Values larger than 1 mean zoom out; values smaller than one mean zoom in.",
        default=1.0,
        min=0.0,
        max=10.0,
    )
    smoothingsteps: IntProperty(
        name="Normals smoothing steps",
        description="Face normals will be smoothed to make the perturbation more homogeneous. This parameter represents the number of smoothing steps.",
        default=5,
        min=0,
    )
    seed: IntProperty(
        name="Seed",
        description="By varying this seed, the terrain morphology will change. Don't change the seed if you want to refine the current terrain morphology by changing the other parameters.",
        default=2,
    )
    algorithm: EnumProperty(
        name="Algorithm",
        description="The algorithm with which the fractal terrain will be generated.",
        items=[
            ("0", "fBM (fractal Brownian Motion)", ""),
            ("1", "Standard multifractal", ""),
            ("2", "Heterogeneous multifractal", ""),
            ("3", "Hybrid multifractal terrain", ""),
            ("4", "Ridged multifractal terrain", ""),
        ],
        default="4",
    )
    octaves: FloatProperty(
        name="Octaves",
        description="The number of Perlin noise frequencies that will be used to generate the terrain. Reasonable values are in range [2,9].",
        default=8.0,
        min=1.0,
        max=20.0,
    )
    lacunarity: FloatProperty(
        name="Lacunarity",
        description="The gap between noise frequencies. This parameter is used in conjunction with fractal increment to compute the spectral weights that contribute to the noise in each octave.",
        default=4.0,
    )
    fractalincrement: FloatProperty(
        name="Fractal increment",
        description="This parameter defines how rough the generated terrain will be. The range of reasonable values changes according to the used algorithm, however you can choose it in range [0.2, 1.5].",
        default=0.2,
    )
    offset: FloatProperty(
        name="Offset",
        description="This parameter controls the multifractality of the generated terrain. If offset is low, then the terrain will be smooth.",
        default=0.9,
    )
    gain: FloatProperty(
        name="Gain",
        description="Ignored in all the algorithms except the ridged one. This parameter defines how hard the terrain will be.",
        default=2.5,
    )
    saveasquality: BoolProperty(
        name="Save as vertex quality",
        description="Saves the perturbation value as vertex quality (accessible via Geometry/Shader nodes).",
        default=False,
    )
