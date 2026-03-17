"""
Geocoding and Reverse Geocoding Service.
Uses Nominatim (OpenStreetMap) - free, no key required.
"""
from typing import Optional, List, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from geopy.location import Location

from app.core.config import get
from app.core.logger import log
from app.models.geo_result import GeoResult


def _get_geocoder() -> Nominatim:
    """Create Nominatim geocoder with configured user agent."""
    ua = get("geocoding.user_agent", "GEOINT-CLI/1.0")
    timeout = get("geocoding.timeout", 10)
    return Nominatim(user_agent=ua, timeout=timeout)


def geocode_place(place_name: str) -> Optional[GeoResult]:
    """Convert place name to coordinates and address details."""
    geocoder = _get_geocoder()
    try:
        loc = geocoder.geocode(place_name, exactly_one=True, language="ru")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        log.warning("Geocode error: %s", e)
        return None

    if not loc:
        return None

    addr = loc.raw.get("address", {}) if hasattr(loc, "raw") and loc.raw else {}
    country = addr.get("country") or getattr(loc, "raw", {}).get("address", {}).get("country")
    if not country and hasattr(loc, "raw"):
        country = loc.raw.get("display_name", "").split(",")[-1].strip() if loc.raw else None

    return GeoResult(
        query=place_name,
        query_type="place",
        latitude=loc.latitude,
        longitude=loc.longitude,
        country=addr.get("country") or (loc.address.split(",")[-1].strip() if loc.address else None),
        region=addr.get("state") or addr.get("region"),
        city=addr.get("city") or addr.get("town") or addr.get("village"),
        address=loc.address,
        postal_code=addr.get("postcode"),
        raw={"display_name": loc.address, "address": addr},
        note="Геокодирование по открытым данным OpenStreetMap.",
    )


def reverse_geocode(lat: float, lon: float) -> Optional[GeoResult]:
    """Convert coordinates to human-readable address."""
    geocoder = _get_geocoder()
    try:
        loc = geocoder.reverse(f"{lat}, {lon}", language="ru")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        log.warning("Reverse geocode error: %s", e)
        return None

    if not loc:
        return None

    addr = loc.raw.get("address", {}) if hasattr(loc, "raw") and loc.raw else {}
    return GeoResult(
        query=f"{lat}, {lon}",
        query_type="coords",
        latitude=lat,
        longitude=lon,
        country=addr.get("country"),
        region=addr.get("state") or addr.get("region"),
        city=addr.get("city") or addr.get("town") or addr.get("village"),
        address=loc.address,
        postal_code=addr.get("postcode"),
        raw={"display_name": loc.address, "address": addr},
        note="Обратное геокодирование по OpenStreetMap.",
    )
