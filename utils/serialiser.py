import logging

from bpy.types    import PropertyGroup

class RNAPropertyManager:
    """
    Serialise Blender RNA based PropertyGroups and its values into a dictionary for easier manipulation and storage.
    
    ### Functions:
    
    extract: Extracts specified PropertyGroup.

    restore: Restores specified PropertyGroup with input data.

    remove: Removes PropertGroup collection at specified index. Restores PropertyGroup without the removed collection.

    """

    def __init__(self):
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def extract(self, prop_group: PropertyGroup) -> dict:
        return self.extract_property_group(prop_group)
    
    def restore(self, data: dict, prop_group: PropertyGroup):
        self.restore_property_group(data, prop_group)
    
    def remove(self, collection: PropertyGroup, index_to_remove: int):
        """Remove item at specified index and restores PropertyGroup without it, keeping the original order"""
        if index_to_remove < 0 or index_to_remove >= len(collection):
            return False
        
        temp_items = []
        for index, item in enumerate(collection):
            if index != index_to_remove:
                temp_items.append(self.extract_property_group(item))
        
        collection.clear()
        for item_data in temp_items:
            new_item = collection.add()
            self.restore_property_group(item_data, new_item)
        
        return True

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
                self.restore_value_by_type(prop_group, prop_name, value, prop_type)
                
            except Exception as e:
                self.logger.info(f'Warning: Could not restore property "{prop_name}": {e}')
    
    def restore_value_by_type(self, prop_group: PropertyGroup, prop_name: str, value, prop_type: str):
        if prop_type == "COLLECTION":
            collection = getattr(prop_group, prop_name)
            collection.clear()
            for item_data in value:
                new_item = collection.add()
                self.restore_property_group(item_data, new_item)
                
        elif prop_type == "POINTER":
            if value is not None:
                pointer = getattr(prop_group, prop_name)
                if pointer is not None:
                    self.restore_property_group(value, pointer)
                    
        elif prop_type == "ENUM":
            try:
                setattr(prop_group, prop_name, value)
            except:
                prop_group.property_unset(prop_name)
                
            
        else:
            setattr(prop_group, prop_name, value)
    
    
    