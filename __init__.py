import bpy

from .              import preferences
from .              import properties
from .ui            import panel
from .file          import export
from .file          import modpack
from .file          import ya_import
from .util          import logging
from .util          import handlers
from .util          import penumbra
from .outfit        import overview 
from .outfit        import mesh 
from .outfit        import shapes   
from .outfit        import weights  
from .outfit        import armature
from .ui.helpers    import operators
from .ui.helpers    import containers

from importlib      import reload
from .ui.menu       import menu_emptyvgroup_append
       
modules = [
    preferences,
    properties,
    containers,
    operators,
    ya_import,
    export,
    modpack,
    weights,
    armature,
    shapes,
    overview,
    mesh,
    panel
]

m_reload = [
    handlers,
    penumbra,
    logging
]
    
def register():
    for module in modules + m_reload:
        reload(module)

    for module in modules:
        for cls in module.CLASSES:
            bpy.utils.register_class(cls)
        if module == properties:
            properties.set_addon_properties()
        if module == containers:
            containers.set_ui_containers()
      
    handlers.set_handlers()
    bpy.types.Scene.ya_addon_ver = (0, 15, 0)
    bpy.types.MESH_MT_vertex_group_context_menu.append(menu_emptyvgroup_append)

def unregister():
    handlers.remove_handlers()
    bpy.types.MESH_MT_vertex_group_context_menu.remove(menu_emptyvgroup_append)
    del bpy.types.Scene.ya_addon_ver
    
    for module in reversed(modules):
        if module == properties:
            properties.remove_addon_properties()
        if module == containers:
            containers.remove_ui_containers()
        for cls in reversed(module.CLASSES):
            bpy.utils.unregister_class(cls)