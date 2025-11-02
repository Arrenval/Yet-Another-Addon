import os
import bpy
import zipfile

from pathlib           import Path
from bpy.types         import Operator, PropertyGroup, Context
from bpy.props         import StringProperty, IntProperty, EnumProperty, CollectionProperty
from collections       import defaultdict

from ..props           import get_window_props, get_file_props
from ..xiv.io.model    import ModelImport
from ..preferences     import get_prefs
from ..utils.typings   import BlendEnum
from ..props.modpack   import BlendModOption, BlendModGroup, ModFileEntry
from ..xiv.formats.pmp import Modpack


class PMPOption(PropertyGroup):
    name: StringProperty() # type: ignore

class PMPGroup(PropertyGroup):
    group_name: StringProperty() # type: ignore
    group_desc: StringProperty() # type: ignore
    files: CollectionProperty(type=PMPOption) # type: ignore

class PMPSelector(Operator):
    bl_idname = "ya.pmp_selector"
    bl_label = "Select Modpack"
    bl_description = """Options:
    *SHIFT click to open modpack.
    *CTRL click to unload modpack selected. 
    *ALT click to open the folder"""
    
    filepath: StringProperty() # type: ignore

    category: StringProperty(options={'HIDDEN'}) # type: ignore
    
    filter_glob: StringProperty(
        default='*.pmp',
        options={'HIDDEN'}) # type: ignore
    
    @classmethod
    def poll(cls, context:Context):
        props = get_window_props()
        return props.file.modpack.modpack_replace
    
    def invoke(self, context:Context, event):
        self.props  = get_window_props()
        actual_file = Path(self.props.file.modpack.modpack_dir) 

        if event.alt and event.type == "LEFTMOUSE" and actual_file.is_file():
            actual_dir = actual_file.parent
            os.startfile(str(actual_dir))

        elif event.shift and event.type == "LEFTMOUSE" and actual_file.is_file():
            os.startfile(str(actual_file))

        elif event.ctrl and event.type == "LEFTMOUSE" and actual_file.is_file():
            get_file_props().loaded_pmp_groups.clear()
            self.props.file.modpack.property_unset("modpack_dir") 

        else :
            context.window_manager.fileselect_add(self)
    
        return {"RUNNING_MODAL"}
    
    def execute(self, context:Context):
        selected_file = Path(self.filepath)

        if selected_file.exists() and selected_file.suffix == ".pmp":
            self.props.file.modpack.modpack_dir = str(selected_file) 
            self.props.file.modpack.modpack_display_dir = selected_file.stem
            self.report({'INFO'}, f"{selected_file.stem} selected!")
        else:
            self.report({'ERROR'}, "Not a valid modpack!")
        
        return {'FINISHED'}

class FileSelector(Operator):
    bl_idname      = "ya.file_selector"
    bl_label       = "Select File"
    bl_description = "Select file"
    bl_options     = {'UNDO'}

    filepath: StringProperty(options={'HIDDEN'}) # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context: Context, event):
        if self.category.startswith("INSP"):
            self.filter_glob = "*.phyb;*.mdl"

        if self.category == 'MDL':
            self.filter_glob = "*.pmp;*.mdl"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        file = Path(self.filepath)

        if not file.is_file():
            self.report({"ERROR"}, "Not a valid file!")
            return {'FINISHED'}
        
        if self.category == 'MDL':
            if file.suffix == '.mdl':
                ModelImport.from_file(self.filepath, file.stem)
                self.report({"INFO"}, "Model Imported!")
            elif file.suffix == '.pmp':
                bpy.ops.ya.select_from_pmp('INVOKE_DEFAULT', filepath=self.filepath)
        else:
            setattr(get_window_props(), self.attr_from_category(), self.filepath)
            self.report({"INFO"}, "File selected!")
        
        return {'FINISHED'}

    def attr_from_category(self) -> str:
        if self.category == "INSP1":
            return "insp_file1"
        elif self.category == "INSP2":
            return "insp_file2"

