import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from app.core.config import get
from app.core.logger import log
from app.models.geo_result import GeoResult, DomainResult
from app.reports.html_report import save_geo_html_report, save_domain_html_report


def _report_dir(sub: str) -> Path:
    key = f"paths.reports_{sub}"
    p = Path(get(key) or f"reports/{sub}")
    base = Path(get("_base_dir", "."))
    if not p.is_absolute():
        p = base / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_json(data: dict, prefix: str = "report") -> Optional[str]:
    d = _report_dir("json")
    fp = d / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(fp)
    except OSError as e:
        log.warning("Save JSON failed: %s", e)
        return None


def save_txt(content: str, prefix: str = "report") -> Optional[str]:
    d = _report_dir("txt")
    fp = d / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        fp.write_text(content, encoding="utf-8")
        return str(fp)
    except OSError as e:
        log.warning("Save TXT failed: %s", e)
        return None


def save_csv(rows: list, headers: list, prefix: str = "report") -> Optional[str]:
    d = _report_dir("csv")
    fp = d / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        with open(fp, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)
        return str(fp)
    except OSError as e:
        log.warning("Save CSV failed: %s", e)
        return None


def format_geo_txt(geo: GeoResult) -> str:
    lines = [
        "=" * 50,
        f"solvnox GEOINT — Отчёт ({geo.query_type.upper()})",
        f"Время: {geo.timestamp}",
        "=" * 50,
        f"Запрос: {geo.query}",
        f"Страна: {geo.country or '—'}",
        f"Регион: {geo.region or '—'}",
        f"Город: {geo.city or '—'}",
        f"Адрес: {geo.address or '—'}",
        f"Широта: {geo.latitude or '—'}",
        f"Долгота: {geo.longitude or '—'}",
        f"Часовой пояс: {geo.timezone or '—'}",
        f"ISP: {geo.isp or '—'}",
        f"ASN/Орг: {geo.asn or geo.org or '—'}",
        "",
        geo.note or "",
    ]
    return "\n".join(lines)


def save_geo_report(geo: GeoResult, formats: list = None) -> Dict[str, str]:
    formats = formats or ["json", "txt", "csv", "html"]
    prefix = f"geo_{geo.query_type}"
    out = {}
    if "json" in formats:
        p = save_json(geo.to_dict(), prefix)
        if p:
            out["json"] = p
    if "txt" in formats:
        p = save_txt(format_geo_txt(geo), prefix)
        if p:
            out["txt"] = p
    if "csv" in formats:
        row = [
            geo.query,
            geo.country or "",
            geo.region or "",
            geo.city or "",
            geo.latitude or "",
            geo.longitude or "",
            geo.timestamp,
        ]
        p = save_csv([row], ["query", "country", "region", "city", "lat", "lon", "timestamp"], prefix)
        if p:
            out["csv"] = p
    if "html" in formats:
        p = save_geo_html_report(geo)
        if p:
            out["html"] = p
    return out


def save_domain_report(result: DomainResult) -> Dict[str, str]:
    out = {}
    data = {
        "domain": result.domain,
        "resolved_ips": result.resolved_ips or [result.resolved_ip] if result.resolved_ip else [],
        "geo": result.geo.to_dict() if result.geo else None,
        "whois": result.whois,
        "dns": result.dns,
        "timestamp": datetime.now().isoformat(),
    }
    p = save_json(data, "domain")
    if p:
        out["json"] = p
    txt = f"Домен: {result.domain}\nIP: {', '.join(result.resolved_ips) if result.resolved_ips else (result.resolved_ip or '—')}\n\n"
    if result.geo:
        txt += format_geo_txt(result.geo)
    if result.whois_snippet:
        txt += f"\n\nWHOIS/RDAP:\n{result.whois_snippet}"
    if result.dns:
        for rtype, vals in result.dns.items():
            if vals:
                txt += f"\n{rtype}: {', '.join(vals)}"
    p = save_txt(txt, "domain")
    if p:
        out["txt"] = p
    p = save_domain_html_report(result)
    if p:
        out["html"] = p
    return out
