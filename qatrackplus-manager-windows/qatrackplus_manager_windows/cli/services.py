from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from ..transport.powershell import PowerShellTransport
from ..operations.services import get_qatrack_services, control_service

console = Console()

def manage_services_menu(transport: PowerShellTransport):
    """CLI for managing QATrack+ Windows services."""
    while True:
        console.clear()
        console.print("[bold blue]=== Manage QATrack+ Services ===[/bold blue]\n")
        
        services = get_qatrack_services(transport)
        
        if not services:
            console.print("[yellow]No QATrack+ services detected on this system.[/yellow]")
            console.print("[dim](Looking for: CherryPy, DjangoQ, QATrackPlus, Waitress)[/dim]")
            input("\nPress Enter to return...")
            break
            
        table = Table(title="Service Status")
        table.add_column("ID", style="cyan")
        table.add_column("Service Name", style="white")
        table.add_column("Status", style="magenta")
        
        for idx, svc in enumerate(services, 1):
            status_style = "green" if svc['status'] == "Running" else "yellow"
            table.add_row(str(idx), svc['name'], f"[{status_style}]{svc['status']}[/{status_style}]")
            
        console.print(table)
        console.print("\nActions: [1-N] Select Service | [R] Refresh | [0] Back")
        
        choice = Prompt.ask("Select an option", default="0")
        
        if choice == "0":
            break
        elif choice.lower() == "r":
            continue
        elif choice.isdigit() and 1 <= int(choice) <= len(services):
            selected_svc = services[int(choice)-1]
            if selected_svc.get('is_virtual'):
                console.print("[yellow]This is a remote/monitored connection, not a local service. Actions unavailable.[/yellow]")
                input("\nPress Enter to continue...")
                continue
            service_action_menu(transport, selected_svc)
        else:
            console.print("[red]Invalid choice.[/red]")

def service_action_menu(transport: PowerShellTransport, service: dict):
    """Menu for actions on a specific service."""
    while True:
        console.print(f"\n[bold]Service: {service['name']} ([{'green' if service['status'] == 'Running' else 'yellow'}]{service['status']}[/])[/bold]")
        console.print("1. Start")
        console.print("2. Stop")
        console.print("3. Restart")
        console.print("0. Back")
        
        action_choice = Prompt.ask("Action", choices=["0", "1", "2", "3"], default="0")
        
        if action_choice == "0":
            break
            
        action_map = {"1": "start", "2": "stop", "3": "restart"}
        action = action_map[action_choice]
        
        try:
            console.print(f"[yellow]Performing {action} on {service['name']}...[/yellow]")
            control_service(transport, service['name'], action)
            console.print(f"[green]✔ Service {action}ed successfully.[/green]")
            # Update status for the next loop display
            service['status'] = transport.get_service_status(service['name'])
        except Exception as e:
            console.print(f"[red]✘ Failed to {action} service: {str(e)}[/red]")
        
        input("\nPress Enter to continue...")
        break # Return to service list
