import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from .. import __version__
from ..transport.powershell import PowerShellTransport
from ..operations.scan import run_system_scan

# Initialize with legacy windows support and force terminal mode for better stability
console = Console(force_terminal=True)

def show_header(update_info: dict = None):
    header_text = (
        f"v{__version__} | [bold green]Windows Edition[/bold green]"
    )
    if update_info and update_info.get('updated'):
        header_text += f"\n\n[bold green]✔ Manager was automatically updated![/bold green]"
    
    console.print(Panel(header_text, title="QA Track Plus Manager (Windows)", style="bold blue"))

def main_menu():
    transport = PowerShellTransport()
    
    # Check for updates once on startup
    update_info = {'updated': False}
    with console.status("[bold cyan]Checking for updates..."):
        results = run_system_scan(transport)
        repo_info = results.get('repository')
        
        if repo_info and repo_info.get('behind'):
            console.print("[yellow]Update found! Applying automatically...[/yellow]")
            transport.run("git pull", capture_output=False)
            update_info['updated'] = True
            # Refresh version info if needed (though it won't affect current process memory)
            update_info['branch'] = repo_info.get('branch')

    while True:
        # Use native OS clear command for maximum compatibility on Windows
        os.system('cls' if os.name == 'nt' else 'clear')
            
        show_header(update_info)
        
        console.print("\n[bold]Main Menu[/bold]")
        console.print("1. Guided Setup & Scan")
        console.print("2. Install QATrack+")
        console.print("3. Manage Services (CherryPy, Django Q)")
        console.print("4. Backup & Restore")
        console.print("5. Database Management")
        console.print("6. PDF Report Setup (Chrome)")
        console.print("0. Exit")
        
        choice = Prompt.ask("\nSelect an option", choices=["0", "1", "2", "3", "4", "5", "6"], default="0")
        transport = PowerShellTransport()
        
        if choice == "1":
            from ..operations.wizard import run_setup_wizard
            run_setup_wizard(transport)
            console.input("\nPress Enter to return...")
        elif choice == "2":
            from .install import run_installation_wizard
            run_installation_wizard(transport)
        elif choice == "3":
            from .services import manage_services_menu
            manage_services_menu(transport)
        elif choice == "4":
            from .database import database_management_menu
            database_management_menu(transport)
        elif choice == "5":
            # Direct to database tools if we have more specific ones later
            from .database import database_management_menu
            database_management_menu(transport)
        elif choice == "6":
            console.print("[yellow]Chrome/PDF setup coming soon...[/yellow]")
            console.input("\nPress Enter to return...")
        elif choice == "0":
            console.print("[yellow]Goodbye![/yellow]")
            break
