import bpy
import time

from pathlib                  import Path
from itertools                import combinations
from bpy.types                import Operator, Context

from .simple                  import check_triangulation, get_export_path, export_result
from ...properties            import get_file_properties, get_devkit_properties, get_window_properties, get_devkit_win_props
from ...preferences           import get_prefs
from ...utils.logging         import YetAnotherLogger
from ...utils.scene_optimiser import SceneOptimiser


class BatchQueue(Operator):
    # Currently very messy, will refactor later
    # The combinations and queue calculation is atrocious why did past me do this
    # It works tho, somehow

    bl_idname = "ya.batch_queue"
    bl_label = "Export"
    bl_description = "Exports your scene based on your selections"
    bl_options = {'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context: Context):
        self.props        = get_file_properties()
        self.window       = get_window_properties()
        self.prefs        = get_prefs()
        self.devkit_props = get_devkit_properties()
        self.devkit_win   = get_devkit_win_props()
        self.size_options = self.get_size_options()

        self.check_tris : bool  = self.window.check_tris
        self.subfolder  : bool  = self.window.create_subfolder
        self.export_dir         = Path(self.prefs.export_dir)
        self.file_format        = self.window.file_format
        self.body_slot  : str   = self.window.export_body_slot
        self.prefix     : str   = self.window.export_prefix
        self.collections        = self.devkit_props.collection_state
    
        self.leg_sizes = {
            "Melon": self.size_options["Melon"],
            "Skull": self.size_options["Skull"], 
            "Yanilla": self.size_options["Yanilla"], 
            "Mini Legs": self.size_options["Mini Legs"]
            }

        self.queue = []
        self.leg_queue = []

        if self.check_tris:
            self.devkit_win.devkit_triangulation = True
            not_triangulated= check_triangulation()
            if not_triangulated:
                self.report({'ERROR'}, f"Not Triangulated: {', '.join(not_triangulated)}")
                return {'CANCELLED'} 
        
        if not self.export_dir.is_dir():
            self.report({'ERROR'}, "No directory selected for export!")
            return {'CANCELLED'} 
        
        if self.subfolder:
            Path.mkdir(self.export_dir / self.body_slot, exist_ok=True)
        
        if self.body_slot == "Chest & Legs":
            self.actual_combinations = self.shape_combinations("Chest")
            self.calculate_queue("Chest")
            
            self.actual_combinations = self.shape_combinations("Legs")
            self.calculate_queue("Legs")
        else:
            self.actual_combinations = self.shape_combinations(self.body_slot)
            self.calculate_queue(self.body_slot)

        if self.queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        if self.body_slot == "Chest & Legs" and self.leg_queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        self.save_chest_sizes()
        self.collection_state()

        try:
            with SceneOptimiser(context, optimisation_level="high"):
                self.logger = YetAnotherLogger(total=len(self.queue), output_dir=self.export_dir, start_time=time.time())
                self.logger.start_terminal()
                for item in self.queue:
                    self.logger.log_progress(operation="Exporting files", clear_messages=True)
                    self.logger.log_separator()
                    self.logger.log(f"Size: {item[0]}")
                    self.logger.log_separator()
                    self.logger.log("Applying sizes...", 2)
                    self.export_queue(item, self.body_slot)
                    
        except Exception as e:
            if self.logger:
                self.logger.close(e)
        finally:
            if self.logger:
                self.logger.close()
            self.reset_chest_values()
            self.collections.export = False
            bpy.context.view_layer.update()
        return {"FINISHED"}
       
    def collection_state(self) -> None:
        if self.body_slot == "Chest" or self.body_slot == "Chest & Legs":
            self.collections.chest = True
            if self.size_options["Piercings"]:
                self.collections.nipple_piercings = True
            else:
                self.collections.nipple_piercings = False
            
            self.collections.legs = False
            self.collections.feet = False
            self.collections.hands = False
                
        if self.body_slot == "Legs" or self.body_slot == "Chest & Legs":
            self.collections.legs = True
            if self.size_options["Pubes"]:
                self.collections.pubes = True
            
            self.collections.feet = False
            self.collections.chest = False
            self.collections.hands = False

        elif self.body_slot ==  "Hands":
            self.collections.hands = True

            self.collections.feet = False
            self.collections.legs = False
            self.collections.chest = False

        elif self.body_slot ==  "Feet":
            self.collections.feet = True

            self.collections.legs = False
            self.collections.hands = False
            self.collections.chest = False
         
        self.collections.export = True

    def get_size_options(self) -> dict[str, bool]:
        options     = {}
        
        for shape, (name, slot, shape_category, description, body, key) in self.devkit_props.ALL_SHAPES.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(self.devkit_win, prop_name):
                options[shape] = getattr(self.devkit_win, prop_name)

        return options

    def calculate_queue(self, body_slot:str) -> None:

        def get_body_key(body:str, body_slot:str) -> str:
            if body == "Masc" and body_slot == "Chest":
                body = "Flat"
            if body_slot == "Chest":
                body_key = body
            else:
                body_key = f"{body} {body_slot}"

            return body_key
        
        def exception_handling(size:str, gen:str, gen_options:int) -> None:
            if body_key == "Lava" and size not in lava_sizes:
                return 
            if body_key != "Lava" and size == "Sugar":
                return 
            if body_key != "Flat" and size in masc_sizes:
                return
            if body_key == "Flat" and size not in masc_sizes:
                return 
            for options in options_groups:
                if (size == "Mini Legs" or body == "Lava") and any("Hip Dips" in option for option in options):
                    continue
                if body == "YAB" and any("Rue" in option for option in options):
                    continue
                if body_slot == "Chest" and body == "Rue" and "Rue" not in options:
                    continue
                if body_slot =="Legs" and body == "Rue" and "Rue Legs" not in options:
                    continue
                if body in ("Lava", "Rue") or body_key == "Masc Legs":
                    options = (*options, body_key)

                name = self.name_generator(options, size, body, len(enabled_bodies), gen, gen_options, body_slot)
                if (body_slot == "Feet" or body_slot == "Hands") and any(name in entry[0] for entry in self.queue):
                    continue
                if self.body_slot == "Chest & Legs" and body_slot == "Legs":
                    self.leg_queue.append((name, options, size, gen))
                else:
                    self.queue.append((name, options, size, gen))
                
        rue_export      = self.window.rue_export
        leg_sizes       = [key for key in self.leg_sizes.keys() if self.leg_sizes[key]]
        gen_options     = len(self.actual_combinations.keys())
        all_bodies      = ["YAB", "Rue", "Lava", "Masc"]
        lava_sizes      = ["Large", "Medium", "Small", "Sugar"]
        masc_sizes      = ["Flat", "Pecs"]
        enabled_bodies  = []

        for shape, (name, slot, category, description, body, key) in self.devkit_props.ALL_SHAPES.items():
            if body and slot == body_slot and self.size_options[shape]:
                enabled_bodies.append(shape)
    
        for body in all_bodies:
            body_key = get_body_key(body, body_slot)
            if body_key not in self.size_options:
                continue
            if self.size_options[body_key] == False:
                continue
            if not rue_export and body == "Rue":
                continue
            if body_slot != "Legs":
                for size, options_groups in self.actual_combinations.items():
                    exception_handling(size, "", 0)
            else:
                for size in leg_sizes:
                    if (body == "Lava" or body == "Masc") and (size == "Skull" or size == "Mini Legs" or size == "Yanilla"):
                        continue
                    for gen, options_groups in self.actual_combinations.items(): 
                        exception_handling(size, gen, gen_options)
                 
    def shape_combinations(self, body_slot:str) -> dict[str, set[tuple]]:
        devkit         = get_devkit_properties()
        possible_parts = [ 
            "Small Butt", "Soft Butt", "Hip Dips", "Rue Legs",
            "Buff", "Rue",
            "Clawsies"
            ]
        
        actual_parts        = []
        all_combinations    = set()
        actual_combinations = {}

        #Excludes possible parts based on which body slot they belong to
        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
            if any(shape in possible_parts for parts in possible_parts) and body_slot == slot and self.size_options[shape]:
                actual_parts.append(shape)  

        for r in range(0, len(actual_parts) + 1):
            all_combinations.update(combinations(actual_parts, r))

        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
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
              
    def name_generator(self, options:tuple[str, ...], size:str, body:str, bodies:int, gen:str, gen_options:int, body_slot:str) -> str:
        devkit      = get_devkit_properties()
        gen_name    = None

        if self.window.body_names or (bodies > 1 and "YAB" != body and body_slot != "Feet"):
            file_names = [body]
        elif bodies == 1 and body_slot == "Legs" and (body == "Lava" or body == "Masc"):
            file_names = [body]
        else:
            file_names = []

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body_bool, key) in devkit.ALL_SHAPES.items():
            if any(shape in options for option in options) and not shape.startswith("Gen"):
                if body_bool == True and not("Rue" not in body and "Rue" == name):
                    continue
                if name in file_names:
                    continue
                if name == "Hip Dips":
                    name = "Alt Hip"
                if name.endswith("Butt"):
                    name = name[:-len(" Butt")]
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

        if body == "Lava":
            if size_name == "Large":
                size_name = "Omoi"
            if size_name == "Medium":
                size_name = "Teardrop"
            if size_name == "Small":
                size_name = "Cupcake"

        if not (body_slot == "Legs" and (body == "Lava" or body == "Masc")):
            file_names.append(size_name)

        if body_slot == "Feet":
            file_names = reversed(file_names)

        if gen_name != None:
            file_names.append(gen_name)

        if self.prefix.strip():
            return f"{self.prefix.strip()} - " + " - ".join(list(file_names))
        
        return " - ".join(list(file_names))

    def export_queue(self, item: tuple, body_slot:str) -> int | None:

        def clean_file_name (file_name: str) -> str:
            parts = file_name.split(" - ")
            rue_match = False
            new_parts = []

            for part in parts:
                if part == "Rue":
                    if rue_match:
                        continue
                    rue_match = True
                new_parts.append(part)
                
            
            file_name = " - ".join(new_parts)

            return file_name
        
        def check_rue_match (options, file_name) -> bool:
            '''This function checks the name of the leg export vs the chest export and makes sure only 
            rue tops and bottoms are combined'''
            if "Rue" in file_name:
                if any("Rue Legs" in option for option in options):
                    return True
                else:
                    return False
            elif any("Rue Legs" in option for option in options):
                return False
        
            return True
    
        main_name, options, size, gen = item

        self.hand_feet_collection(body_slot, options, size)

        self.reset_model_state(body_slot)
        self.apply_model_state(options, size, gen, body_slot)
        
        if body_slot == "Chest & Legs":
            exported = []
            for leg_task in self.leg_queue:
                leg_name, options, size, gen = leg_task
                # rue_match stops non-rue tops to be used with rue legs and vice versa
                if check_rue_match(options, main_name):
                    self.reset_model_state("Legs")
                    self.apply_model_state(options, size, gen, "Legs")

                    combined_name = main_name + " - " + leg_name
                    final_name = clean_file_name(combined_name)
                    if not any(final_name in name for name in exported):
                        bpy.context.evaluated_depsgraph_get()
                        exported.append(final_name)
                        file_path = get_export_path(self.export_dir, final_name, self.subfolder, self.body_slot)
                        export_result(file_path, self.file_format, self.logger)
        
        else:
            bpy.context.evaluated_depsgraph_get()
            file_path = get_export_path(self.export_dir, main_name, self.subfolder, self.body_slot)
            export_result(file_path, self.file_format, self.logger)
    
    def hand_feet_collection(self, body_slot: str, options: tuple, size: str) -> None:
        if body_slot == "Hands":
            if size in ("Straight", "Curved"):
                self.collections.clawsies = True
    
            else:
                self.collections.nails = True
                self.collections.practical = True
        
        if body_slot == "Feet":
            if "Clawsies" in options:
                self.collections.toe_clawsies = True
                
            else:
                self.collections.toenails = True

    def apply_model_state(self, options: tuple[str, ...], size:str , gen: str, body_slot: str) -> None:
        if body_slot == "Chest & Legs":
            body_slot = "Chest"
        
        model = self.devkit_props

        if body_slot == "Legs":
            legs_to_value = {
                "Gen A":   '0',
                "Gen B":   '1',
                "Gen C":   '2',
                "Gen SFW": '3',

                "Melon":   '0',
                "Skull":   '1',
                "Yanilla": '2',
                "Masc Legs": '3',
                "Lava Legs": '4',
                "Mini Legs": '5',
            }

            leg_options = ("Masc Legs", "Lava Legs", "Mini Legs")
        
            leg_size = size
            for option in options:
                if option in leg_options:
                    leg_size = option

            model.leg_state.gen        = legs_to_value[gen]
            model.leg_state.leg_size   = legs_to_value[leg_size]
            model.leg_state.rue        = "Rue Legs" in options
            model.leg_state.small_butt = "Small Butt" in options
            
        elif body_slot == "Hands":
            hands_to_value = {
                "Rue Hands"  : '1',
                "Lava Hands" : '2'
            }

            nails_to_value = {
                "Long":      '0',
                "Short":     '1',
                "Ballerina": '2',
                "Stabbies":  '3',

                "Straight": '0',
                "Curved"  : '1',
            }

            hands = None
            for option in options:
                if option in hands_to_value:
                    hands = option

            model.hand_state.hand_size = '0' if hands is None else hands_to_value[option]
            model.hand_state.nails     = '0' if size not in nails_to_value[size] else nails_to_value[size]
            model.hand_state.clawsies  = '0' if size not in nails_to_value[size] else nails_to_value[size]
            
        elif body_slot == "Feet":
            model.feet_state.rue_feet = "Rue Feet" in options

        elif body_slot == "Chest":
            chest_to_value = {
                "Large":  '0',
                "Medium": '1',
                "Small":  '2',
                "Masc":   '3',
            }

            category = self.devkit_props.ALL_SHAPES[size][2]

            model.torso_state.chest_size = chest_to_value[category]
            model.torso_state.buff       = "Buff" in options
            model.torso_state.rue        = "Rue" in options
            model.torso_state.lavabod    = "Lava" in options

            if model.torso_state.lavabod:
                saved_sizes = self.lava_keys
            else:
                saved_sizes = self.yab_keys

            skip_keys                = ("Nip Nops",)
            preset: dict[str, float] = {}

            try:
                preset = saved_sizes[size]
            except:
                preset = self.devkit_props.get_shape_presets(size)
            
            key_filter = []
            for key in preset.keys():
                if key.endswith(skip_keys):
                    key_filter.append(key)
            
            for key in key_filter:
                del preset[key]
            
            for key_name, value in preset.items():
                model.yam_torso.data.shape_keys.key_blocks[key_name].value = value
                
    def reset_model_state(self,body_slot: str) -> None:
        if body_slot == "Chest & Legs":
            body_slot = "Chest"

        if body_slot == "Chest":
            self.devkit_props.torso_state.chest_size = '0'
            self.devkit_props.torso_state.buff       = False
            self.devkit_props.torso_state.rue        = False
            self.devkit_props.torso_state.lavabod    = False

        elif body_slot == "Legs":
            self.devkit_props.leg_state.gen        = '0'
            self.devkit_props.leg_state.leg_size   = '0'
            self.devkit_props.leg_state.small_butt = False
            self.devkit_props.leg_state.soft_butt  = False
            self.devkit_props.leg_state.alt_hips   = False

        elif body_slot == "Hands":
            self.devkit_props.hand_state.nails     = '0'
            self.devkit_props.hand_state.clawsies  = '0'
            self.devkit_props.hand_state.hand_size = '0'
            
        elif body_slot == "Feet":
            self.devkit_props.feet_state.rue_feet = False

    def save_chest_sizes(self) -> None:
        self.yab_keys: dict[str, float]  = {}
        self.lava_keys: dict[str, float] = {}

        obj       = self.devkit_props.yam_torso
        obj_state = self.devkit_props.torso_state
        
        if obj_state.lavabod:
            stored_keys = obj_state.yab_keys
        else:
            stored_keys = obj_state.lava_keys

        for key in obj.data.shape_keys.key_blocks:
            if not key.name.startswith("- "):
                continue
            if key.name.startswith("---- "):
                continue

            if obj_state.lavabod:
                self.lava_keys[key.name] = key.value
            else:
                self.yab_keys[key.name]  = key.value
        
        for key in stored_keys:
            if obj_state.lavabod:
                self.yab_keys[key.name]  = key.value
            else:
                self.lava_keys[key.name] = key.value

    def reset_chest_values(self) -> None:
        obj       = self.devkit_props.yam_torso
        obj_state = self.devkit_props.torso_state
        
        if obj_state.lavabod:
            new_values = obj_state.yab_keys
        else:
            new_values = obj_state.lava_keys

        new_values.clear()
        if obj_state.lavabod:
            for key_name, value in self.lava_keys.items():
                obj.data.shape_keys.key_blocks[key_name].value = value

            for key_name, value in self.yab_keys.items():
                new_value = new_values.add()
                new_value.name  = key_name  
                new_value.value = value      
        else:
            for key_name, value in self.yab_keys.items():
                obj.data.shape_keys.key_blocks[key_name].value = value

            for key_name, value in self.lava_keys.items():
                new_value = new_values.add()
                new_value.name  = key_name  
                new_value.value = value     
    

CLASSES = [
    BatchQueue
]