import bpy
from bpy.types import Operator


class RemoveEmptyVGroups(Operator):
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = "Weights"
    bl_description = "Removes Vertex Groups with no weights. Ignores IVCS and YAS groups"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == "OBJECT"

    def execute(self, context):
        obj = bpy.context.active_object
        prefixes = ["ya_", "iv_"]
        
        for vg in obj.vertex_groups:
            emptyvg = not any(vg.index in [g.group for g in v.groups] for v in obj.data.vertices)
            vgname = vg.name
            
            # Ignores yas and ivcs prefixed groups as they could be empty even if you need them later
            if emptyvg and not vgname.startswith(tuple(prefixes)):
                obj.vertex_groups.remove(vg)

        return {"FINISHED"}


CLASSES = [
    RemoveEmptyVGroups,
]