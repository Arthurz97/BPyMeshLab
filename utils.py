import bpy
import bmesh
import numpy as np


def blender_to_numpy(obj, extract_selection=False):
    """
    Extrai coordenadas e faces de um objeto Blender para matrizes NumPy.
    Utiliza foreach_get e numpy vectorize para máxima performance em C.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()

    # O PyMeshLab exige malhas trianguladas. Usamos o bmesh apenas para a triangulação rápida.
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Limpeza prévia: Funde vértices sobrepostos (Weld) a uma distância de 1 milímetro (0.001m)
    # Garante que malhas desconexas ou resultantes de operações booleanas fiquem perfeitamente seladas
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)

    bmesh.ops.triangulate(
        bm, faces=bm.faces[:], quad_method="FIXED", ngon_method="BEAUTY"
    )
    bm.to_mesh(mesh)
    bm.free()

    # --- Extração Ultra-rápida (C-Level) ---
    num_verts = len(mesh.vertices)
    num_faces = len(mesh.polygons)

    # Vértices (Local Space)
    verts_flat = np.zeros(num_verts * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", verts_flat)
    vertices = verts_flat.reshape((num_verts, 3))

    # Converte para World Space rapidamente usando matriz do numpy
    matrix_world = np.array(obj.matrix_world, dtype=np.float64)
    # Adiciona a 4ª dimensão (W=1) para a multiplicação de matriz
    ones = np.ones((num_verts, 1), dtype=np.float64)
    verts_4d = np.hstack((vertices, ones))
    # Multiplica e descarta a dimensão W
    vertices_world = np.dot(verts_4d, matrix_world.T)[:, :3]

    # Faces
    faces_flat = np.zeros(num_faces * 3, dtype=np.int32)
    mesh.polygons.foreach_get("vertices", faces_flat)
    faces = faces_flat.reshape((num_faces, 3))

    # --- Seleção (Transformada em Cor RGBA para o PyMeshLab) ---
    v_color_matrix = None
    if extract_selection:
        sel_flat = np.zeros(num_verts, dtype=bool)
        mesh.vertices.foreach_get("select", sel_flat)

        # Cria a matriz de cores: Branco (1,1,1,1) se selecionado, Preto (0,0,0,1) se não.
        v_color_matrix = np.zeros((num_verts, 4), dtype=np.float64)
        v_color_matrix[:, 3] = 1.0  # Alpha
        v_color_matrix[sel_flat, 0:3] = 1.0  # RGB = Branco onde True

    obj_eval.to_mesh_clear()

    return vertices_world, faces, v_color_matrix


def numpy_to_blender(vertices, faces, original_name, vertex_quality=None):
    """
    Reconstrói a geometria do PyMeshLab de volta para o Blender em um novo objeto.
    Utiliza o verdadeiro foreach_set para injeção massiva de memória (C-Level).
    Suporta dinamicamente Triângulos, Quads e Ngons.
    """
    mesh = bpy.data.meshes.new(original_name)

    num_verts = len(vertices)

    # O PyMeshLab pode retornar faces como uma Lista de Arrays (Quads/Ngons) ou um Array 2D NumPy (Triângulos)
    if isinstance(faces, list):
        num_faces = len(faces)
        if num_faces == 0:
            face_sizes = np.array([], dtype=np.int32)
            face_indices = np.array([], dtype=np.int32)
        else:
            face_sizes = np.array([len(f) for f in faces], dtype=np.int32)
            # Adicionado .ravel() para achatar a estrutura das sublistas C++ com segurança
            face_indices = np.concatenate(faces).ravel().astype(np.int32)
    else:
        # Alternativa para o Array 2D tradicional (Geralmente Triângulos)
        num_faces = len(faces)
        verts_per_face = faces.shape[1] if faces.ndim > 1 else 3
        face_sizes = np.full(num_faces, verts_per_face, dtype=np.int32)
        face_indices = faces.ravel().astype(np.int32)

    mesh.vertices.add(num_verts)
    mesh.polygons.add(num_faces)
    mesh.loops.add(len(face_indices))

    mesh.vertices.foreach_set("co", vertices.ravel())

    # loop_start requer o índice acumulado indicando onde cada face começa na malha achatada
    face_starts = np.zeros(num_faces, dtype=np.int32)
    if num_faces > 1:
        face_starts[1:] = np.cumsum(face_sizes)[:-1]

    mesh.polygons.foreach_set("loop_start", face_starts)
    mesh.polygons.foreach_set("loop_total", face_sizes)
    mesh.loops.foreach_set("vertex_index", face_indices)

    # ATUALIZA A MALHA E GERA AS ARESTAS ANTES DE LIMPAR A SELEÇÃO
    mesh.update(calc_edges=True)

    # Injeção Direta de Qualidade (Vertex Quality) como Atributo Blender
    if vertex_quality is not None and len(vertex_quality) == num_verts:
        quality_attr = mesh.attributes.new(name="quality", type="FLOAT", domain="POINT")
        quality_attr.data.foreach_set(
            "value", np.array(vertex_quality, dtype=np.float32).ravel()
        )

    # 3. Limpeza de Seleção Absoluta (Vértices, Faces E Arestas)
    mesh.vertices.foreach_set("select", np.zeros(num_verts, dtype=bool))
    mesh.polygons.foreach_set("select", np.zeros(num_faces, dtype=bool))
    mesh.edges.foreach_set("select", np.zeros(len(mesh.edges), dtype=bool))

    # SALVA A LIMPEZA PARA O MODO RAM
    mesh.update()

    new_obj = bpy.data.objects.new(original_name, mesh)
    return new_obj
