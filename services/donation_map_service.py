#!/usr/bin/env python3
"""
Bitcoin/Crypto PAC & Donation Tracker — Protocol Pulse
=======================================================
Uses OpenFEC API (free personal key = 1000 req/hr) to surface:
  - Top individual donations to crypto-friendly candidates/PACs
  - Fairshake PAC + Defend American Jobs spend (the dominant crypto super PAC)
  - Crypto-adjacent independent expenditures (who PACs are spending to elect)
  - Daily change in donation velocity

Crypto-friendly candidate list: pro-Bitcoin senators/reps known to the community.
"""
import json, logging, os, time, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR   = Path("/home/ultron/protocol_pulse")
CACHE_PATH = BASE_DIR / "data" / "donation_pulse.json"
CACHE_TTL  = 3600  # 1 hour

API_BASE = "https://api.open.fec.gov/v1"

# Known crypto-friendly committee IDs (Fairshake PAC is the big one)
CRYPTO_PACS = {
    "C00835959": "Fairshake PAC",
    "C00835975": "Protect Progress (Fairshake affiliate)",
    "C00835983": "Defend American Jobs (Fairshake affiliate)",
    "C00694323": "Blockchain Association PAC",
    "C00835942": "Stand With Crypto Alliance",
}

# Pro-Bitcoin candidate keywords (FEC name search)
CRYPTO_CANDIDATE_KEYWORDS = [
    "Lummis", "Hagerty", "Scott", "Emmer", "McHenry",
    "Soto", "Torres", "Lawler", "Hill",
]


def _get(endpoint: str, params: dict, key: str) -> list:
    params["api_key"] = key
    try:
        r = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=12)
        if r.status_code == 429:
            logger.warning("OpenFEC rate limit hit")
            return []
        if not r.ok:
            logger.warning("OpenFEC %s: %s", r.status_code, r.text[:100])
            return []
        return r.json().get("results", [])
    except Exception as e:
        logger.error("OpenFEC error: %s", e)
        return []


def fetch_fairshake_spend(key: str) -> dict:
    """Get Fairshake PAC's latest independent expenditures — the Bitcoin super PAC."""
    results = []
    for cid, name in list(CRYPTO_PACS.items())[:2]:  # Top 2 to save quota
        data = _get("/schedules/schedule_e/", {
            "committee_id": cid,
            "per_page": 5,
            "sort": "-expenditure_date",
            "two_year_transaction_period": 2026,
        }, key)
        for d in data:
            results.append({
                "pac":         name,
                "candidate":   d.get("candidate_name", "?"),
                "support":     d.get("support_oppose_indicator", "?"),
                "amount":      d.get("expenditure_amount", 0),
                "date":        d.get("expenditure_date", ""),
                "description": d.get("expenditure_description", ""),
                "state":       d.get("candidate_office_state", ""),
            })
        time.sleep(0.5)

    total = sum(r["amount"] for r in results)
    return {"expenditures": results[:10], "total_spend": total}


def fetch_crypto_candidate_donations(key: str) -> list:
    """Get recent large donations TO crypto-friendly candidates."""
    donations = []
    # Search schedule A (individual contributions) filtered to crypto-adjacent committees
    for cid, pac_name in list(CRYPTO_PACS.items())[:3]:
        data = _get("/schedules/schedule_a/", {
            "committee_id": cid,
            "per_page": 5,
            "sort": "-contribution_receipt_date",
            "min_amount": 1000,
            "two_year_transaction_period": 2026,
        }, key)
        for d in data:
            donations.append({
                "donor":     d.get("contributor_name", "Anonymous"),
                "employer":  d.get("contributor_employer", ""),
                "amount":    d.get("contribution_receipt_amount", 0),
                "date":      d.get("contribution_receipt_date", ""),
                "recipient": pac_name,
                "state":     d.get("contributor_state", ""),
                "city":      d.get("contributor_city", ""),
            })
        time.sleep(0.5)

    donations.sort(key=lambda x: x["amount"], reverse=True)
    return donations[:10]


