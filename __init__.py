import bpy

from .         import props
from .         import preferences
from .handlers import set_handlers, remove_handlers

from pathlib   import Path
from importlib import import_module

SUBFOLDERS = [
    "operators",
    "operators/export",
    "operators/modpack",
    "ui/operators",
    "ui",
]

modules = [
    props,
    preferences
]

classes = []

def load_modules():
    addon_dir = Path(__file__).parent

    for folder in SUBFOLDERS:
        folder_path = addon_dir / folder
        for py_file in folder_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            relative_path = folder_path.relative_to(addon_dir)
            module_name   = f"{__name__}.{'.'.join(relative_path.parts)}.{py_file.stem}"
                        
            try:
                module = import_module(module_name)
                modules.append(module)
                if hasattr(module, 'CLASSES'):
                    classes.extend(module.CLASSES)
                    
            except ImportError as e:
                print(f"Failed to import {module_name}: {e}")

load_modules()
    
def register():
    for module in modules[:2]:
        for cls in module.CLASSES:
            bpy.utils.register_class(cls)
        if module == props:
            props.set_addon_properties()

    for cls in classes:
        bpy.utils.register_class(cls)

    preferences.register_menus()

    set_handlers()
    bpy.types.Scene.ya_addon_ver = (0, 22, 4)
    

def unregister():
    del bpy.types.Scene.ya_addon_ver
    remove_handlers()

    preferences.unregister_menus()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for module in reversed(modules[:2]):
        if module == props:
            props.remove_addon_properties()
        for cls in reversed(module.CLASSES):
            bpy.utils.unregister_class(cls)
