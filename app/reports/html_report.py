import json
import html as html_mod
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.core.config import get
from app.core.logger import log
from app.models.geo_result import GeoResult, DomainResult
from app.branding.assets import header_html, footer_html, STYLES


def _ensure_dir() -> Path:
    p = Path(get("paths.reports_html") or "reports/html")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _card(title: str, content: str, card_id: str = "") -> str:
    id_attr = f' id="{card_id}"' if card_id else ""
    return f"""
    <div class="report-card"{id_attr}>
        <h3>{title}</h3>
        <div class="card-content">{content}</div>
    </div>
    """


def _meta_row(label: str, value: str) -> str:
    if not value:
        return ""
    return f'<tr><td class="meta-label">{html_mod.escape(label)}</td><td>{html_mod.escape(str(value))}</td></tr>'


def _geo_section(geo: GeoResult) -> str:
    rows = [
        _meta_row("Запрос", geo.query),
        _meta_row("Страна", geo.country),
        _meta_row("Регион", geo.region),
        _meta_row("Город", geo.city),
        _meta_row("Адрес", geo.address),
        _meta_row("Широта", f"{geo.latitude:.6f}" if geo.latitude else ""),
        _meta_row("Долгота", f"{geo.longitude:.6f}" if geo.longitude else ""),
        _meta_row("Часовой пояс", geo.timezone),
        _meta_row("ISP", geo.isp),
        _meta_row("ASN", geo.asn or geo.org),
    ]
    table = f"<table class='meta-table'><tbody>{''.join(r for r in rows if r)}</tbody></table>"
    if geo.note:
        table += f"<p class='note'>{html_mod.escape(geo.note)}</p>"
    return table


def _query_summary(query_type: str, query: str, timestamp: str = "") -> str:
    if not timestamp:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    type_labels = {"ip": "IP-анализ", "domain": "Домен", "coords": "Координаты", "place": "Место"}
    label = type_labels.get(query_type, query_type.upper() if query_type else "Запрос")
    return f"""
    <div class="query-summary">
        <span class="query-badge">{html_mod.escape(label)}</span>
        <span class="query-value">{html_mod.escape(str(query))}</span>
        <span class="query-time">{html_mod.escape(timestamp)}</span>
    </div>
    """


