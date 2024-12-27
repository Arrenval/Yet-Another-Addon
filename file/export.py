import os
import bpy
import time
import random

from pathlib        import Path
from functools      import partial
from itertools      import combinations
from bpy.props      import StringProperty
from bpy.types      import Operator, Object, Context, ShapeKey
from ..util.props   import get_object_from_mesh, visible_meshobj

def add_driver(shape_key:ShapeKey, source:Object) -> None:
            shape_key.driver_remove("value")
            shape_key.driver_remove("mute")
            value = shape_key.driver_add("value").driver
            mute = shape_key.driver_add("mute").driver
            
            value.type = "AVERAGE"
            value_var = value.variables.new()
            value_var.name = "key_value"
            value_var.type = "SINGLE_PROP"

            value_var.targets[0].id_type = "KEY"
            value_var.targets[0].id = source.data.shape_keys
            value_var.targets[0].data_path = f'key_blocks["{shape_key.name}"].value'

            mute.type = "AVERAGE"
            mute_var = mute.variables.new()
            mute_var.name = "key_mute"
            mute_var.type = "SINGLE_PROP"
            
            mute_var.targets[0].id_type = "KEY"
            mute_var.targets[0].id = source.data.shape_keys
            mute_var.targets[0].data_path = f'key_blocks["{shape_key.name}"].mute'

def check_triangulation() -> tuple[bool, list[str]]:
    visible = visible_meshobj()
    not_triangulated = []

    for obj in visible:
        triangulated = False
        for modifier in reversed(obj.modifiers):
            if modifier.type == "TRIANGULATE" and modifier.show_viewport:
                triangulated = True
                break
        if not triangulated:
            not_triangulated.append(obj.name)
    
    if not_triangulated:
        return False, not_triangulated
    else:
        return True, not_triangulated

def force_yas(export="SIMPLE", body_slot="") -> None:
    devkit = bpy.context.scene.devkit_props
    if export == "SIMPLE":
        for obj in bpy.context.scene.objects:
            if obj.visible_get(view_layer=bpy.context.view_layer) and obj.type == "MESH":
                if obj.data.name == "Torso":
                    devkit.controller_yas_chest = True
                if obj.data.name == "Waist":
                    devkit.controller_yas_legs = True
                if obj.data.name == "Hands":
                    devkit.controller_yas_hands = True
                if obj.data.name == "Feet":
                    devkit.controller_yas_feet = True
    else:
        match body_slot:
            case "Chest":
                devkit.controller_yas_chest = True
            case "Legs":
                devkit.controller_yas_legs = True
            case "Hands":
                devkit.controller_yas_hands = True
            case "Feet":
                devkit.controller_yas_feet = True
            case "Chest & Legs":
                devkit.controller_yas_chest = True
                devkit.controller_yas_legs = True

def ivcs_mune(yas=False) -> None:
    chest_obj = []
    collection = bpy.data.collections.get("Chest")
    for obj in collection.all_objects:
        chest_obj.append(obj)

    for obj in chest_obj:
        for group in obj.vertex_groups:
            try:
                if yas:
                    if group.name == "j_mune_r":
                        group.name = "iv_c_mune_r"
                    if group.name == "j_mune_l":
                        group.name = "iv_c_mune_l"
                else:
                    if group.name == "iv_c_mune_r":
                            group.name = "j_mune_r"
                    if group.name == "iv_c_mune_l":
                        group.name = "j_mune_l"
            except:
                continue

def armature_visibility(export=False) -> None:
    # Makes sure armatures are enabled in scene's space data
    # W ill not affect armatures that are specifically hidden
    context = bpy.context
    if export:
        context.scene.animation_optimise.clear()
        optimise = bpy.context.scene.animation_optimise.add()
        optimise.show_armature = context.space_data.show_object_viewport_armature
        context.space_data.show_object_viewport_armature = True
    else:
        try:
            area = [area for area in context.screen.areas if area.type == 'VIEW_3D'][0]
            view3d = [space for space in area.spaces if space.type == 'VIEW_3D'][0]

            with context.temp_override(area=area, space=view3d):
                context.space_data.show_object_viewport_armature = optimise[0].show_armature
        except:
            pass

