import bmesh

from bpy.types     import Object, DataTransferModifier
from bmesh.types   import BMFace
from collections   import Counter


def sequential_faces(self, dupe: Object, original: Object) -> None:
    mesh = dupe.data
    bm = bmesh.new()
    bm.from_mesh(mesh)

    original_faces: list[tuple[set[int], int]] = [
        (set(v.index for v in face.verts), len(face.verts) - 2) 
        for face in bm.faces
        ]

    bmesh.ops.triangulate(
        bm, 
        faces=bm.faces[:], 
        quad_method=self.tri_method[0], 
        ngon_method=self.tri_method[1]
        )

    tri_to_verts : dict[BMFace, set[int]] = {}
    vert_to_faces: list[set[BMFace]]      = [set() for _ in range(len(bm.verts))]
    for tri in bm.faces:
        vert_indices = set()
        for vert in tri.verts:
            vert_indices.add(vert.index)
            vert_to_faces[vert.index].add(tri)
        tri_to_verts[tri] = vert_indices
        
    new_index     = 0
    ordered_faces = {}
    for face_verts, tri_count in original_faces:
        face_count = 0
        
        if tri_count > 2:
            # Checks if faces share a vertex.
            adjacent_faces: set[BMFace] = {tri for vert in face_verts for tri in vert_to_faces[vert]}
            
        else:
            # Checks if faces share an edge.
            face_shared_verts = Counter(tri for vert in face_verts for tri in vert_to_faces[vert])
            adjacent_faces = {tri for tri, count in face_shared_verts.items() if count >= 2}
        
        for tri in adjacent_faces:
            if tri not in ordered_faces and tri_to_verts[tri] <= face_verts:
                ordered_faces[tri] = new_index
                new_index  += 1
                face_count += 1

            if face_count == tri_count:
                break
    
    bm.faces.sort(key=lambda face:ordered_faces.get(face, float('inf')))
    bm.faces.index_update()

    bm.to_mesh(mesh)
    bm.free()  

    modifier:DataTransferModifier = dupe.modifiers.new(name="keep_transparent_normals", type="DATA_TRANSFER")
    modifier.object               = original
    modifier.use_loop_data        = True
    modifier.data_types_loops     = {"CUSTOM_NORMAL"}
    modifier.loop_mapping         = "NEAREST_POLYNOR"  
