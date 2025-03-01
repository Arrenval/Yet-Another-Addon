import bpy
import bmesh

from bmesh.types import BMFace
from bpy.types   import Operator, Context, Object, DataTransferModifier
from bpy.props   import StringProperty
from collections import defaultdict

class TagBackfaces(Operator):
    bl_idname = "ya.tag_backfaces"
    bl_label = "Backfaces"
    bl_description = "Tags faces you want to create backfaces for on export"
    bl_options = {'UNDO'}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == "EDIT_MESH"
    
    def execute(self, context):
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        self.obj = bpy.context.active_object

        backface_material = [material.name for material in self.obj.data.materials if material.name.endswith(".BACKFACES")]
        
        if backface_material:
            self.material = backface_material[0][:-10]
        else:
            self.material = self.obj.active_material.name
        
        self.selected_vertices = [v.index for v in self.obj.data.vertices if v.select]

        if not self.selected_vertices:
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'ERROR'}, "Please select vertices to add")
            return {'CANCELLED'}

        if self.preset == 'ADD':
            status = self.add()
        else:
            status = self.remove()

        bpy.ops.object.mode_set(mode='EDIT')
        return status
    
    def add(self):
        group = self.obj.vertex_groups.get("BACKFACES")
        if not group:
            group = self.obj.vertex_groups.new(name="BACKFACES")
        group.add(index=self.selected_vertices, weight=1.0, type='ADD')
        
        if len(self.obj.material_slots) < 3:
            bpy.ops.object.mode_set(mode='EDIT')
            self.add_material()

        return {'FINISHED'}
    
    def add_material(self):
        backface_material = self.material + ".BACKFACES"
        index = self.obj.data.materials.find(backface_material)
        if len(self.obj.material_slots) == 1:
            for material in bpy.data.materials:
                if material.name == backface_material:
                    self.obj.data.materials.append(material)

        if len(self.obj.material_slots) == 1:
            new_material = self.obj.data.materials[0].copy()
            new_material.name = backface_material
            new_material.use_backface_culling = False
            self.obj.data.materials.append(new_material)
            self.obj.active_material_index = self.obj.data.materials.find(backface_material)
            bpy.ops.object.material_slot_assign()
        elif index != -1:
            self.obj.active_material_index = index
            bpy.ops.object.material_slot_assign()

    def remove(self):
        self.obj.vertex_groups.active = self.obj.vertex_groups["BACKFACES"]
        group = self.obj.vertex_groups.get("BACKFACES")
        group.remove(index=self.selected_vertices)

        if any(material.name.endswith(".BACKFACES") for material in self.obj.data.materials):
            index = self.obj.data.materials.find(self.material)
            bpy.ops.object.mode_set(mode='EDIT')
            self.obj.active_material_index = index
            bpy.ops.object.material_slot_assign()

        return {'FINISHED'}