def fetch_crypto_committees(key: str) -> list:
    """Get all crypto/bitcoin related committees currently active."""
    committees = []
    for kw in ["bitcoin", "crypto", "blockchain", "digital asset", "fairshake"]:
        data = _get("/committees/", {
            "q": kw,
            "per_page": 5,
            "committee_type": ["O", "Q", "V", "W"],  # Super PACs + non-connected
            "cycle": 2026,
        }, key)
        for c in data:
            if c.get("committee_id") not in [x.get("id") for x in committees]:
                committees.append({
                    "id":      c.get("committee_id"),
                    "name":    c.get("name"),
                    "type":    c.get("committee_type_full", ""),
                    "state":   c.get("state", ""),
                    "party":   c.get("party_full", ""),
                    "cycle":   c.get("cycles", []),
                })
        time.sleep(0.3)
    return committees[:15]


def compute_pulse_score(fairshake: dict, donations: list, committees: list) -> dict:
    """Score 0-100 based on PAC spending velocity and donation activity."""
    spend   = fairshake.get("total_spend", 0)
    n_don   = len(donations)
    n_comm  = len(committees)
    top_don = donations[0]["amount"] if donations else 0

    # Scoring: spend velocity weighted most heavily
    spend_score = min(40, int(spend / 50000))   # $2M spend = 40pts
    don_score   = min(30, n_don * 3)             # 10 donations = 30pts
    comm_score  = min(20, n_comm * 2)            # 10 committees = 20pts
    size_score  = min(10, int(top_don / 10000))  # $100k top donor = 10pts

    total = spend_score + don_score + comm_score + size_score
    return {
        "score":       min(100, total),
        "label":       "HIGH" if total > 70 else ("MODERATE" if total > 40 else "LOW"),
        "spend_score": spend_score,
        "don_score":   don_score,
        "comm_score":  comm_score,
    }


def fetch_donation_pulse(force: bool = False) -> dict:
    """Master function. Returns full donation intelligence payload."""
    if not force and CACHE_PATH.exists():
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < CACHE_TTL:
            try:
                return json.loads(CACHE_PATH.read_text())
            except Exception:
                pass

    key = os.environ.get("OPENFEC_API_KEY", "DEMO_KEY")
    if key == "DEMO_KEY":
        logger.warning("Using DEMO_KEY — rate limited to 40/hr. Set OPENFEC_API_KEY.")

    t0 = time.time()
    logger.info("Fetching donation pulse (key: %s...)", key[:8])

    fairshake  = fetch_fairshake_spend(key)
    donations  = fetch_crypto_candidate_donations(key)
    committees = fetch_crypto_committees(key)
    pulse      = compute_pulse_score(fairshake, donations, committees)

    result = {
        "updated_at":       datetime.now(timezone.utc).isoformat(),
        "fetch_ms":         round((time.time() - t0) * 1000),
        "score":            pulse["score"],
        "label":            pulse["label"],
        "crypto_committees": len(committees),
        "states_active":    len(set(d.get("state","") for d in donations if d.get("state"))),
        "fairshake_spend":  fairshake.get("total_spend", 0),
        "fairshake_expenditures": fairshake.get("expenditures", []),
        "top_donations":    donations,
        "committees":       committees,
        "source":           "OpenFEC API (FEC Public Data)",
        "key_type":         "demo" if key == "DEMO_KEY" else "personal",
    }

    try:
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(result, indent=2, default=str))
    except Exception as e:
        logger.error("Cache write: %s", e)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    result = fetch_donation_pulse(force=True)
    print(f"\nPulse score:    {result['score']} ({result['label']})")
    print(f"Committees:     {result['crypto_committees']}")
    print(f"States active:  {result['states_active']}")
    print(f"Fairshake spend: ${result['fairshake_spend']:,.0f}")
    print(f"Top donations:")
    for d in result['top_donations'][:5]:
        print(f"  ${d['amount']:>10,.0f}  {d['donor'][:30]:30}  -> {d['recipient']}")
    print(f"\nFairshake expenditures:")
    for e in result['fairshake_expenditures'][:5]:
        print(f"  ${e['amount']:>10,.0f}  {e['support']:7}  {e['candidate'][:30]}")
