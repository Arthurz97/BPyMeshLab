from bpy.types import PropertyGroup
from bpy.props import FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_sampling_regular_recursive(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_sampling_regular_recursive"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["cellsize", "offset"]

    batch_support = True
    global_mode = "BOOLEAN"

    cellsize: FloatProperty(
        name="Precision",
        description="Size of the cell, the default is 1/50 of the box diag. Smaller cells give better precision at a higher computational cost. Remember that halving the cell size means that you build a volume 8 times larger.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.034641,
        min=0.0,
    )
    offset: FloatProperty(
        name="Offset",
        description="Offset of the created surface (i.e. distance of the created surface from the original one).\nIf offset is zero, the created surface passes on the original mesh itself. Values greater than zero mean an external surface, and lower than zero mean an internal surface.\nIn practice this value is the threshold passed to the Marching Cube algorithm to extract the isosurface from the distance field representation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0,
    )
