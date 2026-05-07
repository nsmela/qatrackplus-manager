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
    from .. import __version__
    import os
    module_path = os.path.abspath(__file__)
    console.clear()
    header_text = (
        f"v{__version__} | {module_path}\n"
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
    from rich.prompt import Confirm, IntPrompt
    import secrets

    console.print("\n[bold blue]─── QATrack+ Installation ───[/bold blue]")
    
    def ask_with_default(msg, default, password=False):
        prompt_str = f"{msg} [dim](leave blank for default: {default})[/dim]: "
        val = console.input(prompt_str, password=password)
        return val.strip() or default

    # 1. Basic paths
    app_dir = ask_with_default("Application directory", "/opt/qatrackplus")
    app_user = ask_with_default("Application user", "qatrack")
    
    # 2. Release
    with console.status("[dim]Fetching latest release from GitHub..."):
        latest_release = get_latest_qatrack_release()
    
    release_url = ask_with_default("Release URL (tar.gz)", latest_release)
    
    # 3. Database Type (Numbered Choice)
    db_types = ["postgresql", "mysql", "sqlite", "mssql"]
    console.print("\n[bold]Select Database Type:[/bold]")
    for i, t in enumerate(db_types, 1):
        console.print(f"{i}. {t}")
    
    # Map current state to default index
    default_idx = 1
    if state.db_type in db_types:
        default_idx = db_types.index(state.db_type) + 1
        
    choice_idx = IntPrompt.ask("Select an option", choices=[str(i) for i in range(1, len(db_types)+1)], default=default_idx)
    db_type = db_types[choice_idx - 1]
    state.db_type = db_type
    
    # 4. Database Config
    console.print(f"\n[bold]Database Configuration ([cyan]{state.db_type}[/cyan])[/bold]")
    db_host = ask_with_default("Database host IP/Hostname", "localhost")
    state.db_host = db_host
    
    db_user = ask_with_default("Database user", state.db_user)
    state.db_user = db_user
    
    db_pass = console.input(f"Password for user [cyan]{db_user}[/cyan]: ", password=True)
    
    # 5. Django Settings
    console.print(f"\n[bold]Django Settings[/bold]")
    secret_key = console.input("SECRET_KEY [dim](leave blank to generate)[/dim]: ", password=True)
    if not secret_key:
        secret_key = secrets.token_urlsafe(50)
        console.print("[dim]Generated a random secret key.[/dim]")
    
    allowed_hosts = ask_with_default("ALLOWED_HOSTS (comma separated)", "localhost")

    # Confirm
    if not Confirm.ask("\nReady to begin installation?"):
        return

    install_config = {
        'app_dir': app_dir,
        'app_user': app_user,
        'release_url': release_url,
        'db_password': db_pass,
        'secret_key': secret_key,
        'allowed_hosts': [h.strip() for h in allowed_hosts.split(",") if h.strip()],
    }


    try:
        def status_update(msg):
            console.print(f"  [bold blue]•[/bold blue] {msg}")

        console.print("\n[bold yellow]Starting Installation...[/bold yellow]")
        install(transport, state, install_config, status_callback=status_update)
        console.print("\n[bold green]SUCCESS:[/bold green] QATrack+ has been installed and services started.")
    except Exception as e:
        console.print(f"\n[bold red]Installation Failed:[/bold red] {str(e)}")
        logging.exception("Installation failed")
    
    console.input("\nPress Enter to return to menu...")


def handle_upgrade(transport: LocalTransport, state: ManagerState):
    from ..operations.upgrade import upgrade
    from .prompts import ask_with_default
    from ..operations.install import get_latest_qatrack_release
    
    if not state.servers[0].app_dir:
        console.print("[red]No installation detected. Please install first.[/red]")
        time.sleep(2)
        return

    console.print("\n[bold blue]─── QATrack+ Upgrade ───[/bold blue]")
    
    # 1. New Release
    with console.status("[dim]Fetching latest release from GitHub..."):
        latest_release = get_latest_qatrack_release()
    
    release_url = ask_with_default("New Release URL (tar.gz)", latest_release)
    
    # 2. Backup Location
    backup_dir = ask_with_default("Backup directory", "/opt/qatrackplus-backups")
    
    # Confirm
    if not Confirm.ask("\nReady to begin upgrade? [dim](A backup will be created first)[/dim]"):
        return

    upgrade_config = {
        'app_dir': state.servers[0].app_dir,
        'app_user': state.servers[0].app_user,
        'release_url': release_url,
        'backup_dir': backup_dir,
        'db_password': "", # Will be detected from local_settings.py
        'secret_key': "",   # Will be detected
        'allowed_hosts': [], # Will be detected
    }
    
    def status_update(msg):
        console.print(f"  [bold blue]•[/bold blue] {msg}")

    try:
        console.print("\n[bold yellow]Starting Upgrade Process...[/bold yellow]")
        upgrade(transport, state, upgrade_config, status_callback=status_update)
        console.print("\n[bold green]SUCCESS:[/bold green] QATrack+ has been upgraded and services restarted.")
    except Exception as e:
        console.print(f"\n[bold red]Upgrade Failed:[/bold red] {str(e)}")
        logging.exception("Upgrade failed")
    
    console.input("\nPress Enter to return to menu...")


def handle_backup(transport: LocalTransport, state: ManagerState):
    from ..operations.backup import backup
    from .prompts import ask_with_default
    
    if not state.servers[0].app_dir:
        console.print("[red]No installation detected.[/red]")
        time.sleep(2)
        return

    console.print("\n[bold blue]─── QATrack+ Backup ───[/bold blue]")
    backup_dir = ask_with_default("Backup directory", "/opt/qatrackplus-backups")
    label = Prompt.ask("Backup label [dim](optional)[/dim]", default="manual")

    try:
        with console.status("[bold yellow]Creating backup..."):
            from ..config.detect import detect_full_settings_from_file
            settings = detect_full_settings_from_file(transport, state.local_settings_file)
            
            db_config = {
                'name': state.db_name,
                'user': state.db_user,
                'host': state.db_host,
                'port': state.db_port,
                'password': settings.get('db_password', '')
            }
            
            archive_path = backup(
                transport,
                state.servers[0].app_dir,
                backup_dir,
                state.db_type,
                db_config,
                label=label
            )
        console.print(f"\n[bold green]SUCCESS:[/bold green] Backup created at [cyan]{archive_path}[/cyan]")
    except Exception as e:
        console.print(f"\n[bold red]Backup Failed:[/bold red] {str(e)}")
        logging.exception("Backup failed")
    
    console.input("\nPress Enter to return to menu...")






def handle_restore(transport: LocalTransport, state: ManagerState):
    from ..operations.restore import restore
    from .prompts import ask_with_default
    
    if not state.servers[0].app_dir:
        console.print("[red]No installation detected.[/red]")
        time.sleep(2)
        return

    console.print("\n[bold blue]─── QATrack+ Restore ───[/bold blue]")
    archive_path = Prompt.ask("Path to backup archive (.tar.gz)")
    
    if not transport.file_exists(archive_path):
        console.print(f"[red]Error: Archive not found at {archive_path}[/red]")
        time.sleep(2)
        return

    # Confirm
    if not Confirm.ask(f"\n[yellow]WARNING: This will overwrite your current database and media files.[/yellow]\nReady to restore from [cyan]{archive_path}[/cyan]?"):
        return

    try:
        with console.status("[bold yellow]Restoring from backup..."):
             from ..config.detect import detect_full_settings_from_file
             
             db_config = {
                'name': state.db_name,
                'user': state.db_user,
                'host': state.db_host,
                'port': state.db_port,
                'password': ""
             }
             
             if state.local_settings_file and transport.file_exists(state.local_settings_file):
                 settings = detect_full_settings_from_file(transport, state.local_settings_file)
                 db_config['password'] = settings.get('db_password', '')
             
             if not db_config['password'] and state.db_type != 'sqlite':
                 db_config['password'] = console.input(f"Password for database user [cyan]{state.db_user}[/cyan]: ", password=True)

             restore(
                transport,
                archive_path,
                state.servers[0].app_dir,
                db_config
             )
        console.print(f"\n[bold green]SUCCESS:[/bold green] Restoration complete!")
    except Exception as e:
        console.print(f"\n[bold red]Restore Failed:[/bold red] {str(e)}")
        logging.exception("Restore failed")
    
    console.input("\nPress Enter to return to menu...")


def handle_settings(transport: LocalTransport, state: ManagerState):
    from .prompts import ask_with_default
    
    console.print("\n[bold blue]─── QATrack+ Manager Settings ───[/bold blue]")
    console.print(f"App Directory: [cyan]{state.servers[0].app_dir}[/cyan]")
    console.print(f"App User: [cyan]{state.servers[0].app_user}[/cyan]")
    console.print(f"Database Type: [cyan]{state.db_type}[/cyan]")
    console.print(f"Database Host: [cyan]{state.db_host}[/cyan]")
    console.print(f"Web Server: [cyan]{state.web_server}[/cyan]")
    
    if Confirm.ask("\nUpdate active application directory?"):
        new_dir = Prompt.ask("New directory", default=state.servers[0].app_dir)
        state.servers[0].app_dir = new_dir
        # Re-detect
        from ..config.detect import auto_detect
        auto_detect(transport, state)
        # Save
        from ..config.state import save_state
        save_state(transport, new_dir, state)
        console.print("[green]Settings updated and re-detected.[/green]")
    
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
        
        choice = console.input("\n[bold]Select an option: [/bold]").strip()

        
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
            elif choice == "4":
                handle_upgrade(transport, state)
            elif choice == "5":
                handle_backup(transport, state)
            elif choice == "6":
                handle_restore(transport, state)
            elif choice == "7":
                handle_settings(transport, state)
            elif choice == "0":
                console.print("[yellow]Goodbye![/yellow]")
                sys.exit(0)
            else:
                console.print("[red]Invalid option.[/red]")
                time.sleep(1)
        except Exception as e:
            console.print(f"\n[red bold]Error:[/red bold] {str(e)}")
            logging.exception("An error occurred during menu option execution")
            console.print(f"Check the log for full details: /var/log/qatrackplus-manager.log")
            console.input("\nPress Enter to return to menu...")
