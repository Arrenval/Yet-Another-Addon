import bpy

from bpy.types import Operator, Object
from bpy.props import StringProperty, IntProperty, EnumProperty, BoolProperty

class Attributes(Operator):
    bl_idname = "ya.attributes"
    bl_label = "Attributes"
    bl_description = ""
    bl_options = {'UNDO'}

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
        context.view_layer.objects.active = obj

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
    bl_options = {'UNDO'}

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
        context.view_layer.objects.active = obj
        name_parts = obj.name.split(" ")

        if self.type == "NAME":
            obj.name = f"{self.user_input} {name_parts[-1]}"

        return {'FINISHED'}
    
class ChangeGroupPart(Operator):
    bl_idname = "ya.overview_group"
    bl_label = "Group"
    bl_description = "Change group/part of the object"
    bl_options = {'UNDO'}

    obj: StringProperty() # type: ignore
    type: StringProperty() # type: ignore
    user_input: IntProperty(name="", default=0, min=0, max=99) # type: ignore

    def invoke(self, context, event):
        obj: Object = bpy.data.objects[self.obj]
        name_parts = obj.name.split(" ")
        if self.type == "GROUP":
            self.user_input = int(name_parts[-1].split(".")[0])
        elif self.type == "PART":
            self.user_input  = int(name_parts[-1].split(".")[1])
        else:
            return self.execute(context)
        bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=1)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self, context):
        obj: Object = bpy.data.objects[self.obj]
        context.view_layer.objects.active = obj
        name_parts = obj.name.split(" ")
        group = int(name_parts[-1].split(".")[0])
        part  = int(name_parts[-1].split(".")[1])

        if self.type == "GROUP":
            new = f"{self.user_input}.{part}"
            obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        if self.type == "PART":
            new = f"{group}.{self.user_input}"
            obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        if self.type == "INC_PART":
            new = f"{group}.{part + 1}"
            obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        if self.type == "DEC_PART":
            new = f"{group}.{part - 1}"
            obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        if self.type == "INC_GROUP":
            new = f"{group + 1}.{part}"
            obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        if self.type == "DEC_GROUP":
            new = f"{group - 1}.{part}"
            obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        return {'FINISHED'}
    
class ChangeMaterial(Operator):
    bl_idname = "ya.overview_material"
    bl_label = "Material"
    bl_description = "Tags faces you want to create backfaces for on export"
    bl_options = {'UNDO'}

    obj: StringProperty() # type: ignore
    type: StringProperty() # type: ignore
    user_input: StringProperty(name="", default="") # type: ignore

    def invoke(self, context, event):
        bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Confirm")
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        obj:Object = bpy.data.objects[self.obj]
        layout = self.layout
        layout.template_list('MATERIAL_UL_matslots',
                            "",
                            obj,
                            "material_slots",
                            obj,
                            "active_material_index",
                            rows=2
                            )

    def execute(self, context):
        # obj: Object = bpy.data.objects[self.obj]
        # context.view_layer.objects.active = obj
        # name_parts = obj.name.split(" ")
        # group = name_parts[-1].split(".")[0]
        # part  = name_parts[-1].split(".")[1]

        # if self.type == "NAME":
        #     obj.name = f"{self.user_input} {name_parts[-1]}"
        # if self.type == "GROUP":
        #     new = f"{self.user_input}.{part}"
        #     obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        # if self.type == "PART":
        #     new = f"{group}.{self.user_input}"
        #     obj.name = f"{obj.name[:-len(name_parts[-1])]}{new}"
        return {'FINISHED'}

CLASSES = [
    Attributes,
    ChangeObjectName,
    ChangeGroupPart,
    ChangeMaterial
]

