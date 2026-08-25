from bpy.types import PropertyGroup
from bpy.props import BoolProperty, IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_remove_connected_component_by_face_number(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_remove_connected_component_by_face_number"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    mincomponentsize: IntProperty(
        name="Enter minimum conn. comp size:",
        description="Delete all the connected components (floating pieces) composed by a number of triangles smaller than the specified one.",
        default=25,
        min=0,
    )
    removeunref: BoolProperty(
        name="Remove unfreferenced vertices",
        description="if true, the unreferenced vertices remaining after the face deletion are removed.",
        default=True,
    )
