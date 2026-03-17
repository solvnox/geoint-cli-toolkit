#!/usr/bin/env python3
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from app.core.config import load_config, get
from app.core.logger import log
from app.ui.banner import show_banner, show_main_menu, show_animated_startup, show_submenu
from app.ui.tables import render_geo_result, render_domain_result
from app.ui.prompts import (
    prompt_choice,
    prompt_after_result,
    prompt_ip,
    prompt_coords,
    prompt_place,
    prompt_domain,
    prompt_two_coords,
)
from app.ui.spinner import spinner
from app.utils.validators import is_valid_ip, parse_coordinates, is_valid_domain, normalize_domain
from app.services.ip_service import lookup_ip
from app.services.geocode_service import geocode_place, reverse_geocode
from app.services.domain_service import lookup_domain
from app.services.geoint_tools import (
    haversine_distance,
    bearing,
    google_maps_link,
    osm_link,
    yandex_maps_link,
    decimal_to_dms,
    bounding_box,
    nearby_places,
    timezone_by_coords,
)
from app.reports.map_generator import generate_map
from app.reports.report_saver import save_geo_report, save_domain_report
from app.geoint.elevation import get_elevation
from app.geoint.sun_position import sun_info
from app.utils.history import add_to_history, load_history
from app.storage.favorites import load_favorites, add_favorite
from app.storage.sessions import create_session, add_to_session, list_sessions, load_session
from app.models.geo_result import GeoResult
from app.services.image_search import reverse_image_links, reverse_image_upload_pages, image_to_base64
from app.services.face_search import face_search_links, detect_face

console = Console()

_investigation_points = []


def run_ip_analysis():
    ip = prompt_ip()
    if not ip:
        console.print("[red]Введите IP.[/red]")
        return
    if not is_valid_ip(ip):
        console.print("[red]Неверный формат IP.[/red]")
        return
    with spinner("Анализ IP..."):
        geo = lookup_ip(ip)
    if not geo:
        console.print(Panel(
            "[red]Не удалось получить геолокацию. Приватный IP или лимит API.[/red]",
            title="[bold]Ошибка[/bold]",
            border_style="red",
            padding=(1, 2),
        ))
        return
    if geo.is_private:
        console.print(Panel(geo.note or "Приватный IP", title="[bold]Результат[/bold]", border_style="yellow", padding=(1, 2)))
        return
    summary = geo.city or geo.region or geo.country or "?"
    add_to_history(ip, "ip", summary)
    render_geo_result(geo, "IP-анализ")
    _post_result_menu(geo, add_radius=True)


def run_domain_analysis():
    domain = prompt_domain()
    if not domain:
        console.print("[red]Введите домен.[/red]")
        return
    domain = normalize_domain(domain)
    if not is_valid_domain(domain):
        console.print("[red]Неверный формат домена.[/red]")
        return
    with spinner("Разрешение домена, WHOIS, DNS..."):
        result = lookup_domain(domain)
    add_to_history(domain, "domain", result.resolved_ip or result.error or "")
    render_domain_result(result)
    if result.geo and result.geo.has_coordinates():
        choice = prompt_after_result()
        if choice == 1:
            _do_show_map(result.geo, add_radius=True)
        elif choice == 2:
            paths = save_domain_report(result)
            _show_saved(paths)
        elif choice == 3:
            _investigation_points.append(result.geo)
            console.print(f"[green]Добавлено в расследование. Точек: {len(_investigation_points)}[/green]")


def run_coords_search():
    raw = prompt_coords()
    lat, lon, err = parse_coordinates(raw)
    if err:
        console.print(f"[red]{err}[/red]")
        return
    with spinner("Обратное геокодирование..."):
        geo = reverse_geocode(lat, lon)
    if not geo:
        console.print(Panel("[red]Место не найдено.[/red]", title="[bold]Ошибка[/bold]", border_style="red", padding=(1, 2)))
        return
    add_to_history(f"{lat},{lon}", "coords", geo.address or f"{lat},{lon}")
    render_geo_result(geo)
    _post_result_menu(geo, add_radius=False)


def run_place_search():
    place = prompt_place()
    if not place:
        console.print("[red]Введите место.[/red]")
        return
    with spinner("Геокодирование..."):
        geo = geocode_place(place)
    if not geo:
        console.print(Panel("[red]Место не найдено.[/red]", title="[bold]Ошибка[/bold]", border_style="red", padding=(1, 2)))
        return
    add_to_history(place, "place", geo.address or geo.city or place)
    render_geo_result(geo)
    _post_result_menu(geo, add_radius=False)


