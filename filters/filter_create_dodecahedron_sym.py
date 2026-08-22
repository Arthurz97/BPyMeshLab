from bpy.types import PropertyGroup
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_dodecahedron_sym(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_dodecahedron_sym"
    requires_selection = False
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
