from bpy.types import PropertyGroup
from bpy.props import IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_meshing_surface_subdivision_catmull_clark(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_surface_subdivision_catmull_clark"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    batch_support = True
    global_mode = "NONE"

    iterations: IntProperty(
        name="Iterations",
        description="Number of times the model is subdivided.",
        default=2,
        min=0,
    )
