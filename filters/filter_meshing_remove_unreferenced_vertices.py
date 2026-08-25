from bpy.types import PropertyGroup
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_remove_unreferenced_vertices(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_remove_unreferenced_vertices"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Trava de Segurança: Força o motor C++ a utilizar o disco e o formato .obj na ida e na volta,
    # preservando Quads e N-gons originais e impedindo a triangulação destrutiva da memória (RAM).
    requires_polygons_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"
