import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_plane_fitting_to_selection(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_plane_fitting_to_selection"
    requires_selection = True
    ignore_selection_count = True
    ignores_modifiers = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    custom_name = "FittedPlane"

    batch_support = True
    global_mode = "JOIN"

    @classmethod
    def pre_process_parameters(cls, params, props):
        params["orientation"] = int(props.orientation)
        if "selectedonly" in params:
            del params["selectedonly"]

        # Lógica Condicional RAM vs DISCO para Quad/Tri
        engine = bpy.context.scene.meshlab_prefs.processing_engine
        if engine == "DISK":
            # No Disco, o PyMeshLab quebra em Tris. Reconstruímos os Quads se o usuário pedir.
            cls.post_filter_on_true = "meshing_tri_to_quad_dominant"
            cls.post_filter_on_false = None
        else:
            # Na Memória, já nasce em Quads. Quebramos em Tris se a opção for desmarcada.
            cls.post_filter_on_true = None
            cls.post_filter_on_false = "meshing_poly_to_tri"

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
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
