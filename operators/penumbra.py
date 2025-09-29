import bpy
import json
import shutil
import tempfile
import urllib.request as req

from time              import time
from typing            import Optional
from pathlib           import Path
from bpy.types         import Operator
from urllib.error      import URLError

from ..preferences     import get_prefs
from ..props.getters   import get_window_props
from ..xiv.formats.pmp import Modpack, sanitise_path


class PenumbraClient:

    def __init__(self, base_url: str = "http://localhost:42069"):
        self.base_url = f"{base_url.rstrip('/')}/api"
    
    def _send(self, endpoint: str, data: dict | None = None) -> None:
        request = req.Request(
                        url=f"{self.base_url}{endpoint}", 
                        data=json.dumps(data).encode('utf-8'),
                        headers={'Content-Type': 'application/json'},
                        method='POST'
                    )
        
        try:
            req.urlopen(request, timeout=1)
        except URLError as e:
            raise ConnectionError(f"Failed to connect: {e}")
        
    def get_dir(self) -> str | None:
        try:
            with req.urlopen(f"{self.base_url}/moddirectory", timeout=1) as response:
                return response.read().decode('utf-8').replace('"', "")
        except URLError:
            return None
    
    def get_mods(self) -> dict | None:
        try:
            with req.urlopen(f"{self.base_url}/mods", timeout=5) as response:
                return json.loads(response.read().decode('utf-8'))
        except URLError:
            return None
    
    def install_mod(self, path: str) -> None:
        self._send("/installmod", {"Path": path})

    def reload_mod(self, path: Optional[str] = None, name: Optional[str] = None) -> None:
        if not any((path, name)):
            raise ValueError("Requires name or path to be specified.")
        self._send("/reloadmod", {"Path": path, "Name": name})

    def focus_mod(self, path: Optional[str] = None, name: Optional[str] = None) -> None:
        if not any((path, name)):
            raise ValueError("Requires name or path to be specified.")
        self._send("/focusmod", {"Path": path, "Name": name})

    def open_window(self) -> None:
        self._send("/openwindow")
    
    def redraw(self, mode: str) -> None:
        if mode == 'SELF':
            self._send("/redraw", {"ObjectTableIndex": 0, "Type": 0})
        else:
            self._send("/redrawAll")

    def set_mod_settings(
                    self, 
                    collection: Optional[int]  = None, 
                    path      : Optional[str]  = None, 
                    name      : Optional[str]  = None,
                    inherit   : Optional[bool] = None, 
                    state     : Optional[bool] = None, 
                    priority  : Optional[int]  = None,
                    ) -> None:
        
        self._send(
                "/setmodsettings", 
                {
                    "CollectionId": collection, 
                    "ModPath"     : path, 
                    "Modname"     : name, 
                    "Inherit"     : inherit, 
                    "State"       : state,
                    "Priority"    : priority, 
                }
            )


class PenumbraCall(Operator):
    bl_idname = "ya.penumbra_call"
    bl_label = "Modpacker"
    bl_description = "FBX to MDL converter via ConsoleTools"

    def invoke(self, context, event):
        self.client  = PenumbraClient()
        penumbra_dir = self.client.get_dir()

        if penumbra_dir is None or not penumbra_dir.strip():
            self.report({'ERROR'}, "Couldn't retrieve Penumbra Mod Directory. Make sure FFXIV is running.")
            return {'CANCELLED'}
        
        self.mod_name = sanitise_path(get_window_props().file.penumbra_mod)
        self.folder   = Path(penumbra_dir) / self.mod_name

        if self.folder.is_dir() and not self._check_mod_tag(self.folder):
            wm = context.window_manager
            wm.invoke_confirm(
                        self,
                        event=event, 
                        title="Warning", 
                        message= "Mod already exists, do you want to replace it?",
                        icon='WARNING', 
                        confirm_text="Export")
            
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)
        
    def _check_mod_tag(self, folder: Path) -> bool:
        try:
            pmp = Modpack.read_meta(folder)
            return "YABlender" in pmp.meta.ModTags
        except FileNotFoundError:
            return False

    def execute(self, context):
        backup_dir  = get_prefs().export.output_dir
        redraw_mode = get_window_props().file.redraw_mode
        
        if not get_window_props().file.io.valid_xiv_path:
            self.report({'ERROR'}, "Please input a path to your target model.")
            return {'CANCELLED'}
        
        context.window.cursor_set('WAIT')
        try:
            self.create_modpack(self.folder)

            self.client.open_window()
            self.client.reload_mod(path=self.mod_name)
            self.client.focus_mod(path=self.mod_name)
            self.client.set_mod_settings(path=self.mod_name, priority=999, state=True)
            if redraw_mode != 'GLAM':
                self.client.redraw(redraw_mode)

        except ConnectionError:
            self.report({'ERROR'}, "Couldn't Connect to Penumbra. Make sure FFXIV is running.")
        finally:
            context.window.cursor_set('DEFAULT')
            get_prefs().export.output_dir = backup_dir
            return {'FINISHED'}
    
    def create_modpack(self, folder: Path) -> Modpack:
        file_name = "yamodel_" + hex(int(time()))[2:]
        xiv_path  = get_window_props().file.io.export_xiv_path
        rel_path  = "Blender\\" + file_name + ".mdl"

        pmp = Modpack()
        pmp.meta.Author  = "Blender"
        pmp.meta.Version = "TEST"
        pmp.meta.Name    = self.mod_name
        pmp.meta.ModTags.append("YABlender")
        pmp.default.Files[xiv_path] = rel_path

        with tempfile.TemporaryDirectory(prefix=f"_penumbra_blender_", ignore_cleanup_errors=True) as temp_dir:
            temp_path = Path(temp_dir)
            get_prefs().export.output_dir = temp_dir
            try:
                bpy.ops.ya.export('INVOKE_DEFAULT', mode="PENUMBRA", user_input=file_name)
                temp_mdl = temp_path / (file_name + ".mdl")
                pmp.to_folder(folder, {temp_mdl: rel_path})
            finally:
                log_name = "yet_another_error.log"
                log_file = temp_path / log_name
                if log_file.exists():
                    permanent_log = folder / log_name
                    folder.parent.mkdir(exist_ok=True)
                    shutil.copy(log_file, permanent_log)
                    self.report({'ERROR'}, f"An error occurred, log saved to: {permanent_log}")


CLASSES = [
    PenumbraCall
]