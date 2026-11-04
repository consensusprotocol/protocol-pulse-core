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

# 30 varied Bitcoin-adjacent queries for rotation
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
    return nouns[:4]

def _build_query(title, category, article_id):
    """Build a diverse Pexels query from the article title's distinctive nouns."""
    nouns = _extract_nouns(title)
    if nouns:
        q = " ".join(nouns[:3])
        if len(q) > 8:
            return q
    return _DIVERSE_QUERIES[article_id % len(_DIVERSE_QUERIES)]


def _check_with_guard(img_bytes, title):
    """Run image through image_guard if available. Returns (ok, phash)."""
    try:
        import sys, os as _os
        # image_guard lives at repo_root/services/articles/image_guard.py
        repo_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        guard_dir = _os.path.join(repo_root, "services", "articles")
        if guard_dir not in sys.path:
            sys.path.insert(0, _os.path.join(repo_root, "services"))
        from articles.image_guard import check_image_bytes, remember_accepted
        verdict = check_image_bytes(img_bytes, title_hint=title)
        return verdict.ok, verdict.phash, verdict.reason
    except ImportError:
        logger.debug("image_guard not available, skipping perceptual check")
        return True, None, "guard_unavailable"


def _remember_guard(phash, article_id, title):
    """Record accepted image in guard's recent cache."""
    try:
        import sys, os as _os
        repo_root = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        guard_dir = _os.path.join(repo_root, "services", "articles")
        if guard_dir not in sys.path:
            sys.path.insert(0, _os.path.join(repo_root, "services"))
        from articles.image_guard import remember_accepted
        remember_accepted(phash, article_id=str(article_id), title=title)
    except ImportError:
        pass


def get_pexels_image(title, category="bitcoin", article_id=0):
    """Fetch a Pexels image that passes image_guard checks (not banned, not duplicate)."""
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return DEFAULT, None  # (url, phash)

    used = _load_used()
    used_ids = set(used.values())

    q = _build_query(title, category, article_id)
    page = (int(hashlib.md5(str(article_id).encode()).hexdigest()[:4], 16) % 8) + 1

    # Try primary query, then a fallback query
    queries_to_try = [q]
    fallback_q = _DIVERSE_QUERIES[(article_id + 7) % len(_DIVERSE_QUERIES)]
    if fallback_q != q:
        queries_to_try.append(fallback_q)

    for query in queries_to_try:
        try:
            r = requests.get("https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": query, "per_page": 15, "page": page, "orientation": "landscape"},
                timeout=8)
            r.raise_for_status()
            photos = r.json().get("photos", [])
            for photo in photos:
                pid = str(photo["id"])
                if pid in used_ids:
                    continue
                url = photo["src"]["large2x"]
                # Download image bytes for guard check
                try:
                    img_r = requests.get(url, timeout=10, stream=True)
                    img_r.raise_for_status()
                    img_bytes = img_r.content
                except Exception:
                    continue

                ok, phash, reason = _check_with_guard(img_bytes, title)
                if not ok:
                    logger.info("Pexels photo %s rejected by guard: %s", pid, reason)
                    continue

                # Accepted — record in both systems
                used[str(article_id)] = pid
                if len(used) > 60:
                    keys = sorted(used.keys(), key=lambda k: int(k) if k.isdigit() else 0)
                    used = {k: used[k] for k in keys[-60:]}
                _save_used(used)
                if phash:
                    _remember_guard(phash, article_id, title)
                return url, phash

        except Exception as e:
            logger.error("Pexels query '%s': %s", query, e)

    return DEFAULT, None
