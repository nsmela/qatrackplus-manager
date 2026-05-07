from __future__ import annotations
from ..transport.base import Transport
from .backup import backup
from .install import install
from ..config.models import ManagerState
from ..config.detect import detect_full_settings_from_file

def upgrade(
    transport: Transport,
    state: ManagerState,
    upgrade_config: dict,
    status_callback: Optional[callable] = None
) -> None:
    """
    Perform an upgrade by backing up and re-running installation with new source.
    """
    def update_status(msg):
        if status_callback:
            status_callback(msg)

    app_dir = upgrade_config['app_dir']
    
    # 1. Detect current settings to preserve them
    update_status("Detecting existing configuration...")
    current_settings = detect_full_settings_from_file(transport, state.local_settings_file)
    
    # Merge detected settings into upgrade_config
    if 'db_password' not in upgrade_config or not upgrade_config['db_password']:
        upgrade_config['db_password'] = current_settings.get('db_password', '')
    
    if 'secret_key' not in upgrade_config or not upgrade_config['secret_key']:
        upgrade_config['secret_key'] = current_settings.get('secret_key', '')
        
    if 'allowed_hosts' not in upgrade_config or not upgrade_config['allowed_hosts']:
        upgrade_config['allowed_hosts'] = current_settings.get('allowed_hosts', ['localhost'])

    # 2. Auto-backup
    update_status(f"Creating pre-upgrade backup in {upgrade_config['backup_dir']}...")
    backup_path = backup(
        transport,
        app_dir,
        upgrade_config['backup_dir'],
        state.db_type,
        {
            'name': state.db_name,
            'user': state.db_user,
            'host': state.db_host,
            'port': state.db_port,
            'password': upgrade_config['db_password']
        },
        label=f"pre-upgrade"
    )
    update_status(f"Backup created: {backup_path}")
    
    # 3. Re-run install with the new release URL
    # install() will handle extraction, venv, migrations, etc.
    install(transport, state, upgrade_config, status_callback=status_callback)

