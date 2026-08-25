from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_hc_laplacian_smoothing(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_hc_laplacian_smoothing"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    requires_polygons_disk = True
    prefer_ply_disk = False

    # Controles de Arquitetura
    batch_support = True

    def is_property_disabled(self, key, context):
        if key == "blender_polygonal":
            return False

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Este filtro não aceita parâmetros no C++. Removemos 'iterations' antes de enviar.
        if "iterations" in params:
            params.pop("iterations")

    @classmethod
    def pre_invoke_filters(cls, ms, params, props):
        # A Classe Mestra sempre executa o filtro uma vez no final do ciclo.
        # Por isso, subtraímos 1 do total e rodamos o resto aqui na memória C++ antecipadamente.
        for _ in range(props.iterations - 1):
            ms.apply_filter(cls.pymeshlab_filter, **params)

    # --- PARÂMETROS DA INTERFACE ---
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    iterations: IntProperty(
        name="Iterations",
        description="Number of times the algorithm is iterated.",
        default=1,
        min=1,
    )
