import bpy


from bpy.types     import Operator, Context, Object
from ..properties import get_outfit_properties


class ModifierShape(Operator):
    """
    Applies selected Modifier to Shape Key.
    """
    bl_idname = "ya.apply_modifier"
    bl_label = "Backfaces"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        modifier:str = get_outfit_properties().shape_modifiers
        return context.mode == "OBJECT" and modifier != "None"
    
    @classmethod
    def description(cls, context, properties):
        props = get_outfit_properties()
        obj   = context.active_object
        modifier:str = props.shape_modifiers
        if modifier == "None":
            return "Missing modifier"
        if obj.modifiers[modifier].type == "DATA_TRANSFER":
            return "Applies Data Transfer to current shape key mix"
        else:
            return "Applies Deform Modifier to active shape key"

    def execute(self, context: Context):
        props     = get_outfit_properties()
        self.keep = props.keep_modifier

        obj          = context.active_object
        modifier:str = props.shape_modifiers
        key_name     = obj.active_shape_key.name

        if obj.modifiers[modifier].type == "DATA_TRANSFER":
            self.apply_data(obj, modifier)
            self.report({'INFO'}, "Applied data transfer.")
        else:
            self.apply_deform(key_name, obj, modifier)
            self.report({'INFO'}, "Modifier Applied to Shape.")
        return {'FINISHED'}
    
    def apply_deform(self, key_name: str, target: Object, modifier: str) -> None:
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


CLASSES = [
    ModifierShape,
]