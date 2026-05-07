from __future__ import annotations
import os
import shutil
import subprocess
import pathlib
import psutil
from typing import List, Optional, Tuple, Dict
from .base import Transport, CommandResult

class LocalTransport(Transport):

    def run(
        self,
        cmd: List[str],
        input: Optional[str] = None,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> CommandResult:
        try:
            # Merge with current environment so we don't lose PATH, etc.
            full_env = os.environ.copy()
            if env:
                full_env.update(env)

            result = subprocess.run(
                cmd,
                input=input,
                text=True,
                capture_output=True,
                env=full_env,
                cwd=cwd,
                check=False
            )

            return CommandResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
        except Exception as e:
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=str(e)
            )


    def run_as(self, user: str, cmd: List[str]) -> CommandResult:
        # Implementation of sudo -u USER
        sudo_cmd = ["sudo", "-u", user] + cmd
        return self.run(sudo_cmd)

    def read_file(self, path: str) -> str:
        return pathlib.Path(path).read_text()

    def write_file(self, path: str, content: str, mode: int = 0o644) -> None:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        os.chmod(path, mode)

    def file_exists(self, path: str) -> bool:
        return pathlib.Path(path).is_file()

    def dir_exists(self, path: str) -> bool:
        return pathlib.Path(path).is_dir()

    def make_dirs(self, path: str) -> None:
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    def list_files(self, path: str, pattern: str = "*") -> List[str]:
        p = pathlib.Path(path)
        return [str(f) for f in p.glob(pattern)]

    def file_size(self, path: str) -> int:
        return pathlib.Path(path).stat().st_size

    def service_active(self, name: str) -> bool:
        """Try systemctl first, fall back to process_running."""
        # Check systemctl
        res = self.run(["systemctl", "is-active", "--quiet", name])
        if res.succeeded:
            return True
        
        # Fallback to pgrep-like check via process_running
        return self.process_running(name)

    def process_running(self, name: str) -> bool:
        """Return True if a process with this name exists."""
        for proc in psutil.process_iter(['name']):
            try:
                if name.lower() in proc.info['name'].lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def port_pids(self, port: int) -> List[Tuple[int, str]]:
        """Return list of (pid, process_name) tuples listening on a port."""
        pids = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    pids.append((conn.pid, proc.name()))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pids.append((conn.pid, "unknown"))
        return pids
