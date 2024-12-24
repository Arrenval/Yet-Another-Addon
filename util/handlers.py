import bpy

from .props               import get_object_from_mesh
from bpy.app.handlers     import persistent

def frame_ui(dummy):
    bpy.context.scene.outfit_props.animation_frame = bpy.context.scene.frame_current

@persistent
def get_mesh_props(dummy) -> None:
    scene = bpy.context.scene
    props = bpy.context.scene.outfit_props
    obj = bpy.context.active_object

    if obj is None:
        scene.deform_modifiers.clear()
        scene.yas_vgroups.clear()
        return None

    if obj.modifiers:
        deform = {
                'ARMATURE', 'DISPLACE', 'LATTICE', 'MESH_DEFORM', 'SIMPLE_DEFORM',
                'WARP', 'SMOOTH', 'SHRINKWRAP', 'SURFACE_DEFORM', 'CORRECTIVE_SMOOTH'
            }
        scene.deform_modifiers.clear()
        deform_modifiers =  [modifier for modifier in obj.modifiers if any(modifier.type in type for type in deform) ]
        for modifier in deform_modifiers:
            new_modifier = scene.deform_modifiers.add()
            new_modifier.name = modifier.name
            if "SMOOTH" in modifier.type:
                new_modifier.icon = "MOD_SMOOTH"
            elif "DEFORM" in modifier.type:
                new_modifier.icon = "MOD_MESHDEFORM"
            else:
                new_modifier.icon = f"MOD_{modifier.type.upper()}"
    else:
        scene.deform_modifiers.clear()
        
    if obj.vertex_groups:
        prefix = ("iv_", "ya_")
        groups = [group for group in obj.vertex_groups if group.name.startswith(prefix)]

        scene.yas_vgroups.clear()
        for group in groups:
            new_group = scene.yas_vgroups.add()
            new_group.name = group.name
            new_group.lock_weight = obj.vertex_groups[group.name].lock_weight
        if not groups:
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
        optimise.uv_transfer   = context.scene.devkit_props.controller_uv_transfers
        context.scene.devkit_props.controller_triangulation = False
        context.scene.devkit_props.controller_uv_transfers  = False
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
        context.scene.devkit_props.controller_uv_transfers  = optimise[0].uv_transfer
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
    
