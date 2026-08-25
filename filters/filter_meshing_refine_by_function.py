from bpy.types import PropertyGroup
from bpy.props import StringProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_refine_by_function(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_refine_by_function"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    condselect: StringProperty(
        name="boolean function",
        default="(q0 >= 0 && q1 >= 0)",
        description="type a boolean function that will be evaluated on every edge.",
    )
    x: StringProperty(
        name="x =",
        default="(x0+x1)/2",
        description="function to generate x coord of new vertex in [x0,x1].\nFor example (x0+x1)/2",
    )
    y: StringProperty(
        name="y =",
        default="(y0+y1)/2",
        description="function to generate x coord of new vertex in [y0,y1].\nFor example (y0+y1)/2",
    )
    z: StringProperty(
        name="z =",
        default="(z0+z1)/2",
        description="function to generate x coord of new vertex in [z0,z1].\nFor example (z0+z1)/2",
    )
