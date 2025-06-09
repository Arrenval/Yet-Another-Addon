import os
import bpy

from pathlib        import Path
from bpy.types      import Operator, Context
from bpy.props      import StringProperty, EnumProperty, BoolProperty, IntProperty
from .containers    import BlendModOption, BlendModGroup, CorrectionEntry, ModFileEntry, ModMetaEntry
from ...properties  import get_file_properties, get_outfit_properties, safe_set_enum
from ...preferences import get_preferences

class FrameJump(Operator):
    bl_idname = "ya.frame_jump"
    bl_label = "Jump to Endpoint"
    bl_description = "Jump to first/last frame in frame range"
    bl_options = {'REGISTER'}

    end: BoolProperty() # type: ignore
 
    def execute(self, context):
        bpy.ops.screen.frame_jump(end=self.end)
        get_outfit_properties().animation_frame = context.scene.frame_current

        return {'FINISHED'}

class KeyframeJump(Operator):
    bl_idname = "ya.keyframe_jump"
    bl_label = "Jump to Keyframe"
    bl_description = "Jump to previous/next keyframe"
    bl_options = {'REGISTER'}

    next: BoolProperty() # type: ignore

    def execute(self, context):
        bpy.ops.screen.keyframe_jump(next=self.next)
        get_outfit_properties().animation_frame = context.scene.frame_current

        return {'FINISHED'}
    
class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select file or directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype="DIR_PATH",
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context, event):
        self.props = get_file_properties()
        actual_dir = getattr(self.props, f"{self.category}_dir", "")     

        if event.alt and event.type == "LEFTMOUSE" and os.path.isdir(actual_dir):
            os.startfile(actual_dir)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)
        else:
             self.report({"ERROR"}, "Not a directory!")
    
        return {"RUNNING_MODAL"}

    def execute(self, context):
        actual_dir_prop = f"{self.category}_dir"
        display_dir_prop = f"{self.category}_display_dir"
        selected_file = Path(self.directory)  

        if selected_file.is_dir():
            setattr(self.props, actual_dir_prop, str(selected_file))
            setattr(self.props, display_dir_prop, str(Path(*selected_file.parts[-3:])))
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}

class ModpackFileSelector(Operator):
    bl_idname = "ya.modpack_file_selector"
    bl_label = "Select File"
    bl_description = "CTRL click to remove file entry"
    
    filepath : StringProperty(subtype="FILE_PATH") # type: ignore

    category: StringProperty(options={'HIDDEN'}) # type: ignore
    group   : IntProperty(options={'HIDDEN'}) # type: ignore
    option  : IntProperty(options={'HIDDEN'}) # type: ignore
    entry   : IntProperty(options={'HIDDEN'}) # type: ignore

    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context, event):
        self.group:int
        self.option:int
        self.container:BlendModGroup | BlendModOption | ModFileEntry

        mod_group = context.scene.pmp_mod_groups[self.group]
        group_options:list[BlendModOption] = mod_group.mod_options
   
        self.container = group_options[self.option].file_entries[self.entry]

        self.filter_glob = "*.mdl;*.phyb;*.tex"

        if event.ctrl and event.type == "LEFTMOUSE":
            bpy.ops.ya.modpacker_ui_containers(
            'EXEC_DEFAULT',
            add=False,
            category=self.category,
            group=self.group,
            option=self.option,
            entry=self.entry)

        else:
            context.window_manager.fileselect_add(self,)

        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_file = Path(self.filepath) 

        if selected_file.is_file():
            self.container.file_path = str(selected_file)
            self.report({"INFO"}, f"File selected: {selected_file.name}")
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}
    
