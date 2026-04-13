#!/usr/bin/env python3
"""
Bitcoin Bill Gap Tracker — Protocol Pulse
==========================================
Tracks all US federal Bitcoin/crypto legislation via LegiScan API.
Shows the gap between public sentiment and congressional action —
exactly like House of the People but for Bitcoin.

Data sources:
  - LegiScan API: bill status, votes, sponsors, full text
  - Polymarket:   prediction market odds on passage
  - SQLite poll:  native Protocol Pulse user votes per bill

Gap score = |public_support_pct - congressional_support_pct|
"""
import json, logging, os, sqlite3, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR   = Path("/home/ultron/protocol_pulse")
DB_PATH    = BASE_DIR / "instance/protocol_pulse.db"
CACHE_PATH = BASE_DIR / "data/bill_tracker.json"
CACHE_TTL  = 6 * 3600  # 6 hours

KEY = os.environ.get("LEGISCAN_API_KEY", "b3c6764f901c2f9e52850a173c4947c3")
LS_BASE = f"https://api.legiscan.com/?key={KEY}&op="

# ── Curated Bitcoin/crypto bill identifiers ──────────────────────────────────
# These are pre-seeded so the tracker works immediately without scanning all 173 bills.
# LegiScan bill_ids confirmed from API probe.
TRACKED_QUERIES = [
    "bitcoin",
    "GENIUS stablecoin",
    "CBDC anti-surveillance",
    "digital asset market structure",
    "cryptocurrency self custody",
]

# Bills we always want even if not in search results
PRIORITY_BILL_IDS = [
    2000399,  # BITCOIN Act (HB2032)
    2000465,  # BITCOIN Act Senate (SB954)
]

# Category tags for filtering/display
CATEGORY_KEYWORDS = {
    "strategic_reserve": ["strategic reserve", "bitcoin reserve", "strategic bitcoin"],
    "stablecoin":        ["stablecoin", "genius act", "payment stablecoin"],
    "cbdc":              ["cbdc", "central bank digital", "anti-surveillance"],
    "market_structure":  ["market structure", "fit21", "digital commodity", "digital asset market"],
    "self_custody":      ["self custody", "keep your coins", "not your keys"],
    "mining":            ["mining", "proof of work", "energy use"],
    "taxation":          ["tax", "capital gains", "de minimis"],
}

