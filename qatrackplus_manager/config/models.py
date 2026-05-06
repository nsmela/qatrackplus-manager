from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ServerEntry:
    name: str
    host: str  # "localhost" for local mode
    ssh_user: Optional[str] = None  # None = local mode
    ssh_port: int = 22
    ssh_key: Optional[str] = None
    app_dir: str = "/opt/qatrackplus"
    app_user: str = "qatrack"

@dataclass
class ManagerState:
    # Active server
    active_server: str = "local"
    servers: List[ServerEntry] = field(default_factory=lambda: [
        ServerEntry(name="local", host="localhost")
    ])

    # Installation config (per server — but stored flat for now)
    db_type: str = "postgresql"  # postgresql | mysql | sqlite | mssql | oracle
    db_host: str = "localhost"
    db_port: str = ""
    db_name: str = "qatrackplus"
    db_user: str = "qatrack"
    web_server: str = "nginx"  # nginx | apache

    # Auto-detected (written after install or detection)
    qatrack_version_major: int = 3
    local_settings_file: str = ""
    django_settings: str = ""
