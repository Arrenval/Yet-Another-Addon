import re
import bpy
import bmesh
import numpy as np

from numpy         import float32
from numpy.typing  import NDArray
from bpy.types     import Object, TriangulateModifier, Depsgraph, ShapeKey, DataTransferModifier
from bmesh.types   import BMFace, BMesh
from collections   import Counter, defaultdict

from .typings      import ObjIterable
from .logging      import YetAnotherLogger
from .objects      import visible_meshobj, safe_object_delete, copy_mesh_object, quick_copy
from .ya_exception import XIVMeshParentError
from ..properties  import get_window_properties, get_devkit_properties

def get_shape_mix(source_obj: Object, extra_key: str="") -> NDArray[float32]:
    """
    Get current mix of shape keys from a mesh. 
    The extra key is optional and will blend that key in at its full value.
    """
    key_blocks = source_obj.data.shape_keys.key_blocks
    vert_count = len(source_obj.data.vertices)
    co_bases   = {}

    basis_co = np.zeros(vert_count * 3, dtype=np.float32)
    key_blocks[0].data.foreach_get("co", basis_co)
    co_bases[key_blocks[0].name] = basis_co

    # We need a copy of the main basis to mix our keys with
    mix_coords = basis_co.copy()

    # Account for keys with a different relative shape
    for key in key_blocks[1:]:
        if key.relative_key.name in co_bases:
            continue
        relative_co = np.zeros(vert_count * 3, dtype=np.float32)
        key.relative_key.data.foreach_get("co", relative_co)
        co_bases[key.relative_key.name] = relative_co

    for key in key_blocks[1:]:
        if key.name == extra_key:
            keep  = True
            blend = 1
        else:
            keep  = False
            blend = key.value
            
        if keep or (key.value != 0 and not key.mute):
            relative_key = key.relative_key.name
            key_coords   = np.zeros(vert_count * 3, dtype=np.float32)
            key.data.foreach_get("co", key_coords)

            # Use relative key coordinates to get offset
            offset = key_coords - co_bases[relative_key]
            mix_coords += offset * blend
    
    return mix_coords
    
def triangulation_method(obj:Object)-> tuple[str, str]:
            tri_method = ('BEAUTY', 'BEAUTY')
            for modifier in reversed(obj.modifiers):
                if modifier.type == "TRIANGULATE" and modifier.show_viewport:
                    modifier: TriangulateModifier
                    tri_method = (modifier.quad_method, modifier.ngon_method)
                    break
            return tri_method


def create_backfaces(obj:Object) -> None:
    """Assumes the mesh is triangulated to get the faces from _get_backfaces."""
    mesh = obj.data
    old_poly_count = len(mesh.polygons) 

    bm = bmesh.new()
    bm.from_mesh(mesh)

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    bf_idx    = obj.vertex_groups["BACKFACES"].index
    backfaces = _get_backfaces(bm, bf_idx)
    
    dupe_faces = [
        geo for geo in 
        bmesh.ops.duplicate(bm, geom=backfaces[:])["geom"] 
        if isinstance(geo, bmesh.types.BMFace)
        ]

    bmesh.ops.reverse_faces(bm, faces=dupe_faces)

    bm.to_mesh(mesh)
    bm.free()

    normals = []
    for face_idx, face in enumerate(mesh.polygons):
        if face_idx >= old_poly_count:
            normals.extend([(0, 0, 0)] * face.loop_total)
        else:
            for i in range(face.loop_total):
                loop_idx = face.loop_start + i
                normals.append(tuple(mesh.loops[loop_idx].normal))

    mesh.normals_split_custom_set(normals)

def backfaces_with_shapes(obj: Object):
    key_blocks = obj.data.shape_keys.key_blocks

    temp_obj = {}
    verts    = len(obj.data.vertices)
    shape_co = np.zeros(verts * 3, dtype=np.float32)
    for key in key_blocks[1:]:
        temp_copy = quick_copy(obj)
        
        key.data.foreach_get("co", shape_co)

        temp_copy.shape_key_clear()
        temp_copy.data.vertices.foreach_set("co", shape_co)
        create_backfaces(temp_copy)

        temp_obj[key.name] = temp_copy
    
    obj.shape_key_clear()
    create_backfaces(obj)
    obj.shape_key_add(name="Basis")

    verts = len(obj.data.vertices)
    shape_co = np.zeros(verts * 3, dtype=np.float32)

    for key_name, copy in temp_obj.items():
        copy: Object
        copy.data.vertices.foreach_get("co", shape_co)

        new_shape = obj.shape_key_add(name=key_name)
        new_shape.data.foreach_set("co", shape_co)

        safe_object_delete(copy)

