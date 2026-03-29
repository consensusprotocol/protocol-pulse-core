import os, logging, requests
from typing import Dict
logger = logging.getLogger(__name__)
_CACHE: Dict[str, str] = {}
DEFAULT = "/static/images/default-header.png"
TOPIC_MAP = {
    "mining": "bitcoin mining facility servers",
    "hashrate": "data center server rack",
    "etf": "stock market wall street trading",
    "halving": "bitcoin cryptocurrency gold",
    "lightning": "lightning network technology",
    "regulation": "government law financial",
    "inflation": "economy financial crisis",
    "blackrock": "wall street asset management",
    "saylor": "bitcoin corporate treasury",
    "defi": "decentralized finance blockchain",
    "stablecoin": "cryptocurrency digital currency",
    "default": "bitcoin cryptocurrency technology dark",
}
def _query(title, category=""):
    t = f"{title} {category}".lower()
    for kw, q in TOPIC_MAP.items():
        if kw in t:
            return q
    return TOPIC_MAP["default"]
def get_pexels_image(title, category="bitcoin"):
    api_key = os.environ.get("PEXELS_API_KEY","").strip()
    if not api_key:
        return DEFAULT
    q = _query(title, category)
    if q in _CACHE:
        return _CACHE[q]
    try:
        r = requests.get("https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": q, "per_page": 3, "orientation": "landscape"},
            timeout=8)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if photos:
            url = photos[0]["src"]["large2x"]
            _CACHE[q] = url
            return url
    except Exception as e:
        logger.error(f"Pexels error: {e}")
    _CACHE[q] = DEFAULT
    return DEFAULT
