import bpy
from bpy.types import PropertyGroup
from ..base_filter import MeshLabFilterBase

class MESHLAB_PG_generate_convex_hull(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_convex_hull"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]