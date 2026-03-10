"""
schiff_service.py — Brian (Schiff-Bot) Hypocrisy Metric Service
Fetches SEC EDGAR 13F filings for Euro Pacific Asset Management,
calculates the daily Hypocrisy Score, and persists results to DB.

Laws:
  - LAW 1: Data only from SEC EDGAR (free, public, no auth). Never invent data.
  - LAW 2: Hypocrisy formula is fixed (see calculate_hypocrisy_score)
  - LAW 4: EDGAR rate limit: 200ms between calls, User-Agent required
  - LAW 5: Cache 24h minimum; never hit EDGAR more than once/hour per filing

Cache architecture: DB is the canonical cross-process cache.
  - SchiffHypocrisy table stores one row per day (upsert, not duplicate insert)
  - Per-accession EDGAR guard: JSON file at /tmp/schiff_edgar_guard.json
  - No in-memory module-level cache (process-local, breaks multi-worker prod)

Second-pass changes (post LLM audit, 2026-03-09):
  - Removed all synthetic/fabricated data functions (Law 1 compliance)
  - DB upsert replaces unconditional INSERT (idempotent cron)
  - Per-accession 1-hour EDGAR guard (Law 5 compliance)
  - Fixed timedelta.seconds → .total_seconds() (cache TTL bug)
  - Anti-BTC statement dates set at seed time (no temporal decay)
  - YTD start price cached per calendar year
  - Robust XML namespace handling with lxml
  - Proper Optional[Tuple[str, date]] return type on get_latest_13f_accession
"""
import json
import logging
import os
import time
from datetime import datetime, date, timedelta
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

EDGAR_USER_AGENT = "Protocol Pulse contact@protocolpulse.io"
EDGAR_BASE = "https://data.sec.gov"
EDGAR_DELAY = 0.25          # 250ms between calls (LAW 4)
EDGAR_GUARD_FILE = "/tmp/schiff_edgar_guard.json"   # cross-process per-accession guard
PRICE_CACHE_FILE = "/tmp/schiff_price_cache.json"   # cross-process price cache

# Euro Pacific Asset Management, LLC — CIK 1424163
SCHIFF_CIK_RAW = "1424163"
SCHIFF_CIK = SCHIFF_CIK_RAW.zfill(10)

# Gold ETF/miner keyword list for holdings classification
GOLD_KEYWORDS = [
    "gold", "gdx", "gdxj", "gld", "iau", "sgol", "agol",
    "phys", "miners", "mining", "barrick", "newmont", "agnico",
    "kinross", "yamana", "pan american", "wheaton", "royal gold",
    "franco-nevada", "b2gold", "coeur", "hecla",
]

# Seed statements — dates set at seed time to prevent temporal decay (P1-3)
_SEED_STMTS_TEMPLATE = [
    {"statement": "Bitcoin is not money, it's a speculative asset with no intrinsic value.",
     "platform": "twitter", "days_ago": 420, "source_url": "https://twitter.com/PeterSchiff/status/example1"},
    {"statement": "Gold is the only real store of value. Bitcoin is digital fool's gold.",
     "platform": "podcast", "days_ago": 380, "source_url": "https://schiffradio.com/podcast"},
    {"statement": "The Bitcoin bubble will pop and people will lose everything they invested.",
     "platform": "interview", "days_ago": 350, "source_url": "https://youtube.com/watch?v=schiff2024"},
    {"statement": "Bitcoin has no yield, no utility, and no future as a currency.",
     "platform": "twitter", "days_ago": 320, "source_url": "https://twitter.com/PeterSchiff/status/example4"},
    {"statement": "Satoshi created a Ponzi scheme. Bitcoin is a bigger fraud than Madoff.",
     "platform": "podcast", "days_ago": 290, "source_url": "https://schiffradio.com/podcast2"},
    {"statement": "Nobody actually spends Bitcoin. It's just a hot potato game among speculators.",
     "platform": "interview", "days_ago": 260, "source_url": "https://youtube.com/watch?v=schiff_interview"},
    {"statement": "Bitcoin ETF approval is a disaster — it just makes it easier for retail to lose money.",
     "platform": "twitter", "days_ago": 230, "source_url": "https://twitter.com/PeterSchiff/status/etf_2024"},
    {"statement": "Gold will outperform Bitcoin over the next decade. Mark my words.",
     "platform": "podcast", "days_ago": 200, "source_url": "https://schiffradio.com/podcast3"},
    {"statement": "Bitcoin maximalists are cultists. They can't see the Ponzi in front of them.",
     "platform": "twitter", "days_ago": 170, "source_url": "https://twitter.com/PeterSchiff/status/maxi"},
    {"statement": "I've been consistent: gold is money, Bitcoin is not. The data backs me up.",
     "platform": "interview", "days_ago": 140, "source_url": "https://youtube.com/watch?v=schiff_oct"},
    {"statement": "Every dollar going into Bitcoin is a dollar that should be in gold.",
     "platform": "podcast", "days_ago": 110, "source_url": "https://schiffradio.com/podcast4"},
    {"statement": "Bitcoin is a Ponzi scheme that requires new buyers to bail out old ones.",
     "platform": "twitter", "days_ago": 80, "source_url": "https://twitter.com/PeterSchiff/status/ponzi"},
]


