from pathlib             import Path
from bpy.types           import Operator, Context
from bpy.props           import StringProperty

from ..properties        import get_window_properties
from ..formats.phyb.file import PhybFile


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

class FileInspector(Operator):
    bl_idname = "ya.file_inspector"
    bl_label = "Inspect"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = "Prints a binary comparison of the two files"

    def execute(self, context):
        compare_binaries(
            get_window_properties().insp_file_first, 
            get_window_properties().insp_file_sec
            )
        
        return {'FINISHED'}
    
class PhybAppend(Operator):
    bl_idname = "ya.phyb_append"
    bl_label = "Inspect"
    bl_options = {"UNDO", "REGISTER"}
    bl_description = """Appends simulators from secondary to primary phyb.
Prints an error for every simulator that has undefined collision objects in the primary phyb.
Resulting phyb is written to the same folder as the secondary phyb"""

    def execute(self, context):
        self.window = get_window_properties()

        if not Path(self.window.insp_file_first).suffix == ".phyb" and Path(self.window.insp_file_first).suffix == ".phyb":
            self.window({'ERROR'}, "Please select phyb files.")
            return {'CANCELLED'}
            
        base_phyb = PhybFile.from_file(self.window.insp_file_first)
        sim_phyb  = PhybFile.from_file(self.window.insp_file_sec)
        collision_obj = base_phyb.get_collision_names()

        for idx, simulator in enumerate(sim_phyb.simulators):
            if not simulator.get_collision_names() <= collision_obj:
                print(f"{Path(self.window.insp_file_first).stem}: Simulator {idx} has collision object not defined in the base phyb.")
                continue
            base_phyb.simulators.append(simulator)
        
        base_phyb.to_file(str(Path(self.window.insp_file_first).parent / "AppendPhyb.phyb"))
        
        return {'FINISHED'}
    
    
CLASSES = [
    FileInspector,
    PhybAppend
]