import numpy as np
from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty, FloatVectorProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_compute_normal_for_point_clouds(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase
):
    pymeshlab_filter = "compute_normal_for_point_clouds"
    requires_selection = True
    shade_flat = False
    remove_attributes = []

    batch_support = True
    global_mode = "NONE"

    @classmethod
    def pre_process_parameters(cls, params, props):

        # Converte o vetor nativo do Blender para o formato C++ exigido (numpy.ndarray)
        params["viewpos"] = np.array(props.viewpos, dtype=np.float64)

    k: IntProperty(
        name="Neighbour num",
        description="The number of neighbors used to estimate normals.",
        default=10,
        min=2,
    )
    smoothiter: IntProperty(
        name="Smooth Iteration",
        description="The number of smoothing iteration done on the p used to estimate and propagate normals.",
        default=0,
        min=0,
    )
    flipflag: BoolProperty(
        name="Flip normals w.r.t. viewpoint",
        description="If the 'viewpoint' (i.e. scanner position) is known, it can be used to disambiguate normals orientation, so that all the normals will be oriented in the same direction.",
        default=False,
    )
    viewpos: FloatVectorProperty(
        name="Viewpoint Pos.",
        description="The viewpoint position can be set by hand (i.e. getting the current viewpoint) or it can be retrieved from mesh camera, if the viewpoint position is stored there.",
        size=3,
        default=(0.0, 0.0, 0.0),
    )
