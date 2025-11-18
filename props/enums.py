from enum            import Enum
from ..utils.typings import BlendEnum


# Scaling values
SCALE_FROM_BASE = {
    101: 1.0000,    # Midlander Male
    201: 0.9120,    # Midlander Female
    301: 0.9491,    # Highlander Male
    401: 0.8623,    # Highlander Female
    501: 1.1260,    # Elezen Male
    601: 1.0761,    # Elezen Female
    701: 1.0049,    # Miqo'te Male
    801: 0.9024,    # Miqo'te Female
    901: 1.4048,    # Roegadyn Male
    1001: 0.9818,   # Roegadyn Female
    1101: 0.4415,   # Lalafell Male
    1201: 0.4415,   # Lalafell Female
    1301: 1.0000,   # Au Ra Male 
    1401: 0.8992,   # Au Ra Female
    1501: 1.4048,   # Hrothgar Male
    1601: 1.0918,   # Hrothgar Female
    1701: 1.0000,   # Viera Male
    1801: 0.8782,   # Viera FeMale
}

class RacialCodes(Enum):
    Middie_M = '0101'
    Middie_F = '0201'
    High_M   = '0301'
    High_F   = '0401'
    Elezen_M = '0501'
    Elezen_F = '0601'
    Miqo_M   = '0701'
    Miqo_F   = '0801'
    Roe_M    = '0901'
    Roe_F    = '1001'
    Lala_M   = '1101'
    Lala_F   = '1201' 
    Aura_M   = '1301'
    Aura_F   = '1401'
    Hroth_M  = '1501'
    Hroth_F  = '1601'
    Viera_M  = '1701'
    Viera_F  = '1801'

def get_racial_name(code: str, gender=True) -> str:
    name = RacialCodes(code).name.replace('_', ' ').split(' ')
    if gender:
        return " ".join(name)
    else:
        return name[0]
    
def get_racial_enum(optional=True) -> BlendEnum:
    items = [('', "Unspecified:", ""), ('0', "None", ""), ('', "MALE:", "")] if optional else [('', "MALE:", "")]
    items.extend([(race.value , race.name.replace("_", " "), "") for race in RacialCodes if race.name.endswith('_M')])
    items.append(('', "FEMALE:", ""))
    items.extend([(race.value , race.name.replace("_", " "), "") for race in RacialCodes if race.name.endswith('_F')])
    return items