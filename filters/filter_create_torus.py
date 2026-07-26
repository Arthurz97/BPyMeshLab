import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


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
