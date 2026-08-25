from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    # Dinamiza as flags da Classe Mestra em tempo real ao clicar no checkbox
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_apply_coord_random_displacement(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "apply_coord_random_displacement"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    # Adicionamos displacement na lista de porcentagem para ser enviado como PureValue
    percentage_parameters = ["displacement"]

    # Estados iniciais sincronizados com o default=True do checkbox blender_polygonal
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

    # --- PARÂMETROS DA INTERFACE ---
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    updatenormals: BoolProperty(
        name="Recompute normals",
        description="Toggle the recomputation of the normals after the random displacement. If disabled the face normals will remains unchanged resulting in a visually pleasant effect.",
        default=True,
    )
    displacement: FloatProperty(
        name="Max displacement (abs and %)",
        description="The vertex are displaced of a vector whose norm is bounded by this value.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    randomseed: IntProperty(
        name="Random Seed",
        description="The seed used to generate random values. If seed is zero no random seed is used.",
        default=0,
    )
