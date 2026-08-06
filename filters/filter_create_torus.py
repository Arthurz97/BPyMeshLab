import bpy
import math
import bmesh
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_torus(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_torus"
    requires_selection = False
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Lógica Condicional RAM vs DISCO para Quad/Tri
        engine = bpy.context.scene.meshlab_prefs.processing_engine
        if engine == "DISK":
            # Abortamos o filtro quad nativo do PyMeshLab no Disco para evitar artefatos.
            cls.post_filter_on_true = None
            cls.post_filter_on_false = None
        else:
            # Na Memória já nasce em Quads puros.
            cls.post_filter_on_true = None
            cls.post_filter_on_false = "meshing_poly_to_tri"

    @classmethod
    def apply_filter(cls, context, props):
        status, msg = super().apply_filter(context, props)

        engine = context.scene.meshlab_prefs.processing_engine

        # Intercepta com BMesh APENAS se for via DISCO e o usuário pedir Quad
        if (
            status == "FINISHED"
            and engine == "DISK"
            and getattr(props, "blender_quad", False)
        ):
            obj = context.view_layer.objects.active
            if obj and obj.type == "MESH":

                bm = bmesh.new()
                bm.from_mesh(obj.data)

                # Tris to Quads idêntico ao do Cone
                bmesh.ops.join_triangles(
                    bm,
                    faces=bm.faces,
                    angle_face_threshold=math.radians(40.0),
                    angle_shape_threshold=math.radians(60.01),
                    topology_influence=2.0,
                )

                bm.to_mesh(obj.data)
                bm.free()
                obj.data.update()

        return status, msg

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
