from dataclasses import dataclass

from ..utils     import PMPJson


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
