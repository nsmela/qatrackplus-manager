from __future__ import annotations
from typing import List
from rich.table import Table
from rich.text import Text
from .theme import STATUS_ICONS
from ..checks import ScanResult, TestResult

def render_scan_section(title: str, results: List[ScanResult]) -> Table:
    table = Table(title=title, show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Status", width=10)
    table.add_column("Label", width=40)
    table.add_column("Details")

    for res in results:
        icon = STATUS_ICONS.get(res.status, res.status)
        table.add_row(icon, res.label, res.detail)
    
    return table

def render_test_section(title: str, results: List[TestResult]) -> Table:
    table = Table(title=title, show_header=True, header_style="bold blue", expand=True)
    table.add_column("Status", width=10)
    table.add_column("Label", width=40)
    table.add_column("Details")

    for res in results:
        icon = STATUS_ICONS.get(res.status, res.status)
        table.add_row(icon, res.label, res.detail)
    
    return table