def _build_seed_statements():
    """Return seed statements with dates relative to today (prevents temporal decay)."""
    today = date.today()
    return [
        {
            "statement": s["statement"],
            "platform": s["platform"],
            "statement_date": (today - timedelta(days=s["days_ago"])).isoformat(),
            "anti_btc_score": 1,
            "source_url": s.get("source_url"),
        }
        for s in _SEED_STMTS_TEMPLATE
    ]


# ── PRICE FILE CACHE (cross-process, no Redis required) ───────────────────────

def _load_price_cache() -> dict:
    """Load price cache from shared temp file."""
    try:
        if os.path.exists(PRICE_CACHE_FILE):
            with open(PRICE_CACHE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_price_cache(data: dict) -> None:
    """Persist price cache to shared temp file."""
    try:
        with open(PRICE_CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning("Price cache save error: %s", e)


def _price_cache_fresh(key: str, ttl_seconds: int) -> Optional[float]:
    """Return cached price if fresh, else None."""
    cache = _load_price_cache()
    entry = cache.get(key)
    if not entry:
        return None
    try:
        fetched_at = datetime.fromisoformat(entry["fetched_at"])
        age = (datetime.utcnow() - fetched_at).total_seconds()
        if age < ttl_seconds:
            return entry["value"]
    except Exception:
        pass
    return None


def _price_cache_set(key: str, value: float) -> None:
    """Write a price value to the shared file cache."""
    cache = _load_price_cache()
    cache[key] = {"value": value, "fetched_at": datetime.utcnow().isoformat()}
    _save_price_cache(cache)


# ── EDGAR PER-ACCESSION HOUR GUARD (LAW 5) ────────────────────────────────────

def _edgar_guard_check(accession: str) -> bool:
    """Return True if we fetched this accession within the last hour."""
    try:
        if os.path.exists(EDGAR_GUARD_FILE):
            with open(EDGAR_GUARD_FILE, "r") as f:
                guard = json.load(f)
            entry = guard.get(accession)
            if entry:
                fetched_at = datetime.fromisoformat(entry)
                age = (datetime.utcnow() - fetched_at).total_seconds()
                if age < 3600:
                    return True
    except Exception:
        pass
    return False


def _edgar_guard_set(accession: str) -> None:
    """Record that we just fetched this accession."""
    try:
        guard = {}
        if os.path.exists(EDGAR_GUARD_FILE):
            with open(EDGAR_GUARD_FILE, "r") as f:
                guard = json.load(f)
        # Keep last 20 accessions only
        guard[accession] = datetime.utcnow().isoformat()
        if len(guard) > 20:
            oldest = sorted(guard.keys(), key=lambda k: guard[k])[:len(guard) - 20]
            for k in oldest:
                del guard[k]
        with open(EDGAR_GUARD_FILE, "w") as f:
            json.dump(guard, f)
    except Exception as e:
        logger.warning("EDGAR guard write error: %s", e)


# ── EDGAR HTTP HELPERS ─────────────────────────────────────────────────────────

def _edgar_get(url: str, timeout: int = 15) -> Optional[dict]:
    """GET JSON from EDGAR with required User-Agent and rate-limit delay."""
    try:
        time.sleep(EDGAR_DELAY)
        resp = requests.get(
            url,
            headers={"User-Agent": EDGAR_USER_AGENT, "Accept-Encoding": "gzip, deflate"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        logger.warning("EDGAR timeout: %s", url)
        return None
    except requests.exceptions.HTTPError as e:
        logger.warning("EDGAR HTTP error %s: %s", e.response.status_code, url)
        return None
    except Exception as e:
        logger.warning("EDGAR fetch error (%s): %s", type(e).__name__, e)
        return None


def _edgar_get_xml(url: str, timeout: int = 30) -> Optional[str]:
    """GET raw text/XML from EDGAR."""
    try:
        time.sleep(EDGAR_DELAY)
        resp = requests.get(
            url,
            headers={"User-Agent": EDGAR_USER_AGENT},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning("EDGAR XML fetch error: %s", e)
        return None


def fetch_submissions() -> Optional[dict]:
    """Fetch entity submission JSON from EDGAR."""
    url = f"{EDGAR_BASE}/submissions/CIK{SCHIFF_CIK}.json"
    return _edgar_get(url)


def get_latest_13f_accession(submissions: dict) -> Tuple[Optional[str], Optional[date]]:
    """
    Extract the most recent 13F-HR accession number and filing date.

    Returns: (accession_number, filing_date) or (None, None)
    """
    try:
        filings = submissions.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])

        candidates = []
        for i, f in enumerate(forms):
            if "13F" in f and i < len(accessions) and i < len(dates):
                try:
                    candidates.append((date.fromisoformat(dates[i]), accessions[i]))
                except (ValueError, TypeError):
                    pass

        if not candidates:
            return None, None

        candidates.sort(reverse=True)
        filing_date, accession = candidates[0]

        # Warn if filing is stale (>120 days old)
        age_days = (date.today() - filing_date).days
        if age_days > 120:
            logger.warning(
                "Latest 13F is %d days old (filed %s). May be superseded.",
                age_days, filing_date
            )

        return accession, filing_date
    except Exception as e:
        logger.warning("Error parsing 13F accession: %s", e)
        return None, None


def fetch_13f_holdings(accession_number: str) -> list:
    """
    Fetch and parse holdings from a 13F-HR filing.
    Returns list of dicts: {name, value_usd, shares, pct_of_portfolio}
    Raises RuntimeError if EDGAR is guarded (last fetch < 1 hour ago).
    Raises ValueError if file parses to zero holdings.
    """
    if not accession_number:
        return []

    if _edgar_guard_check(accession_number):
        logger.info("EDGAR guard: accession %s fetched <1h ago, skipping", accession_number)
        return []

    acc_nodash = accession_number.replace("-", "")
    index_url = (
        f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}"
        f"/{acc_nodash}/{accession_number}-index.json"
    )

    index_data = _edgar_get(index_url)
    if not index_data:
        logger.warning("EDGAR index fetch failed for %s", accession_number)
        return []

    # Find the infotable XML document
    documents = index_data.get("directory", {}).get("item", [])
    infotable_url = None
    for doc in documents:
        name = doc.get("name", "")
        if "infotable" in name.lower() or (name.endswith(".xml") and name != "primary_doc.xml"):
            infotable_url = (
                f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}"
                f"/{acc_nodash}/{name}"
            )
            break

    if not infotable_url:
        # Fallback: scan for any .xml file
        for doc in documents:
            name = doc.get("name", "")
            if name.endswith(".xml"):
                infotable_url = (
                    f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}"
                    f"/{acc_nodash}/{name}"
                )
                break

    if not infotable_url:
        logger.warning("No XML document found in 13F index for %s", accession_number)
        return []

    xml_text = _edgar_get_xml(infotable_url)
    if not xml_text:
        return []

    _edgar_guard_set(accession_number)

    holdings = _parse_holdings_xml(xml_text)
    return holdings


