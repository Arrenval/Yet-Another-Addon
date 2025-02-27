import json

from typing      import List, Dict
from dataclasses import dataclass, asdict, field

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

@dataclass
class ModManipulations:
    Type         :str = ""
    Manipulation :List[TypeManip] = None
    
    def __post_init__(self):
        self.Manipulation = TypeManip(self.Manipulation)

@dataclass
class CombinedContainers:
    Name            :str | None            = None
    Files           :Dict[str, str] | None = None
    FileSwaps       :Dict[str, str] | None = None
    Manipulations   :List[ModManipulations] | None = None

    def __post_init__(self):
        if self.Manipulations != None:
            self.Manipulations = [ModManipulations(**manip) for manip in self.Manipulations]

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

    def __post_init__(self):
        if self.Manipulations != None:
            self.Manipulations = [ModManipulations(**manip) for manip in self.Manipulations]
                 
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


    def __post_init__(self):
        if self.Options != None:
            self.Options         = [GroupOptions(**option) for option in self.Options]
            if self.Containers  != None:
                self.Containers  = [CombinedContainers(**container) for container in self.Containers]
        elif self.Manipulations != None:
            self.Manipulations   = [ModManipulations(**manip) for manip in self.Manipulations]
            self.Identifier      = TypeManip(self.Identifier)
            self.DefaultEntry    = TypeManip(self.DefaultEntry)

    def to_json(self):
        return json.dumps(self.remove_none(asdict(self)), indent=4)
    
    def remove_none(self, obj):
        if isinstance(obj, dict):
            return {k: self.remove_none(v) for k, v in obj.items() if v is not None}
        
        elif isinstance(obj, list):
            return [self.remove_none(i) for i in obj if i is not None]
        
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

    def to_json(self):
        return json.dumps(asdict(self), indent=4)

