import os, re, requests, logging
logger = logging.getLogger(__name__)

def fetch_pexels_cover(title):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return None
    words = [w for w in re.sub(r"[^a-zA-Z ]", "", title or "").split() if len(w) > 3][:3]
    q = " ".join(words) if words else "bitcoin technology"
    try:
        r = requests.get(f"https://api.pexels.com/v1/search?query={q}&per_page=1",
            headers={"Authorization": key}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large"]
    except Exception as e:
        logger.warning(f"Pexels fetch failed: {e}")
    return "https://images.pexels.com/photos/844124/pexels-photo-844124.jpeg?auto=compress&cs=tinysrgb&h=650&w=940"
