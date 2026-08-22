import bpy
import numpy as np
import bmesh
import mathutils
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, FloatVectorProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_surface_reconstruction_vcg(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_surface_reconstruction_vcg"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    percentage_parameters = ["voxsize"]
    prefer_ply_disk = True

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        # Cascata de Esmaecimento do Pré-Filtro Embutido
        if key == "cn_enable":
            return not getattr(self, "mergecolor", False)
        if key in ["cn_k", "cn_smoothiter", "cn_flipflag", "cn_viewpos"]:
            return not getattr(self, "mergecolor", False) or not getattr(
                self, "cn_enable", False
            )

        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Remove os parâmetros embutidos da lista principal para que a Classe Mestra não os envie ao VCG por engano
        for key in ["cn_enable", "cn_k", "cn_smoothiter", "cn_flipflag", "cn_viewpos"]:
            if key in params:
                params.pop(key)

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        # Se Vertex Splatting e Compute Normals estiverem ativos, injeta o filtro antes do VCG
        if props.mergecolor and props.cn_enable:

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
                "Batch Surface Reconstruction: VCG concluído"
                if len(original_objs) > 1
                else "Surface Reconstruction: VCG concluído"
            )
            return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

        # MODO GLOBAL (BOOLEAN MANIFOLD PARA MALHAS / JOIN PARA POINT CLOUDS)
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

            if getattr(props, "mergecolor", False):
                # ROTA 1: VERTEX SPLATTING (Nuvens de Pontos) -> Apenas JOIN
                bpy.ops.object.select_all(action="DESELECT")
                for obj in temp_objs:
                    obj.select_set(True)

                context.view_layer.objects.active = temp_objs[active_idx]
                bpy.ops.object.join()
                host_obj = context.active_object

                # RESGATE: Vincula o objeto fundido à coleção principal para que ele não desapareça quando a temp_col for deletada
                context.collection.objects.link(host_obj)
            else:
                # ROTA 2: RASTERIZAÇÃO (Malhas) -> BOOLEAN + WELD
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
                        "A união falhou. O modo Global sem Vertex Splatting exige que as malhas cruzadas sejam fechadas (Manifold).",
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

            return status, "Global Surface Reconstruction (VCG) gerado com sucesso."

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

    voxsize: FloatProperty(
        name="Voxel Side",
        description="Voxel Side.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0346,
        min=0.0001,
    )
    subdiv: IntProperty(
        name="SubVol Splitting",
        description="The level of recursive splitting of the subvolume reconstruction process. A value of '3' means that a 3x3x3 regular space subdivision is created and the reconstruction process generate 8 matching meshes. It is useful for reconsruction objects at a very high resolution. Default value (1) means no splitting.",
        default=1,
        min=1,
    )
    geodesic: FloatProperty(
        name="Geodesic Weighting",
        description="The influence of each range map is weighted with its geodesic distance from the borders. In this way when two (or more ) range maps overlaps their contribution blends smoothly hiding possible misalignments.",
        default=2.0,
    )
    openresult: BoolProperty(
        name="Show Result",
        description="if not checked the result is only saved into the current directory.",
        default=True,
        options={"HIDDEN"},
    )
    smoothnum: IntProperty(
        name="Volume Laplacian iter",
        description="How many volume smoothing step are performed to clean out the eventually noisy borders.",
        default=1,
        min=0,
    )
    widenum: IntProperty(
        name="Widening",
        description="How many voxel the field is expanded. Larger this value more holes will be filled.",
        default=3,
        min=0,
    )
    mergecolor: BoolProperty(
        name="Vertex Splatting",
        description="This option use a different way to build up the volume, instead of using rasterization of the triangular face it splat the vertices into the grids. It works under the assumption that you have at least one sample for each voxel of your reconstructed volume.",
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

    simplification: BoolProperty(
        name="Post Merge simplification",
        description="After the merging an automatic simplification step is performed.",
        default=False,
    )
    normalsmooth: IntProperty(
        name="PreSmooth iter",
        description="How many times, before converting meshes into volume, the normal of the surface are smoothed. It is useful only to get more smooth expansion in case of noisy borders.",
        default=3,
        min=0,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
