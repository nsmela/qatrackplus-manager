from __future__ import annotations
import re
from typing import Optional, Dict, Tuple
from ..transport.base import Transport
from .models import ManagerState

def detect_qatrack_version(transport: Transport, app_dir: str) -> Tuple[int, str, str]:
    """
    Returns (major_version, local_settings_path, django_settings_module)
    """
    settings_py = f"{app_dir}/qatrack/settings.py"
    settings_dir = f"{app_dir}/qatrack/settings"
    
    # 1. If qatrack/settings.py exists AND contains "from .local_settings import"
    if transport.file_exists(settings_py):
        content = transport.read_file(settings_py)
        if "from .local_settings import" in content or "from qatrack.local_settings import" in content:
            return 4, f"{app_dir}/qatrack/local_settings.py", "qatrack.settings"

    # 2. If qatrack/settings/ is a directory
    if transport.dir_exists(settings_dir):
        return 3, f"{app_dir}/qatrack/settings/local_settings.py", "qatrack.settings.local_settings"

    # 3. If qatrack/local_settings.py exists
    if transport.file_exists(f"{app_dir}/qatrack/local_settings.py"):
        return 4, f"{app_dir}/qatrack/local_settings.py", "qatrack.settings"

    # 4. If qatrack/settings/local_settings.py exists
    if transport.file_exists(f"{app_dir}/qatrack/settings/local_settings.py"):
        return 3, f"{app_dir}/qatrack/settings/local_settings.py", "qatrack.settings.local_settings"

    # 5. If qatrack/settings.py exists (but didn't match above)
    if transport.file_exists(settings_py):
        return 4, f"{app_dir}/qatrack/local_settings.py", "qatrack.settings"

    # 6. Default
    return 3, f"{app_dir}/qatrack/settings/local_settings.py", "qatrack.settings.local_settings"

def detect_db_from_settings(transport: Transport, local_settings_path: str) -> Optional[Dict[str, str]]:
    if not transport.file_exists(local_settings_path):
        return None
    
    content = transport.read_file(local_settings_path)
    
    db_config = {}
    
    patterns = {
        'engine': r"'ENGINE':\s*'([^']+)'",
        'name': r"'NAME':\s*'([^']+)'",
        'user': r"'USER':\s*'([^']+)'",
        'host': r"'HOST':\s*'([^']+)'",
        'port': r"'PORT':\s*'([^']+)'",
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            val = match.group(1)
            if key == 'engine':
                if 'postgresql' in val: db_config['db_type'] = 'postgresql'
                elif 'mysql' in val: db_config['db_type'] = 'mysql'
                elif 'sqlite3' in val: db_config['db_type'] = 'sqlite'
                elif 'mssql' in val or 'sql_server' in val: db_config['db_type'] = 'mssql'
                elif 'oracle' in val: db_config['db_type'] = 'oracle'
            else:
                db_config[f'db_{key}'] = val

    return db_config if db_config else None

def detect_db_from_services(transport: Transport) -> Optional[str]:
    # SQLite file exists at known path
    # We don't know the app_dir here easily without passing it, but usually /opt/qatrackplus
    # Let's assume common paths or skip if uncertain. 
    # Actually, the instructions say "Priority order".
    
    if transport.service_active("mssql-server"):
        return "mssql"
    if transport.service_active("postgresql"):
        return "postgresql"
    if transport.service_active("mariadb") or transport.service_active("mysql"):
        return "mysql"
    
    # Check for client commands
    res = transport.run(["sqlplus", "-V"])
    if res.exit_code == 0 or "sqlplus" in res.output.lower():
        return "oracle"
    
    res = transport.run(["psql", "--version"])
    if res.exit_code == 0:
        return "postgresql"
    
    res = transport.run(["mysql", "--version"])
    if res.exit_code == 0:
        return "mysql"
        
    return None

def auto_detect(transport: Transport, state: ManagerState) -> ManagerState:
    # Use current active server app_dir
    app_dir = state.servers[0].app_dir # Simplified for now
    for s in state.servers:
        if s.name == state.active_server:
            app_dir = s.app_dir
            break

    major, path, module = detect_qatrack_version(transport, app_dir)
    state.qatrack_version_major = major
    state.local_settings_file = path
    state.django_settings = module
    
    db_settings = detect_db_from_settings(transport, path)
    if db_settings:
        for k, v in db_settings.items():
            setattr(state, k, v)
    else:
        db_type = detect_db_from_services(transport)
        if db_type:
            state.db_type = db_type
            
    return state
