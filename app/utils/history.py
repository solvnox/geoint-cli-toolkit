import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.core.config import get
from app.core.logger import log


def _history_path() -> Path:
    p = Path(get("paths.history") or "data/history.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_history(max_items: int = 50, query_type: Optional[str] = None) -> List[Dict[str, Any]]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            items = []
        if query_type:
            items = [x for x in items if x.get("query_type") == query_type]
        seen = set()
        deduped = []
        for x in items:
            k = (x.get("query", ""), x.get("query_type", ""))
            if k not in seen:
                seen.add(k)
                deduped.append(x)
        return deduped[:max_items]
    except (json.JSONDecodeError, OSError) as e:
        log.debug("History load: %s", e)
        return []


def save_history(items: List[Dict[str, Any]], max_items: int = 150) -> None:
    try:
        with open(_history_path(), "w", encoding="utf-8") as f:
            json.dump(items[:max_items], f, ensure_ascii=False, indent=2)
    except OSError as e:
        log.warning("History save: %s", e)


def add_to_history(query: str, query_type: str, result_summary: str = "") -> None:
    items = load_history(max_items=200)
    items.insert(0, {
        "query": query,
        "query_type": query_type,
        "summary": (result_summary or "")[:200],
        "timestamp": datetime.now().isoformat(),
    })
    save_history(items)
