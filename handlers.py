import bpy

from bpy.types            import Object
from bpy.app.handlers     import persistent
from .properties          import get_object_from_mesh, get_window_properties, get_devkit_properties

def frame_ui(dummy):
    get_window_properties().animation_frame = bpy.context.scene.frame_current

@persistent
def get_mesh_props(dummy) -> None:
    obj: Object = bpy.context.active_object
    window      = get_window_properties()
    
    if obj and obj.mode != 'OBJECT':
        return None
    
    if not obj:
        window.shape_modifiers_group.clear()
        window.yas_vgroups.clear()
        window.shape_source = None
        window.yas_source = None
        return 

    if obj.modifiers:
        window.shape_source = obj
    if obj.vertex_groups:
        window.yas_source = obj
      
DEVKIT_VER = (0, 0, 0)

@persistent
def devkit_check(dummy):
    global DEVKIT_VER
    if bpy.data.texts.get("devkit.py"):
        devkit = bpy.data.texts["devkit.py"].as_module()
        DEVKIT_VER = devkit.DEVKIT_VER
        bpy.types.Scene.ya_devkit = devkit

@persistent
def remove_devkit(dummy):
    if hasattr(bpy.context.scene, "devkit"):
        del bpy.types.Scene.devkit
    elif hasattr(bpy.context.scene, "ya_devkit"):
        del bpy.types.Scene.ya_devkit

@persistent
def pre_anim_handling(dummy) ->None:
    props    = get_window_properties()
    devkit   = get_devkit_properties()
    context = bpy.context
    props.animation_optimise.clear()
    optimise = props.animation_optimise.add()
    if devkit:
        optimise.triangulation = devkit.controller_triangulation
        context.scene.devkit_props.controller_triangulation = False
        get_object_from_mesh("Controller").update_tag()
        bpy.ops.yakit.collection_manager(preset="Animation")
    
    try:
        area = [area for area in context.screen.areas if area.type == 'VIEW_3D'][0]
        view3d = [space for space in area.spaces if space.type == 'VIEW_3D'][0]

        with context.temp_override(area=area, space=view3d):
            optimise.show_armature = context.space_data.show_object_viewport_armature
            context.space_data.show_object_viewport_armature = False
    except:
        pass

    bpy.app.handlers.frame_change_pre.append(frame_ui)

@persistent
def post_anim_handling(dummy) ->None:
    props    = get_window_properties()
    devkit   = get_devkit_properties()
    context  = bpy.context
    optimise = props.animation_optimise
    if devkit:
        devkit.controller_triangulation = optimise[0].triangulation
        bpy.ops.yakit.collection_manager(preset="Restore") 
    
    props.animation_frame = context.scene.frame_current
    
    try:
        area = [area for area in context.screen.areas if area.type == 'VIEW_3D'][0]
        view3d = [space for space in area.spaces if space.type == 'VIEW_3D'][0]

        with context.temp_override(area=area, space=view3d):
            context.space_data.show_object_viewport_armature = optimise[0].show_armature
    except:
        pass
    bpy.app.handlers.frame_change_pre.remove(frame_ui)


def set_handlers() -> None:
    bpy.app.handlers.load_post.append(devkit_check)
    bpy.app.handlers.load_pre.append(remove_devkit)
    bpy.app.handlers.depsgraph_update_post.append(get_mesh_props)
    bpy.app.handlers.animation_playback_pre.append(pre_anim_handling)
    bpy.app.handlers.animation_playback_post.append(post_anim_handling)

def remove_handlers() -> None:
    bpy.app.handlers.load_post.remove(devkit_check)
    bpy.app.handlers.load_pre.remove(remove_devkit)
    bpy.app.handlers.animation_playback_pre.remove(pre_anim_handling)
    bpy.app.handlers.animation_playback_post.remove(post_anim_handling)
    bpy.app.handlers.depsgraph_update_post.remove(get_mesh_props)
    
