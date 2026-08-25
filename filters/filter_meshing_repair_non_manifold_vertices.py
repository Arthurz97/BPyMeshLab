from bpy.types import PropertyGroup
from bpy.props import FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_meshing_repair_non_manifold_vertices(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_repair_non_manifold_vertices"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    vertdispratio: FloatProperty(
        name="Vertex Displacement Ratio",
        description="This parameter denote the ratio ⍺ of displacement of a vertex. When a vertex v is split, it is moved towards the barycenter b of the FF connected faces sharing it of a (v-b)*⍺. When ⍺ is zero vertex is not displaced. When ⍺ is 0.5 the new vertex is half away toward the barycenter of the face. Reasonable values are in the [0 .. 0.1] range.",
        default=0.0,
        min=0.0,
        max=1.0,
        soft_max=0.1,
    )