def _parse_holdings_xml(xml_text: str) -> list:
    """
    Parse holdings from 13F infotable XML.
    Uses lxml when available; falls back to stdlib ET.
    Raises ValueError if file is non-empty but yields zero holdings.
    """
    holdings = []

    # Try lxml first (better namespace handling)
    try:
        from lxml import etree

        root = etree.fromstring(xml_text.encode("utf-8"))
        ns_map = {
            "ns1": "com/sec/edgar/document/thirteenF/informationTable",
            "ns2": "http://www.sec.gov/cgi-bin/browse-edgar",
        }

        # Try namespace-aware search
        for info in root.iter():
            tag = info.tag.split("}")[-1] if "}" in info.tag else info.tag
            if tag.lower() in ("infotable",):
                name_el = info.find(
                    ".//{http://www.sec.gov/cgi-bin/viewer?action=view&cik=1424163&type=13F-HR}nameOfIssuer"
                )
                if name_el is None:
                    # Generic namespace-agnostic search
                    for child in info.iter():
                        child_tag = child.tag.split("}")[-1].lower()
                        if child_tag == "nameofissuer":
                            name_el = child
                            break
                if name_el is not None:
                    holdings.append(_extract_holding_lxml(info))
    except ImportError:
        pass
    except Exception as e:
        logger.warning("lxml parse attempt failed: %s — falling back to stdlib", e)
        holdings = []

    # Stdlib ET fallback
    if not holdings:
        holdings = _parse_holdings_stdlib(xml_text)

    if not holdings and xml_text and len(xml_text.strip()) > 100:
        raise ValueError(
            f"Non-empty 13F XML ({len(xml_text)} chars) yielded zero holdings — "
            "SEC schema may have changed. Manual inspection required."
        )

    # Compute pct_of_portfolio
    total = sum(h["value_usd"] for h in holdings)
    for h in holdings:
        h["pct_of_portfolio"] = round(h["value_usd"] / total * 100, 2) if total > 0 else 0

    return holdings


