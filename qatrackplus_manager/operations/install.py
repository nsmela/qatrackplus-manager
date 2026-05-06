from __future__ import annotations
import os
import time
from typing import Dict, Any, List
from ..transport.base import Transport
from ..exceptions import InstallError, MigrationError
from ..config.models import ManagerState
from ..config.state import save_state
from ..config.detect import detect_qatrack_version
from ..config.settings_writer import generate_local_settings
from .dependencies import find_requirements_file, resolve_missing_dependencies
from ..services.gunicorn import GunicornManager
from ..services.web_server import WebServerManager

def install(
    transport: Transport,
    state: ManagerState,
    install_config: Dict[str, Any]
) -> None:
    """
    Perform the QA Track Plus installation.
    """
    app_dir = install_config['app_dir']
    app_user = install_config['app_user']
    release_url = install_config['release_url']
    db_type = state.db_type
    
    # 1. Save state immediately
    save_state(transport, app_dir, state)

    # 2. Install apt packages
    apt_pkgs = ["python3", "python3-pip", "python3-venv", "build-essential", "libpq-dev"]
    if db_type == 'mysql':
        apt_pkgs.append("libmysqlclient-dev")
    
    res = transport.run(["apt-get", "update", "-qq"])
    res = transport.run(["apt-get", "install", "-y", "-qq"] + apt_pkgs)
    if not res.succeeded:
        raise InstallError(f"Failed to install apt packages: {res.stderr}")

    # 3. Create app user if not exists
    res = transport.run(["id", "-u", app_user])
    if not res.succeeded:
        transport.run(["useradd", "-m", "-s", "/bin/bash", app_user])

    # 4. Download and extract tarball
    transport.make_dirs(app_dir)
    tmp_tar = "/tmp/qatrackplus.tar.gz"
    res = transport.run(["curl", "-L", "-o", tmp_tar, release_url])
    if not res.succeeded:
        raise InstallError(f"Failed to download release: {res.stderr}")
    
    res = transport.run(["tar", "-xzf", tmp_tar, "-C", app_dir, "--strip-components=1"])
    if not res.succeeded:
        raise InstallError(f"Failed to extract release: {res.stderr}")

    # 5. Create virtualenv
    venv_dir = os.path.join(app_dir, "venv")
    res = transport.run(["python3", "-m", "venv", venv_dir])
    if not res.succeeded:
        raise InstallError(f"Failed to create virtualenv: {res.stderr}")

    # 6. pip install --upgrade pip wheel
    pip_bin = os.path.join(venv_dir, "bin", "pip")
    transport.run([pip_bin, "install", "--upgrade", "pip", "wheel"])

    # 7. Install from requirements
    req_source = find_requirements_file(transport, app_dir, db_type)
    if req_source:
        if req_source.mode == "requirements_txt":
            transport.run([pip_bin, "install", "-r", req_source.path])
        else:
            transport.run([pip_bin, "install", "."], cwd=app_dir)

    # 8. Install DB driver
    db_drivers = {
        'postgresql': 'psycopg2-binary',
        'mysql': 'mysqlclient',
        'mssql': 'mssql-django',
        'oracle': 'oracledb'
    }
    driver = db_drivers.get(db_type)
    if driver:
        transport.run([pip_bin, "install", driver])

    # 9. Detect version and resolve dependencies loop
    major, ls_file, dj_settings = detect_qatrack_version(transport, app_dir)
    state.qatrack_version_major = major
    state.local_settings_file = ls_file
    state.django_settings = dj_settings
    
    python_bin = os.path.join(venv_dir, "bin", "python")
    resolve_missing_dependencies(transport, python_bin, dj_settings, app_dir)

    # 10. Write local_settings.py
    ls_content = generate_local_settings(
        version_major=major,
        db_type=db_type,
        db_config={
            'name': state.db_name,
            'user': state.db_user,
            'password': install_config['db_password'],
            'host': state.db_host,
            'port': state.db_port
        },
        secret_key=install_config['secret_key'],
        allowed_hosts=install_config['allowed_hosts'],
        static_root=os.path.join(app_dir, "static"),
        media_root=os.path.join(app_dir, "media")
    )
    transport.write_file(ls_file, ls_content)

    # 11. Run migrations
    env = {"DJANGO_SETTINGS_MODULE": dj_settings}
    res = transport.run([python_bin, "manage.py", "migrate", "--noinput"], env=env, cwd=app_dir)
    if not res.succeeded:
        raise MigrationError(f"Django migrations failed: {res.stderr}")

    # 12. Collectstatic
    transport.run([python_bin, "manage.py", "collectstatic", "--noinput"], env=env, cwd=app_dir)

    # 13. Install gunicorn and setup service
    transport.run([pip_bin, "install", "gunicorn"])
    gm = GunicornManager(transport)
    gm.write_service_file(app_user, app_dir, venv_dir)

    # 14. Configure web server
    wm = WebServerManager(transport, state.web_server)
    # (Apache/Nginx config logic would go here)
    # ...
    wm.start()

    # 15. Fix ownership
    transport.run(["chown", "-R", f"{app_user}:{app_user}", app_dir])
    
    # 16. Save final state
    save_state(transport, app_dir, state)
