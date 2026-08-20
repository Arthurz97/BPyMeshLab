import bpy
import bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty
from ..base_filter import MeshLabFilterBase


def update_polygonal_state(self, context):
    # O truque: Usa a flag nativa para pular ou executar a triangulação dinamicamente
    type(self).requires_polygons_disk = self.blender_polygonal

    # A correção da assimetria: Sincroniza o retorno (PLY ou OBJ) com a ida
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_generate_solid_wireframe(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_solid_wireframe"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    percentage_parameters = [
        "edgecylradius",
        "vertcylradius",
        "vertsphradius",
        "faceextheight",
        "faceextinset",
    ]

    extract_multiple_layers = True
    custom_name = "SolidWireframe"

    # Força a interface a bloquear a Engine e ficar para sempre em DISCO nativamente
    forces_disk_only = True
    requires_polygons_disk = True

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        if key == "blender_polygonal":
            return False

        if key == "edgecylradius":
            return not self.edgecylflag
        if key == "vertcylradius":
            return not self.vertcylflag
        if key == "vertsphradius":
            return not self.vertsphflag
        if key in ["faceextheight", "faceextinset"]:
            return not self.faceextflag

        if key == "cylindersidenum":
            return not self.edgecylflag and not self.vertcylflag

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
                    if hasattr(cls, "custom_name") and cls.custom_name:
                        context.active_object.name = f"{cls.custom_name}_bpymeshlab"
                    else:
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
                "Batch Solid Wireframe concluído"
                if len(original_objs) > 1
                else "Solid Wireframe concluído"
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

            if host_obj.name in bpy.data.objects:
                bpy.data.objects.remove(host_obj, do_unlink=True)

            if status == "FINISHED" and context.active_object:
                if hasattr(cls, "custom_name") and cls.custom_name:
                    context.active_object.name = f"{cls.custom_name}_bpymeshlab"
                else:
                    base_name = active_orig.name.split("_bpymeshlab")[0]
                    context.active_object.name = f"{base_name}_bpymeshlab"

            prefs.global_prev_mesh_action = original_action

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            return status, "Global Solid Wireframe gerado com sucesso."

    # --- PROPRIEDADES DE COMPORTAMENTO ---
    blender_batch: BoolProperty(
        name="Batch Process",
        description="If checked, processes each selected object individually. If unchecked, generates a single global solid wireframe englobing all objects.",
        default=False,
    )
    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, skips pre-triangulation. If unchecked, triangulates the mesh before generating the wireframe.",
        default=True,
        update=update_polygonal_state,
    )

    # --- PARÂMETROS DO FILTRO ---
    edgecylflag: BoolProperty(
        name="Edge -> Cyl.",
        description="If True all the edges are converted into cylinders.",
        default=True,
    )
    edgecylradius: FloatProperty(
        name="Edge Cylinder Rad. (abs and %)",
        description="The radius of the cylinder replacing each edge.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    vertcylflag: BoolProperty(
        name="Vertex -> Cyl.",
        description="If True all the vertices are converted into cylinders.",
        default=False,
    )
    vertcylradius: FloatProperty(
        name="Vertex Cylinder Rad. (abs and %)",
        description="The radius of the cylinder replacing each vertex.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    vertsphflag: BoolProperty(
        name="Vertex -> Sph.",
        description="If True all the vertices are converted into sphere.",
        default=True,
    )
    vertsphradius: FloatProperty(
        name="Vertex Sphere Rad. (abs and %)",
        description="The radius of the sphere replacing each vertex.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    faceextflag: BoolProperty(
        name="Face -> Prism",
        description="If True all the faces are converted into prism.",
        default=True,
    )
    faceextheight: FloatProperty(
        name="Face Prism Height (abs and %)",
        description="The Height of the prism that is substituted with each face.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.005,
        min=0.0,
    )
    faceextinset: FloatProperty(
        name="Face Prism Inset (abs and %)",
        description="The inset radius of each prism, e.g. how much it is moved toward the inside each vertex on the border of the prism.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.005,
        min=0.0,
    )
    edgefauxflag: BoolProperty(
        name="Ignore faux edges",
        description="If true only the Non-Faux edges will be considered for conversion.",
        default=True,
    )
    cylindersidenum: IntProperty(
        name="Cylinder Side",
        description="Number of sides of the cylinder (both edge and vertex).",
        default=16,
        min=3,
    )

    # --- SHADING FINAL ---
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
