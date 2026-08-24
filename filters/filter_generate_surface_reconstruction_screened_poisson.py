import numpy as np
import bmesh
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, FloatVectorProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_generate_surface_reconstruction_screened_poisson(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "generate_surface_reconstruction_screened_poisson"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    prefer_ply_disk = True

    def is_property_disabled(self, key, context):
        if key == "blender_point_cloud":
            return len(context.selected_objects) <= 1 or getattr(
                self, "blender_batch", False
            )

        # Cascata de Esmaecimento do Pré-Filtro Embutido
        if key in ["cn_k", "cn_smoothiter", "cn_flipflag", "cn_viewpos"]:
            return not getattr(self, "cn_enable", False)

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def get_global_mode(cls, props):
        # Alterna entre fundir vértices (JOIN) ou rasterizar malha (BOOLEAN) dependendo do Checkbox
        return "JOIN" if getattr(props, "blender_point_cloud", False) else "BOOLEAN"

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
        # Injeta o cálculo de normais na memória antes do Poisson, se ativado na UI
        if getattr(props, "cn_enable", False):
            ms.apply_filter(
                "compute_normal_for_point_clouds",
                k=props.cn_k,
                smoothiter=props.cn_smoothiter,
                flipflag=props.cn_flipflag,
                viewpos=np.array(props.cn_viewpos, dtype=np.float64),
            )

    @classmethod
    def post_process_mesh(cls, context, obj):
        # Recálculo de normais automático via BMesh após a malha ser gerada
        if obj and obj.type == "MESH":
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

    blender_point_cloud: BoolProperty(
        name="Global Point Cloud (Join)",
        description="Enable this if you are reconstructing from Point Clouds (vertices only) instead of dense meshes. It uses 'Join' instead of 'Boolean Manifold', ensuring normals are fused and preserved correctly across multiple objects.",
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
