import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_cone(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_cone"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    # Pós-processamento nativo C++
    post_filter_on_true = "meshing_tri_to_quad_dominant"
    post_filter_on_false = None

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
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
