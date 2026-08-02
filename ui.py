import bpy
from .constants import UI_MAPPING, FILTER_NAMES, FILTER_DESCRIPTIONS


class MESHLAB_OT_set_filter(bpy.types.Operator):
    bl_idname = "meshlab.set_filter"
    bl_label = "Select Filter"
    bl_options = {"INTERNAL"}

    filter_id: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        if properties and properties.filter_id:
            return FILTER_DESCRIPTIONS.get(
                properties.filter_id, "Selects a PyMeshLab filter."
            )
        return "Selects a PyMeshLab filter."

    def execute(self, context):
        # Atualiza a string do filtro selecionado no momento
        context.scene.meshlab_ui_state.filter_name = self.filter_id

        # Auto-switch: Muda a engine para DISK automaticamente se o filtro exigir polígonos
        props = getattr(context.scene, f"ml_{self.filter_id}", None)
        if props and getattr(props.__class__, "requires_polygons_disk", False):
            context.scene.meshlab_prefs.processing_engine = "DISK"

        return {"FINISHED"}


# Lista para guardar as classes de submenu geradas dinamicamente
dynamic_menu_classes = []


def create_menu_classes():
    global dynamic_menu_classes
    dynamic_menu_classes.clear()

    for idx, (category_name, filters) in enumerate(UI_MAPPING.items()):
        bl_idname = f"MESHLAB_MT_category_{idx}"

        def make_draw(cat_filters):
            def draw(self, context):
                layout = self.layout
                current_filter = context.scene.meshlab_ui_state.filter_name

                # Ordena os filtros pelo nome visual antes de desenhar no submenu
                sorted_filters = sorted(
                    cat_filters,
                    key=lambda f: FILTER_NAMES.get(f, f.replace("_", " ").title()),
                )

                for f_id in sorted_filters:
                    name = FILTER_NAMES.get(f_id, f_id.replace("_", " ").title())

                    # Desenha o operador com ou sem o ícone 'FILTER' (funil) dependendo do estado
                    if f_id == current_filter:
                        op = layout.operator(
                            "meshlab.set_filter", text=name, icon="FILTER"
                        )
                    else:
                        op = layout.operator("meshlab.set_filter", text=name)

                    op.filter_id = f_id

            return draw

        # Geração dinâmica da classe do Submenu para o Blender
        menu_cls = type(
            bl_idname,
            (bpy.types.Menu,),
            {
                "bl_idname": bl_idname,
                "bl_label": category_name,
                "draw": make_draw(filters),
            },
        )
        dynamic_menu_classes.append(menu_cls)


# Inicializa as classes dinâmicas durante o carregamento do módulo
create_menu_classes()


class MESHLAB_MT_main_menu(bpy.types.Menu):
    bl_idname = "MESHLAB_MT_main_menu"
    bl_label = "BPyMeshLab Filters"

    def draw(self, context):
        layout = self.layout
        current_filter = context.scene.meshlab_ui_state.filter_name

        for idx, category_name in enumerate(UI_MAPPING.keys()):
            # Verifica se o filtro atualmente ativo está dentro da lista desta categoria
            if current_filter in UI_MAPPING[category_name]:
                # Desenha o submenu com o ícone caso o filtro pertença a ele
                layout.menu(
                    f"MESHLAB_MT_category_{idx}", text=category_name, icon="FILTER"
                )
            else:
                # Desenha o submenu normalmente sem o ícone
                layout.menu(f"MESHLAB_MT_category_{idx}", text=category_name)


class MESHLAB_OT_reset_filter_settings(bpy.types.Operator):
    bl_idname = "meshlab.reset_filter_settings"
    bl_label = "Reset Filter Settings"
    bl_description = "Reset filter parameters to default values."
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        ui_state = context.scene.meshlab_ui_state
        active_filter = ui_state.filter_name
        props = getattr(context.scene, f"ml_{active_filter}", None)
        if props:
            for key in props.bl_rna.properties.keys():
                if key not in ["rna_type", "name"]:
                    props.property_unset(key)
        return {"FINISHED"}


