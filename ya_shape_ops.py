import bpy
from bpy.types import Operator
from ya_utils import get_shape_presets, get_chest_category, get_chest_size_keys
import ya_utils as utils

class MESH_OT_YA_ApplyShapes(Operator):
    bl_idname = "mesh.apply_shapes"
    bl_label = ""
    bl_description = "Applies the chosen shape to the selected models. This overrides any custom shape values"
    bl_options = {'UNDO'}

    def execute(self, context):
        ApplyShapes = MESH_OT_YA_ApplyShapes
        apply_mq = context.scene.ya_props.shape_mq_chest_bool
        
        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        
        size = context.scene.ya_props.chest_shape_enum
        category = get_chest_category(size)
        shape_presets = get_shape_presets(size)
        if apply_mq:
            ApplyShapes.reset_shape_values("mq", category)
            ApplyShapes.apply_shape_values("mq", category, shape_presets)
            ApplyShapes.mute_chest_shapes(mannequin, category)
        else:
            ApplyShapes.reset_shape_values("torso", category)
            ApplyShapes.apply_shape_values("torso", category, shape_presets)
            ApplyShapes.mute_chest_shapes(torso, category)
        
        if apply_mq:
            bpy.context.view_layer.objects.active = utils.get_object_from_mesh("Mannequin")
        else:  
            bpy.context.view_layer.objects.active = utils.get_object_from_mesh("Torso")
        bpy.context.view_layer.update()
        return {"FINISHED"}

    def apply_shape_values(apply_target, category, shape_presets):
        ya_props = bpy.context.scene.ya_props
        for shape_key in shape_presets:
            norm_key = shape_key.lower().replace(" ","").replace("-","")
            category_lower = category.lower()

            if norm_key == "sag" and category_lower == "large":
                category_lower = "omoi"
            
            prop = f"key_{norm_key}_{category_lower}_{apply_target}"
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
            
            prop = f"key_{norm_key}_{category_lower}_{apply_target}"
            if hasattr(ya_props, prop):
                setattr(ya_props, prop, 100 * reset[reset_key])
                             
    def mute_chest_shapes(apply_target, category):
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

    def mute_gen_shapes(apply_target, gen: str):
        gen_mute_mapping = {
            "Gen A": (True, True, True), 
            "Gen B": (False, True, True), 
            "Gen C": (True, False, True),   
            "Gen SFW": (True, True, False),   
        }

        # Gets category and its bools
        mute_b, mute_c, mute_sfw = gen_mute_mapping.get(gen, (True, True, True))

        # Apply the mute states to the target
        apply_target["Gen B"].mute = mute_b
        apply_target["Gen C"].mute = mute_c
        apply_target["Gen SFW"].mute = mute_sfw

    def mute_leg_shapes(apply_target, size: str):
        size_mute_mapping = {
            "Melon": (True, True), 
            "Skull": (False, True), 
            "Mini": (True, False),   
        }

        # Gets category and its bools
        mute_skull, mute_mini = size_mute_mapping.get(size, (True, True))

        # Apply the mute states to the target
        apply_target["Skull Crushers"].mute = mute_skull
        apply_target["Mini"].mute = mute_mini

        if not mute_mini:
            apply_target["Hip Dips (for YAB)"].mute = True
            apply_target["Less Hip Dips (for Rue)"].mute = True

    def mute_nail_shapes(apply_target, nails: str):
        nails_mute_mapping = {
            "Long": (True, True, True), 
            "Short": (False, True, True), 
            "Ballerina": (True, False, True), 
            "Stabbies": (True, True, False), 
             
        }
        # Gets category and its bools
        mute_short, mute_ballerina, mute_stabbies = nails_mute_mapping.get(nails, (True, True, True))

        # Apply the mute states to the target
        apply_target["Short Nails"].mute = mute_short
        apply_target["Ballerina"].mute = mute_ballerina
        apply_target["Stabbies"].mute = mute_stabbies
    
    def toggle_other(apply_target, key: str, not_legs=True):

        if not_legs:
            if apply_target[key].mute:
                apply_target[key].mute = False
            else:
                apply_target[key].mute = True

        # Alt hips were a mistake

        else:
            if key == "Hip":
                if apply_target["Hip Dips (for YAB)"].mute and apply_target["Less Hip Dips (for Rue)"].mute:
                    if apply_target["Rue"].mute: 
                        apply_target["Hip Dips (for YAB)"].mute = False
                        apply_target["Less Hip Dips (for Rue)"].mute = True
                    else:
                        apply_target["Hip Dips (for YAB)"].mute = True
                        apply_target["Less Hip Dips (for Rue)"].mute = False
                else:
                    apply_target["Hip Dips (for YAB)"].mute = True
                    apply_target["Less Hip Dips (for Rue)"].mute = True


            elif apply_target[key].mute:
                if key == "Rue" and not apply_target["Hip Dips (for YAB)"].mute:
                    apply_target["Hip Dips (for YAB)"].mute = True
                    apply_target["Less Hip Dips (for Rue)"].mute = False
                if key == "Rue Other":
                    key = "Rue"
                apply_target[key].mute = False
            else:
                if key == "Rue" and not apply_target["Less Hip Dips (for Rue)"].mute:
                    apply_target["Hip Dips (for YAB)"].mute = False
                    apply_target["Less Hip Dips (for Rue)"].mute = True
                if key == "Rue Other":
                    key = "Rue"
                apply_target[key].mute = True


