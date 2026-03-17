from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class GeoResult:
    query: str
    query_type: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    asn: Optional[str] = None
    org: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    note: Optional[str] = None
    is_private: Optional[bool] = None
    confidence: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "query_type": self.query_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "country": self.country,
            "region": self.region,
            "city": self.city,
            "address": self.address,
            "postal_code": self.postal_code,
            "timezone": self.timezone,
            "isp": self.isp,
            "asn": self.asn,
            "org": self.org,
            "timestamp": self.timestamp,
            "note": self.note,
            "is_private": self.is_private,
        }

    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


@dataclass
class DomainResult:
    domain: str
    resolved_ips: List[str] = field(default_factory=list)
    resolved_ip: Optional[str] = None
    geo: Optional[GeoResult] = None
    whois: Optional[Dict[str, Any]] = None
    whois_snippet: Optional[str] = None
    dns: Optional[Dict[str, List[str]]] = None
    error: Optional[str] = None
