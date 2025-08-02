import re
import bpy

from bpy.types       import Operator, ArmatureModifier, Context
from bpy.props       import StringProperty
from ..properties    import get_file_properties, get_window_properties
from ..preferences   import get_prefs
from ..utils.objects import safe_object_delete


class SimpleImport(Operator):
    bl_idname = "ya.simple_import"
    bl_label = "Open Import Window"
    bl_description = "Import a file in the selected format"
    bl_options = {"UNDO"}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context: Context):
        return context.mode == "OBJECT"
    
    def invoke(self, context, event):
        self.cleanup = get_prefs().auto_cleanup
        self.props   = get_window_properties()
        setattr(self.props, "waiting_import", False)

        format = get_window_properties().file_format

        if format == "GLTF":
            bpy.ops.import_scene.gltf("INVOKE_DEFAULT")
        elif format == "FBX":
            bpy.ops.import_scene.fbx("INVOKE_DEFAULT")
        
        if self.cleanup:
            bpy.ops.object.select_all(action="DESELECT")
            self.pre_import_objects = len(context.scene.objects)
            self._timer = context.window_manager.event_timer_add(0.1, window=context.window)
            context.window_manager.modal_handler_add(self)
            setattr(self.props, "waiting_import", True)
            bpy.context.view_layer.update()
            
        return {"RUNNING_MODAL"}

    def modal(self, context: Context, event):
        if event.type == "TIMER":
            if len(context.scene.objects) > self.pre_import_objects:
                context.window_manager.event_timer_remove(self._timer)
                return self.execute(context)
    
        elif event.type == "ESC" and event.value == "PRESS":
            context.window_manager.event_timer_remove(self._timer)
            setattr(self.props, "waiting_import", False)
            return {"CANCELLED"}
        
        return {"PASS_THROUGH"}

    def execute(self, context):
        bpy.ops.ya.simple_cleanup("EXEC_DEFAULT")
        setattr(self.props, "waiting_import", False)
        bpy.context.view_layer.update()
        return {"FINISHED"}
    
class SimpleCleanUp(Operator):
    bl_idname = "ya.simple_cleanup"
    bl_label = "Open Import Window"
    bl_description = "Cleanup the selected files"
    bl_options = {"UNDO", "REGISTER"}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        self.window = get_window_properties()
        self.props  = get_file_properties()
        self.prefs  = get_prefs()
        self.selected = bpy.context.selected_objects

        if not self.selected:
            return {"CANCELLED"}
        
        if self.props.import_armature:
            self.fix_parent(self.props.import_armature)

        if self.prefs.update_material:
            self.update_material()

        if self.window.rename_import.strip() != "":
            self.rename_import()

        if self.prefs.reorder_meshid:
            # This just looks for the default TT naming convention and corrects it
            for obj in self.selected:
                if re.search(r"\s\d+.\d+$", obj.name):
                    name_parts = obj.name.split(" ")
                    if name_parts[-2] == "Part":
                        end_idx = -2
                    else:
                        end_idx = -1
                    obj.name = " ".join(name_parts[-1:] + name_parts[0:end_idx])
        if self.prefs.remove_nonmesh:
            self.remove()

        return {"FINISHED"}

    def update_material(self) -> None:
        for obj in self.selected:
            bpy.context.view_layer.objects.active = obj
            if obj.type == "MESH":
                material = obj.active_material
                material.surface_render_method = "BLENDED"
                material.use_backface_culling = True
                material.roughness = 0.5
                material.metallic = 0.0
                material.use_transparency_overlap = False
                for node in material.node_tree.nodes:
                    if node.inputs:
                        try:
                            node.inputs["Metallic"].default_value = 0.0
                            node.inputs["Roughness"].default_value = 0.5
                        except:
                            pass

    def fix_parent(self, armature) -> None:
        for obj in self.selected:
            if obj.type != "MESH":
                continue
            if obj.parent == armature:
                continue
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = obj
            obj.select_set(state=True)
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
            obj.parent = armature
            bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
            
            for modifier in obj.modifiers:
                if modifier.type == "ARMATURE":
                    modifier: ArmatureModifier
                    modifier.object = armature
                    modifier.name = "Armature"

    def remove(self):
        for obj in self.selected:
            if obj.type == "MESH":
                continue
            if self.props.import_armature == obj:
                continue
            if not self.props.import_armature and obj.type == 'ARMATURE':
                continue
            safe_object_delete(obj)
        
    def rename_import(self) -> None:
        for obj  in self.selected:
            bpy.context.view_layer.objects.active = obj
            if obj.type == "MESH":
                if re.search(r"^\d+.\d+\s", obj.name):
                    id_index = 1
                elif re.search(r"\s\d+.\d+$", obj.name):
                    id_index = 0
                else:
                    obj.name = self.window.rename_import
                    continue
                split = obj.name.split()
                split[id_index] = self.window.rename_import
                obj.name = " ".join(split)


CLASSES = [
    SimpleImport,
    SimpleCleanUp
]      