class ModpackDirSelector(Operator):
    bl_idname = "ya.modpack_dir_selector"
    bl_label = "Select folder"
    bl_description = """Options:
    *SHIFT click to copy directory from file export.
    *CTRL click to remove folder. 
    *ALT click to open the folder"""
    
    directory: StringProperty(subtype="DIR_PATH") # type: ignore

    category: StringProperty(options={'HIDDEN'}) # type: ignore
    group   : IntProperty(options={'HIDDEN'}) # type: ignore
    option  : IntProperty(options={'HIDDEN'}) # type: ignore

    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context, event):
        self.group:int
        self.option:int
        self.container:BlendModGroup | BlendModOption | ModFileEntry

        self.prefs  = get_preferences()

        mod_group = context.scene.pmp_mod_groups[self.group]
        group_options:list[BlendModOption] = mod_group.mod_options
   
        match self.category:
            case "GROUP":
                self.container = mod_group
                self.folder    = self.container.folder_path
                attribute      = "file_path"

            case "OPTION":
                self.container = group_options[self.option]
                self.folder    = self.container.folder_path
                attribute      = "file_path"
            case "OUTPUT_PMP":
                self.folder    = self.container.modpack_output_dir
                attribute      = "modpack_output_dir"

        self.filter_glob = "DIR_PATH"

        if self.folder == "":
            context.window_manager.fileselect_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.folder = Path(self.folder)
            
        if event.ctrl and event.type == "LEFTMOUSE" and self.folder.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.property_unset("modpack_output_display_dir")
            else:
                self.container.property_unset(attribute)
            return {'FINISHED'}
        
        elif event.alt and event.type == "LEFTMOUSE" and self.folder.is_dir():
            os.startfile(self.folder)
        elif event.shift and event.type == "LEFTMOUSE":
            bpy.ops.ya.directory_copy(
                "EXEC_DEFAULT", 
                category=self.category,
                group=self.group,
                option=self.option)
        else:
            context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_file = Path(self.directory)  

        if selected_file.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.modpack_output_display_dir = str(Path(*selected_file.parts[-3:]))
                self.prefs.modpack_output_dir = str(selected_file)
            else:
                self.container.folder_path = str(selected_file)
            self.report({"INFO"}, f"Directory selected: {selected_file}")
        else:
            self.report({"ERROR"}, "Not a valid path!")
        
        return {'FINISHED'}

class CopyToModpacker(Operator):
    bl_idname = "ya.directory_copy"
    bl_label = "Copy Path"
    bl_description = "Copies the export directory to your modpack directory. This should be where your FBX files are located"

    category: StringProperty() # type: ignore

    group   : IntProperty() # type: ignore
    option  : IntProperty() # type: ignore

    def execute(self, context):
        self.group:int
        self.option:int
        prefs = get_preferences()
        export_dir = Path(prefs.export_dir)

        scene = context.scene

        mod_groups: list[BlendModGroup] = scene.pmp_mod_groups

        if len(scene.pmp_mod_groups) > 0:
            mod_group = mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        
        match self.category:
            case "OUTPUT_PMP":
                prefs.modpack_output_dir = str(export_dir)
                prefs.modpack_output_display_dir = str(Path(*export_dir.parts[-3:]))
            case "GROUP":
                mod_group.folder_path = str(export_dir)
            case "OPTION":
                group_options[self.option].folder_path = str(export_dir)

        return {'FINISHED'}

