import math
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    type(self).requires_polygons_disk = self.blender_polygonal
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_meshing_cut_along_crease_edges(
    PropertyGroup, MeshLabBatchGlobalProps, MeshLabSmoothProp, MeshLabFilterBase
):
    pymeshlab_filter = "meshing_cut_along_crease_edges"
    requires_selection = True
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]

    requires_polygons_disk = True
    prefer_ply_disk = False
    angle_parameters = ["angledeg"]

    # Controles de Arquitetura herdados da base
    batch_support = True
    global_mode = "NONE"

    @classmethod
    def apply_filter(cls, context, props):
        original_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]

        # --- VALIDAÇÃO TOPOLÓGICA (FAIL FAST) ---
        for obj in original_objs:
            if len(obj.data.polygons) == 0:
                return (
                    "CANCELLED",
                    f"A malha '{obj.name}' não possui faces (polígonos) para ser cortada.",
                )

        return super().apply_filter(context, props)

    # --- PARÂMETROS DA INTERFACE ---
    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, forces the engine to Disk (I/O) to keep Quads/Ngons using OBJ format. If unchecked, allows Memory (RAM) or Disk (using PLY).",
        default=True,
        update=update_polygonal_state,
    )

    angledeg: FloatProperty(
        name="Crease Angle",
        description="If the angle between the normals of two adjacent faces is larger that this threshold the edge is considered a creased and the mesh is cut along it.",
        default=math.radians(90.0),
        subtype="ANGLE",
    )
