import os
import bpy

from pathlib                    import Path
from bpy.types                  import Operator, Context
from bpy.props                  import StringProperty

from ...preferences              import get_prefs


class ConsoleToolsDirectory(Operator):
    bl_idname = "ya.consoletools_dir"
    bl_label = "Select File"
    bl_description = "Use this to manually find the TexTools directory and select ConsoleTools.exe. Hold Alt to open the TexTools folder if already found"
    
    filepath: StringProperty() # type: ignore
    filter_glob: bpy.props.StringProperty(
        default='*.exe',
        options={'HIDDEN'}) # type: ignore

    def invoke(self, context:Context, event):
        self.prefs = get_prefs()
        textools   = self.prefs.textools_directory

        if event.alt and os.path.exists(textools):
            os.startfile(textools)

        elif event.type == 'LEFTMOUSE':
            context.window_manager.fileselect_add(self)

        else:
             self.report({'ERROR'}, "Not a directory!")
    
        return {'RUNNING_MODAL'}

    def execute(self, context:Context):
        selected_file = Path(self.filepath)

        if selected_file.exists() and selected_file.name == "ConsoleTools.exe":
            textools_folder = str(selected_file.parent)
            self.prefs.textools_directory = textools_folder
            setattr(self.prefs, "consoletools_status", True)
            self.report({'INFO'}, f"Directory selected: {textools_folder}")
        
        else:
            self.report({'ERROR'}, "Not a valid ConsoleTools.exe!")
        
        return {'FINISHED'}
    
class ConsoleTools(Operator):
    bl_idname = "ya.consoletools"
    bl_label = "Modpacker"
    bl_description = "Checks for a valid TexTools install with ConsoleTools"

    def execute(self, context:Context):
        self.prefs             = get_prefs()
        consoletools, textools = self.console_tools_location(context)

        if os.path.exists(consoletools):
            self.prefs.textools_directory  = textools
            setattr(self.prefs, "consoletools_status", True)
        else:
            self.prefs.property_unset("textools_directory")
            self.prefs.consoletools_status = False
        
        return {"FINISHED"}
    
    def console_tools_location(self, context:Context) -> tuple[str, str]:
        import winreg
        textools = "FFXIV TexTools"
        textools_install = ""
        
        registry_path = r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
        reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path)
        
        for i in range(0, winreg.QueryInfoKey(reg_key)[0]):
            subkey_name = winreg.EnumKey(reg_key, i)
            subkey = winreg.OpenKey(reg_key, subkey_name)
            
            try:
                display_name, type = winreg.QueryValueEx(subkey, "DisplayName")
                
                if textools.lower() in display_name.lower():
                    textools_install, type = winreg.QueryValueEx(subkey, "InstallLocation")
                    break
                
            except FileNotFoundError:
                continue
            
            finally:
                winreg.CloseKey(subkey)
        
        winreg.CloseKey(reg_key)

        textools_install = Path(textools_install.strip('"'))
        consoletools = textools_install / "FFXIV_TexTools" / "ConsoleTools.exe"
        textools_folder = consoletools.parent
        
        return str(consoletools), str(textools_folder)


CLASSES = [
    ConsoleToolsDirectory,
    ConsoleTools,
]
  