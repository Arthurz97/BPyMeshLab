from bpy.types import PropertyGroup
from bpy.props import BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_decimation_edge_collapse_for_marching_cubes_meshes(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_decimation_edge_collapse_for_marching_cube_meshes"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"
