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

class ModpackGamePathError(ModpackError):
    """XIV game path is not valid"""
    pass

class SurfaceDeformBindError(Exception):
    pass

class VertexCountError(Exception):
    pass

class XIVMeshError(Exception):
    """Base class"""
    pass

class XIVMeshParentError(XIVMeshError):
    """Raised if mesh parent is not a visible armature"""

    def __init__(self, amount: int) -> None:
        self.amount = amount
        plural  = "es" if self.amount > 1 else ""
        concord = "are" if self.amount > 1 else "is"
        message = f"{self.amount} mesh{plural} {concord} missing a parent skeleton."
        super().__init__(message)

