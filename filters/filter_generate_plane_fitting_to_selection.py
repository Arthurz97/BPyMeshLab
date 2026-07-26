import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, IntProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_plane_fitting_to_selection(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_plane_fitting_to_selection"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    custom_name = "FittedPlane"

    @classmethod
    def pre_process_parameters(cls, params, props):
        params["orientation"] = int(props.orientation)
        if "selectedonly" in params:
            del params["selectedonly"]

    selectedonly: BoolProperty(
        default=True,
        options={"HIDDEN"},
    )
    extent: FloatProperty(
        name="Extent (w.r.t selection)",
        description="How large is the plane, with respect to the size of the selection: 1.0 means as large as the selection, 1.1 means 10% larger then the selection.",
        default=1.0,
        min=0.001,
    )
    subdiv: IntProperty(
        name="Plane XY subdivisions",
        description="Subdivision steps of plane borders.",
        default=3,
        min=0,
    )
    hasuv: BoolProperty(
        name="UV parametrized",
        description="The created plane has an UV parametrization.",
        default=False,
    )
    orientation: bpy.props.EnumProperty(
        name="Plane orientation",
        description="Orientation of the fitting plane.",
        items=[
            (
                "0",
                "quasi-Straight Fit",
                "The fitting plane will be oriented (as much as possible) straight with the axeses.",
            ),
            (
                "1",
                "Best Fit",
                "The fitting plane will be oriented and sized trying to best fit to the selected area.",
            ),
            (
                "2",
                "XZ Parallel",
                "The fitting plane will be oriented with a side parallel with the chosen plane. WARNING: do not use if the selection is exactly parallel to a plane.",
            ),
            ("3", "YZ Parallel", "Parallel to YZ."),
            ("4", "YX Parallel", "Parallel to YX."),
        ],
        default="0",
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Convert tris to quads.",
        default=True,
    )
