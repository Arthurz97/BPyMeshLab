import bpy
import pymeshlab
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_resampled_uniform_mesh(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_resampled_uniform_mesh"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["cellsize", "offset"]

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

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        return False

    def is_property_hidden(self, key):
        if key == "offset" and self.absdist:
            return True
        if key == "ui_offset_abs" and not self.absdist:
            return True
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
                "Batch Resampling concluído"
                if len(original_objs) > 1
                else "Resampling concluído"
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

            # Se a falha reportada no seu print acontecer, o objeto terá 0 faces
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

            # --- LIMPEZA DE COSTURA BOOLEANA (WELD) ---
            # Remove vértices duplos microscópicos (0.01mm) gerados pela interseção do Exact Solver
            import bmesh

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

            return status, "Global Uniform Mesh Resampling gerado com sucesso."

    @classmethod
    def pre_process_parameters(cls, params, props):
        if props.absdist:
            params["offset"] = pymeshlab.PureValue(float(props.ui_offset_abs))

    cellsize: FloatProperty(
        name="Precision",
        description="Size of the cell. Smaller cells give better precision at a higher computational cost. Remember that halving the cell size means that you build a volume 8 times larger.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.03,
        min=0.0001,
        soft_min=0.01,
    )
    offset: FloatProperty(
        name="Offset",
        description="Offset of the created surface (i.e. distance of the created surface from the original one). If offset is zero, the created surface passes on the original mesh itself. Values greater than zero mean an external surface, and lower than zero mean an internal surface. In practice this value is the threshold passed to the Marching Cube algorithm to extract the isosurface from the distance field representation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0,
        soft_min=-0.1,
        soft_max=1.0,
    )
    ui_offset_abs: FloatProperty(
        name="Offset",
        description="[Absolute Mode] Offset of the created surface. Must be strictly positive. Values too close to zero may result in broken topology.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.03,
        min=0.000001,
        soft_min=0.03,
        soft_max=1.0,
    )
    mergeclosevert: BoolProperty(
        name="Clean Vertices",
        description="If true the mesh generated by MC will be cleaned by unifying vertices that are almost coincident.",
        default=False,
    )
    discretize: BoolProperty(
        name="Discretize",
        description="If true the position of the intersected edge of the marching cube grid is not computed by linear interpolation, but it is placed in fixed middle position. As a consequence the resampled object will look severely aliased by a stairstep appearance. Useful only for simulating the output of 3D printing devices.",
        default=False,
    )
    multisample: BoolProperty(
        name="Multi-sample",
        description="If true the distance field is more accurately compute by multisampling the volume (7 sample for each voxel). Much slower but less artifacts.",
        default=False,
    )
    absdist: BoolProperty(
        name="Absolute Distance",
        description="If true a not signed distance field is computed. In this case you have to choose a not zero Offset and a double surface is built around the original surface, inside and outside. Is useful to convert thin floating surfaces into solid, thick meshes.",
        default=False,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
