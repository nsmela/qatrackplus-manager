from rich.console import Console
from rich.prompt import Prompt, Confirm
from ..transport.powershell import PowerShellTransport
from ..operations.db import test_db_connection, create_db_backup, restore_db_backup
import json
import os
import datetime

console = Console()

def get_db_config():
    """Reads the saved database configuration."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "setup_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return None

def database_management_menu(transport: PowerShellTransport):
    """CLI for database management tasks."""
    config = get_db_config()
    
    while True:
        console.clear()
        console.print("[bold blue]=== Database Management ===[/bold blue]\n")
        
        if not config:
            console.print("[yellow]No database configuration found. Please run Guided Setup first.[/yellow]")
            input("\nPress Enter to return...")
            break
            
        console.print(f"Connected to: [bold cyan]{config['db_type']} | {config['db_server']} | {config['db_name']}[/bold cyan]\n")
        
        console.print("1. Test Connection")
        console.print("2. Create Database Backup (SQL Only)")
        console.print("3. Create Full System Backup (DB + Uploaded Files)")
        console.print("4. Create Portable Backup (OS-Agnostic JSON + Media)")
        console.print("5. Restore from Backup")
        console.print("6. Run Migrations (Python/Django)")
        console.print("0. Back")
        
        choice = Prompt.ask("\nSelect an option", choices=["0", "1", "2", "3", "4", "5", "6"], default="0")
        
        if choice == "0":
            break
        elif choice == "1":
            results = test_db_connection(transport, config['db_type'].lower(), {
                "server": config['db_server'],
                "name": config['db_name'],
                "user": config['db_user'],
                "password": config.get('password') # Note: we might not have saved password in config for security, but let's assume it's there for now or we prompt
            })
            if results['status'] == "Success":
                console.print(f"[green]✔ {results['message']}[/green]")
            else:
                console.print(f"[red]✘ {results['message']}[/red]")
            input("\nPress Enter to continue...")
            
        elif choice == "2":
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            default_path = f"C:\\backups\\qatrackplus_{timestamp}.bak"
            backup_path = Prompt.ask("Backup Destination Path", default=default_path)
            
            # Ensure directory exists
            dir_path = os.path.dirname(backup_path)
            transport.run(f"if (!(Test-Path '{dir_path}')) {{ New-Item -ItemType Directory -Path '{dir_path}' }}")
            
            console.print(f"[yellow]Creating backup...[/yellow]")
            results = create_db_backup(transport, config['db_type'].lower(), {
                "server": config['db_server'],
                "name": config['db_name'],
                "user": config['db_user'],
                "password": config.get('password')
            }, backup_path)
            
            if results['status'] == "Success":
                console.print(f"[green]✔ {results['message']}[/green]")
            else:
                console.print(f"[red]✘ {results['message']}[/red]")
            input("\nPress Enter to continue...")

        elif choice == "3":
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Prompt.ask("Backup Directory Path", default=f"C:\\backups\\full_backup_{timestamp}")
            
            # Ensure directory exists
            transport.run(f"if (!(Test-Path '{backup_dir}')) {{ New-Item -ItemType Directory -Path '{backup_dir}' }}")
            
            from ..operations.db import create_full_backup
            console.print(f"[yellow]Creating full system backup...[/yellow]")
            results = create_full_backup(transport, config, backup_dir)
            
            if results['status'] == "Success":
                console.print(f"[green]✔ {results['message']}[/green]")
            elif results['status'] == "Partial":
                console.print(f"[yellow]! {results['message']}[/yellow]")
            else:
                console.print(f"[red]✘ {results['message']}[/red]")
            input("\nPress Enter to continue...")

        elif choice == "4":
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = Prompt.ask("Backup Directory Path", default=f"C:\\backups\\portable_backup_{timestamp}")
            
            # Ensure directory exists
            transport.run(f"if (!(Test-Path '{backup_dir}')) {{ New-Item -ItemType Directory -Path '{backup_dir}' }}")
            
            from ..operations.db import create_portable_backup
            console.print(f"[yellow]Creating portable system backup...[/yellow]")
            results = create_portable_backup(transport, config, backup_dir)
            
            if results['status'] == "Success":
                console.print(f"[green]✔ {results['message']}[/green]")
            else:
                console.print(f"[red]✘ {results['message']}[/red]")
            input("\nPress Enter to continue...")

        elif choice == "5":
            backup_path = Prompt.ask("Path to Backup File (.bak)")
            if not Confirm.ask(f"[bold red]WARNING: This will overwrite the current database '{config['db_name']}'. Proceed?[/bold red]"):
                continue
                
            console.print(f"[yellow]Restoring database...[/yellow]")
            results = restore_db_backup(transport, config['db_type'].lower(), config, backup_path)
            
            if results['status'] == "Success":
                console.print(f"[green]✔ {results['message']}[/green]")
            else:
                console.print(f"[red]✘ {results['message']}[/red]")
            input("\nPress Enter to continue...")

        elif choice == "6":
            console.print("[yellow]Running Django migrations...[/yellow]")
            # Placeholder for running manage.py migrate
            console.print("[dim]This requires the QATrack+ repository to be installed.[/dim]")
            input("\nPress Enter to continue...")
