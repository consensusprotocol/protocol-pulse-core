import os, json, logging, re, requests, hashlib
logger = logging.getLogger(__name__)
_CACHE = {}
DEFAULT = "/static/images/default-header.png"
_USED_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "pexels_used.json")

# Stopwords to strip when building a query from the title
_STOP = {"bitcoin","network","landscape","overview","current","update","market","the","a","an",
         "and","of","for","in","on","to","is","its","with","by","from","as","at","or","that",
         "this","was","are","be","has","had","have","it","but","not","what","all","were",
         "when","we","there","can","been","one","if","would","about","their","will","up","out",
         "how","which","do","each","she","he","his","her","they","them","these","so","some",
         "could","other","than","then","now","only","very","just","also","after","into","over",
         "between","through","during","before","more","most","such","why","no","any","both",
         "new","like","may","our","your","here","where","who","still","analysis","detailed","pulse"}

# 20 varied Bitcoin-adjacent queries for rotation (no generic "bitcoin" or "crypto")
_DIVERSE_QUERIES = [
    "bitcoin mining rig close up", "data center server room blue lights",
    "city skyline night neon", "gold vault bars", "wall street trading floor",
    "circuit board macro photography", "lightning storm dark sky",
    "bank building architecture", "satellite earth orbit", "blockchain network abstract",
    "financial chart screen", "computer hardware close up", "digital currency coins",
    "stock exchange building", "technology abstract dark", "neon lights urban",
    "server rack data center", "digital lock cybersecurity", "gold coins wealth",
    "futuristic technology dark", "sunrise mountain landscape", "clock gears mechanism",
    "rocket launch space", "chess strategy game", "telescope observatory night",
    "factory industrial machinery", "ocean waves aerial", "library books knowledge",
    "compass navigation travel", "crystal glass abstract",
]

def _load_used():
    try:
        if os.path.exists(_USED_FILE):
            with open(_USED_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_used(used):
    try:
        os.makedirs(os.path.dirname(_USED_FILE), exist_ok=True)
        with open(_USED_FILE, "w") as f:
            json.dump(used, f)
    except Exception as e:
        logger.warning("Failed to save pexels_used.json: %s", e)

def _extract_nouns(title):
    """Extract distinctive nouns from a title, stripping stopwords."""
    words = re.findall(r'[a-zA-Z]+', (title or "").lower())
    nouns = [w for w in words if w not in _STOP and len(w) > 2]
    return nouns[:4]  # max 4 keywords

def _build_query(title, category, article_id):
    """Build a diverse Pexels query from the article title's distinctive nouns."""
    nouns = _extract_nouns(title)
    if nouns:
        q = " ".join(nouns[:3])
        if len(q) > 8:
            return q
    # Fallback: rotate through diverse queries seeded by article_id
    return _DIVERSE_QUERIES[article_id % len(_DIVERSE_QUERIES)]

def get_pexels_image(title, category="bitcoin", article_id=0):
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return DEFAULT

    used = _load_used()
    used_ids = set(used.values())

    q = _build_query(title, category, article_id)
    # Vary the page using a hash of the article_id to spread results
    page = (int(hashlib.md5(str(article_id).encode()).hexdigest()[:4], 16) % 8) + 1

    try:
        r = requests.get("https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": q, "per_page": 15, "page": page, "orientation": "landscape"},
            timeout=8)
        r.raise_for_status()
        photos = r.json().get("photos", [])
        if photos:
            # Pick the first photo whose ID is not already used
            for photo in photos:
                pid = str(photo["id"])
                if pid not in used_ids:
                    url = photo["src"]["large2x"]
                    used[str(article_id)] = pid
                    # Keep only last 60 entries
                    if len(used) > 60:
                        keys = sorted(used.keys(), key=lambda k: int(k) if k.isdigit() else 0)
                        used = {k: used[k] for k in keys[-60:]}
                    _save_used(used)
                    return url
            # All 15 were used — pick by index anyway
            url = photos[article_id % len(photos)]["src"]["large2x"]
            return url
    except Exception as e:
        logger.error("Pexels: %s", e)
    return DEFAULT
