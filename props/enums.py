from enum            import Enum
from ..utils.typings import BlendEnum


def get_racial_enum(optional=True) -> BlendEnum:
    items = [('', "Unspecified:", ""), ('0', "None", ""), ('', "MALE:", "")] if optional else [('', "MALE:", "")]
    items.extend([(race.value , race.name.replace("_", " "), "") for race in RacialCodes if race.name.endswith('_M')])
    items.append(('', "FEMALE:", ""))
    items.extend([(race.value , race.name.replace("_", " "), "") for race in RacialCodes if race.name.endswith('_F')])
    return items

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
