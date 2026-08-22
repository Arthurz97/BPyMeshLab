from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabSmoothProp


class MESHLAB_PG_create_sphere_cap(PropertyGroup, MeshLabSmoothProp, MeshLabFilterBase):
    pymeshlab_filter = "create_sphere_cap"
    requires_selection = False
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]
    angle_parameters = ["angle"]
    prefer_ply_disk = True

    angle: FloatProperty(
        name="Angle (°)",
        description="Angle of the cone subtending the cap. It must be < 180.",
        default=60.0,
        min=0.001,
        max=179.99,
        precision=1,
        step=10,
    )
    subdiv: IntProperty(
        name="Subdiv. Level",
        description="Number of the recursive subdivision of the surface. Default is 3 (a sphere approximation composed by 1280 faces). Admitted values are in the range 0 (an icosahedron) to 8 (a 1.3 MegaTris approximation of a sphere)",
        default=3,
        min=0,
        max=8,
    )
