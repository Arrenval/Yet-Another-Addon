import bpy

from bpy.types            import Object
from bpy.app.handlers     import persistent
from .properties          import get_object_from_mesh, get_window_properties, get_devkit_properties, get_outfit_properties, get_devkit_win_props


_active_obj = None

def frame_ui(dummy):
    get_window_properties().animation_frame = bpy.context.scene.frame_current

def get_mesh_props(dummy=None) -> None:
    obj: Object = bpy.context.active_object
    outfit       = get_outfit_properties()
    if obj and obj.mode != 'OBJECT':
        return None
    
    if not obj:
        outfit.shape_modifiers_group.clear()
        outfit.mod_shape_source = None

        outfit.yas_vgroups.clear()
        outfit.yas_source = None
        return 

    if obj.modifiers:
        outfit.mod_shape_source = obj
    if obj.vertex_groups:
        outfit.yas_source = obj

@persistent
def active_obj_msgbus(dummy):
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=_active_obj,
        args=(),
        notify=get_mesh_props,
        )

@persistent
def remove_devkit(dummy):
    if hasattr(bpy.context.scene, "devkit"):
        del bpy.types.Scene.devkit
    elif hasattr(bpy.context.scene, "ya_devkit"):
        del bpy.types.Scene.ya_devkit

@persistent
def pre_anim_handling(dummy) ->None:
    props    = get_window_properties()
    devkit   = get_devkit_win_props()
    context = bpy.context
    props.animation_optimise.clear()
    optimise = props.animation_optimise.add()
    if devkit:
        optimise.triangulation = devkit.devkit_triangulation
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
    devkit   = get_devkit_win_props()
    context  = bpy.context
    optimise = props.animation_optimise
    if devkit:
        devkit.devkit_triangulation = optimise[0].triangulation
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
    dummy = None
    active_obj_msgbus(dummy)
    bpy.app.handlers.load_post.append(active_obj_msgbus)
    bpy.app.handlers.load_pre.append(remove_devkit)
    bpy.app.handlers.animation_playback_pre.append(pre_anim_handling)
    bpy.app.handlers.animation_playback_post.append(post_anim_handling)

def remove_handlers() -> None:
    bpy.msgbus.clear_by_owner(_active_obj)
    bpy.app.handlers.load_pre.remove(remove_devkit)
    bpy.app.handlers.load_post.remove(active_obj_msgbus)
    bpy.app.handlers.animation_playback_pre.remove(pre_anim_handling)
    bpy.app.handlers.animation_playback_post.remove(post_anim_handling)

    
