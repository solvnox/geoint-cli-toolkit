import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from app.core.config import get
from app.core.logger import log


def _sessions_dir() -> Path:
    p = Path(get("paths.sessions") or "data/sessions")
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_session(name: str = "") -> str:
    sid = str(uuid.uuid4())[:8]
    data = {
        "id": sid,
        "name": name or f"Сессия {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "created": datetime.now().isoformat(),
        "queries": [],
    }
    path = _sessions_dir() / f"{sid}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return sid
    except OSError as e:
        log.warning("Session create failed: %s", e)
        return ""


def add_to_session(sid: str, query_type: str, query: str, result: dict) -> bool:
    path = _sessions_dir() / f"{sid}.json"
    if not path.exists():
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("queries", []).append({
            "type": query_type,
            "query": query,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def list_sessions() -> List[Dict[str, Any]]:
    sessions = []
    for p in _sessions_dir().glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            sessions.append({"id": d.get("id"), "name": d.get("name"), "created": d.get("created")})
        except (OSError, json.JSONDecodeError):
            pass
    return sorted(sessions, key=lambda x: x.get("created", ""), reverse=True)


def load_session(sid: str):
    path = _sessions_dir() / f"{sid}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
