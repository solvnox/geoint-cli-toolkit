"""
Input validation utilities for IP, coordinates, domains.
"""
import ipaddress
import re
from typing import Tuple, Optional


def is_valid_ip(ip_str: str) -> bool:
    """Validate IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(ip_str.strip())
        return True
    except ValueError:
        return False


def parse_coordinates(raw: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Parse latitude and longitude from user input.
    Accepts: "55.75, 37.62" or "55.75 37.62" or "55°45'N 37°37'E" etc.
    Returns (lat, lon, error_msg).
    """
    raw = raw.strip()
    # Try comma or space separated decimal
    parts = re.split(r"[,; \t]+", raw)
    if len(parts) >= 2:
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon, None
            return None, None, "Координаты вне допустимого диапазона (широта: -90..90, долгота: -180..180)."
        except ValueError:
            pass
    return None, None, "Неверный формат. Введите широту и долготу, например: 55.7558 37.6173"


def is_valid_domain(domain: str) -> bool:
    """Basic domain format validation."""
    domain = domain.strip().lower()
    if not domain or len(domain) > 253:
        return False
    # Simple pattern: subdomain.domain.tld
    pattern = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$"
    return bool(re.match(pattern, domain)) or bool(re.match(r"^[a-z0-9][a-z0-9-]+\.[a-z]{2,}$", domain))


def normalize_domain(domain: str) -> str:
    """Remove protocol and path, keep domain only."""
    domain = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    domain = domain.split("/")[0]
    return domain
