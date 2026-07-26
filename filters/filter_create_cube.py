import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


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