class SelectFromPMP(Operator):
    bl_idname      = "ya.select_from_pmp"
    bl_label       = "Select File"
    bl_description = "Select file"
    bl_options     = {'UNDO'}

    filepath: StringProperty(options={'HIDDEN'}) # type: ignore
    pmp_groups: CollectionProperty(type=PMPGroup) # type: ignore
    
    def invoke(self, context: Context, event):
        pmp = Modpack.from_archive(Path(self.filepath))
        self.mdl_files: dict[str, dict[str, set[str]]] = defaultdict(dict)
        self.parse_modpack(pmp)
        
        return context.window_manager.invoke_props_dialog(self, confirm_text="Import")
    
    def parse_modpack(self, pmp: Modpack):
        pmp_groups: list[PMPGroup] = self.pmp_groups

        added_groups = 0
        for group in pmp.groups:
            options = group.Containers if group.Containers else group.Options or []

            mdl_files: dict[str, set[str]] = defaultdict(set)
            for option in options:
                files = [(key, relative_path) for key, relative_path in (option.Files or {}).items()]
                
                for (key, relative_path) in files:
                    file = Path(relative_path)
                    if file.suffix != ".mdl":
                        continue

                    mdl_files[option.Name].add(relative_path)

            if mdl_files:
                new_group            = pmp_groups.add()
                new_group.group_name = group.Name
                new_group.group_desc = group.Description

                for option, paths in mdl_files.items():
                    new_file          = new_group.files.add()
                    new_file.name     = option

                    self.mdl_files[(added_groups)][option] = set()
                    for path in paths:
                        self.mdl_files[(added_groups)][option].add(path)
                        
                added_groups += 1

    def get_groups_items(self, context) -> BlendEnum:
        pmp_groups: list[PMPGroup] = self.pmp_groups

        items = []
        for idx, group in enumerate(pmp_groups):
            items.append((str(idx), group.group_name, group.group_desc))

        return items
        
    def get_files_items(self, context: Context) -> BlendEnum:
        pmp_groups: list[PMPGroup] = self.pmp_groups
        options: list[PMPOption]   = pmp_groups[int(self.group)].files
        
        items = []
        for option in options:
            items.append((option.name, option.name, ""))
        
        return items

    group: EnumProperty(
                name="",
                description="Select a group",
                items=get_groups_items,
                # update=lambda self, context: self.on_group_changed(context)
            ) # type: ignore
    
    option: EnumProperty(
                name="",
                description="Select a file",
                items=get_files_items,
            ) # type: ignore
    
    def draw(self, context) -> None:
        layout = self.layout

        if len(self.pmp_groups) == 0:
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(icon='INFO', text=f"Modpack contains no models.")
            return

        split  = layout.split(factor=0.5, align=True)

        col_group = split.column(align=True)
        col_group.label(text="Group:")
        col_group.column(align=True).prop(self, "group", text="")

        col_files = split.column(align=True)
        col_files.label(text="Option:")
        col_files.column(align=True).prop(self, "option", text="")

        files = len(self.mdl_files[int(self.group)][self.option])
        if files > 1:
            row = layout.row(align=True)
            row.alignment = 'CENTER'
            row.label(icon='INFO', text=f"This option contains {files} models.")

    def execute(self, context):
        if len(self.pmp_groups) == 0:
            return {'FINISHED'}
        
        rel_paths = self.mdl_files[int(self.group)][self.option]

        with zipfile.ZipFile(self.filepath, 'r') as zip_file:
            archive_files = zip_file.namelist()
            archive_lower = {file.lower(): file for file in archive_files}

            for rel_path in rel_paths:
                normalised_path = rel_path.replace('\\', '/').lower()
                
                if normalised_path in archive_lower:
                    actual_path = archive_lower[normalised_path]
                    data = zip_file.read(actual_path)
                    ModelImport.from_bytes(data, self.option)
        
        self.report({"INFO"}, "Model Imported!")
        return {'FINISHED'}
    
