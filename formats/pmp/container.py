from typing        import List, Dict
from dataclasses   import dataclass, field

from ..utils       import PMPJson
from .manipulation import ManipulationType


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
class DefaultMod(PMPJson):
    Version      :int  = 0
    Files        :Dict[str, str] = field(default_factory=dict)
    FileSwaps    :Dict[str, str] = field(default_factory=dict)
    Manipulations:List[ManipulationType] = field(default_factory=dict)

    def __post_init__(self):
        if self.Manipulations is not None:
            self.Manipulations = [ManipulationType.from_dict(manip) for manip in self.Manipulations] 