class MESH_OT_YA_ApplySizeCategoryLarge(Operator):
    bl_idname = "mesh.apply_size_category_large"
    bl_label = ""
    bl_description = "Changes size without affecting custom values"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_chest_bool
        category = "Large"

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
 
        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_chest_shapes(mannequin, category)
        else:
            MESH_OT_YA_ApplyShapes.mute_chest_shapes(torso, category)

        
        return {"FINISHED"}


class MESH_OT_YA_ApplySizeCategoryMedium(Operator):
    bl_idname = "mesh.apply_size_category_medium"
    bl_label = ""
    bl_description = "Changes size without affecting custom values"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_chest_bool
        category = "Medium"

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_chest_shapes(mannequin, category)
        else:
            MESH_OT_YA_ApplyShapes.mute_chest_shapes(torso, category)
        
        return {"FINISHED"}


class MESH_OT_YA_ApplySizeCategorySmall(Operator):
    bl_idname = "mesh.apply_size_category_small"
    bl_label = ""
    bl_description = "Changes size without affecting custom values"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_chest_bool
        category = "Small"

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_chest_shapes(mannequin, category)
        else:
            MESH_OT_YA_ApplyShapes.mute_chest_shapes(torso, category)
        
        return {"FINISHED"}


class MESH_OT_YA_ApplyBuff(Operator):
    bl_idname = "mesh.apply_buff"
    bl_label = ""
    bl_description = "Applies the buff torso"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_chest_bool

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Buff"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(torso, key)

        
        return {"FINISHED"}
    

class MESH_OT_YA_ApplyRueTorso(Operator):
    bl_idname = "mesh.apply_rue_torso"
    bl_label = ""
    bl_description = "Applies Rue tummy"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_chest_bool

        torso = utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Rue"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(torso, key)
        
        return {"FINISHED"}


class MESH_OT_YA_ApplyMelon(Operator):
    bl_idname = "mesh.apply_melon"
    bl_label = ""
    bl_description = "Applies Melon Crushers"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Melon"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_leg_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_leg_shapes(legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplySkull(Operator):
    bl_idname = "mesh.apply_skull"
    bl_label = ""
    bl_description = "Applies Skull Crushers"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Skull"

        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_leg_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_leg_shapes(legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyMini(Operator):
    bl_idname = "mesh.apply_mini"
    bl_label = ""
    bl_description = "Applies Mini Legs. Not compatible with Skull Crushers or alternate hip dips"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Mini"

        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_leg_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_leg_shapes(legs, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyRueLegs(Operator):
    bl_idname = "mesh.apply_rue_legs"
    bl_label = ""
    bl_description = "Applies Rue tummy"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        Legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks

        key = "Rue"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key, not_legs=False)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(Legs, key, not_legs=False)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyGenA(Operator):
    bl_idname = "mesh.apply_gena"
    bl_label = ""
    bl_description = "Labia majora"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        Legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Gen A"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(Legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyGenB(Operator):
    bl_idname = "mesh.apply_genb"
    bl_label = ""
    bl_description = "Visible labia minora"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        Legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Gen B"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(Legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyGenC(Operator):
    bl_idname = "mesh.apply_genc"
    bl_label = ""
    bl_description = "Open vagina"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        Legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Gen C"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(Legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyGenSFW(Operator):
    bl_idname = "mesh.apply_gensfw"
    bl_label = ""
    bl_description = "Barbie doll"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        Legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Gen SFW"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_gen_shapes(Legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplySmallButt(Operator):
    bl_idname = "mesh.apply_small_butt"
    bl_label = ""
    bl_description = "Makes the butt smaller"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Small Butt"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplySoftButt(Operator):
    bl_idname = "mesh.apply_soft_butt"
    bl_label = ""
    bl_description = "Makes the butt softer"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Soft Butt"
        
        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(legs, key)

        return {"FINISHED"}
    

class MESH_OT_YA_ApplyHips(Operator):
    bl_idname = "mesh.apply_hip_dips"
    bl_label = ""
    bl_description = "Adds hip dips on YAB, removes them on Rue"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_legs_bool

        legs = utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Hip"
        
        if apply_mq:
            if not mannequin["Mini"].mute:
                self.report({'ERROR'}, "Not compatible with Mini!")
                return {'CANCELLED'}
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key, not_legs=False)
            
        else:
            if not legs["Mini"].mute:
                self.report({'ERROR'}, "Not compatible with Mini!")
                return {'CANCELLED'}
            MESH_OT_YA_ApplyShapes.toggle_other(legs, key, not_legs=False)

        return {"FINISHED"}


