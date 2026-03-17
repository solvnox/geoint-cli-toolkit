import base64
from pathlib import Path
from app.core.config import get

LOGO_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def _find_logo(folder_name: str):
    base = Path(get("_base_dir", "."))
    folder = base / "assets" / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    for ext in LOGO_EXTS:
        for p in folder.glob(f"*{ext}"):
            if p.is_file():
                return p
    return None


def _logo_img_from_path(p: Path, max_height: int = 36) -> str:
    try:
        raw = p.read_bytes()
        ext = p.suffix.lower()
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(ext, "image/png")
        b64 = base64.b64encode(raw).decode("ascii")
        return f'<img src="data:{mime};base64,{b64}" alt="logo" style="height:{max_height}px;margin-right:8px;vertical-align:middle;object-fit:contain;">'
    except OSError:
        return ""


def map_logo_html() -> str:
    p = _find_logo("map_logo")
    if p:
        img = _logo_img_from_path(p)
        if img:
            return img
    text = get("branding.logo_text", "solvnox")
    return f'<span class="logo-text">{text}</span>'


def report_logo_html() -> str:
    p = _find_logo("report_logo")
    if p:
        img = _logo_img_from_path(p)
        if img:
            return img
    text = get("branding.logo_text", "solvnox")
    return f'<span class="logo-text">{text}</span>'


def logo_html(logo_path: str = None) -> str:
    path = logo_path or get("branding.logo_file", "")
    base = Path(get("_base_dir", "."))
    if path and (base / path).exists():
        img = _logo_img_from_path(base / path)
        if img:
            return img
    return report_logo_html()


def header_html(title: str = "", subtitle: str = "", use_map_logo: bool = False) -> str:
    t = title or get("branding.product_title", "solvnox")
    logo = map_logo_html() if use_map_logo else report_logo_html()
    return f"""
    <div class="report-header">
        <div class="logo-area">
            <span class="uroboros">◇</span>
            {logo}
        </div>
        <div class="header-meta">
            <h1>{t}</h1>
            {f'<p class="subtitle">{subtitle}</p>' if subtitle else ''}
        </div>
    </div>
    """


def footer_html(query_type: str = "", query: str = "", ts: str = "") -> str:
    from datetime import datetime
    footer_text = get("branding.report_footer", "GEOINT / OSINT • Публичные данные")
    if not ts:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [query_type, query] if query_type and query else []
    return f"""
    <div class="report-footer">
        <span>{footer_text}</span>
        <span>•</span>
        <span>{ts}</span>
        {f'<span>•</span><span>{query_type}: {query}</span>' if parts else ''}
    </div>
    """


STYLES = """
.report-header-wrap { margin-bottom: 8px; }
.report-footer-wrap { margin-top: 8px; }
.report-header {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%);
    color: #e0e0e0;
    padding: 20px 24px;
    border-bottom: 1px solid #2a2a4a;
    display: flex;
    align-items: center;
    gap: 16px;
}
.logo-area {
    display: flex;
    align-items: center;
}
.uroboros {
    color: #6c5ce7;
    font-size: 24px;
    margin-right: 8px;
}
.logo-text {
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-weight: 700;
    font-size: 22px;
    letter-spacing: 1px;
    color: #fff;
}
.header-meta h1 { margin: 0; font-size: 18px; font-weight: 600; }
.header-meta .subtitle { margin: 4px 0 0 0; font-size: 13px; color: #888; }
.report-footer {
    background: #0d0d14;
    color: #666;
    padding: 10px 24px;
    font-size: 12px;
    text-align: center;
}
"""
