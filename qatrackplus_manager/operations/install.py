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
    install_config: Dict[str, Any],
    status_callback: Optional[callable] = None
) -> None:
    """
    Perform the QA Track Plus installation.
    """
    def update_status(msg: str):
        if status_callback:
            status_callback(msg)

    app_dir = install_config['app_dir']
    app_user = install_config['app_user']
    release_url = install_config['release_url']
    db_type = state.db_type
    
    # 1. Save state immediately
    update_status("Saving initial configuration...")
    save_state(transport, app_dir, state)

    # 2. Install apt packages
    update_status("Installing system dependencies (apt)...")
    apt_pkgs = ["python3", "python3-pip", "python3-venv", "build-essential", "libpq-dev"]
    if db_type == 'mysql':
        apt_pkgs.append("libmysqlclient-dev")
    
    transport.run(["apt-get", "update", "-qq"])
    res = transport.run(["apt-get", "install", "-y", "-qq"] + apt_pkgs)
    if not res.succeeded:
        raise InstallError(f"Failed to install apt packages: {res.stderr}")

    # 3. Create app user if not exists
    update_status(f"Ensuring user '{app_user}' exists...")
    res = transport.run(["id", "-u", app_user])
    if not res.succeeded:
        transport.run(["useradd", "-m", "-s", "/bin/bash", app_user])

    # 4. Download and extract tarball
    update_status("Downloading and extracting QATrack+ source...")
    transport.make_dirs(app_dir)
    tmp_tar = "/tmp/qatrackplus.tar.gz"
    res = transport.run(["curl", "-L", "-o", tmp_tar, release_url])
    if not res.succeeded:
        raise InstallError(f"Failed to download release: {res.stderr}")
    
    res = transport.run(["tar", "-xzf", tmp_tar, "-C", app_dir, "--strip-components=1"])
    if not res.succeeded:
        raise InstallError(f"Failed to extract release: {res.stderr}")

    # 5. Create virtualenv
    update_status("Creating Python virtual environment...")
    venv_dir = os.path.join(app_dir, "venv")
    res = transport.run(["python3", "-m", "venv", venv_dir])
    if not res.succeeded:
        raise InstallError(f"Failed to create virtualenv: {res.stderr}")

    # 6. pip install --upgrade pip wheel
    pip_bin = os.path.join(venv_dir, "bin", "pip")
    transport.run([pip_bin, "install", "--upgrade", "pip", "wheel"])

    # 7. Install from requirements
    update_status("Installing Python dependencies (pip)... This may take a while.")
    req_source = find_requirements_file(transport, app_dir, db_type)
    if req_source:
        if req_source.mode == "requirements_txt":
            transport.run([pip_bin, "install", "-r", req_source.path])
        else:
            transport.run([pip_bin, "install", "."], cwd=app_dir)

    # 8. Install DB driver
    update_status(f"Installing database driver for {db_type}...")
    db_drivers = {
        'postgresql': 'psycopg2-binary',
        'mysql': 'mysqlclient',
        'mssql': 'mssql-django',
        'oracle': 'oracledb'
    }
    driver = db_drivers.get(db_type)
    if driver:
        transport.run([pip_bin, "install", driver])

    # 9. Detect version
    update_status("Detecting QATrack+ version...")
    major, ls_file, dj_settings = detect_qatrack_version(transport, app_dir)
    state.qatrack_version_major = major
    state.local_settings_file = ls_file
    state.django_settings = dj_settings
    
    # 10. Write local_settings.py (MUST BE BEFORE DEPENDENCY RESOLUTION)
    update_status("Configuring QATrack+ (local_settings.py)...")
    
    db_name = state.db_name
    if db_type == 'sqlite':
        db_name = os.path.join(app_dir, "db.sqlite3")

    ls_content = generate_local_settings(
        version_major=major,
        db_type=db_type,
        db_config={
            'name': db_name,
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


    # 11. Resolve dependencies loop
    update_status("Resolving missing dependencies...")
    python_bin = os.path.join(venv_dir, "bin", "python")
    resolve_missing_dependencies(transport, python_bin, dj_settings, app_dir)

    # 12. Run migrations
    update_status("Running database migrations...")
    env = {"DJANGO_SETTINGS_MODULE": dj_settings}

    res = transport.run([python_bin, "manage.py", "migrate", "--noinput"], env=env, cwd=app_dir)
    if not res.succeeded:
        raise MigrationError(f"Django migrations failed: {res.stderr}")

    # 12. Collectstatic
    update_status("Collecting static files...")
    transport.run([python_bin, "manage.py", "collectstatic", "--noinput"], env=env, cwd=app_dir)

    # 13. Install gunicorn and setup service
    update_status("Configuring Gunicorn service...")
    transport.run([pip_bin, "install", "gunicorn"])
    gm = GunicornManager(transport)
    gm.write_service_file(app_user, app_dir, venv_dir)

    # 14. Configure web server
    update_status(f"Configuring {state.web_server}...")
    wm = WebServerManager(transport, state.web_server)
    wm.start()

    # 15. Fix ownership
    update_status("Setting final file permissions...")
    transport.run(["chown", "-R", f"{app_user}:{app_user}", app_dir])
    
    # 16. Save final state
    update_status("Installation complete!")
    save_state(transport, app_dir, state)

