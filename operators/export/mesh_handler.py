import re
import bpy
import bmesh
import numpy as np

from numpy            import float32
from numpy.typing     import NDArray
from bpy.types        import Object, TriangulateModifier, Depsgraph, Modifier, DataTransferModifier
from bmesh.types      import BMFace, BMesh
from collections      import Counter

from ...properties    import get_file_properties, get_devkit_properties
from ...utils.objects import visible_meshobj
from ...utils.logging import YetAnotherLogger


def copy_mesh_object(source_obj: Object, depsgraph: Depsgraph) -> Object:
    """Fast mesh copy without depsgraph update, specific for mesh handler due to extra modifier handling"""

    modifier_state: dict[Modifier, tuple[bool, bool]] = {}

    for modifier in source_obj.modifiers:
        modifier_state[modifier] = (modifier.show_viewport, modifier.show_render)

        if modifier.type == "ARMATURE":
            modifier.show_render   = False
            modifier.show_viewport = False

    eval_obj  = source_obj.evaluated_get(depsgraph)
    temp_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    
    new_mesh = temp_mesh.copy()
    new_obj  = source_obj.copy()

    new_obj.data = new_mesh
    
    eval_obj.to_mesh_clear()
    new_obj.modifiers.clear()

    for collection in source_obj.users_collection:
        collection.objects.link(new_obj)

    new_obj.parent = source_obj.parent
    
    armature        = new_obj.modifiers.new(name="Armature", type="ARMATURE")
    armature.object = source_obj.parent

    for modifier, (viewport, render) in modifier_state.items():
        modifier.show_viewport = viewport
        modifier.show_render   = render

    # If we don't do this, we will crash later.
    if new_obj.animation_data:
        new_obj.animation_data_clear()
        
    if new_obj.data and hasattr(new_obj.data, 'shape_keys') and new_obj.data.shape_keys:
        if new_obj.data.shape_keys.animation_data:
            new_obj.data.shape_keys.animation_data_clear()
    
    # Not this, this is just annoying sometimes
    if new_obj.data.shape_keys:
        new_obj.shape_key_clear()

    return new_obj
    
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

def ivcs_mune(obj: Object) -> None:
    right = obj.vertex_groups.get("j_mune_r", False)
    left  = obj.vertex_groups.get("j_mune_l", False)
    
    if right:
        right.name = "iv_c_mune_r"

    if left:
        left.name = "iv_c_mune_l"

