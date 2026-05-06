from __future__ import annotations
from ..transport.base import Transport
from .backup import backup
from .install import install
from ..config.models import ManagerState

def upgrade(
    transport: Transport,
    state: ManagerState,
    upgrade_config: dict
) -> None:
    # 1. Auto-backup
    backup(
        transport,
        upgrade_config['app_dir'],
        upgrade_config['backup_dir'],
        state.db_type,
        upgrade_config['db_config'],
        label=f"pre-upgrade-{state.qatrack_version_major}"
    )
    
    # 2. Re-run install with the new release URL
    install(transport, state, upgrade_config)
