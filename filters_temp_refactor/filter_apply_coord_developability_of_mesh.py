import bpy
import math
import mathutils
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty, EnumProperty
from ..base_filter import MeshLabFilterBase


def update_polygonal_state(self, context):
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


def enforce_batch_true(self, context):
    if not self.blender_batch:
        self.blender_batch = True


class MESHLAB_PG_apply_coord_developability_of_mesh(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "apply_coord_developability_of_mesh"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    requires_polygons_disk = True
    prefer_ply_disk = False

    angle_parameters = ["anglethreshold"]

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        if key in ["minstepsize", "tau", "m1"]:
            return self.optmethod == "[F] Fixed stepsize"
        if key == "blender_polygonal":
            return False
        return False

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

        # Processamento iterativo (Batch)
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
            "Batch Make Mesh Developable concluído"
            if len(original_objs) > 1
            else "Make Mesh Developable concluído"
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
    optmethod: EnumProperty(
        name="Gradient method",
        description="The gradient method optimization algorithm to use.",
        items=[
            ("[B] Backtracking line search", "[B] Backtracking line search", ""),
            ("[F] Fixed stepsize", "[F] Fixed stepsize", ""),
        ],
        default="[B] Backtracking line search",
    )
    maxfunevals: IntProperty(
        name="Max function evaluations",
        description="The maximum number of function evaluation. Once reached, the optimization stops.",
        default=400,
        min=1,
    )
    eps: FloatProperty(
        name="Stop threshold",
        description="Optimization stops when the squared norm of the gradient is less than or equal to the accuracy.",
        default=1e-05,
        precision=5,
    )
    stepsize: FloatProperty(
        name="Initial step size",
        description="The initial step size of the opt method, fixed when using [F] optimizer.",
        default=0.01,
        precision=4,
    )
    minstepsize: FloatProperty(
        name="Min step size (B only)",
        description="The minimum step size for the backtracking line search opt method.",
        default=1e-10,
        precision=8,
    )
    tau: FloatProperty(
        name="Tau (B only)",
        description="Scaling factor of the step size for the backtracking line search opt method.",
        default=0.8,
        precision=3,
    )
    m1: FloatProperty(
        name="Armijo constant (B only)",
        description="The constant of the Armijo condition of the backtracking line search opt method.",
        default=0.0001,
        precision=4,
    )
    edgeflips: BoolProperty(
        name="Apply edge flips",
        description="Whether or not to apply edge flips when necessary during optimization.",
        default=True,
    )
    edgecollapses: BoolProperty(
        name="Apply edge collapses",
        description="Whether or not to apply edge collapses when necessary during optimization.",
        default=True,
    )
    # Subtype 'ANGLE' habilita a interface nativa do Blender (Graus) processando em radianos nos bastidores
    anglethreshold: FloatProperty(
        name="Post-processing angle threshold",
        description="The maximum angle under which an edge flip or an edge collapse must be performed during optimization.",
        default=math.radians(18),
        subtype="ANGLE",
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
