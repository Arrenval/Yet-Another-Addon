import bpy

from typing    import Any
from bpy.types import Space, Context


class SceneOptimiser:
    """
    Simple context manager to optimise scene rendering during various operations. 
    Funny thing is it doesn't actually work for its most important use case.
    """
    
    def __init__(self, context: Context= None, optimisation_level="high") -> None:
        self.original_settings: dict[str, dict[str, Any]] = {
            "render" : {},
            "shading": {},
            "overlay": {},
            "visibility": {}
        }
        self.optimisation_level   = optimisation_level
        self.optimisation_applied = False

        self.context   : Context  = context if context else bpy.context
        self.space_data: Space    = None

    def __enter__(self) -> Context:
        self.valid_context = self._validate_context()

        if self.valid_context:
            self._get_original_settings()
            self._apply_export_optimisations()
        else:
            print("Warning: Invalid context for scene optimisation")
        
        return self.context

    def _validate_context(self) -> bool:
        if not hasattr(self.context, "space_data"):
            print("Warning: No space_data available")
            return False
        
        if self.context.space_data is None:
            print("Warning: space_data is None")
            return False
        
        if self.context.space_data.type != "VIEW_3D":
            print(f"Warning: Not in 3D viewport (current: {self.context.space_data.type})")
            return False
        
        self.space_data = self.context.space_data
        return True
    
    def _get_original_settings(self):
        if not self.space_data:
            return
        
        shading = self.space_data.shading

        self.original_settings["shading"]["type"]                  = shading.type
        self.original_settings["shading"]["light"]                 = shading.light
        self.original_settings["shading"]["color_type"]            = shading.color_type
        self.original_settings["shading"]["show_backface_culling"] = shading.show_backface_culling
        self.original_settings["shading"]["show_xray"]             = shading.show_xray
        self.original_settings["shading"]["show_shadows"]          = shading.show_shadows
        self.original_settings["shading"]["show_cavity"]           = shading.show_cavity
        self.original_settings["shading"]["use_dof"]               = shading.use_dof
        self.original_settings["shading"]["show_object_outline"]   = shading.show_object_outline

        self.original_settings["visibility"]["armature_visibility"] = self.space_data.show_object_viewport_armature
        
        overlay = self.space_data.overlay
        self.original_settings["overlay"]["show_overlays"] = overlay.show_overlays

        scene = self.context.scene
        self.original_settings["render"]["fps"]      = scene.render.fps
        self.original_settings["render"]["fps_base"] = scene.render.fps_base
        
    def _apply_export_optimisations(self):
        if not self.space_data:
            return
        
        shading = self.space_data.shading
        
        # Currently the shading type refuses to update any operator context
        bpy.ops.view3d.toggle_shading(type="SOLID")
        
        shading.light                 = "FLAT"
        shading.color_type            = "SINGLE"

        shading.show_backface_culling = True
        shading.show_xray             = False
        shading.show_shadows          = False
        shading.show_cavity           = False
        shading.use_dof               = False
        shading.show_object_outline   = False

        self.space_data.show_object_viewport_armature = True
        
        overlay = self.space_data.overlay
        overlay.show_overlays = False  
        
        self.context.scene.render.fps = 1 
        self.context.scene.render.fps_base = 100
        
        self.optimisation_applied = True
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            print(f"Exception occurred in viewport context: {exc_type.__name__}: {exc_value}")
        
        if self.valid_context and self.optimisation_applied:
            try:
                self._restore_original_settings()
            except Exception as e:
                print(f"Error restoring scene settings: {e}")
        
        return False

    def _restore_original_settings(self):
        if not self.original_settings:
            print("No original settings to restore")
            return
        
        if not self.space_data:
            return
        
        render     = self.context.scene.render
        space_data = self.context.space_data
        shading    = self.space_data.shading
        overlay    = self.space_data.overlay

        for setting_name, value in self.original_settings["render"].items():
            if not hasattr(render, setting_name):
                continue
            setattr(render, setting_name, value)
            
        for setting_name, value in self.original_settings["shading"].items():
            if setting_name == "type":
                bpy.ops.view3d.toggle_shading(type=value)
                continue
            if not hasattr(shading, setting_name):
                continue
            setattr(shading, setting_name, value)

        for setting_name, value in self.original_settings["overlay"].items():
            if not hasattr(overlay, setting_name):
                continue
            setattr(overlay, setting_name, value)

        for setting_name, value in self.original_settings["visibility"].items():
            if not hasattr(space_data, setting_name):
                continue
            setattr(space_data, setting_name, value)

        self.optimisation_applied = False

    