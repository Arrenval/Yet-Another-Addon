import re
import bpy

from bpy.types import Operator, Object
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty

from ..props   import get_studio_props


class Attributes(Operator):
    bl_idname = "ya.attributes"
    bl_label = "Attributes"
    bl_description = ""
    bl_options = {"UNDO"}

    obj: StringProperty() # type: ignore
    attr: StringProperty() # type: ignore
    user_input: StringProperty(name="", default="atr_") # type: ignore
    selection: EnumProperty(items=(
        ("atr_nek", "Neck", ""),
        ("atr_ude", "Elbow", ""),
        ("atr_hij", "Wrist", ""),
        None,
        ("atr_arm", "Glove", ""),
        None,
        ("atr_kod", "Waist", ""),
        ("atr_hiz", "Knee", ""),
        ("atr_sne", "Shin", ""),
        None,
        ("atr_leg", "Boot", ""),
        ("atr_lpd", "Knee Pad", "")),
        name=""
    ) # type: ignore
    custom: BoolProperty(default=False) # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.attr == "NEW":
            return "Add new attribute to the object"
        else:
            return "Remove this attribute"

    def invoke(self, context, event):
        if self.attr == "NEW":
            bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", width=1)
        else:
            self.execute(context)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        obj: Object = bpy.data.objects[self.obj]
        layout = self.layout
        layout.prop(self, "custom", text="Custom", icon="FILE_TEXT")
        if self.custom:
            layout.prop(self, "user_input")
        else:
            layout.prop(self, "selection")
            if self.selection in obj:
                layout.label(text="Attribute already exists.")

    def execute(self, context):
        obj: Object = bpy.data.objects[self.obj]

        if self.attr == "NEW":
            if self.custom:
                self.attr = self.user_input
            else:
                self.attr = self.selection
        
        if self.attr in obj and obj[self.attr]:
            bpy.ops.wm.properties_remove(data_path="object", property_name=self.attr)
        else:
            obj[self.attr] = True
        
        return {'FINISHED'}
    
class ChangeObjectName(Operator):
    bl_idname = "ya.overview_name"
    bl_label = "Name"
    bl_description = "Change name of the object"
    bl_options = {"UNDO"}

    obj: StringProperty() # type: ignore
    type: StringProperty() # type: ignore
    user_input: StringProperty(name="", default="") # type: ignore

    def invoke(self, context, event):
        bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=2)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self, context):
        obj: Object = bpy.data.objects[self.obj]
        name_parts = obj.name.split(" ")

        if self.type == "NAME":
            obj.name = f"{self.user_input} {name_parts[-1]}"

        return {'FINISHED'}
    
class ChangeGroupPart(Operator):
    bl_idname = "ya.overview_group"
    bl_label = "Group/Part"
    bl_description = "Change group/part of the object"
    bl_options = {"UNDO"}

    obj: StringProperty() # type: ignore
    type: StringProperty() # type: ignore
    user_input: IntProperty(name="", default=0, min=0, max=99) # type: ignore

    @classmethod
    def description(cls, context, properties):
        if "GROUP" in properties.type:
            return "Change group of the object"
        if "PART" in properties.type:
            return "Change part of the object"
        else:
            return "Change group/part of the object"
        
    def invoke(self, context, event):
        obj: Object = bpy.data.objects[self.obj]

        if re.search(r"^\d+.\d+\s", obj.name):
            self.id_index = 0
        else:
            self.id_index = -1

        self.name_parts = obj.name.split(" ")
        self.group = int(self.name_parts[self.id_index].split(".")[0])
        self.part  = int(self.name_parts[self.id_index].split(".")[1])
        
        if self.type == "GROUP":
            self.user_input = self.group
        elif self.type == "PART":
            self.user_input  = self.part
        else:
            return self.execute(context)
        bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=1)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self, context):
        obj: Object = bpy.data.objects[self.obj]

        match self.type:
            case "PART":
                self.part = self.user_input
            case "GROUP":
                self.group = self.user_input
            case "INC_PART":
                self.part += 1
            case "DEC_PART":
                self.part -= 1
            case "INC_GROUP":
                self.group += 1
            case "DEC_GROUP":
                self.group -= 1

        self.name_parts[self.id_index] = f"{self.group if self.group >= 0 else 0}.{self.part if self.part >= 0 else 0}"
        obj.name = " ".join(self.name_parts)
     
        return {'FINISHED'}
    
class MeshMaterial(Operator):
    bl_idname = "ya.mesh_material"
    bl_label = "Material"
    bl_description = "Tags faces you want to create backfaces for on export"
    bl_options = {"UNDO"}

    mesh: IntProperty(default=0, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    def execute(self, context):
        model_props = get_studio_props().model
        while self.mesh >= len(model_props.meshes):
            mesh_idx = len(model_props.meshes)
            mesh     = model_props.meshes.add()
            mesh.idx = mesh_idx
            
            material = list(mesh.get_obj_materials())
            if material:
                mesh.material = material[0]

        return {'FINISHED'}


CLASSES = [
    Attributes,
    ChangeObjectName,
    ChangeGroupPart,
    MeshMaterial
]

