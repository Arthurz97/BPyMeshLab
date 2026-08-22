import bpy
import bmesh
import mathutils
import pymeshlab
from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty, PointerProperty
from ..base_filter import MeshLabFilterBase
from .. import utils


class MESHLAB_PG_generate_sampling_poisson_disk(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_sampling_poisson_disk"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True
    percentage_parameters = ["radius"]

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        # Cascata de esmaecimento baseada nas opções escolhidas
        if key == "refinemesh_object":
            return not self.refineflag
        if key == "bestsamplepool":
            return not self.bestsampleflag
        if key == "exactnumtolerance":
            return not self.exactnumflag
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Removemos o PointerProperty do Blender antes de enviar ao C++
        if "refinemesh_object" in params:
            del params["refinemesh_object"]

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        # Injeção dinâmica da malha secundária em RAM caso a flag seja verdadeira
        if props.refineflag and props.refinemesh_object:
            target_obj = props.refinemesh_object
            vertices, faces, _, v_scalars, v_normals = utils.blender_to_numpy(
                target_obj, extract_selection=False, extract_quality=True
            )
            mesh_kwargs = {"vertex_matrix": vertices, "face_matrix": faces}
            if v_scalars is not None:
                mesh_kwargs["v_scalar_array"] = v_scalars
            if v_normals is not None:
                mesh_kwargs["v_normals_matrix"] = v_normals

            m = pymeshlab.Mesh(**mesh_kwargs)
            ms.add_mesh(m)

            # Como a malha primária está no index 0, injetamos o ID 1 como alvo para o refinamento
            params["refinemesh"] = 1
        else:
            params["refinemesh"] = 0

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
                "Batch Poisson-disk Sampling concluído"
                if len(original_objs) > 1
                else "Poisson-disk Sampling concluído"
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

            return status, "Global Poisson-disk Sampling gerado com sucesso."

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
    montecarlorate: IntProperty(
        name="MonterCarlo OverSampling",
        description="The over-sampling rate that is used to generate the initial Montecarlo samples (e.g. if this parameter is K means thatK x poisson sample points will be used). The generated Poisson-disk samples are a subset of these initial Montecarlo samples. Larger this number slows the process but make it a bit more accurate.",
        default=20,
        min=1,
    )
    savemontecarlo: BoolProperty(
        name="Save Montecarlo",
        description="If true, it will generate an additional Layer with the montecarlo sampling that was pruned to build the poisson distribution.",
        default=False,
    )
    approximategeodesicdistance: BoolProperty(
        name="Approximate Geodesic Distance",
        description="If true Poisson Disc distances are computed using an approximate geodesic distance, e.g. an euclidean distance weighted by a function of the difference between the normals of the two points.",
        default=False,
    )
    subsample: BoolProperty(
        name="Base Mesh Subsampling",
        description="If true the original vertices of the base mesh are used as base set of points. In this case the SampleNum should be obviously much smaller than the original vertex number.\nNote that this option is very useful in the case you want to subsample a dense point cloud.",
        default=False,
    )
    refineflag: BoolProperty(
        name="Refine Existing Samples",
        description="If true the vertices of the below mesh are used as starting vertices, and they will utterly refined by adding more and more points until possible.",
        default=False,
    )
    refinemesh_object: PointerProperty(
        type=bpy.types.Object,
        name="Samples to be refined",
        description="Used only if the above option is checked. Mesh object used as starting vertices.",
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
    radiusvariance: FloatProperty(
        name="Radius Variance",
        description="The radius of the disk is allowed to vary between r and r*var. If this parameter is 1 the sampling is the same of the Poisson Disk Sampling.",
        default=1.0,
        min=0.0,
    )
