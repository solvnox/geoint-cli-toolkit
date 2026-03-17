from pathlib import Path
from datetime import datetime
from typing import Optional, List, Union
import html

import folium
from folium import Circle, PolyLine, DivIcon
from folium.plugins import Fullscreen, MiniMap, MousePosition, MeasureControl

from app.core.config import get
from app.core.logger import log
from app.models.geo_result import GeoResult
from app.branding.assets import header_html, footer_html, STYLES


def _ensure_maps_dir() -> Path:
    p = Path(get("paths.maps") or "reports/maps")
    p.mkdir(parents=True, exist_ok=True)
    return p


QUERY_TYPE_LABELS = {
    "ip": "IP",
    "domain": "Domain",
    "coords": "Coords",
    "place": "Place",
    "multi": "Point",
}

QUERY_TYPE_COLORS = {
    "ip": "#e74c3c",
    "domain": "#3498db",
    "coords": "#2ecc71",
    "place": "#f39c12",
    "multi": "#9b59b6",
}

MARKER_COLORS = {
    "ip": "red",
    "domain": "blue",
    "coords": "green",
    "place": "orange",
    "multi": "purple",
}


def _popup_html(geo: GeoResult, index: int = None) -> str:
    def esc(s):
        return html.escape(str(s)) if s else ""
    qt = geo.query_type or "unknown"
    label = QUERY_TYPE_LABELS.get(qt, qt.upper())
    color = QUERY_TYPE_COLORS.get(qt, "#6c5ce7")
    lines = []
    header_parts = []
    if index is not None:
        header_parts.append(f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">#{index} {label}</span>')
    else:
        header_parts.append(f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">{label}</span>')
    lines.append(" ".join(header_parts))
    if geo.city:
        lines.append(f"<b>Город:</b> {esc(geo.city)}")
    if geo.region:
        lines.append(f"<b>Регион:</b> {esc(geo.region)}")
    if geo.country:
        lines.append(f"<b>Страна:</b> {esc(geo.country)}")
    if geo.address:
        lines.append(f"<b>Адрес:</b> {esc(geo.address)}")
    if geo.latitude is not None and geo.longitude is not None:
        lines.append(f"<b>Координаты:</b> {geo.latitude:.6f}, {geo.longitude:.6f}")
    if geo.isp:
        lines.append(f"<b>ISP:</b> {esc(geo.isp)}")
    if geo.asn:
        lines.append(f"<b>ASN:</b> {esc(geo.asn)}")
    if geo.query:
        lines.append(f"<b>Запрос:</b> {esc(geo.query)}")
    if geo.note:
        lines.append(f"<small><i>{esc(geo.note)}</i></small>")
    return "<br>".join(lines) if lines else "—"


TILE_LAYERS = [
    ("OpenStreetMap", "OpenStreetMap", None),
    ("CartoDB Dark", "CartoDB dark_matter", None),
]


def _numbered_icon(index: int, color: str = "#e74c3c") -> DivIcon:
    return DivIcon(
        icon_size=(28, 28),
        icon_anchor=(14, 14),
        html=f'<div style="background:{color};color:#fff;border-radius:50%;width:28px;height:28px;'
             f'text-align:center;line-height:28px;font-size:13px;font-weight:700;'
             f'border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.4);">{index}</div>',
    )


def generate_map(
    geo: Union[GeoResult, List[GeoResult]],
    add_radius: bool = False,
    filename: Optional[str] = None,
    tile_style: str = None,
    draw_lines: bool = False,
) -> Optional[str]:
    geos = [geo] if isinstance(geo, GeoResult) else geo
    valid = [g for g in geos if g.has_coordinates()]
    if not valid:
        log.warning("No coordinates for map")
        return None
    first = valid[0]
    lat, lon = first.latitude, first.longitude
    zoom = get("map.default_zoom", 14)
    if len(valid) > 1:
        zoom = min(zoom, 10)
    radius = get("map.ip_radius_meters", 50000) if add_radius and first.query_type == "ip" else None
    tiles = tile_style or get("map.default_tiles", "OpenStreetMap")
    default_idx = next((i for i, (n, _, _) in enumerate(TILE_LAYERS) if n == tiles), 0)
    default_name, default_url, default_attr = TILE_LAYERS[default_idx]
    try:
        m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles=None)
        if default_attr:
            folium.TileLayer(tiles=default_url, attr=default_attr, name=default_name).add_to(m)
        else:
            folium.TileLayer(tiles=default_url, name=default_name).add_to(m)
        for name, url, attr in TILE_LAYERS:
            if name == default_name:
                continue
            if attr:
                folium.TileLayer(tiles=url, attr=attr, name=name).add_to(m)
            else:
                folium.TileLayer(tiles=url, name=name).add_to(m)
        folium.LayerControl().add_to(m)
        Fullscreen().add_to(m)
        MiniMap(toggle_display=True).add_to(m)
        MousePosition(
            position="bottomleft",
            separator=" | ",
            prefix="Координаты:",
            lat_formatter="function(num) {return L.Util.formatNum(num, 5);}",
            lng_formatter="function(num) {return L.Util.formatNum(num, 5);}",
        ).add_to(m)
        MeasureControl(
            position="bottomleft",
            primary_length_unit="kilometers",
            secondary_length_unit="meters",
            primary_area_unit="sqkilometers",
        ).add_to(m)
    except Exception as e:
        log.warning("Map init failed: %s", e)
        m = folium.Map(location=[lat, lon], zoom_start=zoom, tiles="OpenStreetMap")

    use_numbers = len(valid) > 1
    for i, g in enumerate(valid, 1):
        popup = folium.Popup(_popup_html(g, index=i if use_numbers else None), max_width=340)
        tooltip = g.city or g.region or g.country or f"{g.latitude:.4f}, {g.longitude:.4f}"
        if use_numbers:
            tooltip = f"#{i} {tooltip}"
        qt = g.query_type or "multi"
        if use_numbers:
            icon = _numbered_icon(i, QUERY_TYPE_COLORS.get(qt, "#6c5ce7"))
        else:
            icon = folium.Icon(color=MARKER_COLORS.get(qt, "red"), icon="info-sign")
        folium.Marker(
            location=[g.latitude, g.longitude],
            popup=popup,
            tooltip=tooltip,
            icon=icon,
        ).add_to(m)

    if radius and first.query_type == "ip":
        Circle(
            location=[first.latitude, first.longitude],
            radius=radius,
            color="#6c5ce7",
            fill=True,
            fill_color="#6c5ce7",
            fill_opacity=0.12,
            popup="Приблизительная область (IP)",
        ).add_to(m)

    if draw_lines and len(valid) > 1:
        pts = [[g.latitude, g.longitude] for g in valid]
        PolyLine(pts, color="#6c5ce7", weight=2, opacity=0.7, dash_array="8").add_to(m)

    if len(valid) > 1:
        lats = [g.latitude for g in valid]
        lons = [g.longitude for g in valid]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=[30, 30])

    header = header_html("solvnox", "GEOINT Карта", use_map_logo=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    foot = footer_html(first.query_type, first.query, ts)
    m.get_root().html.add_child(folium.Element(f"<style>{STYLES}</style>"))
    m.get_root().html.add_child(folium.Element(f'<div class="report-header-wrap">{header}</div>'))
    m.get_root().html.add_child(folium.Element(f'<div class="report-footer-wrap">{foot}</div>'))

    maps_dir = _ensure_maps_dir()
    base = filename or f"map_{first.query_type}_{str(first.query)[:25].replace('.', '_').replace(' ', '_')}"
    base = "".join(c for c in base if c.isalnum() or c in "_-.")
    fp = maps_dir / f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    try:
        m.save(str(fp))
        return str(fp)
    except OSError as e:
        log.warning("Map save failed: %s", e)
        return None
