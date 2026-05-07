from __future__ import annotations
from rich.prompt import Prompt, Confirm
from ..ui.console import console

def ask_string(message: str, default: str = "") -> str:
    return Prompt.ask(message, default=default)

def ask_confirm(message: str, default: bool = False) -> bool:
    return Confirm.ask(message, default=default)

def ask_choice(message: str, choices: list, default: str = "") -> str:
    return Prompt.ask(message, choices=choices, default=default)
