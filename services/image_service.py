# Protocol Pulse Editorial Image Service
# 90% Pexels stock photos, 10% Grok hyper-realistic (top articles with named people/brands only)
# Red/black brand overlay on all images for cohesive look
# ALL image outputs are guarded via image_guard (phash dedup, ban list, quality).

import os
import re
import sys
import time
import logging
import sqlite3
import requests
import hashlib
import threading
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from io import BytesIO

logger = logging.getLogger(__name__)

# ── image_guard import ─────────────────────────────────────────────
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_svc_path = os.path.join(_repo_root, "services")
if _svc_path not in sys.path:
    sys.path.insert(0, _svc_path)
from articles.image_guard import check_image_bytes, compute_phash, remember_accepted

# ── Module-level session phash set (prevents two calls in one process colliding) ─
_session_phashes = set()
_session_lock = threading.Lock()

# ── DB phash cache (loaded once per process, refreshed every 60s) ─
_db_phashes_cache = set()
_db_phashes_ts = 0.0
_DB_CACHE_TTL = 60  # seconds
_DB_PATH = os.path.expanduser("~/protocol_pulse/instance/protocol_pulse.db")


def _load_db_phashes():
    """Load all published image_phash values from DB, cached for 60s."""
    global _db_phashes_cache, _db_phashes_ts
    now = time.time()
    if now - _db_phashes_ts < _DB_CACHE_TTL and _db_phashes_cache:
        return set(_db_phashes_cache)
    try:
        conn = sqlite3.connect(_DB_PATH)
        rows = conn.execute(
            "SELECT image_phash FROM articles WHERE published=1 AND image_phash IS NOT NULL AND image_phash != ''"
        ).fetchall()
        conn.close()
        _db_phashes_cache = {r[0] for r in rows}
        _db_phashes_ts = now
    except Exception as e:
        logger.warning("Failed to load DB phashes: %s", e)
    return set(_db_phashes_cache)

HEADERS_DIR = Path("static/images/headers")
HEADERS_DIR.mkdir(parents=True, exist_ok=True)

# Target size: 1200x630 (OpenGraph standard, works for SEO, Substack, social)
TARGET_WIDTH = 1200
TARGET_HEIGHT = 630

# Keywords that indicate a "top article" worthy of Grok generation
TOP_ARTICLE_INDICATORS = [
    'michael saylor',
    'elon musk',
    'trump',
    'biden',
    'powell',
    'gensler',
    'blackrock',
    'fidelity',
    'jpmorgan',
    'goldman sachs',
    'sec ',
    'fed ',
    'federal reserve',
    'congress',
    'senate',
    'white house',
    'breaking:',
    'exclusive:',
    'just in:',
]

