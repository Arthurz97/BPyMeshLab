import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_meshing_isotropic_explicit_remeshing(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "meshing_isotropic_explicit_remeshing"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["quality", "texture_u", "texture_v", "sharp_face", "Col"]
    prefer_ply_disk = True
    percentage_parameters = ["targetlen", "maxsurfdist"]
    angle_parameters = ["featuredeg"]

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key in ["blender_preserve_transforms", "selectedonly"]:
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        return False

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        is_batch = getattr(props, "blender_batch", False)
        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # MODO BATCH ou MODO ÚNICO
        if is_batch or len(original_objs) == 1:
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
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )

                status, msg = super().apply_filter(context, props)

                if preserve and status == "FINISHED" and context.active_object:
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

                if new_obj.name in bpy.data.objects:
                    bpy.data.objects.remove(new_obj, do_unlink=True)

                if status == "FINISHED" and context.active_object:
                    base_name = obj.name.split("_pymeshlab")[0]
                    context.active_object.name = f"{base_name}_pymeshlab"

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
                "Batch Remesh concluído"
                if len(original_objs) > 1
                else "Isotropic Remesh concluído"
            )
            return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

        # MODO GLOBAL (BOOLEAN MANIFOLD VIA COLLECTION)
        else:
            bpy.ops.object.select_all(action="DESELECT")

            temp_col = bpy.data.collections.new("Temp_Boolean_Collection")
            context.scene.collection.children.link(temp_col)

            temp_objs = []
            for obj in original_objs:
                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                temp_col.objects.link(new_obj)

                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                bpy.ops.object.convert(target="MESH")
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )
                temp_objs.append(new_obj)

            host_mesh = bpy.data.meshes.new("Host_Mesh")
            host_obj = bpy.data.objects.new("Host_Obj", host_mesh)
            context.collection.objects.link(host_obj)

            bpy.ops.object.select_all(action="DESELECT")
            host_obj.select_set(True)
            context.view_layer.objects.active = host_obj

            active_orig = (
                context.active_object
                if context.active_object in original_objs
                else original_objs[0]
            )
            host_obj.location = active_orig.location.copy()

            bool_mod = host_obj.modifiers.new(name="Global_Union", type="BOOLEAN")
            bool_mod.operation = "UNION"
            bool_mod.operand_type = "COLLECTION"
            bool_mod.collection = temp_col
            bool_mod.solver = "MANIFOLD"

            bpy.ops.object.modifier_apply(modifier=bool_mod.name)

            if len(host_obj.data.polygons) == 0:
                bpy.data.objects.remove(host_obj, do_unlink=True)
                for obj in temp_objs:
                    bpy.data.objects.remove(obj, do_unlink=True)
                bpy.data.collections.remove(temp_col)

                return (
                    "CANCELLED",
                    "A união falhou. O modo Global exige que as malhas cruzadas sejam fechadas (Manifold).",
                )

            for obj in temp_objs:
                bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.collections.remove(temp_col)

            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            # OVERRIDE TEMPORÁRIO: Desliga o selectedonly para evitar a trava de proteção da Classe Mestra
            original_selectedonly = getattr(props, "selectedonly", False)
            if original_selectedonly:
                props.selectedonly = False

            status, msg = super().apply_filter(context, props)

            # Restaura a opção original da interface para o usuário
            if original_selectedonly:
                props.selectedonly = True

            if host_obj.name in bpy.data.objects:
                bpy.data.objects.remove(host_obj, do_unlink=True)

            if status == "FINISHED" and context.active_object:
                base_name = active_orig.name.split("_pymeshlab")[0]
                context.active_object.name = f"{base_name}_pymeshlab"

            prefs.global_prev_mesh_action = original_action

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            return status, "Global Isotropic Remesh gerado com sucesso."

    blender_batch: BoolProperty(
        name="Batch Process",
        description="If checked, processes each selected object individually. If unchecked, generates a single global volume englobing all objects.",
        default=False,
    )
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
