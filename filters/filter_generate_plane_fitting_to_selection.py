import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, IntProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_generate_plane_fitting_to_selection(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "generate_plane_fitting_to_selection"
    requires_selection = True
    ignore_selection_count = True
    ignores_modifiers = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    custom_name = "FittedPlane"

    @classmethod
    def pre_process_parameters(cls, params, props):
        params["orientation"] = int(props.orientation)
        if "selectedonly" in params:
            del params["selectedonly"]

        # Lógica Condicional RAM vs DISCO para Quad/Tri
        engine = bpy.context.scene.meshlab_prefs.processing_engine
        if engine == "DISK":
            # No Disco, o PyMeshLab quebra em Tris. Reconstruímos os Quads se o usuário pedir.
            cls.post_filter_on_true = "meshing_tri_to_quad_dominant"
            cls.post_filter_on_false = None
        else:
            # Na Memória, já nasce em Quads. Quebramos em Tris se a opção for desmarcada.
            cls.post_filter_on_true = None
            cls.post_filter_on_false = "meshing_poly_to_tri"

    # Checkbox de Batch
    blender_batch: BoolProperty(
        name="Batch Process",
        description="If checked, processes each valid object individually. If unchecked, fits a single plane to all selected faces globally.",
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

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = context.selected_objects[:]
        valid_objs = []

        for obj in original_objs:
            if obj.type == "MESH":
                if any(p.select for p in obj.data.polygons):
                    valid_objs.append(obj)

        if not valid_objs:
            return (
                "CANCELLED",
                "Nenhum dos objetos avaliados possui faces ativamente selecionadas.",
            )

        is_batch = getattr(props, "blender_batch", False)
        preserve = getattr(props, "blender_preserve_transforms", False)

        prefs = context.scene.meshlab_prefs
        original_action = prefs.global_prev_mesh_action
        prefs.global_prev_mesh_action = "KEEP"

        overall_status = "FINISHED"
        error_msg = ""

        # MODO BATCH ou MODO ÚNICO
        if is_batch or len(valid_objs) == 1:
            for obj in valid_objs:
                bpy.ops.object.select_all(action="DESELECT")

                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                context.collection.objects.link(new_obj)

                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                new_obj.modifiers.clear()

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
                for obj in valid_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if overall_status != "FINISHED":
                return overall_status, error_msg

            msg_end = (
                "Batch Plane Fit concluído"
                if len(valid_objs) > 1
                else "Plane Fit concluído"
            )
            return (
                overall_status,
                f"{msg_end} em {len(valid_objs)} objeto(s).",
            )

        # MODO GLOBAL
        else:
            active_idx = 0
            if context.active_object in valid_objs:
                active_idx = valid_objs.index(context.active_object)

            bpy.ops.object.select_all(action="DESELECT")
            temp_objs = []

            for obj in valid_objs:
                new_obj = obj.copy()
                new_obj.data = obj.data.copy()
                context.collection.objects.link(new_obj)

                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                context.view_layer.objects.active = new_obj

                new_obj.modifiers.clear()
                bpy.ops.object.transform_apply(
                    location=False, rotation=True, scale=True
                )

                temp_objs.append(new_obj)

            bpy.ops.object.select_all(action="DESELECT")
            for obj in temp_objs:
                obj.select_set(True)

            context.view_layer.objects.active = temp_objs[active_idx]
            bpy.ops.object.join()

            temp_merged = context.active_object

            status, msg = super().apply_filter(context, props)

            if temp_merged:
                try:
                    if temp_merged.name in bpy.data.objects:
                        bpy.data.objects.remove(temp_merged, do_unlink=True)
                except ReferenceError:
                    pass

            for obj in temp_objs:
                try:
                    if obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                except ReferenceError:
                    pass

            prefs.global_prev_mesh_action = original_action

            if status == "FINISHED" and original_action in ["HIDE", "DELETE"]:
                for obj in valid_objs:
                    if original_action == "HIDE":
                        obj.hide_set(True)
                    elif original_action == "DELETE":
                        bpy.data.objects.remove(obj, do_unlink=True)

            if status != "FINISHED":
                return status, msg

            return status, "Global Plane gerado englobando todas as seleções válidas."

    selectedonly: BoolProperty(
        default=True,
        options={"HIDDEN"},
    )
    extent: FloatProperty(
        name="Extent (w.r.t selection)",
        description="How large is the plane, with respect to the size of the selection: 1.0 means as large as the selection, 1.1 means 10% larger then the selection.",
        default=1.0,
        min=0.001,
    )
    subdiv: IntProperty(
        name="Plane XY subdivisions",
        description="Subdivision steps of plane borders.",
        default=3,
        min=0,
    )
    hasuv: BoolProperty(
        name="UV parametrized",
        description="The created plane has an UV parametrization.",
        default=False,
    )
    orientation: bpy.props.EnumProperty(
        name="Plane orientation",
        description="Orientation of the fitting plane.",
        items=[
            (
                "0",
                "quasi-Straight Fit",
                "The fitting plane will be oriented (as much as possible) straight with the axeses.",
            ),
            (
                "1",
                "Best Fit",
                "The fitting plane will be oriented and sized trying to best fit to the selected area.",
            ),
            (
                "2",
                "XZ Parallel",
                "The fitting plane will be oriented with a side parallel with the chosen plane. WARNING: do not use if the selection is exactly parallel to a plane.",
            ),
            ("3", "YZ Parallel", "Parallel to YZ."),
            ("4", "YX Parallel", "Parallel to YX."),
        ],
        default="0",
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