class ImageGenerationService:
    """Pexels-first image service with Grok fallback for premium articles.
    All outputs guarded via image_guard (phash dedup, ban list, quality).
    """

    def __init__(self):
        self.pexels_key = os.environ.get("PEXELS_API_KEY", "")
        self.xai_key = os.environ.get("XAI_API_KEY", "")
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.last_phash = None  # phash of most recently saved file

        if self.pexels_key:
            logger.info("Image service initialized with Pexels (primary)")
        else:
            logger.warning(
                "PEXELS_API_KEY not set — image service will use fallbacks only"
            )

        if self.xai_key:
            logger.info(
                "Grok image generation available (secondary, top articles only)"
            )

    # ─── GUARD HELPER ──────────────────────────────────────────────

    def _guard_pil_image(self, image, title):
        """Run image_guard on a PIL Image. Returns True if accepted, False if rejected."""
        if image is None:
            return False
        try:
            buf = BytesIO()
            image.save(buf, "JPEG", quality=90)
            img_bytes = buf.getvalue()
            db_ph = _load_db_phashes()
            with _session_lock:
                sp = set(_session_phashes)
            verdict = check_image_bytes(img_bytes, title_hint=title,
                                        db_phashes=db_ph, session_phashes=sp)
            if not verdict.ok:
                logger.info("Guard rejected image for '%s': %s", title[:50], verdict.reason)
                return False
            return True
        except Exception as e:
            logger.warning("Guard check error: %s", e)
            return True  # fail-open so we don't block production

    # ─── PUBLIC API ────────────────────────────────────────────────

    def generate_article_header_image(self,
                                      title,
                                      category=None,
                                      force_grok=False):
        """Generate a header image for an article.
        Returns: path string like '/static/images/headers/header_xxx.jpg'
        """
        path, _ = self.generate_article_header_image_with_phash(title, category, force_grok)
        return path

    def generate_article_header_image_with_phash(self,
                                                  title,
                                                  category=None,
                                                  force_grok=False):
        """Generate a header image, returning (path, file_phash).
        The file_phash is computed from the SAVED file bytes on disk.
        """
        safe_title = _safe_filename(title)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"header_{safe_title}_{timestamp}.jpg"
        filepath = HEADERS_DIR / filename

        # Priority: Grok (if key) -> Pexels (reliable) -> DALL-E -> branded fallback
        image = None

        # 1. Grok (primary — hyper-realistic, when xai_key available)
        if self.xai_key:
            logger.info(f"Generating Grok image for: {title[:50]}")
            grok_img = self._generate_grok_image(title)
            if self._guard_pil_image(grok_img, title):
                image = grok_img

        # 2. Pexels (reliable stock photo — guarded iteration)
        if image is None and self.pexels_key:
            logger.info(f"Using Pexels for: {title[:50]}")
            image = self._fetch_pexels_image(title, category)

        # 3. OpenAI DALL-E (tertiary fallback — guarded)
        if image is None and self.openai_key:
            logger.info(f"Using DALL-E for: {title[:50]}")
            dalle_img = self._generate_openai_image(title)
            if self._guard_pil_image(dalle_img, title):
                image = dalle_img

        # 4. Branded fallback (guarded)
        if image is None:
            logger.warning(f"All image sources failed for: {title[:50]}")
            fb_img = self._generate_fallback_image(title)
            if self._guard_pil_image(fb_img, title):
                image = fb_img
            else:
                image = fb_img  # fallback always accepted

        try:
            # Apply brand overlay and save
            image = _resize_and_crop(image, TARGET_WIDTH, TARGET_HEIGHT)
            image = _apply_brand_overlay(image)
            image.save(str(filepath), "JPEG", quality=85, optimize=True)
            result_path = f"/static/images/headers/{filename}"
            size_kb = filepath.stat().st_size // 1024
            logger.info(f"Saved header image: {result_path} ({size_kb}KB)")

            # Compute phash from SAVED file bytes
            file_phash = None
            try:
                with open(str(filepath), "rb") as fh:
                    file_phash = compute_phash(fh.read())
            except Exception as e:
                logger.warning("Failed to compute file phash: %s", e)

            self.last_phash = file_phash

            # Add to session set so two calls in one process cannot collide
            if file_phash:
                with _session_lock:
                    _session_phashes.add(file_phash)
                try:
                    remember_accepted(file_phash, title=title[:120])
                except Exception:
                    pass

            return result_path, file_phash
        except Exception as save_err:
            logger.error(f"Image save failed: {save_err}")
            self.last_phash = None
            return "/static/images/default-header.png", None

    # ─── PEXELS (PRIMARY — 90% of articles) ────────────────────────

    def _fetch_pexels_image(self, title, category=None):
        """Search Pexels for a relevant stock photo. Iterates ALL candidates
        through image_guard, returning the first that passes."""
        # Build query list: smart → title nouns → category → generic pool
        smart = _smart_pexels_query(title)
        base = _build_pexels_queries(title, category)

        # Add a rotating generic pool (20 entries, rotated by hash(title))
        _generic_pool = [
            "bitcoin mining rig close up", "data center server room blue lights",
            "city skyline night neon", "gold vault bars", "wall street trading floor",
            "circuit board macro photography", "lightning storm dark sky",
            "bank building architecture", "satellite earth orbit",
            "financial chart screen", "computer hardware close up",
            "stock exchange building", "technology abstract dark",
            "server rack data center", "digital lock cybersecurity",
            "gold coins wealth", "futuristic technology dark",
            "sunrise mountain landscape", "clock gears mechanism",
            "rocket launch space",
        ]
        pool_offset = int(hashlib.md5(title.encode()).hexdigest()[:8], 16) % len(_generic_pool)
        pool_picks = [_generic_pool[(pool_offset + i) % len(_generic_pool)] for i in range(3)]

        queries = ([smart] + base + pool_picks) if smart else (base + pool_picks)
        # Deduplicate preserving order
        seen_q = set()
        unique_queries = []
        for q in queries:
            if q and q not in seen_q:
                seen_q.add(q)
                unique_queries.append(q)

        # Ensure >= 3 queries
        while len(unique_queries) < 3:
            unique_queries.append("financial technology dark background")

        db_ph = _load_db_phashes()
        with _session_lock:
            sp = set(_session_phashes)

        for query in unique_queries:
            try:
                for _attempt in range(3):
                    resp = requests.get(
                        "https://api.pexels.com/v1/search",
                        headers={"Authorization": self.pexels_key},
                        params={
                            "query": query,
                            "per_page": 15,
                            "orientation": "landscape",
                            "size": "large",
                        },
                        timeout=10,
                    )
                    if resp.status_code == 429:
                        wait = max(int(resp.headers.get("Retry-After", 20)), 20)
                        logger.info("Pexels 429 on '%s', waiting %ds (attempt %d/3)", query, wait, _attempt + 1)
                        time.sleep(wait)
                        continue
                    break
                else:
                    logger.warning("Pexels 3x 429 on '%s', skipping query", query)
                    continue

                if resp.status_code != 200:
                    logger.warning(f"Pexels returned {resp.status_code} for '{query}'")
                    continue

                photos = resp.json().get("photos", [])
                if not photos:
                    logger.info(f"No Pexels results for '{query}', trying next query")
                    continue

                # Iterate ALL photos through guard — first accepted wins
                for photo in photos:
                    img_url = photo.get("src", {}).get("landscape") or photo.get(
                        "src", {}).get("large2x")
                    if not img_url:
                        continue

                    try:
                        img_resp = requests.get(img_url, timeout=15)
                        if img_resp.status_code != 200:
                            continue
                        img_bytes = img_resp.content
                    except Exception:
                        continue

                    # Guard check
                    verdict = check_image_bytes(img_bytes, title_hint=title,
                                                db_phashes=db_ph, session_phashes=sp)
                    if not verdict.ok:
                        logger.info("Pexels photo %s rejected: %s", photo.get("id", "?"), verdict.reason)
                        continue

                    img = Image.open(BytesIO(img_bytes)).convert("RGB")
                    logger.info(
                        f"Pexels hit: '{query}' → {photo.get('photographer', 'unknown')}"
                    )
                    return img

            except Exception as e:
                logger.error(f"Pexels error for '{query}': {e}")
                continue

        return None

    # ─── GROK (SECONDARY — top articles with named entities only) ───

    def _generate_grok_image(self, title):
        """Use Grok/xAI for hyper-realistic editorial images on premium articles."""
        prompt = _build_grok_prompt(title)

        try:
            resp = requests.post(
                "https://api.x.ai/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.xai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-imagine-image",
                    "prompt": prompt,
                    "n": 1,
                    "response_format": "b64_json",
                },
                timeout=60,
            )

            if resp.status_code != 200:
                logger.warning(
                    f"Grok image API returned {resp.status_code}: {resp.text[:200]}"
                )
                return None

            data = resp.json()
            b64 = data.get("data", [{}])[0].get("b64_json")
            if not b64:
                logger.warning("No b64_json in Grok response")
                return None

            import base64
            img = Image.open(BytesIO(base64.b64decode(b64))).convert("RGB")
            logger.info(f"Grok image generated: {img.size}")
            return img

        except Exception as e:
            logger.error(f"Grok image generation failed: {e}")
            return None

    # ─── OPENAI FALLBACK ────────────────────────────────────────────

    def _generate_openai_image(self, title):
        """Last resort: OpenAI DALL-E (no white frames, better prompt)."""
        prompt = (
            f"Editorial photograph for news article: {title[:100]}. "
            "Cinematic, dramatic lighting, dark moody tones with deep reds and blacks. "
            "Photojournalism style. NO text, NO logos, NO borders, NO frames, NO watermarks. "
            "Full bleed image, edge to edge. Hyper-realistic photography.")

        try:
            resp = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-image-1",
                    "prompt": prompt,
                    "n": 1,
                    "size": "1536x1024"
                },
                timeout=60,
            )

            if resp.status_code != 200:
                # Try DALL-E 3
                resp = requests.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": "1792x1024",
                        "quality": "hd"
                    },
                    timeout=60,
                )

            if resp.status_code == 200:
                data = resp.json()
                # Handle both URL and b64 responses
                item = data.get("data", [{}])[0]
                if "b64_json" in item:
                    import base64
                    return Image.open(
                        BytesIO(base64.b64decode(
                            item["b64_json"]))).convert("RGB")
                elif "url" in item:
                    img_resp = requests.get(item["url"], timeout=15)
                    if img_resp.status_code == 200:
                        return Image.open(BytesIO(
                            img_resp.content)).convert("RGB")

        except Exception as e:
            logger.error(f"OpenAI image generation failed: {e}")

        return None

    # ─── PURE FALLBACK (no API needed) ──────────────────────────────

    def _generate_fallback_image(self, title):
        """Generate a branded placeholder if all APIs fail."""
        img = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (10, 10, 10))
        draw = ImageDraw.Draw(img)

        # Red gradient bar at bottom
        for y in range(TARGET_HEIGHT - 80, TARGET_HEIGHT):
            alpha = (y - (TARGET_HEIGHT - 80)) / 80.0
            r = int(180 * alpha)
            draw.line([(0, y), (TARGET_WIDTH, y)], fill=(r, 0, 0))

        # Red accent line
        draw.line([(50, TARGET_HEIGHT - 90),
                   (TARGET_WIDTH - 50, TARGET_HEIGHT - 90)],
                  fill=(220, 38, 38),
                  width=2)

        return img

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────

