from bpy.types import PropertyGroup
from bpy.props import IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_generate_voronoi_atlas_parametrization(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "generate_voronoi_atlas_parametrization"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    requires_uv_disk = True
    extract_multiple_layers = True
    layer_mapping = {1: "VoroAtlas"}

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    @classmethod
    def apply_filter(cls, context, props):
        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]

        # --- VALIDAÇÃO DE UV (FAIL FAST) ---
        for obj in original_objs:
            if obj.data.uv_layers:
                return (
                    "CANCELLED",
                    f"A malha '{obj.name}' já possui coordenadas UV. "
                    "O Voronoi Atlas falhará na memória C++. Remova os UV Maps antes de aplicar.",
                )

        return super().apply_filter(context, props)

    regionnum: IntProperty(
        name="Approx. Region Num",
        description="An estimation of the number of regions that must be generated. Smaller regions could lead to parametrizations with smaller distortion.",
        default=10,
        min=0,
    )
    overlapflag: BoolProperty(
        name="Overlap",
        description="If checked the resulting parametrization will be composed by overlapping regions, e.g. the resulting mesh will have duplicated faces: each region will have a ring of ovelapping duplicate faces that will ensure that border regions will be parametrized in the atlas twice. This is quite useful for building mipmap robust atlases.",
        default=False,
    )
