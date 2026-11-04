import os, json, logging, re, requests, hashlib
logger = logging.getLogger(__name__)
DEFAULT = "/static/images/default-header.png"
_USED_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "pexels_used.json")

_STOP = {"bitcoin","network","landscape","overview","current","update","market","the","a","an",
         "and","of","for","in","on","to","is","its","with","by","from","as","at","or","that",
         "this","was","are","be","has","had","have","it","but","not","what","all","were",
         "when","we","there","can","been","one","if","would","about","their","will","up","out",
         "how","which","do","each","she","he","his","her","they","them","these","so","some",
         "could","other","than","then","now","only","very","just","also","after","into","over",
         "between","through","during","before","more","most","such","why","no","any","both",
         "new","like","may","our","your","here","where","who","still","analysis","detailed","pulse",
         "state","detailed","dynamics","exploration","examination","comprehensive","remains",
         "dynamic","continues","evolve","amid","shifting","signals","navigating","unfolding"}

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

_CATEGORY_QUERIES = {
    "bitcoin": "cryptocurrency digital gold",
    "defi": "decentralized finance blockchain",
    "regulation": "government regulation law",
    "mining": "crypto mining hardware",
    "market": "stock market trading",
    "lightning": "lightning network payment",
    "security": "cybersecurity digital lock",
    "nft": "digital art collectible",
}

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
    words = re.findall(r'[a-zA-Z]+', (title or "").lower())
    nouns = [w for w in words if w not in _STOP and len(w) > 2]
    return nouns[:4]


def _get_guard():
    """Import image_guard functions. Returns (check_fn, remember_fn) or (None, None)."""
    try:
        import sys
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        svc_path = os.path.join(repo_root, "services")
        if svc_path not in sys.path:
            sys.path.insert(0, svc_path)
        from articles.image_guard import check_image_bytes, remember_accepted
        return check_image_bytes, remember_accepted
    except ImportError:
        return None, None


def get_pexels_image(title, category="bitcoin", article_id=0,
                     db_phashes=None, session_phashes=None):
    """Fetch a Pexels image that passes image_guard dedup against DB + session + ban list.

    Args:
        db_phashes: set of phash strings from published articles in DB (loaded once by caller)
        session_phashes: mutable set of phashes accepted in current batch (caller accumulates)

    Returns:
        (url, phash) tuple. url=DEFAULT on failure. phash=None if guard unavailable.
    """
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return DEFAULT, None

    if db_phashes is None:
        db_phashes = set()
    if session_phashes is None:
        session_phashes = set()

    check_fn, remember_fn = _get_guard()
    used = _load_used()
    used_ids = set(used.values())

    # Build 3-tier query list
    queries = []
    # Tier 1: title nouns
    nouns = _extract_nouns(title)
    if nouns:
        q = " ".join(nouns[:3])
        if len(q) > 8:
            queries.append(q)
    # Tier 2: category-based
    cat_q = _CATEGORY_QUERIES.get((category or "").lower().strip())
    if cat_q and cat_q not in queries:
        queries.append(cat_q)
    # Tier 3: rotating diverse pool (3 different entries)
    for offset in [0, 7, 13]:
        dq = _DIVERSE_QUERIES[(article_id + offset) % len(_DIVERSE_QUERIES)]
        if dq not in queries:
            queries.append(dq)
        if len(queries) >= 5:
            break

    page = (int(hashlib.md5(str(article_id).encode()).hexdigest()[:4], 16) % 8) + 1

    for query in queries:
        try:
            for _attempt in range(3):
                r = requests.get("https://api.pexels.com/v1/search",
                    headers={"Authorization": api_key},
                    params={"query": query, "per_page": 15, "page": page, "orientation": "landscape"},
                    timeout=8)
                if r.status_code == 429:
                    import time as _t
                    wait = max(int(r.headers.get("Retry-After", 20)), 20)
                    logger.info("Pexels 429 on '%s', waiting %ds (attempt %d/3)", query, wait, _attempt+1)
                    _t.sleep(wait)
                    continue
                r.raise_for_status()
                break
            else:
                logger.error("Pexels query '%s': 3x 429, skipping", query)
                continue
            photos = r.json().get("photos", [])
            for photo in photos:
                pid = str(photo["id"])
                if pid in used_ids:
                    continue
                url = photo["src"]["large2x"]
                try:
                    img_r = requests.get(url, timeout=10)
                    img_r.raise_for_status()
                    img_bytes = img_r.content
                except Exception:
                    continue

                # Guard check with DB + session phashes
                if check_fn:
                    verdict = check_fn(img_bytes, title_hint=title,
                                       db_phashes=db_phashes, session_phashes=session_phashes)
                    if not verdict.ok:
                        logger.info("Pexels %s rejected: %s", pid, verdict.reason)
                        continue
                    phash = verdict.phash
                else:
                    phash = None

                # Accepted — record everywhere
                used[str(article_id)] = pid
                if len(used) > 200:
                    keys = sorted(used.keys(), key=lambda k: int(k) if k.isdigit() else 0)
                    used = {k: used[k] for k in keys[-200:]}
                _save_used(used)
                if phash:
                    session_phashes.add(phash)
                    db_phashes.add(phash)
                    if remember_fn:
                        remember_fn(phash, article_id=str(article_id), title=title or "")
                return url, phash

        except Exception as e:
            logger.error("Pexels query '%s': %s", query, e)

    return DEFAULT, None