class ModpackerContainers(Operator):
    bl_idname = "ya.modpacker_ui_containers"
    bl_label = ""
    bl_description = ""

    add     : BoolProperty() # type: ignore
    category: StringProperty() # type: ignore

    group   : IntProperty() # type: ignore
    option  : IntProperty() # type: ignore
    entry   : IntProperty() # type: ignore

    def get_user_input_items(self, context):
        base_items = [
            ("FILE_ENTRY", "File", ""),
            ("SHP_ENTRY", "Shape Key", ""),
            ("ATR_ENTRY", "Attribute", "")
        ]
        
        return base_items
    
    user_input: EnumProperty(
        name="",
        items=get_user_input_items
    ) # type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.add == True:
            if properties.category == "ENTRY":
                return f"""Add {properties.category.capitalize()}:
        *SHIFT click for file.
        *CTRL click for shape key.
        *ALT click for attribute"""
            elif properties.category == "OPTION":
                return f"""Add {properties.category.capitalize()}. 
        *SHIFT click to add a correction entry to a Combining group"""
            else:
                return f"Add {properties.category.capitalize()}"
        elif properties.category.endswith("_ENTRY"):
            return f"Hold CTRL to remove {properties.category[:3]}"
        else:
            return f"Hold CTRL to remove {properties.category.capitalize()}"
        
    def invoke(self, context:Context, event):
        scene = context.scene
        self.mod_groups: list[BlendModGroup] = scene.pmp_mod_groups

        if self.category in ("ENTRY", "COMBI_ENTRY"):
            if event.shift:
                self.category = "FILE_ENTRY"
            if event.ctrl:
                self.category = f"SHP_{self.category.split('_')[0]}"
            elif event.alt:
                self.category = f"ATR_{self.category.split('_')[0]}"
            else:
                context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=2)
                return {'RUNNING_MODAL'}
                
        if self.category == "OPTION":
            mod_group = self.mod_groups[self.group]
            if event.shift and mod_group.group_type == "Combining":
                self.category = "COMBI"

        if not self.add and not event.ctrl:
            return {'FINISHED'}
        return self.execute(context)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "user_input")

    def execute(self, context:Context):
        self.prefs = get_preferences()
        
        if self.category == "ENTRY":
            self.category = self.user_input
        self.group: int
        self.option: int

        scene = context.scene
        self.mod_groups: list[BlendModGroup] = scene.pmp_mod_groups

        if len(scene.pmp_mod_groups) > 0:
            mod_group = self.mod_groups[self.group]
            group_options:list[BlendModOption] = mod_group.mod_options
        

        match self.category:
            case "GROUP":
                if self.add:
                    new_group     = self.mod_groups.add()
                    new_group.idx = "New"
                else:
                    self.remove_mod_group(self.mod_groups, self.group)

            case "OPTION":
                if self.add:
                    new_option = group_options.add()
                    new_option.name = f"Option #{len(group_options)}"
                else:
                    self.remove_regular_option(group_options, self.option)

            case "COMBI":
                if self.add:
                    new_correction = mod_group.corrections.add()
                    new_correction.group_idx = self.group
                else:
                    self.remove_correction(mod_group.corrections, self.option)

            case "FILE_ENTRY":

                option_entries = group_options[self.option].file_entries

                if self.add:
                    option_entries.add()
                else:
                    self.remove_file_entry(option_entries, self.entry)

            case "SHP_ENTRY" | "ATR_ENTRY" | "SHP_COMBI" | "ATR_COMBI":
                if self.category.endswith("ENTRY"):
                    option_entries = group_options[self.option].meta_entries
                else:
                    option_entries = mod_group.corrections[self.option].meta_entries

                if self.add:
                    new_entry = option_entries.add()
                    new_entry.type = self.category[:3]
                    new_entry.manip_ref = "shpx_" if self.category[:3] == "SHP" else "atrx_"
                else:
                    self.remove_meta_entry(option_entries, self.entry)

    
        # self.calculate_final_options(context)

        return {'FINISHED'}
    
    def set_preset(self, context) -> None:
        model_id = self.get_model_id_from_path(context)
        prefix = "shpx_"
        
        slot, options, corrections = self.get_preset(context, self.preset)

        idx = len(self.combining_options)
        for option, key_data in options.items():
            new_option = self.combining_options.add()
            new_option.name = option

            for entries in key_data:
                new_shape = self.combining_options[idx].meta_entries.add()
                new_shape.slot = slot
                new_shape.modelid = model_id
                new_shape.condition = entries["Conditional"]
                new_shape.manip_ref = prefix + entries["Shape"]
            idx +=1
        for correction in corrections:
            add_corrections = self.corrections.add()
            add_corrections.name = "Alt Hips/Soft Butt"
            add_corrections.entry.slot = slot
            add_corrections.entry.modelid = model_id
            add_corrections.entry.condition = correction["Conditional"]
            add_corrections.entry.manip_ref = prefix + correction["Shape"]

            total_options = [option.name for option in self.combining_options]

            idx_list = []
            split = "Alt Hips/Soft Butt".split("/")
            for option in split:
                idx = total_options.index(option)
                idx_list.append(idx)
            for idx in idx_list:
                item = add_corrections.option_idx.add()
                item.value = idx

    def get_preset(self, context, preset):
        slot = "Legs"

        options = {"Alt Hips":  [{"Shape": "yab_hip", "Conditional": "None"},
                                 {"Shape": "rue_hip", "Conditional": "None"}],

                   "Soft Butt": [{"Shape": "softbutt", "Conditional": "None"},
                                 {"Shape": "yabc_waist", "Conditional": "Waist"}]}
        
        corrections = [{"Shape": "yabc_hipsoft", "Conditional": "None"},
                       {"Shape": "ruec_hipsoft", "Conditional": "None"}]
        
        return slot, options, corrections

    def extract_meta_entry(self, entry:ModMetaEntry):
        """Extract ModMetaEntry to tuple"""
        return (
            entry.type,
            entry.manip_ref, 
            entry.slot,
            entry.race_condition,
            entry.connector_condition,
            entry.model_id,
            entry.enable
        )

    def extract_file_entry(self, entry:ModFileEntry):
        """Extract ModFileEntry to tuple"""
        return (
            entry.name,
            entry.file_path,
            entry.game_path
        )

    def extract_mod_option(self, option:BlendModOption):
        """Extract BlendModOption to tuple"""
        meta_entries = [self.extract_meta_entry(entry) for entry in option.meta_entries]
        file_entries = [self.extract_file_entry(entry) for entry in option.file_entries]
        
        return (
            option.name,
            option.description,
            option.priority,

            meta_entries,
            file_entries,

            option.show_option,    
        )

    def extract_correction_enty(self, option:CorrectionEntry):
        """Extract CorrectionEntry to tuple"""
        meta_entries = [self.extract_meta_entry(option) for option in option.meta_entries] 
        file_entries = [self.extract_file_entry(option) for option in option.file_entries] 
        
        return (
            option.group_idx,
            meta_entries,
            file_entries,
            option.names,
            option.show_option
        )
    
    def extract_mod_group(self, group:BlendModGroup):
        """Extract BlendModGroup to tuple"""
        mod_options = [self.extract_mod_option(option) for option in group.mod_options]
        correction_entries = [self.extract_correction_enty(option) for option in group.corrections]
        
        return (
            group.idx,
            group.page,
            group.group_type,
            group.subfolder,
            
            group.name,
            group.description,
            group.game_path,
            group.folder_path,
            group.priority,

            mod_options,
            correction_entries,

            group.show_folder,
            group.show_group,
            group.use_folder,
            group.valid_path,
        )

    def restore_meta_entry(self, data, entry:ModMetaEntry):
        """Restore tuple data to ModMetaEntry"""
        entry.type = data[0]
        entry.manip_ref = data[1]
        safe_set_enum(entry, "slot", data[2], "Body")
        safe_set_enum(entry, "race_condition", data[3], "0")
        safe_set_enum(entry, "connector_condition", data[4], "None")
        entry.modelid = data[5]
        entry.enable = data[6]

    def restore_file_entry(self, data, entry:ModFileEntry):
        """Restore tuple data to ModFileEntry"""
        entry.name = data[0]
        entry.file_path = data[1]
        entry.game_path = data[2]

    def restore_mod_option(self, data, option:BlendModOption):
        """Restore tuple data to BlendModOption"""
        option.name         = data[0]
        option.description  = data[1]
        option.priority     = data[2]
        
        option.meta_entries.clear()
        for meta_data in data[3]:
            new_meta = option.meta_entries.add()
            self.restore_meta_entry(meta_data, new_meta)
          
        option.file_entries.clear()
        for file_data in data[4]:
            new_file = option.file_entries.add()
            self.restore_file_entry(file_data, new_file)

        option.show_option   = data[5]

    def restore_correction_entry(self, data, option:CorrectionEntry):
        """Restore tuple data to CorrectionEntry"""
        option.group_idx = data[0]

        option.meta_entries.clear()
        for meta_data in data[1]:
            new_meta = option.meta_entries.add()
            self.restore_meta_entry(meta_data, new_meta)
        
        option.file_entries.clear()
        for file_data in data[1]:
            new_meta = option.meta_entries.add()
            self.restore_file_entry(file_data, new_meta)
   
        safe_set_enum(option, "names", data[2], "0")
        
        option.show_option = data[3] 
        
    def restore_mod_group(self, data, group:BlendModGroup):
        """Restore tuple data to BlendModGroup"""

        safe_set_enum(group, "idx", data[0], "New")
        safe_set_enum(group, "page", data[1], "0")
        safe_set_enum(group, "group_type", data[2], "Single")
        safe_set_enum(group, "subfolder", data[3], "None")
        
        group.name        = data[4]
        group.description = data[5]
        group.game_path   = data[6]
        group.folder_path = data[7]
        group.priority    = data[8]

        group.mod_options.clear()
        for option_data in data[9]:
            new_option = group.mod_options.add()
            self.restore_mod_option(option_data, new_option)

        group.corrections.clear()
        for correction_data in data[10]:
            new_correction = group.correction_entries.add()
            self.restore_correction_entry(correction_data, new_correction)

        group.show_folder = data[11]
        group.show_group  = data[12]
        group.use_folder  = data[13]
        group.valid_path  = data[14]
        
    def remove_mod_group(self, mod_groups_collection, index_to_remove):
        """Remove a BlendModGroup at specific index"""
        temp_groups = []
        
        for index, group in enumerate(mod_groups_collection):
            if index == index_to_remove:
                continue
            temp_groups.append(self.extract_mod_group(group))
        
        mod_groups_collection.clear()
        for group_data in temp_groups:
            new_group = mod_groups_collection.add()
            self.restore_mod_group(group_data, new_group)

    def remove_correction(self, corrections_collection, index_to_remove):
        """Remove a CorrectionEntr at specific index"""
        temp_options = []
        
        for index, option in enumerate(corrections_collection):
            if index == index_to_remove:
                continue
            temp_options.append(self.extract_correction_enty(option))
        
        corrections_collection.clear()
        for option_data in temp_options:
            new_option = corrections_collection.add()
            self.restore_correction_entry(option_data, new_option)

    def remove_regular_option(self, mod_options_collection, index_to_remove):
        """Remove a BlendModOption at specific index"""
        temp_options = []
        
        for index, option in enumerate(mod_options_collection):
            if index == index_to_remove:
                continue
            temp_options.append(self.extract_mod_option(option))
        
        mod_options_collection.clear()
        for option_data in temp_options:
            new_option = mod_options_collection.add()
            self.restore_mod_option(option_data, new_option)

    def remove_meta_entry(self, meta_entries_collection, index_to_remove):
        """Remove a ModMetaEntry at specific index"""
        temp_entries = []
        
        for index, entry in enumerate(meta_entries_collection):
            if index == index_to_remove:
                continue
            temp_entries.append(self.extract_meta_entry(entry))
        
        meta_entries_collection.clear()
        for entry_data in temp_entries:
            new_entry = meta_entries_collection.add()
            self.restore_meta_entry(entry_data, new_entry)

    def remove_file_entry(self, file_entries_collection, index_to_remove):
        """Remove a ModFileEntry at specific index"""
        temp_entries = []
        
        for index, entry in enumerate(file_entries_collection):
            if index == index_to_remove:
                continue
            temp_entries.append(self.extract_file_entry(entry))
        
        file_entries_collection.clear()
        for entry_data in temp_entries:
            new_entry = file_entries_collection.add()
            self.restore_file_entry(entry_data, new_entry)

