import bpy
import os
import json
import ya_utils as utils

from itertools import combinations
from functools import partial
from ya_shape_ops import MESH_OT_YA_ApplyShapes as ApplyShapes
from bpy.types import Operator
from bpy.props import StringProperty

# Global variable for making sure all functions can properly track the current export.
# Ease of use alongside blender's timers.
ya_is_exporting: bool = False

class FILE_OT_SimpleExport(Operator):
    bl_idname = "file.simple_export"
    bl_label = "Open FBX Export Window"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        gltf = context.scene.ya_props.export_gltf 
        directory = context.scene.ya_props.export_directory
        export_path = os.path.join(directory, "untitled")
        export_settings = FILE_OT_YA_FileExport.get_export_settings(gltf)

        if gltf:
            bpy.ops.export_scene.gltf('INVOKE_DEFAULT', filepath=export_path + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx('INVOKE_DEFAULT', filepath=export_path + ".fbx", **export_settings)
        
        return {'FINISHED'}


class FILE_OT_YA_BatchQueue(Operator):
    bl_idname = "file.batch_queue"
    bl_label = "Export"
    bl_description = "Exports your files based on your selections"
    bl_options = {'UNDO'}

    ob_mesh_dict = {
            "Chest": "Torso", 
            "Legs": "Waist", 
            "Hands": "Hands",
            "Feet": "Feet"
            }

    def __init__(self):
        self.size_options = None
        self.selected_directory = None
        self.filetype = None
        self.body_slot = None
        self.queue = []
        self.leg_queue = []
        
    def execute(self, context):
        prop = context.scene.ya_props
        selected_directory = prop.export_directory
        self.gltf = prop.export_gltf
        self.body_slot = prop.export_body_slot
        
        print (selected_directory)
        if not os.path.exists(selected_directory):
            self.report({'ERROR'}, "No directory selected for export!")
            return {'CANCELLED'} 

        self.size_options = self.get_size_options(context)
        to_keep = self.collection_state

        if self.body_slot == "Chest/Legs":
            self.actual_combinations = self.shape_combinations("Chest")
            self.calculate_queue("Chest")
            self.actual_combinations = self.shape_combinations("Legs")
            self.calculate_queue("Legs")
        else:
            self.actual_combinations = self.shape_combinations(self.body_slot)
            self.calculate_queue(self.body_slot)

        if self.body_slot == "Legs" or self.body_slot == "Chest/Legs":
            gen_options = len(self.actual_combinations.keys())
        else:
            gen_options = 0

        if self.queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        if self.body_slot == "Chest/Legs":
            if self.leg_queue == []:
                self.report({'ERROR'}, "No valid combinations!")
                return {'CANCELLED'} 
        
        bpy.ops.utils.collection_manager(extra_json = to_keep)
        FILE_OT_YA_BatchQueue.process_queue(context, self.queue, self.leg_queue, self.body_slot, gen_options)

        return {'FINISHED'}
    
    # The following functions is executed to establish the queue and valid options 
    # before handing all variables over to queue processing
    def collection_state(self):
        collections = []

        if self.body_slot == "Chest":
            collections = ["Chest"]
            if self.size_options["Piercings"]:
                collections.append("Nipple Piercings")

        elif self.body_slot == "Legs":
            collections = ["Legs"]
            if self.size_options["Pubes"]:
                collections.append("Pubes")

        elif self.body_slot == "Chest/Legs":
            collections = ["Chest", "Legs"]
            if self.size_options["Piercings"]:
                collections.append("Nipple Piercings")
            if self.size_options["Pubes"]:
                collections.append("Pubes")

        return json.dumps(collections)
    
    def get_size_options(self, context):
        options = {}
        prop = context.scene.ya_props

        for shape, (name, slot, shape_category, description, body, key) in utils.all_shapes.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(prop, prop_name):
                options[shape] = getattr(prop, prop_name)

        return options

    def calculate_queue(self, body_slot):
        mesh = self.ob_mesh_dict[body_slot]
        target = utils.get_object_from_mesh(mesh).data.shape_keys.key_blocks

        leg_sizes = {
            "Melon": self.size_options["Melon"],
            "Skull": self.size_options["Skull"], 
            "Mini Legs": self.size_options["Mini Legs"]
            }

        if body_slot != "Legs":
            gen = None             
            for size, options_groups in self.actual_combinations.items(): 
                for options in options_groups:
                    self.queue.append((options, size, gen, target))
            return "Main queue finished."

        # Legs need different handling due to genitalia combos     
        for size, enabled in leg_sizes.items():
            if enabled:
                for gen, options_groups in self.actual_combinations.items(): 
                    for options in options_groups:
                        if self.body_slot == "Chest/Legs":
                            self.leg_queue.append((options, size, gen, target))
                        else:
                            self.queue.append((options, size, gen, target))
        if self.leg_queue != []:
            return "No leg options selected."
        
        return "Leg queue finished."
 
    def shape_combinations(self, body_slot):
        possible_parts  = [
            "Rue Legs", "Small Butt", "Soft Butt", "Hip Dips",
            "Buff", "Rue", 
            "Rue Hands", "YAB Hands", 
            "Clawsies"
            ]
        actual_parts = []
        all_combinations = set()
        actual_combinations = {}

        
        #Excludes possible parts based on which body slot they belong to
        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():
            if any(shape in possible_parts for parts in possible_parts) and body_slot == slot and self.size_options[shape]:
                actual_parts.append(shape)  

        for r in range(0, len(actual_parts) + 1):
            if body_slot == "Hands":
                r = 1
            all_combinations.update(combinations(actual_parts, r))

        all_combinations = tuple(all_combinations)  

        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():
            if body_slot == "Legs":
                if self.size_options[shape] and category == "Vagina":
                    actual_combinations[shape] = all_combinations

            elif body_slot == "Chest" and slot == "Chest":
                if self.size_options[shape] and category != "":
                    actual_combinations[shape] = all_combinations

            elif body_slot == "Hands":
                if self.size_options[shape] and category == "Nails":
                    actual_combinations[shape] = all_combinations

            elif body_slot == "Feet":
                if self.size_options[shape] and category == "Feet":
                    actual_combinations[shape] = all_combinations

        return actual_combinations

    # These functions are responsible for processing the queue.
    # Export queue is running on a timer interval until the queue is empty.

    def process_queue(context, queue, leg_queue, body_slot, gen_options):
        global ya_is_exporting
        ya_is_exporting = False

        callback = partial(FILE_OT_YA_BatchQueue.export_queue, context, queue, leg_queue, body_slot, gen_options)
        
        bpy.app.timers.register(callback, first_interval=0.5) 

    def export_queue(context, queue, leg_queue, body_slot, gen_options):
        global ya_is_exporting

        if ya_is_exporting:
            return 0.1
        
        second_queue = leg_queue

        ya_is_exporting = True
        options, size, gen, target = queue.pop()
        
        FILE_OT_YA_BatchQueue.reset_model_state(body_slot, target)

        main_name = FILE_OT_YA_BatchQueue.name_generator(options, size, gen, gen_options, body_slot)
        FILE_OT_YA_BatchQueue.apply_model_state(options, size, gen, body_slot, target)

        if body_slot == "Hands":

            if size == "Straight" or size == "Curved":
                collections = ["Hands", "Clawsies"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
    
            else:
                collections = ["Hands", "Nails"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
    
        if body_slot == "Feet":

            if "Clawsies" in options:
                collections = ["Feet", "Toe Clawsies"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
    
            else:
                collections = ["Feet", "Toenails"]
                extra = json.dumps(collections)
                bpy.ops.utils.collection_manager(extra_json = extra)
        
        if body_slot == "Chest/Legs":
            for leg_task in second_queue:
                options, size, gen, target = leg_task
                if FILE_OT_YA_BatchQueue.check_rue_match(options, main_name):
                    body_slot = "Legs"
                    
                    FILE_OT_YA_BatchQueue.reset_model_state(body_slot, target)
                    FILE_OT_YA_BatchQueue.apply_model_state(options, size, gen, body_slot, target)

                    leg_name = FILE_OT_YA_BatchQueue.name_generator(options, size, gen, gen_options, body_slot)
                    main_name = leg_name + " - " + main_name
                    main_name = FILE_OT_YA_BatchQueue.clean_file_name(main_name)

                    FILE_OT_YA_FileExport.export_template(context, file_name=main_name)
        else:
            FILE_OT_YA_FileExport.export_template(context, file_name=main_name)

        ya_is_exporting = False

        if queue:
            return 0.1
        else:
            return None

    # These functions are responsible for applying the correct model state and appropriate file name.
    # They are called from the export_queue function.

    def check_rue_match (options, file_name):
        
        if any("Rue" in option for option in options):
            if "Rue" in file_name:
                return True
            else:
                return False
            
        elif "Rue" in file_name:
            return False

        else:
            return True

    def clean_file_name (file_name):
        first = file_name.find("Rue - ")

        second = file_name.find("Rue - ", first + len("Rue - "))

        if second == -1:
            return file_name
        
        return file_name[:second] + file_name[second + len("Rue - "):]

    def apply_model_state(options, size, gen, body_slot, ob):
        if body_slot == "Chest/Legs":
            body_slot = "Chest"

        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():

            if shape == size and key != "":
                ob[key].mute = False

            if any(shape in options for option in options):
                if key != "":
                    ob[key].mute = False

        # Adds the shape value presets alongside size toggles
        if body_slot == "Chest":
            keys_to_filter = ["Squeeze", "Squish", "Push-Up", "Nip Nops"]
            preset = utils.get_shape_presets(size)
            filtered_preset = {}
           

            for key in preset.keys():
                if not any(key.endswith(sub) for sub in keys_to_filter):
                    filtered_preset[key] = preset[key]

            category = utils.all_shapes[size][2]
            ApplyShapes.mute_chest_shapes(ob, category)
            ApplyShapes.apply_shape_values("torso", category, filtered_preset)
            bpy.context.view_layer.objects.active = utils.get_object_from_mesh("Torso")
            bpy.context.view_layer.update()
                
        
        if gen != None and gen.startswith("Gen") and gen != "Gen A":
            ob[gen].mute = False
                        
    def name_generator(options, size, gen, gen_options, body_slot):
        if body_slot == "Chest/Legs":
            body_slot = "Chest"
        file_names = []
        gen_name = None

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body, key) in utils.all_shapes.items():
            if any(shape in options for option in options) and not shape.startswith("Gen") and name != "YAB":
                if name == "Hip Dips":
                    name = "Alt Hip" 
                file_names.append(name)
        
        # Checks if any Genitalia shapes and applies the shortened name 
        # Ignores gen_name if only one option is selected
        if gen != None and gen.startswith("Gen") and gen_options > 1:
            gen_name = gen.replace("Gen ","")       
        
        # Tweaks name output for the sizes
        size_name = size.replace(" Legs", "").replace("YAB ", "")
        if size == "Skull":
            size_name = "Skull Crushers"
        if size == "Melon":
            size_name = "Watermelon Crushers"
        if size == "Short" or size == "Long":
            size_name = size + " Nails"

        file_names.append(size_name)

        if body_slot == "Feet":
            file_names = reversed(file_names)

        if gen_name != None:
            file_names.append(gen_name)
        
        return " - ".join(list(file_names))
    
    def reset_model_state(body_slot, ob):
        if body_slot == "Chest/Legs":
            body_slot = "Chest"

        reset_shape_keys = []

        for shape, (name, slot, shape_category, description, body, key) in utils.all_shapes.items():
            if key != "" and slot == body_slot:
                if shape == "Hip Dips":
                    reset_shape_keys.append("Hip Dips (for YAB)")
                    reset_shape_keys.append("Less Hip Dips (for Rue)")
                else:
                    reset_shape_keys.append(key)

        for key in reset_shape_keys:   
            ob[key].mute = True

    
class FILE_OT_YA_FileExport(Operator):
    bl_idname = "file.file_export"
    bl_label = "Export"
    bl_description = ""
    bl_options = {'UNDO'}

    file_name: str = StringProperty()
    preset: str = StringProperty()

    def execute(self, context):
            FILE_OT_YA_FileExport.export_template(context, self.file_name)

    def export_template(context, file_name):
        gltf = context.scene.ya_props.export_gltf
        selected_directory = context.scene.ya_props.export_directory

        export_path = os.path.join(selected_directory, file_name)
        export_settings = FILE_OT_YA_FileExport.get_export_settings(export_path, gltf)

        if gltf:
            bpy.ops.export_scene.gltf(filepath=export_path + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx(filepath=export_path + ".fbx", **export_settings)
        
        
    def get_export_settings(gltf):
        if gltf:
            return {
                "export_format": "GLTF_SEPARATE", 
                "export_texture_dir": "GLTF Textures",
                "use_selection": False,
                "use_active_collection": False,
                "export_animations": False,
                "export_extras": True,
                "export_leaf_bone": False,
                "export_apply": True,
                "use_visible": True,
                "export_try_sparse_sk": False,
                "export_attributes": True,
                "export_tangents": True,
                "export_influence_nb": 8,
                "export_active_vertex_color_when_no_material": True,
                "export_all_vertex_colors": True,
                "export_image_format": "NONE"
            }
        
        else:
            return {
                "use_selection": False,
                "use_active_collection": False,
                "bake_anim": False,
                "use_custom_props": True,
                "use_triangles": False,
                "add_leaf_bones": False,
                "use_mesh_modifiers": True,
                "use_visible": True,
            }

