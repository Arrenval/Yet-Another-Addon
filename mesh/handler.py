import re
import bpy
import bmesh
import numpy as np

from bpy.types            import Object, Depsgraph, ShapeKey
from bmesh.types          import BMFace, BMesh
from collections          import defaultdict
from collections.abc      import Iterable 
             
from .shapes              import get_shape_mix
from .weights             import remove_vertex_groups
from .face_order          import get_original_faces, sequential_faces
from ..properties         import get_window_properties, get_devkit_properties
from ..utils.logging      import YetAnotherLogger
from ..utils.objects      import visible_meshobj, safe_object_delete, copy_mesh_object, quick_copy
from ..utils.ya_exception import XIVMeshParentError


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

def backfaces_with_shapes(obj: Object) -> None:
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
    for idx, vert in enumerate(bm.verts):
        vertex_weights[idx] = vert[deform_layer].get(bf_idx, 0)
    
    face_indices = np.array([[v.index for v in face.verts] for face in bm.faces])
    face_weights = vertex_weights[face_indices] 
    faces_mask   = np.any(face_weights > 0, axis=1)

    bm.faces.ensure_lookup_table()

    backfaces = [bm.faces[idx] for idx, is_backface in enumerate(faces_mask) if is_backface]
    
    return backfaces
    

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

    def __init__(self, logger: YetAnotherLogger=None, depsgraph: Depsgraph=None, batch=False):
        props                            = get_window_properties()
        self.depsgraph : Depsgraph       = depsgraph
        self.shapekeys : bool            = props.keep_shapekeys
        self.backfaces : bool            = (props.create_backfaces and props.check_tris)
        self.is_tris   : bool            = props.check_tris
        self.yas_vag   : bool            = True
        self.remove_yas: str             = props.remove_yas
        self.batch     : bool            = batch
        self.torso     : bool            = self.batch and "Chest" in get_window_properties().export_body_slot
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
                no_skeleton.append(obj.name)
                continue
            shape_key    = self.sort_shape_keys(obj) if self.shapekeys and obj.data.shape_keys else []
            transparency = ("xiv_transparency" in obj and obj["xiv_transparency"])
            backfaces    = (self.is_tris and self.backfaces and obj.vertex_groups.get("BACKFACES")) 

            if self.devkit and obj == self.devkit.yam_legs:
                gen_b   = obj.data.shape_keys.key_blocks.get("Gen B")
                gen_c   = obj.data.shape_keys.key_blocks.get("Gen C")
                yas_vag = (gen_b and not gen_b.mute and gen_b.value == 1) or (gen_c and not gen_c.mute and gen_c.value == 1)
                self.yas_vag = yas_vag

            self.reset.append(obj)
            self.meshes[obj] = {
                'shape'       : shape_key, 
                'transparency': transparency, 
                'backfaces'   : backfaces
                }
        
        if no_skeleton:
            raise XIVMeshParentError(f"Missing Skeleton Parent: {', '.join(no_skeleton)}.")

    def devkit_checks(self, visible_obj: Iterable[Object]) -> None:
        for obj in visible_obj:
            if not obj.data.shape_keys:
                continue 
            rue_key  = obj.data.shape_keys.key_blocks.get("Rue")
            buff_key = obj.data.shape_keys.key_blocks.get("Buff")
            if not self.rue and (rue_key and rue_key.mute == False and rue_key.value == 1.0):
                self.rue = True 
            if not self.buff and (buff_key and buff_key.mute == False and buff_key.value == 1.0):
                self.buff = True
            if not self.torso and obj == get_devkit_properties().yam_torso:
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
        fixed_transp = {}
        shape_keys   = []
        backfaces    = []
        dupes        = []

        if not self.depsgraph:
            self.depsgraph = bpy.context.evaluated_depsgraph_get()
        
        transparency = []
        for obj, stats in self.meshes.items():
            if self.logger:
                self.logger.last_item = f"{obj.name}"
            
            if stats["transparency"]:
                transparency.append(obj)

        if transparency:
            fixed_transp = self.handle_transparency(transparency)

        for obj, stats in self.meshes.items():
            if self.logger:
                self.logger.last_item = f"{obj.name}"

            if obj in fixed_transp:
                dupe = fixed_transp[obj]
            else:
                dupe = copy_mesh_object(obj, self.depsgraph)

                if re.search(r"^\d+\.\d+\s", obj.name):
                    name_parts = obj.name.split(" ")
                    dupe.name = " ".join(["ExportMesh"] + name_parts[1:] + name_parts[0:1])
                else:
                    dupe.name = "ExportMesh " + obj.name

            if stats["shape"]:
                shape_keys.append((dupe, obj, stats["shape"]))
            
            if stats["backfaces"]:
                backfaces.append(dupe)
            
            dupes.append(dupe)
            self.delete.append(dupe)
        
        if shape_keys:
            self.handle_shape_keys(shape_keys)
            
        if backfaces:
            self.handle_backfaces(backfaces)

        self.handle_vertex_groups(dupes)

        for obj in self.meshes:
            obj.hide_set(state=True)

    def handle_transparency(self, transparency: list[Object]) -> dict[Object, Object]:
        if self.logger:
            self.logger.log("Fixing face order...", 2)

        fixed_transp = {}
        to_process: list[tuple[Object, list]] = []
        for obj in transparency:
            if self.logger:
                self.logger.last_item = f"{obj.name}"
            
            original_faces = get_original_faces(obj)

            dupe = copy_mesh_object(obj, self.depsgraph)

            if re.search(r"^\d+.\d+\s", obj.name):
                name_parts = obj.name.split(" ")
                dupe.name = " ".join(["ExportMesh"] + name_parts[1:] + name_parts[0:1])
            else:
                dupe.name = "ExportMesh " + obj.name

            fixed_transp[obj] = dupe
            to_process.append((dupe, original_faces))
        
        tri_graph = bpy.context.evaluated_depsgraph_get()
        for dupe, original_faces in to_process:
            eval_obj  = dupe.evaluated_get(tri_graph)
            dupe.data = bpy.data.meshes.new_from_object(
                            eval_obj, 
                            preserve_all_data_layers=True,
                            depsgraph=tri_graph
                            )
            
            sequential_faces(dupe, original_faces)
        
        return fixed_transp
   
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

    def handle_backfaces(self, backfaces: Iterable[Object]):
        if self.logger:
            self.logger.log("Creating backfaces...", 2)

        for dupe in backfaces:
            if self.logger:
                self.logger.last_item = f"{dupe.name}"

            if dupe.data.shape_keys:
                backfaces_with_shapes(dupe)    
            else:
                create_backfaces(dupe)

    def handle_vertex_groups(self, dupes: Iterable[Object]):
        if self.logger:
            self.logger.log("Cleaning vertex groups...", 2)

        prefix = self._get_yas_filter()
        for dupe in dupes:
            for v_group in dupe.vertex_groups:
                if not dupe.parent.data.bones.get(v_group.name):
                    dupe.vertex_groups.remove(v_group)
            if prefix:
                remove_vertex_groups(dupe, dupe.parent, prefix)

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

 