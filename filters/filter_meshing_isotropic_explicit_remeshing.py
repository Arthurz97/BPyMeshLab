import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_meshing_isotropic_explicit_remeshing(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "meshing_isotropic_explicit_remeshing"
    requires_selection = True
    is_batch_only = True
    shade_flat = True
    remove_attributes = ["quality", "texture_u", "texture_v", "sharp_face", "Col"]
    prefer_ply_disk = True
    percentage_parameters = ["targetlen", "maxsurfdist"]
    angle_parameters = ["featuredeg"]

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        overall_status = "FINISHED"

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

            # 2. Aplica modificadores e transformações para uma malha final limpa
            bpy.ops.object.convert(target="MESH")

            original_matrix = new_obj.matrix_world.copy()
            original_rotation = new_obj.rotation_euler.copy()
            original_scale = new_obj.scale.copy()
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            # 3. Roda o filtro no objeto temporário
            status, msg = super().apply_filter(context, props)

            if (
                getattr(props, "blender_preserve_transforms", False)
                and status == "FINISHED"
                and context.active_object
            ):
                import mathutils

                temp_matrix = mathutils.Matrix.Translation(original_matrix.translation)
                context.active_object.data.transform(
                    original_matrix.inverted() @ temp_matrix
                )
                context.active_object.matrix_world = original_matrix
                context.active_object.rotation_euler = original_rotation
                context.active_object.scale = original_scale

            if status != "FINISHED":
                overall_status = status

            # 4. Limpa o objeto temporário usado de ponte
            if new_obj.name in bpy.data.objects:
                bpy.data.objects.remove(new_obj, do_unlink=True)

            # Renomeia o objeto final gerado, removendo sufixo
            if status == "FINISHED" and context.active_object:
                base_name = obj.name.split("_pymeshlab")[0]
                context.active_object.name = f"{base_name}_pymeshlab"

        # Restaura a preferência de UI
        prefs.global_prev_mesh_action = original_action

        # Aplica HIDE ou DELETE aos originais no final do processo
        if overall_status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
            for obj in original_objs:
                if original_action == "HIDE":
                    obj.hide_set(True)
                elif original_action == "DELETE":
                    bpy.data.objects.remove(obj, do_unlink=True)

        if len(original_objs) > 1:
            return (
                overall_status,
                f"Batch Remesh concluído em {len(original_objs)} objetos.",
            )
        return overall_status, "Isotropic Remesh concluído com sucesso."

    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )

    iterations: IntProperty(
        name="Iterations",
        description="Number of iterations of the remeshing operations to repeat on the mesh.",
        default=10,
        min=0,
    )
    adaptive: BoolProperty(
        name="Adaptive remeshing",
        description="Toggles adaptive isotropic remeshing.",
        default=False,
    )
    selectedonly: BoolProperty(
        name="Remesh only selected faces",
        description="If checked the remeshing operations will be applied only to the selected faces.",
        default=False,
    )
    targetlen: FloatProperty(
        name="Target Length",
        description="Sets the absolute target length for the remeshed mesh edges.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.1,
        min=0.0001,
        soft_min=0.01,
    )
    featuredeg: FloatProperty(
        name="Crease Angle (°)",
        description="Minimum angle between faces of the original to consider the shared edge as a feature to be preserved.",
        default=30.0,
        min=0.0,
        max=180.0,
        precision=1,
        step=10,
    )
    checksurfdist: BoolProperty(
        name="Check Surface Distance",
        description="If toggled each local operation must deviate from original mesh by [Max. surface distance].",
        default=False,
    )
    maxsurfdist: FloatProperty(
        name="Max. Surface Distance",
        description="Maximal absolute surface deviation allowed for each local operation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    splitflag: BoolProperty(
        name="Refine Step",
        description="If checked the remeshing operations will include a refine step.",
        default=True,
    )
    collapseflag: BoolProperty(
        name="Collapse Step",
        description="If checked the remeshing operations will include a collapse step.",
        default=True,
    )
    swapflag: BoolProperty(
        name="Edge-Swap Step",
        description="If checked the remeshing operations will include a edge-swap step, aimed at improving the vertex valence of the resulting mesh.",
        default=True,
    )
    smoothflag: BoolProperty(
        name="Smooth Step",
        description="If checked the remeshing operations will include a smoothing step, aimed at relaxing the vertex positions in a Laplacian sense.",
        default=True,
    )
    reprojectflag: BoolProperty(
        name="Reproject Step",
        description="If checked the remeshing operations will include a step to reproject the mesh vertices on the original surface.",
        default=True,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
