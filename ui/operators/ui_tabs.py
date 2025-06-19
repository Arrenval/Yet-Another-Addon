from bpy.types          import Operator, Context
from bpy.props          import StringProperty
from ...properties      import get_file_properties, get_outfit_properties, get_window_properties

 
class OutfitCategory(Operator):
    bl_idname = "ya.outfit_category"
    bl_label = "Select menus."
    bl_description = """Changes the panel menu.
    *Click to select single category.
    *Shift+Click to pin/unpin categories"""

    menu: StringProperty() # type: ignore
    panel: StringProperty() # type: ignore

    def invoke(self, context, event):
        props = get_window_properties()
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

        return {'FINISHED'}


CLASSES = [
    OutfitCategory,
]