class MeshHandler:
    """
    This class takes all visible meshes in a Blender scene and runs various logic on them to retain/add properties needed for XIV models. 
    It's designed to work with my export operators to save and restore the Blender scene when the class is done with its operations.
    It works non-destructively by duplicating the initial models, hiding them, then making the destructice edits on the duplicates.
    1. prepare_meshes saves the scene visibility state, sorts meshes, and creates dupes to work on.
    2. process_meshes are the actual operations.
    3. restore_meshes restores the initial Blender scene from before prepare_meshes.
    Each function should be called separately on the same instance of the class in the listed order.

    """

    def __init__(self, logger: YetAnotherLogger=None):
        props                            = get_file_properties()
        self.depsgraph : Depsgraph       = bpy.context.evaluated_depsgraph_get()
        self.shapekeys : bool            = props.keep_shapekeys
        self.backfaces : bool            = props.create_backfaces
        self.is_tris   : bool            = props.check_tris
        self.yas       : bool            = False
        self.reset     : list[Object]    = []
        self.delete    : list[Object]    = []
        self.tri_method: tuple[str, str] = ("BEAUTY", "BEAUTY")

        self.logger    : YetAnotherLogger = logger
        self.meshes    : dict[Object, dict[str, list | bool]] = {}                       
    
    def prepare_meshes(self) -> None:
        if self.logger:
            self.logger.log("Preparing meshes...", 2)
        visible_obj = visible_meshobj()

        # Bools for deciding which waist shape keys to keep. Only relevant for Yet Another Devkit.
        rue    = False
        buff   = False
        torso  = False
        devkit = get_devkit_properties()
        
        if devkit:
            self.yas = devkit.controller_yas_chest
            for obj in visible_obj:
                if not obj.data.shape_keys:
                    continue 
                rue_key  = obj.data.shape_keys.key_blocks.get("Rue")
                buff_key = obj.data.shape_keys.key_blocks.get("Buff")
                if rue_key and rue_key.mute == False and rue_key.value == 1.0:
                    rue = True 
                if buff_key and buff_key.mute == False and buff_key.value == 1.0 :
                    buff = True
                if obj.data.name == "Torso":
                    torso = True

        for obj in visible_obj:
            shape_key    = []
            transparency = ("xiv_transparency" in obj and obj["xiv_transparency"])
            backfaces    = (self.is_tris and self.backfaces and obj.vertex_groups.get("BACKFACES")) 
            if self.shapekeys and obj.data.shape_keys:
                for key in obj.data.shape_keys.key_blocks:
                    if not key.name.startswith("shp"):
                        continue
                    if rue:
                        if key.name[5:8] == "wa_":
                        # Rue does not use any waist shape keys.
                            continue
                        if key.name[5:8] == "yab":
                            continue  
                    else:
                        if key.name[5:8] == "rue":
                            continue

                    if devkit and key.name[5:8] == "wa_":
                        # We check for buff and torso because in the case where the torso and waist are present we
                        # remove the abs key from both body parts.
                        if not buff and torso and key.name.endswith("_yabs"):
                            continue

                        # We don't have to check for torso here because it's implicitly assumed to be present when buff is True.
                        # If waist and torso are present we then remove the yab key.
                        if buff and key.name.endswith("_yab"):
                            continue
        
                    shape_key.append(key)
            
            self.reset.append(obj)
            self.meshes[obj] = {
                'shape'       : shape_key, 
                'transparency': transparency, 
                'backfaces'   : backfaces
                }
                  
    def process_meshes(self) -> None:
        dupe: Object
        transparency = []
        shape_keys   = []
        backfaces    = []
      
        for obj, stats in self.meshes.items():
            if self.logger:
                self.logger.last_item = f"{obj.name}"
            dupe = copy_mesh_object(obj, self.depsgraph)

            if self.yas:
                ivcs_mune(dupe)

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
            
            self.delete.append(dupe)
            obj.hide_set(state=True)
        
        if self.logger and transparency:
            self.logger.log("Fixing face order...", 2)

        for dupe, original in transparency:
            if self.logger:
                self.logger.last_item = f"{dupe.name}"

            self.tri_method = triangulation_method(dupe)
            self.sequential_faces(dupe, original)
        
        if self.logger and shape_keys:
            self.logger.log("Retaining shape keys...", 2)

        for dupe, original, keys in shape_keys:
            for key in keys:
                if self.logger:
                    self.logger.last_item = f"{dupe.name}: Shape {key.name}"

                self.keep_shapes(original, dupe, key.name)

        if self.logger and backfaces:
            self.logger.log("Creating backfaces...", 2)

        for dupe in backfaces:
            if self.logger:
                self.logger.last_item = f"{dupe.name}"

            if dupe.data.shape_keys:
                self.create_backfaces_sk(dupe)
            else:
                self.create_backfaces(dupe)

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

        tri_to_verts: dict[BMFace, set[int] ] = {}
        vert_to_faces: list[set[BMFace]] = [set() for _ in range(len(bm.verts))]
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

        mesh.update()    

        # We do it the simple way because I do not want to learn how to calculate normals right now and bmesh.ops.triangulate is bugged.
        self._restore_normals(dupe, original)   

    def _restore_normals(self, obj: Object, original: Object) -> None:
        modifier:DataTransferModifier = obj.modifiers.new(name="keep_transparent_normals", type="DATA_TRANSFER")
        modifier.object           = original
        modifier.use_loop_data    = True
        modifier.data_types_loops = {"CUSTOM_NORMAL"}
        modifier.loop_mapping     = "NEAREST_POLYNOR"

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    
    def _keep_shapes(self, original: Object, dupe: Object, key_name: str) -> None:
        if len(original.data.vertices) == len(dupe.data.vertices):
            source_obj = original
        else:
            source_obj = self.copy_mesh_object(original, self.depsgraph)
            self.delete.append(source_obj)

        if not dupe.data.shape_keys:
            dupe.shape_key_add(name="Basis")

        new_shape = dupe.shape_key_add(name=key_name)
        
        coords = get_shape_mix(source_obj, key_name)
      
        new_shape.data.foreach_set("co", coords)
        dupe.data.update()
       
    def create_backfaces(self, obj:Object) -> None:
        """Assumes the mesh is triangulated to get the faces from _get_backfaces."""
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        bf_idx    = obj.vertex_groups["BACKFACES"].index
        backfaces = self._get_backfaces(bm, bf_idx)
       
        duplicates = bmesh.ops.duplicate(bm, geom=backfaces)

        duplicated_faces = [geo for geo in duplicates["geom"] if isinstance(geo, bmesh.types.BMFace)]

        bmesh.ops.reverse_faces(bm, faces=duplicated_faces)
 
        bm.to_mesh(mesh)
        bm.free()

        mesh.update()

    def _get_backfaces(self, bm: BMesh, bf_idx: int) -> list[BMFace]:
        deform_layer = bm.verts.layers.deform.active
  
        vertex_weights = np.zeros(len(bm.verts), dtype=np.float32)
        for i, vert in enumerate(bm.verts):
            vertex_weights[i] = vert[deform_layer].get(bf_idx, 0)
        
        face_indices = np.array([[v.index for v in face.verts] for face in bm.faces])
        
        face_weights = vertex_weights[face_indices] 
        
        faces_mask = np.any(face_weights > 0, axis=1)

        bm.faces.ensure_lookup_table()

        backfaces = [bm.faces[i] for i, is_backface in enumerate(faces_mask) if is_backface]
        
        return backfaces
    
    def create_backfaces_sk(self, obj: Object):
        bpy.context.view_layer.objects.active = obj
        obj.vertex_groups.active = obj.vertex_groups["BACKFACES"]
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.duplicate()
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')

    def restore_meshes(self) -> None:
        """We're trying a lot."""
        if self.logger:
            self.logger.log("Restoring scene...", 2)
        
        for obj in self.delete:
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            try:
                if obj.parent:
                    obj.parent = None
                
                for collection in obj.users_collection:
                    collection.objects.unlink(obj)
                    
            except Exception as e:
                if self.logger:
                    self.logger.log_exception(f"Error preparing {obj.name} for deletion: {e}")
                else:
                    print(f"Error preparing {obj.name} for deletion: {e}")
        
        try:
            bpy.context.view_layer.update()
        except:
            if self.logger:
                    self.logger.log_exception(f"Error updating view layer: {e}")
            else:
                print(f"Error updating view layer: {e}")
        
        for obj in self.delete:
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            try:
                bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
            except Exception as e:
                if self.logger:
                    self.logger.log_exception(f"Error deleting {obj.name}: {e}")
                else:
                    print(f"Error deleting {obj.name}: {e}")
        
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

 