from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    @property
    def output(self) -> str:
        """Combined stdout + stderr for display."""
        return (self.stdout + self.stderr).strip()

class Transport(ABC):

    @abstractmethod
    def run(
        self,
        cmd: List[str],
        input: Optional[str] = None,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> CommandResult:
        """Run a command and return its result. Never raises on non-zero exit."""

    @abstractmethod
    def run_as(self, user: str, cmd: List[str]) -> CommandResult:
        """Run a command as a different user (sudo -u USER)."""

    @abstractmethod
    def read_file(self, path: str) -> str:
        """Read a text file. Raises FileNotFoundError if missing."""

    @abstractmethod
    def write_file(self, path: str, content: str, mode: int = 0o644) -> None:
        """Write a text file, creating parent directories."""

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Return True if the path exists."""

    @abstractmethod
    def dir_exists(self, path: str) -> bool:
        """Return True if the path is an existing directory."""

    @abstractmethod
    def make_dirs(self, path: str) -> None:
        """Create directories recursively (like mkdir -p)."""

    @abstractmethod
    def list_files(self, path: str, pattern: str = "*") -> List[str]:
        """List files matching a glob pattern under path."""

    @abstractmethod
    def file_size(self, path: str) -> int:
        """Return file size in bytes."""

    @abstractmethod
    def service_active(self, name: str) -> bool:
        """Return True if the named systemd service is active."""

    @abstractmethod
    def process_running(self, name: str) -> bool:
        """Return True if a process with this name exists (pgrep fallback)."""

    @abstractmethod
    def port_pids(self, port: int) -> List[Tuple[int, str]]:
        """Return list of (pid, process_name) tuples listening on a port."""
