import bpy
import bmesh
import mathutils
import pymeshlab
import tempfile
import os
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, PointerProperty
from ..base_filter import MeshLabFilterBase
from .. import utils


class MESHLAB_PG_generate_boolean_union(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_boolean_union"
    requires_selection = True
    ignore_selection_count = False
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    _temp_second_obj = None

    @classmethod
    def pre_process_parameters(cls, params, props):
        if "second_mesh_object" in params:
            del params["second_mesh_object"]

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        engine = bpy.context.scene.meshlab_prefs.processing_engine
        target_obj = cls._temp_second_obj

        if engine == "MEMORY":
            vertices, faces, _, v_scalars, v_normals = utils.blender_to_numpy(
                target_obj, extract_selection=False, extract_quality=True
            )
            mesh_kwargs = {"vertex_matrix": vertices, "face_matrix": faces}
            if v_scalars is not None:
                mesh_kwargs["v_scalar_array"] = v_scalars
            if v_normals is not None:
                mesh_kwargs["v_normals_matrix"] = v_normals

            m = pymeshlab.Mesh(**mesh_kwargs)
            ms.add_mesh(m)

        elif engine == "DISK":
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "second_mesh.ply")

                active_before = bpy.context.view_layer.objects.active
                selected_before = bpy.context.selected_objects[:]

                bpy.ops.object.select_all(action="DESELECT")
                target_obj.select_set(True)
                bpy.context.view_layer.objects.active = target_obj

                bpy.ops.wm.ply_export(
                    filepath=input_path,
                    export_selected_objects=True,
                    ascii_format=False,
                    export_normals=False,
                    export_uv=False,
                    export_colors="NONE",
                    forward_axis="Y",
                    up_axis="Z",
                )

                ms.load_new_mesh(input_path)

                bpy.ops.object.select_all(action="DESELECT")
                for obj in selected_before:
                    obj.select_set(True)
                bpy.context.view_layer.objects.active = active_before

        params["first_mesh"] = 0
        params["second_mesh"] = 1

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        if len(context.selected_objects) > 1:
            return (
                "CANCELLED",
                "Múltiplas seleções não são suportadas. Selecione apenas 1 objeto principal (First Mesh).",
            )

        original_first_obj = context.active_object
        original_second_obj = props.second_mesh_object

        if not original_first_obj or original_first_obj.type != "MESH":
            return (
                "CANCELLED",
                "O objeto ativo (First Mesh) precisa ser uma malha (Mesh).",
            )

        if not original_second_obj or original_second_obj.type != "MESH":
            return (
                "CANCELLED",
                "Selecione um objeto alvo válido (Second Mesh) no conta-gotas.",
            )

        if original_first_obj == original_second_obj:
            return (
                "CANCELLED",
                "O objeto alvo (Second Mesh) não pode ser o mesmo objeto ativo.",
            )

        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        bpy.ops.object.select_all(action="DESELECT")
        temp_first_obj = original_first_obj.copy()
        temp_first_obj.data = original_first_obj.data.copy()
        context.collection.objects.link(temp_first_obj)

        temp_first_obj.select_set(True)
        context.view_layer.objects.active = temp_first_obj

        bpy.ops.object.convert(target="MESH")

        original_matrix = temp_first_obj.matrix_world.copy()
        original_rotation = temp_first_obj.rotation_euler.copy()
        original_scale = temp_first_obj.scale.copy()
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        bpy.ops.object.select_all(action="DESELECT")
        temp_second_obj = original_second_obj.copy()
        temp_second_obj.data = original_second_obj.data.copy()
        context.collection.objects.link(temp_second_obj)

        temp_second_obj.select_set(True)
        context.view_layer.objects.active = temp_second_obj

        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

        engine = prefs.processing_engine
        if engine == "DISK":
            bm = bmesh.new()
            bm.from_mesh(temp_second_obj.data)
            bmesh.ops.triangulate(
                bm, faces=bm.faces[:], quad_method="FIXED", ngon_method="BEAUTY"
            )
            bm.to_mesh(temp_second_obj.data)
            bm.free()
            temp_second_obj.data.update()

        cls._temp_second_obj = temp_second_obj

        bpy.ops.object.select_all(action="DESELECT")
        temp_first_obj.select_set(True)
        context.view_layer.objects.active = temp_first_obj

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

        if temp_first_obj.name in bpy.data.objects:
            bpy.data.objects.remove(temp_first_obj, do_unlink=True)
        if temp_second_obj.name in bpy.data.objects:
            bpy.data.objects.remove(temp_second_obj, do_unlink=True)
        cls._temp_second_obj = None

        if status == "FINISHED" and context.active_object:
            base_name = original_first_obj.name.split("_bpymeshlab")[0]
            context.active_object.name = f"{base_name}_bpymeshlab"

        prefs.global_prev_mesh_action = original_action

        if overall_status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
            for obj_to_action in [original_first_obj, original_second_obj]:
                if obj_to_action:
                    if original_action == "HIDE":
                        obj_to_action.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj_to_action, do_unlink=True)

        if overall_status != "FINISHED":
            return overall_status, error_msg

        return overall_status, "Mesh Boolean: Union aplicado com sucesso."

    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )
    second_mesh_object: PointerProperty(
        type=bpy.types.Object,
        name="Object",
        description="Mesh object to use for Boolean operation.",
    )
    transfer_face_color: BoolProperty(
        name="Transfer face color",
        description="Save the color of the birth face to the faces of resulting mesh.",
        default=False,
    )
    transfer_face_quality: BoolProperty(
        name="Transfer face quality",
        description="Save the quality of the birth face to the faces of resulting mesh.",
        default=False,
    )
    transfer_vert_color: BoolProperty(
        name="Transfer vertex color",
        description="Save the color of the birth vertex to the faces of resulting mesh. For newly created vertices, a simple average of the neighbours is computed.",
        default=False,
    )
    transfer_vert_quality: BoolProperty(
        name="Transfer vertex quality",
        description="Save the quality of the birth vertex to the faces of resulting mesh. For newly created vertices, a simple average of the neighbours is computed.",
        default=False,
    )
