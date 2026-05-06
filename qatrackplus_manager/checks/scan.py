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

    # 1. Check all supported SQL engines
    from ..services.database import get_database_engine
    supported_types = ['postgresql', 'mysql', 'mssql']
    
    for t in supported_types:
        engine = get_database_engine(transport, t, {})
        svc = engine.get_service_name()
        is_active = transport.service_active(svc)
        
        status = "ok" if is_active else "info"
        # If this is the configured DB but it's down, mark as fail
        if t == db_type and not is_active:
            status = "fail"
            
        label = f"{t.capitalize()} Service"
        if t == db_type:
            label += " [bold magenta](Configured)[/bold magenta]"
            
        detail = "Running" if is_active else "Stopped"
        results.append(ScanResult(label, status, detail))

    # 2. SQLite check (if configured)
    if db_type == 'sqlite':
        results.append(ScanResult("SQLite [bold magenta](Configured)[/bold magenta]", "ok", "Serverless"))

    # 3. Mismatch check: warn if more than one engine is running
    running = []
    for t in supported_types:
        engine = get_database_engine(transport, t, {})
        if transport.service_active(engine.get_service_name()):
            running.append(t)
            
    if len(running) > 1:
        results.append(ScanResult(
            "Multiple DB Engines", 
            "warn", 
            f"Caution: {', '.join(running)} are all running."
        ))

    return results

def run_full_scan(transport: Transport, state: ManagerState) -> List[List[ScanResult]]:
    return [
        scan_existing_installation(transport, state),
        scan_system_services(transport, state),
        scan_configured_database(transport, state),
        # ... other sections
    ]
