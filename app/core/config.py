import os
from pathlib import Path
from typing import Any, Dict

try:
    import yaml
except ImportError:
    yaml = None

_DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {"name": "solvnox GEOINT", "version": "2.0.0", "language": "ru"},
    "branding": {
        "product_title": "solvnox",
        "logo_text": "solvnox",
        "logo_file": "",
        "report_theme": "dark",
        "report_footer": "GEOINT / OSINT • Публичные данные",
    },
    "ui": {"browser_auto_open": True, "cli_theme": "dark"},
    "ip_geolocation": {"provider": "ip-api", "endpoint": "http://ip-api.com/json/", "timeout": 10},
    "geocoding": {"provider": "nominatim", "user_agent": "solvnox-GEOINT/2.0", "timeout": 10},
    "paths": {
        "data": "data",
        "logs": "logs",
        "reports": "reports",
        "history": "data/history.json",
        "sessions": "data/sessions",
        "favorites": "data/favorites.json",
        "reports_html": "reports/html",
        "reports_json": "reports/json",
        "reports_txt": "reports/txt",
        "reports_csv": "reports/csv",
        "maps": "reports/maps",
    },
    "map": {"default_zoom": 14, "default_tiles": "OpenStreetMap", "ip_radius_meters": 50000},
}

_config: Dict[str, Any] = {}


def load_config(config_path: str = None) -> Dict[str, Any]:
    global _config
    if _config:
        return _config
    base_dir = Path(__file__).resolve().parent.parent.parent
    path = Path(config_path) if config_path else base_dir / "config.yaml"
    if path.exists() and yaml:
        try:
            with open(path, "r", encoding="utf-8") as f:
                _config = yaml.safe_load(f) or {}
        except Exception:
            _config = _DEFAULT_CONFIG.copy()
    else:
        _config = _DEFAULT_CONFIG.copy()
    paths = _config.get("paths", {})
    for key, val in list(paths.items()):
        if isinstance(val, str) and not os.path.isabs(val):
            paths[key] = str(base_dir / val)
    _config["paths"] = paths
    _config["_base_dir"] = str(base_dir)
    return _config


def get(key: str, default: Any = None) -> Any:
    if not _config:
        load_config()
    keys = key.split(".")
    val = _config
    for k in keys:
        val = val.get(k, default) if isinstance(val, dict) else default
        if val is None:
            return default
    return val
