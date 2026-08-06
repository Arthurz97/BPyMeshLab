import bpy
import numpy as np
import bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, FloatVectorProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_surface_reconstruction_screened_poisson(
    PropertyGroup, MeshLabFilterBase
):
    pymeshlab_filter = "generate_surface_reconstruction_screened_poisson"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    prefer_ply_disk = True

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        # Cascata de Esmaecimento do Pré-Filtro Embutido (Depende de ser Point Cloud)
        if key == "cn_enable":
            return not getattr(self, "blender_point_cloud", False)
        if key in ["cn_k", "cn_smoothiter", "cn_flipflag", "cn_viewpos"]:
            return not getattr(self, "blender_point_cloud", False) or not getattr(
                self, "cn_enable", False
            )

        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Remove os parâmetros embutidos e flags do Blender para que não sejam enviados ao C++
        for key in [
            "cn_enable",
            "cn_k",
            "cn_smoothiter",
            "cn_flipflag",
            "cn_viewpos",
            "blender_point_cloud",
        ]:
            if key in params:
                params.pop(key)

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        # Se for Modo Point Cloud e Compute Normals estiver ativo, injeta o filtro antes
        if props.blender_point_cloud and props.cn_enable:
            ms.apply_filter(
                "compute_normal_for_point_clouds",
                k=props.cn_k,
                smoothiter=props.cn_smoothiter,
                flipflag=props.cn_flipflag,
                viewpos=np.array(props.cn_viewpos, dtype=np.float64),
            )

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

                # Recálculo de normais automático via BMesh após a malha ser gerada
                if (
                    status == "FINISHED"
                    and context.active_object
                    and context.active_object.type == "MESH"
                ):
                    bm = bmesh.new()
                    bm.from_mesh(context.active_object.data)
                    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                    bm.to_mesh(context.active_object.data)
                    bm.free()
                    context.active_object.data.update()

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
                "Batch Screened Poisson concluído"
                if len(original_objs) > 1
                else "Screened Poisson concluído"
            )
            return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

        # MODO GLOBAL (HÍBRIDO: POINT CLOUD (JOIN) vs MESH (BOOLEAN MANIFOLD))
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
                        "A união falhou. O modo Global para Malhas exige que elas sejam fechadas (Manifold). Se forem Nuvens de Pontos, ative o 'Point Cloud Mode'.",
                    )

                # Limpeza dos temporários usados no Boolean
                for obj in temp_objs:
                    try:
                        if obj.name in bpy.data.objects:
                            bpy.data.objects.remove(obj, do_unlink=True)
                    except ReferenceError:
                        pass

                # Limpeza de Costura (Weld)
                bm = bmesh.new()
                bm.from_mesh(host_obj.data)
                bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.00001)
                bm.to_mesh(host_obj.data)
                bm.free()
                host_obj.data.update()

            bpy.data.collections.remove(temp_col)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            status, msg = super().apply_filter(context, props)

            # Recálculo de normais automático via BMesh após a malha ser gerada
            if (
                status == "FINISHED"
                and context.active_object
                and context.active_object.type == "MESH"
            ):
                bm = bmesh.new()
                bm.from_mesh(context.active_object.data)
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                bm.to_mesh(context.active_object.data)
                bm.free()
                context.active_object.data.update()

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
                "Global Surface Reconstruction (Screened Poisson) gerado com sucesso.",
            )

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
        name="Point Cloud Mode",
        description="Enable this if you are reconstructing from Point Clouds (vertices only) instead of dense meshes. This ensures normals are fused and preserved correctly across multiple objects.",
        default=False,
    )

    # -------------------------------------------------------------
    # PARÂMETROS INJETADOS DO COMPUTE NORMALS FOR POINT SETS
    # -------------------------------------------------------------
    cn_enable: BoolProperty(
        name="Compute Normals (Pre-Filter)",
        description="Automatically calculates point cloud normals before running the reconstruction. Required if the Point Cloud has no faces and no orientation.",
        default=False,
    )
    cn_k: IntProperty(
        name="Neighbour num",
        description="The number of neighbors used to estimate normals.",
        default=10,
        min=2,
    )
    cn_smoothiter: IntProperty(
        name="Smooth Iteration",
        description="The number of smoothing iteration done on the p used to estimate and propagate normals.",
        default=0,
        min=0,
    )
    cn_flipflag: BoolProperty(
        name="Flip normals w.r.t. viewpoint",
        description="If the 'viewpoint' (i.e. scanner position) is known, it can be used to disambiguate normals orientation.",
        default=False,
    )
    cn_viewpos: FloatVectorProperty(
        name="Viewpoint Pos.",
        description="The viewpoint position can be set by hand (i.e. getting the current viewpoint).",
        size=3,
        default=(0.0, 0.0, 0.0),
    )
    # -------------------------------------------------------------

    depth: IntProperty(
        name="Reconstruction Depth",
        description="This integer is the maximum depth of the tree that will be used for surface reconstruction. Running at depth d corresponds to solving on a voxel grid whose resolution is no larger than 2^d x 2^d x 2^d. Note that since the reconstructor adapts the octree to the sampling density, the specified reconstruction depth is only an upper bound. The default value for this parameter is 8.",
        default=8,
    )
    fulldepth: IntProperty(
        name="Adaptive Octree Depth",
        description="This integer specifies the depth beyond depth the octree will be adapted. At coarser depths, the octree will be complete, containing all 2^d x 2^d x 2^d nodes. The default value for this parameter is 5.",
        default=5,
    )
    cgdepth: IntProperty(
        name="Conjugate Gradients Depth",
        description="This integer is the depth up to which a conjugate-gradients solver will be used to solve the linear system. Beyond this depth Gauss-Seidel relaxation will be used. The default value for this parameter is 0.",
        default=0,
    )
    scale: FloatProperty(
        name="Scale Factor",
        description="This floating point value specifies the ratio between the diameter of the cube used for reconstruction and the diameter of the samples' bounding cube. The default value is 1.1.",
        default=1.1,
    )
    samplespernode: FloatProperty(
        name="Minimum Number of Samples",
        description="This floating point value specifies the minimum number of sample points that should fall within an octree node as the octree construction is adapted to sampling density. For noise-free samples, small values in the range [1.0 - 5.0] can be used. For more noisy samples, larger values in the range [15.0 - 20.0] may be needed to provide a smoother, noise-reduced, reconstruction. The default value is 1.5.",
        default=1.5,
    )
    pointweight: FloatProperty(
        name="Interpolation Weight",
        description="This floating point value specifies the importants that interpolation of the point samples is given in the formulation of the screened Poisson equation. The results of the original (unscreened) Poisson Reconstruction can be obtained by setting this value to 0. The default value for this parameter is 4.",
        default=4.0,
    )
    iters: IntProperty(
        name="Gauss-Seidel Relaxations",
        description="This integer value specifies the number of Gauss-Seidel relaxations to be performed at each level of the hierarchy. The default value for this parameter is 8.",
        default=8,
    )
    confidence: BoolProperty(
        name="Confidence Flag",
        description="Enabling this flag tells the reconstructor to use the quality as confidence information; this is done by scaling the unit normals with the quality values. When the flag is not enabled, all normals are normalized to have unit-length prior to reconstruction.",
        default=False,
    )
    preclean: BoolProperty(
        name="Pre-Clean",
        description="Enabling this flag force a cleaning pre-pass on the data removing all unreferenced vertices or vertices with null normals.",
        default=False,
    )
    threads: IntProperty(
        name="Number Threads",
        description="Maximum number of threads that the reconstruction algorithm can use.",
        default=16,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
