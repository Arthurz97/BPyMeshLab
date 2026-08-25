from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_re_orient_faces_by_geometry(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_re_orient_faces_by_geometry"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Não forçamos requires_polygons_disk, pois este filtro trava com polígonos na API

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    @classmethod
    def apply_filter(cls, context, props):
        # --- VALIDAÇÃO TOPOLÓGICA ESTRITA (FAIL FAST) ---
        # O Embree3 na API crua do PyMeshLab entra em loop infinito (Memory Leak) se receber Quads/Ngons neste filtro.
        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        for obj in original_objs:
            has_polygons = any(len(p.vertices) > 3 for p in obj.data.polygons)
            if has_polygons:
                return (
                    "CANCELLED",
                    f"Filtro abortado: A malha '{obj.name}' contém Quads/Ngons. "
                    "O algoritmo de Raytracing deste filtro exige uma malha 100% triangulada para não travar a API.",
                )

        # Se passou na trava, segue o fluxo padronizado da Base
        return super().apply_filter(context, props)

    rays: IntProperty(
        name="Number of rays",
        description="The number of rays shoot from the barycenter of the face. The higher the number the higher the definition of the normal analysis but at the cost of the calculation time",
        default=64,
        min=1,
    )
    parity_sampling: BoolProperty(
        name="Parity Sampling",
        description="If checked, the normal analysis will be performed using the parity sampling algorithm. This algorithm is slower than the visibility sampling but works better with some models",
        default=False,
    )