def run_geoint_tools():
    show_submenu("GEOINT-инструменты", [
        ("1", "Расстояние между точками"),
        ("2", "Азимут между точками"),
        ("3", "Координаты \u2192 DMS"),
        ("4", "Ограничивающий прямоугольник"),
        ("5", "Окрестности места"),
        ("6", "Часовой пояс по координатам"),
        ("7", "Ссылки на карты"),
        ("8", "Высота над уровнем моря"),
        ("9", "Анализ положения солнца"),
        ("0", "Назад"),
    ])
    ch = prompt_choice(9, 0, "Выбор")
    if ch == 0:
        return
    if ch == 1:
        c1, c2 = prompt_two_coords()
        lat1, lon1, e1 = parse_coordinates(c1)
        lat2, lon2, e2 = parse_coordinates(c2)
        if e1 or e2:
            console.print("[red]Проверьте формат координат.[/red]")
            return
        dist = haversine_distance(lat1, lon1, lat2, lon2)
        console.print(Panel(
            f"[bold]Расстояние:[/bold] {dist:.2f} км ({dist * 1000:.0f} м)",
            title="Результат", border_style="green", padding=(1, 2),
        ))
    elif ch == 2:
        c1, c2 = prompt_two_coords()
        lat1, lon1, e1 = parse_coordinates(c1)
        lat2, lon2, e2 = parse_coordinates(c2)
        if e1 or e2:
            console.print("[red]Проверьте формат координат.[/red]")
            return
        b = bearing(lat1, lon1, lat2, lon2)
        console.print(Panel(f"[bold]Азимут:[/bold] {b:.1f}°", title="Результат", border_style="green", padding=(1, 2)))
    elif ch == 3:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        dms_lat, dms_lon = decimal_to_dms(lat, lon)
        console.print(Panel(f"Широта: {dms_lat}\nДолгота: {dms_lon}", title="DMS", border_style="green", padding=(1, 2)))
    elif ch == 4:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        r = float(Prompt.ask("[bold cyan]Радиус (км)[/bold cyan]", default="10"))
        s, w, n, e = bounding_box(lat, lon, r)
        console.print(Panel(f"Юг: {s:.4f}\nЗапад: {w:.4f}\nСевер: {n:.4f}\nВосток: {e:.4f}", title="Bbox", border_style="green", padding=(1, 2)))
    elif ch == 5:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        with spinner("Поиск..."):
            places = nearby_places(lat, lon)
        if not places:
            console.print("[dim]Не найдено.[/dim]")
            return
        t = Table(show_header=True, header_style="bold")
        t.add_column("Тип")
        t.add_column("Название")
        for p in places:
            t.add_row(p.get("type", ""), p.get("name", ""))
        console.print(Panel(t, title="Окрестности", border_style="green", padding=(1, 2)))
    elif ch == 6:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        with spinner("Запрос..."):
            tz = timezone_by_coords(lat, lon)
        console.print(Panel(f"[bold]Часовой пояс:[/bold] {tz or '—'}", title="Результат", border_style="green", padding=(1, 2)))
    elif ch == 7:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        gm, om, ym = google_maps_link(lat, lon), osm_link(lat, lon), yandex_maps_link(lat, lon)
        console.print(f"Google: [link={gm}]{gm}[/link]")
        console.print(f"OSM: [link={om}]{om}[/link]")
        console.print(f"Yandex: [link={ym}]{ym}[/link]")
    elif ch == 8:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        with spinner("Запрос высоты..."):
            elev = get_elevation(lat, lon)
        if elev is not None:
            console.print(Panel(f"[bold]Высота:[/bold] {elev:.1f} м над уровнем моря", title="Результат", border_style="green", padding=(1, 2)))
        else:
            console.print(Panel("[yellow]Не удалось получить данные о высоте.[/yellow]", border_style="yellow", padding=(1, 2)))
    elif ch == 9:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        dt_str = Prompt.ask("[bold cyan]Дата и время UTC[/bold cyan] (ГГГГ-ММ-ДД ЧЧ:ММ, Enter — сейчас)", default="").strip()
        dt = None
        if dt_str:
            try:
                from datetime import datetime as _dt, timezone as _tz
                dt = _dt.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=_tz.utc)
            except ValueError:
                console.print("[red]Неверный формат. Используйте ГГГГ-ММ-ДД ЧЧ:ММ[/red]")
                return
        with spinner("Расчёт..."):
            info = sun_info(lat, lon, dt)
        if not info:
            console.print(Panel("[yellow]Не удалось рассчитать положение солнца.[/yellow]", border_style="yellow", padding=(1, 2)))
            return
        t = Table(show_header=True, header_style="bold")
        t.add_column("Параметр", style="dim", width=22)
        t.add_column("Значение", style="white")
        t.add_row("Рассвет", info["dawn"])
        t.add_row("Восход", info["sunrise"])
        t.add_row("Полдень", info["noon"])
        t.add_row("Закат", info["sunset"])
        t.add_row("Сумерки", info["dusk"])
        t.add_row("Долгота дня", info["day_length"])
        t.add_row("Высота солнца", f"{info['solar_elevation']}°")
        t.add_row("Азимут солнца", f"{info['solar_azimuth']}°")
        console.print(Panel(t, title="Положение солнца", border_style="green", padding=(1, 2)))