class MESH_OT_YA_ApplyRueHands(Operator):
    bl_idname = "mesh.apply_rue_hands"
    bl_label = ""
    bl_description = "Applies Rue hands"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        hands = utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Rue"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(hands, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyLongNails(Operator):
    bl_idname = "mesh.apply_long_nails"
    bl_label = ""
    bl_description = "Applies long nails"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        hands = utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Long"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(hands, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyShortNails(Operator):
    bl_idname = "mesh.apply_short_nails"
    bl_label = ""
    bl_description = "Applies short nails"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        hands = utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Short"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(hands, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyBallerinaNails(Operator):
    bl_idname = "mesh.apply_ballerina_nails"
    bl_label = ""
    bl_description = "Applies ballerina nails"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        hands = utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Ballerina"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(hands, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyStabbiesNails(Operator):
    bl_idname = "mesh.apply_stabbies_nails"
    bl_label = ""
    bl_description = "Applies stabbies"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        hands = utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Stabbies"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.mute_nail_shapes(hands, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyClawsies(Operator):
    bl_idname = "mesh.apply_hand_clawsies"
    bl_label = ""
    bl_description = "Applies murder nails of your choosing"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        hands = utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Curved"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(hands, key)

        return {"FINISHED"}


class MESH_OT_YA_ApplyRueFeet(Operator):
    bl_idname = "mesh.apply_rue_feet"
    bl_label = ""
    bl_description = "Applies Rue hands"
    bl_options = {'UNDO'}

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_other_bool

        feet = utils.get_object_from_mesh("Feet").data.shape_keys.key_blocks
        mannequin = utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks
        key = "Rue"

        if apply_mq:
            MESH_OT_YA_ApplyShapes.toggle_other(mannequin, key)
        else:
            MESH_OT_YA_ApplyShapes.toggle_other(feet, key)

        return {"FINISHED"}


class MESH_OT_YA_FeetNailVisibility(Operator):
    bl_idname = "mesh.visible_feet_nails"
    bl_label = ""
    bl_description = "Hides nails"
    bl_options = {'UNDO'}

    def execute(self, context):
        if bpy.context.view_layer.layer_collection.children["Feet"].children["Toenails"].exclude:
            bpy.context.view_layer.layer_collection.children["Feet"].children["Toenails"].exclude = False
        else:
            bpy.context.view_layer.layer_collection.children["Feet"].children["Toenails"].exclude = True

        return {"FINISHED"}


class MESH_OT_YA_FeetClawVisibiliy(Operator):
    bl_idname = "mesh.visible_feet_clawsies"
    bl_label = ""
    bl_description = "Hides clawsies"
    bl_options = {'UNDO'}

    def execute(self, context):
        if bpy.context.view_layer.layer_collection.children["Feet"].children["Toe Clawsies"].exclude:
            bpy.context.view_layer.layer_collection.children["Feet"].children["Toe Clawsies"].exclude = False
        else:
            bpy.context.view_layer.layer_collection.children["Feet"].children["Toe Clawsies"].exclude = True

        return {"FINISHED"}


class MESH_OT_YA_HandNailVisibility(Operator):
    bl_idname = "mesh.visible_hand_nails"
    bl_label = ""
    bl_description = "Hides nails"
    bl_options = {'UNDO'}

    def execute(self, context):
        if bpy.context.view_layer.layer_collection.children["Hands"].children["Nails"].exclude:
            bpy.context.view_layer.layer_collection.children["Hands"].children["Nails"].exclude = False
        else:
            bpy.context.view_layer.layer_collection.children["Hands"].children["Nails"].exclude = True

        return {"FINISHED"}


class MESH_OT_YA_HandClawVisibiliy(Operator):
    bl_idname = "mesh.visible_hand_clawsies"
    bl_label = ""
    bl_description = "Hides clawsies"
    bl_options = {'UNDO'}

    def execute(self, context):
        if bpy.context.view_layer.layer_collection.children["Hands"].children["Clawsies"].exclude:
            bpy.context.view_layer.layer_collection.children["Hands"].children["Clawsies"].exclude = False
        else:
            bpy.context.view_layer.layer_collection.children["Hands"].children["Clawsies"].exclude = True

        return {"FINISHED"}