def _map_links_section(geo: GeoResult) -> str:
    if not geo.has_coordinates():
        return ""
    lat, lon = geo.latitude, geo.longitude
    links = [
        ("Google Maps", f"https://www.google.com/maps?q={lat},{lon}&z=15"),
        ("OpenStreetMap", f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=15/{lat}/{lon}"),
        ("Yandex Maps", f"https://yandex.ru/maps/?pt={lon},{lat}&z=15"),
    ]
    buttons = "".join(
        f'<a href="{html_mod.escape(url)}" target="_blank" class="map-btn">{html_mod.escape(name)}</a>'
        for name, url in links
    )
    return _card("Карта", f'<div class="map-links">{buttons}</div>')


def _technical_section(raw: dict) -> str:
    if not raw:
        return ""
    try:
        raw_json = json.dumps(raw, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        raw_json = str(raw)
    return f"""
    <details class="technical-section">
        <summary>Технические данные (JSON)</summary>
        <pre class="raw-json">{html_mod.escape(raw_json)}</pre>
    </details>
    """


NODE_COLORS = {
    "query": "#8b7cf6",
    "ip": "#c27066",
    "domain": "#5b8ec2",
    "asn": "#c49a5c",
    "provider": "#b5a044",
    "country": "#5ba577",
    "city": "#4fa5a0",
    "location": "#5ba577",
    "coords": "#9b7cb5",
    "dns": "#6b8bc0",
}

NODE_ICONS = {
    "query": "\u25ce",
    "ip": "\u2316",
    "domain": "\u2609",
    "asn": "\u2b22",
    "provider": "\u2699",
    "country": "\u2691",
    "city": "\u25c6",
    "location": "\u25c6",
    "coords": "\u2295",
    "dns": "\u25a4",
}

NODE_TYPE_LABELS = {
    "query": "Запрос",
    "ip": "IP",
    "domain": "Домен",
    "asn": "ASN",
    "provider": "ISP",
    "country": "Страна",
    "city": "Город",
    "location": "Регион",
    "coords": "Координаты",
    "dns": "DNS",
}


def _build_relationship_graph(geo: GeoResult = None, domain_result: DomainResult = None) -> dict:
    nodes = []
    links = []
    seen = set()

    def add_node(nid: str, label: str, ntype: str, is_root: bool = False):
        if nid not in seen and label:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "type": ntype, "root": is_root})

    def add_link(src: str, tgt: str, label: str = ""):
        if src in seen and tgt in seen:
            links.append({"source": src, "target": tgt, "label": label})

    if domain_result:
        add_node("domain", domain_result.domain, "domain", is_root=True)
        for ip in (domain_result.resolved_ips or []):
            nid = f"ip_{ip}"
            add_node(nid, ip, "ip")
            add_link("domain", nid, "resolves_to")
        if domain_result.dns:
            for rtype, vals in domain_result.dns.items():
                if rtype == "NS" and vals:
                    for ns in vals[:4]:
                        nid = f"ns_{ns}"
                        add_node(nid, str(ns)[:40], "dns")
                        add_link("domain", nid, "uses_nameserver")
                elif rtype == "MX" and vals:
                    for mx in vals[:3]:
                        nid = f"mx_{mx}"
                        add_node(nid, str(mx)[:40], "dns")
                        add_link("domain", nid, "mail_exchange")
        geo = domain_result.geo or geo

    if geo:
        query_id = "query"
        if geo.query_type == "ip":
            query_id = f"ip_{geo.query}"
            add_node(query_id, geo.query, "ip", is_root=not domain_result)
        elif not domain_result:
            add_node(query_id, geo.query, "query", is_root=True)

        if geo.country:
            add_node("country", geo.country, "country")
            add_link(query_id, "country", "located_in")
        if geo.region:
            add_node("region", geo.region, "location")
            parent = "country" if geo.country else query_id
            add_link(parent, "region", "located_in")
        if geo.city:
            add_node("city", geo.city, "city")
            parent = "region" if geo.region else ("country" if geo.country else query_id)
            add_link(parent, "city", "located_in")
        if geo.has_coordinates():
            coord_label = f"{geo.latitude:.4f}, {geo.longitude:.4f}"
            add_node("coords", coord_label, "coords")
            parent = "city" if geo.city else query_id
            add_link(parent, "coords", "located_at")
        if geo.isp:
            add_node("isp", geo.isp, "provider")
            add_link(query_id, "isp", "belongs_to")
        if geo.asn:
            add_node("asn", geo.asn, "asn")
            add_link(query_id, "asn", "belongs_to")

    return {"nodes": nodes, "links": links}


