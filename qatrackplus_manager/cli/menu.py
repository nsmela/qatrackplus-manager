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
from ..ui.tables import render_scan_section

def show_header(state: ManagerState):
    console.clear()
    header_text = (
        f"Active Server: [cyan]{state.active_server}[/cyan] | "
        f"DB: [cyan]{state.db_type}[/cyan] | "
        f"Web: [cyan]{state.web_server}[/cyan]"
    )
    console.print(Panel(header_text, title="QA Track Plus Manager", style="bold blue"))

def main_menu(state: ManagerState):
    transport = LocalTransport()
    
    while True:
        show_header(state)
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