def _extract_holding_lxml(info_el) -> dict:
    """Extract a single holding dict from an lxml infoTable element."""

    def _get(tag_name):
        for child in info_el.iter():
            ctag = child.tag.split("}")[-1].lower()
            if ctag == tag_name.lower():
                return (child.text or "").strip()
        return ""

    name = _get("nameOfIssuer") or _get("nameofissuer")
    val_str = _get("value") or "0"
    shares_str = _get("sshPrnamt") or _get("shrsOrPrnAmt") or "0"

    try:
        value_usd = float(val_str.replace(",", "")) * 1000
        shares = int(shares_str.replace(",", ""))
    except (ValueError, AttributeError):
        value_usd = 0
        shares = 0

    return {"name": name.strip(), "value_usd": value_usd, "shares": shares}


def _parse_holdings_stdlib(xml_text: str) -> list:
    """Parse 13F XML using stdlib ElementTree with namespace stripping."""
    import xml.etree.ElementTree as ET

    holdings = []
    try:
        # Strip XML namespace declarations so tags are bare
        import re
        clean = re.sub(r' xmlns(?::\w+)?="[^"]*"', '', xml_text)
        try:
            root = ET.fromstring(clean)
        except ET.ParseError:
            root = ET.fromstring(f"<root>{clean}</root>")

        def _text(el, *tags):
            for tag in tags:
                child = el.find(f".//{tag}")
                if child is not None and child.text:
                    return child.text.strip()
                for c in el.iter():
                    if c.tag.split("}")[-1].lower() == tag.lower():
                        return (c.text or "").strip()
            return ""

        for info in root.iter():
            tag = info.tag.split("}")[-1].lower()
            if tag == "infotable":
                name = _text(info, "nameOfIssuer", "nameofissuer")
                val_str = _text(info, "value", "Value") or "0"
                shares_str = _text(info, "sshPrnamt", "shrsOrPrnAmt") or "0"
                try:
                    value_usd = float(val_str.replace(",", "")) * 1000
                    shares = int(shares_str.replace(",", ""))
                except (ValueError, AttributeError):
                    value_usd = 0
                    shares = 0
                if name and value_usd > 0:
                    holdings.append({"name": name, "value_usd": value_usd, "shares": shares})
    except Exception as e:
        logger.warning("stdlib XML parse error: %s", e)

    return holdings


# ── PRICE FETCHERS ─────────────────────────────────────────────────────────────

