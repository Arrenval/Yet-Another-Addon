import bpy

from bpy.types import Operator, ArmatureModifier
from bpy.props import StringProperty

class SimpleImport(Operator):
    bl_idname = "ya.simple_import"
    bl_label = "Open Import Window"
    bl_description = "Import a file in the selected format"
    bl_options = {'UNDO'}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        gltf = context.scene.file_props.file_gltf
        if gltf:
            bpy.ops.import_scene.gltf('INVOKE_DEFAULT')
        else:
            bpy.ops.import_scene.fbx('INVOKE_DEFAULT', ignore_leaf_bones=True)

        return {"FINISHED"}
    
class SimpleCleanUp(Operator):
    bl_idname = "ya.simple_cleanup"
    bl_label = "Open Import Window"
    bl_description = "Cleanup the selected files"
    bl_options = {'UNDO'}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def execute(self, context):
        props = context.scene.file_props
        self.selected = bpy.context.selected_objects
        armature = props.armatures
        if armature != "None":
            self.fix_parent(armature)
        if props.remove_nonmesh:
            self.remove()
            self.selected = bpy.context.selected_objects
        if props.update_material:
            self.update_material()
        if props.rename_import != "":
            self.rename_import()
        
        
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
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = obj
            obj.select_set(state=True)
            bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
            obj.parent = bpy.data.objects[armature]
            bpy.ops.object.transform_apply(location=True, scale=True, rotation=True)
            

            for modifier in obj.modifiers:
                if modifier.type == "ARMATURE":
                    modifier: ArmatureModifier
                    modifier.object = bpy.data.objects[armature]
                    modifier.name = "Armature"

    def remove(self):
        for obj in self.selected:
            if obj.type == "MESH":
                continue
            bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)

    def rename_import(self) -> None:
        for obj  in self.selected:
            bpy.context.view_layer.objects.active = obj
            if obj.type == "MESH":
                split = obj.name.split()
                split[0] = bpy.context.scene.file_props.rename_import
                obj.name = " ".join(split)

CLASSES = [
    SimpleImport,
    SimpleCleanUp
]      