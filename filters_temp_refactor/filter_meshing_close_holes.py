import bpy
import mathutils
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, IntProperty, FloatProperty
from ..base_filter import MeshLabFilterBase


def enforce_batch_true(self, context):
    if not self.blender_batch:
        self.blender_batch = True


class MESHLAB_PG_meshing_close_holes(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "meshing_close_holes"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "refineholeedgelen":
            return not getattr(self, "refinehole", False)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        import pymeshlab

        # Transforma a propriedade de interface do Blender na chave esperada pela API
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

        # Injeta o objeto PercentageValue nativo do PyMeshLab enviando o valor exato da UI.
        # Se a UI mostra 3.0%, envia 3.0 para o motor calcular a proporção da malha.
        if "refineholeedgelen" in params:
            params["refineholeedgelen"] = pymeshlab.PercentageValue(
                props.refineholeedgelen
            )

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        # TRAVA FAIL-FAST: Evita o crash nativo do C++ ("Current mesh does not have Any Faces")
        for obj in original_objs:
            if len(obj.data.polygons) == 0:
                return (
                    "CANCELLED",
                    f"Filtro abortado: A malha '{obj.name}' não possui faces (Point Cloud). O filtro Close Holes exige geometria base.",
                )

        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # Processamento iterativo (Batch) forçado para evitar travamentos com buracos complexos em operações booleanas
        for obj in original_objs:
            bpy.ops.object.select_all(action="DESELECT")

            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            context.collection.objects.link(new_obj)

            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj

            bpy.ops.object.convert(target="MESH")

            original_matrix = new_obj.matrix_world.copy()
            original_rotation = new_obj.rotation_euler.copy()
            original_scale = new_obj.scale.copy()
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            status, msg = super().apply_filter(context, props)

            if preserve and status == "FINISHED" and context.active_object:
                temp_matrix = mathutils.Matrix.Translation(original_matrix.translation)
                context.active_object.data.transform(
                    original_matrix.inverted() @ temp_matrix
                )
                context.active_object.matrix_world = original_matrix
                context.active_object.rotation_euler = original_rotation
                context.active_object.scale = original_scale

            if status != "FINISHED":
                overall_status = status
                error_msg = msg

            if new_obj.name in bpy.data.objects:
                bpy.data.objects.remove(new_obj, do_unlink=True)

            if status == "FINISHED" and context.active_object:
                base_name = obj.name.split("_bpymeshlab")[0]
                context.active_object.name = f"{base_name}_bpymeshlab"

        prefs.global_prev_mesh_action = original_action

        if overall_status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
            for obj in original_objs:
                if original_action == "HIDE":
                    obj.hide_set(True)
                elif original_action == "DELETE":
                    bpy.data.objects.remove(obj, do_unlink=True)

        if overall_status != "FINISHED":
            return overall_status, error_msg

        msg_end = (
            "Batch Close Holes concluído"
            if len(original_objs) > 1
            else "Close Holes concluído"
        )
        return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

    blender_batch: BoolProperty(
        name="Batch Process",
        description="Processes each selected object individually.",
        default=True,
        update=enforce_batch_true,
    )
    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )

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
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
