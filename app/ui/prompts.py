from rich.console import Console
from rich.prompt import Prompt, IntPrompt

console = Console()


def prompt_choice(max_val: int, default: int = 1, msg: str = "Выберите действие") -> int:
    try:
        return IntPrompt.ask(f"\n[bold cyan]{msg}[/bold cyan]", default=default)
    except (ValueError, EOFError, KeyboardInterrupt):
        return -1


def prompt_after_result() -> int:
    console.print()
    console.print(
        "  [dim]Действия:[/dim]  "
        "[bold #6c5ce7]1[/] Карта   "
        "[bold #6c5ce7]2[/] Сохранить отчёт   "
        "[bold #6c5ce7]3[/] Добавить в расследование   "
        "[bold #6c5ce7]4[/] Назад"
    )
    try:
        return IntPrompt.ask("[bold cyan]Выбор[/bold cyan]", default=4)
    except (ValueError, EOFError, KeyboardInterrupt):
        return 4


def prompt_ip() -> str:
    return Prompt.ask("\n[bold cyan]IP-адрес[/bold cyan]").strip()


def prompt_coords() -> str:
    return Prompt.ask("\n[bold cyan]Широта и долгота[/bold cyan] (55.7558 37.6173)").strip()


def prompt_place() -> str:
    return Prompt.ask("\n[bold cyan]Название места или адрес[/bold cyan]").strip()


def prompt_domain() -> str:
    return Prompt.ask("\n[bold cyan]Доменное имя[/bold cyan] (example.com)").strip()


def prompt_two_coords():
    c1 = Prompt.ask("[bold cyan]Точка 1 (широта долгота)[/bold cyan]").strip()
    c2 = Prompt.ask("[bold cyan]Точка 2 (широта долгота)[/bold cyan]").strip()
    return c1, c2
