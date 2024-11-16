import bpy
from bpy.types import Operator
from ya_utils import get_shape_presets, get_chest_category, get_chest_size_keys
import ya_utils as utils

class MESH_OT_YA_RemoveEmptyVGroups(Operator):
    bl_idname = "mesh.remove_empty_vgroups"
    bl_label = "Weights"
    bl_description = "Removes Vertex Groups with no weights. Ignores IVCS and YAS groups"
    bl_options = {'UNDO'}

    def execute(self, context):
        ob = bpy.context.active_object
        prefixes = ["ya_", "iv_"]

        # Iterates over all vertex groups and its vertices to see if it is empty
        for vg in ob.vertex_groups:
            emptyvg = not any(vg.index in [g.group for g in v.groups] for v in ob.data.vertices)
            vgname = vg.name
            
            # Ignores yas and ivcs prefixed groups
            if emptyvg and not vgname.startswith(tuple(prefixes)):
                ob.vertex_groups.remove(vg)
                # print (f"Removed {vgname}.")

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyShapes(Operator):
    bl_idname = "mesh.apply_shapes"
    bl_label = "Shapes"
    bl_description = "Applies the chosen shape to the selected models. This overrides any custom shape values"
    bl_options = {'UNDO'}

    def apply_shape_values(apply_target, category, shape_presets):
            ya_props = bpy.context.scene.ya_props
           
            for shape_key in shape_presets:
                norm_key = shape_key.lower().replace(" ","").replace("-","")
                category_lower = category.lower()

                if norm_key == "sag" and category_lower == "large":
                    category_lower = "omoi"
                
                prop = f"key_{norm_key}_{category_lower}"
                if hasattr(ya_props, prop):
                    setattr(ya_props, prop, 100 * shape_presets[shape_key])
            

    def reset_shape_values(apply_target, category):
            reset = get_shape_presets(category)
            ya_props = bpy.context.scene.ya_props

            for reset_key in reset:
                norm_key = reset_key.lower().replace(" ","").replace("-","")
                category_lower = category.lower()

                if norm_key == "sag" and category_lower == "large":
                    category_lower = "omoi"
                
                prop = f"key_{norm_key}_{category_lower}"
                if hasattr(ya_props, prop):
                    setattr(ya_props, prop, 100 * reset[reset_key])
                
                    
    def mute_shapes(apply_target, category):
        # Defines what categories mutes (medium, small)
        category_mute_mapping = {
            "Large": (True, True), 
            "Medium": (False, True), 
            "Small": (True, False),   
        }

        # Gets category and its bools
        mute_medium, mute_small = category_mute_mapping.get(category, (True, True))

        # Apply the mute states to the target
        apply_target[get_chest_size_keys("Medium")].mute = mute_medium
        apply_target[get_chest_size_keys("Small")].mute = mute_small

    def execute(self, context):
        ApplyShapes = MESH_OT_YA_ApplyShapes
        apply_mq = context.scene.ya_props.shape_mq_bool
        apply_torso = context.scene.ya_props.shape_torso_bool
        
        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        
        size = context.scene.ya_props.chest_shape_enum
        category = get_chest_category(size)
        shape_presets = get_shape_presets(size)

        # What models to change based on user input
        if apply_torso:
            ApplyShapes.reset_shape_values(torso, category)
            ApplyShapes.apply_shape_values(torso, category, shape_presets)
            ApplyShapes.mute_shapes(torso, category)

        if apply_mq:
            ApplyShapes.reset_shape_values(mannequin, category)
            ApplyShapes.apply_shape_values(mannequin, category, shape_presets)
            ApplyShapes.mute_shapes(mannequin, category)
        
        if apply_torso or apply_mq:
            bpy.context.view_layer.objects.active = utils.get_object_from_mesh("Torso")
        else:  
            bpy.context.view_layer.objects.active = utils.get_object_from_mesh("Mannequin")
        bpy.context.view_layer.update()
        return {"FINISHED"}


class MESH_OT_YA_ApplySizeCategoryLarge(Operator):
    bl_idname = "mesh.apply_size_category_large"
    bl_label = "Shapes"
    bl_description = "Changes size without affecting custom values"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq, apply_torso = utils.apply_shapes_targets(self, context)
        category = "Large"

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks

         # What models to change based on user input
        if apply_torso:
            MESH_OT_YA_ApplyShapes.mute_shapes(torso, category)

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_shapes(mannequin, category)

        
        return {"FINISHED"}


class MESH_OT_YA_ApplySizeCategoryMedium(Operator):
    bl_idname = "mesh.apply_size_category_medium"
    bl_label = "Shapes"
    bl_description = "Changes size without affecting custom values"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq, apply_torso = utils.apply_shapes_targets(self, context)
        category = "Medium"

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks

         # What models to change based on user input
        if apply_torso:
            MESH_OT_YA_ApplyShapes.mute_shapes(torso, category)

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_shapes(mannequin, category)

        
        return {"FINISHED"}


class MESH_OT_YA_ApplySizeCategorySmall(Operator):
    bl_idname = "mesh.apply_size_category_small"
    bl_label = "Shapes"
    bl_description = "Changes size without affecting custom values"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq, apply_torso = utils.apply_shapes_targets(self, context)
        category = "Small"

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks

         # What models to change based on user input
        if apply_torso:
            MESH_OT_YA_ApplyShapes.mute_shapes(torso, category)

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_shapes(mannequin, category)

        
        return {"FINISHED"}


class YA_OBJECT_OT_SetBodyPart(bpy.types.Operator):
    bl_idname = "object.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        # Update the export_body_part with the selected body part
        context.scene.ya_props.export_body_slot = self.body_part
        return {'FINISHED'}