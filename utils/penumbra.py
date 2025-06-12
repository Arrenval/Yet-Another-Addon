# Based around Penumbra's schemas: https://github.com/xivdev/Penumbra/tree/master/schemas.

import os
import json
import shutil
import hashlib
import logging

from typing      import List, Dict
from zipfile     import ZipFile, ZIP_DEFLATED
from pathlib     import Path
from collections import defaultdict
from dataclasses import dataclass, asdict, field, fields


def sanitise_path(path:str) -> str:
        """Removes invalid characters from Windows paths. Used mostly for modpack paths."""
        invalid = '<>:"/\|?*'

        for char in invalid:
            path = path.replace(char, '_')
        
        if path[-1] == " ":
            path = path[0:-1]
            
        return path

class PMPJson:

    @classmethod
    def from_dict(cls, input:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_input = {}

        for key, value in input.items():
            if key in field_names:
                filtered_input[key] = value
            else:
                print(f"Unknown field: {key} in {cls.__name__}")
        
        return cls(**filtered_input)

    def update_from_dict(self, input: dict):
        field_names = {field.name for field in fields(self)}
        
        for key, value in input.items():
            if key in field_names:
                setattr(self, key, value)
            else:
                print(f"Unknown field: {key} in {self.__class__.__name__}")

    def remove_none(self, obj):
        if isinstance(obj, dict):
            return {key: self.remove_none(value) for key, value in obj.items() if value is not None}
        
        elif isinstance(obj, list):
            return [self.remove_none(index) for index in obj if index is not None]
        
        return obj

    def to_json(self):
        return json.dumps(self.remove_none(asdict(self)), indent=4)
    
    def write_json(self, output_dir:Path, file_name):
        with open(os.path.join(output_dir, file_name + ".json"), "w") as file:
                file.write(self.to_json())

@dataclass
class ManipulationEntry(PMPJson):
    '''Contains fields for all penumbra manipulations, several are shared between types.
    See https://github.com/xivdev/Penumbra/tree/master/schemas for schemas.'''
    Entry                  : int | float | dict | bool | None = None
        
    #Shared    
    Gender                 : str |       None = None
    Race                   : str |       None = None
    SetId                  : str |       None = None
    Slot                   : str |       None = None
    Id                     : int |       None = None
    Attribute              : str |       None = None
    Type                   : str |       None = None
    Index                  : int |       None = None
             
    #Atr          
    GenderRaceCondition    : int |       None = None
         
    #Enums (Used by several manipulations)         
    EquipSlot              : str |       None = None
    HumanSlot              : str |       None = None
    ModelRace              : str |       None = None
    ObjectType             : str |       None = None
    BodySlot               : str |       None = None
    SubRace                : str |       None = None
    ShapeConnectorCondition: str |       None = None
    U8                     : str | int | None = None
    U16                    : str | int | None = None
     
    #GlobalEqp     
    Condition              : str | None = None
     
    # ImcIdentifier        
    PrimaryId              : int | None = None
    SecondaryId            : int | None = None
    Variant                : int | None = None
     
     
    # ImcEntry                
    MaterialId             : int | None = None
    DecalId                : int | None = None
    VfxId                  : int | None = None
    MaterialAnimationId    : int | None = None
    AttributeMask          : int | None = None
    SoundId                : int | None = None
 
    #Shp    
    Shape                  : str | None = None
    ConnectorCondition     : str | None = None
   
@dataclass
class ManipulationType(PMPJson):
    Type        : str = ""
    Manipulation: ManipulationEntry = None
    
    def __post_init__(self):
        if self.Manipulation is not None:
            self.Manipulation = ManipulationEntry.from_dict(self.Manipulation)

@dataclass
class GroupContainer(PMPJson):
    '''Contains all entries for combining options.'''
    Files          : Dict[str, str]         | None = field(default_factory=dict)
    FileSwaps      : Dict[str, str]         | None = None 
    Manipulations  : List[ManipulationType] | None = field(default_factory=list)

    def __post_init__(self):
        if self.Manipulations is not None:
            self.Manipulations = [ManipulationType.from_dict(manip) for manip in self.Manipulations]

@dataclass
class GroupOption(PMPJson):
    '''Contains all entries for Penumbra single, multi, combining and imc options.'''
    Name           : str        = ""    
    Description    : str | None = None
    Priority       : int | None = None
    Image          : str | None = None
  
    Files          : Dict[str, str]         | None = None
    FileSwaps      : Dict[str, str]         | None = None
    Manipulations  : List[ManipulationType] | None = None
    AttributeMask  : int                    | None = None
    IsDisableSubMod: bool                   | None = None
   
    def __post_init__(self):
        if self.Manipulations is not None:
            self.Manipulations = [ManipulationType.from_dict(manip) for manip in self.Manipulations]
           
@dataclass
class ModGroup(PMPJson):
    '''Contains all entries for Penumbra single, multi, combining and imc groups.'''

    Version        : int                           = 0
    Name           : str                           = ""
    Description    : str                           = ""
    Image          : str                           = ""
    Page           : int                           = 0
    Priority       : int                           = 0
    Type           : str                    | None = None
    DefaultSettings: int                           = 0

    Options        : List[GroupOption]      | None = None
    Manipulations  : List[ManipulationType] | None = None
    Containers     : List[GroupContainer]   | None = None

    AllVariants    : bool                   | None = None
    OnlyAttributes : bool                   | None = None
    Identifier     : ManipulationEntry      | None = None
    DefaultEntry   : ManipulationEntry      | None = None
    
    def __post_init__(self):
        if self.Options is not None:
            self.Options         = [GroupOption.from_dict(option) for option in self.Options]

            if self.Containers  is not None:
                self.Containers  = [GroupContainer.from_dict(container) for container in self.Containers]

        elif self.Manipulations is not None:
            self.Manipulations   = [ManipulationType.from_dict(manip) for manip in self.Manipulations]
            self.Identifier      = ManipulationEntry.from_dict(self.Identifier)
            self.DefaultEntry    = ManipulationEntry.from_dict(self.DefaultEntry)     

@dataclass
class DefaultMod(PMPJson):
    Version      :int  = 0
    Files        :Dict[str, str] = field(default_factory=dict)
    FileSwaps    :Dict[str, str] = field(default_factory=dict)
    Manipulations:List[ManipulationType] = field(default_factory=dict)

    def __post_init__(self):
        if self.Manipulations is not None:
            self.Manipulations = [ManipulationType.from_dict(manip) for manip in self.Manipulations]

@dataclass
class ModMeta(PMPJson):
    FileVersion: int  = 3
    Name       : str  = "YetAnotherMod"
    Author     : str  = ""
    Description: str  = ""
    Image      : str  = ""
    Version    : str  = ""
    Website    : str  = ""
    ModTags    : list[str] = field(default_factory=list)

    DefaultPreferredItems: list[int] | None = None
    RequiredFeatures     : list[str] | None = None

@dataclass
class Modpack:

    meta   : ModMeta        = field(default_factory=ModMeta)
    groups : List[ModGroup] = field(default_factory=list)
    default: DefaultMod     = field(default_factory=DefaultMod)

    def __post_init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @classmethod
    def from_archive(cls, archive:Path):
        '''Takes a .pmp and reads its JSON data.'''
        modpack = cls()
        with ZipFile(archive, "r") as pmp:
            try:
                with pmp.open("meta.json", "r") as file:
                    modpack.meta = ModMeta.from_dict(json.load(file))
            except:
                raise FileNotFoundError("Modpack lacks a meta.json!")
            
            try:
                with pmp.open("default_mod.json", "r") as file:
                    modpack.default = DefaultMod.from_dict(json.load(file))
            except:
                pass

            for file_name in pmp.namelist():
                if file_name.count('/') == 0 and file_name.startswith("group") and file_name.endswith(".json"):
                    with pmp.open(file_name, "r") as file:
                        modpack.groups.append(ModGroup.from_dict(json.load(file)))
        
        return modpack

    @classmethod           
    def from_folder(cls, folder:Path):
        '''Takes a penumbra mod folder and reads its JSON data.'''
        modpack = cls()
        folder_content = [file for file in folder.glob(f'*.json') if file.is_file()]
        is_meta_json   = any("meta.json" in file.name for file in folder_content)

        if not is_meta_json:
            raise FileNotFoundError("Modpack lacks a meta.json!")
        
        for file_path in folder_content:
            if file_path.stem == "meta":
                with file_path.open("r") as file:
                    modpack.meta = ModMeta.from_dict(json.load(file))

            elif file_path.stem == "default_mod":
                with file_path.open("r") as file:
                    modpack.default = DefaultMod.from_dict(json.load(file))

            elif file_path.stem.startswith("group_"):
                with file_path.open("r") as file:
                    modpack.groups.append(ModGroup.from_dict(json.load(file)))
        
        return modpack
    
    @staticmethod
    def extract_archive(archive:Path, output_folder:Path):
        with ZipFile(archive, "r") as pmp:
                pmp.extractall(output_folder)

    @staticmethod
    def delete_orphaned_files(folder:Path) -> set[Path]:
        modpack = Modpack.from_folder(folder)

        file_references = set()
        orphans         = set()

        for group in modpack.groups:
            options = group.Containers if group.Containers else group.Options or []
            for option in options:
                for relpath in (option.Files or {}).values():
                    file_references.add(folder / Path(relpath))
                        
        for relpath in (modpack.default.Files or {}).values():
            file_path = folder / Path(relpath)
            file_references.add(file_path)

        for subfolder in folder.iterdir():
            if not subfolder.is_dir():
                continue
            for file_path in subfolder.rglob("*"):
                if file_path.is_file() and file_path not in file_references:
                    orphans.add(file_path)
                    file_path.unlink(missing_ok=True)
                    modpack.logger.info(f"Deleting file with missing reference: {file_path.name}")

        return orphans
    
    @staticmethod
    def deduplicate_folder(folder:Path) -> set[Path]:

        def hash_file(file_path: Path) -> str:
            hash_sha256 = hashlib.sha256()
            with file_path.open('rb') as file:
                for chunk in iter(lambda: file.read(65536), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        
        modpack                     = Modpack.from_folder(folder)
        size_groups:dict[int, list] = defaultdict(list)
        processed_paths             = set()
        suffix                      = [".mdl"]

        files = [
            (key, relative_path) 
            for key, relative_path in (modpack.default.Files or {}).items() 
            if relative_path not in processed_paths
            ]
        
        for key, relative_path in files:
            file = folder / Path(relative_path)
            if file.suffix not in suffix:
                continue

            file_size = file.stat().st_size
            size_groups[file_size].append(
                        {
                        "path":        file,
                        "relpath":     relative_path,
                        "default":     True,
                        "group":       0,
                        "option":      0,
                        "option_type": "",
                        "entry":       key
                    }
                    )
            
            processed_paths.add(relative_path)
            
        for group_idx, group in enumerate(modpack.groups):
            options = group.Containers if group.Containers else group.Options or []
            for option_idx, option in enumerate(options):
                if isinstance(option, GroupOption):
                    option_type = True
                else:
                    option_type = False

                files = [
                    (key, relative_path) 
                    for key, relative_path in (option.Files or {}).items() 
                    if relative_path not in processed_paths
                    ]
                
                for (key, relative_path) in files:
                    file = folder / Path(relative_path)
                    if file.suffix not in suffix:
                        continue

                    file_size = file.stat().st_size
                    size_groups[file_size].append(
                        {
                        "path":        file,
                        "relpath":     relative_path,
                        "default":     False,
                        "group":       group_idx,
                        "option":      option_idx,
                        "option_type": option_type,
                        "entry":       key
                    }
                    )

                    processed_paths.add(relative_path)
        
        duplicates: dict[int, list] = {}
        for size, files in size_groups.items():
            if len(files) <= 1:
                continue
            hash_groups = defaultdict(list)
            for file_info in files:
                file_hash = hash_file(file_info["path"])
                hash_groups[file_hash].append(file_info)
            
            for file_hash, duplicate_files in hash_groups.items():
                if len(duplicate_files) > 1:
                    duplicates[file_hash] = duplicate_files

        removed = set()
        rewrite_json = set()
        for file_hash, files in duplicates.items():
            relative_path: str = files[0]["relpath"]
            main_group   : int = files[0]["group"]

            for file_info in files[1:]:
                file      :Path = file_info["path"]
                group_idx :int  = file_info["group"]
                option_idx:int  = file_info["option"]
                entry_key :str  = file_info["entry"]
                
                Path.unlink(file, missing_ok=True)
                removed.add(file)
                
                if file_info["default"]:
                    modpack.default.Files[entry_key] = file_info["relpath"]
                    log_string = f"Duplicate file, {file.name}, in Default Mod linked to file in {modpack.groups[main_group].Name}."
                    rewrite_json.add("default")

                else:
                    option = modpack.groups[group_idx].Options[option_idx] if file_info["option_type"] else modpack.groups[group_idx].Containers[option_idx]
                    
                    option.Files[entry_key] = relative_path
                    log_string = f"Duplicate file, {file.name}, in {modpack.groups[group_idx].Name} linked to file in {modpack.groups[main_group].Name}."
                    rewrite_json.add(group_idx)
                
                modpack.logger.info(log_string)
            
            for json in rewrite_json:
                if json == "default":
                    modpack.default.write_json(folder, "default_mod")

                else:
                    old_json = [file for file in folder.glob(f"group_{json + 1:03d}*") if file.is_file()][0]
                    Path.unlink(old_json, missing_ok=True)

                    file_name = f"group_{json + 1:03d}_{sanitise_path(group.Name).lower()}"
                    group.write_json(folder, file_name)

        return removed

    def write_mod_jsons(self, folder:Path):
        """Removes existing jsons and writes new ones."""
        file_stem = ["meta", "default_mod"]
        folder_content = [file for file in folder.glob(f'*.json') if file.is_file()]

        for file_path in folder_content:
            if file_path.stem in file_stem:
                Path.unlink(file_path)

            elif file_path.stem.startswith("group_"):
                Path.unlink(file_path)
                
        self.default.write_json(folder, "default_mod")
        self.meta.write_json(folder, "meta")

        for idx, group in enumerate(self.groups):
            file_name = f"group_{idx + 1:03d}_{sanitise_path(group.Name).lower()}"
            group.write_json(folder, file_name)

    def to_archive(self, source_folder:Path, output_folder:Path, pmp_name:str):
        with ZipFile(output_folder / f"{pmp_name}.pmp", 'w', ZIP_DEFLATED) as pmp:
            for root, dir, files in os.walk(source_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    pmp.write(file_path, os.path.relpath(file_path, source_folder))
    
    def to_folder(self, folder:Path, new_files:dict[Path, str]={}) -> set[Path]:
        '''Writes the current modpack instance to a folder. It also calls write_mod_jsons.
        It takes a file list with the files you want to package and which ingame file it is supposed to replace.
        Returns two sets of removed files.'''

        Path.mkdir(folder, exist_ok=True)

        self.write_mod_jsons(folder)

        for file, relative_path in new_files.items():
            target_path = folder / Path(relative_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
        
            shutil.copy(file, target_path)

        orphans = Modpack.delete_orphaned_files(folder)

        duplicates = Modpack.deduplicate_folder(folder)

        return orphans, duplicates
    
    def update_group_page(self, page:int, update_group:ModGroup, new_group:bool=False):
        if not new_group:
            current_idx  = self.groups.index(update_group)
            update_group = self.groups.pop(current_idx)

        insertion_index = len(self.groups)
        for idx, group in enumerate(self.groups):
            if group.Page > page:
                insertion_index = idx
                break

        update_group.Page = page
        self.groups.insert(insertion_index, update_group)

    def update_group_idx(self, index:int, update_group:ModGroup, new_group:bool=False):
        page = self.groups[index - 1].Page if len(self.groups) > 1 else 0
        
        if not new_group:
            current_idx  = self.groups.index(update_group)
            update_group = self.groups.pop(current_idx)

        update_group.Page = page
        self.groups.insert(index, update_group)

    
    
    
     

    