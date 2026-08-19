import bpy
import bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_sampling_montecarlo(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_sampling_montecarlo"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

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
                "Batch Montecarlo Sampling concluído"
                if len(original_objs) > 1
                else "Montecarlo Sampling concluído"
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

            bm = bmesh.new()
            bm.from_mesh(host_obj.data)
            bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.00001)
            bm.to_mesh(host_obj.data)
            bm.free()
            host_obj.data.update()

            status, msg = super().apply_filter(context, props)

            if host_obj:
                try:
                    if host_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(host_obj, do_unlink=True)
                except ReferenceError:
                    pass

            if status == "FINISHED" and context.active_object:
                base_name = active_orig.name.split("_bpymeshlab")[0]
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

            return status, "Global Montecarlo Sampling gerado com sucesso."

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
    samplenum: IntProperty(
        name="Number of samples",
        description="The desired number of samples. It can be smaller or larger than the mesh size, and according to the chosen sampling strategy it will try to adapt.",
        default=8,
        min=0,
    )
    weighted: BoolProperty(
        name="Quality Weighted Sampling",
        description="Use per vertex quality to drive the vertex sampling. The number of samples falling in each face is proportional to the face area multiplied by the average quality of the face vertices.",
        default=False,
    )
    perfacenormal: BoolProperty(
        name="Per-Face Normal",
        description="If true for each sample we take the normal of the sampled face, otherwise the normal interpolated from the vertex normals.",
        default=False,
    )
    radiusvariance: FloatProperty(
        name="Radius Variance",
        description="The radius of the disk is allowed to vary between r/var and r*var. If this parameter is 1 the sampling is the same of the Poisson Disk Sampling.",
        default=1.0,
    )
    exactnum: BoolProperty(
        name="Exact Sample Number",
        description="If the required total number of samples is not a strict exact requirement we can exploit a different algorithmbased on the choice of the number of samples inside each triangle by a random Poisson-distributed number with mean equal to the expected number of samples times the area of the triangle over the surface of the whole mesh.",
        default=True,
    )
    edgesampling: BoolProperty(
        name="Sample CreaseEdge Only",
        description="Restrict the sampling process to the crease edges only. Useful to sample in a more accurate way the feature edges of a mechanical mesh.",
        default=False,
    )
