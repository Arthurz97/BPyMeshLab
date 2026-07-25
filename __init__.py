import bpy
from . import base_filter
from . import preferences
from . import ui
from . import io_handlers
from .filters import filters_create
from .filters import filters_meshing
from .filters import filters_generate

classes = (
    preferences.MESHLAB_props_preferences,
    preferences.MESHLAB_props_ui_state,
    base_filter.MESHLAB_OT_apply_filter,
    ui.MESHLAB_OT_reset_filter_settings,
    ui.MESHLAB_OT_set_filter,
    ui.MESHLAB_MT_main_menu,
    *ui.dynamic_menu_classes,
    ui.MESHLAB_PT_main_panel,
    filters_create.MESHLAB_PG_create_cube,
    filters_create.MESHLAB_PG_create_sphere,
    filters_create.MESHLAB_PG_create_sphere_cap,
    filters_create.MESHLAB_PG_create_torus,
    filters_create.MESHLAB_PG_create_annulus,
    filters_create.MESHLAB_PG_create_cone,
    filters_create.MESHLAB_PG_create_dodecahedron,
    filters_create.MESHLAB_PG_create_dodecahedron_sym,
    filters_create.MESHLAB_PG_create_icosahedron,
    filters_create.MESHLAB_PG_create_octahedron,
    filters_create.MESHLAB_PG_create_tetrahedron,
    filters_create.MESHLAB_PG_create_grid,
    filters_create.MESHLAB_PG_create_noisy_isosurface,
    filters_generate.MESHLAB_PG_generate_plane_fitting_to_selection,
    filters_create.MESHLAB_PG_create_fractal_terrain,
    filters_meshing.MESHLAB_PG_meshing_isotropic_explicit_remeshing,
    filters_generate.MESHLAB_PG_generate_resampled_uniform_mesh,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.meshlab_prefs = bpy.props.PointerProperty(
        type=preferences.MESHLAB_props_preferences
    )
    bpy.types.Scene.meshlab_ui_state = bpy.props.PointerProperty(
        type=preferences.MESHLAB_props_ui_state
    )

    bpy.types.Scene.ml_create_cube = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_cube
    )
    bpy.types.Scene.ml_create_sphere = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_sphere
    )
    bpy.types.Scene.ml_create_sphere_cap = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_sphere_cap
    )
    bpy.types.Scene.ml_create_torus = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_torus
    )
    bpy.types.Scene.ml_create_annulus = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_annulus
    )
    bpy.types.Scene.ml_create_cone = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_cone
    )
    bpy.types.Scene.ml_create_dodecahedron = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_dodecahedron
    )
    bpy.types.Scene.ml_create_dodecahedron_sym = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_dodecahedron_sym
    )
    bpy.types.Scene.ml_create_icosahedron = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_icosahedron
    )
    bpy.types.Scene.ml_create_octahedron = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_octahedron
    )
    bpy.types.Scene.ml_create_tetrahedron = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_tetrahedron
    )
    bpy.types.Scene.ml_create_grid = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_grid
    )
    bpy.types.Scene.ml_create_noisy_isosurface = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_noisy_isosurface
    )
    bpy.types.Scene.ml_generate_plane_fitting_to_selection = bpy.props.PointerProperty(
        type=filters_generate.MESHLAB_PG_generate_plane_fitting_to_selection
    )
    bpy.types.Scene.ml_create_fractal_terrain = bpy.props.PointerProperty(
        type=filters_create.MESHLAB_PG_create_fractal_terrain
    )
    bpy.types.Scene.ml_meshing_isotropic_explicit_remeshing = bpy.props.PointerProperty(
        type=filters_meshing.MESHLAB_PG_meshing_isotropic_explicit_remeshing
    )
    bpy.types.Scene.ml_generate_resampled_uniform_mesh = bpy.props.PointerProperty(
        type=filters_generate.MESHLAB_PG_generate_resampled_uniform_mesh
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.meshlab_prefs
    del bpy.types.Scene.meshlab_ui_state
    del bpy.types.Scene.ml_create_cube
    del bpy.types.Scene.ml_create_sphere
    del bpy.types.Scene.ml_create_sphere_cap
    del bpy.types.Scene.ml_create_torus
    del bpy.types.Scene.ml_create_annulus
    del bpy.types.Scene.ml_create_cone
    del bpy.types.Scene.ml_create_dodecahedron
    del bpy.types.Scene.ml_create_dodecahedron_sym
    del bpy.types.Scene.ml_create_icosahedron
    del bpy.types.Scene.ml_create_octahedron
    del bpy.types.Scene.ml_create_tetrahedron
    del bpy.types.Scene.ml_create_grid
    del bpy.types.Scene.ml_create_noisy_isosurface
    del bpy.types.Scene.ml_generate_plane_fitting_to_selection
    del bpy.types.Scene.ml_create_fractal_terrain
    del bpy.types.Scene.ml_meshing_isotropic_explicit_remeshing
    del bpy.types.Scene.ml_generate_resampled_uniform_mesh
