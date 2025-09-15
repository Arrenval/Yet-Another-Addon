import json

from pathlib import Path


_FOLDER = Path(__file__).parent

def get_neck_morphs(race_code: str) -> list[tuple[list[float], list[float]]]:
    if race_code == "0":
        return []
    
    neck_morphs = []
    with open(_FOLDER / "neck_morph.json", 'r') as file:
        json_morphs = json.load(file)
        for data in json_morphs[race_code]:
            neck_morphs.append((data["positions"], data["normals"]))
    
    return neck_morphs
    