def _safe_filename(title):
    """Convert title to safe filename."""
    safe = re.sub(r'[^\w\s-]', '', title)
    safe = re.sub(r'\s+', '_', safe).strip('_')
    return safe[:80]

def _is_top_article(title):
    """Check if article deserves Grok generation (named people/brands)."""
    lower = title.lower()
    return any(indicator in lower for indicator in TOP_ARTICLE_INDICATORS)


def _smart_pexels_query(title):
    """Ask Grok to pick the best Pexels search query for this article title.
    Returns a specific 3-5 word string, or None on failure."""
    try:
        import os as _os, json as _json, urllib.request as _ur
        _key = _os.environ.get('XAI_API_KEY', '')
        if not _key:
            return None
        _payload = _json.dumps({
            "model": "grok-3-mini-fast",
            "messages": [{
                "role": "user",
                "content": (
                    "News article title: " + title + "\n\n"
                    "Return ONLY a 3-5 word Pexels stock photo search query for this story. "
                    "Be specific and visual. Example: for a bitcoin ETF story say 'stock exchange trading floor'. "
                    "For Japan crypto regulation say 'Tokyo government parliament building'. "
                    "No quotes, no explanation, just the query."
                )
            }],
            "max_tokens": 15,
            "temperature": 0.2
        }).encode()
        _req = _ur.Request(
            'https://api.x.ai/v1/chat/completions',
            data=_payload,
            headers={'Authorization': 'Bearer ' + _key, 'Content-Type': 'application/json'},
            method='POST'
        )
        with _ur.urlopen(_req, timeout=8) as _r:
            _result = _json.loads(_r.read())
            _q = _result['choices'][0]['message']['content'].strip().strip('"').strip("'")
            # Must be 2-6 words, no URLs or special chars
            _words = _q.split()
            if 2 <= len(_words) <= 6 and all(c.isalnum() or c in ' -' for c in _q):
                return _q
    except Exception:
        pass
    return None


