import bpy
import time
import tempfile

from pathlib         import Path
from itertools       import combinations
from bpy.types       import Operator, Context, Object
from bpy.props       import StringProperty, BoolProperty
   
from ...props        import get_file_props, get_devkit_props, get_window_props, get_devkit_win_props
from ...utils        import SceneOptimiser, PenumbraClient
from ...ui.draw      import aligned_row, show_ui_button
from ...io.logging   import YetAnotherLogger
from ...xivpy.pmp    import Modpack, sanitise_path
from ...preferences  import get_prefs
from ...mesh.export  import check_triangulation, get_export_path, export_result, get_export_stats
from ...mesh.objects import visible_meshobj


_yab_keys : dict[str, float] = {}
_lava_keys: dict[str, float] = {}

def save_chest_sizes() -> None:
    global _yab_keys, _lava_keys
    devkit_props = get_devkit_props()

    obj       = devkit_props.yam_torso
    obj_state = devkit_props.torso_state
    
    if obj_state.lavabod:
        stored_keys = obj_state.yab_keys
    else:
        stored_keys = obj_state.lava_keys

    for key in obj.data.shape_keys.key_blocks:
        if not key.name.startswith("-"):
            continue
        if key.name.startswith("----"):
            continue

        if obj_state.lavabod:
            _lava_keys[key.name] = key.value
        else:
            _yab_keys[key.name]  = key.value
    
    for key in stored_keys:
        if obj_state.lavabod:
            _yab_keys[key.name]  = key.value
        else:
            _lava_keys[key.name] = key.value

def reset_chest_values() -> None:
    global _yab_keys, _lava_keys
    devkit_props = get_devkit_props()

    obj       = devkit_props.yam_torso
    obj_state = devkit_props.torso_state
    
    if obj_state.lavabod:
        apply = _lava_keys
        new_values = obj_state.yab_keys

        store = _yab_keys
    else:
        apply = _yab_keys
        new_values = obj_state.lava_keys

        store = _lava_keys

    new_values.clear()
    for key_name, value in apply.items():
        obj.data.shape_keys.key_blocks[key_name].value = value

    for key_name, value in store.items():
        new_value = new_values.add()
        new_value.name  = key_name  
        new_value.value = value      

    _yab_keys  = {}
    _lava_keys = {}

def collection_state(body_slot: str, piercings: bool, pubes: bool) -> None:
    collections = get_devkit_props().collection_state

    if body_slot == "Chest" or body_slot == "Chest & Legs":
        collections.export_chest(piercings)
            
    if body_slot == "Legs" or body_slot == "Chest & Legs":
        collections.export_legs(pubes)

    elif body_slot ==  "Hands":
        collections.export_hands()

    elif body_slot ==  "Feet":
        collections.export_feet()
        
    collections.export = True

def hand_feet_collection(body_slot: str, options: tuple, size: str) -> None:
    collections = get_devkit_props().collection_state

    if body_slot == "Hands":
        if size in ("Straight", "Curved"):
            collections.clawsies = True

        else:
            collections.nails = True
            collections.practical = True
    
    if body_slot == "Feet":
        if "Clawsies" in options:
            collections.toe_clawsies = True
            
        else:
            collections.toenails = True

def apply_model_state(options: tuple[str, ...], size:str , gen: str, body_slot: str) -> None:
    global _yab_keys, _lava_keys
    devkit = get_devkit_props()

    if body_slot == "Legs":
        gen_to_value = {
            "Gen A":   '0',
            "Gen B":   '1',
            "Gen C":   '2',
            "Gen SFW": '3',
        }
        legs_to_value = {
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

        devkit.leg_state.gen        = gen_to_value[gen]
        devkit.leg_state.leg_size   = legs_to_value[leg_size]
        devkit.leg_state.rue        = "Rue Legs" in options
        devkit.leg_state.small_butt = "Small Butt" in options
        
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
        }
        claws_to_value = {
            "Straight": '0',
            "Curved"  : '1',
        }

        hands = None
        for option in options:
            if option in hands_to_value:
                hands = option

        devkit.hand_state.hand_size = '0' if hands is None else hands_to_value[option]
        devkit.hand_state.nails     = '0' if size not in nails_to_value else nails_to_value[size]
        devkit.hand_state.clawsies  = '0' if size not in claws_to_value else claws_to_value[size]
        
    elif body_slot == "Feet":
        devkit.feet_state.rue_feet = "Rue Feet" in options

    elif body_slot == "Chest":
        chest_to_value = {
            "Large":  '0',
            "Medium": '1',
            "Small":  '2',
            "Masc":   '3',
        }
        category = devkit.ALL_SHAPES[size][2]

        devkit.torso_state.chest_size = chest_to_value[category]
        devkit.torso_state.buff       = "Buff" in options
        devkit.torso_state.rue        = "Rue" in options
        devkit.torso_state.lavabod    = "Lava" in options

        if devkit.torso_state.lavabod:
            saved_sizes = _lava_keys
        else:
            saved_sizes = _yab_keys

        skip_keys                = ("Nip Nops",)
        preset: dict[str, float] = {}

        if size in ("Large", "Medium", "Small"):
            preset = saved_sizes
        else:
            preset = devkit.get_shape_presets(size)
        
        key_filter = []
        for key in preset.keys():
            if key.endswith(skip_keys):
                key_filter.append(key)
        
        for key in key_filter:
            del preset[key]
        
        for key_name, value in preset.items():
            devkit.yam_torso.data.shape_keys.key_blocks[key_name].value = value
                
