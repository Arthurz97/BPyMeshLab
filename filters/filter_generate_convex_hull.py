import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_convex_hull(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_convex_hull"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    # Checkbox de Batch
    blender_batch: BoolProperty(
        name="Batch Process",
        description="If checked, processes each selected object individually. If unchecked, generates a single global Convex Hull englobing all objects.",
        default=False,
    )
    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        return False

    @classmethod
    def apply_filter(cls, context, props):
        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]

        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        # MODO BATCH
        if getattr(props, "blender_batch", False) and len(original_objs) > 1:
            overall_status = "FINISHED"
            error_msg = ""

            # Mascara a ação original para o base_filter não deletar os objetos originais no meio do loop
            prefs = context.scene.meshlab_prefs
            original_action = prefs.global_prev_mesh_action
            prefs.global_prev_mesh_action = "KEEP"

            for obj in original_objs:
                bpy.ops.object.select_all(action="DESELECT")

                # 1. Cria a cópia temporária do objeto atual
                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                context.collection.objects.link(new_obj)

                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                # 2. Aplica modificadores e transformações (Garante escala/rotação limpas no MeshLab)
                bpy.ops.object.convert(target="MESH")

                # Salva a matriz ANTES do transform_apply para compensação matemática no modo Batch
                original_matrix = new_obj.matrix_world.copy()
                original_rotation = new_obj.rotation_euler.copy()
                original_scale = new_obj.scale.copy()
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )

                # 3. Roda o filtro no objeto temporário limpo
                status, msg = super().apply_filter(context, props)

                # Compensação matemática e Restauração visual da UI
                if (
                    getattr(props, "blender_preserve_transforms", False)
                    and status == "FINISHED"
                    and context.active_object
                ):
                    import mathutils

                    temp_matrix = mathutils.Matrix.Translation(
                        original_matrix.translation
                    )
                    context.active_object.data.transform(
                        original_matrix.inverted() @ temp_matrix
                    )
                    context.active_object.matrix_world = original_matrix
                    context.active_object.rotation_euler = original_rotation
                    context.active_object.scale = original_scale

                if status != "FINISHED":
                    overall_status = status
                    error_msg = msg

                # 4. Limpa o objeto temporário usado de ponte
                if new_obj.name in bpy.data.objects:
                    bpy.data.objects.remove(new_obj, do_unlink=True)

                # Renomeia o objeto final gerado, removendo qualquer sufixo temporário
                if status == "FINISHED" and context.active_object:
                    base_name = obj.name.split("_bpymeshlab")[0]
                    context.active_object.name = f"{base_name}_bpymeshlab"

            # Restaura a preferência de UI
            prefs.global_prev_mesh_action = original_action

            # Aplica HIDE ou DELETE aos originais, se solicitado, no final do processo
            if overall_status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if overall_status != "FINISHED":
                return overall_status, error_msg

            return (
                overall_status,
                f"Batch Process concluído em {len(original_objs)} objetos.",
            )

        # MODO GLOBAL
        else:
            if len(original_objs) == 1:
                return super().apply_filter(context, props)

            # --- Estratégia de Fusão Temporária (Aplicando Modificadores e Transformações) ---
            # Identifica o índice do objeto ativo real para manter sua origem e nome no Join
            active_idx = 0
            if context.active_object in original_objs:
                active_idx = original_objs.index(context.active_object)

            bpy.ops.object.select_all(action="DESELECT")
            temp_objs = []

            for obj in original_objs:
                # 1. Duplica o objeto (copiando a pilha de modificadores junto)
                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                context.collection.objects.link(new_obj)

                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                # 2. Aplica todos os modificadores da Viewport (Visual Geometry to Mesh)
                bpy.ops.object.convert(target="MESH")

                # 3. Aplica Rotação e Escala mantendo a origem local ancorada (location=False)
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )

                temp_objs.append(new_obj)

            bpy.ops.object.select_all(action="DESELECT")
            for obj in temp_objs:
                obj.select_set(True)

            # Define o representante do ativo original como ativo no Blender para o Join
            context.view_layer.objects.active = temp_objs[active_idx]
            bpy.ops.object.join()

            temp_merged = context.active_object

            prefs = context.scene.meshlab_prefs
            original_action = prefs.global_prev_mesh_action
            prefs.global_prev_mesh_action = "KEEP"

            status, msg = super().apply_filter(context, props)

            prefs.global_prev_mesh_action = original_action

            if temp_merged:
                try:
                    if temp_merged.name in bpy.data.objects:
                        bpy.data.objects.remove(temp_merged, do_unlink=True)
                except ReferenceError:
                    pass

            # Limpeza de segurança (com proteção ReferenceError para objetos já deletados pelo Join)
            for obj in temp_objs:
                try:
                    if obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                except ReferenceError:
                    pass

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if status != "FINISHED":
                return status, msg

            return status, "Global Convex Hull gerado com sucesso."
