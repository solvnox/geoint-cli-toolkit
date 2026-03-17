import ipaddress
import socket
import requests
from typing import Optional, Tuple

from app.core.config import get
from app.core.logger import log
from app.models.geo_result import GeoResult


def _is_private(ip_str: str) -> bool:
    try:
        return ipaddress.ip_address(ip_str.strip()).is_private
    except ValueError:
        return False


def _ptr_lookup(ip_str: str) -> Optional[str]:
    try:
        return socket.gethostbyaddr(ip_str.strip())[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def lookup_ip(ip: str) -> Optional[GeoResult]:
    endpoint = get("ip_geolocation.endpoint", "http://ip-api.com/json/")
    timeout = get("ip_geolocation.timeout", 10)
    is_priv = _is_private(ip)
    if is_priv:
        return GeoResult(
            query=ip,
            query_type="ip",
            raw={},
            note="Приватный/внутренний IP. Геолокация недоступна.",
            is_private=True,
        )
    url = f"{endpoint.rstrip('/')}/{ip}?fields=status,message,country,regionName,city,lat,lon,timezone,isp,org,as,query,zip"
    try:
        resp = requests.get(url, timeout=timeout)
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        log.warning("IP lookup failed: %s", e)
        return None
    if data.get("status") != "success":
        return None
    lat, lon = data.get("lat"), data.get("lon")
    ptr = _ptr_lookup(ip) if ip else None
    geo = GeoResult(
        query=data.get("query", ip),
        query_type="ip",
        latitude=float(lat) if lat is not None else None,
        longitude=float(lon) if lon is not None else None,
        country=data.get("country"),
        region=data.get("regionName"),
        city=data.get("city"),
        postal_code=data.get("zip"),
        timezone=data.get("timezone"),
        isp=data.get("isp"),
        org=data.get("org"),
        asn=data.get("as"),
        raw=data,
        is_private=False,
        confidence="приблизительная",
        note="Геолокация по IP приблизительная — регион/город, не точное местоположение.",
    )
    if ptr:
        geo.raw["ptr"] = ptr
    return geo