def _build_pexels_queries(title, category=None):
    """Build search queries from article title, most specific to most general."""
    queries = []

    # Extract key concepts
    lower = title.lower()

    # Topic-specific mappings
    topic_queries = {
        'mining': [
            'bitcoin mining facility', 'data center servers',
            'industrial computing'
        ],
        'etf': [
            'stock market trading floor', 'wall street financial',
            'investment portfolio'
        ],
        'regulation': [
            'government capitol building', 'legal gavel courtroom',
            'legislative chamber'
        ],
        'lightning': [
            'digital network connections', 'fiber optic cables',
            'electronic circuit board'
        ],
        'defi': [
            'blockchain technology abstract', 'digital finance network',
            'futuristic banking'
        ],
        'whale':
        ['ocean deep water', 'financial trading screens', 'stock market data'],
        'fed': [
            'federal reserve building', 'monetary policy finance',
            'central banking'
        ],
        'inflation': [
            'economic charts data', 'currency money finance',
            'financial markets'
        ],
        'adoption': [
            'global technology innovation', 'digital transformation',
            'modern city technology'
        ],
        'security': [
            'cybersecurity digital lock', 'encrypted data protection',
            'secure vault'
        ],
        'energy': [
            'renewable energy solar', 'power grid electricity',
            'industrial energy'
        ],
        'ai': [
            'artificial intelligence technology', 'futuristic computer',
            'neural network'
        ],
        'quantum': [
            'quantum computing technology', 'advanced processor chip',
            'scientific research lab'
        ],
        'cbdc': [
            'central bank digital', 'government finance technology',
            'monetary system'
        ],
        'halving':
        ['bitcoin gold scarcity', 'precious metals vault', 'digital gold'],
    }

    for keyword, pexels_queries in topic_queries.items():
        if keyword in lower:
            queries.extend(pexels_queries[:2])

    # Generic financial/tech queries based on category
    if category:
        cat_lower = category.lower()
        if cat_lower in ('bitcoin', 'breakingbitcoin'):
            queries.append('cryptocurrency technology dark')
        elif cat_lower == 'opinion':
            queries.append('editorial newspaper desk')
        elif cat_lower == 'macro':
            queries.append('global economy financial markets')

    # Topic-specific fallbacks before generics
    title_lower = title.lower() if title else ''
    extra_map = {
        'japan': 'Tokyo parliament government building',
        'vietnam': 'Ho Chi Minh City skyline business',
        'korea': 'Seoul financial district night',
        'europe': 'European parliament Brussels aerial',
        'uk': 'London Canary Wharf financial district',
        'australia': 'Sydney CBD skyline harbor',
        'cia': 'intelligence agency government building',
        'fbi': 'federal law enforcement headquarters',
        'lawsuit': 'courtroom gavel law scales justice',
        'arrest': 'handcuffs law enforcement federal agents',
        'blackrock': 'Wall Street skyscraper asset management',
        'strategy': 'corporate boardroom executive meeting',
        'stablecoin': 'digital payment network currency',
        'treasury': 'government treasury financial building',
        'tariff': 'shipping containers port trade cargo',
        'oklx': 'cryptocurrency exchange digital trading',
        'circle': 'digital currency fintech office',
        'freeze': 'frozen seized assets law enforcement',
        'hack': 'cybersecurity network breach dark screen',
        'quantum': 'quantum computer laboratory research',
        'senate': 'US Senate Capitol building Washington',
        'congress': 'Capitol Hill Washington DC government',
        'nasdaq': 'Nasdaq stock exchange trading floor',
        'nyse': 'New York Stock Exchange Wall Street',
        'etf': 'stock exchange trading floor investors',
        'miner': 'bitcoin mining facility server warehouse',
        'hashrate': 'data center computing servers bitcoin',
        'fed': 'Federal Reserve building Washington bank',
        'gold': 'gold bars vault precious metals',
        'oil': 'oil refinery energy petroleum industrial',
        'defi': 'blockchain decentralized network nodes',
        'nft': 'digital art gallery screen display',
    }
    for kw, q in extra_map.items():
        if kw in title_lower and q not in queries:
            queries.insert(0, q)
            break

    # Generic fallbacks last resort
    queries.extend([
        'financial technology dark',
        'digital economy abstract',
        'modern technology dark background',
    ])

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique[:5]  # Max 5 queries to avoid rate limits

