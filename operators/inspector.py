import bpy

from pathlib      import Path
from bpy.types    import Operator, Context
from bpy.props    import StringProperty

from ..formats.phyb.file import PhybFile


def compare_binaries(original_path: str, written_path: str, context_bytes: int=32):
        """
        Compare two binary files.
        """
        with open(original_path, 'rb') as orig_file:
            original_data = orig_file.read()
        
        with open(written_path, 'rb') as written_file:
            written_data = written_file.read()
        
        print(f"Original file size: {len(original_data)} bytes")
        print(f"Written file size: {len(written_data)} bytes")
        
        first_difference = None
        min_length = min(len(original_data), len(written_data))
        
        for i in range(min_length):
            if original_data[i] != written_data[i]:
                first_difference = i
                break
        
        if first_difference is None:
            if len(original_data) != len(written_data):
                print(f"Files are identical until byte {min_length}, but different lengths")
            else:
                print("Files are identical!")
            return
        
        print(f"\nFirst difference at address 0x{first_difference:X} (decimal {first_difference})")
        
        start_addr = max(0, first_difference - context_bytes)
        end_addr   = min(min_length, first_difference + context_bytes)
        
        print(f"\nContext around first difference (showing {context_bytes} bytes before and after):")
        print("Address   Original                         Written")
        print("--------  -------------------------------  -------------------------------")
        
        for addr in range(start_addr, end_addr, 16):
            orig_line = original_data[addr:addr + 16]
            written_line = written_data[addr:addr + 16] if addr + 16 <= len(written_data) else written_data[addr:]
            
            orig_hex = ' '.join(f'{b:02x}' for b in orig_line)
            written_hex = ' '.join(f'{b:02x}' for b in written_line)
            
            if orig_line != written_line:
                marker = " <-- DIFFERENT"
            else:
                marker = ""
                
            print(f"0x{addr:06X}  {orig_hex:<31}  {written_hex:<31}{marker}")

class FileInspector(Operator):
    bl_idname = "ya.file_inspector"
    bl_label = "Inspect"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = ""

    filepath : StringProperty(subtype="FILE_PATH") # type: ignore

    def invoke(self, context: Context, event):
        context.window_manager.fileselect_add(self,)

        return {"RUNNING_MODAL"}
    
    def execute(self, context):
        selected_file = self.filepath

        phyb = PhybFile.from_file(selected_file)

        print(phyb.get_collision_names())

        new_file = Path(selected_file).parent / "testphyb.phyb"
        
        phyb.to_file(new_file)

        compare_binaries(selected_file, new_file)
        
        return {'FINISHED'}
    
    
    

CLASSES = [
    FileInspector
]