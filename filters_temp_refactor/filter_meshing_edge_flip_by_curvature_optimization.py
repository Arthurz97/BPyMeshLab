import bpy
import mathutils
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase


def enforce_batch_true(self, context):
    if not self.blender_batch:
        self.blender_batch = True


class MESHLAB_PG_meshing_edge_flip_by_curvature_optimization(
    PropertyGroup, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_edge_flip_by_curvature_optimization"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Inclusão da propriedade na lista de ângulos para tratamento matemático da classe base
    angle_parameters = ["pthreshold"]

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Mapeia a propriedade 'selectedonly' (da nossa interface) para 'selection' (do PyMeshLab)
        if "selectedonly" in params:
            params["selection"] = params.pop("selectedonly")

        # Converte a seleção da interface (String) para Inteiro
        params["curvtype"] = int(props.curvtype)

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

        # Processamento iterativo individual (Batch) na memória
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
            "Batch Curvature Flipping concluído"
            if len(original_objs) > 1
            else "Curvature Flipping Optimization concluído"
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

    selectedonly: BoolProperty(
        name="Update selection",
        description="Apply edge flip optimization on selected faces only.",
        default=False,
    )
    pthreshold: FloatProperty(
        name="Angle Thr (deg) (°)",
        description="To avoid excessive flipping/swapping we consider only couple of faces with a significant diedral angle (e.g. greater than the indicated threshold).",
        default=1.0,
        min=0.0,
        max=180.0,
        precision=1,
        step=10,
    )
    curvtype: EnumProperty(
        name="Curvature metric",
        description="Choose a metric to compute surface curvature on vertices\nH = mean curv, K = gaussian curv, A = area per vertex\n\n1: Mean curvature = H\n2: Norm squared mean curvature = (H * H) / A\n3: Absolute curvature:\nif(K >= 0) return 2 * H\nelse return 2 * sqrt(H ^ 2 - A * K)",
        items=[
            ("0", "mean", ""),
            ("1", "norm squared", ""),
            ("2", "absolute", ""),
        ],
        default="0",
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
