from __future__ import annotations
import logging
from .cli.menu import main_menu
from .config.state import load_state
from .transport.local import LocalTransport

LOG_FILE = "/var/log/qatrackplus-manager.log"

def main():
    # Setup logging
    # In a real Ubuntu environment, we'd need root for /var/log
    # For now, let's use a local log if /var/log is not writable
    try:
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    except IOError:
        logging.basicConfig(
            filename="qatrackplus-manager.log",
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    transport = LocalTransport()
    # Default app_dir for state loading
    state = load_state(transport, "/opt/qatrackplus")
    
    main_menu(state)

if __name__ == "__main__":
    main()
