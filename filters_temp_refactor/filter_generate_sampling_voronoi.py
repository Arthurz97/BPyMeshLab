import bpy
import bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_sampling_voronoi(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_sampling_voronoi"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    # Feature Flag: Avisa a Classe Mestra para extrair a malha original processada + as 2 camadas extras (Mesh e Polyline)
    extract_multiple_layers = True
    layer_mapping = {1: "Voronoi_Mesh", 2: "Voronoi_Polyline"}

    @classmethod
    def pre_process_parameters(cls, params, props):
        # O PyMeshLab recebe as opções de ENUM como Inteiros neste filtro
        params["colorstrategy"] = int(props.colorstrategy)
        params["distancetype"] = int(props.distancetype)
        params["relaxtype"] = int(props.relaxtype)

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        # Cascata de Esmaecimento: Desativa os parâmetros dependentes se o Preprocessing estiver desligado
        if key in ["refinefactor", "perturbprobability", "perturbamount"]:
            return not getattr(self, "preprocessflag", False)

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

                if preserve and status == "FINISHED":
                    # Restaura as matrizes para todos os objetos gerados pelas múltiplas camadas
                    for gen_obj in context.selected_objects:
                        if gen_obj.type == "MESH":
                            temp_matrix = mathutils.Matrix.Translation(
                                original_matrix.translation
                            )
                            gen_obj.data.transform(
                                original_matrix.inverted() @ temp_matrix
                            )
                            gen_obj.matrix_world = original_matrix
                            gen_obj.rotation_euler = original_rotation
                            gen_obj.scale = original_scale

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
                "Batch Voronoi Sampling concluído"
                if len(original_objs) > 1
                else "Voronoi Sampling concluído"
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

            prefs.global_prev_mesh_action = original_action

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in original_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if status != "FINISHED":
                return status, msg

            return status, "Global Voronoi Sampling gerado com sucesso."

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

    # PARÂMETROS DO FILTRO VORONOI SAMPLING
    iternum: IntProperty(
        name="Iteration",
        description="Number of iterations.",
        default=10,
        min=0,
    )
    samplenum: IntProperty(
        name="Sample Num.",
        description="Number of samples.",
        default=10,
        min=1,
    )
    radiusvariance: FloatProperty(
        name="Radius Variance",
        description="The distance metric will vary along the surface between 1/x and x, linearly according to the scalar field specified by the quality.",
        default=1.0,
        min=0.0,
    )
    colorstrategy: EnumProperty(
        name="Color Strategy",
        description="Select the coloring strategy for the samples.",
        items=[
            ("0", "None", ""),
            ("1", "Seed Distance", ""),
            ("2", "Border Distance", ""),
            ("3", "Region Area", ""),
        ],
        default="1",
    )
    distancetype: EnumProperty(
        name="Distance Type",
        description="Select the distance type.",
        items=[
            ("0", "Euclidean", ""),
            ("1", "Quality Weighted", ""),
            ("2", "Anisotropic", ""),
        ],
        default="0",
    )
    preprocessflag: BoolProperty(
        name="Preprocessing",
        description="Enable/Disable preprocessing.",
        default=False,
    )
    refinefactor: IntProperty(
        name="Refinement Factor",
        description="To ensure good convergence the mesh should be more complex than the voronoi partitioning. This number affect how much the mesh is refined according to the required number of samples.",
        default=10,
        min=1,
    )
    perturbprobability: FloatProperty(
        name="Perturbation Probability",
        description="To ensure good convergence the mesh should be more complex than the voronoi partitioning. This number affect how much the mesh is refined according to the required number of samples.",
        default=0.0,
        min=0.0,
        max=1.0,
    )
    perturbamount: FloatProperty(
        name="Perturbation Amount",
        description="To ensure good convergence the mesh should be more complex than the voronoi partitioning. This number affect how much the mesh is refined according to the required number of samples.",
        default=0.001,
        min=0.0,
    )
    randomseed: IntProperty(
        name="Random seed",
        description="To ensure repeatability you can specify the random seed used. If 0 the random seed is tied to the current clock.",
        default=0,
        min=0,
    )
    relaxtype: EnumProperty(
        name="Relax Type",
        description="At each relaxation step we search for each voronoi region the new position of the seed.",
        items=[
            (
                "0",
                "Geodesic",
                "The seed is placed onto the vertex that maximize the geodesic distance from the border of the region.",
            ),
            (
                "1",
                "Squared Distance",
                "The seed is placed in the vertex that minimize the squared sum of the distances from all the pints of the region.",
            ),
            (
                "2",
                "Restricted",
                "The seed is placed in the barycenter of current voronoi region. Even if it is outside the surface. During the relaxation process the seed is free to move off the surface in a continuous way. Re-association to vertex is done at the end.",
            ),
        ],
        default="1",
    )
