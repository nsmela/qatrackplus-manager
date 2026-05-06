from __future__ import annotations
from typing import List, Optional
from ..transport.base import Transport, CommandResult

class DatabaseManager:
    def __init__(self, transport: Transport, db_type: str, db_config: dict):
        self.transport = transport
        self.db_type = db_type
        self.db_config = db_config

    def check_service(self) -> bool:
        service_map = {
            'postgresql': 'postgresql',
            'mysql': 'mysql',
            'mssql': 'mssql-server'
        }
        name = service_map.get(self.db_type)
        if name:
            return self.transport.service_active(name)
        return True # SQLite etc.

    def run_query(self, query: str) -> CommandResult:
        if self.db_type == 'postgresql':
            env = {'PGPASSWORD': self.db_config.get('password', '')}
            cmd = [
                "psql", "-h", self.db_config.get('host', 'localhost'),
                "-p", self.db_config.get('port', '5432'),
                "-U", self.db_config.get('user', 'qatrack'),
                "-d", self.db_config.get('name', 'qatrackplus'),
                "-c", query
            ]
            return self.transport.run(cmd, env=env)
        
        elif self.db_type == 'mysql':
            cmd = [
                "mysql", "-h", self.db_config.get('host', 'localhost'),
                "-P", self.db_config.get('port', '3306'),
                "-u", self.db_config.get('user', 'qatrack'),
                f"-p{self.db_config.get('password', '')}",
                "-e", query, self.db_config.get('name', 'qatrackplus')
            ]
            return self.transport.run(cmd)
            
        elif self.db_type == 'sqlite':
            # Simplified sqlite check
            path = self.db_config.get('name', 'qatrackplus.sqlite3')
            cmd = ["sqlite3", path, query]
            return self.transport.run(cmd)
            
        return CommandResult(-1, "", "Unsupported DB type for direct query")

    def dump(self, output_path: str) -> CommandResult:
        if self.db_type == 'postgresql':
            env = {'PGPASSWORD': self.db_config.get('password', '')}
            cmd = [
                "pg_dump", "-Fc",
                "-h", self.db_config.get('host', 'localhost'),
                "-p", self.db_config.get('port', '5432'),
                "-U", self.db_config.get('user', 'qatrack'),
                self.db_config.get('name', 'qatrackplus')
            ]
            # Need to handle stdout redirecting to file. 
            # In LocalTransport/SSHTransport, we might need a way to redirect or write to file directly.
            # The instructions say: "pg_dump stdout must never be mixed with log output. Write directly to a file path".
            # I'll modify the run command to support redirection or just use > in the shell string if I was using a shell.
            # But I'm using List[str]. 
            # I'll add a 'redirect_stdout' to the transport or just handle it here if I can.
            # Actually, I'll use the transport's 'run' with a shell-like command if needed, or implement it in transport.
            # For now, let's assume the transport can handle it or I'll use a temporary approach.
            pass
            
        return CommandResult(-1, "", "Not implemented")
