import bpy
import bmesh
from bpy.types import PropertyGroup
from bpy.props import IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps


class MESHLAB_PG_meshing_surface_subdivision_doo_sabin(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_surface_subdivision_doo_sabin"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    # Fundamental para o Doo Sabin, que constrói n-gons em vértices extraordinários (ex: triângulos nas pontas de um cubo)
    requires_polygons_disk = True

    batch_support = True
    global_mode = "NONE"

    @classmethod
    def apply_filter(cls, context, props):
        if context.active_object and context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not original_objs:
            return "CANCELLED", "Selecione pelo menos um objeto do tipo malha (Mesh)."

        # --- VALIDAÇÃO TOPOLÓGICA ESTRITA (ABORTO TOTAL) ---
        # O algoritmo Doo Sabin entra em loop ou crasha (Segfault) com qualquer geometria non-manifold.
        # Checamos todos os objetos antes do processamento (Fail Fast).
        for obj in original_objs:
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            # Busca otimizada: e.is_manifold garante EXATAMENTE 2 faces por aresta.
            # v.is_manifold garante que não há vértices 'bow-tie' (gravata-borboleta).
            has_error = any(not e.is_manifold for e in bm.edges) or any(
                not v.is_manifold for v in bm.verts
            )
            bm.free()

            if has_error:
                return (
                    "CANCELLED",
                    f"A operação falhou. O objeto '{obj.name}' não é estritamente Manifold (possui buracos, faces internas ou vértices soltos).",
                )

        return super().apply_filter(context, props)

    iterations: IntProperty(
        name="Iterations",
        description="Number of times the model is subdivided.",
        default=2,
        min=0,
    )
