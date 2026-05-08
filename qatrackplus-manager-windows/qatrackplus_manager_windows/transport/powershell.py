import subprocess
import logging
from typing import List, Optional

class PowerShellTransport:
    """Handles execution of PowerShell commands locally on Windows."""

    def __init__(self):
        self.ps_exe = self._find_best_powershell()

    def _find_best_powershell(self) -> str:
        """Prefers pwsh.exe (PS 7+) over powershell.exe (PS 5.1)."""
        import shutil
        if shutil.which("pwsh"):
            return "pwsh"
        return "powershell.exe"

    def run(self, command: str, capture_output: bool = True, shell: bool = False, check: bool = True, log_errors: bool = True) -> subprocess.CompletedProcess:
        """Runs a PowerShell command, optionally streaming output to console."""
        full_command = [
            self.ps_exe,
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", command
        ]
        
        logging.debug(f"Executing PS: {command}")
        
        try:
            if not capture_output:
                # Stream directly to stdout/stderr
                result = subprocess.run(
                    full_command,
                    capture_output=False,
                    check=check
                )
                # Return a dummy completed process for compatibility
                return result
            
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if log_errors:
                logging.error(f"Command failed with exit code {e.returncode}")
                if capture_output:
                    logging.error(f"Stdout: {e.stdout}")
                    logging.error(f"Stderr: {e.stderr}")
            raise

    def get_service_status(self, service_name: str) -> str:
        """Returns the status of a Windows service."""
        try:
            result = self.run(f"(Get-Service '{service_name}').Status")
            return result.stdout.strip()
        except Exception:
            return "NotFound"

    def file_exists(self, path: str) -> bool:
        """Checks if a file or directory exists."""
        try:
            result = self.run(f"Test-Path '{path}'")
            return result.stdout.strip().lower() == "true"
        except Exception:
            return False
