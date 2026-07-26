import bpy
from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_noisy_isosurface(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_noisy_isosurface"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]

    resolution: IntProperty(
        name="Grid Resolution",
        description="Resolution of the side of the cubic grid used for the volume creation.",
        default=64,
        min=2,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
