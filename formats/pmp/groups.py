from typing        import List
from dataclasses   import dataclass

from ..utils       import PMPJson
from .container    import GroupOption, GroupContainer
from .manipulation import ManipulationEntry, ManipulationType


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
