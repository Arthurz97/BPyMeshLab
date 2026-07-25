import bpy
from bpy.props import EnumProperty

UI_MAPPING = {
    "Create New Mesh": [
        "create_cube",
        "create_sphere",
        "create_sphere_cap",
        "create_torus",
        "create_annulus",
        "create_cone",
        "create_dodecahedron",
        "create_dodecahedron_sym",
        "create_icosahedron",
        "create_octahedron",
        "create_tetrahedron",
    ],
    "Remeshing, Simplification and Reconstruction": [
        "meshing_isotropic_explicit_remeshing",
        "generate_resampled_uniform_mesh",
    ],
}

FILTER_NAMES = {
    "create_cube": "Box/Cube",
    "create_sphere": "Sphere",
    "create_sphere_cap": "Sphere Cap",
    "create_torus": "Torus",
    "create_annulus": "Annulus",
    "create_cone": "Cone",
    "create_dodecahedron": "Dodecahedron",
    "create_dodecahedron_sym": "Dodecahedron (symmetric)",
    "create_icosahedron": "Icosahedron",
    "create_octahedron": "Octahedron",
    "create_tetrahedron": "Tetrahedron",
    "meshing_isotropic_explicit_remeshing": "Remeshing: Isotropic Explicit Remeshing",
    "generate_resampled_uniform_mesh": "Uniform Mesh Resampling",
}

FILTER_DESCRIPTIONS = {
    "create_cube": "Create a Box, Cube, Hexahedron. You can specify the side length.",
    "create_sphere": "Create a Sphere, whose topology is obtained as regular subdivision of an icosahedron.",
    "create_sphere_cap": "Create a Sphere Cap, or spherical dome, subtended by a cone of given angle.",
    "create_torus": "Create a Torus",
    "create_annulus": "Create an Annulus e.g. a flat region bounded by two concentric circles, or a holed disk.",
    "create_cone": "Create a Cone",
    "create_dodecahedron": "Create an Dodecahedron.",
    "create_dodecahedron_sym": "Create a Dodecahedron, but triangulated with an additional vertex in the middle of each face to preserve symmetry.",
    "create_icosahedron": "Create an Icosahedron.",
    "create_octahedron": "Create an Octahedron.",
    "create_tetrahedron": "Create a Tetrahedron.",
    "meshing_isotropic_explicit_remeshing": "Perform a explicit remeshing of a triangular mesh, by repeatedly applying edge flip, collapse, relax and refine operations.",
    "generate_resampled_uniform_mesh": "Create a new mesh that is a resampled version of the current one. The resampling is done by building a uniform volumetric representation where each voxel contains the signed distance from the original surface. The resampled surface is reconstructed using the marching cube algorithm over this volume.",
}


class MESHLAB_props_preferences(bpy.types.PropertyGroup):
    processing_engine: EnumProperty(
        name="Engine",
        description="Select the processing pipeline. Memory is vastly faster, Disk is safer for extreme high-poly meshes.",
        items=[
            (
                "MEMORY",
                "Memory (RAM)",
                "Processes arrays directly in memory via NumPy. Instant I/O.",
                "MEMORY",
                0,
            ),
            (
                "DISK",
                "Disk (I/O)",
                "Exports temporary PLY files. Slower, but safe fallback for memory limits.",
                "DISK_DRIVE",
                1,
            ),
        ],
        default="MEMORY",
    )

    global_prev_mesh_action: EnumProperty(
        name="Action on Selected",
        description="Choose what to do with the originally selected object.",
        # A tupla completa exige 5 elementos no Blender moderno: (ID, Nome, Descrição, Ícone, Valor Inteiro)
        items=[
            (
                "KEEP",
                "Keep",
                "Keeps the selected object untouched.",
                "OUTLINER_OB_MESH",
                0,
            ),
            ("HIDE", "Hide", "Hides the selected object.", "HIDE_ON", 1),
            (
                "DELETE",
                "Delete",
                "Permanently deletes the selected object.",
                "TRASH",
                2,
            ),
        ],
        default="HIDE",
    )


# Captura o primeiro filtro da primeira categoria para ser o default
_default_filter = "NONE"
if UI_MAPPING:
    _first_category_filters = list(UI_MAPPING.values())[0]
    if _first_category_filters:
        # Ordena usando a mesma lógica visual para garantir que o primeiro seja o correto
        _sorted_filters = sorted(
            _first_category_filters,
            key=lambda f: FILTER_NAMES.get(f, f.replace("_", " ").title()),
        )
        _default_filter = _sorted_filters[0] if _sorted_filters else "NONE"


class MESHLAB_props_ui_state(bpy.types.PropertyGroup):
    filter_name: bpy.props.StringProperty(name="Filter", default=_default_filter)