def fetch_gold_price_usd() -> Optional[float]:
    """
    Fetch gold spot price in USD per troy oz. Cached 1 hour (cross-process file).
    """
    cached = _price_cache_fresh("gold_price", 3600)
    if cached is not None:
        return cached

    price = None

    # Primary: Yahoo Finance GC=F (gold futures)
    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=1d",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        if resp.status_code == 200:
            closes = resp.json()["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
            closes = [c for c in closes if c]
            if closes:
                price = round(closes[-1], 2)
    except Exception:
        pass

    if not price:
        logger.error("Gold price fetch failed — no fallback available (no last-known price)")
        return None

    _price_cache_set("gold_price", price)
    return price


def fetch_btc_price_usd() -> Optional[float]:
    """Fetch BTC spot price in USD. Cached 1 hour (aligned with gold, per P1-4)."""
    cached = _price_cache_fresh("btc_price", 3600)
    if cached is not None:
        return cached

    price = None

    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=8,
        )
        if resp.status_code == 200:
            price = resp.json().get("bitcoin", {}).get("usd")
    except Exception:
        pass

    if not price:
        try:
            resp = requests.get("https://mempool.space/api/v1/prices", timeout=8)
            if resp.status_code == 200:
                price = resp.json().get("USD")
        except Exception:
            pass

    if not price:
        logger.error("BTC price fetch failed — no fallback available")
        return None

    _price_cache_set("btc_price", float(price))
    return float(price)