def reset_model_state(body_slot: str) -> None:
    devkit  = get_devkit_props()
    
    if body_slot == "Chest":
        devkit.reset_torso()

    elif body_slot == "Legs":
        devkit.reset_legs()

    elif body_slot == "Hands":
        devkit.reset_hands()
        
    elif body_slot == "Feet":
        devkit.reset_feet()

def verify_armature(objects: list[Object]) -> bool:
    no_armature = []
    armatures   = set()
    for obj in objects:
        if not obj.parent or obj.parent.type != 'ARMATURE':
            no_armature.append(obj)
        armatures.add(obj.parent)

    return no_armature or len(armatures) != 1

def set_armature(objects: list[Object], armature: Object) -> None:
    for obj in objects:
        obj.parent = armature

        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.object = armature

def check_mod_tag(folder: Path) -> bool:
    try:
        pmp = Modpack.read_meta(folder)
        return "YABlender" in pmp.meta.ModTags
    except FileNotFoundError:
        return False

class YetAnotherExport(Operator):
    bl_idname = "ya.export"
    bl_label = "Export"
    bl_description = "Exports your scene based on your selections"
    bl_options = {'UNDO'}
    
    user_input: StringProperty(name="File Name", default="", options={'HIDDEN'}) # type: ignore

    mode        : StringProperty(name="", default="SIMPLE", options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    show_objs   : BoolProperty(
                    name="",
                    description="", 
                    default=False, 
                    options={'HIDDEN', "SKIP_SAVE"}
                    ) # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def invoke(self, context: Context, event):
        self.penumbra    = self.mode == 'PENUMBRA'
        self.window      = get_window_props()
        self.prefs       = get_prefs()
        self.file_format = 'MDL' if self.penumbra else self.window.file.model_format
        self.export_dir  = Path(get_prefs().export.output_dir)
        self.visible     = visible_meshobj()
        self.no_armature = verify_armature(self.visible)
        self.client      = PenumbraClient() if self.penumbra else None
        penum_mod_name   = self.window.file.penumbra_mod if self.penumbra else None
        penumbra_dir     = self.client.get_dir() if self.client else None
        self.logger      = YetAnotherLogger(
                                    total=1, 
                                    output_dir=self.export_dir, 
                                    start_time=time.time()
                                )

        if not self.penumbra and not self.export_dir.is_dir():
            self.report({'ERROR'}, "No export directory selected.")
            return {'CANCELLED'}
        elif self.penumbra and (penumbra_dir is None or not penumbra_dir.strip()):
            self.report({'ERROR'}, "Couldn't retrieve Penumbra Mod Directory. Make sure FFXIV is running.")
            return {'CANCELLED'}
        elif self.penumbra and (not penum_mod_name.strip() or not self.window.file.is_property_set("penumbra_mod")):
            self.report({'ERROR'}, "Please enter a mod name.")
            return {'CANCELLED'}
        
        self.penum_conflict = self._penumbra_validate(penumbra_dir, penum_mod_name)
        
        if self.window.check_tris or self.file_format == 'MDL':
            not_triangulated = check_triangulation()
            if not_triangulated:
                self.report({'ERROR'}, f"Not Triangulated: {', '.join(not_triangulated)}.")
                return {'CANCELLED'}
            
        if self.mode == "SIMPLE" or self.no_armature or self.penum_conflict:
            bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Export")
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)
    
    def _penumbra_validate(self, penumbra_dir: str | None, mod_name: str) -> bool:
        if penumbra_dir is None:
            return False
        
        self.penum_mod    = sanitise_path(mod_name)
        self.penum_folder = Path(penumbra_dir) / self.penum_mod

        return self.penum_folder.is_dir() and not check_mod_tag(self.penum_folder)

    def execute(self, context):
        if self.no_armature:
            armature = get_file_props().export_armature
            if not armature:
                self.report({'ERROR'}, "Armature was not set.")
                return {'CANCELLED'}
            set_armature(self.visible, armature)

        armature = self.visible[0].parent
        arm_vis  = armature.hide_get()
        armature.hide_set(state=False)
        bpy.context.window.cursor_set('WAIT')
        try:
            with SceneOptimiser(bpy.context, optimisation_level="high"):
                if self.mode == 'SIMPLE':
                    file_name: str = self.user_input.strip()
                    if file_name == "":
                        self.report({'ERROR'}, "Missing file name.")
                        return {'CANCELLED'}
                    self.simple_export(file_name)
                
                elif self.mode == 'PENUMBRA':
                    if not get_window_props().file.io.valid_xiv_path:
                        self.report({'ERROR'}, "Please input a path to your target model.")
                        return {'CANCELLED'}
                    self.penumbra_export()
                
                else:
                    self.batch_export()

        except ConnectionError:
            self.report({'ERROR'}, "Couldn't Connect to Penumbra. Make sure FFXIV is running.")
            return {'CANCELLED'}

        except Exception as e:
            if self.logger:
                if self.penumbra:
                    self.export_dir        = self.penum_folder
                    self.logger.output_dir = self.penum_folder
                    self.penum_folder.mkdir(exist_ok=True)

                self.logger.close(e)
                self.report({'ERROR'}, f"Exporter ran into an error, please see the log in {self.export_dir}.")
            else:
                self.report({'ERROR'}, f"Error during export: {e}")
            return {'CANCELLED'}
        
        finally:
            bpy.context.window.cursor_set('DEFAULT')
            if self.logger:
                self.logger.close()

            for obj in self.visible:
                try:
                    obj.select_set(state=True)
                except:
                    pass
            armature.hide_set(state=arm_vis)

        if self.file_format == 'MDL':
            get_export_stats(context)
        else:
            self.report({'INFO'}, "Export complete!")
        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        if self.penum_conflict:
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(icon='INFO', text="Mod already exists, it will be replaced.")

            layout.separator(type='LINE')

        if self.no_armature:
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(icon='ERROR', text="Missing or multiple armatures detected.")
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(text="Please select an armature to use for your export.")

            layout.separator(type='LINE')

            button, row = show_ui_button(layout, self, "show_objs", "Show Object/Armature")   
            if button:
                layout.separator(type='LINE', factor=0.5)

                for obj in self.visible:
                    parent = "" if not obj.parent or obj.parent.type != 'ARMATURE' else obj.parent.name
                    aligned_row(layout, f"{obj.name}:", parent, factor=0.5)

            layout.separator(type='LINE')

            aligned_row(layout, "Armature:", "export_armature", get_file_props())

            if self.mode == "SIMPLE":
                layout.separator(type='LINE')

        if self.mode == "SIMPLE":
            aligned_row(layout, "File Name:", "user_input", self)

    def simple_export(self, file_name) -> set[str]:
        devkit = get_devkit_props()

        if devkit:
            devkit.collection_state.export = True
        
        export_result(self.export_dir / file_name, self.file_format)

        if devkit:
            devkit.collection_state.export = False
    
    def penumbra_export(self) -> set[str]:
        redraw_mode = get_window_props().file.redraw_mode
        
        self.create_modpack(self.penum_folder)

        self.client.open_window()
        self.client.reload_mod(path=self.penum_mod)
        self.client.focus_mod(path=self.penum_mod)
        self.client.set_mod_settings(path=self.penum_mod, priority=999, state=True)
        if redraw_mode != 'GLAM':
            self.client.redraw(redraw_mode)

    def create_modpack(self, folder: Path) -> Modpack:
        file_name = "yamodel_" + hex(int(time.time()))[2:]
        xiv_path  = get_window_props().file.io.export_xiv_path
        rel_path  = "Blender\\" + file_name + ".mdl"

        pmp = Modpack()
        pmp.meta.Author  = "Blender"
        pmp.meta.Version = "TEST"
        pmp.meta.Name    = self.penum_mod
        pmp.meta.ModTags.append("YABlender")
        pmp.default.Files[xiv_path] = rel_path

        with tempfile.TemporaryDirectory(prefix=f"_penumbra_blender_", ignore_cleanup_errors=True) as temp_dir:
            temp_path       = Path(temp_dir)
            self.export_dir = temp_path
            self.simple_export(file_name)
            temp_mdl = temp_path / (file_name + ".mdl")
            pmp.to_folder(folder, {temp_mdl: rel_path})

    def batch_export(self) -> set[str]:
        self.props = get_file_props()
        
        self.ALL_SHAPES   = get_devkit_props().ALL_SHAPES
        self.size_options = self._get_size_options()
        self.body_slot    = self.window.file.io.export_body_slot
    
        self.leg_sizes = {
            "Melon": self.size_options["Melon"],
            "Skull": self.size_options["Skull"], 
            "Yanilla": self.size_options["Yanilla"], 
            "Mini Legs": self.size_options["Mini Legs"]
            }

        self.queue     = []
        self.leg_queue = []

        if self.window.create_subfolder:
            Path.mkdir(self.export_dir / self.body_slot, exist_ok=True)
        
        if self.body_slot == "Chest & Legs":
            self.actual_combinations = self._shape_combinations("Chest")
            self._calculate_queue("Chest")
            
            self.actual_combinations = self._shape_combinations("Legs")
            self._calculate_queue("Legs")
        else:
            self.actual_combinations = self._shape_combinations(self.body_slot)
            self._calculate_queue(self.body_slot)

        if self.queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        if self.body_slot == "Chest & Legs" and self.leg_queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        save_chest_sizes()
        get_devkit_props().export_state(
            self.body_slot, 
            self.size_options["Piercings"], 
            self.size_options["Pubes"]
            )

        try:
            self.logger.total = len(self.queue)
            for item in self.queue:
                self.logger.log_progress(operation="Exporting files", clear_messages=True)
                self.logger.log_separator()
                self.logger.log(f"Size: {item[0]}")
                self.logger.log_separator()
                self.logger.log("Applying sizes...", 2)

                self._process_queue(item, self.body_slot, leg_queue=self.leg_queue)
        
        finally:
            reset_chest_values()
            get_devkit_props().collection_state.export = False
            bpy.context.view_layer.update()
    
    def _get_size_options(self) -> dict[str, bool]:
        devkit_win = get_devkit_win_props()
        options    = {}
        
        for shape, (name, slot, shape_category, description, body, key) in self.ALL_SHAPES.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(devkit_win, prop_name):
                options[shape] = getattr(devkit_win, prop_name)

        return options

    def _calculate_queue(self, body_slot:str) -> None:

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

                name = self._name_generator(options, size, body, len(enabled_bodies), gen, gen_options, body_slot)
                if (body_slot == "Feet" or body_slot == "Hands") and any(name in entry[0] for entry in self.queue):
                    continue
                if self.body_slot == "Chest & Legs" and body_slot == "Legs":
                    self.leg_queue.append((name, options, size, gen))
                else:
                    self.queue.append((name, options, size, gen))
                
        rue_export     = self.window.rue_export
        leg_sizes      = [key for key in self.leg_sizes.keys() if self.leg_sizes[key]]
        gen_options    = len(self.actual_combinations.keys())
        all_bodies     = ["YAB", "Rue", "Lava", "Masc"]
        lava_sizes     = ["Large", "Medium", "Small", "Sugar"]
        masc_sizes     = ["Flat", "Pecs"]
        enabled_bodies = []

        for shape, (name, slot, category, description, body, key) in self.ALL_SHAPES.items():
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
                 
    def _shape_combinations(self, body_slot:str) -> dict[str, set[tuple]]:
        devkit         = get_devkit_props()
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
              
    def _name_generator(self, options:tuple[str, ...], size:str, body:str, bodies:int, gen:str, gen_options:int, body_slot:str) -> str:
        gen_name    = None

        if self.window.body_names or (bodies > 1 and "YAB" != body and body_slot != "Feet"):
            file_names = [body]
        elif bodies == 1 and body_slot == "Legs" and (body == "Lava" or body == "Masc"):
            file_names = [body]
        else:
            file_names = []

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body_bool, key) in self.ALL_SHAPES.items():
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

        prefix = self.window.file.io.export_prefix
        if prefix:
            return f"{prefix} - " + " - ".join(list(file_names))
        
        return " - ".join(list(file_names))

    def _process_queue(self, item: tuple, body_slot:str, export=True, leg_queue=[]) -> int | None:
        if body_slot == "Chest & Legs":
            body_slot = "Chest"

        file_name, options, size, gen = item
        
        hand_feet_collection(body_slot, options, size)
        
        reset_model_state(body_slot)
        apply_model_state(options, size, gen, body_slot)
        
        if leg_queue:
            self._handle_combined_slots(file_name)
            
        elif export:
            self._export_item(file_name)
    
    def _handle_combined_slots(self, torso_name: str):

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

        exported = set()
        for leg_task in self.leg_queue:
            combined_name = torso_name + " - " + leg_task[0]
            final_name = clean_file_name(combined_name)

            # rue_match stops non-rue tops to be used with rue legs and vice versa
            if check_rue_match(leg_task[1], torso_name):
                self._process_queue(leg_task, "Legs", export=False)
                if final_name not in exported:
                    self._export_item(final_name)
                    exported.add(final_name)

    def _export_item(self, file_name: str):
        file_path = get_export_path(self.export_dir, file_name, self.window.create_subfolder, self.body_slot)
        export_result(file_path, self.file_format, logger=self.logger, batch=True)
    

CLASSES = [
    YetAnotherExport
]