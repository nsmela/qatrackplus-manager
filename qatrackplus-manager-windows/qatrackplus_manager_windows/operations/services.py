from ..transport.powershell import PowerShellTransport
from typing import List, Dict

import json
import os

def get_qatrack_services(transport: PowerShellTransport) -> List[Dict[str, str]]:
    """Detects and returns status of QATrack+ related services including infra."""
    results = []
    
    # 1. Configured Database Check
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "setup_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
        
        server = config.get('db_server', 'Unknown')
        port = config.get('db_port', 0)
        db_type = config.get('db_type', 'Unknown')
        
        # Test ping
        ping_test = transport.run(f"Test-Connection -ComputerName {server} -Count 1 -Quiet", log_errors=False).stdout.strip()
        ping_status = "Responding" if ping_test == "True" else "No Response"
        
        status_text = f"{db_type} | {server}:{port} | {ping_status}"
        results.append({"name": "Database", "status": status_text, "is_virtual": True})
    else:
        results.append({"name": "Database", "status": "No configuration found", "is_virtual": True})

    # 2. Local Services (CherryPy, DjangoQ, IIS)
    potential_services = ["CherryPy", "DjangoQ", "QATrackPlus", "W3SVC"]
    for svc in potential_services:
        status = transport.get_service_status(svc)
        if status != "NotFound":
            display_name = "IIS (Web Server)" if svc == "W3SVC" else svc
            results.append({"name": display_name, "status": status})
            
    return results

def control_service(transport: PowerShellTransport, service_name: str, action: str):
    """Starts, stops, or restarts a service."""
    if action == "start":
        transport.run(f"Start-Service '{service_name}'")
    elif action == "stop":
        transport.run(f"Stop-Service '{service_name}'")
    elif action == "restart":
        transport.run(f"Restart-Service '{service_name}'")
    else:
        raise ValueError(f"Invalid service action: {action}")
