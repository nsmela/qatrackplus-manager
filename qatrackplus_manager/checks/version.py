from __future__ import annotations
import requests
from .. import __version__

GITHUB_API_URL = "https://api.github.com/repos/nsmela/qatrackplus-manager/releases/latest"

def check_for_updates() -> tuple[bool, str]:
    """
    Check if a newer version of the manager is available on GitHub.
    Returns (update_available, latest_version).
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        latest_version = data.get("tag_name", "").lstrip("v")
        if not latest_version:
            return False, ""
            
        from packaging.version import parse
        if parse(latest_version) > parse(__version__):
            return True, latest_version
            
    except Exception as e:
        raise RuntimeError(f"Could not verify version on GitHub: {str(e)}")
        
    return False, ""
