from bpy.types import PropertyGroup
from bpy.props import BoolProperty, IntProperty, FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_close_holes(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_close_holes"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    # Controles de Arquitetura e Matemática
    batch_support = True
    global_mode = "NONE"
    percentage_parameters = ["refineholeedgelen"]

    def is_property_disabled(self, key, context):
        if key == "refineholeedgelen":
            return not getattr(self, "refinehole", False)

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Transforma a propriedade de interface do Blender na chave esperada pela API
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

    @classmethod
    def apply_filter(cls, context, props):
        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]

        # TRAVA FAIL-FAST: Evita o crash nativo do C++ ("Current mesh does not have Any Faces")
        for obj in original_objs:
            if len(obj.data.polygons) == 0:
                return (
                    "CANCELLED",
                    f"Filtro abortado: A malha '{obj.name}' não possui faces (Point Cloud). O filtro Close Holes exige geometria base.",
                )

        return super().apply_filter(context, props)

    maxholesize: IntProperty(
        name="Max size to be closed",
        description="The size is expressed as number of edges composing the hole boundary.",
        default=30,
        min=0,
    )
    selectedonly: BoolProperty(
        name="Close holes with selected faces",
        description="Only the holes with at least one of the boundary faces selected are closed.",
        default=False,
    )
    newfaceselected: BoolProperty(
        name="Select the newly created faces",
        description="After closing a hole the faces that have been created are left selected. Any previous selection is lost. Useful for example for smoothing the newly created holes.",
        default=False,
        options={"HIDDEN"},
    )
    selfintersection: BoolProperty(
        name="Prevent creation of selfIntersecting faces",
        description="When closing an holes it tries to prevent the creation of faces that intersect faces adjacent to the boundary of the hole. It is an heuristic, non intersetcting hole filling can be NP-complete.",
        default=True,
    )
    refinehole: BoolProperty(
        name="Refine Filled Hole",
        description="After closing the hole it will refine the newly created triangles to make the surface more smooth and the triangulation more evenly spaced.",
        default=False,
    )
    refineholeedgelen: FloatProperty(
        name="Hole Refinement Edge Len",
        description="The target edge lenght of the triangulation inside the filled hole.",
        default=3.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE",
    )
