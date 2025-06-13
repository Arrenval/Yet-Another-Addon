import logging

from bpy.types    import PropertyGroup


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
        
        result = {}
        
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
            
            # We only extract the pointer if its an PropertyGroup we can handle
            if isinstance(pointer_data, PropertyGroup):
                return self.extract_property_group(pointer_data)
            
            else:
                return None  





    
    
    