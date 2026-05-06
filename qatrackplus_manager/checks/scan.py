from __future__ import annotations
import os
from typing import List
from ..transport.base import Transport
from . import ScanResult
from ..config.models import ManagerState

def scan_existing_installation(transport: Transport, state: ManagerState) -> List[ScanResult]:
    results = []
    app_dir = state.servers[0].app_dir # Simplified
    
    if transport.dir_exists(app_dir):
        results.append(ScanResult("App directory", "ok", app_dir))
    else:
        results.append(ScanResult("App directory", "fail", f"Not found at {app_dir}"))

    manage_py = os.path.join(app_dir, "manage.py")
    if transport.file_exists(manage_py):
        results.append(ScanResult("manage.py", "ok", "Found"))
    else:
        results.append(ScanResult("manage.py", "warn", "Not found"))

    venv_dir = os.path.join(app_dir, "venv")
    if transport.dir_exists(venv_dir):
        results.append(ScanResult("Virtualenv", "ok", venv_dir))
    else:
        results.append(ScanResult("Virtualenv", "warn", "Missing"))
        
    return results

def scan_system_services(transport: Transport, state: ManagerState) -> List[ScanResult]:
    results = []
    
    # Gunicorn
    if transport.service_active("qatrackplus"):
        results.append(ScanResult("Gunicorn service", "ok", "Running"))
    else:
        results.append(ScanResult("Gunicorn service", "fail", "Stopped or missing"))

    # Web Server
    if transport.service_active(state.web_server):
        results.append(ScanResult(f"{state.web_server.capitalize()} service", "ok", "Running"))
    else:
        results.append(ScanResult(f"{state.web_server.capitalize()} service", "fail", "Stopped"))
        
    return results

def scan_configured_database(transport: Transport, state: ManagerState) -> List[ScanResult]:
    results = []
    db_type = state.db_type
    
    # Service check
    from ..services.database import get_database_engine
    db_config = {
        'host': state.db_host,
        'port': state.db_port,
        'name': state.db_name,
        'user': state.db_user
    }
    engine = get_database_engine(transport, db_type, db_config)
    svc = engine.get_service_name()
    
    if svc:
        if transport.service_active(svc):
            results.append(ScanResult(f"{db_type.capitalize()} service", "ok", "Running"))
        else:
            results.append(ScanResult(f"{db_type.capitalize()} service", "fail", "Stopped"))
    elif db_type == 'sqlite':
        results.append(ScanResult("SQLite", "ok", "Serverless"))

    # Mismatch check
    for other_db, other_svc in service_map.items():
        if other_db != db_type and transport.service_active(other_svc):
            results.append(ScanResult("DB Mismatch Warning", "warn", f"{other_db} is running but {db_type} is configured"))

    return results

def run_full_scan(transport: Transport, state: ManagerState) -> List[List[ScanResult]]:
    return [
        scan_existing_installation(transport, state),
        scan_system_services(transport, state),
        scan_configured_database(transport, state),
        # ... other sections
    ]
