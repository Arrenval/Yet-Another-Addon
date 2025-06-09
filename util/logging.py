class ModpackError(Exception):
    """Base Modpack related class"""
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

class ModpackGamePathError(ModpackError):
    """XIV game path is not valid"""
    pass
