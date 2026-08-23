from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, IntProperty
from ..base_filter import MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp


def update_polygonal_state(self, context):
    # O truque: Usa a flag nativa para pular ou executar a triangulação dinamicamente
    type(self).requires_polygons_disk = self.blender_polygonal

    # A correção da assimetria: Sincroniza o retorno (PLY ou OBJ) com a ida
    type(self).prefer_ply_disk = not self.blender_polygonal


class MESHLAB_PG_generate_solid_wireframe(
    PropertyGroup, MeshLabFilterBase, MeshLabBatchGlobalProps, MeshLabSmoothProp
):
    pymeshlab_filter = "generate_solid_wireframe"
    requires_selection = True
    shade_flat = True
    remove_attributes = ["custom_normal", "sharp_edge", "sharp_face"]
    percentage_parameters = [
        "edgecylradius",
        "vertcylradius",
        "vertsphradius",
        "faceextheight",
        "faceextinset",
    ]

    extract_multiple_layers = True
    custom_name = "SolidWireframe"

    # Força a interface a bloquear a Engine e ficar para sempre em DISCO nativamente
    forces_disk_only = True
    requires_polygons_disk = True

    batch_support = True
    global_mode = "BOOLEAN"

    def is_property_disabled(self, key, context):
        # Delega Batch e Transforms para a classe mestra
        if super().is_property_disabled(key, context):
            return True

        if key == "blender_polygonal":
            return False

        if key == "edgecylradius":
            return not self.edgecylflag
        if key == "vertcylradius":
            return not self.vertcylflag
        if key == "vertsphradius":
            return not self.vertsphflag
        if key in ["faceextheight", "faceextinset"]:
            return not self.faceextflag

        if key == "cylindersidenum":
            return not self.edgecylflag and not self.vertcylflag

        return False

    blender_polygonal: BoolProperty(
        name="Preserve Polygons",
        description="If checked, skips pre-triangulation. If unchecked, triangulates the mesh before generating the wireframe.",
        default=True,
        update=update_polygonal_state,
    )

    # --- PARÂMETROS DO FILTRO ---
    edgecylflag: BoolProperty(
        name="Edge -> Cyl.",
        description="If True all the edges are converted into cylinders.",
        default=True,
    )
    edgecylradius: FloatProperty(
        name="Edge Cylinder Rad. (abs and %)",
        description="The radius of the cylinder replacing each edge.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    vertcylflag: BoolProperty(
        name="Vertex -> Cyl.",
        description="If True all the vertices are converted into cylinders.",
        default=False,
    )
    vertcylradius: FloatProperty(
        name="Vertex Cylinder Rad. (abs and %)",
        description="The radius of the cylinder replacing each vertex.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    vertsphflag: BoolProperty(
        name="Vertex -> Sph.",
        description="If True all the vertices are converted into sphere.",
        default=True,
    )
    vertsphradius: FloatProperty(
        name="Vertex Sphere Rad. (abs and %)",
        description="The radius of the sphere replacing each vertex.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.01,
        min=0.0,
    )
    faceextflag: BoolProperty(
        name="Face -> Prism",
        description="If True all the faces are converted into prism.",
        default=True,
    )
    faceextheight: FloatProperty(
        name="Face Prism Height (abs and %)",
        description="The Height of the prism that is substituted with each face.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.005,
        min=0.0,
    )
    faceextinset: FloatProperty(
        name="Face Prism Inset (abs and %)",
        description="The inset radius of each prism, e.g. how much it is moved toward the inside each vertex on the border of the prism.",
        subtype="DISTANCE",
        unit="LENGTH",
        default=0.005,
        min=0.0,
    )
    edgefauxflag: BoolProperty(
        name="Ignore faux edges",
        description="If true only the Non-Faux edges will be considered for conversion.",
        default=True,
    )
    cylindersidenum: IntProperty(
        name="Cylinder Side",
        description="Number of sides of the cylinder (both edge and vertex).",
        default=16,
        min=3,
    )
