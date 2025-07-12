import struct
import logging

from bpy.types    import PropertyGroup


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
    
    def read_uint32(self) -> int:
        return self.read_struct('<I')  
    
    def read_uint16(self) -> int:
        return self.read_struct('<H')
    
    def read_byte(self) -> int:
        return self.read_struct('<B')
    
    def read_float(self) -> float:
        return self.read_struct('<f')
    
    def read_vector(self, length: int, format_str: str ='f') -> tuple[float, ...]:
        return self.read_struct(f'<{format_str * length}')
    
    def read_bytes(self, count: int) -> bytes:
        if self.pos + count > self.length:
            raise EOFError("End of stream")
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result
    
    def read_string(self, length: int, encoding: str='utf-8') -> str:
        raw_bytes = self.read_bytes(length)
    
        null_index = raw_bytes.find(b'\x00')
        if null_index != -1:
            string_bytes = raw_bytes[:null_index]
        else:
            string_bytes = raw_bytes

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
    
class RNAPropertyIO:
    """
    Serialise Blender RNA based PropertyGroups and its values into a dictionary for easier manipulation and storage.
    
    ### Methods
    
    extract: Extracts specified PropertyGroup.

    restore: Restores specified PropertyGroup with input data.

    remove: Removes PropertGroup collection at specified index. Restores PropertyGroup without the removed collection.

    """

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    
    def extract(self, prop_group: PropertyGroup) -> list[dict]:
        if hasattr(prop_group, '__len__') and hasattr(prop_group, '__iter__'):
            return [self.extract_property_group(item) for item in prop_group]
        
        else:
            return [self.extract_property_group(prop_group)]
    
    def add(self, collection_data: list[dict], target_group: PropertyGroup):
        for item_data in collection_data:
            new_item = target_group.add()
            self.restore_property_group(item_data, new_item)

    def restore(self, collection_data: list[dict], prop_group: PropertyGroup):
        prop_group.clear()
        for entry in collection_data:
            new_item = prop_group.add()
            self.restore_property_group(entry, new_item)
    
    def remove(self, prop_group: PropertyGroup, index_to_remove: int):
        """Remove item at specified index and restores PropertyGroup without it, keeping the original order"""
        if index_to_remove < 0 or index_to_remove >= len(prop_group):
            return False
        
        temp_items = []
        for index, item in enumerate(prop_group):
            if index != index_to_remove:
                temp_items.append(self.extract_property_group(item))
        
        prop_group.clear()
        for item_data in temp_items:
            new_item = prop_group.add()
            self.restore_property_group(item_data, new_item)
        
        return True

    def extract_property_group(self, prop_group: PropertyGroup) -> dict:
        if prop_group is None:
            return None
            
        # Checks for required attributes
        if not hasattr(prop_group, "bl_rna") and not hasattr(prop_group.bl_rna, "properties"):
            return None
        
        result     = {}
        properties = prop_group.bl_rna.properties
        for prop_name in properties.keys():
            if prop_name == "rna_type":
                continue
            
            prop_def = properties[prop_name]
            prop_type = prop_def.type
            try:
                value = getattr(prop_group, prop_name)

                if prop_type == "COLLECTION":
                    result[prop_name] = self.handle_collection(prop_group, prop_name, value, restore=False)

                elif prop_type == "POINTER":
                    result[prop_name] = self.handle_pointer(prop_group, prop_name, value, restore=False)

                elif prop_type in ["INT_ARRAY", "FLOAT_ARRAY", "BOOLEAN_ARRAY"]:
                    result[prop_name] = list(value) if hasattr(value, "__iter__") else [value]

                else:
                    result[prop_name] = value
                
            except AttributeError:
                self.logger.info(f'Warning: Could not read "{prop_name}".')
        
        return result
    
    def restore_property_group(self, data: dict, prop_group: PropertyGroup):
        if data is None:
            return
        
        for prop_name, value in data.items():
            if not hasattr(prop_group, prop_name):
                continue
                
            try:
                prop_def = prop_group.bl_rna.properties.get(prop_name)
                if prop_def is None:
                    continue
                    
                prop_type = prop_def.type
                if prop_type == "COLLECTION":
                    self.handle_collection(prop_group, prop_name, value)

                elif prop_type == "POINTER":
                    self.handle_pointer(prop_group, prop_name, value)

                elif prop_type == "ENUM":
                    try:
                        setattr(prop_group, prop_name, value)
                    except:
                        prop_group.property_unset(prop_name)

                else:
                    setattr(prop_group, prop_name, value)
                
            except Exception as e:
                self.logger.info(f'Warning: Could not restore property "{prop_name}": {e}')
    
    def handle_collection(self, prop_group: PropertyGroup, prop_name: str, collection_data, restore=True) -> list:
        if restore:
            collection = getattr(prop_group, prop_name)
            collection.clear()
            for item_data in collection_data:
                new_collection = collection.add()
                self.restore_property_group(item_data, new_collection)

        else:
            return [self.extract_property_group(item) for item in collection_data]
    
    def handle_pointer(self, prop_group: str, prop_name: str, pointer_data, restore=True) -> dict:
        if restore:
            if pointer_data is not None:
                pointer = getattr(prop_group, prop_name)
                if pointer is not None:
                    self.restore_property_group(pointer_data, pointer)
        else:
            if pointer_data is None:
                return None
            
            # We only extract the pointer if it's a PropertyGroup we can handle
            if isinstance(pointer_data, PropertyGroup):
                return self.extract_property_group(pointer_data)
            
            else:
                return None  





    
    
    