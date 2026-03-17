import socket
from typing import Optional, List

from app.core.logger import log
from app.models.geo_result import GeoResult, DomainResult
from app.services.ip_service import lookup_ip
from app.services.whois_service import whois_rdap, whois_text
from app.services.dns_service import lookup_dns


def resolve_domain(domain: str) -> List[str]:
    ips = []
    try:
        for r in socket.getaddrinfo(domain, None):
            if r[0] == socket.AF_INET and r[4][0] not in ips:
                ips.append(r[4][0])
        for r in socket.getaddrinfo(domain, None):
            if r[0] == socket.AF_INET6 and r[4][0] not in ips:
                ips.append(r[4][0])
    except socket.gaierror as e:
        log.info("Domain resolve failed: %s", e)
    return ips


def lookup_domain(domain: str) -> DomainResult:
    result = DomainResult(domain=domain)
    result.resolved_ips = resolve_domain(domain)
    result.resolved_ip = result.resolved_ips[0] if result.resolved_ips else None
    if not result.resolved_ip:
        result.error = "Не удалось разрешить домен в IP. Проверьте имя и подключение."
        return result
    result.geo = lookup_ip(result.resolved_ip)
    whois_data = whois_rdap(domain)
    if whois_data:
        result.whois = whois_data
        lines = []
        if whois_data.get("events"):
            for k, v in whois_data["events"].items():
                lines.append(f"{k}: {v}")
        if whois_data.get("nameservers"):
            lines.append(f"NS: {', '.join(whois_data['nameservers'][:5])}")
        if whois_data.get("entities"):
            for role, name in list(whois_data["entities"].items())[:3]:
                if name:
                    lines.append(f"{role}: {name}")
        result.whois_snippet = "\n".join(lines) if lines else None
    if not result.whois_snippet:
        raw = whois_text(domain)
        if raw:
            result.whois_snippet = raw[:1500]
    try:
        result.dns = lookup_dns(domain)
    except Exception as e:
        log.debug("DNS lookup failed: %s", e)
    return result
