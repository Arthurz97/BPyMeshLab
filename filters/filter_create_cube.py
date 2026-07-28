import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_cube(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_cube"
    requires_selection = False
    shade_flat = True
    remove_attributes = [
        "material_index",
        "sharp_face",
        "UVMap",
        "custom_normal",
        "sharp_edge",
    ]

    # Pós-processamento nativo C++ (Lógica invertida)
    post_filter_on_true = None  # Se Quad=True, deixa como está (o cubo já é Quad)
    post_filter_on_false = "meshing_poly_to_tri"  # Se Quad=False, quebra em triângulos

    size: FloatProperty(
        name="Size",
        description="Scales the new mesh.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.001,
        max=5000.0,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
