import time
import traceback
import subprocess

from pathlib     import Path
from collections import deque

class YetAnotherLogger:
    SEPARATOR_LENGTH = 50         
    PROGRESS_BAR_LENGTH = 20        
    
    STANDARD_SEP_CHAR = "-"         
    ERROR_SEP_CHAR = "="            
    
    PROGRESS_FILLED_CHAR = "-"      
    PROGRESS_EMPTY_CHAR = " "       
    
    # Not in use because PowerShell doesn't allow fancy icons :(
    ERROR_ICON = "X"
    SUCCESS_ICON = "OK"  
    WARNING_ICON = "!"
    INFO_ICON = "i"
    
    def __init__(self, terminal_title="Yet Another Log", total=100, output_dir: Path=None, start_time: time=None) -> None:
        self.terminal_title    = terminal_title
        self.current_operation = "Waiting..."

        self.process    = None
        self.running    = False
        self.exception  = False
        self.warning    = False
        self.start_time = start_time
        self.output_dir = output_dir
        self.messages   = deque(maxlen=20)
        self.last_item  = None  # Stores the last processed item at the lowest level of detail. Used in final error output.
        self.total      = total  
        self.current    = 0      
        
    def start_terminal(self) -> None:
        """Start the Windows terminal using PowerShell"""
        if self.running:
            print("Terminal logger is already running.")
            return
        
        # self._create_log_file()

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 1 
            
            self.process = subprocess.Popen(
                ["powershell", "-NoExit", "-Command", "-"],
                stdin=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=startupinfo
            )
            
            self.running = True
            self.send_command("$WarningPreference = 'SilentlyContinue'")
            self.send_command(f"$host.ui.RawUI.WindowTitle = '{self.terminal_title}'")
            self.send_command(f"Clear-Host")
            # self.send_command(f"Get-Content -Path '{self.log_file.name}' -Tail 0 -Wait")
            
            time.sleep(1)
            self.refresh_display()
            
        except Exception as e:
            print(f"Error starting terminal: {e}")
            self.running = False
            raise 

    def send_command(self, command) -> bool:
        """Send a command to the terminal"""
        if not self.running or not self.process or not self.process.stdin:
            return False
            
        try:
            self.process.stdin.write(f'{command}\n')
            self.process.stdin.flush()
            return True
        except (BrokenPipeError, OSError) as e:
            print(f"Connection to terminal lost: {e}")
            self.running = False
            return False
    
    def refresh_display(self) -> None:
        self.send_command("Clear-Host")
        
    def _generate_progress_display(self, current: int, total: int) -> None:
        """Generate the progress bar display string"""
        if total <= 0:
            percentage = 0
        else:
            percentage = (current / total) * 100
            
        filled_length = int(percentage / 100 * self.PROGRESS_BAR_LENGTH)
        empty_length = self.PROGRESS_BAR_LENGTH - filled_length
        
        progress_bar = (self.PROGRESS_FILLED_CHAR * filled_length + 
                       self.PROGRESS_EMPTY_CHAR * empty_length)
        
        return f"{self.current_operation}: [{progress_bar}] {current}/{total}"
    
    def _time_estimate(self) -> None:
        if self.start_time:
            if self.current < 1:
                time_left = "| Estimating duration..."
            else:
                total_time   = time.time() - self.start_time 
                average_time = total_time / self.current
                estimate = int((self.total - self.current) * average_time)

            if estimate < 60:
                time_left = f"| ~{estimate} seconds"
            else:
                minutes = estimate / 60
                seconds = estimate % 60
                time_left = f"~{int(minutes)} min {int(seconds)} seconds"
            
            return time_left
        else:
            return ""
        
    def log(self, message: str, indent=0) -> None:
        """Write log to file"""
       
        if not self.running and not self.warning:
            self.warning = True
            print("Terminal not started. Call start_terminal() first.")
            return
        
        self.messages.append(f"{message}\n") 
        self.send_command(f"Write-Host '{' ' * indent}{message}'")
          
    def log_separator(self, char=None) -> None:
        char = char or self.STANDARD_SEP_CHAR
        self.log(char * self.SEPARATOR_LENGTH)
    
    def log_progress(self, current: int=None, temp_total: int=None, operation="Processing", time_estimate=True) -> None:
        """Log a progress bar - now updates the persistent progress display at top
        
        Args:
            current: Current progress count. If None, increments by 1. -1 will just reprint the main process' value.
            temp_total: Can be used to track a subprocess related to the main process.
        """
        if current is None:
            self.current += 1
            current = self.current
        elif current == -1:
            current = self.current

        if temp_total:
            total = temp_total
        else:
            total = self.total
        
        self.current_operation = operation

        time_estimate = f" {self._time_estimate()}" if time_estimate else ""

        message = self._generate_progress_display(current, total) + time_estimate
        
        self.refresh_display()
        self.log(message)
    
    def log_exception(self, message: str, indent: int) -> None:
        self.exception = True
        self.log(f"[ERROR]: {message}", indent)

    def save_log(self, error: str | Exception=None) -> str | None:
        if self.output_dir:
            with open(self.output_dir / "ya_error.log", "w") as log:
                log.writelines(self.messages)

                if error:
                    log.write(self.ERROR_SEP_CHAR * self.SEPARATOR_LENGTH + "\n")
                    
                    if isinstance(error, Exception):
                        traceback_text = "".join(
                            traceback.format_exception(
                                type(error), 
                                error, 
                                error.__traceback__
                                )
                            )
                        
                        log.write(traceback_text)
                    elif isinstance(error, str):
                        log.write(error)
            
            if self.last_item:
                log.write("LAST PROCESSED ITEM: \n")
                log.write(self.ERROR_SEP_CHAR * self.SEPARATOR_LENGTH + "\n")
                log.write(str(self.last_item) + "\n")

            return "ya_error.log"

    def close(self, error: str | Exception=None) -> None:
        """Close the terminal logger"""
        if not self.running:
            return
        
        if self.exception or error:
            self.save_log(error)
        
        try:
            if self.process:
                if self.process.stdin:
                    self.process.stdin.close()
                self.process.terminate()
                
        except Exception as e:
            print(f"Error during cleanup: {e}")

        finally:
            self.running = False
            # print("Terminal logger closed.")