class CreateBackfaces(Operator):
    bl_idname = "ya.create_backfaces"
    bl_label = "Backfaces"
    bl_description = "Creates backfaces for selected meshes. Use this if you don't plan on creating them on export"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        if obj is not None and obj.type == 'MESH':
            backfaces = obj.vertex_groups.get('BACKFACES')
        else:
            backfaces = False
        return context.mode == "OBJECT" and backfaces
    
    def execute(self, context):
        status = self.create_backfaces(context)
        return status
    
    def create_backfaces(self, context:Context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'ERROR'}, "No mesh selected.")
            return {'CANCELLED'}
        created_meshes = [] 

        for obj in selected:
            if not obj.vertex_groups.get("BACKFACES"):
                continue
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(state=True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate()
            backfaces_mesh = bpy.context.active_object

            split = obj.name.split(" ")
            split[0] = "Backfaces"
            group_id = split[-1].split(".")
            group = int(group_id[0])
            part = self.mesh_parts(selected, group) + 1
            group_id[1] = str(part)
            split[-1] = ".".join(group_id)

            backfaces_mesh.name = " ".join(split)
            backfaces_mesh.vertex_groups.active = backfaces_mesh.vertex_groups["BACKFACES"]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.object.vertex_group_deselect()
            bpy.ops.mesh.delete(type='FACE')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.flip_normals()
            created_meshes.append(backfaces_mesh)

        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

    def mesh_parts(self, selected, current_group):
        groups = {}
        for obj in selected:
            split = obj.name.split(" ")[-1]
            group = int(split.split(".")[0])
            part = int(split.split(".")[1])
            if group in groups:
                if part > groups[group]:
                    groups[group] = part
            else:
                groups[group] = part
        return int(groups[current_group])
    
class ModifierShape(Operator):
    bl_idname = "ya.apply_modifier"
    bl_label = "Backfaces"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        modifier:str = context.scene.outfit_props.shape_modifiers
        return context.mode == "OBJECT" and modifier != "None"
    
    @classmethod
    def description(cls, context, properties):
        props = context.scene.outfit_props
        obj = context.active_object
        modifier:str = props.shape_modifiers
        if modifier == "None":
            return "Missing modifier"
        if obj.modifiers[modifier].type == "DATA_TRANSFER":
            return "Applies Data Transfer to current shape key mix"
        else:
            return "Applies Deform Modifier to active shape key"

    def execute(self, context):
        props = context.scene.outfit_props
        self.keep = props.keep_modifier
        obj = context.active_object
        modifier:str = props.shape_modifiers
        key_name = obj.active_shape_key.name

        if obj.modifiers[modifier].type == "DATA_TRANSFER":
            self.apply_data(obj, modifier)
            self.report({'INFO'}, "Applied data transfer.")
        else:
            self.apply_deform(key_name, obj, modifier)
            self.report({'INFO'}, "Modifier Applied to Shape.")
        return {'FINISHED'}
    
    def apply_deform(self, key_name:str, target:Object, modifier:str) -> None:
        bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=self.keep, modifier=modifier)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        key_index = target.data.shape_keys.key_blocks.find(key_name)
        target.active_shape_key_index = key_index
        bpy.ops.mesh.blend_from_shape(shape=modifier, add=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        key_index = target.data.shape_keys.key_blocks.find(modifier)
        target.active_shape_key_index = key_index
        bpy.ops.object.shape_key_remove(all=False)
        key_index = target.data.shape_keys.key_blocks.find(key_name)
        target.active_shape_key_index = key_index

    def apply_data(self, target:Object, modifier:str) -> None:
        old_shape = target.active_shape_key_index
        bpy.ops.object.shape_key_add(from_mix=True)
        target.data.update()
        bpy.ops.object.modifier_apply(modifier=modifier)
        bpy.ops.object.shape_key_remove()
        target.active_shape_key_index = old_shape

class TransparencyOverview(Operator):
    bl_idname = "ya.transparency"
    bl_label = "Transparency"
    bl_options = {'UNDO'}
    bl_description ="Tag mesh as being transparent ingame for extra handling on export. Adjust rendering in Blender when using 'BLENDED'"

    render: StringProperty(default="") # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.render == 'BLENDED':
            return "Simpler Blender render method, less accurate transparency"
        elif properties.render == "DITHERED":
            return "More accurate Blender rendering of transparency. More performance heavy"
        
    def execute(self, context:Context):
        obj = context.active_object
        if obj.active_material:
            material = obj.active_material

        if self.render == 'BLENDED':
            material.surface_render_method = 'BLENDED'
        elif self.render == 'DITHERED':
            material.surface_render_method = 'DITHERED'
        else:
            if "xiv_transparency" not in obj:
                obj["xiv_transparency"] = True
                if obj.active_material:
                    obj.active_material.use_transparency_overlap = True
            elif obj["xiv_transparency"]:
                obj["xiv_transparency"] = False
                if obj.active_material:
                    obj.active_material.use_transparency_overlap = False
            elif not obj["xiv_transparency"]:
                obj["xiv_transparency"] = True
                if obj.active_material:
                    obj.active_material.use_transparency_overlap = True
        return {"FINISHED"}

class TriangulationOrder(Operator):
    bl_idname = "ya.tris"
    bl_label = "Triangulation"
    bl_options = {'UNDO'}

    def execute(self, context):
        self.transparency_adjustment(context)
        return {"FINISHED"}
    
    def transparency_adjustment(self, context:Context) -> None:
        obj = context.active_object
        bpy.ops.object.duplicate()
        obj.hide_set(True)
        dupe = context.active_object

        split    = obj.name.split()
        split[0] = "Transparency"
        dupe.name = " ".join(split) 

        self.sequential_faces(dupe)
        
    def sequential_faces(self, obj:Object) -> None:
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        original_faces = []
        for face in bm.faces:
            # ignores n-gons
            if len(face.verts) > 4:
                continue
            original_faces.append({
                "verts": [v.index for v in face.verts],
                "triangle": False if len(face.verts) == 4 else True
            })
        
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')

        vert_to_faces: dict[int, list] = {}
        for tri in bm.faces:
            for vert in tri.verts:
                vert_to_faces.setdefault(vert.index, [])
                vert_to_faces[vert.index].append(tri)
      
        ordered_faces = {}
        new_index = 0
        for face in original_faces:
            face_verts = set(face["verts"])
            face_count = 0

            adjacent_faces:set[BMFace] = set()
            for vert in face_verts:
                if vert in vert_to_faces:
                    adjacent_faces.update(vert_to_faces[vert])
            
            for tri in adjacent_faces:
                tri_verts = set(vert.index for vert in tri.verts)
                if tri not in ordered_faces and tri_verts.issubset(face_verts):
                    ordered_faces[tri] = new_index
                    new_index += 1
                    face_count += 1
                
                if face_count == 2 or face["triangle"]:
                    break
        
        for face in bm.faces:
            if face not in ordered_faces:
                ordered_faces[face] = new_index
                new_index += 1
        
        bm.faces.sort(key=lambda face:ordered_faces.get(face))
        bm.faces.index_update()

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()


CLASSES = [
    TagBackfaces,
    CreateBackfaces,
    ModifierShape,
    TransparencyOverview,
    TriangulationOrder
]