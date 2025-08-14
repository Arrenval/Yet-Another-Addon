import bpy

from bpy.props      import StringProperty, BoolProperty, CollectionProperty
from bpy.types      import Operator, PropertyGroup, Context, Object, Mesh, UILayout

from ..props        import get_window_properties, get_outfit_properties
from ..ui.draw      import get_conditional_icon
from ..mesh.shapes  import create_co_cache, create_shape_keys
from ..mesh.objects import quick_copy, evaluate_obj, safe_object_delete


class ModifierShape(Operator):
    """
    Applies selected Modifier to Shape Key.
    """
    bl_idname = "ya.apply_modifier"
    bl_label = "Backfaces"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        modifier:str = get_window_properties().shape_modifiers
        return context.mode == "OBJECT" and modifier != "None"
    
    @classmethod
    def description(cls, context, properties):
        window = get_window_properties()
        obj   = context.active_object
        modifier:str = window.shape_modifiers
        if modifier == "None":
            return "Missing modifier"
        if obj.modifiers[modifier].type == "DATA_TRANSFER":
            return "Applies Data Transfer to current shape key mix"
        else:
            return "Applies Deform Modifier to active shape key"

    def execute(self, context: Context):
        window    = get_window_properties()
        self.keep = window.keep_modifier

        obj          = context.active_object
        modifier:str = window.shape_modifiers
        key_name     = obj.active_shape_key.name

        context.window.cursor_set('WAIT')
        try:
            if obj.modifiers[modifier].type == "DATA_TRANSFER":
                self.apply_data(obj, modifier)
                self.report({'INFO'}, "Applied data transfer.")
            else:
                self.apply_deform(key_name, obj, modifier)
                self.report({'INFO'}, "Modifier Applied to Shape.")
        finally:
            context.window.cursor_set('DEFAULT')
            get_outfit_properties().set_modifiers(context)
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

class ModifierState(PropertyGroup):
    name : StringProperty(default="", name="", description="Modifier name") # type: ignore
    type : StringProperty(default="", name="", description="Modifier type") # type: ignore
    apply: BoolProperty(default=False) # type: ignore
    
