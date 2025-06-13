import re
import bpy
import bmesh

from bpy.types        import Object, ShapeKey, TriangulateModifier
from bmesh.types      import BMFace
from collections      import Counter

from ...properties    import get_file_properties, get_devkit_properties
from ...utils.objects import visible_meshobj


def verify_target(obj: Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(state=True)
    bpy.ops.object.mode_set(mode='OBJECT')

def activate_shape_key(obj: Object, key: ShapeKey) -> None:
    obj.data.shape_keys.key_blocks[key.name].driver_remove("mute")
    obj.data.shape_keys.key_blocks[key.name].driver_remove("value")
    obj.data.shape_keys.key_blocks[key.name].mute  = False
    obj.data.shape_keys.key_blocks[key.name].value = 1.0

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

    def __init__(self):
        props                              = get_file_properties()
        self.shapekeys   : bool            = props.keep_shapekeys
        self.backfaces   : bool            = props.create_backfaces
        self.yas         : bool            = False
        self.reset       : list[Object]    = []
        self.delete      : list[Object]    = []
        self.tri_method  : tuple[str, str] = ('BEAUTY', 'BEAUTY')
        self.handler_list: list[dict[str, Object | list | bool]] = []                       
    
    def prepare_meshes(self) -> None:
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
                print(obj.name)
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
            transparency = True if "xiv_transparency" in obj and obj["xiv_transparency"] else False
            backfaces    = True if self.backfaces and obj.vertex_groups.get("BACKFACES") else False
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
        
                    print((obj.name, key.name))
                    shape_key.append(key)

        

            verify_target(obj)

            bpy.ops.object.duplicate()
            dupe = bpy.context.active_object
            
            if re.search(r"^\d+.\d+\s", obj.name):
                name_parts = obj.name.split(" ")
                dupe.name = " ".join(["ExportMesh"] + name_parts[1:] + name_parts[0:1])
            else:
                dupe.name = "ExportMesh " + obj.name
                
            if dupe.data.shape_keys:
                for key in dupe.data.shape_keys.key_blocks:
                    key.lock_shape = False
            
            self.handler_list.append({
                'dupe'        : dupe, 
                'original'    : obj, 
                'shape'       : shape_key, 
                'transparency': transparency, 
                'backfaces'   : backfaces})
            
            self.reset.append(obj)
            self.delete.append(dupe)
                     
    def process_meshes(self):

        for entry in self.handler_list:
            obj = entry['dupe']
            if entry['transparency']:
                if not self.triangulation_check(obj):
                    verify_target(obj)
                    self.sequential_faces(obj)

            if entry['shape']:
                verify_target(obj)
                # print((obj.name, obj.data.shape_keys))
                self.shape_key_keeper(obj, entry["shape"])
            else:
                verify_target(obj)
                self.apply_modifiers(obj)
            
            if entry['backfaces']:
                verify_target(obj)
                self.create_backfaces(obj)
                
            entry['original'].hide_set(state=True)

            if self.yas:
                ivcs_mune(obj)

    def triangulation_check(self, obj:Object)-> bool:
            verify_target(obj)
            self.tri_method = ('BEAUTY', 'BEAUTY')
            for modifier in reversed(obj.modifiers):
                if modifier.type == "TRIANGULATE" and modifier.show_viewport:
                    modifier: TriangulateModifier
                    self.tri_method = (modifier.quad_method, modifier.ngon_method)
                    bpy.ops.object.modifier_remove(modifier=modifier.name)
                    break
            
            triangulated = all(len(poly.vertices) <= 3 for poly in obj.data.polygons)

            return triangulated
    
    def apply_modifiers(self, obj:Object, data_transfer=True) -> None:
        # We initially look for inactive modifiers so we can assume the remaining ones should be retained.
        # This is done to avoid any unforeseen behaviour when removing a driver.
        inactive = [modifier for modifier in obj.modifiers if not modifier.show_viewport]
        for modifier in inactive:
            bpy.ops.object.modifier_remove(modifier=modifier.name)

        modifiers = [modifier for modifier in obj.modifiers if modifier.type != "ARMATURE"]
        if obj.data.shape_keys:
            bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
            obj.data.update()
        
        for modifier in modifiers:
            if not data_transfer and modifier.type == "DATA_TRANSFER":
                continue

            try:
                modifier.driver_remove("show_viewport")
            except:
                pass
            modifier.show_viewport = True
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except:
                bpy.ops.object.modifier_remove(modifier=modifier.name)
    
    def sequential_faces(self, obj:Object) -> None:
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        original_faces: list[tuple[set[int], int]] = [(set(v.index for v in face.verts), len(face.verts) - 2) for face in bm.faces]
        
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method=self.tri_method[0], ngon_method=self.tri_method[1])

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

    def shape_key_keeper(self, obj:Object, xiv_key:list[ShapeKey]) -> None:
        # to_join are the temporary dupes with the shape keys activated that will be merged into the export mesh (obj)
        to_join     :list[tuple[Object, str]] = []

        for key in xiv_key:
            verify_target(obj)
            bpy.ops.object.duplicate()
 
            shapekey_dupe = bpy.context.selected_objects[0]
            activate_shape_key(shapekey_dupe, key)
            to_join.append((shapekey_dupe, key.name))

        if to_join:
            verify_target(obj)
            self.apply_modifiers(obj)

            for dupe, key_name in to_join:
                if len(obj.data.vertices) != len(dupe.data.vertices):
                    verify_target(dupe)
                    self.apply_modifiers(dupe, data_transfer=False)

                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(state=True)

                else:
                    dupe.select_set(state=True)

                bpy.ops.object.join_shapes()
                obj.data.shape_keys.key_blocks[-1].name = key_name
                bpy.data.objects.remove(dupe, do_unlink=True, do_id_user=True, do_ui_user=True)

    def create_backfaces(self, obj:Object) -> None: 
        obj.vertex_groups.active = obj.vertex_groups["BACKFACES"]
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.duplicate()
        bpy.ops.mesh.flip_normals()
        bpy.ops.object.mode_set(mode='OBJECT')
        
    def restore_meshes(self) -> None:
        for obj in self.delete:
            try:
                bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
            except:
                pass
        
        for obj in self.reset:
            try:
                obj.hide_set(state=False)
            except:
                pass

 