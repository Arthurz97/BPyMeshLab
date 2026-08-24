import numpy as np
import bmesh
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty, FloatVectorProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_generate_surface_reconstruction_ball_pivoting(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "generate_surface_reconstruction_ball_pivoting"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face", "UVMap"]
    percentage_parameters = ["ballradius"]
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
        # Injeta o cálculo de normais na memória antes da reconstrução, se ativado na UI
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

    ballradius: FloatProperty(
        name="Pivoting Ball radius (0 autoguess) (abs and %)",
        description="The radius of the ball pivoting (rolling) over the set of points. Gaps that are larger than the ball radius will not be filled; similarly the small pits that are smaller than the ball radius will be filled.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.0,
        min=0.0,
    )
    clustering: FloatProperty(
        name="Clustering radius (% of ball radius)",
        description="To avoid the creation of too small triangles, if a vertex is found too close to a previous one, it is clustered/merged with it.",
        default=20.0,
    )
    creasethr: FloatProperty(
        name="Angle Threshold (degrees)",
        description="If we encounter a crease angle that is too large we should stop the ball rolling.",
        default=90.0,
    )
    deletefaces: BoolProperty(
        name="Delete initial set of faces",
        description="if true all the initial faces of the mesh are deleted and the whole surface is rebuilt from scratch. Otherwise the current faces are used as a starting point. Useful if you run the algorithm multiple times with an increasing ball radius.",
        default=False,
    )
