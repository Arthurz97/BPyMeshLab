from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_generate_simplified_point_cloud(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps
):
    pymeshlab_filter = "generate_simplified_point_cloud"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    percentage_parameters = ["radius"]

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        # Delega as travas de Batch/Transform para a Classe Mestra
        if super().is_property_disabled(key, context):
            return True

        # Trava exclusiva deste filtro
        if key == "blender_point_cloud":
            return len(context.selected_objects) <= 1 or getattr(
                self, "blender_batch", False
            )

        # Lógica UI do PyMeshLab original
        radius_active = getattr(self, "radius", 0.0) > 0.0

        if key in ["samplenum", "exactnumflag", "exactnumtolerance"]:
            return radius_active

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
        # Modo Global Híbrido: define o tipo de união dinamicamente antes de repassar para a Classe Mestra
        cls.global_mode = (
            "JOIN" if getattr(props, "blender_point_cloud", False) else "BOOLEAN"
        )
        return super().apply_filter(context, props)

    # =================================================================
    # PARÂMETROS DA INTERFACE
    # =================================================================
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
