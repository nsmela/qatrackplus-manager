import subprocess
import logging
from typing import List, Optional

class PowerShellTransport:
    """Handles execution of PowerShell commands locally on Windows."""

    def run(self, command: str, capture_output: bool = True, shell: bool = False, check: bool = True, log_errors: bool = True) -> subprocess.CompletedProcess:
        """Runs a PowerShell command."""
        # Use a list for subprocess.run to handle quoting correctly
        full_command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-Command", command
        ]
        
        logging.debug(f"Executing PS: {command}")
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=capture_output,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if log_errors:
                logging.error(f"Command failed with exit code {e.returncode}")
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
