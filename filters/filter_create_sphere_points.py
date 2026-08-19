import bpy
from bpy.types import PropertyGroup
from bpy.props import IntProperty, EnumProperty
from ..base_filter import MeshLabFilterBase


class MESHLAB_PG_create_sphere_points(PropertyGroup, MeshLabFilterBase):
    pymeshlab_filter = "create_sphere_points"
    requires_selection = False
    ignore_selection_count = True
    shade_flat = True
    remove_attributes = ["custom_normal", "material_index", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True  # O formato PLY é muito mais robusto e performático para lidar com Nuvem de Pontos em disco.

    # Propriedades da UI baseadas no JSON e na API
    # Como o PyMeshLab aceita diretamente a string do Enum, não é necessário um pre_process_parameters.
    # Não adicionamos as opções de topologia (Quad/Smooth) pois é uma nuvem de pontos (Point Cloud).

    pointnum: IntProperty(
        name="Point Num",
        description="Number of points (approximate).",
        default=100,
        min=1,
    )

    spheregentech: EnumProperty(
        name="Generation Technique",
        description="Create a spherical point cloud, it can be random or regularly distributed.",
        items=[
            (
                "Montecarlo",
                "Montecarlo",
                "The points are randomly generated with an uniform distribution.",
            ),
            (
                "Poisson Sampling",
                "Poisson Sampling",
                "The points are to follow a poisson disk distribution.",
            ),
            (
                "DiscoBall",
                "DiscoBall",
                "Dave Rusin's disco ball algorithm for the regular placement of points on a sphere is used.",
            ),
            (
                "Octahedron",
                "Octahedron",
                "Points are generated on the vertex of a recursively subdivided octahedron.",
            ),
            ("Fibonacci", "Fibonacci", "Fibonacci sequence based distribution."),
        ],
        default="Octahedron",
    )