GRAPH_JS = """
(function() {
    const data = __DATA__;
    const typeColors = __COLORS__;
    const typeIcons = __ICONS__;

    const container = document.getElementById('relationship-graph');
    if (!container) return;
    const width = container.clientWidth || 900;
    const height = 520;

    const nodeR = d => d.root ? 26 : 18;

    const svg = d3.select('#relationship-graph')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .style('display', 'block');

    const defs = svg.append('defs');

    const glowFilter = defs.append('filter').attr('id', 'nodeGlow')
        .attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
    const merge = glowFilter.append('feMerge');
    merge.append('feMergeNode').attr('in', 'blur');
    merge.append('feMergeNode').attr('in', 'SourceGraphic');

    defs.append('marker').attr('id', 'arrow')
        .attr('viewBox', '0 -4 8 8').attr('refX', 8).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-3L8,0L0,3').attr('fill', '#3a3a5a');

    const g = svg.append('g');

    const zoom = d3.zoom().scaleExtent([0.15, 5]).on('zoom', e => {
        g.attr('transform', e.transform);
    });
    svg.call(zoom);

    const rootNode = data.nodes.find(n => n.root);

    const sim = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(d => {
            const s = data.nodes.find(n => n.id === (typeof d.source === 'object' ? d.source.id : d.source));
            return (s && s.root) ? 170 : 130;
        }).strength(0.6))
        .force('charge', d3.forceManyBody().strength(-450))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => nodeR(d) + 24))
        .force('x', d3.forceX(width / 2).strength(0.04))
        .force('y', d3.forceY(height / 2).strength(0.04))
        .alphaDecay(0.022)
        .velocityDecay(0.35);

    if (rootNode) {
        rootNode.fx = width / 2;
        rootNode.fy = height / 2;
        setTimeout(() => { rootNode.fx = null; rootNode.fy = null; sim.alpha(0.3).restart(); }, 1500);
    }

    const linkG = g.append('g');
    const link = linkG.selectAll('path').data(data.links).join('path')
        .attr('fill', 'none')
        .attr('stroke', '#2a2a4a')
        .attr('stroke-width', 1.5)
        .attr('stroke-opacity', 0.45)
        .attr('marker-end', 'url(#arrow)');

    const linkLabelG = g.append('g');
    const linkLabel = linkLabelG.selectAll('text').data(data.links).join('text')
        .text(d => d.label || '')
        .attr('font-size', '9px')
        .attr('fill', '#4a4a5e')
        .attr('text-anchor', 'middle')
        .attr('dy', -5)
        .style('pointer-events', 'none')
        .style('font-family', "'Segoe UI', system-ui, sans-serif");

    const nodeG = g.append('g');
    const node = nodeG.selectAll('g').data(data.nodes).join('g')
        .attr('class', 'gnode')
        .style('cursor', 'grab')
        .call(d3.drag()
            .on('start', (e, d) => {
                if (!e.active) sim.alphaTarget(0.3).restart();
                d.fx = d.x; d.fy = d.y;
            })
            .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
            .on('end', (e, d) => {
                if (!e.active) sim.alphaTarget(0);
                d.fx = null; d.fy = null;
            })
        );

    node.append('circle')
        .attr('r', d => nodeR(d) + 6)
        .attr('fill', 'none')
        .attr('stroke', d => typeColors[d.type] || '#6c5ce7')
        .attr('stroke-width', 0)
        .attr('stroke-opacity', 0.4)
        .attr('class', 'halo');

    node.append('circle')
        .attr('r', nodeR)
        .attr('fill', d => typeColors[d.type] || '#6c5ce7')
        .attr('fill-opacity', 0.12)
        .attr('stroke', d => typeColors[d.type] || '#6c5ce7')
        .attr('stroke-width', d => d.root ? 2.5 : 1.8)
        .attr('class', 'disc');

    node.append('text')
        .text(d => typeIcons[d.type] || '')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.38em')
        .attr('font-size', d => d.root ? '15px' : '11px')
        .attr('fill', d => typeColors[d.type] || '#6c5ce7')
        .style('pointer-events', 'none');

    node.append('text')
        .text(d => d.label.length > 26 ? d.label.slice(0, 24) + '\u2026' : d.label)
        .attr('text-anchor', 'middle')
        .attr('dy', d => nodeR(d) + 15)
        .attr('font-size', d => d.root ? '12px' : '10.5px')
        .attr('fill', '#9a9ab0')
        .attr('font-weight', d => d.root ? '600' : '400')
        .style('pointer-events', 'none')
        .style('font-family', "'Segoe UI', system-ui, sans-serif");

    node.append('text')
        .text(d => (d.type || '').toUpperCase())
        .attr('text-anchor', 'middle')
        .attr('dy', d => nodeR(d) + 27)
        .attr('font-size', '7.5px')
        .attr('fill', '#444')
        .attr('letter-spacing', '0.6px')
        .style('pointer-events', 'none')
        .style('font-family', "'Segoe UI', system-ui, sans-serif");

    const tip = d3.select('#relationship-graph').append('div')
        .attr('class', 'graph-tip').style('opacity', 0);

    node.on('mouseover', function(ev, d) {
        const conn = new Set([d.id]);
        data.links.forEach(l => {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            if (s === d.id) conn.add(t);
            if (t === d.id) conn.add(s);
        });
        node.transition().duration(250).style('opacity', n => conn.has(n.id) ? 1 : 0.1);
        link.transition().duration(250)
            .attr('stroke-opacity', l => {
                const s = typeof l.source === 'object' ? l.source.id : l.source;
                const t = typeof l.target === 'object' ? l.target.id : l.target;
                return (s === d.id || t === d.id) ? 0.85 : 0.04;
            })
            .attr('stroke', l => {
                const s = typeof l.source === 'object' ? l.source.id : l.source;
                const t = typeof l.target === 'object' ? l.target.id : l.target;
                return (s === d.id || t === d.id) ? (typeColors[d.type] || '#6c5ce7') : '#2a2a4a';
            })
            .attr('stroke-width', l => {
                const s = typeof l.source === 'object' ? l.source.id : l.source;
                const t = typeof l.target === 'object' ? l.target.id : l.target;
                return (s === d.id || t === d.id) ? 2.5 : 1.5;
            });
        linkLabel.transition().duration(250).style('opacity', l => {
            const s = typeof l.source === 'object' ? l.source.id : l.source;
            const t = typeof l.target === 'object' ? l.target.id : l.target;
            return (s === d.id || t === d.id) ? 1 : 0;
        });
        d3.select(this).select('.halo').transition().duration(200).attr('stroke-width', 8);
        d3.select(this).select('.disc').transition().duration(200).attr('fill-opacity', 0.3);
        const c = typeColors[d.type] || '#6c5ce7';
        tip.html('<b>' + d.label + '</b><br><span style="color:' + c + '">' + (d.type||'').toUpperCase() + '</span>')
            .style('left', (ev.offsetX + 16) + 'px').style('top', (ev.offsetY - 12) + 'px')
            .transition().duration(150).style('opacity', 1);
    }).on('mouseout', function() {
        node.transition().duration(350).style('opacity', 1);
        link.transition().duration(350)
            .attr('stroke-opacity', 0.45).attr('stroke', '#2a2a4a').attr('stroke-width', 1.5);
        linkLabel.transition().duration(350).style('opacity', 1);
        d3.select(this).select('.halo').transition().duration(300).attr('stroke-width', 0);
        d3.select(this).select('.disc').transition().duration(300).attr('fill-opacity', 0.12);
        tip.transition().duration(150).style('opacity', 0);
    });

    sim.on('tick', () => {
        link.attr('d', d => {
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const sr = nodeR(d.source);
            const tr = nodeR(d.target) + 6;
            const sx = d.source.x + dx * sr / dist;
            const sy = d.source.y + dy * sr / dist;
            const tx = d.target.x - dx * tr / dist;
            const ty = d.target.y - dy * tr / dist;
            const cx = (sx + tx) / 2 - (ty - sy) * 0.08;
            const cy = (sy + ty) / 2 + (tx - sx) * 0.08;
            return 'M' + sx + ',' + sy + 'Q' + cx + ',' + cy + ' ' + tx + ',' + ty;
        });
        linkLabel.attr('x', d => (d.source.x + d.target.x) / 2)
                 .attr('y', d => (d.source.y + d.target.y) / 2);
        node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
    });

    document.getElementById('graph-reset').addEventListener('click', () => {
        svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    });
    document.getElementById('graph-fit').addEventListener('click', () => {
        const b = g.node().getBBox();
        if (!b.width || !b.height) return;
        const s = 0.85 / Math.max(b.width / width, b.height / height);
        const tx = width / 2 - s * (b.x + b.width / 2);
        const ty = height / 2 - s * (b.y + b.height / 2);
        svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(s));
    });
})();
"""


