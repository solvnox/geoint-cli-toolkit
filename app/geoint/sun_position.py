from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.core.logger import log

try:
    from astral import LocationInfo
    from astral.sun import sun, elevation as solar_elevation, azimuth as solar_azimuth
    _HAS_ASTRAL = True
except ImportError:
    _HAS_ASTRAL = False


def sun_info(lat: float, lon: float, dt: datetime = None) -> Optional[Dict[str, Any]]:
    if not _HAS_ASTRAL:
        log.warning("astral library not installed")
        return None
    try:
        if dt is None:
            dt = datetime.now(timezone.utc)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        loc = LocationInfo(name="Query", region="", timezone="UTC",
                           latitude=lat, longitude=lon)
        s = sun(loc.observer, date=dt.date())
        sel = solar_elevation(loc.observer, dt)
        saz = solar_azimuth(loc.observer, dt)
        sunrise = s["sunrise"]
        sunset = s["sunset"]
        day_seconds = (sunset - sunrise).total_seconds()
        hours = int(day_seconds // 3600)
        minutes = int((day_seconds % 3600) // 60)
        return {
            "sunrise": sunrise.strftime("%H:%M:%S UTC"),
            "sunset": sunset.strftime("%H:%M:%S UTC"),
            "dawn": s["dawn"].strftime("%H:%M:%S UTC"),
            "dusk": s["dusk"].strftime("%H:%M:%S UTC"),
            "noon": s["noon"].strftime("%H:%M:%S UTC"),
            "solar_elevation": round(sel, 2),
            "solar_azimuth": round(saz, 2),
            "day_length": f"{hours}ч {minutes}мин",
        }
    except Exception as e:
        log.warning("Sun position calculation failed: %s", e)
        return None