def run_map_menu():
    show_submenu("Работа с картой", [
        ("1", "Карта по координатам"),
        ("2", "Карта нескольких точек"),
        ("3", f"Карта расследования ({len(_investigation_points)} точек)"),
        ("0", "Назад"),
    ])
    ch = prompt_choice(3, 0, "Выбор")
    if ch == 0:
        return
    if ch == 1:
        raw = prompt_coords()
        lat, lon, err = parse_coordinates(raw)
        if err:
            console.print(f"[red]{err}[/red]")
            return
        geo = GeoResult(query=f"{lat},{lon}", query_type="coords", latitude=lat, longitude=lon, address=f"{lat}, {lon}")
        _do_show_map(geo, add_radius=False)
    elif ch == 2:
        console.print("[dim]Введите координаты точек (пустая строка — конец):[/dim]")
        geos = []
        while True:
            raw = input("  Точка: ").strip()
            if not raw:
                break
            lat, lon, err = parse_coordinates(raw)
            if err:
                console.print(f"[red]{err}[/red]")
                continue
            geos.append(GeoResult(query=raw, query_type="multi", latitude=lat, longitude=lon))
        if len(geos) < 2:
            console.print("[yellow]Нужно минимум 2 точки.[/yellow]")
            return
        path = generate_map(geos, add_radius=False, draw_lines=True)
        if path:
            _open_map(path)
        else:
            console.print("[red]Не удалось создать карту.[/red]")
    elif ch == 3:
        if not _investigation_points:
            console.print(Panel("[yellow]Нет точек. Добавьте точки через результат анализа (IP, координаты, место).[/yellow]",
                                border_style="yellow", padding=(1, 2)))
            return
        console.print(f"[bold]Точек в расследовании: {len(_investigation_points)}[/bold]")
        for i, g in enumerate(_investigation_points, 1):
            label = g.city or g.address or g.query
            console.print(f"  [{i}] {g.query_type.upper()}: {label}")
        draw = Confirm.ask("Соединить точки линиями?", default=True)
        path = generate_map(_investigation_points, add_radius=False, draw_lines=draw)
        if path:
            console.print(f"[green]Карта: {path}[/green]")
            _open_map(path)
        else:
            console.print("[red]Не удалось создать карту.[/red]")
        if Confirm.ask("Очистить точки расследования?", default=False):
            _investigation_points.clear()
            console.print("[dim]Точки очищены.[/dim]")


