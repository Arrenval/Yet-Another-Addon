class ModpackError(Exception):
    """Base class"""
    pass

class ModpackNameError(ModpackError):
    """Raised when modpack data validation doesn't find a valid name"""
    pass

class ModpackValidationError(ModpackError):
    """Raised when modpack data validation fails"""
    pass

class ModpackFileError(ModpackError):
    """Either the file does not exist or is not a supported file format"""
    pass

class ModpackFolderError(ModpackError):
    """Could not find the specified folder"""
    pass

class ModpackPhybCollisionError(ModpackError):
    """New simulator uses collision object not defined in base phybs"""
    pass

class ModpackGamePathError(ModpackError):
    """XIV game path is not valid"""
    pass

class XIVModelError(Exception):
    """Error in XIVModel"""
    pass

class XIVMeshError(XIVModelError):
    """Error in a XIVMesh"""
    pass

class XIVMeshIDError(XIVMeshError):
    """Meshes uses an x.y identifier in their name before processing.
    Unable to resolve said identifier."""
    pass

class XIVMeshParentError(XIVMeshError):
    """Raised if mesh parent is not a visible armature"""
    pass