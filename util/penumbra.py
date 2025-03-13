import json

from typing      import List, Dict
from dataclasses import dataclass, asdict, field, fields

@dataclass
class TypeManip:
    Entry               :int | float | dict | None = None
    #EQDP, EQP, Est
    Gender              :str | None = None
    Race                :str | None = None
    SetID               :str | None = None
    Slot                :str | None = None
    #Rsp
    SubRace             :str | None = None
    Attribute           :str | None = None
    #GlobalEqp| None 
    Type                :str | None = None
    Condition           :str | None = None
    #Imc| None 
    ObjectType          :str | None = None
    PrimaryId           :int | None = None
    SecondaryId         :int | None = None
    Variant             :int | None = None
    EquipSlot           :str | None = None
    BodySlot            :str | None = None
    #ImcDefault| None 
    MaterialId          :int | None = None
    DecalId             :int | None = None
    VfxId               :int | None = None
    MaterialAnimationId :int | None = None
    AttributeAndSound   :int | None = None
    AttributeMask       :int | None = None
    SoundId             :int | None = None

    @classmethod
    def from_dict(cls, data:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)
    
@dataclass
class ModManipulations:
    Type         :str = ""
    Manipulation :list[TypeManip] = None
    
    @classmethod
    def from_dict(cls, data:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)
    
    def __post_init__(self):
        self.Manipulation = TypeManip(self.Manipulation)

@dataclass
class CombinedContainers:
    Name            :str | None            = None
    Files           :Dict[str, str] | None = None
    FileSwaps       :Dict[str, str] | None = None
    Manipulations   :list[ModManipulations] | None = None

    @classmethod
    def from_dict(cls, data:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)
    
    def __post_init__(self):
        if self.Manipulations != None:
            self.Manipulations = [ModManipulations.from_dict(manip) for manip in self.Manipulations]

@dataclass
class GroupOptions:
    Files           :Dict[str, str] | None = None
    FileSwaps       :Dict[str, str] | None = None
    Manipulations   :List[ModManipulations] | None = None
    Priority        :int = 0
    AttributeMask   :int | None = None
    Name            :str = ""
    Description     :str = ""
    Image           :str = ""

    @classmethod
    def from_dict(cls, data:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)

    def __post_init__(self):
        if self.Manipulations != None:
            self.Manipulations = [ModManipulations.from_dict(manip) for manip in self.Manipulations]
                 
@dataclass
class ModGroups:    
    Version         :int       | None                = None
    DefaultEntry    :TypeManip | None                = None
    Identifier      :TypeManip | None                = None
    AllVariants     :bool      | None                = None
    OnlyAttributes  :bool      | None                = None
    Name            :str                             = ""
    Description     :str                             = ""
    Priority        :int                             = 0
    Image           :str                             = ""
    Page            :int                             = 0
    Type            :str       | None                = None
    DefaultSettings :int                             = 0
    Options         :List[GroupOptions]       | None = None
    Manipulations   :List[ModManipulations]   | None = None
    Containers      :List[CombinedContainers] | None = None

    @classmethod
    def from_dict(cls, data:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)

    def __post_init__(self):
        if self.Options != None:
            self.Options         = [GroupOptions.from_dict(option) for option in self.Options]
            if self.Containers  != None:
                self.Containers  = [CombinedContainers.from_dict(container) for container in self.Containers]
        elif self.Manipulations != None:
            self.Manipulations   = [ModManipulations(**manip) for manip in self.Manipulations]
            self.Identifier      = TypeManip(self.Identifier)
            self.DefaultEntry    = TypeManip(self.DefaultEntry)

    def to_json(self):
        return json.dumps(self.remove_none(asdict(self)), indent=4)
    
    def remove_none(self, obj):
        if isinstance(obj, dict):
            return {key: self.remove_none(value) for key, value in obj.items() if value is not None}
        
        elif isinstance(obj, list):
            return [self.remove_none(index) for index in obj if index is not None]
        
        return obj         

@dataclass
class ModMeta:
    FileVersion :int  = 3
    Name        :str  = ""
    Author      :str  = ""
    Description :str  = ""
    Image       :str  = ""
    Version     :str  = ""
    Website     :str  = ""
    ModTags     :list = field(default_factory=list)
    DefaultPreferredItems:list | None = None

    @classmethod
    def from_dict(cls, data:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_data = {key: value for key, value in data.items() if key in field_names}
        
        return cls(**filtered_data)

    def to_json(self):
        return json.dumps(asdict(self), indent=4)
    

