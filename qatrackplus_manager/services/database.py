from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from ..transport.base import Transport, CommandResult

class DatabaseEngine(ABC):
    def __init__(self, transport: Transport, db_config: Dict[str, str]):
        self.transport = transport
        self.db_config = db_config

    @abstractmethod
    def get_service_name(self) -> str:
        """Return the systemd service name."""

    @abstractmethod
    def get_client_command(self) -> str:
        """Return the primary client command (psql, mysql, etc.)."""

    @abstractmethod
    def test_connection(self) -> CommandResult:
        """Test the connection as the app user."""

    @abstractmethod
    def dump(self, output_path: str) -> CommandResult:
        """Perform a database dump to the specified path."""

    @abstractmethod
    def restore(self, input_path: str) -> CommandResult:
        """Restore the database from the specified path."""

class PostgresEngine(DatabaseEngine):
    def get_service_name(self) -> str:
        return "postgresql"

    def get_client_command(self) -> str:
        return "psql"

    def test_connection(self) -> CommandResult:
        env = {'PGPASSWORD': self.db_config.get('password', '')}
        cmd = [
            "psql", "-h", self.db_config.get('host', 'localhost'),
            "-p", self.db_config.get('port', '5432'),
            "-U", self.db_config.get('user', 'qatrack'),
            "-d", self.db_config.get('name', 'qatrackplus'),
            "-c", "SELECT 1;"
        ]
        return self.transport.run(cmd, env=env)

    def dump(self, output_path: str) -> CommandResult:
        env = {'PGPASSWORD': self.db_config.get('password', '')}
        cmd = [
            "pg_dump", "-Fc",
            "-h", self.db_config.get('host', 'localhost'),
            "-p", self.db_config.get('port', '5432'),
            "-U", self.db_config.get('user', 'qatrack'),
            "-f", output_path,
            self.db_config.get('name', 'qatrackplus')
        ]
        return self.transport.run(cmd, env=env)

    def restore(self, input_path: str) -> CommandResult:
        env = {'PGPASSWORD': self.db_config.get('password', '')}
        db_name = self.db_config.get('name', 'qatrackplus')
        # Recreate DB first
        self.transport.run(["dropdb", "-h", self.db_config.get('host'), "-U", self.db_config.get('user'), db_name], env=env)
        self.transport.run(["createdb", "-h", self.db_config.get('host'), "-U", self.db_config.get('user'), db_name], env=env)
        
        cmd = [
            "pg_restore", "-d", db_name,
            "-h", self.db_config.get('host'), "-U", self.db_config.get('user'),
            input_path
        ]
        return self.transport.run(cmd, env=env)

class MysqlEngine(DatabaseEngine):
    def get_service_name(self) -> str:
        return "mysql"

    def get_client_command(self) -> str:
        return "mysql"

    def test_connection(self) -> CommandResult:
        cmd = [
            "mysql", "-h", self.db_config.get('host', 'localhost'),
            "-P", self.db_config.get('port', '3306'),
            "-u", self.db_config.get('user', 'qatrack'),
            f"-p{self.db_config.get('password', '')}",
            "-e", "SELECT 1;", self.db_config.get('name', 'qatrackplus')
        ]
        return self.transport.run(cmd)

    def dump(self, output_path: str) -> CommandResult:
        cmd = [
            "mysqldump", "--single-transaction",
            "-h", self.db_config.get('host', 'localhost'),
            "-P", self.db_config.get('port', '3306'),
            "-u", self.db_config.get('user', 'qatrack'),
            f"-p{self.db_config.get('password', '')}",
            f"--result-file={output_path}",
            self.db_config.get('name', 'qatrackplus')
        ]
        return self.transport.run(cmd)

    def restore(self, input_path: str) -> CommandResult:
        # Implementation using mysql client to source the file
        cmd = [
            "mysql", "-h", self.db_config.get('host', 'localhost'),
            "-P", self.db_config.get('port', '3306'),
            "-u", self.db_config.get('user', 'qatrack'),
            f"-p{self.db_config.get('password', '')}",
            self.db_config.get('name', 'qatrackplus'),
            "-e", f"source {input_path}"
        ]
        return self.transport.run(cmd)

class SqliteEngine(DatabaseEngine):
    def get_service_name(self) -> str:
        return "" # No service for SQLite

    def get_client_command(self) -> str:
        return "sqlite3"

    def test_connection(self) -> CommandResult:
        path = self.db_config.get('name', 'qatrackplus.sqlite3')
        return self.transport.run(["sqlite3", path, "PRAGMA integrity_check;"])

    def dump(self, output_path: str) -> CommandResult:
        path = self.db_config.get('name', 'qatrackplus.sqlite3')
        return self.transport.run(["cp", path, output_path])

    def restore(self, input_path: str) -> CommandResult:
        path = self.db_config.get('name', 'qatrackplus.sqlite3')
        return self.transport.run(["cp", input_path, path])

class MssqlEngine(DatabaseEngine):
    def get_service_name(self) -> str:
        return "mssql-server"

    def get_client_command(self) -> str:
        return "sqlcmd"

    def test_connection(self) -> CommandResult:
        cmd = [
            "sqlcmd", "-S", f"{self.db_config.get('host', 'localhost')},{self.db_config.get('port', '1433')}",
            "-U", self.db_config.get('user', 'qatrack'),
            "-P", self.db_config.get('password', ''),
            "-Q", "SELECT 1;"
        ]
        return self.transport.run(cmd)

    def dump(self, output_path: str) -> CommandResult:
        # MSSQL backups are usually done via T-SQL command
        db_name = self.db_config.get('name', 'qatrackplus')
        query = f"BACKUP DATABASE [{db_name}] TO DISK = '{output_path}' WITH FORMAT, MEDIANAME = 'QATrackBackup', NAME = 'Full Backup of {db_name}';"
        cmd = [
            "sqlcmd", "-S", f"{self.db_config.get('host', 'localhost')},{self.db_config.get('port', '1433')}",
            "-U", self.db_config.get('user', 'sa'), # Usually needs SA for backup
            "-P", self.db_config.get('password', ''),
            "-Q", query
        ]
        return self.transport.run(cmd)

    def restore(self, input_path: str) -> CommandResult:
        db_name = self.db_config.get('name', 'qatrackplus')
        query = f"RESTORE DATABASE [{db_name}] FROM DISK = '{input_path}' WITH REPLACE;"
        cmd = [
            "sqlcmd", "-S", f"{self.db_config.get('host', 'localhost')},{self.db_config.get('port', '1433')}",
            "-U", self.db_config.get('user', 'sa'),
            "-P", self.db_config.get('password', ''),
            "-Q", query
        ]
        return self.transport.run(cmd)

def get_database_engine(transport: Transport, db_type: str, db_config: Dict[str, str]) -> DatabaseEngine:
    if db_type == 'postgresql':
        return PostgresEngine(transport, db_config)
    elif db_type == 'mysql':
        return MysqlEngine(transport, db_config)
    elif db_type == 'sqlite':
        return SqliteEngine(transport, db_config)
    elif db_type == 'mssql':
        return MssqlEngine(transport, db_config)
    
    raise ValueError(f"Unsupported database type: {db_type}")
