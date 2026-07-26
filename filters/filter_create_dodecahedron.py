import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_dodecahedron(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_dodecahedron"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]
