from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from ..transport.base import Transport
from ..exceptions import DependencyError

@dataclass
class RequirementsSource:
    mode: str  # "requirements_txt" | "pip_install_dot"
    path: Optional[str] = None

def _requirements_file_usable(transport: Transport, path: str) -> bool:
    if not transport.file_exists(path):
        return False
    
    content = transport.read_file(path)
    base_dir = os.path.dirname(path)
    
    for line in content.splitlines():
        line = line.strip()
        if line.startswith(("-r", "--requirement")):
            # Extract included file
            parts = line.split()
            if len(parts) > 1:
                inc = parts[1]
                if not inc.startswith("/"):
                    inc = os.path.join(base_dir, inc)
                if not transport.file_exists(inc):
                    return False
    return True

def find_requirements_file(transport: Transport, app_dir: str, db_type: str) -> Optional[RequirementsSource]:
    """
    Locate a usable requirements file.
    """
    
    # 1. DB-specific file
    db_map = {
        'postgresql': 'postgres.txt',
        'mysql': 'mysql.txt',
        'sqlite': 'sqlite.txt'
    }
    db_file = db_map.get(db_type)
    if db_file:
        path = os.path.join(app_dir, "requirements", db_file)
        if _requirements_file_usable(transport, path):
            return RequirementsSource(mode="requirements_txt", path=path)

    # 2. Fallback candidates
    candidates = [
        "requirements/base.txt",
        "requirements/requirements.txt",
        "requirements/production.txt",
        "requirements/common.txt",
        "requirements/app.txt",
        "requirements.txt" # Risk of Docker one, but we'll validate
    ]
    
    for c in candidates:
        path = os.path.join(app_dir, c)
        if _requirements_file_usable(transport, path):
            # Skip root requirements.txt if it's the Docker one (usually contains -r docker.txt)
            if c == "requirements.txt":
                content = transport.read_file(path)
                if "-r docker.txt" in content:
                    continue
            return RequirementsSource(mode="requirements_txt", path=path)

    # 3. pyproject.toml
    if transport.file_exists(os.path.join(app_dir, "pyproject.toml")):
        return RequirementsSource(mode="pip_install_dot")
    
    if transport.file_exists(os.path.join(app_dir, "setup.py")):
        return RequirementsSource(mode="pip_install_dot")

    return None

def resolve_missing_dependencies(
    transport: Transport,
    venv_python: str,
    django_settings: str,
    app_dir: str,
    max_attempts: int = 15,
) -> List[str]:
    """
    Repeatedly try to run django.setup() and install any missing module.
    """
    installed = []
    
    for attempt in range(max_attempts):
        # Run django setup check
        cmd = [
            venv_python, "-c",
            f"import os; import django; os.environ['DJANGO_SETTINGS_MODULE']='{django_settings}'; django.setup()"
        ]
        res = transport.run(cmd, cwd=app_dir)
        
        if res.succeeded:
            return installed
        
        # Parse ModuleNotFoundError: No module named 'X'
        match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", res.stderr)
        if not match:
            # If it's not a ModuleNotFoundError, we can't resolve it here
            raise DependencyError(f"Django setup failed with non-import error: {res.stderr}")
            
        module_name = match.group(1)
        # Convert X to pip package name: replace _ with -
        package_name = module_name.replace("_", "-")
        
        # Run pip install
        pip_cmd = [os.path.dirname(venv_python) + "/pip", "install", package_name]
        pip_res = transport.run(pip_cmd)
        
        if not pip_res.succeeded:
            raise DependencyError(
                f"Failed to install dependency '{package_name}' for module '{module_name}'. "
                f"Error: {pip_res.stderr}\nTry installing it manually."
            )
            
        installed.append(package_name)
        
    raise DependencyError(f"Exceeded max attempts ({max_attempts}) to resolve dependencies.")
