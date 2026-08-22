from bpy.types import PropertyGroup
from bpy.props import FloatProperty, StringProperty
from ..base_filter import MeshLabFilterBase, MeshLabSmoothProp


class MESHLAB_PG_create_implicit_surface(
    PropertyGroup, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "create_implicit_surface"
    requires_selection = False
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    voxelsize: FloatProperty(
        name="Size of Voxel",
        description="Size of the voxel that is used by for the grid where the field is sampled. Smaller this value, higher precision, but higher processing times.",
        default=0.05,
        min=0.001,
    )
    minx: FloatProperty(
        name="Min X",
        description="Range where the field is sampled",
        default=-1.0,
    )
    miny: FloatProperty(
        name="Min Y",
        description="Range where the field is sampled",
        default=-1.0,
    )
    minz: FloatProperty(
        name="Min Z",
        description="Range where the field is sampled",
        default=-1.0,
    )
    maxx: FloatProperty(
        name="Max X",
        description="Range where the field is sampled",
        default=1.0,
    )
    maxy: FloatProperty(
        name="Max Y",
        description="Range where the field is sampled",
        default=1.0,
    )
    maxz: FloatProperty(
        name="Max Z",
        description="Range where the field is sampled",
        default=1.0,
    )
    expr: StringProperty(
        name="Function =",
        description="This expression is evaluated for each voxel of the grid. The surface passing through the zero valued points of this field is then extracted using marching cube.",
        default="x*x+y*y+z*z-0.5",
    )