class ShapeKeyModifier(Operator):
    bl_idname = "ya.apply_modifier_sk"
    bl_label = ""
    bl_description = "Apply modifiers to meshes with shape keys"

    bl_options = {"UNDO"}

    modifiers: CollectionProperty(type=ModifierState, options={"SKIP_SAVE"}) # type: ignore
    remove   : BoolProperty(
                    default=False, 
                    description="Applies current mix of shape keys alongside selected modifier. Removes all shapes", 
                    options={"HIDDEN","SKIP_SAVE"}
                    ) # type: ignore
    
    all_mod  : BoolProperty(
                    default=False, 
                    description="Applies all modifiers", 
                    options={"HIDDEN","SKIP_SAVE"}
                    ) # type: ignore
    
    @classmethod
    def poll(cls, context: Context):
        return context.mode == "OBJECT" and context.active_object.data.shape_keys
        
    def invoke(self, context: Context, event) -> None:
        obj = context.active_object
        for modifier in obj.modifiers:
            new_modifier = self.modifiers.add()
            new_modifier.name = modifier.name
            new_modifier.type = modifier.type

        context.window_manager.invoke_props_dialog(
            self, 
            confirm_text="Confirm", 
            title="Apply Modifiers", 
            width=300)
        
        return {"RUNNING_MODAL"}

    def execute(self, context: Context) -> None:
        bpy.ops.object.select_all(action="DESELECT")

        self.applied     = []
        self.delete_obj  = set()
        self.delete_mesh = set()
        self.original    = context.active_object
        self.main_copy   = quick_copy(self.original)

        self.delete_obj.add(self.main_copy)
        self.delete_mesh.add(self.main_copy.data)

        for modifier in self.modifiers:
            if modifier.apply or self.all_mod:
                self.main_copy.modifiers[modifier.name].show_viewport = True
                self.applied.append(modifier.name)
            else:
                self.main_copy.modifiers[modifier.name].show_viewport = False
        
        depsgraph = context.evaluated_depsgraph_get()
        evaluate_obj(self.main_copy, depsgraph)

        context.window.cursor_set('WAIT')
        try:
            if not self.remove:
                self.resolve_shapes(context)

            self.delete_mesh.add(self.main_copy.data)
            self.original.data.clear_geometry()
            self.original.select_set(state=True)
            self.main_copy.select_set(state=True)
            bpy.ops.object.join()

            if self.remove:
                self.original.data.shape_keys.animation_data_clear()
                self.original.shape_key_clear()

            for modifier_name in self.applied:
                modifier = self.original.modifiers.get(modifier_name)
                self.original.modifiers.remove(modifier)

        except Exception as e:
            self.report({"ERROR"}, f"Application failed: {e}.")
            return {"FINISHED"}
        
        finally:
            context.window.cursor_set('DEFAULT')
            self._cleanup()

        self.report({"INFO"}, "Modifier applied.")
        return {"FINISHED"}
    
    def resolve_shapes(self, context: Context) -> None:
        base_key   = self.original.data.shape_keys.key_blocks[0].name
        vert_count = len(self.main_copy.data.vertices)
        co_cache   = {}

        temp_copies: dict[str, tuple[Object, Mesh]] = {}

        for key in self.original.data.shape_keys.key_blocks:
            relative_key = key.relative_key.name
            temp_copy    = quick_copy(self.original, key.name)
            old_mesh     = temp_copy.data

            self.delete_obj.add(temp_copy)
            self.delete_mesh.add(old_mesh)

            for modifier in self.modifiers:
                if modifier.apply or self.all_mod:
                    temp_copy.modifiers[modifier.name].show_viewport = True
                else:
                    temp_copy.modifiers[modifier.name].show_viewport = False
            
            for temp_key in temp_copy.data.shape_keys.key_blocks:
                if temp_key.name in (key.name, relative_key):
                    temp_key.value = 1

                else:
                    temp_key.value = 0

            if relative_key not in co_cache:
                co_cache[key.relative_key.name] = None

            temp_copies[key.name] = temp_copy

        self._set_relative_keys(add_keys=True)

        depsgraph = context.evaluated_depsgraph_get()

        create_co_cache(co_cache, temp_copies, self.main_copy, base_key, vert_count, depsgraph)

        create_shape_keys(co_cache, temp_copies, self.main_copy, base_key, vert_count, depsgraph)

    def _set_relative_keys(self, add_keys=False):
        rel_keys = {}
        for key in self.original.data.shape_keys.key_blocks:
            if add_keys:
                self.main_copy.shape_key_add(name=key.name)

            rel_keys[key.name] = key.relative_key.name
        
        for key in self.main_copy.data.shape_keys.key_blocks:
            key.relative_key = self.main_copy.data.shape_keys.key_blocks.get(rel_keys[key.name])

    def _cleanup(self) -> None:
        for mesh in self.delete_mesh:
            try:
                bpy.data.meshes.remove(mesh, do_unlink=True)
            except:
                pass
        
        for obj in self.delete_obj:
            try:
                safe_object_delete(obj)
            except:
                pass

    def draw(self, context: Context) -> None:
        layout:UILayout = self.layout

        row = layout.row()
        split = row.split(factor=0.6)

        icon = get_conditional_icon(self.all_mod)
        split.prop(self, "all_mod", text="All Modifiers", icon=icon)

        icon = get_conditional_icon(self.remove)
        split.prop(self, "remove", text="Apply Shape Mix", icon=icon)

        if not self.all_mod:
            layout.separator(type="LINE", factor=2)

            for modifier in self.modifiers:
                row = layout.row(align=True)
                split = row.split(factor=0.6)
                icon = get_conditional_icon(modifier.apply)
                split.prop(modifier, "apply", icon=icon, text=modifier.name)
                text = modifier.type.replace("_", " ")
                split.label(text=text)
        
        layout.separator(type="LINE")

              
CLASSES = [
    ModifierShape,
    ModifierState,
    ShapeKeyModifier
]