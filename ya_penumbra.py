
@dataclass
class TypeManip:
    Entry: Union[int, float, dict] = None
    #EQDP, EQP, Est
    Gender: str = None
    Race: str = None
    SetID: str = None
    Slot: str = None
    #Rsp
    SubRace: str = None
    Attribute: str = None
    #GlobalEqp
    Type: str = None
    Condition: str = None
    #Imc
    ObjectType: str = None
    PrimaryId: int = None
    SecondaryId: int = None
    Variant: int = None
    EquipSlot: str = None
    BodySlot: str = None

@dataclass
class ModManipulations:
    Type: str = ""
    Manipulation: List[TypeManip] = None
    
    def __post_init__(self):
        self.Manipulation = TypeManip(self.Manipulation)

@dataclass
class ImcDefaultEntry:
    MaterialId: int = 0
    DecalId: int = 0
    VfxId: int = 0
    MaterialAnimationId: int = 0
    AttributeAndSound: int = 0
    AttributeMask: int = 0
    SoundId: int = 0

@dataclass
class ImcIdentifier:
    ObjectType: str = ""
    PrimaryId: int = 0
    SecondaryId: int = 0
    Variant: int = 0
    EquipSlot: str = ""
    BodySlot: str = ""

@dataclass
class GroupOptions:
    Files: Dict[str, str] = None
    FileSwaps: Dict[str, str] = None
    Manipulations: List[ModManipulations] = None
    Priority: int = 0
    AttributeMask: int = None
    Name: str = ""
    Description: str = ""
    Image: str = ""

    def __post_init__(self):
        if self.Manipulations != None:
            self.Manipulations = [ModManipulations(**manip) for manip in self.Manipulations]
        
@dataclass
class ModGroups:
    Version: int = 0
    DefaultEntry: ImcDefaultEntry = None
    Identifier: ImcIdentifier = None
    AllVariants: bool = None
    OnlyAttributes: bool = None
    Name: str = ""
    Description: str = ""
    Priority: int = 0
    Image: str = ""
    Page: int = 0
    Type: str = None
    DefaultSettings: int = 0
    Options: List[GroupOptions] = None
    Manipulations: List[ModManipulations] = None

    def __post_init__(self):
        if self.Options != None:
            self.Options = [GroupOptions(**option) for option in self.Options]
        elif self.Manipulations != None:
            self.Manipulations = [ModManipulations(**manip) for manip in self.Manipulations]
        

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
    FileVersion: int = 3
    Name: str = ""
    Author: str = ""
    Description: str = ""
    Image: str = ""
    Version: str = ""
    Website: str = ""
    ModTags: list = field(default_factory=list)
    Description: str = ""

    def to_json(self):
        return json.dumps(asdict(self), indent=4)
  