def _get_backfaces(bm: BMesh, bf_idx: int) -> list[BMFace]:
    deform_layer = bm.verts.layers.deform.active

    vertex_weights = np.zeros(len(bm.verts), dtype=np.float32)
    for i, vert in enumerate(bm.verts):
        vertex_weights[i] = vert[deform_layer].get(bf_idx, 0)
    
    face_indices = np.array([[v.index for v in face.verts] for face in bm.faces])
    face_weights = vertex_weights[face_indices] 
    faces_mask   = np.any(face_weights > 0, axis=1)

    bm.faces.ensure_lookup_table()

    backfaces = [bm.faces[i] for i, is_backface in enumerate(faces_mask) if is_backface]
    
    return backfaces
    

def remove_vertex_groups(obj: Object, prefix: tuple[str]) -> None:
    """Can remove any vertex group and add weights to parent group."""
    group_to_parent = _get_group_parent(obj, prefix)
    source_groups   = [value for value in group_to_parent.keys()]
    missing_groups  = {value for value in group_to_parent.values() if isinstance(value, str)}

    if not source_groups:
        return

    verts         = len(obj.data.vertices)
    max_groups    = len(obj.vertex_groups) + len(missing_groups)
    weight_matrix = np.zeros((verts, max_groups), dtype=np.float32)

    if len(source_groups) == 1:
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        group_idx = source_groups[0]
        deform_layer = bm.verts.layers.deform.active
        for vert_idx, vert in enumerate(bm.verts):
            weight_matrix[vert_idx, group_idx] = vert[deform_layer].get(group_idx, 0)

        bm.free()
    else:
        for vertex_idx, vertex in enumerate(obj.data.vertices):
            for group in vertex.groups:
                if group.group in source_groups:
                    weight_matrix[vertex_idx, group.group] = group.weight
    
    added_parents   = {}
    updated_indices = defaultdict(lambda: np.array([], dtype=np.uint32))
    for group_idx, parent in group_to_parent.items():
        if isinstance(parent, str):
            parent = _get_missing_parent(obj, group_idx, parent, added_parents)

        group_vertices = np.flatnonzero(weight_matrix[:, group_idx])
        
        existing = updated_indices[parent]
        updated_indices[parent] = np.union1d(existing, group_vertices)

        weight_matrix[:, parent] += weight_matrix[:, group_idx]

    for v_group in obj.vertex_groups:
        if v_group.index not in updated_indices:
            continue
        
        for index in updated_indices[v_group.index]:
            v_group.add([int(index)], weight_matrix[index, v_group.index], type="ADD")

    for v_group in obj.vertex_groups:
        if v_group.name.startswith(prefix):
            obj.vertex_groups.remove(v_group)
    
def _get_group_parent(obj: Object, prefix: set[str]) -> dict[int, int | str]:
    group_to_parent = {}

    for v_group in obj.vertex_groups:
        if not v_group.name.startswith(prefix):
            continue
        
        parent = obj.parent.data.bones.get(v_group.name).parent.name
        parent_group = obj.vertex_groups.get(parent)

        if parent_group:
            group_to_parent[v_group.index] = parent_group.index
        else:
            group_to_parent[v_group.index] = parent
    
    return group_to_parent

def _get_missing_parent(obj: Object, group_idx:int, parent:str, added_parents: dict) -> int:
    if parent in added_parents:
        return added_parents[parent]

    else:
        v_group   = obj.vertex_groups[group_idx].name
        parent    = obj.parent.data.bones.get(v_group).parent.name
        new_group = obj.vertex_groups.new(name=parent)

        added_parents[parent] = new_group.index

        return new_group.index
        

