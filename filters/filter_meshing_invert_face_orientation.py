from bpy.types import PropertyGroup
from bpy.props import BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_invert_face_orientation(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_invert_face_orientation"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    requires_polygons_disk = True

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    @classmethod
    def pre_process_parameters(cls, params, props):
        # A classe mestra precisa da chave 'selectedonly' para capturar os vértices selecionados na Viewport.
        # Mas a API do PyMeshLab para este filtro espera a chave 'onlyselected'. Fazemos o swap aqui.
        if "selectedonly" in params:
            params["onlyselected"] = params.pop("selectedonly")

    forceflip: BoolProperty(
        name="Force Flip",
        description="If selected, the normals will always be flipped; otherwise, the filter tries to set them outside.",
        default=True,
    )
    selectedonly: BoolProperty(
        name="Flip only selected faces",
        description="If selected, only selected faces will be affected.",
        default=False,
    )
