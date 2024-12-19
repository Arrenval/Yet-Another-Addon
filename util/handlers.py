import bpy

from .props               import get_object_from_mesh
from bpy.app.handlers     import persistent

@persistent
def yas_vgroups(dummy) -> None:
    scene = bpy.context.scene
    props = bpy.context.scene.outfit_props
    obj = bpy.context.active_object
    if props.outfit_ui == "Weights" and props.filter_vgroups and obj.type == "MESH":
        prefix = ("iv_", "ya_")
        groups = [group for group in obj.vertex_groups if group.name.startswith(prefix)]

        scene.yas_vgroups.clear()
        for group in groups:
            new_group = scene.yas_vgroups.add()
            new_group.name = group.name
            new_group.lock_weight = obj.vertex_groups[group.name].lock_weight
        if not groups:
            new_group = scene.yas_vgroups.add()
            new_group.name = "Mesh has no YAS groups"

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


def set_handlers() -> None:
    bpy.app.handlers.depsgraph_update_post.append(yas_vgroups)
    bpy.app.handlers.animation_playback_pre.append(pre_anim_handling)
    bpy.app.handlers.animation_playback_post.append(post_anim_handling)

def remove_handlers() -> None:
    bpy.app.handlers.animation_playback_pre.remove(pre_anim_handling)
    bpy.app.handlers.animation_playback_post.remove(post_anim_handling)
    bpy.app.handlers.depsgraph_update_post.remove(yas_vgroups)