def _build_grok_prompt(title):
    """Build a unique, hyper-realistic prompt — title-driven so every article gets a distinct image."""
    import hashlib

    tl = title.lower()
    h = int(hashlib.md5(title.encode()).hexdigest()[:8], 16)

    # Category detection — but with multiple scene variants per category
    if any(w in tl for w in ["mining", "miner", "hashrate", "difficulty", "asic", "bitfarms", "mara", "riot", "cleanspark"]):
        scenes = [
            "Inside a cavernous Bitcoin mining warehouse at night. Thousands of ASIC rigs in perfect rows, blue LED status lights flickering. Heat haze rising from the machines. A lone technician with a flashlight.",
            "Aerial drone shot of a remote mining facility surrounded by snow-capped mountains. Steam rising from cooling towers. Utility lines stretching to the horizon. Industrial scale in pristine wilderness.",
            "Close-up of a mining rig circuit board, extreme macro photography. Copper traces and silicon chips in sharp focus. Heat sink fins catching light. The microscopic heart of Bitcoin.",
            "A mining operator studying server rack diagnostics on a handheld tablet. Dark server room, faces lit blue by screens. Rows of machines disappear into darkness behind them.",
        ]
        cameras = ["Sony A7R V, 24mm wide angle", "DJI Mavic 3, aerial", "Nikon Z9, 100mm macro", "Leica Q3, 35mm documentary"]
    elif any(w in tl for w in ["congress", "senator", "regulation", "sec", "policy", "law", "bill", "warren", "gensler", "cftc", "clarity act"]):
        scenes = [
            "The marble halls of the U.S. Capitol building at dusk. Dramatic shafts of late light through tall windows. A lone legislator silhouetted, papers in hand.",
            "A Senate hearing room: long mahogany table, nameplates, water pitchers. Empty chairs but documents scattered — testimony about to begin. Overhead lighting creates drama.",
            "Exterior of the SEC headquarters in Washington D.C. on an overcast day. American flag at half-staff. Security checkpoint visible. Institutional weight.",
            "A congressional aide rushing through marble corridors, arms full of briefing documents. Blurred background suggests urgency. Power and bureaucracy in motion.",
        ]
        cameras = ["Leica Q3, 28mm political", "Canon R3, 24mm architectural", "Nikon Z8, 35mm editorial", "Sony A7IV, 85mm f/1.4"]
    elif any(w in tl for w in ["etf", "blackrock", "fidelity", "401k", "retirement", "institutional", "morgan stanley", "goldman"]):
        scenes = [
            "A sleek trading floor at dawn: massive curved screens showing Bitcoin ETF inflows, traders arriving with coffee. Floor-to-ceiling glass overlooking a waking city.",
            "An executive in a corner office studying a tablet showing Bitcoin ETF performance charts. City skyline behind her at golden hour. Decision at scale.",
            "Close-up of a Bloomberg terminal screen showing ETF ticker data. Fingers typing. Blurred trading floor background. Institutional capital moving.",
            "The lobby of a major financial institution: marble floors, high ceilings, digital displays showing market data. A security guard watches. Old money meets new asset.",
        ]
        cameras = ["Nikon Z9, 50mm f/1.4", "Canon R5, 35mm", "Sony A1, 85mm macro", "Hasselblad X2D, 45mm"]
    elif any(w in tl for w in ["price", "surge", "crash", "bull", "bear", "rally", "plunge", "liquidation", "dip", "ath", "all-time"]):
        scenes = [
            "Rain-soaked financial district at night. Street lights reflect in puddles. A digital billboard shows cryptocurrency prices. One figure with an umbrella walks past.",
            "A trader's multiple monitor setup in a dark home office. Charts everywhere. An energy drink half-drunk. The solitary intensity of market watching at 3am.",
            "Aerial view of Wall Street intersection at rush hour. Yellow cabs, suits, motion blur. The physical city underneath the digital markets.",
            "A stock ticker display in a public space, strangers looking up at numbers. Diverse crowd reactions — some alarmed, some excited. Markets touching everyday life.",
        ]
        cameras = ["Fujifilm GFX100, 45mm", "Sony A7IV, 35mm documentary", "DJI Mavic 3, aerial", "Leica M11, 28mm street"]
    elif any(w in tl for w in ["hack", "theft", "heist", "fraud", "scam", "exploit", "breach", "attack", "stolen", "phishing"]):
        scenes = [
            "A darkened room lit only by the glow of multiple monitors showing scrolling terminal code. A silhouetted figure hunched forward. Digital forensics atmosphere.",
            "Close-up of a person's hands on a keyboard, faces obscured. Extreme shallow depth of field. Monitor glow catching just the knuckles. Menace and anonymity.",
            "Law enforcement agents in a server room, pointing flashlights at equipment being seized. Evidence bags. The moment digital crime meets physical reality.",
            "A cracked phone screen on concrete showing a crypto wallet with zero balance. Dramatic lighting from one side. The human cost of digital theft.",
        ]
        cameras = ["Sony A1, 85mm f/1.2 thriller", "Nikon Z9, 50mm macro", "Canon R3, 24mm documentary", "Leica SL2, 35mm"]
    elif any(w in tl for w in ["quantum", "technology", "ai ", "artificial intelligence", "algorithm"]):
        scenes = [
            "A quantum computing lab: cylindrical cryogenic chambers suspended from the ceiling, golden connectors, cables descending into a machine that operates near absolute zero.",
            "A researcher in a clean room suit working with fiber optic cables. Blue light from optical equipment. The frontier of computation made physical.",
            "A server farm corridor at night. Emergency lighting only. The hum of cooling fans. Endless racks of the digital infrastructure underpinning civilization.",
            "Close-up of a computer chip being installed with robotic precision arms. Extreme macro, shallow DOF. Silicon and human ingenuity.",
        ]
        cameras = ["Canon R5, 35mm sci-fi editorial", "Sony A7R V, 85mm", "Leica Q3, 28mm", "Nikon Z9, 100mm macro"]
    elif any(w in tl for w in ["lightning", "layer 2", "node", "wallet", "self-custody", "hardware wallet", "coldcard", "ledger", "passport"]):
        scenes = [
            "Weathered hands holding a small hardware wallet device. Extreme shallow DOF, background completely blurred. The weight of self-sovereignty in a palm.",
            "A node operator in their home office: a Raspberry Pi with LED indicators, cables, a small screen showing block height. Unpretentious digital sovereignty.",
            "A network visualization: glowing nodes connected by light trails across a dark background. Geographic spread of the Bitcoin network made tangible.",
            "A person at a kitchen table setting up a cold storage device. Natural window light. Ordinary space, extraordinary act of financial self-determination.",
        ]
        cameras = ["Nikon Z8, 85mm macro intimate", "Sony A7IV, 35mm documentary", "Canon R6 II, 24mm", "Fuji X-T5, 56mm natural light"]
    elif any(w in tl for w in ["trump", "president", "white house", "executive order", "david sacks"]):
        scenes = [
            "The White House South Lawn at dusk. Warm amber light from windows. American flags in a light breeze. Power and consequence made architectural.",
            "A press briefing podium in a wood-panelled room. Microphones clustered. Empty chairs facing it. The moment before a market-moving announcement.",
            "Pennsylvania Avenue at night with long-exposure light trails. The White House illuminated in the background. History in motion.",
            "A high-ranking official's desk: leather blotter, sealed documents, pen poised. Hand visible but face cropped. Authority and decision.",
        ]
        cameras = ["Canon R3, 70-200mm political", "Leica Q3, 28mm", "Nikon Z9, 24mm long exposure", "Sony A1, 85mm"]
    elif any(w in tl for w in ["defi", "solana", "ethereum", "uniswap", "aave", "protocol", "smart contract", "dao", "nft"]):
        scenes = [
            "A developer's multiple-monitor setup: code on one screen, protocol architecture diagrams on another. Empty coffee cups. The unglamorous reality of building decentralized finance.",
            "A conference panel on stage: speakers in front of a large screen showing blockchain data visualizations. Audience silhouettes in the foreground.",
            "Close-up of a laptop screen showing Solidity code or a DeFi protocol dashboard. Shallow DOF, soft background light. The beauty of functional code.",
            "A hacker space: whiteboards covered in protocol architecture diagrams, laptops open, energy drinks. Where decentralized finance gets built.",
        ]
        cameras = ["Sony A7IV, 35mm documentary", "Canon R5, 50mm event", "Nikon Z8, 85mm macro", "Leica Q3, 28mm"]
    elif any(w in tl for w in ["stablecoin", "usdt", "usdc", "tether", "circle", "payment"]):
        scenes = [
            "A split-second currency exchange moment: hands passing a phone showing a stablecoin transfer. Motion blur on the hands. Instant settlement made human.",
            "A merchant's point-of-sale display showing crypto payment options alongside traditional methods. A customer deciding. Commerce at the frontier.",
            "Stack of physical dollar bills next to a phone showing a digital equivalent. Hard light creating drama. The two faces of the same value.",
            "An international money transfer office, late at night. Fluorescent light, a teller window, a customer sending remittance. Stablecoins disrupting this.",
        ]
        cameras = ["Leica M11, 35mm street", "Canon R6 II, 50mm", "Sony A7R V, 85mm still life", "Nikon Z9, 28mm"]
    elif any(w in tl for w in ["oil", "gold", "macro", "inflation", "fed ", "rate", "yield", "recession", "gdp", "bond"]):
        scenes = [
            "Oil refinery towers at dawn, fire stacks burning against a pink sky. Industrial scale and environmental tension. The old energy system.",
            "A gold vault interior: stacked bars catching warm light, narrow perspective, the density of physical wealth stored underground.",
            "A Federal Reserve building exterior on a grey morning. The institution that moves markets. Understated architecture, massive power.",
            "Economic data on a screen: charts trending in different directions, a hand pointing. The complexity of macro in one frame.",
        ]
        cameras = ["Hasselblad X2D, 65mm", "Leica SL2, 50mm", "Canon R3, 35mm", "Nikon Z9, 85mm"]
    else:
        # Default: title-seeded unique scenes so no two articles get the same fallback
        scenes = [
            "A journalist working late at a standing desk surrounded by multiple screens showing financial data. Monitor glow on their face. The 3am pursuit of truth.",
            "Aerial view of a sprawling data center at twilight, surrounded by mountains. Steam from cooling systems rising into cold air. The physical scale of the digital world.",
            "Close-up of weathered hands holding a hardware wallet. Shallow depth of field, soft warm background. The human side of digital sovereignty.",
            "A boardroom at golden hour: long table, empty chairs, documents scattered. Through floor-to-ceiling glass, a city skyline. Decision made and departed.",
            "Street-level view of a financial district at dawn. Morning light cutting between towers. A lone figure walking toward the light with purpose.",
            "A conference room where a deal just happened: champagne glasses half-empty, documents signed on the table. No people, just evidence of importance.",
            "A satellite view of Earth at night showing city lights — a metaphor for the global network of money, information, and power.",
            "A cargo ship at a port at dusk, cranes silhouetted. The physical infrastructure of global trade. Bitcoin as counterpoint.",
        ]
        cameras = [
            "Shot on Sony A7IV, 35mm, documentary style",
            "Shot on DJI Mavic 3, aerial photography",
            "Shot on Nikon Z8, 85mm macro, intimate portrait",
            "Shot on Canon R6 II, 24mm, architectural editorial",
            "Shot on Fuji X-T5, 56mm, street photography",
            "Shot on Leica Q3, 28mm, still life editorial",
            "Shot on Hasselblad X2D, 45mm, conceptual",
            "Shot on Canon R3, 70-200mm, telephoto compression",
        ]
        scene = scenes[h % len(scenes)]
        camera = cameras[h % len(cameras)]
        return (
            f"Hyper-realistic photograph for the news headline: \'{title}\'. "
            f"{scene} "
            f"{camera}. "
            "Color grading: deep shadows with subtle warm highlights, cinematic color science. "
            "CRITICAL: Must look like a REAL photograph. NOT AI render. NOT 3D. NOT illustration. "
            "NO text, NO typography, NO logos, NO crypto symbols. NO borders, NO frames, NO watermarks. Full bleed."
        )

    # For categorized articles — pick sub-variant using title hash
    variant = h % len(scenes)
    scene = scenes[variant]
    camera = cameras[variant]

    return (
        f"Hyper-realistic photograph for the news headline: \'{title}\'. "
        f"{scene} "
        f"{camera}. "
        "Color grading: deep shadows with subtle warm highlights, cinematic color science. "
        "Teal and orange complementary tones. "
        "CRITICAL: Must look like a REAL photograph by a professional photojournalist. "
        "NOT an AI render. NOT a 3D scene. NOT a digital illustration. "
        "NO text, NO typography, NO logos, NO Bitcoin coin symbols, NO crypto symbols. "
        "NO borders, NO frames, NO watermarks. Full bleed edge to edge."
    )



