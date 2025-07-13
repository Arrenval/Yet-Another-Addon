import os
import json
import copy

from pathlib     import Path
from typing      import Self
from dataclasses import asdict, fields

class PMPJson:

    @classmethod
    def from_dict(cls, input:dict):
        field_names = {field.name for field in fields(cls)}
        
        filtered_input = {}

        for key, value in input.items():
            if key in field_names:
                filtered_input[key] = value
            else:
                print(f"Unknown field: {key} in {cls.__name__}")
        
        return cls(**filtered_input)

    def update_from_dict(self, input: dict):
        field_names = {field.name for field in fields(self)}
        
        for key, value in input.items():
            if key in field_names:
                setattr(self, key, value)
            else:
                print(f"Unknown field: {key} in {self.__class__.__name__}")

    def remove_none(self, obj):
        if isinstance(obj, dict):
            return {key: self.remove_none(value) for key, value in obj.items() if value is not None}
        
        elif isinstance(obj, list):
            return [self.remove_none(index) for index in obj if index is not None]
        
        return obj

    def to_json(self):
        return json.dumps(self.remove_none(asdict(self)), indent=4)
    
    def write_json(self, output_dir:Path, file_name):
        with open(os.path.join(output_dir, file_name + ".json"), "w") as file:
                file.write(self.to_json())
    
    def copy(self) -> Self:
        return copy.deepcopy(self)
