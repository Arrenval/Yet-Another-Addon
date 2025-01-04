import bpy

from .props               import get_object_from_mesh
from bpy.app.handlers     import persistent

def frame_ui(dummy):
    bpy.context.scene.outfit_props.animation_frame = bpy.context.scene.frame_current

@persistent
def get_mesh_props(dummy) -> None:
    obj           = bpy.context.active_object
    scene         = bpy.context.scene
    props         = bpy.context.scene.outfit_props
    mod_button    = props.button_modifiers_expand
    weight_button = props.filter_vgroups
    
    if obj and obj.mode != 'OBJECT':
        return None
    
    if not obj:
        scene.shape_modifiers.clear()
        scene.yas_vgroups.clear()
        return None

    if getattr(props, "mesh_category") and mod_button and obj.modifiers:
        mod_types = {
                'ARMATURE', 'DISPLACE', 'LATTICE', 'MESH_DEFORM', 'SIMPLE_DEFORM',
                'WARP', 'SMOOTH', 'SHRINKWRAP', 'SURFACE_DEFORM', 'CORRECTIVE_SMOOTH',
                'DATA_TRANSFER'
            }
        
        scene.shape_modifiers.clear()
        for modifier in obj.modifiers:
            if modifier.type in mod_types:
                new_modifier = scene.shape_modifiers.add()
                new_modifier.name = modifier.name
                new_modifier.icon = "MOD_SMOOTH" if "SMOOTH" in modifier.type else \
                                    "MOD_MESHDEFORM" if "DEFORM" in modifier.type else \
                                    f"MOD_{modifier.type}"
        
        if scene.shape_modifiers and props.shape_modifiers == "":
            props.shape_modifiers = scene.shape_modifiers[0].name

    else:
        scene.shape_modifiers.clear()
        
    if getattr(props, "weights_category") and weight_button and obj.vertex_groups:
        prefixes = {"iv_", "ya_"}

        scene.yas_vgroups.clear()
        has_groups = False
        for group in obj.vertex_groups:
            if any(group.name.startswith(prefix) for prefix in prefixes):
                has_groups = True
                new_group = scene.yas_vgroups.add()
                new_group.name = group.name
                new_group.lock_weight = obj.vertex_groups[group.name].lock_weight
        if not has_groups:
            new_group = scene.yas_vgroups.add()
            new_group.name = "Mesh has no YAS Groups"

    else:
        scene.yas_vgroups.clear()
        
DEVKIT_VER = (0, 0, 0)

@persistent
def devkit_check(dummy):
    global DEVKIT_VER
    if bpy.data.texts.get("devkit.py"):
        devkit = bpy.data.texts["devkit.py"].as_module()
        DEVKIT_VER = devkit.DEVKIT_VER
        bpy.types.Scene.devkit = devkit

@persistent
def remove_devkit(dummy):
    if hasattr(bpy.context.scene, "devkit"):
        del bpy.types.Scene.devkit

@persistent
def pre_anim_handling(dummy) ->None:
    context = bpy.context
    context.scene.animation_optimise.clear()
    optimise = bpy.context.scene.animation_optimise.add()
    if hasattr(bpy.context.scene, "devkit_props"):
        optimise.triangulation = context.scene.devkit_props.controller_triangulation
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
    context = bpy.context
    optimise = context.scene.animation_optimise
    if hasattr(bpy.context.scene, "devkit_props"):
        context.scene.devkit_props.controller_triangulation = optimise[0].triangulation
        bpy.ops.yakit.collection_manager(preset="Restore") 
    
    context.scene.outfit_props.animation_frame = context.scene.frame_current
    
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
    
