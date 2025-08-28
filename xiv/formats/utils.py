import os
import json
import copy
import numpy as np
import struct

from io           import BytesIO
from typing       import Self
from pathlib      import Path
from dataclasses  import asdict, fields
from numpy.typing import NDArray


def write_padding(amount: int) -> bytes:
    if amount == 0:
        return b''
    
    return bytes([0] * amount)

def write_alignment(file: BytesIO, alignment: int=8) -> bytes:
    current_pos = file.tell()
    if current_pos % alignment == 0:
        return
    
    padding = alignment - (current_pos % alignment)
    
    return bytes([0] * padding)

def read_packed_version(packed_version: int) -> float:
    build = packed_version & 0xFF
    patch = (packed_version >> 8) & 0xFF
    minor = (packed_version >> 16) & 0xFF
    major = (packed_version >> 24) & 0xFF
    return f"{major}.{minor}.{patch}.{build}"

class BinaryReader:
    def __init__(self, data: bytes):
        self.data   = data
        self.pos    = 0
        self.length = len(data)
    
    def read_struct(self, format_str: str):
        size = struct.calcsize(format_str)
        if self.pos + size > self.length:
            raise EOFError("End of stream")
        
        result = struct.unpack_from(format_str, self.data, self.pos)
        self.pos += size
        return result[0] if len(result) == 1 else result
    
    def read_byte(self) -> int:
        return self.read_struct('<B')
    
    def read_bytes(self, length: int) -> bytes:
        if self.pos + length > self.length:
            raise EOFError("End of stream")
        result = self.data[self.pos:self.pos + length]
        self.pos += length
        return result
    
    def read_bool(self) -> bool:
        return self.read_struct('<?')
    
    def read_uint16(self) -> int:
        return self.read_struct('<H')
    
    def read_uint32(self) -> int:
        return self.read_struct('<I')  
    
    def read_float(self) -> float:
        return self.read_struct('<f')
    
    def read_array(self, length: int, format_str: str='I', endian: str='<') -> list[int | float]:
        array = []
        for _ in range(length):
            array.append(self.read_struct(f'{endian}{format_str}'))
        
        return array
    
    def read_to_ndarray(self, dtype: str, count: int) -> NDArray:
        array = np.frombuffer(
                    self.data[self.pos:],
                    dtype,
                    count,
                    0
                ).copy()

        self.pos += np.dtype(dtype).itemsize * count
        return array

    def read_string(self, length: int, encoding: str='utf-8') -> str:
        raw_bytes = self.read_bytes(length)
    
        null_index   = raw_bytes.find(b'\x00')
        string_bytes = raw_bytes if null_index == -1 else raw_bytes[:null_index]

        try:
            return string_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(f"Couldn't decode string: {e}") 
    
    def slice_from(self, offset: int, length: int) -> 'BinaryReader':
        if offset + length > self.length:
            raise EOFError("Slice extends beyond stream")
        return BinaryReader(self.data[offset:offset + length])
    
    def remaining_bytes(self) -> int:
        return self.length - self.pos

class PMPJson:

    @classmethod
    def from_dict(cls, input: dict):
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
