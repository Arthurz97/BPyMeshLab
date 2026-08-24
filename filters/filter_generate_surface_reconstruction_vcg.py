import numpy as np
import bmesh
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, FloatVectorProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_generate_surface_reconstruction_vcg(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "generate_surface_reconstruction_vcg"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    percentage_parameters = ["voxsize"]
    prefer_ply_disk = True

    def is_property_disabled(self, key, context):
        # Cascata de Esmaecimento do Pré-Filtro Embutido
        if key == "cn_enable":
            return not getattr(self, "mergecolor", False)
        if key in ["cn_k", "cn_smoothiter", "cn_flipflag", "cn_viewpos"]:
            return not getattr(self, "mergecolor", False) or not getattr(
                self, "cn_enable", False
            )

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def get_global_mode(cls, props):
        # No VCG, a flag "mergecolor" atua como o Vertex Splatting (Point Cloud / JOIN)
        return "JOIN" if getattr(props, "mergecolor", False) else "BOOLEAN"

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
    def post_process_mesh(cls, context, obj):
        # Recálculo de normais automático via BMesh após a malha ser gerada
        if obj and obj.type == "MESH":
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()

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
