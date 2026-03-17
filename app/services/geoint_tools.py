import math
from typing import Tuple, List, Optional
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

from app.core.config import get


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def decimal_to_dms(lat: float, lon: float) -> Tuple[str, str]:
    def dd_to_dms(dd: float, is_lat: bool) -> str:
        d = int(abs(dd))
        m = int((abs(dd) - d) * 60)
        s = (abs(dd) - d - m / 60) * 3600
        direction = "N" if is_lat and dd >= 0 else "S" if is_lat else "E" if dd >= 0 else "W"
        return f"{d}°{m}'{s:.2f}\"{direction}"
    return dd_to_dms(lat, True), dd_to_dms(lon, False)


def dms_to_decimal(dms: str) -> Optional[float]:
    import re
    m = re.match(r"(\d+)[°](\d+)[\'′](\d+(?:\.\d+)?)[\"″]?\s*([NSEW])?", dms.strip(), re.I)
    if not m:
        return None
    d, mi, s, direction = float(m.group(1)), float(m.group(2)), float(m.group(3)), (m.group(4) or "").upper()
    dec = d + mi / 60 + s / 3600
    if direction in ("S", "W"):
        dec = -dec
    return dec


def bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return lat - dlat, lon - dlon, lat + dlat, lon + dlon


def google_maps_link(lat: float, lon: float, zoom: int = 15) -> str:
    return f"https://www.google.com/maps?q={lat},{lon}&z={zoom}"


def osm_link(lat: float, lon: float, zoom: int = 15) -> str:
    return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map={zoom}/{lat}/{lon}"


def yandex_maps_link(lat: float, lon: float, zoom: int = 15) -> str:
    return f"https://yandex.ru/maps/?pt={lon},{lat}&z={zoom}"


def nearby_places(lat: float, lon: float, radius_km: float = 5, limit: int = 10) -> List[dict]:
    try:
        ua = get("geocoding.user_agent", "solvnox-GEOINT/2.0")
        g = Nominatim(user_agent=ua, timeout=10)
        locs = g.reverse(f"{lat}, {lon}")
        if not locs:
            return []
        addrs = locs.raw.get("address", {})
        results = []
        seen = set()
        for key in ("city", "town", "village", "county", "state", "country"):
            v = addrs.get(key)
            if v and v not in seen:
                seen.add(v)
                results.append({"type": key, "name": v})
        return results[:limit]
    except Exception:
        return []


def timezone_by_coords(lat: float, lon: float) -> Optional[str]:
    from app.geoint.timezone_lookup import timezone_by_coords as _tz_lookup
    return _tz_lookup(lat, lon)
