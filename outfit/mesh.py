import bpy

from bpy.types import Operator, Context, Object
from bpy.props import StringProperty

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

        if self.obj.material_slots[0].name.endswith(".BACKFACES"):
            self.obj.active_material_index = 0
            bpy.ops.object.material_slot_move(direction="DOWN")

        self.material = self.obj.active_material
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
        backface_material_name = self.material.name + ".BACKFACES"
        index = self.obj.data.materials.find(backface_material_name)
        if len(self.obj.material_slots) == 1:
            for material in bpy.data.materials:
                if material.name == backface_material_name:
                    self.obj.data.materials.append(material)

        if len(self.obj.material_slots) == 1:
            backface_material = self.material.copy()
            backface_material.name = backface_material_name
            backface_material.use_backface_culling = False
            self.obj.data.materials.append(backface_material)
            self.obj.active_material_index = index
            bpy.ops.object.material_slot_assign()
        elif len(self.obj.material_slots) == 2 and self.obj.material_slots[1].name.endswith(".BACKFACES"):
            self.obj.active_material_index = index
            bpy.ops.object.material_slot_assign()

    def remove(self):
        self.obj.vertex_groups.active = self.obj.vertex_groups["BACKFACES"]
        group = self.obj.vertex_groups.get("BACKFACES")
        group.remove(index=self.selected_vertices)

        if not self.obj.material_slots[0].name.endswith(".BACKFACES"):
            bpy.ops.object.mode_set(mode='EDIT')
            self.obj.active_material_index = 0
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
        obj_backfaces = []
        created_meshes = [] 

        for obj in selected:
            backfaces = obj.vertex_groups.get("BACKFACES")
            if backfaces:
                obj_backfaces.append(obj)
        
        for obj in obj_backfaces:
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
    
class ModifierActiveShape(Operator):
    bl_idname = "ya.apply_modifier"
    bl_label = "Backfaces"
    bl_description = "Applies Deform Modifier to active shape key"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        props = context.scene.outfit_props
        self.keep = props.keep_modifier
        obj = context.active_object
        modifier = props.deform_modifiers
        key_name = obj.active_shape_key.name

        self.apply_modifier(key_name, obj, modifier)
        self.report({'INFO'}, "Modifier Applied to Shape.")
        return {'FINISHED'}
    
    def apply_modifier(self, key_name:str, target:Object, modifier:str) -> None:
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

CLASSES = [
    TagBackfaces,
    CreateBackfaces,
    ModifierActiveShape
]