from __future__ import annotations
import os
import paramiko
import stat
import socket
from typing import List, Optional, Tuple, Dict
from .base import Transport, CommandResult
from ..exceptions import TransportError

class SSHTransport(Transport):
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def _connect(self):
        if self.client:
            return
        
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename,
                timeout=self.timeout
            )
        except Exception as e:
            raise TransportError(f"Failed to connect to {self.host}: {e}")

    @property
    def sftp(self) -> paramiko.SFTPClient:
        self._connect()
        if not self._sftp:
            self._sftp = self.client.open_sftp()
        return self._sftp

    def run(
        self,
        cmd: List[str],
        input: Optional[str] = None,
        env: Optional[dict] = None,
        cwd: Optional[str] = None,
    ) -> CommandResult:
        self._connect()
        full_cmd = " ".join(cmd)
        if cwd:
            full_cmd = f"cd {cwd} && {full_cmd}"
        
        if env:
            env_str = " ".join([f"{k}={v}" for k, v in env.items()])
            full_cmd = f"export {env_str} && {full_cmd}"

        stdin, stdout, stderr = self.client.exec_command(full_cmd, timeout=self.timeout)
        
        if input:
            stdin.write(input)
            stdin.flush()
            stdin.channel.shutdown_write()

        return CommandResult(
            exit_code=stdout.channel.recv_exit_status(),
            stdout=stdout.read().decode('utf-8'),
            stderr=stderr.read().decode('utf-8')
        )

    def run_as(self, user: str, cmd: List[str]) -> CommandResult:
        # Assuming passwordless sudo is configured
        sudo_cmd = ["sudo", "-u", user] + cmd
        return self.run(sudo_cmd)

    def read_file(self, path: str) -> str:
        with self.sftp.open(path, "r") as f:
            return f.read().decode('utf-8')

    def write_file(self, path: str, content: str, mode: int = 0o644) -> None:
        # Create parent directories
        self.make_dirs(os.path.dirname(path))
        with self.sftp.open(path, "w") as f:
            f.write(content)
        self.sftp.chmod(path, mode)

    def file_exists(self, path: str) -> bool:
        try:
            s = self.sftp.stat(path)
            return stat.S_ISREG(s.st_mode)
        except IOError:
            return False

    def dir_exists(self, path: str) -> bool:
        try:
            s = self.sftp.stat(path)
            return stat.S_ISDIR(s.st_mode)
        except IOError:
            return False

    def make_dirs(self, path: str) -> None:
        self.run(["mkdir", "-p", path])

    def list_files(self, path: str, pattern: str = "*") -> List[str]:
        # Using find for glob pattern support
        res = self.run(["find", path, "-maxdepth", "1", "-name", f"'{pattern}'"])
        if res.succeeded:
            return res.stdout.strip().split("\n")
        return []

    def file_size(self, path: str) -> int:
        return self.sftp.stat(path).st_size

    def service_active(self, name: str) -> bool:
        res = self.run(["systemctl", "is-active", "--quiet", name])
        if res.succeeded:
            return True
        return self.process_running(name)

    def process_running(self, name: str) -> bool:
        res = self.run(["pgrep", "-f", name])
        return res.succeeded

    def port_pids(self, port: int) -> List[Tuple[int, str]]:
        # Using ss on Linux to find listening ports
        res = self.run(["ss", "-tlnp", f"sport = :{port}"])
        pids = []
        if res.succeeded:
            # Parse output: LISTEN 0 128 0.0.0.0:80 0.0.0.0:* users:(("nginx",pid=1234,fd=6))
            import re
            matches = re.findall(r'users:\(\("([^"]+)",pid=(\d+)', res.stdout)
            for name, pid in matches:
                pids.append((int(pid), name))
        return pids

    def __del__(self):
        if self._sftp:
            self._sftp.close()
        if self.client:
            self.client.close()
