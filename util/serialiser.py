import logging

from bpy.types    import PropertyGroup
from ..properties import safe_set_enum 

class RNAPropertyManager:
    """
    Serialise Blender RNA based PropertyGroups and its values into a dictionary for easier manipulation and storage.
    Takes a default set of enum values so they can be safely set and avoid invalid values.
    
    ### Functions:
    
    extract: Extracts specified PropertyGroup
    restore: Restores specified PropertyGroup with input data.
    remove: Removes PropertGroup collection at specified index. Restores data without the removed collection

    """

    enum_defaults: dict

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def extract(self, prop_group: PropertyGroup):
        return self.extract_property_group(prop_group)
    
    def restore(self, data: dict, prop_group: PropertyGroup):
        self.restore_property_group(data, prop_group, self.enum_defaults)
    
    def remove(self, collection: PropertyGroup, index_to_remove: int):
        """Remove item at specified index and restores PropertyGroup without it, keeping the original order"""
        return self.remove_from_collection(collection, index_to_remove, self.enum_defaults)

    def extract_property_group(self, prop_group: PropertyGroup):
        if prop_group is None:
            return None
            
        result = {}
        
        # All expected bpy_structs has "bl_rna" and its "properties", we use this to confirm we can parse them.
        if hasattr(prop_group, "bl_rna") and hasattr(prop_group.bl_rna, "properties"):
            properties = prop_group.bl_rna.properties
            
            for prop_name in properties.keys():
                if prop_name == "rna_type":
                    continue
                
                prop_def = properties[prop_name]
                prop_type = prop_def.type
                try:
                    value = getattr(prop_group, prop_name)
                    result[prop_name] = self.extract_value_by_type(value, prop_type)
                    
                except AttributeError:
                    self.logger.info(f'Warning: Could not read "{prop_name}".')
        
        return result
    
    def extract_value_by_type(self, value, prop_type: str):
        if prop_type == "COLLECTION":
            return [self.extract_property_group(item) for item in value]
        
        elif prop_type == "POINTER":
            if value is None:
                return None
            
            if isinstance(value, PropertyGroup):
                return self.extract_property_group(value)
            
            else:
                return None  
        elif prop_type in ["INT_ARRAY", "FLOAT_ARRAY", "BOOLEAN_ARRAY"]:
            return list(value) if hasattr(value, "__iter__") else [value]
        
        else:
            return value
    
    def restore_property_group(self, data: dict, prop_group: PropertyGroup, enum_defaults: dict=None):
        if data is None:
            return
        
        enum_defaults = enum_defaults or {}
        
        for prop_name, value in data.items():
            if not hasattr(prop_group, prop_name):
                continue
                
            try:
                prop_def = prop_group.bl_rna.properties.get(prop_name)
                if prop_def is None:
                    continue
                    
                prop_type = prop_def.type
                self.restore_value_by_type(prop_group, prop_name, value, prop_type, enum_defaults)
                
            except Exception as e:
                self.logger.info(f'Warning: Could not restore property "{prop_name}": {e}')
    
    def restore_value_by_type(self, prop_group: PropertyGroup, prop_name: str, value, prop_type: str, enum_defaults: dict):
        if prop_type == "COLLECTION":
            collection = getattr(prop_group, prop_name)
            collection.clear()
            for item_data in value:
                new_item = collection.add()
                self.restore_property_group(item_data, new_item, enum_defaults)
                
        elif prop_type == "POINTER":
            if value is not None:
                pointer = getattr(prop_group, prop_name)
                if pointer is not None:
                    self.restore_property_group(value, pointer, enum_defaults)
                    
        elif prop_type == "ENUM":
            default_value = enum_defaults.get(prop_name, "0")
            safe_set_enum(prop_group, prop_name, value, default_value)
            
        else:
            setattr(prop_group, prop_name, value)
    
    def remove_from_collection(self, collection: PropertyGroup, index_to_remove: int, enum_defaults: dict=None) -> bool:
        """Remove an item from any collection by extracting, filtering, and restoring"""
        if index_to_remove < 0 or index_to_remove >= len(collection):
            return False
        
        # Extract all items except the one to remove
        temp_items = []
        for index, item in enumerate(collection):
            if index != index_to_remove:
                temp_items.append(self.extract_property_group(item))
        
        # Clear and restore
        collection.clear()
        for item_data in temp_items:
            new_item = collection.add()
            self.restore_property_group(item_data, new_item, enum_defaults)
        
        return True
    