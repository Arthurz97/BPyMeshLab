import bpy
from bpy.props import EnumProperty
from .constants import UI_MAPPING, FILTER_NAMES, FILTER_DESCRIPTIONS


class MESHLAB_props_preferences(bpy.types.PropertyGroup):
    processing_engine: EnumProperty(
        name="Engine",
        description="Select the processing pipeline method: Memory or Disk.",
        items=[
            (
                "MEMORY",
                "Memory (RAM)",
                "Processes data directly in memory via NumPy, without disk I/O.",
                "MEMORY",
                0,
            ),
            (
                "DISK",
                "Disk (I/O)",
                "Exports and imports temporary files via disk.",
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
