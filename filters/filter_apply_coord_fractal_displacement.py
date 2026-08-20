import bpy
import mathutils
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, EnumProperty
from ..base_filter import MeshLabFilterBase


def update_polygonal_state(self, context):
    # Dinamiza as flags da Classe Mestra em tempo real ao clicar no checkbox
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


def enforce_batch_true(self, context):
    if not self.blender_batch:
        self.blender_batch = True


class MESHLAB_PG_apply_coord_fractal_displacement(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "apply_coord_fractal_displacement"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    percentage_parameters = ["maxheight"]

    # Estados iniciais sincronizados com o default=True do checkbox blender_polygonal
    requires_polygons_disk = True
    prefer_ply_disk = False

    def is_property_disabled(self, key, context):
        if key == "blender_batch":
            return len(context.selected_objects) <= 1
        if key == "blender_preserve_transforms":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )
        if key == "blender_polygonal":
            return False
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Converte o Enum da interface do Blender para o Int exigido pelo C++
        params["algorithm"] = int(props.algorithm)

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # Processamento iterativo (Batch) forçado, sem Modo Global
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
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

            status, msg = super().apply_filter(context, props)

            if preserve and status == "FINISHED" and context.active_object:
                temp_matrix = mathutils.Matrix.Translation(original_matrix.translation)
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
            "Batch Fractal Displacement concluído"
            if len(original_objs) > 1
            else "Fractal Displacement concluído"
        )
        return overall_status, f"{msg_end} em {len(original_objs)} objeto(s)."

    # --- PARÂMETROS DA INTERFACE ---

    blender_batch: BoolProperty(
        name="Batch Process",
        description="Processes each selected object individually.",
        default=True,
        update=enforce_batch_true,
    )
    blender_preserve_transforms: BoolProperty(
        name="Preserve Transforms",
        description="Restores the original Rotation and Scale to the final object. If unchecked, applied transforms are used.",
        default=False,
    )
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    maxheight: FloatProperty(
        name="Max height (abs and %)",
        description="Defines the maximum height for the perturbation.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0346,
        min=0.0,
    )
    scale: FloatProperty(
        name="Scale factor",
        description="Scales the fractal perturbation in and out. Values larger than 1 mean zoom out; values smaller than one mean zoom in.",
        default=1.0,
        min=0.0,
        max=10.0,
    )
    smoothingsteps: IntProperty(
        name="Normals smoothing steps",
        description="Face normals will be smoothed to make the perturbation more homogeneous. This parameter represents the number of smoothing steps.",
        default=5,
        min=0,
    )
    seed: IntProperty(
        name="Seed",
        description="By varying this seed, the terrain morphology will change. Don't change the seed if you want to refine the current terrain morphology by changing the other parameters.",
        default=2,
    )
    algorithm: EnumProperty(
        name="Algorithm",
        description="The algorithm with which the fractal terrain will be generated.",
        items=[
            ("0", "fBM (fractal Brownian Motion)", ""),
            ("1", "Standard multifractal", ""),
            ("2", "Heterogeneous multifractal", ""),
            ("3", "Hybrid multifractal terrain", ""),
            ("4", "Ridged multifractal terrain", ""),
        ],
        default="4",
    )
    octaves: FloatProperty(
        name="Octaves",
        description="The number of Perlin noise frequencies that will be used to generate the terrain. Reasonable values are in range [2,9].",
        default=8.0,
        min=1.0,
        max=20.0,
    )
    lacunarity: FloatProperty(
        name="Lacunarity",
        description="The gap between noise frequencies. This parameter is used in conjunction with fractal increment to compute the spectral weights that contribute to the noise in each octave.",
        default=4.0,
    )
    fractalincrement: FloatProperty(
        name="Fractal increment",
        description="This parameter defines how rough the generated terrain will be. The range of reasonable values changes according to the used algorithm, however you can choose it in range [0.2, 1.5].",
        default=0.2,
    )
    offset: FloatProperty(
        name="Offset",
        description="This parameter controls the multifractality of the generated terrain. If offset is low, then the terrain will be smooth.",
        default=0.9,
    )
    gain: FloatProperty(
        name="Gain",
        description="Ignored in all the algorithms except the ridged one. This parameter defines how hard the terrain will be.",
        default=2.5,
    )
    saveasquality: BoolProperty(
        name="Save as vertex quality",
        description="Saves the perturbation value as vertex quality (accessible via Geometry/Shader nodes).",
        default=False,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
