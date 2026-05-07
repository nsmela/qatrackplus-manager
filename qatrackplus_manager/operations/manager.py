from __future__ import annotations
import sys
import os
import subprocess
from ..ui.console import console

GITHUB_URL = "https://github.com/nsmela/qatrackplus-manager.git"

def self_update():
    """
    Update the manager itself from GitHub and restart.
    """
    console.print("[yellow]Updating qatrackplus-manager...[/yellow]")
    
    # Identify the current venv's pip
    pip_bin = os.path.join(sys.prefix, "bin", "pip")
    if not os.path.exists(pip_bin):
        # Fallback for Windows or other layouts
        pip_bin = sys.executable.replace("python", "pip")

    try:
        # Run pip install upgrade
        subprocess.check_call([
            pip_bin, "install", "--upgrade", "--no-cache-dir",
            f"git+{GITHUB_URL}"
        ])


        
        # Save the new SHA
        from ..checks.version import GITHUB_API_URL, SHA_FILE
        import requests
        res = requests.get(GITHUB_API_URL, timeout=5)
        if res.status_code == 200:
            new_sha = res.json().get("sha")
            if new_sha:
                with open(SHA_FILE, "w") as f:
                    f.write(new_sha)

        console.print("[green]Update successful! Restarting...[/green]")
        
        # Restart the process
        os.execv(sys.executable, [sys.executable] + sys.argv)
        
    except Exception as e:
        console.print(f"[red]Update failed: {str(e)}[/red]")
        sys.exit(1)
