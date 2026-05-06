#!/usr/bin/env bash
set -euo pipefail

MANAGER_VENV="/opt/qatrackplus-manager-venv"
GITHUB_URL="https://github.com/nsmela/qatrackplus-manager"

# 1. Check root
[[ "${EUID}" -eq 0 ]] || { echo "Run as root."; exit 1; }

# 2. Check Ubuntu
[[ -f /etc/os-release ]] && source /etc/os-release
[[ "${ID:-}" == "ubuntu" ]] || echo "Warning: not Ubuntu, proceeding anyway."

# 3. System Python
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv

# 4. Create manager venv (separate from the QA Track venv)
python3 -m venv "${MANAGER_VENV}"

# 5. Install package from GitHub
"${MANAGER_VENV}/bin/pip" install --upgrade pip wheel
"${MANAGER_VENV}/bin/pip" install "git+${GITHUB_URL}.git"

# 6. Create convenience wrapper
cat > /usr/local/sbin/qatrackplus-manager << EOF
#!/bin/bash
exec "${MANAGER_VENV}/bin/qatrackplus-manager" "\$@"
EOF
chmod +x /usr/local/sbin/qatrackplus-manager

echo "Installed. Run: sudo qatrackplus-manager"
