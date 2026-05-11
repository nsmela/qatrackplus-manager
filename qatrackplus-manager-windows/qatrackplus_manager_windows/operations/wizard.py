from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from ..transport.powershell import PowerShellTransport
from .scan import run_system_scan
from .db import test_db_connection
import sys
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "setup_config.json")

console = Console()

def handle_failure(message: str, allow_skip: bool = True):
    """Handles a step failure by asking to Retry, Skip, or Quit."""
    console.print(f"[red]✘ {message}[/red]")
    choices = ["retry", "skip", "quit"] if allow_skip else ["retry", "quit"]
    choice = Prompt.ask("What would you like to do?", choices=choices, default="retry")
    
    if choice == "quit":
        return "quit"
    return choice

def run_setup_wizard(transport: PowerShellTransport):
    """Interactive setup wizard for QATrack+ on Windows."""
    console.print("\n[bold blue]=== QATrack+ Interactive Setup Wizard ===[/bold blue]\n")
    
    # --- PHASE 1: TOOLS ---
    while True:
        console.print("[yellow]Phase 1: Tool Verification[/yellow]")
        tools_ok = True
        
        # Incremental scan for tools
        for tool in ['python', 'git', 'odbc_driver']:
            tool_name = tool.capitalize().replace('_', ' ')
            with console.status(f"[bold cyan]Checking {tool_name}..."):
                # We can still use run_system_scan but we'll extract just what we need
                # or better, we could have a more granular scan.
                # For now, let's just refresh the whole scan but only show the current tool.
                results = run_system_scan(transport)
            
            status = results.get(tool, {}).get('status', 'Missing')
            if status == "Found":
                console.print(f"[green]✔ {tool_name} found.[/green]")
            else:
                console.print(f"[red]✘ {tool_name} is {status}.[/red]")
                if tool == 'odbc_driver':
                    if Confirm.ask("Would you like to install the Microsoft ODBC Driver for SQL Server now?"):
                        console.print("[bold cyan]Installing ODBC Driver via winget...[/bold cyan]")
                        transport.run("winget install --id Microsoft.msodbcsql.18 --source winget --exact --silent --accept-package-agreements --accept-source-agreements", capture_output=False)
                        console.print("[green]✔ ODBC Driver installed successfully![/green]")
                else:
                    tools_ok = False
        
        # Package Check
        console.print("\n[yellow]Verifying Python Packages:[/yellow]")
        for pkg in ['django', 'cherrypy']:
            with console.status(f"[bold cyan]Checking {pkg.capitalize()}..."):
                results = run_system_scan(transport)
            
            packages = results.get('packages', {})
            version = packages.get(pkg, "Missing")
            if version == "Missing":
                console.print(f"[red]✘ {pkg.capitalize()} is missing.[/red]")
                if Confirm.ask(f"Would you like to install {pkg.capitalize()} now?"):
                    console.print(f"[bold cyan]Installing {pkg}...[/bold cyan]")
                    transport.run(f"& '{sys.executable}' -m pip install {pkg}", capture_output=False)
                    console.print(f"[green]✔ {pkg.capitalize()} installed successfully![/green]")
                else:
                    tools_ok = False
            else:
                console.print(f"[green]✔ {pkg.capitalize()} ({version}) is installed.[/green]")
        
        if tools_ok:
            # Check for repository updates
            repo_info = results.get('repository', {})
            if repo_info.get('behind'):
                console.print(f"\n[yellow]! An update is available on the '{repo_info['branch']}' branch.[/yellow]")
                if Confirm.ask("Would you like to pull the latest version now?"):
                    console.print("[bold cyan]Pulling updates...[/bold cyan]")
                    transport.run("git pull", capture_output=False)
                    console.print("[green]✔ Repository updated. Please restart the manager if necessary.[/green]")
                    results = run_system_scan(transport)
            else:
                console.print(f"\n[green]✔ Manager is up to date (branch: {repo_info.get('branch', 'unknown')}).[/green]")
            break
        
        choice = handle_failure("Some tools or packages are missing.")
        if choice == "quit":
            console.print("[yellow]Setup aborted. Returning to menu...[/yellow]")
            return
        if choice == "retry":
            results = run_system_scan(transport)
            continue
        break # Skip Phase 1

    # --- PHASE 2: DATABASE ---
    while True:
        console.print("\n[yellow]Phase 2: Database Configuration[/yellow]")
        db_choice = Prompt.ask("Select Database Engine", choices=["MSSQL", "PostgreSQL", "MySQL", "SQLite"], default="MSSQL")
        db_type = db_choice.lower()
        
        if db_type == "sqlite":
            db_path = Prompt.ask("Path to SQLite database file", default="C:\\qatrackplus\\db.sqlite3")
            if not transport.file_exists(db_path):
                console.print("[yellow]! File does not exist (will be created during installation).[/yellow]")
            break # Success
        else:
            # 2a. Test Server Connectivity
            port_map = {"mssql": 1433, "postgresql": 5432, "mysql": 3306}
            default_port = port_map.get(db_type, 0)
            
            server_ok = False
            while not server_ok:
                server = Prompt.ask("Database Server address (IP or Hostname)", default="localhost")
                port = int(Prompt.ask("Database Port", default=str(default_port)))
                
                console.print(f"Testing connectivity to {server}:{port}...")
                
                # 1. Ping test
                ping_test = transport.run(f"Test-Connection -ComputerName {server} -Count 1 -Quiet", log_errors=False).stdout.strip()
                
                # 2. Port test
                console.print(f"Checking if {db_choice} is listening on port {port}...")
                port_test = transport.run(f"Test-NetConnection -ComputerName {server} -Port {port} | Select-Object -ExpandProperty TcpTestSucceeded", log_errors=False).stdout.strip()
                port_ok = (port_test == "True")

                if ping_test == "True" and port_ok:
                    console.print(f"[green]✔ Server {server} is reachable and {db_choice} is listening on port {port}.[/green]")
                    server_ok = True
                else:
                    err_msg = "Could not reach server." if ping_test != "True" else f"{db_choice} not listening on port {port}."
                    choice = handle_failure(err_msg)
                    if choice == "quit":
                        console.print("[yellow]Setup aborted. Returning to menu...[/yellow]")
                        return
                    if choice == "skip": break
            
            if not server_ok: break # Skip Phase 2

            # 2b. Test Authentication
            auth_ok = False
            while not auth_ok:
                user = Prompt.ask("Username")
                password = Prompt.ask("Password", password=True)
                console.print("Testing authentication...")
                test_db = "master" if db_type == "mssql" else "postgres"
                auth_test = test_db_connection(transport, db_type, {"server": server, "user": user, "password": password, "name": test_db})
                
                if auth_test['status'] == "Success":
                    console.print("[green]✔ Authentication successful.[/green]")
                    auth_ok = True
                else:
                    choice = handle_failure(f"Authentication failed: {auth_test['message']}")
                    if choice == "quit":
                        console.print("[yellow]Setup aborted. Returning to menu...[/yellow]")
                        return
                    if choice == "skip": break # Exit Inner Loop
            
            if not auth_ok: break # Skip Phase 2

            # 2c. Database Name
            name_ok = False
            while not name_ok:
                db_name = Prompt.ask("Database Name", default="qatrackplus")
                console.print(f"Verifying database '{db_name}'...")
                final_test = test_db_connection(transport, db_type, {"server": server, "user": user, "password": password, "name": db_name})
                if final_test['status'] == "Success":
                    console.print(f"[green]✔ Database '{db_name}' is ready.[/green]")
                    name_ok = True
                    
                    # Save configuration
                    config = {
                        "db_type": db_choice,
                        "db_server": server,
                        "db_port": port,
                        "db_user": user,
                        "db_name": db_name
                    }
                    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
                    with open(CONFIG_FILE, "w") as f:
                        json.dump(config, f, indent=4)
                    console.print("[dim]Database configuration saved.[/dim]")
                    name_ok = True
                    break # Exit name_ok loop
            
            if name_ok: break # Exit Phase 2 loop

    # --- PHASE 2.5: INSTALLATION PATH ---
    console.print("\n[yellow]Phase 2.5: Application Path[/yellow]")
    install_path = Prompt.ask("Path to QATrack+ Installation Directory", default="C:\\qatrackplus")
    if not transport.file_exists(install_path):
        console.print("[yellow]! Path does not exist yet. It will be used for future backups.[/yellow]")
    
    # Update config with install path
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        config["install_path"] = install_path
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        console.print("[dim]Installation path updated in config.[/dim]")

    # --- PHASE 3: IIS ---
    console.print("\n[yellow]Phase 3: Web Server (IIS) Configuration[/yellow]")
    from .iis import install_iis, install_iis_modules
    
    if results['iis']['status'] == "Missing":
        console.print("[red]✘ IIS (W3SVC) is not installed.[/red]")
        if Confirm.ask("Would you like to install IIS and its required features now?"):
            console.print("[bold cyan]Installing IIS...[/bold cyan]")
            install_iis(transport)
            console.print("[green]✔ IIS installed successfully![/green]")
            results = run_system_scan(transport) # Refresh
    else:
        console.print("[green]✔ IIS is installed.[/green]")
        modules = results['iis'].get('modules', {})
        modules_missing = False
        for mod, status in modules.items():
            if status == "Missing":
                console.print(f"[red]✘ {mod} is missing.[/red]")
                modules_missing = True
            else:
                console.print(f"[green]✔ {mod} is installed.[/green]")
        
        if modules_missing:
            if Confirm.ask("Would you like to install missing IIS modules (URL Rewrite, ARR) now?"):
                console.print("[bold cyan]Installing IIS modules via winget...[/bold cyan]")
                install_iis_modules(transport)
                console.print("[green]✔ IIS modules installed successfully![/green]")
                results = run_system_scan(transport) # Refresh

    # --- PHASE 4: CHROME ---
    console.print("\n[yellow]Phase 4: PDF Generation[/yellow]")
    if results['chrome']['status'] == "Missing":
        console.print("[yellow]! Google Chrome is missing.[/yellow]")
    else:
        console.print("[green]✔ Google Chrome found.[/green]")

    console.print("\n[bold green]Wizard completed![/bold green]")
