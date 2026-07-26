import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


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
