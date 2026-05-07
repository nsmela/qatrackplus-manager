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
    
    # App Service (Gunicorn)
    is_app = transport.service_active("qatrackplus")
    results.append(ScanResult(
        "Gunicorn service", 
        "ok" if is_app else "fail", 
        "Running" if is_app else "Stopped/Missing"
    ))

    # Web Server
    is_web = transport.service_active(state.web_server)
    results.append(ScanResult(
        f"{state.web_server.capitalize()} service", 
        "ok" if is_web else "fail", 
        "Running" if is_web else "Stopped"
    ))

    # Redis
    is_redis = transport.service_active("redis-server") or transport.service_active("redis")
    results.append(ScanResult(
        "Redis service", 
        "ok" if is_redis else "info", 
        "Running" if is_redis else "Not found"
    ))

    # RabbitMQ
    is_rabbitmq = transport.service_active("rabbitmq-server")
    results.append(ScanResult(
        "RabbitMQ service", 
        "ok" if is_rabbitmq else "info", 
        "Running" if is_rabbitmq else "Not found"
    ))
        
    return results


def scan_database_engines(transport: Transport, state: ManagerState) -> List[ScanResult]:
    results = []
    db_type = state.db_type
    
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
            
        detail = "Running" if is_active else "Not found/Stopped"
        results.append(ScanResult(label, status, detail))

    # 2. SQLite check
    app_dir = state.servers[0].app_dir
    sqlite_path = os.path.join(app_dir, "db.sqlite3")
    exists = transport.file_exists(sqlite_path)
    
    label = "SQLite Database"
    if db_type == 'sqlite':
        label += " [bold magenta](Configured)[/bold magenta]"
    
    if exists:
        results.append(ScanResult(label, "ok", f"File found at {sqlite_path}"))
    elif db_type == 'sqlite':
        results.append(ScanResult(label, "fail", "Configured but db.sqlite3 not found"))
    else:
        results.append(ScanResult(label, "info", "File not found"))

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
        scan_database_engines(transport, state),
        # ... other sections
    ]