def run_history_reports():
    show_submenu("История и отчёты", [
        ("1", "История запросов"),
        ("2", "Фильтр по типу"),
        ("3", "Сессия расследования"),
        ("0", "Назад"),
    ])
    ch = prompt_choice(3, 0, "Выбор")
    if ch == 0:
        return
    if ch == 1:
        items = load_history(30)
        if not items:
            console.print(Panel("[dim]История пуста.[/dim]", border_style="dim", padding=(1, 2)))
            return
        t = Table(show_header=True, header_style="bold")
        t.add_column("Время", style="dim", width=19)
        t.add_column("Тип", width=10)
        t.add_column("Запрос", width=30)
        t.add_column("Результат", width=35)
        for h in items:
            ts = (h.get("timestamp") or "")[:19].replace("T", " ")
            t.add_row(ts, h.get("query_type", ""), (h.get("query") or "")[:28], (h.get("summary") or "")[:33])
        console.print(Panel(t, title="[bold]История[/bold]", border_style="#4a4a6a", padding=(1, 2)))
    elif ch == 2:
        show_submenu("Тип записи", [
            ("1", "ip"),
            ("2", "domain"),
            ("3", "coords"),
            ("4", "place"),
        ])
        tch = prompt_choice(4, 1, "Тип")
        m = {1: "ip", 2: "domain", 3: "coords", 4: "place"}
        qtype = m.get(tch, "ip")
        items = load_history(30, query_type=qtype)
        if not items:
            console.print(f"[dim]Нет записей типа {qtype}.[/dim]")
            return
        t = Table(show_header=True, header_style="bold")
        t.add_column("Время")
        t.add_column("Запрос")
        t.add_column("Результат")
        for h in items:
            ts = (h.get("timestamp") or "")[:19].replace("T", " ")
            t.add_row(ts, (h.get("query") or "")[:40], (h.get("summary") or "")[:40])
        console.print(Panel(t, title=f"История ({qtype})", border_style="#4a4a6a", padding=(1, 2)))
    elif ch == 3:
        sessions = list_sessions()
        if sessions:
            console.print("[bold]Сессии:[/bold]")
            for i, s in enumerate(sessions[:10], 1):
                console.print(f"  [{i}] {s.get('name', s.get('id', '?'))}")
        name = input("Имя новой сессии (Enter — пропустить): ").strip()
        sid = create_session(name)
        if sid:
            console.print(f"[green]Сессия создана: {sid}[/green]")


def run_settings():
    show_submenu("Настройки", [
        ("1", "Автооткрытие карты в браузере"),
        ("2", "Избранные места"),
        ("0", "Назад"),
    ])
    ch = prompt_choice(2, 0, "Выбор")
    if ch == 0:
        return
    if ch == 1:
        cur = get("ui.browser_auto_open", True)
        console.print(f"Текущее: {'Да' if cur else 'Нет'}")
        toggle = Confirm.ask("Включить автооткрытие?", default=cur)
    elif ch == 2:
        favs = load_favorites()
        if favs:
            for i, f in enumerate(favs, 1):
                console.print(f"  [{i}] {f.get('name')} — {f.get('lat')}, {f.get('lon')}")
        console.print("[dim]Добавить: используйте 'Добавить в избранное' после результата геолокации.[/dim]")


def run_osint_tools():
    show_submenu("OSINT-инструменты", [
        ("1", "Обратный поиск изображений"),
        ("2", "Поиск по лицу"),
        ("0", "Назад"),
    ])
    ch = prompt_choice(2, 0, "Выбор")
    if ch == 0:
        return
    if ch == 1:
        _run_reverse_image_search()
    elif ch == 2:
        _run_face_search()


def _run_reverse_image_search():
    show_submenu("Обратный поиск изображений", [
        ("1", "По URL изображения"),
        ("2", "По локальному файлу"),
    ])
    ch = prompt_choice(2, 1, "Выбор")
    if ch == 1:
        url = Prompt.ask("[bold cyan]URL изображения[/bold cyan]").strip()
        if not url:
            console.print("[red]Введите URL.[/red]")
            return
        links = reverse_image_links(url)
        t = Table(show_header=True, header_style="bold")
        t.add_column("Сервис", width=20)
        t.add_column("Ссылка")
        for lnk in links:
            display = lnk["url"]
            if len(display) > 70:
                display = display[:70] + "..."
            t.add_row(lnk["name"], f"[link={lnk['url']}]{display}[/link]")
        console.print(Panel(t, title="[bold]Обратный поиск[/bold]", border_style="green", padding=(1, 2)))
        if Confirm.ask("Открыть все ссылки в браузере?", default=False):
            for lnk in links:
                try:
                    webbrowser.open(lnk["url"])
                except Exception:
                    pass
    elif ch == 2:
        path = Prompt.ask("[bold cyan]Путь к файлу изображения[/bold cyan]").strip()
        if not path or not Path(path).exists():
            console.print("[red]Файл не найден.[/red]")
            return
        links = reverse_image_upload_pages()
        console.print(Panel(
            "[dim]Для локального файла загрузите изображение вручную на каждый сервис.[/dim]",
            border_style="dim", padding=(1, 2),
        ))
        t = Table(show_header=True, header_style="bold")
        t.add_column("Сервис", width=20)
        t.add_column("Страница загрузки")
        for lnk in links:
            t.add_row(lnk["name"], f"[link={lnk['url']}]{lnk['url']}[/link]")
        console.print(Panel(t, title="[bold]Страницы загрузки[/bold]", border_style="green", padding=(1, 2)))
        if Confirm.ask("Открыть все ссылки в браузере?", default=False):
            for lnk in links:
                try:
                    webbrowser.open(lnk["url"])
                except Exception:
                    pass