class MESHLAB_PT_main_panel(bpy.types.Panel):
    bl_label = "BPyMeshLab"
    bl_idname = "MESHLAB_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "BPyMeshLab"

    def draw(self, context):
        layout = self.layout
        prefs = context.scene.meshlab_prefs
        ui_state = context.scene.meshlab_ui_state

        active_filter = ui_state.filter_name

        # Obtém o nome formatado para exibir dentro da caixa preta
        if active_filter == "NONE" or not active_filter:
            display_name = "Select a Filter..."
        else:
            display_name = FILTER_NAMES.get(
                active_filter, active_filter.replace("_", " ").title()
            )

        # Replica a estrutura visual exata de "use_property_split" nativa do Blender
        split = layout.split(factor=0.4)

        # Coluna da esquerda (Rótulo): Força o alinhamento para a direita para "grudar" na caixa
        col_label = split.column(align=True)
        col_label.alignment = "RIGHT"
        col_label.label(text="Filter")

        # Coluna da direita (Caixa preta interativa)
        col_menu = split.column(align=True)
        # Controla a altura da caixa do menu principal (1.0 é o padrão)
        col_menu.scale_y = 1.0

        if active_filter == "NONE" or not active_filter:
            col_menu.menu("MESHLAB_MT_main_menu", text=display_name)
        else:
            col_menu.menu("MESHLAB_MT_main_menu", text=display_name, icon="FILTER")

        if active_filter == "NONE":
            return

        props = getattr(context.scene, f"ml_{active_filter}", None)
        layout.separator()

        if props:
            layout.operator(
                "meshlab.reset_filter_settings", text="Reset Filter Settings"
            )

            # --- Ação sobre o objeto e Botão de Aplicar (Movidos para o topo) ---
            # Empilha as configurações globais usando o padrão 'split' nativo

            col_action = layout.column(align=True)
            col_action.use_property_split = True
            col_action.use_property_decorate = False

            # Trava de UI para filtros baseados em polígonos
            requires_poly = getattr(props.__class__, "requires_polygons_disk", False)

            row_engine = col_action.row(align=True)
            if requires_poly:
                row_engine.enabled = False
            row_engine.prop(prefs, "processing_engine", text="Engine")

            col_action.prop(prefs, "global_prev_mesh_action", text="Selected")

            if requires_poly:
                layout.separator()
                col_msg = layout.column(align=True)
                col_msg.label(
                    text="Motor forçado para Disco (I/O) automaticamente.", icon="INFO"
                )
                col_msg.label(
                    text="Quads/Ngons exigem processamento em Disco.", icon="BLANK1"
                )

            # --- INÍCIO DA MENSAGEM DE AVISO DINÂMICO ---
            num_selected = len(context.selected_objects)
            msg_parts = []

            if num_selected > 1:
                if hasattr(props, "blender_batch"):
                    if getattr(props, "blender_batch"):
                        msg_parts.append(f"Batch: {num_selected} objetos.")
                    else:
                        msg_parts.append(f"Global: {num_selected} objetos unidos.")
                elif getattr(props, "is_batch_only", False):
                    msg_parts.append(f"Batch Obrigatório: {num_selected} objetos.")
            elif num_selected == 1 and getattr(props, "ignores_modifiers", False):
                msg_parts.append("1 objeto selecionado.")

            if getattr(props, "ignores_modifiers", False):
                msg_parts.append("(Modificadores não serão usados)")

            if msg_parts:
                row_info = layout.row()
                row_info.label(text=" ".join(msg_parts), icon="INFO")
            # --- FIM DA MENSAGEM DE AVISO DINÂMICO ---

            col = layout.column()
            col.scale_y = 1.5
            op = col.operator("meshlab.apply_filter", text="Apply Filter", icon="PLAY")
            op.filter_id = active_filter

            # Espaçamento para não grudar na caixa de parâmetros abaixo
            layout.separator()

            # --- Caixa de Parâmetros ---
            box_filter = layout.box()
            box_filter.label(text="Parameters:", icon="TOOL_SETTINGS")

            # Desenha todas as propriedades da classe dinamicamente, sem necessidade de customizações
            for key in props.__class__.__annotations__.keys():
                # Verifica se a classe do filtro pede para ocultar essa propriedade no estado atual
                if hasattr(props, "is_property_hidden") and props.is_property_hidden(
                    key
                ):
                    continue

                ui_label = props.bl_rna.properties[key].name
                prop_type = props.bl_rna.properties[key].type

                # Aplica o padrão dividido (igual ao topo) apenas para Enums e Strings
                if prop_type in ["ENUM", "STRING"]:
                    # Usa o sistema nativo do Blender, resolvendo o bug do título e dos dois pontos simultaneamente
                    col_split = box_filter.column()
                    col_split.use_property_split = True
                    col_split.use_property_decorate = False

                    if hasattr(
                        props, "is_property_disabled"
                    ) and props.is_property_disabled(key, context):
                        col_split.enabled = False

                    col_split.prop(props, key, text=ui_label)
                else:
                    # Mantém o padrão nativo para Floats, Ints e Bools (textos dentro das caixas)
                    row = box_filter.row()
                    # INÍCIO DO ESMAECIMENTO DINÂMICO
                    if hasattr(
                        props, "is_property_disabled"
                    ) and props.is_property_disabled(key, context):
                        row.enabled = False
                    # FIM DO ESMAECIMENTO DINÂMICO
                    row.prop(props, key, text=ui_label)
