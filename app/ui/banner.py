import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.config import get

console = Console()


def get_banner_text() -> str:
    product = get("branding.logo_text", "solvnox")
    return (
        f"\n"
        f"  [bold white]◇[/bold white]  [bold white]{product}[/bold white]\n"
        f"\n"
        f"  [dim]GEOINT / OSINT[/dim] [#6c5ce7]•[/#6c5ce7] [dim]Геопространственная разведка[/dim]\n"
        f"  [dim]IP • Домены • Координаты • Места • Карты[/dim]\n"
    )


def show_animated_startup():
    steps = [
        ("[dim]    ◇ Загрузка модулей...[/dim]", 0.12),
        ("[dim]   ◇◇ Инициализация сервисов...[/dim]", 0.12),
        ("[dim]  ◇◇◇ Подключение к данным...[/dim]", 0.15),
        ("[green]    ✓ Готов к работе[/green]", 0.25),
    ]
    for text, delay in steps:
        console.print(text)
        time.sleep(delay)


def show_banner():
    name = get("app.name", "solvnox GEOINT")
    version = get("app.version", "0")
    text = get_banner_text()
    console.print(Panel(text, border_style="#6c5ce7", padding=(0, 2)))
    console.print(f"  [dim]{name} v{version} | Приблизительная геолокация | Публичные данные[/dim]")
    console.print()


def _build_menu_table(items: list) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 1), pad_edge=False)
    table.add_column(style="bold #6c5ce7", width=4, justify="right")
    table.add_column(style="white", no_wrap=True)
    for num, label in items:
        table.add_row(f"[{num}]", label)
    return table


def show_main_menu():
    items = [
        ("1", "IP-анализ"),
        ("2", "Анализ домена / WHOIS / DNS"),
        ("3", "Поиск по координатам"),
        ("4", "Поиск по названию места"),
        ("5", "GEOINT-инструменты"),
        ("6", "OSINT-инструменты"),
        ("7", "Работа с картой"),
        ("8", "История и отчёты"),
        ("9", "Настройки"),
        ("0", "Выход"),
    ]
    table = _build_menu_table(items)
    console.print(Panel(table, title="[bold]Главное меню[/bold]", border_style="#4a4a6a", padding=(1, 2)))


def show_submenu(title: str, items: list, border_style: str = "#4a4a6a"):
    console.print()
    table = _build_menu_table(items)
    console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style=border_style, padding=(1, 2)))
