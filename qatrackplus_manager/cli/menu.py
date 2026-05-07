from __future__ import annotations
import sys
import time
import logging
from rich.panel import Panel
from ..ui.console import console
from ..ui.theme import STATUS_ICONS
from ..config.models import ManagerState
from ..transport.local import LocalTransport
from ..checks.scan import run_full_scan
from ..checks.test_install import run_all_tests
from ..ui.tables import render_scan_section, render_test_section


def show_header(state: ManagerState, latest_version: str = ""):
    console.clear()
    header_text = (
        f"Active Server: [cyan]{state.active_server}[/cyan] | "
        f"DB: [cyan]{state.db_type}[/cyan] | "
        f"Web: [cyan]{state.web_server}[/cyan]"
    )
    console.print(Panel(header_text, title="QA Track Plus Manager", style="bold blue"))
    if latest_version:
        console.print(f"Latest Version: [bold cyan]{latest_version}[/bold cyan]")

def get_latest_qatrack_release() -> str:
    """Fetch the latest release tarball URL from GitHub API."""
    fallback = "https://github.com/qatrackplus/qatrackplus/archive/refs/tags/v3.1.1.tar.gz"
    try:
        import requests
        res = requests.get("https://api.github.com/repos/qatrackplus/qatrackplus/releases/latest", timeout=5)
        if res.status_code == 200:
            return res.json().get("tarball_url", fallback)
    except:
        pass
    return fallback

def handle_install(transport: LocalTransport, state: ManagerState):
    from ..operations.install import install
    from rich.prompt import Confirm, Prompt
    import secrets

    console.print("\n[bold blue]─── QATrack+ Installation ───[/bold blue]")
    
    # 1. Basic paths
    app_dir = Prompt.ask("Application directory", default="/opt/qatrackplus")
    app_user = Prompt.ask("Application user", default="qatrack")
    
    # 2. Release
    with console.status("[dim]Fetching latest release from GitHub..."):
        latest_release = get_latest_qatrack_release()
    
    release_url = Prompt.ask("Release URL (tar.gz)", default=latest_release)
    
    # 3. Database Type
    db_types = ["postgresql", "mysql", "sqlite", "mssql"]
    db_type = Prompt.ask("Database type", choices=db_types, default=state.db_type)
    state.db_type = db_type
    
    # 4. Database Config
    console.print(f"\n[bold]Database Configuration ([cyan]{state.db_type}[/cyan])[/bold]")
    db_host = Prompt.ask("Database host", default=state.db_host)
    state.db_host = db_host
    
    db_user = Prompt.ask("Database user", default=state.db_user)
    state.db_user = db_user
    
    db_pass = Prompt.ask(f"Password for user [cyan]{db_user}[/cyan]", password=True)
    
    # 5. Django Settings
    console.print(f"\n[bold]Django Settings[/bold]")
    secret_key = Prompt.ask("SECRET_KEY (leave blank to generate)", password=True, default="")
    if not secret_key:
        secret_key = secrets.token_urlsafe(50)
        console.print("[dim]Generated a random secret key.[/dim]")
    
    allowed_hosts = Prompt.ask("ALLOWED_HOSTS (comma separated)", default="localhost")

    # Confirm
    if not Confirm.ask("\nReady to begin installation?"):
        return


    install_config = {
        'app_dir': app_dir,
        'app_user': app_user,
        'release_url': release_url,
        'db_password': db_pass,
        'secret_key': secret_key,
        'allowed_hosts': allowed_hosts,
    }

    try:
        with console.status("[bold green]Installing QATrack+... (this may take several minutes)"):
            install(transport, state, install_config)
        console.print("\n[bold green]SUCCESS:[/bold green] QATrack+ has been installed and services started.")
    except Exception as e:
        console.print(f"\n[bold red]Installation Failed:[/bold red] {str(e)}")
        logging.exception("Installation failed")
    
    console.input("\nPress Enter to return to menu...")



def main_menu(state: ManagerState):
    transport = LocalTransport()
    
    # Check for updates on startup
    from ..checks.version import check_for_updates
    from ..operations.manager import self_update
    
    latest_v = ""
    try:
        update_available, latest_v = check_for_updates()
        if update_available:
            console.print(Panel(
                f"[yellow]A new version of the manager is available: [bold]{latest_v}[/bold][/yellow]\n"
                "Auto-updating now...",
                title="Update Found",
                border_style="yellow"
            ))
            time.sleep(2)
            self_update()
    except Exception as e:
        console.print(Panel(
            f"[red]Could not verify for updates: {str(e)}[/red]",
            title="Version Check Error",
            border_style="red"
        ))
        time.sleep(3)
    
    while True:
        show_header(state, latest_v)


            
        console.print("\n[bold]Main Menu[/bold]")
        console.print("1. System Scan")
        console.print("2. Test Install")
        console.print("3. Install")
        console.print("4. Upgrade")
        console.print("5. Backup")
        console.print("6. Restore")
        console.print("7. Settings")
        console.print("0. Exit")
        
        choice = console.input("\n[bold]Select an option: [/bold]")
        
        try:
            if choice == "1":
                results = run_full_scan(transport, state)
                for i, section in enumerate(results):
                    console.print(render_scan_section(f"Scan Section {i+1}", section))
                console.input("\nPress Enter to return to menu...")
            elif choice == "2":
                results = run_all_tests(transport, state)
                for i, section in enumerate(results):
                    console.print(render_test_section(f"Test Section {i+1}", section))
                console.input("\nPress Enter to return to menu...")
            elif choice == "3":
                handle_install(transport, state)
            elif choice == "0":

                console.print("[yellow]Goodbye![/yellow]")
                sys.exit(0)
            else:

                console.print("[red]Not implemented yet.[/red]")
                time.sleep(1)
        except Exception as e:
            console.print(f"\n[red bold]Error:[/red bold] {str(e)}")
            logging.exception("An error occurred during menu option execution")
            console.print(f"Check the log for full details: /var/log/qatrackplus-manager.log")
            console.input("\nPress Enter to return to menu...")
