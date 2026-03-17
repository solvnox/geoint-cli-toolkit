from typing import Optional

import requests
from app.core.logger import log


def timezone_by_coords(lat: float, lon: float) -> Optional[str]:
    url = "https://api.open-meteo.com/v1/forecast"
    try:
        resp = requests.get(url, params={
            "latitude": lat,
            "longitude": lon,
            "timezone": "auto",
            "forecast_days": 1,
        }, timeout=10)
        data = resp.json()
        tz = data.get("timezone")
        utc_offset = data.get("utc_offset_seconds")
        if tz:
            if utc_offset is not None:
                hours = utc_offset // 3600
                sign = "+" if hours >= 0 else ""
                return f"{tz} (UTC{sign}{hours})"
            return tz
        return None
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        log.warning("Timezone lookup failed: %s", e)
        return None
