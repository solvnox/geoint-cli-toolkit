from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.models.geo_result import GeoResult, DomainResult
from app.services.geoint_tools import google_maps_link, osm_link, yandex_maps_link

console = Console()


def _row(table: Table, label: str, value, style: str = ""):
    if value is not None and str(value).strip():
        table.add_row(label, str(value), style=style)


def render_geo_result(geo: GeoResult, title: str = "Результат геолокации"):
    table = Table(show_header=True, header_style="bold #6c5ce7", box=None)
    table.add_column("Параметр", style="dim", width=18)
    table.add_column("Значение", style="white")
    _row(table, "Запрос", geo.query)
    _row(table, "Страна", geo.country)
    _row(table, "Регион", geo.region)
    _row(table, "Город", geo.city)
    _row(table, "Адрес", geo.address)
    _row(table, "Индекс", geo.postal_code)
    _row(table, "Широта", f"{geo.latitude:.6f}" if geo.latitude is not None else None)
    _row(table, "Долгота", f"{geo.longitude:.6f}" if geo.longitude is not None else None)
    _row(table, "Часовой пояс", geo.timezone)
    _row(table, "Провайдер (ISP)", geo.isp)
    _row(table, "ASN/Организация", geo.asn or geo.org)
    if geo.raw.get("ptr"):
        _row(table, "Reverse DNS", geo.raw["ptr"])
    console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="green", padding=(1, 2)))
    if geo.note:
        console.print(f"[dim italic]⚠ {geo.note}[/dim italic]")
        console.print()
    if geo.has_coordinates():
        gm = google_maps_link(geo.latitude, geo.longitude)
        om = osm_link(geo.latitude, geo.longitude)
        ym = yandex_maps_link(geo.latitude, geo.longitude)
        console.print(f"[dim]Ссылки:[/dim] [link={gm}]Google[/link] [link={om}]OSM[/link] [link={ym}]Yandex[/link]")
        console.print()


def render_domain_result(result: DomainResult):
    if result.error:
        console.print(Panel(f"[red]{result.error}[/red]", title="[bold]Ошибка[/bold]", border_style="red", padding=(1, 2)))
        return
    t1 = Table(show_header=True, header_style="bold #6c5ce7", box=None)
    t1.add_column("Параметр", style="dim", width=18)
    t1.add_column("Значение", style="white")
    t1.add_row("Домен", result.domain)
    ips = ", ".join(result.resolved_ips) if result.resolved_ips else (result.resolved_ip or "—")
    t1.add_row("IP", ips)
    console.print(Panel(t1, title="[bold]Разрешение домена[/bold]", border_style="#4a4a6a", padding=(1, 2)))
    if result.geo:
        render_geo_result(result.geo, "Геолокация IP")
    if result.whois_snippet:
        console.print(Panel(result.whois_snippet, title="[bold]WHOIS / RDAP[/bold]", border_style="dim", padding=(1, 2)))
    if result.dns:
        t2 = Table(show_header=True, header_style="bold #6c5ce7", box=None)
        t2.add_column("Тип", style="dim")
        t2.add_column("Записи", style="white")
        for rtype, vals in result.dns.items():
            if vals:
                t2.add_row(rtype, ", ".join(str(v)[:60] for v in vals[:5]))
        if t2.row_count > 0:
            console.print(Panel(t2, title="[bold]DNS[/bold]", border_style="dim", padding=(1, 2)))
        console.print()
