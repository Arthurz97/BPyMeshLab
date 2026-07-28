import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_fractal_terrain(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_fractal_terrain"
    requires_selection = False
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]
    custom_name = "FractalTerrain"

    # Pós-processamento nativo C++
    post_filter_on_true = "meshing_tri_to_quad_dominant"
    post_filter_on_false = None

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
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