class DirSelector(Operator):
    bl_idname = "ya.dir_selector"
    bl_label = "Select Folder"
    bl_description = "Select directory. Hold Alt to open the folder"
    
    directory: StringProperty() # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype="DIR_PATH",
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context: Context, event):
        self.props = get_prefs()
        actual_dir = getattr(self.props, f"{self.category}_dir", "")     

        if event.alt and event.type == "LEFTMOUSE" and os.path.isdir(actual_dir):
            os.startfile(actual_dir)
        elif event.type == "LEFTMOUSE":
            context.window_manager.fileselect_add(self)
        else:
             self.report({"ERROR"}, "Not a directory!")
    
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if self.category == "export":
            actual_dir_prop = "output_dir"
            display_dir_prop = "display_dir"
            self.props = get_prefs().export
        else:
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

    group : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    option: IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    entry : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    
    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context: Context, event):
        self.group:int
        self.option:int
        self.container:BlendModGroup | BlendModOption | ModFileEntry
        props = get_window_props()

        mod_group: BlendModGroup = props.file.modpack.pmp_mod_groups[self.group]

        if self.category == "PHYB":
            return self.manage_phybs(context, event, mod_group, self.option)
        
        if self.category.endswith("COMBI"):
            group_options = mod_group.corrections
        else:
            group_options = mod_group.mod_options

        
        self.container = group_options[self.option].file_entries[self.entry]

        self.filter_glob = "*.mdl;*.phyb;*.tex"

        if event.ctrl and event.type == "LEFTMOUSE":
            self._remove_entry()
            return {"FINISHED"}

        else:
            context.window_manager.fileselect_add(self,)

        return {"RUNNING_MODAL"}
    
    def manage_phybs(self, context: Context, event, mod_group: BlendModGroup, option: int) -> set[str]:
        self.container   = mod_group.base_phybs[option]
        self.filter_glob = "*.phyb"

        if event.ctrl and event.type == "LEFTMOUSE":
            self._remove_entry()
            return {"FINISHED"}
        else:
            context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
    
    def _remove_entry(self):
        bpy.ops.ya.modpack_manager(
                'EXEC_DEFAULT',
                delete=True,
                category=self.category,
                group=self.group,
                option=self.option,
                entry=self.entry
            )

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
    bl_description = ""

    @classmethod
    def description(cls, context, properties):
        if properties.category == "PHYB":
            return "Get base phybs from folder"
        else:
            return """Options:
    *SHIFT click to copy directory from file export.
    *CTRL click to remove folder. 
    *ALT click to open the folder"""
        
    directory: StringProperty(subtype="DIR_PATH") # type: ignore

    category: StringProperty(options={'HIDDEN', "SKIP_SAVE"}) # type: ignore
    group   : IntProperty(default=0, options={'HIDDEN', "SKIP_SAVE"}) # type: ignore

    filter_glob: bpy.props.StringProperty(
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context: Context, event):
        self.group:int
        self.option:int
        self.container: BlendModGroup | BlendModOption | ModFileEntry

        self.prefs = get_prefs()
        self.props = get_window_props()
        
        match self.category:
            case "GROUP" | "SIM":
                self.container = self.props.file.modpack.pmp_mod_groups[self.group]
                self.folder    = self.container.folder_path
                attribute      = "folder_path"

            case "OUTPUT_PMP":
                self.folder    = self.prefs.modpack_output_dir
                attribute      = "modpack_output_dir"
            case "PHYB":
                context.window_manager.fileselect_add(self)
                return {"RUNNING_MODAL"}
                
        if self.folder.strip() == "":
            context.window_manager.fileselect_add(self)
            return {"RUNNING_MODAL"}
        else:
            self.folder = Path(self.folder)
            
        if event.ctrl and event.type == "LEFTMOUSE" and self.folder.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.property_unset("modpack_output_display_dir")
            else:
                self.container.property_unset(attribute)
                self.container.subfolder = "None"
            return {'FINISHED'}
        
        elif event.alt and event.type == "LEFTMOUSE" and self.folder.is_dir():
            os.startfile(self.folder)
        elif event.shift and event.type == "LEFTMOUSE":
            bpy.ops.ya.directory_copy(
                "EXEC_DEFAULT", 
                category=self.category,
                group=self.group,)
        else:
            context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_dir = Path(self.directory)  

        if selected_dir.is_dir():
            if self.category == "OUTPUT_PMP":
                self.prefs.modpack_output_display_dir = str(Path(*selected_dir.parts[-3:]))
                self.prefs.modpack_output_dir = str(selected_dir)
            elif self.category == "PHYB":
                self.phybs_from_folder(selected_dir)
            else:
                self.container.folder_path = str(selected_dir)
            self.report({"INFO"}, f"Directory selected: {selected_dir}")
        else:
            self.report({"ERROR"}, "Not a valid directory!")
        
        return {'FINISHED'}
    
    def phybs_from_folder(self, folder: Path) -> None:
        group = get_window_props().file.modpack.pmp_mod_groups[self.group]
        files = [file for file in folder.glob("*") if file.is_file() and file.suffix in ".phyb"]
        
        group.base_phybs.clear()
        for file in files:
            new_phyb = group.base_phybs.add()
            new_phyb.file_path = str(file)


CLASSES = [
    PMPOption,
    PMPGroup,
    PMPSelector,
    FileSelector,
    SelectFromPMP,
    DirSelector,
    ModpackFileSelector,
    ModpackDirSelector,
]
