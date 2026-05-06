from __future__ import annotations
from ..transport.base import Transport, CommandResult

class WebServerManager:
    def __init__(self, transport: Transport, web_server: str):
        self.transport = transport
        self.web_server = web_server # nginx | apache

    def check_syntax(self) -> CommandResult:
        if self.web_server == 'nginx':
            return self.transport.run(["nginx", "-t"])
        elif self.web_server == 'apache':
            return self.transport.run(["apache2ctl", "-t"])
        return CommandResult(-1, "", "Unknown web server")

    def reload(self) -> CommandResult:
        if self.web_server == 'nginx':
            return self.transport.run(["systemctl", "reload", "nginx"])
        elif self.web_server == 'apache':
            # Try reload, then graceful
            res = self.transport.run(["systemctl", "reload", "apache2"])
            if not res.succeeded:
                res = self.transport.run(["apache2ctl", "graceful"])
            return res
        return CommandResult(-1, "", "Unknown web server")

    def start(self) -> CommandResult:
        service = "nginx" if self.web_server == 'nginx' else "apache2"
        return self.transport.run(["systemctl", "start", service])

    def is_running(self) -> bool:
        service = "nginx" if self.web_server == 'nginx' else "apache2"
        return self.transport.service_active(service)
