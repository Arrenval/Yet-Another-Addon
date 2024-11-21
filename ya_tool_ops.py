import bpy

from bpy.types import Operator


class MESH_OT_YA_RemoveEmptyVGroups(Operator):
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = "Weights"
    bl_description = "Removes Vertex Groups with no weights. Ignores IVCS and YAS groups"
    bl_options = {'UNDO'}

    def execute(self, context):
        ob = bpy.context.active_object
        prefixes = ["ya_", "iv_"]
        
        for vg in ob.vertex_groups:
            emptyvg = not any(vg.index in [g.group for g in v.groups] for v in ob.data.vertices)
            vgname = vg.name
            
            # Ignores yas and ivcs prefixed groups
            if emptyvg and not vgname.startswith(tuple(prefixes)):
                ob.vertex_groups.remove(vg)

        return {"FINISHED"}
    