def _render_d3_graph(graph_data: dict) -> str:
    if len(graph_data.get("nodes", [])) < 2:
        return ""
    data_json = json.dumps(graph_data, ensure_ascii=False)
    colors_json = json.dumps(NODE_COLORS, ensure_ascii=False)
    icons_json = json.dumps(NODE_ICONS, ensure_ascii=False)

    js = GRAPH_JS.replace("__DATA__", data_json).replace("__COLORS__", colors_json).replace("__ICONS__", icons_json)

    used_types = {n["type"] for n in graph_data["nodes"]}
    legend_items = []
    for t in ("query", "ip", "domain", "asn", "provider", "country", "city", "location", "coords", "dns"):
        if t in used_types:
            c = NODE_COLORS.get(t, "#6c5ce7")
            lbl = NODE_TYPE_LABELS.get(t, t.upper())
            legend_items.append(
                f'<span class="legend-item"><span class="legend-dot" style="background:{c}"></span>{lbl}</span>'
            )
    legend_html = "".join(legend_items)

    return f"""
    <div class="report-card" id="graph-card">
        <h3>Граф связей</h3>
        <div id="graph-wrap">
            <div id="relationship-graph"></div>
            <div class="graph-controls">
                <button class="graph-btn" id="graph-fit" title="Вписать">Вписать</button>
                <button class="graph-btn" id="graph-reset" title="Сброс">Сброс</button>
            </div>
            <div class="graph-legend">{legend_html}</div>
        </div>
    </div>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>{js}</script>
    """