def save_sizes() -> dict[str, dict[str, float]]:
        obj    = get_object_from_mesh("Torso")
        saved_sizes = {
            "Large" : {},
            "Medium": {},
            "Small" : {}
        }

        for key in obj.data.shape_keys.key_blocks:
            if key.name.startswith("- "):
                name = key.name[2:]
                saved_sizes["Large"][name] = round(key.value, 2)
            if key.name.startswith("-- "):
                name = key.name[3:]
                saved_sizes["Medium"][name] = round(key.value, 2)
            if key.name.startswith("--- "):
                name = name = key.name[4:]
                saved_sizes["Small"][name] = round(key.value, 2)
        return saved_sizes

def reset_chest_values(saved_sizes) -> None:
    devkit       = bpy.context.scene.devkit
    devkit_props = bpy.context.scene.devkit_props
    base_size    = ["Large", "Medium", "Small"]

    for size in base_size:
        preset      = saved_sizes[size]
        category = devkit_props.ALL_SHAPES[size][2]
        devkit.ApplyShapes.apply_shape_values("torso", category, preset)
    
    bpy.context.view_layer.objects.active = get_object_from_mesh("Torso")
    bpy.context.view_layer.update()

class MeshHandler:

    def __init__(self):
        props                        = bpy.context.scene.file_props
        self.shapekeys  :bool         = props.keep_shapekeys
        self.backfaces  :bool         = props.create_backfaces
        self.reset      :list[Object] = []
        self.delete     :list[Object] = []
    
    def pre_export(self):
        if self.shapekeys:
            self.shape_key_keeper()
        if self.backfaces:
            self.create_backfaces()
        
        return self.reset, self.delete

    def check_modifiers(self, obj:Object, check_mesh=False) -> None:
        mesh_modifiers = ["MIRROR", "SUBSURF", "MASK", "WELD", "BEVEL", "SOLIDIFY"]
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                continue
            if not modifier.show_viewport:
                bpy.ops.object.modifier_remove(modifier=modifier.name)
                continue
            if check_mesh and any(modifier.type in m for m in mesh_modifiers):
                try:
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
                except:
                    bpy.ops.object.modifier_remove(modifier=modifier.name)
            elif not check_mesh:
                try:
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
                except:
                    bpy.ops.object.modifier_remove(modifier=modifier.name)

    def shape_key_keeper(self) -> None:

        def shapekey_object(original_obj:Object) -> Object:
            old_name = original_obj.name
            split    = old_name.split()
            split[0] = "ShapeKey"
            new_name = " ".join(split)
            original_obj.select_set(state=True)
            bpy.context.view_layer.objects.active = original_obj
            
            bpy.ops.object.duplicate()
            original_obj.hide_set(state=True)
            shapekey_obj = bpy.context.selected_objects[0]
            shapekey_obj.name = new_name
            self.reset.append(original_obj)
            self.delete.append(shapekey_obj)
            return shapekey_obj
        
        def create_dupe(shapekey_obj:Object, key:ShapeKey) -> Object:
            shapekey_obj.select_set(state=True)
            bpy.context.view_layer.objects.active = shapekey_obj

            bpy.ops.object.duplicate()
            shapekey_dupe = bpy.context.selected_objects[0]
            shapekey_dupe.data.shape_keys.key_blocks[key.name].value = 1.0
            bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
            shapekey_dupe.name = key.name
            return shapekey_dupe

        # Checks all visible meshes for valid shape keys to keep
        bpy.ops.object.select_all(action="DESELECT")
        visible_obj = visible_meshobj()
        
        # to_join are the temporary dupes with the shape keys activated that will be merged into the export mesh (shapekey_obj)
        to_join     :list[Object] = []

        for original_obj in visible_obj:
            if not original_obj.data.shape_keys:
                continue
            xiv_key = [key for key in original_obj.data.shape_keys.key_blocks if key.name.startswith("shp")]

            if xiv_key:
                shapekey_obj = shapekey_object(original_obj)

            for key in xiv_key:
                shapekey_dupe = create_dupe(shapekey_obj, key)
                shapekey_dupe.select_set(state=True)
                bpy.context.view_layer.objects.active = shapekey_dupe
                self.check_modifiers(shapekey_dupe, check_mesh=True)
                to_join.append(shapekey_dupe)
                bpy.ops.object.select_all(action="DESELECT")

            if to_join:
                shapekey_obj.select_set(state=True)
                bpy.context.view_layer.objects.active = shapekey_obj
                bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                self.check_modifiers(shapekey_obj)
                for dupe in to_join:
                    dupe.select_set(state=True)
                    bpy.ops.object.join_shapes()
                    bpy.data.objects.remove(dupe, do_unlink=True, do_id_user=True, do_ui_user=True)
                to_join = []
            bpy.ops.object.select_all(action="DESELECT")

    def create_backfaces(self) -> None:
        visible = visible_meshobj()
        for obj in visible:
            if not obj.vertex_groups.get("BACKFACES"):
                continue
            
            old_name = obj.name
            split    = old_name.split()
            split[0] = "Backfaces"
            new_name = " ".join(split)

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(state=True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate()
            obj.hide_set(state=True)
            backfaces_mesh = bpy.context.selected_objects[0]
            backfaces_mesh.name = new_name

            if backfaces_mesh.data.shape_keys:
                xiv_key = [key for key in backfaces_mesh.data.shape_keys.key_blocks if key.name.startswith("shp")]
            
            if not xiv_key:
                if backfaces_mesh.data.shape_keys:
                    bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                self.reset.append(obj)

            self.check_modifiers(backfaces_mesh)

            backfaces_mesh.vertex_groups.active = backfaces_mesh.vertex_groups["BACKFACES"]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.object.vertex_group_select()
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.flip_normals()
            self.delete.append(backfaces_mesh)
        if self.delete:
            bpy.ops.object.mode_set(mode='OBJECT')
    
    def restore_meshes(self) -> None:
        for obj in self.delete:
            bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
        
        for obj in self.reset:
            obj.hide_set(state=False)

class SimpleExport(Operator):
    bl_idname = "ya.simple_export"
    bl_label = "Simple Export"
    bl_description = "Exports single model based on visible objects"
    bl_options = {'REGISTER'}

    user_input: StringProperty(name="File Name", default="") # type: ignore

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"
    
    def __init__(self):
        self.props              = bpy.context.scene.file_props
        self.check_tris         = self.props.check_tris
        self.force_yas          = self.props.force_yas
        self.directory          = Path(self.props.export_directory)

    def invoke(self, context, event):
        if not self.directory.is_dir():
            self.report({'ERROR'}, "No export directory selected.")
            return {'CANCELLED'}
        
        if self.check_tris:
            triangulated, obj = check_triangulation()
            if not triangulated:
                self.report({'ERROR'}, f"Not Triangulated: {', '.join(obj)}")
                return {'CANCELLED'} 
            
        bpy.context.window_manager.invoke_props_dialog(self, confirm_text="Export")
        return {'RUNNING_MODAL'}

    def execute(self, context):
        mesh_handler        = MeshHandler()
        armature_visibility(export=True)

        if hasattr(context.scene, "devkit_props"):
            devkit_props = context.scene.devkit_props
            devkit_props.controller_uv_transfers = True
            if self.force_yas:
                force_yas(export="SIMPLE")
            obj = get_object_from_mesh("Controller")
            yas = obj.modifiers["YAS Chest"].show_viewport
            ivcs_mune(yas)

        mesh_handler.pre_export()
        FileExport().export_template(self.user_input, "")
        mesh_handler.restore_meshes()

        if hasattr(context.scene, "devkit_props"):
            ivcs_mune()
            devkit_props.controller_uv_transfers = False
        armature_visibility()
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

class BatchQueue(Operator):
    bl_idname = "ya.batch_queue"
    bl_label = "Export"
    bl_description = "Exports your scene based on your selections"
    bl_options = {'UNDO'}

    ob_mesh_dict = {
            "Chest": "Torso", 
            "Legs": "Waist", 
            "Hands": "Hands",
            "Feet": "Feet"
            }
    
    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def __init__(self):
        props                   = bpy.context.scene.file_props
        self.check_tris         = props.check_tris
        self.force_yas          = props.force_yas
        self.subfolder          = props.create_subfolder
        self.export_directory   = Path(props.export_directory)
        self.body_slot          = props.export_body_slot
        self.selected_directory = props.export_directory
        self.size_options       = self.get_size_options()

        self.leg_sizes = {
            "Melon": self.size_options["Melon"],
            "Skull": self.size_options["Skull"], 
            "Mini Legs": self.size_options["Mini Legs"]
            }

        self.queue = []
        self.leg_queue = []
        
    def execute(self, context):
        props = bpy.context.scene.file_props
        props.controller_uv_transfers = True
        if self.check_tris:
            triangulated, obj = check_triangulation()
            if not triangulated:
                self.report({'ERROR'}, f"Not Triangulated: {', '.join(obj)}")
                return {'CANCELLED'} 
        if self.subfolder:
            Path.mkdir(self.export_directory / self.body_slot, exist_ok=True)
        
        if not os.path.exists(self.selected_directory):
            self.report({'ERROR'}, "No directory selected for export!")
            return {'CANCELLED'} 

        if self.body_slot == "Chest & Legs":
            self.actual_combinations = self.shape_combinations("Chest")
            self.calculate_queue("Chest")
            self.actual_combinations = self.shape_combinations("Legs")
            self.calculate_queue("Legs")
        else:
            self.actual_combinations = self.shape_combinations(self.body_slot)
            self.calculate_queue(self.body_slot)

        if "Legs" in self.body_slot:
            gen_options = len(self.actual_combinations.keys())
        else:
            gen_options = 0

        if self.queue == []:
            self.report({'ERROR'}, "No valid combinations!")
            return {'CANCELLED'} 
        
        if self.body_slot == "Chest & Legs":
            if self.leg_queue == []:
                self.report({'ERROR'}, "No valid combinations!")
                return {'CANCELLED'} 
            
        self.collection_state()
        bpy.ops.yakit.collection_manager(preset="Export")

        if self.force_yas:
            force_yas(export="BATCH", body_slot=self.body_slot)

        if "Chest" in self.body_slot:
            obj = get_object_from_mesh("Controller")
            yas = obj.modifiers["YAS Chest"].show_viewport
            ivcs_mune(yas)

        props.export_total = len(self.queue)
        armature_visibility(export=True)
        BatchQueue.process_queue(context, self.queue, self.leg_queue, self.body_slot)
        return {'FINISHED'}
    
    # The following functions is executed to establish the queue and valid options 
    # before handing all variables over to queue processing

    def collection_state(self) -> None:
        collection_state = bpy.context.scene.devkit_props.collection_state
        collection_state.clear()
        collections = []
        match self.body_slot:
            case "Chest":
                collections = ["Chest"]
                if self.size_options["Piercings"]:
                    collections.append("Nipple Piercings")

            case "Legs":
                collections = ["Legs"]
                if self.size_options["Pubes"]:
                    collections.append("Pubes")

            case "Chest & Legs":
                collections = ["Chest", "Legs"]
                if self.size_options["Piercings"]:
                    collections.append("Nipple Piercings")
                if self.size_options["Pubes"]:
                    collections.append("Pubes")

            case "Hands":
                collections = ["Hands"]

            case "Feet":
                collections = ["Feet"]

        for name in collections:
            state = collection_state.add()
            state.name = name

    def get_size_options(self) -> dict[str, bool]:
        options = {}
        devkit = bpy.context.scene.devkit_props
        

        for shape, (name, slot, shape_category, description, body, key) in devkit.ALL_SHAPES.items():
            slot_lower = slot.lower().replace("/", " ")
            name_lower = name.lower().replace(" ", "_")

            prop_name = f"export_{name_lower}_{slot_lower}_bool"

            if hasattr(devkit, prop_name):
                options[shape] = getattr(devkit, prop_name)

        return options

    def calculate_queue(self, body_slot) -> None:
        mesh = self.ob_mesh_dict[body_slot]
        target = get_object_from_mesh(mesh).data.shape_keys.key_blocks

        leg_sizes = [key for key in self.leg_sizes.keys() if self.leg_sizes[key]]

        if body_slot != "Legs":
            for size, options_groups in self.actual_combinations.items(): 
                for options in options_groups:
                    name = BatchQueue.name_generator(options, size, "", 0, body_slot)
                    self.queue.append((name, options, size, "", target))
        else:
            # Legs need different handling due to genitalia combos     
            for size in leg_sizes:
                gen_options = len(self.actual_combinations.keys())
                for gen, options_groups in self.actual_combinations.items(): 
                    for options in options_groups:
                        if size == "Mini Legs" and any("Hip Dips" in option for option in options):
                            continue
                        name = BatchQueue.name_generator(options, size, gen, gen_options, body_slot) 
                        
                        if self.body_slot == "Chest & Legs":
                            self.leg_queue.append((name, options, size, gen, target))
                        else:
                            self.queue.append((name, options, size, gen, target))
        
    def shape_combinations(self, body_slot) -> dict[str, tuple]:
        devkit = bpy.context.scene.devkit_props
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
        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
            if any(shape in possible_parts for parts in possible_parts) and body_slot == slot and self.size_options[shape]:
                actual_parts.append(shape)  

        for r in range(0, len(actual_parts) + 1):
            if body_slot == "Hands":
                r = 1
            all_combinations.update(combinations(actual_parts, r))

        all_combinations = tuple(all_combinations)  

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
                       
    def name_generator(options, size, gen, gen_options, body_slot) -> str:
        devkit = bpy.context.scene.devkit_props
        yiggle = bpy.context.scene.file_props.force_yas

        if body_slot == "Chest & Legs":
            body_slot = "Chest"
        file_names = []
        
        gen_name = None

        #Loops over the options and applies the shapes name to file_names
        for shape, (name, slot, category, description, body, key) in devkit.ALL_SHAPES.items():
            if any(shape in options for option in options) and not shape.startswith("Gen") and name != "YAB":
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

        file_names.append(size_name)

        if body_slot == "Feet":
            file_names = reversed(file_names)

        if gen_name != None:
            file_names.append(gen_name)
        
        if yiggle:
            return "Yiggle - " + " - ".join(list(file_names))
        
        return " - ".join(list(file_names))
    
    # These functions are responsible for processing the queue.
    # Export queue is running on a timer interval until the queue is empty.

    def process_queue(context:Context, queue:list, leg_queue:list, body_slot:str) -> None:
        start_time = time.time()
        devkit_props = bpy.context.scene.devkit_props
        setattr(devkit_props, "is_exporting", False)

        # randomising the list gives a much better time estimate
        random.shuffle(queue)
        BatchQueue.progress_tracker(queue)
        saved_sizes = save_sizes()
        callback = partial(BatchQueue.export_queue, context, queue, leg_queue, body_slot, saved_sizes, start_time)
       
        bpy.app.timers.register(callback, first_interval=0.5) 
        
    def export_queue(context, queue:list, leg_queue, body_slot:str, saved_sizes, start_time) -> int | None:
        props        = context.scene.file_props
        devkit_props = bpy.context.scene.devkit_props
        collection   = context.view_layer.layer_collection.children
        
        if getattr(devkit_props, "is_exporting"):
            return 0.1
        setattr(devkit_props, "is_exporting", True)
        
        mesh_handler = MeshHandler()
        main_name, options, size, gen, target = queue.pop()
       
        BatchQueue.reset_model_state(body_slot, target)
        BatchQueue.apply_model_state(options, size, gen, body_slot, target, saved_sizes)
        props.export_file_name = main_name
        bpy.context.view_layer.update()

        if body_slot == "Hands":

            if size == "Straight" or size == "Curved":
                collection["Hands"].children["Clawsies"].exclude = False
                collection["Hands"].children["Nails"].exclude = True
                collection["Hands"].children["Nails"].exclude = True
    
            else:
                collection["Hands"].children["Clawsies"].exclude = True
                collection["Hands"].children["Nails"].exclude = False
                collection["Hands"].children["Nails"].children["Practical Uses"].exclude = False
        
        if body_slot == "Feet":

            if "Clawsies" in options:
                collection["Feet"].children["Toe Clawsies"].exclude = False
                collection["Feet"].children["Toenails"].exclude = True
                
    
            else:
                collection["Feet"].children["Toe Clawsies"].exclude = True
                collection["Feet"].children["Toenails"].exclude = False
        
        if body_slot == "Chest & Legs":
            exported = []
            for leg_task in leg_queue:
                leg_name, options, size, gen, leg_target = leg_task
                # rue_match stops non-rue tops to be used with rue legs and vice versa
                if BatchQueue.check_rue_match(options, main_name):
                    BatchQueue.reset_model_state("Legs", leg_target)
                    BatchQueue.apply_model_state(options, size, gen, "Legs", leg_target, saved_sizes)

                    combined_name = main_name + " - " + leg_name
                    final_name = BatchQueue.clean_file_name(combined_name)
                    if not any(final_name in name for name in exported):
                        exported.append(final_name)
                        mesh_handler.pre_export()
                        FileExport().export_template(final_name, "Chest & Legs")
        
        else:
            mesh_handler.pre_export()
            FileExport().export_template(main_name, body_slot)

        setattr(devkit_props, "is_exporting", False)

        mesh_handler.restore_meshes()
        if queue:
            end_time = time.time()
            duration = end_time - start_time
            props.export_time = duration
            BatchQueue.progress_tracker(queue)
            return 0.1
        else:
            if body_slot == "Chest" or body_slot == "Chest & Legs":
                ivcs_mune()
                reset_chest_values(saved_sizes)
            bpy.ops.yakit.collection_manager(preset="Restore")
            props.controller_uv_transfers = False
            BatchQueue.progress_reset(props)
            armature_visibility()
            return None

    # These functions are responsible for applying the correct model state and appropriate file name.
    # They are called from the export_queue function.

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

    def clean_file_name (file_name:str) -> str:
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

    def apply_model_state(options, size, gen, body_slot, ob, saved_sizes) -> None:
        Devkit = bpy.context.scene.devkit
        devkit_props = bpy.context.scene.devkit_props
        if body_slot == "Chest & Legs":
            body_slot = "Chest"

        for shape, (name, slot, category, description, body, key) in devkit_props.ALL_SHAPES.items():

            if shape == size and key != "":
                ob[key].mute = False

            if any(shape in options for option in options):
                if key != "":
                    ob[key].mute = False

        # Adds the shape value presets alongside size toggles
        if body_slot == "Chest":
            keys_to_filter = ["Nip Nops"]
            preset = {}
            filtered_preset = {}

            try:
                preset = saved_sizes[size]
            except:
                preset = Devkit.get_shape_presets(size)
            
            for key in preset.keys():
                if not any(key.endswith(sub) for sub in keys_to_filter):
                    filtered_preset[key] = preset[key]

            category = devkit_props.ALL_SHAPES[size][2]
            Devkit.ApplyShapes.mute_chest_shapes(ob, category)
            Devkit.ApplyShapes.apply_shape_values("torso", category, filtered_preset)
            bpy.context.view_layer.objects.active = get_object_from_mesh("Torso")
            bpy.context.view_layer.update()
                
        if gen != None and gen.startswith("Gen") and gen != "Gen A":
            ob[gen].mute = False

    def reset_model_state(body_slot, ob) -> None:
        devkit = bpy.context.scene.devkit_props
        if body_slot == "Chest & Legs":
            body_slot = "Chest"

        reset_shape_keys = []

        for shape, (name, slot, shape_category, description, body, key) in devkit.ALL_SHAPES.items():
            if key != "" and slot == body_slot:
                if shape == "Hip Dips":
                    reset_shape_keys.append("Hip Dips (for YAB)")
                    reset_shape_keys.append("Less Hip Dips (for Rue)")
                else:
                    reset_shape_keys.append(key)

        for key in reset_shape_keys:   
            ob[key].mute = True

    def progress_tracker(queue) -> None:
        props = bpy.context.scene.file_props
        props.export_progress = (props.export_total - len(queue)) / props.export_total
        props.export_step = (props.export_total - len(queue)) 
        props.export_file_name = queue[-1][0]
        bpy.context.view_layer.update()

    def progress_reset(props) -> None:
        props.export_total = 0
        props.export_progress = 0
        props.export_step = 0
        props.export_time = 0
        props.export_file_name = ""

class FileExport:

    def __init__(self):
        scene = bpy.context.scene
        self.gltf = scene.file_props.file_gltf
        self.subfolder = scene.file_props.create_subfolder
        self.selected_directory = Path(scene.file_props.export_directory)

    def export_template(self, file_name:str, body_slot:str):
        if self.subfolder:
            export_path = str(self.selected_directory / body_slot / file_name)
        else:
            export_path = str(self.selected_directory / file_name)
        export_settings = self.get_export_settings()

        if self.gltf:
            bpy.ops.export_scene.gltf(filepath=export_path + ".gltf", **export_settings)
        else:
            bpy.ops.export_scene.fbx(filepath=export_path + ".fbx", **export_settings)
        
    def get_export_settings(self) -> dict[str, str | int | bool]:
        if self.gltf:
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

CLASSES = [
    SimpleExport,
    BatchQueue
]