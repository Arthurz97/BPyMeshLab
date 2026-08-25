from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_remove_connected_component_by_diameter(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_remove_connected_component_by_diameter"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True
    percentage_parameters = ["mincomponentdiag"]

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    mincomponentdiag: FloatProperty(
        name="Enter max diameter of isolated pieces",
        description="Delete all the connected components (floating pieces) with a diameter smaller than the specified one.",
        subtype="PERCENTAGE",
        default=10.0,
        min=0.0,
        max=100.0,
    )
    removeunref: BoolProperty(
        name="Remove unfreferenced vertices",
        description="if true, the unreferenced vertices remaining after the face deletion are removed.",
        default=True,
    )
