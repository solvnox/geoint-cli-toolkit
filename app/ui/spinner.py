"""
Loading spinners for async-like operations.
"""
from rich.console import Console
from rich.spinner import Spinner
from contextlib import contextmanager

console = Console()


@contextmanager
def spinner(text: str = "Обработка..."):
    """Context manager for showing a spinner during work."""
    with console.status(f"[bold cyan]{text}[/bold cyan]", spinner="dots"):
        yield
