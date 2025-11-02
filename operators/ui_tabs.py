from bpy.types import Operator, Context
from bpy.props import StringProperty

from ..props   import get_studio_props, get_window_props

 
class OutfitCategory(Operator):
    bl_idname = "ya.outfit_category"
    bl_label = "Select menus."
    bl_description = """Changes the panel menu.
    *Click to select single category.
    *Shift+Click to pin/unpin categories"""

    menu: StringProperty() # type: ignore
    panel: StringProperty() # type: ignore

    def invoke(self, context: Context, event):
        props = get_window_props()
        categories = ["overview", "shapes", "mesh", "weights", "armature"]
        if event.shift:
            state = getattr(props, f"{self.menu.lower()}_category")
            if state:
                setattr(props, f"{self.menu.lower()}_category", False)
            else:
                setattr(props, f"{self.menu.lower()}_category", True)
        else:
            for category in categories:
                if self.menu.lower() == category:
                    setattr(props, f"{category.lower()}_category", True)
                else:
                    setattr(props, f"{category.lower()}_category", False)

        if self.menu == "WEIGHTS":
            get_studio_props().set_yas_ui_vgroups(context)
        elif self.menu == "MESH":
            get_studio_props().set_modifiers(context)

        return {'FINISHED'}
    
class InspectorCategory(Operator):
    bl_idname = "ya.inspector_category"
    bl_label = "Select menus."
    bl_description = """Changes the panel menu.
    *Click to select single category.
    *Shift+Click to pin/unpin categories"""

    menu: StringProperty() # type: ignore
    panel: StringProperty() # type: ignore

    def invoke(self, context: Context, event):
        props = get_window_props()
        categories = ["file", "phyb", "model"]
        if event.shift:
            state = getattr(props, f"{self.menu.lower()}_category")
            if state:
                setattr(props, f"{self.menu.lower()}_category", False)
            else:
                setattr(props, f"{self.menu.lower()}_category", True)
        else:
            for category in categories:
                if self.menu.lower() == category:
                    setattr(props, f"{category.lower()}_category", True)
                else:
                    setattr(props, f"{category.lower()}_category", False)

        return {'FINISHED'}


CLASSES = [
    OutfitCategory,
    InspectorCategory,
]
