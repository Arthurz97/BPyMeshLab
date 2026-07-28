import bpy
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, IntProperty, BoolProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_cone(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_cone"
    requires_selection = False
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge"]

    # Removemos as regras C++ (post_filter_on_true) pois o algoritmo do PyMeshLab erra a topologia.
    @classmethod
    def apply_filter(cls, context, props):
        # 1. Executa a geração original do PyMeshLab em triângulos chamando a classe base
        status, msg = super().apply_filter(context, props)

        # 2. Intercepta o resultado no Blender para aplicar a topologia Quad via BMesh
        if status == "FINISHED" and getattr(props, "blender_quad", False):
            obj = context.view_layer.objects.active
            if obj and obj.type == "MESH":
                import bmesh
                import math

                bm = bmesh.new()
                bm.from_mesh(obj.data)

                # Tris to Quads (Limite de 40 graus e influência topológica = 2.0)
                # Mantém as laterais em Quad e poupa os polos (base/topo) sem destruir a curvatura
                bmesh.ops.join_triangles(
                    bm,
                    faces=bm.faces,
                    angle_face_threshold=math.radians(40.0),
                    angle_shape_threshold=math.radians(40.0),
                    topology_influence=2.0,
                )

                # Devolve a malha corrigida para o objeto
                bm.to_mesh(obj.data)
                bm.free()
                obj.data.update()

        return status, msg

    r0: FloatProperty(
        name="Radius 1",
        description="Radius of the bottom circumference",
        subtype="DISTANCE",
        unit="LENGTH",
        default=1.0,
        min=0.0,
    )
    r1: FloatProperty(
        name="Radius 2",
        description="Radius of the top circumference",
        subtype="DISTANCE",
        unit="LENGTH",
        default=2.0,
        min=0.0,
    )
    h: FloatProperty(
        name="Height",
        description="Height of the Cone",
        subtype="DISTANCE",
        unit="LENGTH",
        default=3.0,
        min=0.001,
    )
    subdiv: IntProperty(
        name="Side",
        description="Number of sides of the polygonal approximation of the cone",
        default=36,
        min=3,
    )
    blender_quad: BoolProperty(
        name="Quad",
        description="Outputs the final mesh using quads instead of triangles.",
        default=True,
    )
