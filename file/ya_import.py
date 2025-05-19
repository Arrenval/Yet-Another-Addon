import re
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
        if props.update_material:
            self.update_material()
        if props.rename_import != "":
            self.rename_import()
        if props.reorder_mesh_id:
            # This just looks for the default TT naming convention and corrects it
            for obj in self.selected:
                if re.search(r"\s\d+.\d+$", obj.name):
                    name_parts = obj.name.split(" ")
                    if name_parts[-2] == "Part":
                        end_idx = -2
                    else:
                        end_idx = -1
                    obj.name = " ".join(name_parts[-1:] + name_parts[0:end_idx])
        if props.remove_nonmesh:
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
            if obj.parent == bpy.data.objects[armature]:
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
                if re.search(r"^\d+.\d+\s", obj.name):
                    id_index = 1
                elif re.search(r"\s\d+.\d+$", obj.name):
                    id_index = 0
                else:
                    obj.name = bpy.context.scene.file_props.rename_import
                    continue
                split = obj.name.split()
                split[id_index] = bpy.context.scene.file_props.rename_import
                obj.name = " ".join(split)

CLASSES = [
    SimpleImport,
    SimpleCleanUp
]      