class GamepathCategory(Operator):
    bl_idname = "ya.gamepath_category"
    bl_label = "Modpacker"
    bl_description = "Changes gamepath category"

    body_slot: StringProperty() # type: ignore
    category : StringProperty() # type: ignore
    group : IntProperty() # type: ignore
    option: IntProperty() # type: ignore
    entry : IntProperty() # type: ignore


    def execute(self, context):
        self.group: int
        self.option: int
        self.entry: int

        scene = context.scene
        self.props = get_file_properties()

        mod_groups: list[BlendModGroup] = scene.pmp_mod_groups
        mod_group = mod_groups[self.group]
        group_options:list[BlendModOption] = mod_group.mod_options
        
        if self.category == "GROUP":
            game_path: str = mod_groups[self.group].game_path
        else:
            game_path: str = group_options[self.option].file_entries[self.entry].game_path
        
        game_path_split     = game_path.split("_")
        category_split      = game_path_split[-1].split(".")
        category_split[0]   = self.body_slot
        game_path_split[-1]  = ".".join(category_split)

        game_path = "_".join(game_path_split)

        if self.category == "GROUP":
            setattr(mod_groups[self.group], "game_path", "_".join(game_path_split))
        else:
            setattr(group_options[self.option].file_entries[self.entry], "game_path", "_".join(game_path_split))
        bpy.context.view_layer.update()
        return {'FINISHED'}
    
