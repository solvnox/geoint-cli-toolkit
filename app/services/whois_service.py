import requests
from typing import Optional, Dict, Any

from app.core.logger import log


def whois_rdap(domain: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(f"https://rdap.org/domain/{domain}", timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        out = {
            "status": data.get("status"),
            "nameservers": [],
            "events": {},
            "entities": {},
        }
        for ns in data.get("nameservers", []):
            if isinstance(ns, dict) and ns.get("ldhName"):
                out["nameservers"].append(ns["ldhName"])
        for ev in data.get("events", []):
            action = ev.get("eventAction")
            date = ev.get("eventDate", "")[:10]
            if action:
                out["events"][action] = date
        for e in data.get("entities", []):
            for role in e.get("roles", []):
                if role not in out["entities"]:
                    vcard = e.get("vcardArray", [])
                    name = ""
                    if isinstance(vcard, list) and len(vcard) > 1:
                        for item in vcard[1]:
                            if isinstance(item, list) and item[0] in ("fn", "org"):
                                name = item[-1] if isinstance(item[-1], str) else str(item[-1])
                                break
                    out["entities"][role] = name
        return out
    except Exception as e:
        log.debug("RDAP failed: %s", e)
        return None


def whois_text(domain: str) -> Optional[str]:
    try:
        import subprocess
        result = subprocess.run(
            ["whois", domain],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()[:3000]
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        log.debug("WHOIS command failed: %s", e)
    return None
