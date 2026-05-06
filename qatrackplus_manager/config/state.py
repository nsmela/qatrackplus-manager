from __future__ import annotations
import os
import json
from .models import ManagerState, ServerEntry
from ..transport.base import Transport

STATE_FILE_NAME = ".manager_state.json"

def get_state_path(app_dir: str) -> str:
    return os.path.join(app_dir, STATE_FILE_NAME)

def load_state(transport: Transport, app_dir: str) -> ManagerState:
    path = get_state_path(app_dir)
    if transport.file_exists(path):
        try:
            content = transport.read_file(path)
            data = json.loads(content)
            
            # Reconstruct ServerEntry objects
            servers_data = data.pop("servers", [])
            servers = [ServerEntry(**s) for s in servers_data]
            
            return ManagerState(servers=servers, **data)
        except Exception:
            # Fallback to default if corrupted
            return ManagerState()
    
    # If file doesn't exist, return default state
    # Caller should run auto_detect
    return ManagerState()

def save_state(transport: Transport, app_dir: str, state: ManagerState) -> None:
    path = get_state_path(app_dir)
    
    # Convert dataclass to dict, handle ServerEntry list
    data = {k: v for k, v in state.__dict__.items() if k != "servers"}
    data["servers"] = [s.__dict__ for s in state.servers]
    
    content = json.dumps(data, indent=2)
    transport.write_file(path, content, mode=0o600)
