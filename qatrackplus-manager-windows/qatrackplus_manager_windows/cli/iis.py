from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from ..transport.powershell import PowerShellTransport
from ..operations.iis import get_iis_status, install_iis, install_iis_modules, manage_iis_service

console = Console()

def iis_management_menu(transport: PowerShellTransport):
    """CLI menu for IIS management."""
    while True:
        status = get_iis_status(transport)
        
        console.print("\n" + Panel("[bold blue]IIS Management[/bold blue]", style="blue"))
        
        # Display Current Status
        table = Table(show_header=False, box=None)
        table.add_row("Service Status:", f"[{'green' if status['status'] == 'Running' else 'red'}]{status['status']}[/]")
        table.add_row("IIS Version:", status.get('version', 'Unknown'))
        
        modules = status.get('modules', {})
        for mod, mod_status in modules.items():
            color = "green" if mod_status == "Installed" else "red"
            table.add_row(f"{mod} Module:", f"[{color}]{mod_status}[/]")
            
        console.print(table)
        
        console.print("\n1. Start IIS")
        console.print("2. Stop IIS")
        console.print("3. Restart IIS")
        console.print("4. Install IIS (Windows Features)")
        console.print("5. Install IIS Modules (URL Rewrite, ARR)")
        console.print("0. Back to Main Menu")
        
        choice = Prompt.ask("\nSelect an option", choices=["0", "1", "2", "3", "4", "5"], default="0")
        
        if choice == "1":
            with console.status("[bold cyan]Starting IIS..."):
                manage_iis_service(transport, "start")
        elif choice == "2":
            if Confirm.ask("[yellow]Are you sure you want to STOP IIS? This will take your site offline.[/]"):
                with console.status("[bold cyan]Stopping IIS..."):
                    manage_iis_service(transport, "stop")
        elif choice == "3":
            with console.status("[bold cyan]Restarting IIS..."):
                manage_iis_service(transport, "restart")
        elif choice == "4":
            if Confirm.ask("Install IIS Windows features? (Requires Admin)"):
                with console.status("[bold cyan]Installing IIS..."):
                    res = install_iis(transport)
                    if res['status'] == "Success":
                        console.print("[green]✔ IIS Features enabled![/]")
                    else:
                        console.print(f"[red]✘ Failed: {res['message']}[/]")
                console.input("\nPress Enter to continue...")
        elif choice == "5":
            if Confirm.ask("Install URL Rewrite and ARR modules via winget?"):
                with console.status("[bold cyan]Installing modules..."):
                    res = install_iis_modules(transport)
                    for mod, mres in res.items():
                        if mres == "Success":
                            console.print(f"[green]✔ {mod} installed.[/]")
                        else:
                            console.print(f"[red]✘ {mod} failed: {mres}[/]")
                console.input("\nPress Enter to continue...")
        elif choice == "0":
            break
