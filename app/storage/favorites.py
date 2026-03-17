import json
from pathlib import Path
from typing import List, Dict, Any

from app.core.config import get
from app.core.logger import log


def _favorites_path() -> Path:
    p = Path(get("paths.favorites") or "data/favorites.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_favorites() -> List[Dict[str, Any]]:
    path = _favorites_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_favorites(items: List[Dict[str, Any]]) -> bool:
    try:
        with open(_favorites_path(), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def add_favorite(name: str, lat: float, lon: float, note: str = "") -> bool:
    items = load_favorites()
    items.append({"name": name, "lat": lat, "lon": lon, "note": note})
    return save_favorites(items)
