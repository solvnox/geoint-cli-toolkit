import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict

from app.core.logger import log


def face_search_links(image_url: str = "") -> List[Dict[str, str]]:
    links = []
    if image_url:
        encoded = urllib.parse.quote(image_url, safe="")
        links.append({
            "name": "Yandex Images",
            "url": f"https://yandex.com/images/search?rpt=imageview&url={encoded}",
            "description": "Yandex хорошо распознаёт лица",
        })
        links.append({
            "name": "Google Lens",
            "url": f"https://lens.google.com/uploadbyurl?url={encoded}",
            "description": "Google Lens",
        })
    else:
        links.append({
            "name": "Yandex Images",
            "url": "https://yandex.com/images/",
            "description": "Загрузите фото — Yandex хорошо распознаёт лица",
        })
        links.append({
            "name": "Google Lens",
            "url": "https://lens.google.com/",
            "description": "Загрузите фото для поиска",
        })
    links.append({
        "name": "PimEyes",
        "url": "https://pimeyes.com/en",
        "description": "Специализированный поиск лиц (загрузка вручную)",
    })
    return links


def detect_face(image_path: str) -> Optional[str]:
    try:
        import cv2
    except ImportError:
        log.info("opencv-python not installed, skipping face detection")
        return None

    p = Path(image_path)
    if not p.exists():
        return None

    try:
        img = cv2.imread(str(p))
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        pad = int(max(w, h) * 0.3)
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad)
        y2 = min(img.shape[0], y + h + pad)
        face_img = img[y1:y2, x1:x2]
        out_path = p.parent / f"{p.stem}_face{p.suffix}"
        cv2.imwrite(str(out_path), face_img)
        return str(out_path)
    except Exception as e:
        log.warning("Face detection failed: %s", e)
        return None
