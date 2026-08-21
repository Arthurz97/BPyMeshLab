import bpy
import mathutils
from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


def update_polygonal_state(self, context):
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


def enforce_batch_true(self, context):
    if not self.blender_batch:
        self.blender_batch = True


class MESHLAB_PG_apply_coord_laplacian_smoothing(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "apply_coord_laplacian_smoothing"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    requires_polygons_disk = True
    prefer_ply_disk = False

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key in ["blender_preserve_transforms", "selectedonly"]:
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        if key == "blender_polygonal":
            return False
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Swap da chave de seleção para a exigência do PyMeshLab
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # Processamento iterativo (Batch) forçado, sem Modo Global
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
            "Batch Laplacian Smooth concluído"
            if len(original_objs) > 1
            else "Laplacian Smooth concluído"
        )
        return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

    # --- PARÂMETROS DA INTERFACE ---
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
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    stepsmoothnum: IntProperty(
        name="Smoothing steps",
        description="The number of times that the whole algorithm (normal smoothing + vertex fitting) is iterated.",
        default=3,
        min=0,
    )
    boundary: BoolProperty(
        name="1D Boundary Smoothing",
        description="Smooth boundary edges only by themselves (e.g. the polyline forming the boundary of the mesh is independently smoothed). This can reduce the shrinking on the border but can have strange effects on very small boundaries.",
        default=True,
    )
    cotangentweight: BoolProperty(
        name="Cotangent weighting",
        description="Use cotangent weighting scheme for the averaging of the position. Otherwise the simpler umbrella scheme (1 if the edge is present) is used.",
        default=True,
    )
    selectedonly: BoolProperty(
        name="Affect only selection",
        description="If checked the filter is performed only on the selected area.",
        default=False,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
