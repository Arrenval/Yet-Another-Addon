import bpy
import ya_utils as Utils

from bpy.types import Operator
from bpy.props import StringProperty


class RemoveEmptyVGroups(Operator):
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = "Weights"
    bl_description = "Removes Vertex Groups with no weights. Ignores IVCS and YAS groups"
    bl_options = {'UNDO'}

    def execute(self, context):
        ob = bpy.context.active_object
        prefixes = ["ya_", "iv_"]
        
        for vg in ob.vertex_groups:
            emptyvg = not any(vg.index in [g.group for g in v.groups] for v in ob.data.vertices)
            vgname = vg.name
            
            # Ignores yas and ivcs prefixed groups as they could be empty even if you need them later
            if emptyvg and not vgname.startswith(tuple(prefixes)):
                ob.vertex_groups.remove(vg)

        return {"FINISHED"}

class ApplyShapes(Operator):
    bl_idname = "ya.apply_shapes"
    bl_label = ""
    bl_description = "Applies the selected option"
    bl_options = {'UNDO'}
    
    key: StringProperty() # type: ignore
    target: StringProperty() # type: ignore
    preset: StringProperty() # type: ignore # shapes, chest_category, leg_size, gen, nails, other

    def execute(self, context):
        apply_mq = context.scene.ya_props.shape_mq_chest_bool
        
        if self.target == "Torso":
            not_legs = True
            target = Utils.get_object_from_mesh("Torso").data.shape_keys.key_blocks
            
        elif self.target == "Legs":
            not_legs = False
            target = Utils.get_object_from_mesh("Waist").data.shape_keys.key_blocks

        elif self.target == "Hands":
            not_legs = True
            target = Utils.get_object_from_mesh("Hands").data.shape_keys.key_blocks

        elif self.target == "Feet":
            not_legs = True
            target = Utils.get_object_from_mesh("Feet").data.shape_keys.key_blocks

        mannequin = Utils.get_object_from_mesh("Mannequin").data.shape_keys.key_blocks 

        if self.preset == "chest_category":
            if apply_mq:
                ApplyShapes.mute_chest_shapes(mannequin, self.key)
            else:
                ApplyShapes.mute_chest_shapes(target, self.key)

        elif self.preset == "leg_size":
            if apply_mq:
                ApplyShapes.mute_leg_shapes(mannequin, self.key)
            else:
                ApplyShapes.mute_leg_shapes(target, self.key)
        
        elif self.preset == "gen":

            if apply_mq:
                ApplyShapes.mute_gen_shapes(mannequin, self.key)
            else:
                ApplyShapes.mute_gen_shapes(target, self.key)

        elif self.preset == "nails":
            if apply_mq:
                ApplyShapes.mute_nail_shapes(mannequin, self.key)
            else:
                ApplyShapes.mute_nail_shapes(target, self.key)

        elif self.preset == "other":
            if apply_mq:
                if self.key == "Alt Hips" and not mannequin["Mini"].mute:
                    self.report({"ERROR"}, "Mini not compatible with alternate hips!")
                    return {"CANCELLED"}
                ApplyShapes.toggle_other(mannequin, self.key, not_legs)
            else:
                if self.key == "Alt Hips" and self.target == "Legs" and not target["Mini"].mute:
                    self.report({"ERROR"}, "Mini not compatible with alternate hips!")
                    return {"CANCELLED"}
                ApplyShapes.toggle_other(target, self.key, not_legs)
        
        elif self.preset == "shapes":
            size = context.scene.ya_props.chest_shape_enum
            category = Utils.get_chest_category(size)
            shape_presets = Utils.get_shape_presets(size)

            if apply_mq:
                ApplyShapes.reset_shape_values("mq", category)
                ApplyShapes.apply_shape_values("mq", category, shape_presets)
                ApplyShapes.mute_chest_shapes(mannequin, category)
            else:
                ApplyShapes.reset_shape_values("torso", category)
                ApplyShapes.apply_shape_values("torso", category, shape_presets)
                ApplyShapes.mute_chest_shapes(target, category)
            
            if apply_mq:
                bpy.context.view_layer.objects.active = Utils.get_object_from_mesh("Mannequin")
            else:  
                bpy.context.view_layer.objects.active = Utils.get_object_from_mesh("Torso")
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
        reset = Utils.get_shape_presets(category)
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
        apply_target[Utils.get_chest_size_keys("Medium")].mute = mute_medium
        apply_target[Utils.get_chest_size_keys("Small")].mute = mute_small

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

        else:
            if apply_target[key].mute:
                if key == "Rue Other":
                    key = "Rue"
                apply_target[key].mute = False
            else:
                if key == "Rue Other":
                    key = "Rue"
                apply_target[key].mute = True

class ApplyVisibility(Operator):
    bl_idname = "ya.apply_visibility"
    bl_label = ""
    bl_description = "Hides selected nails/claws"
    bl_options = {'UNDO'}

    key: StringProperty() # type: ignore
    target: StringProperty() # type: ignore

    def execute(self, context):
        collection = bpy.context.view_layer.layer_collection.children
        if self.key == "Nails" and self.target == "Feet":
            
            if collection["Feet"].children["Toenails"].exclude:
                collection["Feet"].children["Toenails"].exclude = False
            else:
                collection["Feet"].children["Toenails"].exclude = True
        
        elif self.target == "Feet":

            if collection["Feet"].children["Toe Clawsies"].exclude:
                collection["Feet"].children["Toe Clawsies"].exclude = False
            else:
                collection["Feet"].children["Toe Clawsies"].exclude = True
    
        elif self.key == "Nails" and self.target == "Hands":

            if collection["Hands"].children["Nails"].exclude:
                collection["Hands"].children["Nails"].exclude = False
            else:
                collection["Hands"].children["Nails"].exclude = True

        elif self.target == "Hands" and self.key == "Clawsies":

            if collection["Hands"].children["Clawsies"].exclude:
                collection["Hands"].children["Clawsies"].exclude = False
            else:
                collection["Hands"].children["Clawsies"].exclude = True


        return {"FINISHED"}


classes = [
    RemoveEmptyVGroups,
    ApplyShapes,
    ApplyVisibility
]
    