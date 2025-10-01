import json
import urllib.request as req

from typing       import Optional
from urllib.error import URLError


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