def _resize_and_crop(img, target_w, target_h):
    """Resize and center-crop to exact dimensions."""
    # Calculate aspect ratios
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        # Image is wider — fit height, crop width
        new_h = target_h
        new_w = int(target_h * img_ratio)
    else:
        # Image is taller — fit width, crop height
        new_w = target_w
        new_h = int(target_w / img_ratio)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Center crop
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    return img

def _apply_brand_overlay(img):
    """Apply subtle red/black brand overlay for cohesive look."""
    # Slightly darken the image
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.75)

    # Boost contrast slightly
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.15)

    # Add subtle red tint via overlay
    overlay = Image.new("RGB", img.size, (40, 0, 0))
    img = Image.blend(img, overlay, alpha=0.08)

    # Add gradient vignette (darker edges)
    vignette = Image.new("L", img.size, 255)
    draw = ImageDraw.Draw(vignette)
    w, h = img.size
    for i in range(40):
        opacity = int(255 * (1 - i / 40.0) * 0.4)
        draw.rectangle([i, i, w - i - 1, h - i - 1], outline=opacity)

    # Apply vignette
    img_array = img.copy()
    r, g, b = img_array.split()
    r = Image.composite(r, Image.new("L", img.size, 0), vignette)
    g = Image.composite(g, Image.new("L", img.size, 0), vignette)
    b = Image.composite(b, Image.new("L", img.size, 0), vignette)
    img = Image.merge("RGB", (r, g, b))

    # Add thin red accent line at bottom
    draw = ImageDraw.Draw(img)
    draw.line([(0, h - 3), (w, h - 3)], fill=(220, 38, 38), width=2)

    return img

# Singleton instance (imported by other modules)
image_service = ImageGenerationService()

# Standalone function aliases (imported by other modules)
def generate_article_header_image(title, category=None):
    return image_service.generate_article_header_image(title, category)

def generate_article_header_image_with_phash(title, category=None):
    return image_service.generate_article_header_image_with_phash(title, category)

def generate_opinion_header_image(title, category=None):
    return image_service.generate_article_header_image(title, category)
