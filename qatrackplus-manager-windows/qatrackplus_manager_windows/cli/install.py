from rich.console import Console
from rich.prompt import Prompt, Confirm
from ..transport.powershell import PowerShellTransport
from ..operations.install import clone_qatrack_repo, setup_venv, configure_qatrack, run_django_commands
import json
import os

console = Console()

def get_db_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "setup_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return None

def run_installation_wizard(transport: PowerShellTransport):
    """CLI wizard for installing QATrack+."""
    console.clear()
    console.print("[bold blue]=== QATrack+ Installation Wizard ===[/bold blue]\n")
    
    config = get_db_config()
    if not config:
        console.print("[yellow]! No database configuration found. Please run Guided Setup first.[/yellow]")
        input("\nPress Enter to return...")
        return

    install_path = config.get("install_path", "C:\\qatrackplus")
    
    # 1. Confirmation
    console.print(f"Installation Path: [bold cyan]{install_path}[/bold cyan]")
    console.print(f"Database: [bold cyan]{config['db_type']} | {config['db_name']}[/bold cyan]")
    
    if not Confirm.ask("\nProceed with installation?"):
        return

    # 2. Clone
    console.print("\n[yellow]Step 1/4: Cloning QATrack+ Repository...[/yellow]")
    res = clone_qatrack_repo(transport, install_path)
    if res['status'] == "Failed":
        console.print(f"[red]✘ {res['message']}[/red]")
        return
    console.print(f"[green]✔ {res['message']}[/green]")

    # 3. Venv
    console.print("\n[yellow]Step 2/4: Setting up Virtual Environment & Dependencies...[/yellow]")
    console.print("[dim](This may take a few minutes depending on your internet connection)[/dim]")
    res = setup_venv(transport, install_path)
    if res['status'] == "Failed":
        console.print(f"[red]✘ {res['message']}[/red]")
        return
    console.print(f"[green]✔ {res['message']}[/green]")

    # 4. Configure
    console.print("\n[yellow]Step 3/4: Configuring local_settings.py...[/yellow]")
    res = configure_qatrack(transport, install_path, config)
    if res['status'] == "Failed":
        console.print(f"[red]✘ {res['message']}[/red]")
        return
    console.print(f"[green]✔ {res['message']}[/green]")

    # 5. Migrations
    console.print("\n[yellow]Step 4/4: Running Database Migrations & Static Collection...[/yellow]")
    res = run_django_commands(transport, install_path)
    if res['status'] == "Failed":
        console.print(f"[red]✘ {res['message']}[/red]")
        return
    console.print(f"[green]✔ {res['message']}[/green]")

    # 6. Final Steps
    console.print("\n[bold green]✔ QATrack+ Installation Successful![/bold green]")
    
    if Confirm.ask("\nWould you like to create a Superuser (Admin) now?"):
        python_exe = os.path.join(install_path, ".venv", "Scripts", "python.exe")
        # We run this interactively
        transport.run(f"& '{python_exe}' manage.py createsuperuser", cwd=install_path)

    console.print("\n[blue]Next Steps:[/blue]")
    console.print("1. Use 'Manage Services' to start CherryPy.")
    console.print("2. Configure IIS for production access.")
    
    input("\nPress Enter to return to main menu...")