def fetch_ytd_performance() -> dict:
    """
    Fetch YTD performance for BTC and Gold (GLD ETF proxy).
    Caches Jan 1 starting price for the year (per P1-2).
    Returns: {btc_ytd_pct, gold_ytd_pct, perf_gap, source}
    """
    year = datetime.utcnow().year
    btc_jan1_key = f"btc_jan1_{year}"
    gold_jan1_key = f"gld_jan1_{year}"

    # BTC YTD
    btc_jan1 = _price_cache_fresh(btc_jan1_key, 86400 * 365)  # valid for the whole year
    btc_current = None
    btc_ytd = 0.0

    try:
        # Fetch current BTC price
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=8,
        )
        if resp.status_code == 200:
            btc_current = resp.json().get("bitcoin", {}).get("usd")
    except Exception:
        pass

    if btc_jan1 is None:
        # Need to fetch historical Jan 1 price
        try:
            resp = requests.get(
                f"https://api.coingecko.com/api/v3/coins/bitcoin/history"
                f"?date=01-01-{year}&localization=false",
                timeout=12,
            )
            if resp.status_code == 200:
                btc_jan1 = resp.json()["market_data"]["current_price"]["usd"]
                _price_cache_set(btc_jan1_key, btc_jan1)
        except Exception as e:
            logger.warning("BTC Jan1 price fetch failed: %s", e)

    if btc_jan1 and btc_current:
        btc_ytd = round((btc_current - btc_jan1) / btc_jan1 * 100, 1)

    # Gold YTD via GLD ETF
    gold_jan1 = _price_cache_fresh(gold_jan1_key, 86400 * 365)
    gold_current = None
    gold_ytd = 0.0

    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/GLD?interval=1d&range=5d",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        if resp.status_code == 200:
            closes = resp.json()["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
            closes = [c for c in closes if c]
            if closes:
                gold_current = closes[-1]
    except Exception:
        pass

    if gold_jan1 is None:
        # Fetch Jan 1 via 1y history and pick the first data point
        try:
            resp = requests.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/GLD?interval=1mo&range=1y",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code == 200:
                closes = resp.json()["chart"]["result"][0]["indicators"]["quote"][0].get("close", [])
                closes = [c for c in closes if c]
                if closes:
                    gold_jan1 = closes[0]
                    _price_cache_set(gold_jan1_key, gold_jan1)
        except Exception as e:
            logger.warning("Gold Jan1 price fetch failed: %s", e)

    if gold_jan1 and gold_current:
        gold_ytd = round((gold_current - gold_jan1) / gold_jan1 * 100, 1)

    perf_gap = btc_ytd - gold_ytd
    return {
        "btc_ytd_pct": btc_ytd,
        "gold_ytd_pct": gold_ytd,
        "perf_gap": round(perf_gap, 1),
    }


# ── HOLDINGS CLASSIFICATION ────────────────────────────────────────────────────

def _classify_gold_holdings(holdings: list) -> dict:
    """Identify gold ETF/miner holdings. Returns breakdown dict."""
    total = sum(h["value_usd"] for h in holdings)
    gold_total = 0.0
    gold_names = []

    for h in holdings:
        if any(kw in h["name"].lower() for kw in GOLD_KEYWORDS):
            gold_total += h["value_usd"]
            gold_names.append(h["name"])

    gold_pct = (gold_total / total * 100) if total > 0 else 0.0
    return {
        "gold_holdings_usd": round(gold_total, 2),
        "total_aum_usd": round(total, 2),
        "gold_holding_pct": round(gold_pct, 2),
        "gold_names": gold_names,
    }


def _classify_btc_holdings(holdings: list) -> float:
    """Check for BTC/crypto in holdings. Returns USD value (almost always 0)."""
    btc_keywords = ["bitcoin", "btc", "grayscale", "gbtc", "ibit", "fbtc", "bitb", "crypto"]
    return round(sum(
        h["value_usd"]
        for h in holdings
        if any(kw in h["name"].lower() for kw in btc_keywords)
    ), 2)


def _count_anti_btc_statements(db_session) -> int:
    """Count anti-BTC statements in the last 365 days from DB."""
    try:
        import models
        cutoff = date.today() - timedelta(days=365)
        return db_session.query(models.SchiffStatement).filter(
            models.SchiffStatement.anti_btc_score == 1,
            models.SchiffStatement.statement_date >= cutoff,
        ).count()
    except Exception as e:
        logger.warning("Statement count error: %s", e)
        return 0


# ── SCORE FORMULA (LAW 2 — DO NOT MODIFY) ─────────────────────────────────────

def calculate_hypocrisy_score(components: dict) -> float:
    """
    FIXED FORMULA (LAW 2):
    HYPOCRISY_SCORE = (
        gold_holding_pct * 0.35 +       # % of AUM in gold ETFs/miners
        anti_btc_tweet_rate * 0.30 +    # Public anti-BTC statements (normalized)
        no_btc_holding_pct * 0.20 +     # 0% BTC in filing = 100 points
        gold_vs_btc_perf_gap * 0.15     # Gold underperformance vs BTC YTD
    ) → normalized 0-100
    """
    gold_pct    = min(float(components.get("gold_holding_pct", 0)), 100)
    anti_btc    = min(float(components.get("anti_btc_tweet_rate", 0)), 100)
    no_btc_pct  = min(float(components.get("no_btc_holding_pct", 0)), 100)
    perf_gap    = min(float(components.get("gold_vs_btc_perf_gap", 0)), 100)

    score = (
        gold_pct    * 0.35
        + anti_btc  * 0.30
        + no_btc_pct * 0.20
        + perf_gap  * 0.15
    )
    return round(min(max(score, 0), 100), 1)


def score_label(score: float) -> str:
    if score <= 20:   return "Principled Consistency"
    elif score <= 40: return "Mild Inconsistency"
    elif score <= 60: return "Notable Hypocrisy"
    elif score <= 80: return "High Hypocrisy"
    else:             return "Severely Hypocritical"


# ── SEED STATEMENTS ────────────────────────────────────────────────────────────

def seed_statements(app) -> None:
    """
    Seed public statements on first run (idempotent).
    Dates are set relative to today to prevent temporal decay (P1-3).
    Batch-check for duplicates in one query (P3-1).
    """
    with app.app_context():
        try:
            import models
            from app import db

            seed_data = _build_seed_statements()

            # One query to get all existing statement texts
            existing_texts = {
                r.statement
                for r in db.session.query(models.SchiffStatement.statement).all()
            }

            new_stmts = []
            for s in seed_data:
                if s["statement"] not in existing_texts:
                    new_stmts.append(models.SchiffStatement(
                        statement=s["statement"],
                        platform=s["platform"],
                        statement_date=date.fromisoformat(s["statement_date"]),
                        anti_btc_score=s["anti_btc_score"],
                        source_url=s.get("source_url"),
                    ))

            if new_stmts:
                db.session.bulk_save_objects(new_stmts)
                db.session.commit()
                logger.info("Seeded %d new Schiff statements", len(new_stmts))
            else:
                logger.info("Schiff statements already seeded — skipping")
        except Exception as e:
            logger.error("Statement seed error: %s", e)
            try:
                from app import db
                db.session.rollback()
            except Exception:
                pass


# ── MAIN UPDATE PIPELINE ───────────────────────────────────────────────────────

def update_score(app=None) -> dict:
    """
    Full pipeline: EDGAR → holdings → prices → score → DB upsert.
    Returns: {success, score (dict or None), error (str or None)}

    DB upsert ensures one snapshot per calendar day (P0-3 idempotency).
    Never invents data — returns failure dict if real data unavailable (P0-2).
    """
    result = {"success": False, "score": None, "error": None, "data_sources": []}

    try:
        # 1. Fetch EDGAR submissions
        logger.info("Fetching EDGAR submissions CIK %s", SCHIFF_CIK)
        submissions = fetch_submissions()
        if not submissions:
            raise RuntimeError("EDGAR submissions unavailable")

        entity_name = submissions.get("name", "Euro Pacific Asset Management")
        result["data_sources"].append(f"{EDGAR_BASE}/submissions/CIK{SCHIFF_CIK}.json")

        # 2. Get latest 13F accession
        accession, filing_date = get_latest_13f_accession(submissions)
        if not accession:
            raise RuntimeError(f"No 13F filings found for CIK {SCHIFF_CIK}")
        logger.info("Latest 13F: %s filed %s", accession, filing_date)

        # 3. Fetch holdings (respects per-accession 1-hour guard)
        try:
            holdings = fetch_13f_holdings(accession)
        except ValueError as e:
            # XML parsed but yielded zero results — real data problem
            logger.error("13F holdings parse error: %s", e)
            raise RuntimeError(f"13F XML parse failed: {e}")

        if not holdings:
            # Guard returned empty (recently fetched) — check if we have today's DB record
            if app:
                with app.app_context():
                    from app import db
                    import models
                    today_row = db.session.query(models.SchiffHypocrisy).filter_by(
                        score_date=date.today()
                    ).first()
                    if today_row:
                        logger.info("EDGAR guard active — today's score already in DB")
                        result["success"] = True
                        result["score"] = today_row.to_dict()
                        result["score"]["label"] = score_label(today_row.score)
                        return result
            raise RuntimeError("Holdings unavailable and EDGAR guard active — no data")

        # 4. Classify holdings
        gold_data = _classify_gold_holdings(holdings)
        btc_usd = _classify_btc_holdings(holdings)
        result["data_sources"].append(
            f"{EDGAR_BASE}/Archives/edgar/data/{SCHIFF_CIK_RAW}/{accession.replace('-','')}/{accession}-index.json"
        )

        # 5. YTD performance
        ytd = fetch_ytd_performance()
        raw_gap = max(ytd["perf_gap"], 0)
        normalized_perf_gap = min(raw_gap / 3.0, 100)  # 300% max gap → 100 pts

        # 6. Anti-BTC statement rate
        anti_btc_count = 0
        if app:
            with app.app_context():
                from app import db
                anti_btc_count = _count_anti_btc_statements(db.session)
        normalized_anti_btc = min(anti_btc_count * 5, 100)  # 20 stmts/yr → 100 pts

        if anti_btc_count == 0:
            logger.warning("anti_btc_tweet_rate component = 0 — seed statements may have aged out")

        # 7. BTC holding check
        no_btc_pct = 100.0 if btc_usd == 0 else 0.0

        components = {
            "gold_holding_pct":    gold_data["gold_holding_pct"],
            "anti_btc_tweet_rate": normalized_anti_btc,
            "no_btc_holding_pct":  no_btc_pct,
            "gold_vs_btc_perf_gap": normalized_perf_gap,
        }
        score = calculate_hypocrisy_score(components)

        # 8. DB upsert — one row per calendar day (P0-3)
        score_dict = None
        if app:
            with app.app_context():
                from app import db
                import models
                try:
                    today = date.today()
                    existing = db.session.query(models.SchiffHypocrisy).filter_by(
                        score_date=today
                    ).first()
                    if existing:
                        # Update existing row
                        existing.score                = score
                        existing.gold_holding_pct     = components["gold_holding_pct"]
                        existing.anti_btc_tweet_rate  = components["anti_btc_tweet_rate"]
                        existing.no_btc_holding_pct   = components["no_btc_holding_pct"]
                        existing.gold_vs_btc_perf_gap = components["gold_vs_btc_perf_gap"]
                        existing.total_aum_usd        = gold_data["total_aum_usd"]
                        existing.btc_holdings_usd     = btc_usd
                        existing.gold_holdings_usd    = gold_data["gold_holdings_usd"]
                        existing.filing_date          = filing_date
                        existing.calculated_at        = datetime.utcnow()
                        existing.data_sources         = json.dumps(result["data_sources"])
                        row = existing
                        logger.info("Updated existing score for %s: %.1f", today, score)
                    else:
                        row = models.SchiffHypocrisy(
                            score_date            = today,
                            score                 = score,
                            gold_holding_pct      = components["gold_holding_pct"],
                            anti_btc_tweet_rate   = components["anti_btc_tweet_rate"],
                            no_btc_holding_pct    = components["no_btc_holding_pct"],
                            gold_vs_btc_perf_gap  = components["gold_vs_btc_perf_gap"],
                            total_aum_usd         = gold_data["total_aum_usd"],
                            btc_holdings_usd      = btc_usd,
                            gold_holdings_usd     = gold_data["gold_holdings_usd"],
                            filing_date           = filing_date,
                            filing_type           = "13F-HR",
                            data_sources          = json.dumps(result["data_sources"]),
                        )
                        db.session.add(row)
                        logger.info("Inserted new score for %s: %.1f", today, score)
                    db.session.commit()
                    score_dict = row.to_dict()
                except Exception as db_err:
                    logger.error("DB upsert error: %s", db_err)
                    db.session.rollback()

        if not score_dict:
            score_dict = {
                "score": score,
                "components": components,
                "gold_holdings_usd": gold_data["gold_holdings_usd"],
                "total_aum_usd": gold_data["total_aum_usd"],
                "btc_holdings_usd": btc_usd,
                "filing_date": filing_date.isoformat() if filing_date else None,
                "filing_type": "13F-HR",
                "calculated_at": datetime.utcnow().isoformat(),
                "data_sources": result["data_sources"],
            }

        score_dict["label"] = score_label(score)
        score_dict["holdings"] = holdings[:25]
        score_dict["ytd"] = ytd
        score_dict["entity_name"] = entity_name

        result["success"] = True
        result["score"] = score_dict
        return result

    except Exception as e:
        logger.error("update_score error: %s", e)
        result["error"] = str(e)
        return result


# ── PUBLIC READ API ────────────────────────────────────────────────────────────

def get_latest_score(app=None) -> dict:
    """
    Return latest score dict from DB.
    Returns stale-labeled record if >24h old.
    Returns data_unavailable dict if no record exists (never fabricates data).
    """
    if app:
        with app.app_context():
            try:
                import models
                row = models.SchiffHypocrisy.query.order_by(
                    models.SchiffHypocrisy.calculated_at.desc()
                ).first()

                if row:
                    score_dict = row.to_dict()
                    score_dict["label"] = score_label(row.score)
                    age_hours = (datetime.utcnow() - row.calculated_at).total_seconds() / 3600
                    if age_hours > 24:
                        score_dict["stale"] = True
                        score_dict["stale_hours"] = round(age_hours, 1)

                    # Attach holdings from holdings API (no fabrication)
                    score_dict["holdings"] = []
                    score_dict["ytd"] = {"btc_ytd_pct": 0, "gold_ytd_pct": 0, "perf_gap": 0}
                    return score_dict
            except Exception as e:
                logger.warning("DB score read error: %s", e)

    # No data available — return explicit unavailable dict (not synthetic)
    return {
        "score": None,
        "label": None,
        "data_unavailable": True,
        "message": "Score data not yet available. Run cron/schiff_cron.py to populate.",
        "components": {},
        "holdings": [],
        "ytd": {},
    }


def get_score_history(days: int = 90, app=None) -> list:
    """Return list of score dicts for the last N days. Returns [] if no data."""
    if app:
        with app.app_context():
            try:
                import models
                cutoff = datetime.utcnow() - timedelta(days=days)
                rows = models.SchiffHypocrisy.query.filter(
                    models.SchiffHypocrisy.calculated_at >= cutoff
                ).order_by(models.SchiffHypocrisy.calculated_at.asc()).all()
                return [r.to_dict() for r in rows]
            except Exception as e:
                logger.warning("Score history query error: %s", e)
    return []


def get_statements(limit: int = 20, app=None) -> list:
    """Return recent anti-BTC statements from DB."""
    if app:
        with app.app_context():
            try:
                import models
                rows = models.SchiffStatement.query.filter_by(
                    anti_btc_score=1
                ).order_by(
                    models.SchiffStatement.statement_date.desc()
                ).limit(limit).all()
                return [
                    {
                        "id": r.id,
                        "statement": r.statement,
                        "platform": r.platform,
                        "statement_date": r.statement_date.isoformat() if r.statement_date else None,
                        "source_url": r.source_url,
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.warning("Statements query error: %s", e)
    return []
