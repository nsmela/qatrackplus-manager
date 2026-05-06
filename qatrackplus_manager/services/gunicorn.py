from __future__ import annotations
from ..transport.base import Transport, CommandResult

class GunicornManager:
    def __init__(self, transport: Transport, service_name: str = "qatrackplus"):
        self.transport = transport
        self.service_name = service_name

    def start(self) -> CommandResult:
        return self.transport.run(["systemctl", "start", self.service_name])

    def stop(self) -> CommandResult:
        return self.transport.run(["systemctl", "stop", self.service_name])

    def restart(self) -> CommandResult:
        return self.transport.run(["systemctl", "restart", self.service_name])

    def status(self) -> bool:
        return self.transport.service_active(self.service_name)

    def write_service_file(
        self,
        app_user: str,
        app_dir: str,
        venv_dir: str,
        db_service: str = ""
    ) -> None:
        content = f"""[Unit]
Description=QA Track Plus (Gunicorn)
After=network.target {db_service}

[Service]
User={app_user}
Group={app_user}
WorkingDirectory={app_dir}
ExecStart={venv_dir}/bin/gunicorn qatrack.wsgi:application \\
    --workers 3 \\
    --bind unix:/run/qatrackplus.sock \\
    --access-logfile /var/log/qatrackplus-access.log \\
    --error-logfile /var/log/qatrackplus-error.log
Restart=always

[Install]
WantedBy=multi-user.target
"""
        self.transport.write_file(f"/etc/systemd/system/{self.service_name}.service", content)
        self.transport.run(["systemctl", "daemon-reload"])
        self.transport.run(["systemctl", "enable", self.service_name])
        
    def get_worker_count(self) -> int:
        # Replicating pgrep -c bug fix: use list of pids
        pids = self.transport.run(["pgrep", "-f", "gunicorn"])
        if pids.succeeded:
            return len(pids.stdout.strip().split("\n"))
        return 0
