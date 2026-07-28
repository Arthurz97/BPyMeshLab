import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_torus(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_torus"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Lógica Condicional RAM vs DISCO para Quad/Tri
        engine = bpy.context.scene.meshlab_prefs.processing_engine
        if engine == "DISK":
            cls.post_filter_on_true = "meshing_tri_to_quad_dominant"
            cls.post_filter_on_false = None
        else:
            cls.post_filter_on_true = None
            cls.post_filter_on_false = "meshing_poly_to_tri"

    hradius: FloatProperty(
        name="Horizontal Radius",
        description="Radius of the whole horizontal ring of the torus",
        subtype="DISTANCE",
        unit="LENGTH",
        default=3.0,
        min=0.001,
    )
    vradius: FloatProperty(
        name="Vertical Radius",
        description="Radius of the vertical section of the ring",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.001,
    )
    hsubdiv: IntProperty(
        name="Horizontal Subdivision",
        description="Subdivision step of the ring",
        default=24,
        min=3,
    )
    vsubdiv: IntProperty(
        name="Vertical Subdivision",
        description="Number of sides of the polygonal approximation of the torus section",
        default=12,
        min=3,
    )
    blender_smooth: BoolProperty(
        name="Shade Smooth",
        description="Render and display faces smooth, using interpolated vertex normals.",
        default=False,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
