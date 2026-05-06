from __future__ import annotations
from typing import List, Dict

def generate_local_settings(
    version_major: int,
    db_type: str,
    db_config: Dict[str, str],
    secret_key: str,
    allowed_hosts: List[str],
    static_root: str,
    media_root: str,
) -> str:
    """
    Generate local_settings.py content.
    """
    
    # Map db_type to Django ENGINE
    engines = {
        'postgresql': 'django.db.backends.postgresql',
        'mysql': 'django.db.backends.mysql',
        'sqlite': 'django.db.backends.sqlite3',
        'mssql': 'mssql',
        'oracle': 'django.db.backends.oracle',
    }
    
    engine = engines.get(db_type, 'django.db.backends.postgresql')
    
    lines = [
        "# QA Track Plus local settings — managed by qatrackplus-manager",
    ]
    
    if version_major == 3:
        lines.append("from .base import *")
    else:
        # v4: NO from .base import * — settings.py already has the base
        lines.append("# (v4: base settings are imported by the main settings.py)")

    lines.extend([
        "",
        f"SECRET_KEY = '{secret_key}'",
        f"ALLOWED_HOSTS = {allowed_hosts}",
        "",
        "DATABASES = {",
        "    'default': {",
        f"        'ENGINE': '{engine}',",
        f"        'NAME': '{db_config.get('name', 'qatrackplus')}',",
        f"        'USER': '{db_config.get('user', 'qatrack')}',",
        f"        'PASSWORD': '{db_config.get('password', '')}',",
        f"        'HOST': '{db_config.get('host', 'localhost')}',",
        f"        'PORT': '{db_config.get('port', '')}',",
        "    }",
        "}",
        "",
        f"STATIC_ROOT = '{static_root}'",
        f"MEDIA_ROOT = '{media_root}'",
    ])
    
    return "\n".join(lines) + "\n"