def _osint_images_section(image_results: list = None) -> str:
    if not image_results:
        return ""
    parts = []
    for item in image_results:
        thumb = item.get("thumbnail", "")
        links = item.get("links", [])
        source = item.get("source", "")
        desc = item.get("description", "")
        thumb_html = ""
        if thumb:
            thumb_html = f'<img src="{html_mod.escape(thumb)}" alt="image" class="osint-thumb">'
        link_btns = "".join(
            f'<a href="{html_mod.escape(l["url"])}" target="_blank" class="map-btn">{html_mod.escape(l["name"])}</a>'
            for l in links
        )
        parts.append(f"""
        <div class="osint-image-item">
            {thumb_html}
            <div class="osint-image-meta">
                {f'<p class="osint-source">{html_mod.escape(source)}</p>' if source else ''}
                {f'<p class="note">{html_mod.escape(desc)}</p>' if desc else ''}
                <div class="map-links">{link_btns}</div>
            </div>
        </div>
        """)
    content = "".join(parts)
    return _card("OSINT анализ изображений", content, card_id="osint-images-card")


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0d0d14;
            color: #e0e0e0;
            line-height: 1.6;
        }}
        .container {{ max-width: 960px; margin: 0 auto; padding: 24px; }}

        .query-summary {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            padding: 14px 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }}
        .query-badge {{
            background: #6c5ce7;
            color: #fff;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .query-value {{
            font-size: 15px;
            font-weight: 500;
            color: #fff;
            flex: 1;
        }}
        .query-time {{
            font-size: 12px;
            color: #666;
        }}

        .report-card {{
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            padding: 20px 24px;
            margin-bottom: 16px;
            transition: border-color 0.2s ease;
        }}
        .report-card:hover {{
            border-color: #6c5ce7;
        }}
        .report-card h3 {{
            margin: 0 0 14px 0;
            font-size: 15px;
            color: #6c5ce7;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}

        .meta-table {{ width: 100%; border-collapse: collapse; }}
        .meta-table td {{ padding: 7px 0; border-bottom: 1px solid #1f1f35; font-size: 14px; }}
        .meta-table tr:last-child td {{ border-bottom: none; }}
        .meta-label {{ color: #888; width: 150px; font-size: 13px; }}

        .note {{ color: #888; font-size: 13px; margin-top: 12px; font-style: italic; }}
        .sources {{ font-size: 12px; color: #555; margin-top: 24px; text-align: center; }}

        .map-links {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .map-btn {{
            display: inline-block;
            background: #2a2a4a;
            color: #e0e0e0;
            padding: 8px 18px;
            border-radius: 6px;
            text-decoration: none;
            font-size: 13px;
            transition: background 0.2s;
        }}
        .map-btn:hover {{ background: #6c5ce7; color: #fff; }}

        .technical-section {{
            margin-bottom: 16px;
        }}
        .technical-section summary {{
            cursor: pointer;
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 14px;
            color: #888;
            transition: border-color 0.2s;
        }}
        .technical-section summary:hover {{
            border-color: #6c5ce7;
            color: #e0e0e0;
        }}
        .technical-section[open] summary {{
            border-radius: 8px 8px 0 0;
            border-bottom: none;
        }}
        .raw-json {{
            background: #12121e;
            border: 1px solid #2a2a4a;
            border-top: none;
            border-radius: 0 0 8px 8px;
            padding: 16px;
            font-family: 'Consolas', 'Fira Code', monospace;
            font-size: 12px;
            color: #a0a0b0;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 400px;
            overflow-y: auto;
        }}

        #graph-wrap {{
            position: relative;
        }}
        #relationship-graph {{
            width: 100%;
            min-height: 520px;
            background: #0d0d16;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }}
        #relationship-graph svg {{ display: block; }}
        .graph-controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            display: flex;
            gap: 6px;
            z-index: 10;
        }}
        .graph-btn {{
            background: #1a1a2ecc;
            border: 1px solid #2a2a4a;
            color: #888;
            padding: 5px 12px;
            border-radius: 5px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }}
        .graph-btn:hover {{
            border-color: #6c5ce7;
            color: #e0e0e0;
        }}
        .graph-legend {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            z-index: 10;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 10px;
            color: #555;
        }}
        .legend-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }}
        .graph-tip {{
            position: absolute;
            background: #1a1a2ef0;
            border: 1px solid #2a2a4a;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            color: #e0e0e0;
            pointer-events: none;
            z-index: 20;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5);
            line-height: 1.5;
        }}

        .osint-image-item {{
            display: flex;
            gap: 16px;
            align-items: flex-start;
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid #1f1f35;
        }}
        .osint-image-item:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        .osint-thumb {{
            max-width: 140px;
            max-height: 140px;
            border-radius: 6px;
            border: 1px solid #2a2a4a;
            object-fit: cover;
        }}
        .osint-image-meta {{
            flex: 1;
        }}
        .osint-source {{
            font-size: 13px;
            color: #aaa;
            margin-bottom: 8px;
        }}

        pre {{ white-space: pre-wrap; word-break: break-all; }}
        {styles}

        @media print {{
            body {{ background: #fff; color: #222; }}
            .report-card {{ border: 1px solid #ddd; }}
            .query-summary {{ background: #f5f5f5; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {header}
        {query_summary}
        {content}
        {graph}
        {osint_images}
        {map_section}
        {technical}
        <div class="sources">{sources}</div>
        {footer}
    </div>
</body>
</html>
"""


def generate_html_report(
    title: str,
    content: str,
    query_type: str = "",
    query: str = "",
    graph_html: str = "",
    map_section: str = "",
    technical: str = "",
    osint_images: str = "",
) -> Optional[str]:
    header = header_html(get("branding.product_title", "solvnox"), title)
    foot = footer_html(query_type, query)
    sources = "Источники: ip-api.com, Nominatim/OSM, RDAP — публичные данные."
    summary = _query_summary(query_type, query)
    html_str = HTML_TEMPLATE.format(
        title=title,
        header=header,
        query_summary=summary,
        content=content,
        graph=graph_html,
        osint_images=osint_images,
        map_section=map_section,
        technical=technical,
        footer=foot,
        styles=STYLES,
        sources=sources,
    )
    d = _ensure_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fp = d / f"report_{query_type or 'geo'}_{ts}.html"
    try:
        fp.write_text(html_str, encoding="utf-8")
        return str(fp)
    except OSError as e:
        log.warning("HTML report save failed: %s", e)
        return None


def save_geo_html_report(geo: GeoResult, osint_data: list = None) -> Optional[str]:
    content = _card("Результат геолокации", _geo_section(geo))
    graph_data = _build_relationship_graph(geo=geo)
    graph_html = _render_d3_graph(graph_data)
    map_section = _map_links_section(geo)
    technical = _technical_section(geo.raw)
    osint_html = _osint_images_section(osint_data)
    return generate_html_report(
        f"Геолокация: {geo.query}", content, geo.query_type, geo.query,
        graph_html=graph_html, map_section=map_section, technical=technical,
        osint_images=osint_html,
    )


def save_domain_html_report(result: DomainResult, osint_data: list = None) -> Optional[str]:
    parts = []
    if result.resolved_ips:
        parts.append(_card("Разрешённые IP", "<br>".join(html_mod.escape(ip) for ip in result.resolved_ips)))
    if result.geo:
        parts.append(_card("Геолокация", _geo_section(result.geo)))
    if result.whois_snippet:
        parts.append(_card("WHOIS / RDAP", f"<pre>{html_mod.escape(result.whois_snippet)}</pre>"))
    if result.dns:
        rows = []
        for rtype, vals in result.dns.items():
            if vals:
                rows.append(f"<b>{html_mod.escape(rtype)}:</b> " + ", ".join(html_mod.escape(str(v)) for v in vals))
        if rows:
            parts.append(_card("DNS", "<br>".join(rows)))
    content = "".join(parts)
    graph_data = _build_relationship_graph(geo=result.geo, domain_result=result)
    graph_html = _render_d3_graph(graph_data)
    map_section = _map_links_section(result.geo) if result.geo else ""
    raw = {}
    if result.geo:
        raw["geo"] = result.geo.raw
    if result.whois:
        raw["whois"] = result.whois
    if result.dns:
        raw["dns"] = result.dns
    technical = _technical_section(raw)
    osint_html = _osint_images_section(osint_data)
    return generate_html_report(
        f"Домен: {result.domain}", content, "domain", result.domain,
        graph_html=graph_html, map_section=map_section, technical=technical,
        osint_images=osint_html,
    )