def _ls_get(op: str, **params) -> dict:
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{LS_BASE}{op}&{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ProtocolPulse/2.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            if d.get("status") != "OK":
                logger.warning("LegiScan %s error: %s", op, d.get("alert", "?"))
                return {}
            return d
    except Exception as e:
        logger.error("LegiScan %s failed: %s", op, e)
        return {}

def _categorize(title: str, description: str = "") -> list:
    text = (title + " " + description).lower()
    return [cat for cat, keywords in CATEGORY_KEYWORDS.items()
            if any(kw in text for kw in keywords)] or ["other"]

def _btc_signal(categories: list, congress_pct: float) -> str:
    """Signal for Bitcoin holders based on bill category and congressional support."""
    pro_btc = {"strategic_reserve", "self_custody", "market_structure"}
    anti_btc = {"cbdc"}
    cats = set(categories)
    if cats & pro_btc:
        return "bullish" if congress_pct >= 50 else "neutral"
    if cats & anti_btc:
        return "bearish" if congress_pct >= 50 else "neutral"
    return "neutral"

def search_crypto_bills() -> dict:
    """Search LegiScan for all Bitcoin/crypto bills, return {bill_id: bill_data}."""
    all_bills = {}

    for query in TRACKED_QUERIES:
        d = _ls_get("getSearch", query=urllib.request.quote(query), state="US")
        sr = d.get("searchresult", {})
        for key in sr:
            if not key.isdigit():
                continue
            b = sr[key]
            bid = b.get("bill_id")
            if bid and bid not in all_bills:
                all_bills[bid] = b
        time.sleep(0.2)  # rate limit courtesy

    logger.info("LegiScan search: found %d unique bills", len(all_bills))
    return all_bills

def fetch_bill_detail(bill_id: int) -> dict:
    """Fetch full bill detail including votes, sponsors, text."""
    d = _ls_get("getBill", id=bill_id)
    return d.get("bill", {})

def parse_vote_tally(bill_detail: dict) -> dict:
    """Extract congressional vote percentages from bill detail."""
    votes = bill_detail.get("votes", [])
    if not votes:
        return {"yea": 0, "nay": 0, "total": 0, "pct_yes": 0, "chamber": "", "date": ""}

    # Use the most recent roll call
    latest = sorted(votes, key=lambda v: v.get("date", ""), reverse=True)[0]
    yea = latest.get("yea", 0)
    nay = latest.get("nay", 0)
    total = yea + nay
    return {
        "yea":      yea,
        "nay":      nay,
        "total":    total,
        "pct_yes":  round(yea / total * 100) if total else 0,
        "chamber":  latest.get("chamber", ""),
        "date":     latest.get("date", ""),
        "roll_call_id": latest.get("roll_call_id", 0),
    }

def get_polymarket_odds(title: str) -> float:
    """Get Polymarket prediction market odds for bill passage. Returns 0-100."""
    try:
        from services.panopticon_service import fetch_polymarket_markets
        markets = fetch_polymarket_markets(10)
        title_lower = title.lower()
        keywords = [w for w in title_lower.split() if len(w) > 4]
        for m in markets:
            q = m.get("question", "").lower()
            if any(kw in q for kw in keywords[:3]):
                yes = m.get("yes_price", 0)
                return round(yes * 100) if yes else 0
    except Exception:
        pass
    return 0

def get_public_votes(bill_id: int) -> dict:
    """Get Protocol Pulse user votes for this bill from SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT yes_votes, no_votes FROM bill_public_votes WHERE bill_id=?",
            (bill_id,)
        ).fetchone()
        conn.close()
        if row:
            yes, no = row
            total = yes + no
            return {"yes": yes, "no": no, "total": total,
                    "pct_yes": round(yes / total * 100) if total else 50}
    except Exception:
        pass
    # No votes yet — use Polymarket as proxy
    return {"yes": 0, "no": 0, "total": 0, "pct_yes": 50}

def _ensure_poll_table():
    """Create the public votes table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bill_public_votes (
                bill_id       INTEGER PRIMARY KEY,
                bill_number   TEXT,
                yes_votes     INTEGER DEFAULT 0,
                no_votes      INTEGER DEFAULT 0,
                last_vote_at  TEXT,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Poll table creation: %s", e)

def cast_public_vote(bill_id: int, bill_number: str, vote: str) -> dict:
    """Record a public vote (yes/no) for a bill. Called from API endpoint."""
    _ensure_poll_table()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            INSERT INTO bill_public_votes (bill_id, bill_number, yes_votes, no_votes, last_vote_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(bill_id) DO UPDATE SET
                yes_votes    = yes_votes + ?,
                no_votes     = no_votes + ?,
                last_vote_at = ?
        """, (
            bill_id, bill_number,
            1 if vote == "yes" else 0,
            1 if vote == "no" else 0,
            datetime.now(timezone.utc).isoformat(),
            1 if vote == "yes" else 0,
            1 if vote == "no" else 0,
            datetime.now(timezone.utc).isoformat(),
        ))
        conn.commit()
        conn.close()
        return get_public_votes(bill_id)
    except Exception as e:
        logger.error("Vote cast failed: %s", e)
        return {}

def build_bill_record(search_result: dict, detail: dict) -> dict:
    """Build a complete bill record combining search result + detail + votes."""
    bill_id    = search_result.get("bill_id", detail.get("bill_id", 0))
    title      = search_result.get("title", detail.get("title", ""))
    categories = _categorize(title, detail.get("description", ""))
    vote_tally = parse_vote_tally(detail)
    pub_votes  = get_public_votes(bill_id)

    # Public support: use our poll if we have votes, else Polymarket, else 50%
    if pub_votes["total"] >= 5:
        public_pct = pub_votes["pct_yes"]
    else:
        pm_odds = get_polymarket_odds(title)
        public_pct = pm_odds if pm_odds > 0 else 50

    congress_pct = vote_tally["pct_yes"]
    gap = abs(public_pct - congress_pct) if vote_tally["total"] > 0 else None

    # Sponsor
    sponsors = detail.get("sponsors", [])
    sponsor  = sponsors[0] if sponsors else {}

    # Status
    status_id = detail.get("status", 0)
    status_map = {0:"Unknown", 1:"Introduced", 2:"Engrossed", 3:"Enrolled",
                  4:"Passed", 5:"Vetoed", 6:"Failed", 11:"Committee"}
    status_label = status_map.get(status_id, "In Progress")

    return {
        "bill_id":          bill_id,
        "bill_number":      search_result.get("bill_number", detail.get("bill_number", "")),
        "title":            title,
        "short_title":      _make_short_title(title),
        "categories":       categories,
        "btc_signal":       _btc_signal(categories, congress_pct),
        "status":           status_label,
        "status_id":        status_id,
        "last_action":      search_result.get("last_action", detail.get("last_action", "")),
        "last_action_date": search_result.get("last_action_date", detail.get("last_action_date", "")),
        "sponsor":          sponsor.get("name", ""),
        "sponsor_party":    sponsor.get("party", ""),
        "url":              search_result.get("url", f"https://legiscan.com/US/bill/{search_result.get('bill_number','')}/2025"),
        "vote_tally":       vote_tally,
        "congress_pct":     congress_pct,
        "public_pct":       public_pct,
        "public_votes":     pub_votes,
        "gap_score":        gap,
        "gap_label":        _gap_label(gap),
        "change_hash":      search_result.get("change_hash", ""),
        "updated_at":       datetime.now(timezone.utc).isoformat(),
    }

def _make_short_title(title: str) -> str:
    """Extract the short name from a bill title."""
    # Many bills have format: "SHORT NAME Act Full Description Act of 2025"
    if "Act of 2025" in title or "Act of 2026" in title:
        parts = title.split("Act of 20")[0].strip()
        if len(parts) < 60:
            return parts + " Act"
    return title[:55] + ("..." if len(title) > 55 else "")

def _gap_label(gap) -> str:
    if gap is None: return "PENDING VOTE"
    if gap >= 60:   return "MASSIVE GAP"
    if gap >= 40:   return "LARGE GAP"
    if gap >= 20:   return "MODERATE GAP"
    if gap >= 10:   return "SMALL GAP"
    return "ALIGNED"

def fetch_all_bills(force: bool = False) -> dict:
    """Master function. Returns full bill tracker payload."""
    # Check cache
    if not force and CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < CACHE_TTL:
            try:
                return json.loads(CACHE_PATH.read_text())
            except Exception:
                pass

    _ensure_poll_table()
    t0 = time.time()
    logger.info("Bill tracker: fetching from LegiScan...")

    search_results = search_crypto_bills()

    # Fetch full detail for each bill (respecting rate limits)
    bills = []
    hashes = {}

    # Load existing hashes to avoid redundant fetches
    if CACHE_PATH.exists():
        try:
            old = json.loads(CACHE_PATH.read_text())
            hashes = {b["bill_id"]: b["change_hash"] for b in old.get("bills", [])}
        except Exception:
            pass

    for bid, sr in list(search_results.items())[:40]:  # cap at 40 bills
        new_hash = sr.get("change_hash", "")
        if bid in hashes and hashes[bid] == new_hash and not force:
            # Hash unchanged — use cached detail
            continue
        detail = fetch_bill_detail(bid)
        if detail:
            record = build_bill_record(sr, detail)
            bills.append(record)
        time.sleep(0.3)  # LegiScan rate limit

    # Sort: most recent action first, then by gap score
    bills.sort(key=lambda b: (b.get("last_action_date",""), b.get("gap_score") or 0), reverse=True)

    # Summary stats
    voted   = [b for b in bills if b["vote_tally"]["total"] > 0]
    bullish = [b for b in bills if b["btc_signal"] == "bullish"]
    bearish = [b for b in bills if b["btc_signal"] == "bearish"]

    result = {
        "updated_at":     datetime.now(timezone.utc).isoformat(),
        "fetch_time_ms":  round((time.time() - t0) * 1000),
        "total_bills":    len(bills),
        "bills_with_votes": len(voted),
        "bullish_count":  len(bullish),
        "bearish_count":  len(bearish),
        "bills":          bills,
        "source":         "LegiScan API (CC BY 4.0)",
    }

    try:
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(result, indent=2, default=str))
        logger.info("Bill tracker: %d bills cached in %dms", len(bills), result["fetch_time_ms"])
    except Exception as e:
        logger.error("Cache write: %s", e)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    result = fetch_all_bills(force=True)
    print(f"\nTotal bills tracked: {result['total_bills']}")
    print(f"Bills with votes:    {result['bills_with_votes']}")
    print(f"Bullish for BTC:     {result['bullish_count']}")
    print(f"Bearish for BTC:     {result['bearish_count']}")
    print(f"Fetch time:          {result['fetch_time_ms']}ms")
    print(f"\nTop bills:")
    for b in result["bills"][:8]:
        gap = f"GAP {b['gap_score']}%" if b['gap_score'] is not None else "PENDING"
        print(f"  {b['bill_number']:12} {b['short_title'][:45]:45} [{gap}]")
        print(f"             {b['status']:20} | Congress: {b['congress_pct']}% | Public: {b['public_pct']}%")
        print(f"             {b['last_action'][:65]}")
