import bpy
from bpy.app.handlers import persistent
from bpy.types import PropertyGroup
from bpy.props import IntProperty, FloatProperty, BoolProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


class MESHLAB_PG_meshing_decimation_quadric_edge_collapse(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "meshing_decimation_quadric_edge_collapse"
    is_processing = False
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    prefer_ply_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        # Esmaece selectedonly se tiver múltiplos objetos e o batch estiver desligado
        if key == "selectedonly":
            return len(context.selected_objects) > 1 and not getattr(
                self, "blender_batch", False
            )

        # Esmaece o número de faces se o Batch estiver ativo
        if key == "targetfacenum":
            return getattr(self, "blender_batch", False)

        if hasattr(super(), "is_property_disabled"):
            return super().is_property_disabled(key, context)
        return False

    @classmethod
    def pre_process_parameters(cls, params, props):
        # Swap da chave de seleção para a exigência do PyMeshLab
        if "selectedonly" in params:
            params["selected"] = params.pop("selectedonly")

        # Converte a barra visual do Blender (0 a 100) para o padrão C++ (0.0 a 1.0)
        if "targetperc" in params:
            params["targetperc"] = params["targetperc"] / 100.0

        # Remove a chave se for 0, permitindo que a API do PyMeshLab acione seu próprio fallback
        if "targetfacenum" in params and params["targetfacenum"] == 0:
            params.pop("targetfacenum")

    @classmethod
    def apply_filter(cls, context, props):
        cls.is_processing = True
        try:
            # Trava de Segurança Crítica para Batch Process
            is_batch = getattr(props, "blender_batch", False)
            target_perc = getattr(props, "targetperc", 0.0)

            if is_batch and target_perc == 0.0:
                return (
                    "CANCELLED",
                    "Erro: No modo Batch, a Porcentagem de Redução (Percentage reduction) deve ser maior que 0%.",
                )

            return super().apply_filter(context, props)
        finally:
            cls.is_processing = False

    targetfacenum: IntProperty(
        name="Target number of faces",
        description="The desired final number of faces.",
        default=0,
        min=0,
    )
    targetperc: FloatProperty(
        name="Percentage reduction",
        description="If non zero, this parameter specifies the desired final size of the mesh as a percentage of the initial size.",
        default=0.0,
        min=0.0,
        max=100.0,
        subtype="PERCENTAGE",
    )
    qualitythr: FloatProperty(
        name="Quality threshold",
        description="Quality threshold for penalizing bad shaped faces.The value is in the range [0..1] 0 accept any kind of face (no penalties), 0.5 penalize faces with quality.",
        default=0.3,
        min=0.0,
        max=1.0,
        subtype="FACTOR",
    )
    preserveboundary: BoolProperty(
        name="Preserve Boundary of the mesh",
        description="The simplification process tries to do not affect mesh boundaries during simplification.",
        default=False,
    )
    boundaryweight: FloatProperty(
        name="Boundary Preserving Weight",
        description="The importance of the boundary during simplification. Default (1.0) means that the boundary has the same importance of the rest. Values greater than 1.0 raise boundary importance and has the effect of removing less vertices on the border. Admitted range of values (0,+inf).",
        default=1.0,
        min=0.0,
    )
    preservenormal: BoolProperty(
        name="Preserve Normal",
        description="Try to avoid face flipping effects and try to preserve the original orientation of the surface.",
        default=False,
    )
    preservetopology: BoolProperty(
        name="Preserve Topology",
        description="Avoid all the collapses that should cause a topology change in the mesh (like closing holes, squeezing handles, etc). If checked the genus of the mesh should stay unchanged.",
        default=False,
    )
    optimalplacement: BoolProperty(
        name="Optimal position of simplified vertices",
        description="Each collapsed vertex is placed in the position minimizing the quadric error. It can fail (creating bad spikes) in case of very flat areas. If disabled edges are collapsed onto one of the two original vertices and the final mesh is composed by a subset of the original vertices.",
        default=True,
    )
    planarquadric: BoolProperty(
        name="Planar Simplification",
        description="Add additional simplification constraints that improves the quality of the simplification of the planar portion of the mesh, as a side effect, more triangles will be preserved in flat areas (allowing better shaped triangles).",
        default=False,
    )
    planarweight: FloatProperty(
        name="Planar Simp. Weight",
        description="How much we should try to preserve the triangles in the planar regions. If you lower this value planar areas will be simplified more.",
        default=0.001,
    )
    qualityweight: BoolProperty(
        name="Weighted Simplification",
        description="Use the Per-Vertex quality as a weighting factor for the simplification. The weight is used as a error amplification value, so a vertex with a high quality value will not be simplified and a portion of the mesh with low quality values will be aggressively simplified.",
        default=False,
    )
    autoclean: BoolProperty(
        name="Post-simplification cleaning",
        description="After the simplification an additional set of steps is performed to clean the mesh (unreferenced vertices, bad faces, etc).",
        default=True,
    )
    selectedonly: BoolProperty(
        name="Simplify only selected faces",
        description="The simplification is applied only to the selected set of faces. Take care of the target number of faces!.",
        default=False,
    )


_last_selected_mesh_names = set()
_last_active_filter = ""


@persistent
def update_targetfacenum_handler(scene, depsgraph):
    global _last_selected_mesh_names, _last_active_filter

    if MESHLAB_PG_meshing_decimation_quadric_edge_collapse.is_processing:
        return

    ui_state = getattr(scene, "meshlab_ui_state", None)
    if not ui_state:
        return

    current_filter = ui_state.filter_name

    # Se o filtro atual não for este, apenas gravamos qual é e abortamos
    if current_filter != "meshing_decimation_quadric_edge_collapse":
        _last_active_filter = current_filter
        return

    selected_meshes = [
        obj for obj in bpy.context.selected_objects if obj.type == "MESH"
    ]
    current_names = {obj.name for obj in selected_meshes}

    # Recalcula se a seleção de objetos mudou OU se o usuário acabou de abrir este filtro na UI
    if (
        current_names != _last_selected_mesh_names
        or current_filter != _last_active_filter
    ):
        _last_selected_mesh_names = current_names
        _last_active_filter = current_filter

        props = getattr(scene, "ml_meshing_decimation_quadric_edge_collapse", None)

        # Só atualiza a matemática se existir propriedades e se o Batch estiver desligado
        if props and not getattr(props, "blender_batch", False):
            total_tris = 0
            for obj in selected_meshes:
                # Usa a função nativa do Blender para calcular os triângulos exatos
                obj.data.calc_loop_triangles()
                total_tris += len(obj.data.loop_triangles)

            # Preenche a interface instantaneamente com a metade
            props.targetfacenum = max(0, total_tris // 2)


# Garante que o handler não seja duplicado em memória quando você recarregar o script no Blender
if update_targetfacenum_handler not in bpy.app.handlers.depsgraph_update_post:
    bpy.app.handlers.depsgraph_update_post.append(update_targetfacenum_handler)
