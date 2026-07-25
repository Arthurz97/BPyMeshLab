import bpy
import math
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase

# ==============================================================================
# Arquivo criado baseado no nome das classes da api do PyMeshLab.
# ==============================================================================


class MESHLAB_PG_create_cube(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_cube"
    requires_selection = False
    shade_flat = True
    remove_attributes = [
        "material_index",
        "sharp_face",
        "UVMap",
        "custom_normal",
        "sharp_edge",
    ]

    size: FloatProperty(
        name="Size",
        description="Scales the new mesh.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.001,
        max=5000.0,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )


class MESHLAB_PG_create_sphere(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_sphere"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    radius: FloatProperty(
        name="Radius",
        description="Create a Sphere, whose topology is obtained as regular subdivision of an icosahedron.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.001,
    )
    subdiv: IntProperty(
        name="Subdiv. Level",
        description="Number of the recursive subdivision of the surface. Default is 3 (a sphere approximation composed by 1280 faces). Admitted values are in the range 0 (an icosahedron) to 8 (a 1.3 MegaTris approximation of a sphere)",
        default=3,
        min=0,
        max=8,
    )


class MESHLAB_PG_create_sphere_cap(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_sphere_cap"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]
    angle_parameters = ["angle"]

    angle: FloatProperty(
        name="Angle (°)",
        description="Angle of the cone subtending the cap. It must be < 180.",
        default=60.0,
        min=0.001,
        max=179.99,
        precision=1,
        step=10,
    )
    subdiv: IntProperty(
        name="Subdiv. Level",
        description="Number of the recursive subdivision of the surface. Default is 3 (a sphere approximation composed by 1280 faces). Admitted values are in the range 0 (an icosahedron) to 8 (a 1.3 MegaTris approximation of a sphere)",
        default=3,
        min=0,
        max=8,
    )


class MESHLAB_PG_create_torus(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_torus"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    hradius: FloatProperty(
        name="Horizontal Radius",
        description="Radius of the whole horizontal ring of the torus",
        subtype="DISTANCE",
        unit="LENGTH",
        default=3.0,
        min=0.001,
    )
    vradius: FloatProperty(
        name="Vertical Radius",
        description="Radius of the vertical section of the ring",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.001,
    )
    hsubdiv: IntProperty(
        name="Horizontal Subdivision",
        description="Subdivision step of the ring",
        default=24,
        min=3,
    )
    vsubdiv: IntProperty(
        name="Vertical Subdivision",
        description="Number of sides of the polygonal approximation of the torus section",
        default=12,
        min=3,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )


class MESHLAB_PG_create_annulus(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_annulus"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]

    internalradius: FloatProperty(
        name="Internal Radius",
        description="Internal Radius of the annulus",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.5,
        min=0.001,
    )
    externalradius: FloatProperty(
        name="External Radius",
        description="Externale Radius of the annulus",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.001,
    )
    sides: IntProperty(
        name="Sides",
        description="Number of the sides of the poligonal approximation of the annulus",
        default=32,
        min=3,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )


class MESHLAB_PG_create_cone(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_cone"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    r0: FloatProperty(
        name="Radius 1",
        description="Radius of the bottom circumference",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.0,
    )
    r1: FloatProperty(
        name="Radius 2",
        description="Radius of the top circumference",
        subtype="DISTANCE",
        unit="LENGTH",
        default=2.0,
        min=0.0,
    )
    h: FloatProperty(
        name="Height",
        description="Height of the Cone",
        subtype="DISTANCE",
        unit="LENGTH",
        default=3.0,
        min=0.001,
    )
    subdiv: IntProperty(
        name="Side",
        description="Number of sides of the polygonal approximation of the cone",
        default=36,
        min=3,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )


# ==============================================================================
# Sólidos Platônicos (Sem parâmetros adicionais definidos via API)
# ==============================================================================
class MESHLAB_PG_create_dodecahedron(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_dodecahedron"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]

    blender_ngon: BoolProperty(
        name="Ngons",
        description="Reconstructs planar faces (ngons) using a Decimate Planar modifier.",
        default=True,
    )


class MESHLAB_PG_create_dodecahedron_sym(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_dodecahedron_sym"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]


class MESHLAB_PG_create_icosahedron(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_icosahedron"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]


class MESHLAB_PG_create_octahedron(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_octahedron"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]


class MESHLAB_PG_create_tetrahedron(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_tetrahedron"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]


class MESHLAB_PG_create_grid(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_grid"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]

    numvertx: IntProperty(
        name="Num Vertices on X",
        description="Number of vertices on x. it must be positive.",
        default=10,
        min=2,
    )
    numverty: IntProperty(
        name="Num Vertices on Y",
        description="Number of vertices on y. it must be positive.",
        default=10,
        min=2,
    )
    absscalex: FloatProperty(
        name="X Scale",
        description="Absolute scale on x (float).",
        default=0.3,
        min=0.001,
    )
    absscaley: FloatProperty(
        name="Y Scale",
        description="Absolute scale on y (float).",
        default=0.3,
        min=0.001,
    )
    center: BoolProperty(
        name="Centered on Origin",
        description="Center grid generated by filter on origin. Grid is first generated and than moved into origin (using muparser lib to perform fast calc on every vertex).",
        default=False,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )


class MESHLAB_PG_create_noisy_isosurface(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_noisy_isosurface"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]

    resolution: IntProperty(
        name="Grid Resolution",
        description="Resolution of the side of the cubic grid used for the volume creation.",
        default=64,
        min=2,
    )


class MESHLAB_PG_create_fractal_terrain(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_fractal_terrain"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]
    custom_name = "FractalTerrain"

    @classmethod
    def pre_process_parameters(cls, params, props):
        params["algorithm"] = int(props.algorithm)

    steps: IntProperty(
        name="Subdivision steps",
        description="Defines the detail of the generated terrain. Allowed values are in range [2,9]. Use values from 6 to 9 to obtain reasonable results.",
        default=8,
        min=2,
        max=9,
    )
    maxheight: FloatProperty(
        name="Max height",
        description="Defines the maximum perturbation height as a fraction of the terrain's side.",
        default=0.2,
        min=0.0,
        max=1.0,
    )
    scale: FloatProperty(
        name="Scale factor",
        description="Scales the fractal perturbation in and out. Values larger than 1 mean zoom out; values smaller than one mean zoom in.",
        default=1.0,
        min=0.0,
        max=10.0,
    )
    seed: IntProperty(
        name="Seed",
        description="By varying this seed, the terrain morphology will change.",
        default=2,
    )
    algorithm: bpy.props.EnumProperty(
        name="Algorithm",
        description="Fractal perturbation algorithms.",
        items=[
            ("0", "fBM (fractal Brownian Motion)", ""),
            ("1", "Standard multifractal", ""),
            ("2", "Heterogeneous multifractal", ""),
            ("3", "Hybrid multifractal", ""),
            ("4", "Ridged multifractal", ""),
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
        description="The gap between noise frequencies. Used in conjunction with fractal increment to compute spectral weights.",
        default=4.0,
    )
    fractalincrement: FloatProperty(
        name="Fractal increment",
        description="Defines how rough the generated terrain will be. Reasonable values in range [0.2, 1.5].",
        default=0.5,
    )
    offset: FloatProperty(
        name="Offset",
        description="Controls the multifractality. If offset is low, then the terrain will be smooth.",
        default=0.9,
    )
    gain: FloatProperty(
        name="Gain",
        description="Ignored in all the algorithms except the ridged one. Defines how hard the terrain will be.",
        default=2.5,
    )
    saveasquality: BoolProperty(
        name="Save as vertex quality",
        description="Saves the perturbation value as a generic FLOAT attribute on vertices (can be accessed via Geometry/Shader nodes).",
        default=False,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )
