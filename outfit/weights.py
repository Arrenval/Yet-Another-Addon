import bpy

from bpy.props import StringProperty
from bpy.types import Operator, Object, VertexGroup, Context, ArmatureModifier

class RemoveEmptyVGroups(Operator):                         
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = "Weights"
    bl_description = "Removes Vertex Groups with no weights. Ignores locked groups"
    bl_options = {'UNDO'}

    preset: StringProperty() # type: ignore
    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context:Context):
        old_mode = context.mode
        match old_mode:
            case "PAINT_WEIGHT":
                old_mode = "WEIGHT_PAINT"
            case "EDIT_MESH":
                old_mode = "EDIT"
   
        bpy.ops.object.mode_set(mode='OBJECT')
        prop = context.scene.outfit_props
        obj = context.active_object
        prefixes = ["ya_", "iv_"]
        
        vgroups = {vg.index: False for vg in obj.vertex_groups if not vg.lock_weight}
    
        for v in obj.data.vertices:
            for g in v.groups:
                if g.group in vgroups and g.weight > 0:
                    vgroups[g.group] = True
        
        removed = []
        for i, used in sorted(vgroups.items(), reverse=True):
            if not used:
                removed.append(obj.vertex_groups[i].name)
                obj.vertex_groups.remove(obj.vertex_groups[i])
                

        self.report({'INFO'}, f"Removed {', '.join(removed)}.")
        bpy.ops.object.mode_set(mode=old_mode)
        return {"FINISHED"}
    
class RemoveSelectedVGroups(Operator):
    bl_idname = "ya.remove_select_vgroups"
    bl_label = "Weights"
    bl_description = "Removes selected group and adds the weights to the parent group"
    bl_options = {'UNDO'}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context:Context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context:Context):
        old_mode = context.mode
        if old_mode == 'PAINT_WEIGHT':
            old_mode = 'WEIGHT_PAINT'
        bpy.ops.object.mode_set(mode='OBJECT')
        obj: Object = context.active_object
        old_weight = {}
        if self.preset != "menu" and context.scene.outfit_props.filter_vgroups:
            yas_vgroups  = context.scene.yas_vgroups
            index        = context.scene.yas_vindex
            vertex_group = obj.vertex_groups.get(yas_vgroups[index].name)
        else: 
            vertex_group = obj.vertex_groups.active
       
        parent_vgroup = self.get_parent_group(obj, vertex_group)
        if not parent_vgroup:
            self.report({'ERROR'}, "Skeleton is missing parent bone, or your mesh is not linked to a skeleton.")
            return {'CANCELLED'}
        
        if not obj.vertex_groups.get(parent_vgroup):
            bpy.ops.object.vertex_group_add()
            obj.vertex_groups.active.name = parent_vgroup
       
        new_group = obj.vertex_groups.get(parent_vgroup)
        
        for v in obj.data.vertices:
            try:
                old_weight[v.index] = vertex_group.weight(v.index)
            except:
                continue

        for index, weight in old_weight.items():
            new_group.add(index=[index], weight=weight, type='ADD')

        self.report({'INFO'}, f"Removed {vertex_group.name}, weights added to {parent_vgroup}.")
        obj.vertex_groups.remove(group=vertex_group)
        bpy.ops.object.mode_set(mode=old_mode)
        return {"FINISHED"}

    def get_parent_group(self, obj:Object, vertex_group:VertexGroup) -> str:
        if obj.parent != None and obj.parent.type == "ARMATURE":
            bone = obj.parent.data.bones.get(vertex_group.name)
            if bone:
                return bone.parent.name
            
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                modifier: ArmatureModifier
                armature = modifier.object
                if armature == None:
                    return ""
                bone = armature.data.bones.get(vertex_group.name)
                if bone:
                    return bone.parent.name
                else:
                    return ""
        
                    
CLASSES = [
    RemoveEmptyVGroups,
    RemoveSelectedVGroups,
]