def _run_face_search():
    show_submenu("Поиск по лицу", [
        ("1", "По URL изображения"),
        ("2", "По локальному файлу"),
    ])
    ch = prompt_choice(2, 1, "Выбор")
    image_url = ""
    if ch == 1:
        image_url = Prompt.ask("[bold cyan]URL изображения с лицом[/bold cyan]").strip()
        if not image_url:
            console.print("[red]Введите URL.[/red]")
            return
    elif ch == 2:
        local_path = Prompt.ask("[bold cyan]Путь к файлу изображения[/bold cyan]").strip()
        if not local_path or not Path(local_path).exists():
            console.print("[red]Файл не найден.[/red]")
            return
        with spinner("Поиск лица на изображении..."):
            face_crop = detect_face(local_path)
        if face_crop:
            console.print(f"[green]Лицо обнаружено и вырезано: {face_crop}[/green]")
        else:
            console.print("[dim]Автоматическое обнаружение лица недоступно или лицо не найдено.[/dim]")
    else:
        return
    links = face_search_links(image_url)
    t = Table(show_header=True, header_style="bold")
    t.add_column("Сервис", width=20)
    t.add_column("Ссылка / Описание")
    for lnk in links:
        display = lnk["url"]
        if len(display) > 70:
            display = display[:70] + "..."
        t.add_row(lnk["name"], f"[link={lnk['url']}]{display}[/link]")
    console.print(Panel(t, title="[bold]Поиск по лицу[/bold]", border_style="green", padding=(1, 2)))
    if Confirm.ask("Открыть ссылки в браузере?", default=False):
        for lnk in links:
            try:
                webbrowser.open(lnk["url"])
            except Exception:
                pass


def _post_result_menu(geo, add_radius: bool = False):
    choice = prompt_after_result()
    if choice == 1:
        _do_show_map(geo, add_radius=add_radius)
    elif choice == 2:
        paths = save_geo_report(geo)
        _show_saved(paths)
    elif choice == 3:
        _investigation_points.append(geo)
        console.print(f"[green]Добавлено в расследование. Точек: {len(_investigation_points)}[/green]")


def _show_saved(paths: dict):
    if paths:
        console.print(f"[green]Сохранено: {', '.join(paths.values())}[/green]")
    else:
        console.print("[yellow]Не удалось сохранить.[/yellow]")


def _do_show_map(geo, add_radius: bool = False):
    path = generate_map(geo, add_radius=add_radius)
    if not path:
        console.print(Panel("[red]Не удалось создать карту.[/red]", border_style="red", padding=(1, 2)))
        return
    console.print(f"[green]Карта: {path}[/green]")
    _open_map(path)


def _open_map(path: str):
    if get("ui.browser_auto_open", True):
        if Confirm.ask("Открыть в браузере?", default=True):
            try:
                webbrowser.open(f"file://{Path(path).resolve()}")
            except Exception:
                pass


def main():
    load_config()
    show_animated_startup()
    console.print()
    show_banner()
    while True:
        show_main_menu()
        choice = prompt_choice(9, 0, "Выбор")
        if choice == 0:
            console.print("\n[bold #6c5ce7]До свидания![/bold #6c5ce7]")
            break
        elif choice == 1:
            run_ip_analysis()
        elif choice == 2:
            run_domain_analysis()
        elif choice == 3:
            run_coords_search()
        elif choice == 4:
            run_place_search()
        elif choice == 5:
            run_geoint_tools()
        elif choice == 6:
            run_osint_tools()
        elif choice == 7:
            run_map_menu()
        elif choice == 8:
            run_history_reports()
        elif choice == 9:
            run_settings()
        else:
            console.print("[yellow]Выберите 0–9.[/yellow]")


if __name__ == "__main__":
    main()
