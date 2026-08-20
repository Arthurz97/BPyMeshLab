import bpy
import bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_simplified_point_cloud(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_simplified_point_cloud"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    percentage_parameters = ["radius"]

    def is_property_disabled(self, key, context):
        # 1. Travas estruturais de Batch / Global
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        if key == "blender_point_cloud":
            return len(context.selected_objects) <= 1 or getattr(
                self, "blender_batch", False
            )

        # 2. Lógica UI do PyMeshLab: O Raio (se > 0) anula a busca por N-Samples exatos
        radius_active = getattr(self, "radius", 0.0) > 0.0

        if key in ["samplenum", "exactnumflag", "exactnumtolerance"]:
            return radius_active

        # 3. Lógica UI do PyMeshLab: Dependências de sub-parâmetros
        if key == "bestsamplepool":
            return not getattr(self, "bestsampleflag", False)
        if key == "exactnumtolerance":
            return not getattr(self, "exactnumflag", False) or radius_active

        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Remove a flag exclusiva do Blender para que a API C++ do PyMeshLab não quebre
        if "blender_point_cloud" in params:
            params.pop("blender_point_cloud")

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

        # =================================================================
        # MODO BATCH ou MODO ÚNICO
        # =================================================================
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
                "Batch Point Cloud Simplification concluído"
                if len(original_objs) > 1
                else "Point Cloud Simplification concluído"
            )
            return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

        # =================================================================
        # MODO GLOBAL (HÍBRIDO: POINT CLOUD (JOIN) vs MESH (BOOLEAN MANIFOLD))
        # =================================================================
        else:
            bpy.ops.object.select_all(action="DESELECT")

            temp_col = bpy.data.collections.new("Temp_Boolean_Collection")
            context.scene.collection.children.link(temp_col)

            temp_objs = []
            active_idx = 0
            if context.active_object in original_objs:
                active_idx = original_objs.index(context.active_object)

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

            if getattr(props, "blender_point_cloud", False):
                # ROTA 1: NUVENS DE PONTOS -> Apenas JOIN (Preserva normais sem criar faces destrutivas)
                bpy.ops.object.select_all(action="DESELECT")
                for obj in temp_objs:
                    obj.select_set(True)

                context.view_layer.objects.active = temp_objs[active_idx]
                bpy.ops.object.join()
                host_obj = context.active_object

                # Vincula o objeto fundido à coleção principal
                context.collection.objects.link(host_obj)
            else:
                # ROTA 2: RASTERIZAÇÃO DE MALHAS -> BOOLEAN MANIFOLD + WELD
                host_mesh = bpy.data.meshes.new("Host_Mesh")
                host_obj = bpy.data.objects.new("Host_Obj", host_mesh)
                context.collection.objects.link(host_obj)

                bpy.ops.object.select_all(action="DESELECT")
                host_obj.select_set(True)
                context.view_layer.objects.active = host_obj

                active_orig = original_objs[active_idx]
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
                        "A união falhou. O modo Global para Malhas exige que elas sejam fechadas (Manifold). Se a intenção for simplificar uma Nuvem de Pontos isolada, ative o 'Global Point Cloud (Join)'.",
                    )

                # Limpeza dos temporários usados no Boolean
                for obj in temp_objs:
                    try:
                        if obj.name in bpy.data.objects:
                            bpy.data.objects.remove(obj, do_unlink=True)
                    except ReferenceError:
                        pass

            bpy.data.collections.remove(temp_col)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            status, msg = super().apply_filter(context, props)

            if host_obj:
                try:
                    if host_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(host_obj, do_unlink=True)
                except ReferenceError:
                    pass

            if status == "FINISHED" and context.active_object:
                base_name = original_objs[active_idx].name.split("_bpymeshlab")[0]
                context.active_object.name = f"{base_name}_bpymeshlab"

            prefs.global_prev_mesh_action = original_action

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if status != "FINISHED":
                return status, msg

            return (
                status,
                "Global Point Cloud Simplification gerado com sucesso.",
            )

    # =================================================================
    # PARÂMETROS DA INTERFACE
    # =================================================================

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
    blender_point_cloud: BoolProperty(
        name="Global Point Cloud (Join)",
        description="Enable this if you are reconstructing from Point Clouds (vertices only) instead of dense meshes. It uses 'Join' instead of 'Boolean Manifold', ensuring normals are fused and preserved correctly across multiple objects.",
        default=False,
    )

    samplenum: IntProperty(
        name="Number of samples",
        description="The desired number of samples. The ray of the disk is calculated according to the sampling density.",
        default=1000,
        min=0,
    )
    radius: FloatProperty(
        name="Explicit Radius",
        description="If not zero this parameter override the previous parameter to allow exact radius specification.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0,
        min=0.0,
    )
    bestsampleflag: BoolProperty(
        name="Best Sample Heuristic",
        description="If true it will use a simple heuristic for choosing the samples. At a small cost (it can slow a bit the process) it usually improve the maximality of the generated sampling.",
        default=True,
    )
    bestsamplepool: IntProperty(
        name="Best Sample Pool Size",
        description="Used only if the Best Sample Flag is true. It control the number of attempt that it makes to get the best sample. It is reasonable that it is smaller than the Montecarlo oversampling factor.",
        default=10,
        min=1,
    )
    exactnumflag: BoolProperty(
        name="Precise sample number",
        description="If requested it will try to do a dicotomic search for the best poisson disk radius that will generate the requested number of samples with the below specified tolerance. Obviously it will takes much longer.",
        default=False,
    )
    exactnumtolerance: FloatProperty(
        name="Precise sample number tolerance",
        description="If a precise number of sample is requested, the sample number will be matched with the precision specified here. Precision is specified as a fraction of the sample number. so for example a precision of 0.005 over 1000 samples means that you can get 995 or 1005 samples.",
        default=0.005,
        min=0.0,
    )
