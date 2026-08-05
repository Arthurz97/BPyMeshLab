import bpy
from . import base_filter
from . import preferences
from . import ui
from . import io_handlers
import importlib
import pkgutil
import inspect

# Classes base e de interface
core_classes = (
    preferences.MESHLAB_props_preferences,
    preferences.MESHLAB_props_ui_state,
    base_filter.MESHLAB_OT_apply_filter,
    ui.MESHLAB_OT_get_viewport_position,
    ui.MESHLAB_OT_reset_filter_settings,
    ui.MESHLAB_OT_set_filter,
    ui.MESHLAB_MT_main_menu,
    ui.MESHLAB_PT_main_panel,
)

# Lista para armazenar as classes de filtros descobertas em runtime
dynamic_filter_classes = []


def discover_filters():
    """Varre a pasta 'filters' e importa as classes de filtros dinamicamente."""
    dynamic_filter_classes.clear()
    from . import filters

    for _, module_name, _ in pkgutil.iter_modules(filters.__path__):
        full_module_name = f"{filters.__name__}.{module_name}"
        module = importlib.import_module(full_module_name)
        # O reload garante que edições nos filtros sejam lidas durante a recarga do script no Blender
        importlib.reload(module)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, bpy.types.PropertyGroup) and hasattr(
                obj, "pymeshlab_filter"
            ):
                # Validação para ignorar possíveis imports secundários no arquivo
                if name.startswith("MESHLAB_PG_"):
                    dynamic_filter_classes.append(obj)


def register():
    # 1. Descoberta Automática de Arquivos
    discover_filters()

    # 2. Registro de Lógica Base e Menus Dinâmicos
    for cls in core_classes:
        bpy.utils.register_class(cls)
    for cls in ui.dynamic_menu_classes:
        bpy.utils.register_class(cls)

    # 3. Registro e Bind Dinâmico dos Filtros na Scene
    for cls in dynamic_filter_classes:
        bpy.utils.register_class(cls)
        setattr(
            bpy.types.Scene,
            f"ml_{cls.pymeshlab_filter}",
            bpy.props.PointerProperty(type=cls),
        )

    # 4. Bind Propriedades Globais
    bpy.types.Scene.meshlab_prefs = bpy.props.PointerProperty(
        type=preferences.MESHLAB_props_preferences
    )
    bpy.types.Scene.meshlab_ui_state = bpy.props.PointerProperty(
        type=preferences.MESHLAB_props_ui_state
    )


def unregister():
    del bpy.types.Scene.meshlab_prefs
    del bpy.types.Scene.meshlab_ui_state

    # Desfaz apontamentos dos filtros dinâmicos
    for cls in reversed(dynamic_filter_classes):
        prop_name = f"ml_{cls.pymeshlab_filter}"
        if hasattr(bpy.types.Scene, prop_name):
            delattr(bpy.types.Scene, prop_name)
        bpy.utils.unregister_class(cls)

    for cls in reversed(ui.dynamic_menu_classes):
        bpy.utils.unregister_class(cls)
    for cls in reversed(core_classes):
        bpy.utils.unregister_class(cls)
