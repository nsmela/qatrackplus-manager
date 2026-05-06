from __future__ import annotations
import requests
from .. import __version__

import os
GITHUB_API_URL = "https://api.github.com/repos/nsmela/qatrackplus-manager/commits/main"
SHA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "current_sha")

def check_for_updates() -> tuple[bool, str]:
    """
    Check if a newer commit is available on GitHub main branch.
    Returns (update_available, latest_sha).
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        latest_sha = data.get("sha", "")
        if not latest_sha:
            return False, ""
            
        current_sha = ""
        if os.path.exists(SHA_FILE):
            with open(SHA_FILE, "r") as f:
                current_sha = f.read().strip()
        
        return latest_sha != current_sha, latest_sha[:7]
            
    except Exception as e:
        raise RuntimeError(f"Could not verify version on GitHub: {str(e)}")
        
    return False, ""

