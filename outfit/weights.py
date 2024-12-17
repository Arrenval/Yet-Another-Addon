import bpy

from bpy.props import StringProperty
from bpy.types import Operator, Object, VertexGroup, Context

class RemoveEmptyVGroups(Operator):
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = "Weights"
    bl_description = "Removes unlocked Vertex Groups with no weights. Ignores IVCS and YAS groups"
    bl_options = {'UNDO'}

    preset: StringProperty() # type: ignore
    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == "OBJECT"

    def execute(self, context:Context):
        prop = context.scene.outfit_props
        obj = context.active_object
        prefixes = ["ya_", "iv_"]
        
        for vg in obj.vertex_groups:
            # Ignores yas and ivcs prefixed groups as they could be empty even if you need them later
            if vg.name.startswith(tuple(prefixes)):
                continue
            if vg.lock_weight:
                continue
            if self.preset != "menu" and prop.filter_vgroups and not any(vg.name == name for name in context.scene.yas_vgroups):
                continue
            emptyvg = not any(g.weight > 0 for v in obj.data.vertices for g in v.groups if g.group == vg.index)

            if emptyvg:
                obj.vertex_groups.remove(vg)

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
        return obj is not None and obj.type == 'MESH' and context.mode == "OBJECT"

    def execute(self, context:Context):
        obj = context.active_object
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

        obj.vertex_groups.remove(group=vertex_group)

        for index, weight in old_weight.items():
            new_group.add(index=[index], weight=weight, type='ADD')

        return {"FINISHED"}

    def get_parent_group(self, obj:Object, vertex_group:VertexGroup) -> str:
        if obj.parent.type == "ARMATURE":
            bone = obj.parent.data.bones.get(vertex_group.name)
            if bone:
                return bone.parent.name
            
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
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