class BodyPartSlot(Operator):
    bl_idname = "ya.set_body_part"
    bl_label = "Select body slot to export."
    bl_description = "The icons almost make sense"

    body_part: StringProperty() # type: ignore

    def execute(self, context):
        get_file_properties().export_body_slot = self.body_part
        return {'FINISHED'}
    
class PanelCategory(Operator):
    bl_idname = "ya.set_ui"
    bl_label = "Select the menu."
    bl_description = "Changes the panel menu"

    menu: StringProperty() # type: ignore

    def execute(self, context):
        get_file_properties().file_man_ui = self.menu
        return {'FINISHED'}

class OutfitCategory(Operator):
    bl_idname = "ya.outfit_category"
    bl_label = "Select menus."
    bl_description = """Changes the panel menu.
    *Click to select single category.
    *Shift+Click to pin/unpin categories"""

    menu: StringProperty() # type: ignore
    panel: StringProperty() # type: ignore

    def invoke(self, context, event):
        props = get_outfit_properties()
        categories = ["overview", "shapes", "mesh", "weights", "armature"]
        if event.shift:
            state = getattr(props, f"{self.menu.lower()}_category")
            if state:
                setattr(props, f"{self.menu.lower()}_category", False)
            else:
                setattr(props, f"{self.menu.lower()}_category", True)
        else:
            for category in categories:
                if self.menu.lower() == category:
                    setattr(props, f"{category.lower()}_category", True)
                else:
                    setattr(props, f"{category.lower()}_category", False)

        return {'FINISHED'}

CLASSES = [
    FrameJump,
    KeyframeJump,
    ModpackerContainers,
    GamepathCategory,
    DirSelector,
    ModpackFileSelector,
    ModpackDirSelector,
    CopyToModpacker,
    BodyPartSlot,
    PanelCategory,
    OutfitCategory,
]