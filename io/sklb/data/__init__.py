import json

from typing  import Literal
from pathlib import Path


_FOLDER = Path(__file__).parent

def get_bone_list(category: Literal['VANILLA', 'IVCS']) -> list[str]:
    with open(_FOLDER / "bone_list.json", 'r') as file:
        return json.load(file)[category]
    
def save_bone_list(bone_list: list[str], category: Literal['VANILLA', 'IVCS']) -> dict[str, int]:
    current_dict   = {}
    existing_bones = set()

    if (_FOLDER / "bone_list.json").stat().st_size > 0:
        with open(_FOLDER / "bone_list.json", 'r') as file:
            current_dict   = json.load(file)
            existing_bones = {bone for blist in current_dict.values() for bone in blist}

    with open(_FOLDER / "bone_list.json", 'w') as file:
        if category not in current_dict:
            current_dict[category] = []

        for bone in bone_list:
            if bone not in existing_bones:
                current_dict[category].append(bone)

        json.dump(current_dict, file, indent=4)
    