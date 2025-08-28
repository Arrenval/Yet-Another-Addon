import os
import tempfile

from pathlib            import Path
from bpy.types          import Operator
from bpy.props          import BoolProperty

from ..props            import get_window_properties
from ..xiv.io           import ModelImport 
from ..xiv.formats.phyb import PhybFile
from ..xiv.formats.model import XIVModel


def compare_binaries(original_path: str, written_path: str, context_bytes: int=32):
        """
        Compare two binary files.
        """
        with open(original_path, 'rb') as orig_file:
            original_data = orig_file.read()
        
        with open(written_path, 'rb') as written_file:
            written_data = written_file.read()
        
        print(f"Primary file size: {len(original_data)} bytes")
        print(f"Secondary file size: {len(written_data)} bytes")
        
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

class FileRoundtrip(Operator):
    bl_idname = "ya.file_roundtrip"
    bl_label = "Inspect"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = "Compares the input file with directly written output"

    def execute(self, context):
        self.window = get_window_properties()
        model = XIVModel.from_file(self.window.insp_file1)
        path = str(Path(self.window.insp_file1).parent / "Roundtrip.mdl")

        model.to_file((path))
   
        compare_binaries(
            get_window_properties().insp_file1, 
            path
            )
        
        return {'FINISHED'}
    
class PhybAppend(Operator):
    bl_idname = "ya.phyb_append"
    bl_label = "Inspect"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = ""

    collision_check: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}) #type: ignore

    @classmethod
    def description(cls, context, properties):
        if properties.collision_check:
            return "Check if all collision objects are defined in the base phyb without outputting a new file"
        else:
            return """Appends simulators to the base phyb.
Prints an error for every simulator that has undefined collision objects in the primary phyb.
Resulting phyb is written to the same folder as the base phyb"""

    def execute(self, context):
        self.window = get_window_properties()

        files_exist = Path(self.window.insp_file1).is_file() and Path(self.window.insp_file2).is_file()
        if not files_exist:
            self.report({'ERROR'}, "Couldn't find selected files.")
            return {'CANCELLED'}
        
        phyb_files  = Path(self.window.insp_file1).suffix == ".phyb" and Path(self.window.insp_file1).suffix == ".phyb"
        if not phyb_files:
            self.report({'ERROR'}, "Please select phyb files.")
            return {'CANCELLED'}
            
        base_phyb = PhybFile.from_file(self.window.insp_file1)
        sim_phyb  = PhybFile.from_file(self.window.insp_file2)
        collision_obj = base_phyb.get_collision_names()

        for idx, simulator in enumerate(sim_phyb.simulators):
            if not simulator.get_collision_names() <= collision_obj:
                print(f"{Path(self.window.insp_file1).stem}: Simulator {idx} has collision object not defined in the base phyb.")
                self.report({'ERROR'}, f"{Path(self.window.insp_file1).stem}: Simulator {idx} has collision object not defined in the base phyb.")
                continue
            base_phyb.simulators.append(simulator)
        
        if not self.collision_check:
            base_phyb.to_file(str(Path(self.window.insp_file1).parent / "Result.phyb"))
        
        return {'FINISHED'}
    
class CompareOutput(Operator):
    bl_idname = "ya.compare_output"
    bl_label = "Inspect"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = "Compares an output of the base file with itself. Used to verify roundtrips"

    def execute(self, context):
        self.window = get_window_properties()
        original    = Path(self.window.insp_file1)
            
        phyb = PhybFile.from_file(self.window.insp_file1)

        temp_fd, temp_path = tempfile.mkstemp(prefix="CompareFile", suffix=original.suffix)
        try:
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(phyb.to_bytes())
            
            compare_binaries(self.window.insp_file1, temp_path)
            
        finally:
            os.unlink(temp_path)
        
        return {'FINISHED'}
    
    
CLASSES = [
    FileRoundtrip,
    PhybAppend,
    CompareOutput
]