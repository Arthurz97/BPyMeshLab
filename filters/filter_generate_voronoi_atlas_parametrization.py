import bpy
import mathutils
from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


def enforce_batch_true(self, context):
    if not self.blender_batch:
        self.blender_batch = True


class MESHLAB_PG_generate_voronoi_atlas_parametrization(
    PropertyGroup, MeshLabFilterBase
):
    pymeshlab_filter = "generate_voronoi_atlas_parametrization"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # 1. Força o tráfego via OBJ para garantir suporte a UV
    requires_uv_disk = True

    # 2. O filtro gera o Atlas em uma nova malha (ID 1).
    # Extraímos a nova camada e nomeamos com o sufixo correto.
    extract_multiple_layers = True
    layer_mapping = {1: "VoroAtlas"}

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
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

            # --- LIMPEZA DE UVs (Segurança Comprovada) ---
            # Se a malha possuir qualquer resquício de UV prévia,
            # o Voronoi Atlas aborta a parametrização na memória C++.
            while new_obj.data.uv_layers:
                new_obj.data.uv_layers.remove(new_obj.data.uv_layers[0])
            # ----------------------------------------------

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
            "Batch Voronoi Atlas concluído"
            if len(original_objs) > 1
            else "Voronoi Atlas Parametrization concluído"
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
    regionnum: IntProperty(
        name="Approx. Region Num",
        description="An estimation of the number of regions that must be generated. Smaller regions could lead to parametrizations with smaller distortion.",
        default=10,
        min=0,
    )
    overlapflag: BoolProperty(
        name="Overlap",
        description="If checked the resulting parametrization will be composed by overlapping regions, e.g. the resulting mesh will have duplicated faces: each region will have a ring of ovelapping duplicate faces that will ensure that border regions will be parametrized in the atlas twice. This is quite useful for building mipmap robust atlases.",
        default=False,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
