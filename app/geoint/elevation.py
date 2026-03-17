from typing import Optional

import requests
from app.core.logger import log


def get_elevation(lat: float, lon: float) -> Optional[float]:
    url = "https://api.open-meteo.com/v1/elevation"
    try:
        resp = requests.get(url, params={"latitude": lat, "longitude": lon}, timeout=10)
        data = resp.json()
        elev = data.get("elevation")
        if isinstance(elev, list) and elev:
            return float(elev[0])
        return None
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        log.warning("Elevation lookup failed: %s", e)
        return None