class MeshHandler:
    """
    This class takes all visible meshes in a Blender scene and runs various logic on them to retain/add properties needed for XIV models. 
    It's designed to work with my export operators to save and restore the Blender scene when the class is done with its operations.
    It works non-destructively by duplicating the initial models, hiding them, then making the destructice edits on the duplicates.
    1. prepare_meshes saves the scene visibility state, checks what process each mesh requires and does an initial sort.
    2. process_meshes are the actual manipulation and finalisation of the meshes.
    3. restore_meshes restores the initial Blender scene from before prepare_meshes.
    Each function should be called separately on the same instance of the class in the listed order.

    """

    def __init__(self, logger: YetAnotherLogger=None, depsgraph: Depsgraph=None):
        props                            = get_window_properties()
        self.depsgraph : Depsgraph       = depsgraph
        self.shapekeys : bool            = props.keep_shapekeys
        self.backfaces : bool            = (props.create_backfaces and props.check_tris)
        self.is_tris   : bool            = props.check_tris
        self.yas_vag   : bool            = True
        self.remove_yas: str             = props.remove_yas
        self.reset     : list[Object]    = []
        self.delete    : list[Object]    = []
        self.tri_method: tuple[str, str] = ("BEAUTY", "BEAUTY")

        self.logger    : YetAnotherLogger = logger
        self.meshes    : dict[Object, dict[str, list | bool]] = {}                       
    
    def prepare_meshes(self) -> None:
        if self.logger:
            self.logger.log("Preparing meshes...", 2)

        visible_obj = visible_meshobj()
        no_skeleton = []

        # Bools for deciding which waist shape keys to keep. Only relevant for Yet Another Devkit.
        self.rue    = False
        self.buff   = False
        self.torso  = False
        self.devkit = get_devkit_properties()

        if self.devkit:
            self.devkit_checks(visible_obj)

        for obj in visible_obj:
            if not obj.parent or obj.parent.type != "ARMATURE":
                no_skeleton.append(obj)
                continue
            shape_key    = self.sort_shape_keys(obj) if self.shapekeys and obj.data.shape_keys else []
            transparency = ("xiv_transparency" in obj and obj["xiv_transparency"])
            backfaces    = (self.is_tris and self.backfaces and obj.vertex_groups.get("BACKFACES")) 

            if self.devkit and obj.data.name == "Waist":
                gen_b   = obj.data.shape_keys.key_blocks.get("Gen B")
                gen_c   = obj.data.shape_keys.key_blocks.get("Gen C")
                yas_vag = (gen_b and not gen_b.mute and gen_b.value != 0) or (gen_c and not gen_c.mute or gen_c.value != 0)
                self.yas_vag = yas_vag

            self.reset.append(obj)
            self.meshes[obj] = {
                'shape'       : shape_key, 
                'transparency': transparency, 
                'backfaces'   : backfaces
                }
        
        if no_skeleton:
            raise XIVMeshParentError(len(no_skeleton))

    def devkit_checks(self, visible_obj: ObjIterable) -> None:
        for obj in visible_obj:
            if not obj.data.shape_keys:
                continue 
            rue_key  = obj.data.shape_keys.key_blocks.get("Rue")
            buff_key = obj.data.shape_keys.key_blocks.get("Buff")
            if rue_key and rue_key.mute == False and rue_key.value == 1.0:
                self.rue = True 
            if buff_key and buff_key.mute == False and buff_key.value == 1.0 :
                self.buff = True
            if obj.data.name == "Torso":
                self.torso = True

    def sort_shape_keys(self, obj: Object) -> list[ShapeKey]:
        shape_keys = []
        for key in obj.data.shape_keys.key_blocks:
            if not key.name.startswith("shp"):
                continue
            if self.rue:
                if key.name[5:11] == "wa_yab":
                # Rue does not use YAB's waist shape keys.
                    continue
                # Removes hip key, use yam for keys meant for rue as well
                if key.name[5:8] == "yab":
                    continue  
            else:
                if key.name[5:8] == "rue":
                    continue

            if self.devkit and key.name[5:8] == "wa_":
                # We check for buff and torso because in the case where the torso and waist are present we
                # remove the abs key from both body parts.
                if not self.buff and self.torso and key.name.endswith("_yabs"):
                    continue

                # We don't have to check for torso here because it's implicitly assumed to be present when buff is True.
                # If waist and torso are present we then remove the yab key.
                if self.buff and key.name.endswith("_yab"):
                    continue
            key.value = 0
            shape_keys.append(key)

        return shape_keys

    def process_meshes(self) -> None:
        dupe: Object 
        transparency = []
        shape_keys   = []
        backfaces    = []
        dupes        = []

        if not self.depsgraph:
            self.depsgraph = bpy.context.evaluated_depsgraph_get()

        for obj, stats in self.meshes.items():
            if self.logger:
                self.logger.last_item = f"{obj.name}"
            dupe = copy_mesh_object(obj, self.depsgraph)

            if re.search(r"^\d+.\d+\s", obj.name):
                name_parts = obj.name.split(" ")
                dupe.name = " ".join(["ExportMesh"] + name_parts[1:] + name_parts[0:1])
            else:
                dupe.name = "ExportMesh " + obj.name

            if stats["transparency"]:
                transparency.append((dupe, obj))

            if stats["shape"]:
                shape_keys.append((dupe, obj, stats["shape"]))
            
            if stats["backfaces"]:
                backfaces.append(dupe)
            
            dupes.append(dupe)
            self.delete.append(dupe)
        
        if transparency:
            self.handle_transparency(transparency)
        
        if shape_keys:
            self.handle_shape_keys(shape_keys)
            
        if backfaces:
            self.handle_backfaces(backfaces)

        self.handle_vertex_groups(dupes)

        for obj in self.meshes:
            obj.hide_set(state=True)

    def handle_transparency(self, transparency: list[tuple[Object, Object]]) -> None:
        if self.logger:
            self.logger.log("Fixing face order...", 2)

        for dupe, original in transparency:
            if self.logger:
                self.logger.last_item = f"{dupe.name}"

            self.tri_method = triangulation_method(dupe)
            self.sequential_faces(dupe, original)
        
        if transparency:
            normal_graph = bpy.context.evaluated_depsgraph_get()
            for dupe, original in transparency:
                eval_obj  = dupe.evaluated_get(normal_graph)
                dupe.data = bpy.data.meshes.new_from_object(
                            eval_obj, 
                            preserve_all_data_layers=True,
                            depsgraph=normal_graph)

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
        vert_to_faces: list[set[BMFace]]       = [set() for _ in range(len(bm.verts))]
        for tri in bm.faces:
            vert_indices = set()
            for vert in tri.verts:
                vert_indices.add(vert.index)
                vert_to_faces[vert.index].add(tri)
            tri_to_verts[tri] = vert_indices
            
        ordered_faces = {}
        new_index = 0
        
        for face_verts, tri_count in original_faces:
            face_count = 0

            if tri_count > 2:
                # Checks if faces shares a vertex.
                adjacent_faces: set[BMFace] = {tri for vert in face_verts for tri in vert_to_faces[vert]}
                
            else:
                # Checks if faces shares an edge.
                face_shared_verts = Counter(tri for vert in face_verts for tri in vert_to_faces[vert])
                adjacent_faces = {tri for tri, count in face_shared_verts.items() if count >= 2}
            
            for tri in adjacent_faces:
                if tri not in ordered_faces and tri_to_verts[tri] <= face_verts:
                    ordered_faces[tri] = new_index
                    new_index += 1
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
   
    def handle_shape_keys(self, shape_keys: list[tuple[Object, Object, list[ShapeKey]]]) -> None:
        if self.logger:
            self.logger.log("Retaining shape keys...", 2)

        vert_mismatches = []
        for dupe, original, keys in shape_keys:
            if len(original.data.vertices) != len(dupe.data.vertices):
                vert_mismatches.append((dupe, original, keys))
                continue

            for key in keys:
                if self.logger:
                    self.logger.last_item = f"{dupe.name}: Shape {key.name}"
                self._keep_shapes(original, dupe, key.name)

        if vert_mismatches:
            if self.logger:
                self.logger.log("-> Accounting for vert mismatch...", 2)
            self._shape_vert_mismatch(vert_mismatches)

    def _keep_shapes(self, original: Object, dupe: Object, key_name: str) -> None:
        if not dupe.data.shape_keys:
            dupe.shape_key_add(name="Basis")

        new_shape = dupe.shape_key_add(name=key_name)
        
        coords = get_shape_mix(original, key_name)
      
        new_shape.data.foreach_set("co", coords)

    def _shape_vert_mismatch(self, vert_mismatches: list[tuple[Object, Object, list[ShapeKey]]]) -> None:
        """
        We take all meshes with a vert mismatch with its original mesh and do a single depsgraph update to get the evaluated shapes we want.
        """
        temp_copies: dict[Object, dict[str, Object]] = defaultdict(dict)

        if self.logger:
            self.logger.log("-> Creating temp objects...", 2)

        for dupe, original, keys in vert_mismatches:
            for key in keys:
                temp_copy:Object = quick_copy(original, key.name)
                temp_copies[dupe][key.name] = temp_copy

        shape_graph = bpy.context.evaluated_depsgraph_get()

        if self.logger:
            self.logger.log("-> Applying shape keys...", 2)

        for dupe, copies in temp_copies.items():
            for key_name, copy in copies.items():
                if self.logger:
                    self.logger.last_item = f"{dupe.name}: Shape {key_name}"

                try:
                    eval_obj   = copy.evaluated_get(shape_graph)
                    mesh       = bpy.data.meshes.new_from_object(eval_obj)
                    vert_count = len(mesh.vertices)

                    basis_co = np.zeros(vert_count * 3, dtype=np.float32)
                    mesh.vertices.foreach_get("co", basis_co)

                    if not dupe.data.shape_keys:
                        dupe.shape_key_add(name="Basis")

                    new_shape = dupe.shape_key_add(name=key_name)

                    new_shape.data.foreach_set("co", basis_co)

                except Exception as e:
                    if self.logger:
                        self.logger.last_item = (f"Vertex count mismatch for {dupe.name} shape {key_name}.")
                    raise e
                
                finally:
                    try:
                        bpy.data.meshes.remove(mesh, do_unlink=True, do_id_user=True, do_ui_user=True)
                    except:
                        pass

                    safe_object_delete(copy)

    def handle_backfaces(self, backfaces: ObjIterable):
        if self.logger:
            self.logger.log("Creating backfaces...", 2)

        for dupe in backfaces:
            if self.logger:
                self.logger.last_item = f"{dupe.name}"

            if dupe.data.shape_keys:
                backfaces_with_shapes(dupe)    
            else:
                create_backfaces(dupe)

    def handle_vertex_groups(self, dupes: ObjIterable):
        if self.logger:
            self.logger.log("Cleaning vertex groups...", 2)

        prefix = self._get_yas_filter()
        for dupe in dupes:
            for v_group in dupe.vertex_groups:
                if not dupe.parent.data.bones.get(v_group.name):
                    dupe.vertex_groups.remove(v_group)
            if prefix:
                remove_vertex_groups(dupe, prefix)

    def _get_yas_filter(self) -> tuple[str]:
        excluded_groups = set()

        genitalia = [
            'iv_kuritto',                   
            'iv_inshin_l',               
            'iv_inshin_r',               
            'iv_omanko', 
            'iv_koumon',                      
            'iv_koumon_l',                 
            'iv_koumon_r',

            'iv_kintama_phys_l',              
            'iv_kintama_phys_r',    
            'iv_kougan_l',
            'iv_kougan_r',
           
            'iv_funyachin_phy_b',        
            'iv_funyachin_phy_c',        
            'iv_funyachin_phy_d',     
            'iv_ochinko_a',                 
            'iv_ochinko_b',              
            'iv_ochinko_c',              
            'iv_ochinko_d',                 
            'iv_ochinko_e',         
            'iv_ochinko_f',
            ]
        
        if self.remove_yas == "REMOVE":
            return ("iv_", "ya_")
        
        elif self.remove_yas == "NO_GEN":
            excluded_groups.update(genitalia)

        if not self.yas_vag:
            excluded_groups.update(genitalia[:4])

        return tuple(excluded_groups)

    def restore_meshes(self) -> None:
        """We're trying a lot."""
        if self.logger:
            self.logger.log("Restoring scene...", 2)
        
        for obj in self.delete:
            safe_object_delete(obj)
    
        for obj in self.reset:
            try:
                obj.hide_set(state=False)
            except Exception as e:
                if self.logger:
                    self.logger.log_exception(f"Error deleting {obj.name}: {e}")
                else:
                    print(f"Error restoring {obj.name}: {e}")
        try:
            bpy.context.view_layer.update()
        except Exception as e:
            if self.logger:
                    self.logger.log_exception(f"Error updating view layer: {e}")
            else:
                print(f"Error updating view layer: {e}")

 