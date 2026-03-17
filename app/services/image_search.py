import base64
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict


def reverse_image_links(image_url: str) -> List[Dict[str, str]]:
    encoded = urllib.parse.quote(image_url, safe="")
    return [
        {
            "name": "Google Lens",
            "url": f"https://lens.google.com/uploadbyurl?url={encoded}",
            "description": "Google Lens",
        },
        {
            "name": "Yandex Images",
            "url": f"https://yandex.com/images/search?rpt=imageview&url={encoded}",
            "description": "Yandex Images",
        },
        {
            "name": "TinEye",
            "url": f"https://tineye.com/search?url={encoded}",
            "description": "TinEye Reverse Search",
        },
        {
            "name": "Bing Visual Search",
            "url": f"https://www.bing.com/images/search?view=detailv2&iss=sbi&form=SBIVSP&q=imgurl:{encoded}",
            "description": "Bing Visual Search",
        },
    ]


def reverse_image_upload_pages() -> List[Dict[str, str]]:
    return [
        {
            "name": "Google Lens",
            "url": "https://lens.google.com/",
            "description": "Загрузите изображение вручную",
        },
        {
            "name": "Yandex Images",
            "url": "https://yandex.com/images/",
            "description": "Нажмите значок камеры для загрузки",
        },
        {
            "name": "TinEye",
            "url": "https://tineye.com/",
            "description": "Загрузите изображение для поиска",
        },
        {
            "name": "Bing Visual Search",
            "url": "https://www.bing.com/visualsearch",
            "description": "Загрузите изображение для поиска",
        },
    ]


def image_to_base64(image_path: str) -> Optional[str]:
    p = Path(image_path)
    if not p.exists():
        return None
    try:
        raw = p.read_bytes()
        ext = p.suffix.lower()
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(ext, "image/png")
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except OSError:
        return None
