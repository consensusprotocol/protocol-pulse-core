"""
SESSION 9 — NODE WATCH
Blueprint: node_watch_bp
Routes:
  GET /node-watch                 — page
  GET /api/nodes/summary          — reachable/total/IPv4/IPv6/Tor/I2P + health score (cache 5min)
  GET /api/nodes/countries        — top 15 countries with % (cache 1h)
  GET /api/nodes/versions         — version distribution (cache 1h)
  GET /api/nodes/history          — node count over time (cache 24h)

Data strategy:
  - Bitnodes /api/v1/snapshots/ → total node count + snapshot URL
  - Bitnodes snapshot detail URL → full node data (country/version/network type)
  - ONE shared raw-snapshot cache avoids repeated API hits (cache 1h for detail)
  - History: /api/v1/snapshots/?limit=100 (each ~2h apart ≈ 200 days)
  - Rate-limit safeguard: all endpoints degrade gracefully to stale or empty state
"""

import logging
import re
import time
from typing import Optional

import requests
from flask import Blueprint, jsonify, make_response, render_template

node_watch_bp = Blueprint("node_watch", __name__)
log = logging.getLogger(__name__)

BITNODES_BASE = "https://bitnodes.io/api/v1"
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "ProtocolPulse/1.0 (bitcoin-network-monitor)",
}
_TIMEOUT = 12  # seconds

# ---------------------------------------------------------------------------
# Shared raw-data cache — ONE fetch populates all derived endpoints
# ---------------------------------------------------------------------------
_raw: dict = {
    # Snapshot list: total count + snapshot URL + previous count
    "list": {"data": None, "expires": 0.0},
    # Full node detail: parsed per-node data (versions, countries, net types)
    "detail": {"data": None, "expires": 0.0},
    # History: [{ts, count}, ...]
    "history": {"data": None, "expires": 0.0},
}

_TTL_LIST   = 5 * 60        # 5 min — refreshes the total count
_TTL_DETAIL = 60 * 60       # 1 h  — per-node breakdown
_TTL_HISTORY = 24 * 60 * 60 # 24 h


# ---------------------------------------------------------------------------
# Country meta
# ---------------------------------------------------------------------------
_CC_NAMES: dict[str, str] = {
    "US": "United States", "DE": "Germany",    "FR": "France",
    "NL": "Netherlands",   "CA": "Canada",     "GB": "United Kingdom",
    "JP": "Japan",         "AU": "Australia",  "SG": "Singapore",
    "RU": "Russia",        "CH": "Switzerland","FI": "Finland",
    "SE": "Sweden",        "HK": "Hong Kong",  "CN": "China",
    "AT": "Austria",       "BR": "Brazil",     "NO": "Norway",
    "IT": "Italy",         "ES": "Spain",      "PL": "Poland",
    "CZ": "Czech Republic","RO": "Romania",    "IN": "India",
    "KR": "South Korea",   "NZ": "New Zealand","BE": "Belgium",
    "AR": "Argentina",     "MX": "Mexico",     "UA": "Ukraine",
    "ZA": "South Africa",  "TR": "Turkey",     "TW": "Taiwan",
    "IL": "Israel",        "IR": "Iran",       "ID": "Indonesia",
    "PT": "Portugal",      "DK": "Denmark",    "HU": "Hungary",
    "??": "Unknown",
}

CC_COORDS: dict[str, list] = {
    "US": [37.09, -95.71],   "DE": [51.17, 10.45],   "FR": [46.23, 2.21],
    "NL": [52.13, 5.29],     "CA": [56.13, -106.35], "GB": [55.38, -3.44],
    "JP": [36.20, 138.25],   "AU": [-25.27, 133.78], "SG": [1.35, 103.82],
    "RU": [61.52, 105.32],   "CH": [46.82, 8.23],    "FI": [61.92, 25.75],
    "SE": [60.13, 18.64],    "HK": [22.30, 114.18],  "CN": [35.86, 104.20],
    "AT": [47.52, 14.55],    "BR": [-14.24, -51.93], "NO": [60.47, 8.47],
    "IT": [41.87, 12.57],    "ES": [40.46, -3.75],   "PL": [51.92, 19.15],
    "CZ": [49.82, 15.47],    "RO": [45.94, 24.97],   "IN": [20.59, 78.96],
    "KR": [35.91, 127.77],   "NZ": [-40.90, 174.89], "BE": [50.50, 4.47],
    "AR": [-38.42, -63.62],  "MX": [23.63, -102.55], "UA": [48.38, 31.17],
    "ZA": [-30.56, 22.94],   "TR": [38.96, 35.24],   "TW": [23.70, 121.00],
    "IL": [31.05, 34.85],    "IR": [32.43, 53.69],   "ID": [-0.79, 113.92],
    "PT": [39.40, -8.22],    "DK": [56.26, 9.50],    "HU": [47.16, 19.50],
}


# ---------------------------------------------------------------------------
# Internal fetchers
# ---------------------------------------------------------------------------

def _get(url: str) -> Optional[dict]:
    """GET → parsed JSON or None.  Never raises."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code == 429:
            log.warning("Bitnodes rate-limited (429) for %s — using stale cache", url)
            return None
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("Bitnodes fetch error %s: %s", url, exc)
        return None


def _classify_addr(addr: str) -> str:
    if ".onion" in addr:
        return "tor"
    if ".i2p" in addr:
        return "i2p"
    if addr.startswith("["):
        return "ipv6"
    return "ipv4"


def _norm_agent(raw_agent: str) -> str:
    """'/Satoshi:28.0.0/' → 'Bitcoin Core 28.0.0'"""
    m = re.search(r"Satoshi:([\d.]+)", raw_agent or "")
    if m:
        return f"Bitcoin Core {m.group(1)}"
    if not raw_agent or raw_agent == "/unknown/":
        return "Unknown"
    # Truncate and clean other agents
    clean = (raw_agent or "").strip("/").replace("/", " ").strip()
    return clean[:45] if clean else "Unknown"


# ---------------------------------------------------------------------------
# Step 1: Fetch snapshot list (fast, just counts + snapshot URL)
# ---------------------------------------------------------------------------

def _fetch_list() -> Optional[dict]:
    """
    Returns:
      {total: int, prev_total: int, timestamp: int, snapshot_url: str}
    or None on failure.
    """
    now = time.time()
    c = _raw["list"]
    if c["data"] and now < c["expires"]:
        return c["data"]

    raw = _get(f"{BITNODES_BASE}/snapshots/?limit=2")
    if not raw:
        return c["data"]  # return stale or None

    results = raw.get("results", [])
    if not results:
        return c["data"]

    r0 = results[0]
    r1 = results[1] if len(results) > 1 else {}

    parsed = {
        "total":        r0.get("total_nodes") or 0,
        "prev_total":   r1.get("total_nodes") or 0,
        "timestamp":    r0.get("timestamp"),
        "snapshot_url": r0.get("url", ""),
    }
    c["data"]    = parsed
    c["expires"] = now + _TTL_LIST
    return parsed


# ---------------------------------------------------------------------------
# Step 2: Fetch snapshot detail (slow, but cached 1h)
# Bitnodes snapshot detail URL contains the full {nodes: {addr: [info]}} blob.
# ---------------------------------------------------------------------------

def _fetch_detail(snapshot_url: str) -> Optional[dict]:
    """
    Fetch the full node-level detail from a snapshot URL.
    Returns parsed dict: {versions, countries, net} or None.
    """
    now = time.time()
    c = _raw["detail"]
    if c["data"] and now < c["expires"]:
        return c["data"]

    if not snapshot_url:
        return c["data"]

    raw = _get(snapshot_url)
    if not raw:
        return c["data"]

    nodes: dict = raw.get("nodes", {})
    if not nodes:
        log.info("Bitnodes snapshot has no node-level data at %s", snapshot_url)
        return c["data"]

    versions: dict[str, int] = {}
    countries: dict[str, int] = {}
    net: dict[str, int] = {"ipv4": 0, "ipv6": 0, "tor": 0, "i2p": 0}

    for addr, info in nodes.items():
        if not isinstance(info, list):
            continue
        # Network type
        n = _classify_addr(addr)
        net[n] = net.get(n, 0) + 1
        # Version agent (index 1)
        agent = info[1] if len(info) > 1 else ""
        label = _norm_agent(agent)
        versions[label] = versions.get(label, 0) + 1
        # Country (index 7)
        cc = (info[7] or "??") if len(info) > 7 else "??"
        countries[cc] = countries.get(cc, 0) + 1

    top_ver = sorted(versions.items(),  key=lambda x: x[1], reverse=True)[:15]
    top_cc  = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:15]

    parsed = {"versions": top_ver, "countries": top_cc, "net": net}
    c["data"]    = parsed
    c["expires"] = now + _TTL_DETAIL
    return parsed


# ---------------------------------------------------------------------------
# Step 3: History
# ---------------------------------------------------------------------------

def _fetch_history() -> list:
    now = time.time()
    c = _raw["history"]
    if c["data"] and now < c["expires"]:
        return c["data"]

    # 100 snapshots ≈ 200 days at ~2h interval
    raw = _get(f"{BITNODES_BASE}/snapshots/?limit=100")
    if not raw:
        return c["data"] or []

    pts = []
    for snap in reversed(raw.get("results", [])):  # oldest → newest
        ts  = snap.get("timestamp")
        cnt = snap.get("total_nodes")
        if ts and cnt:
            pts.append({"ts": ts, "count": cnt})

    c["data"]    = pts
    c["expires"] = now + _TTL_HISTORY
    return pts


# ---------------------------------------------------------------------------
# Health Score
# ---------------------------------------------------------------------------

def _health_score(total: int, delta: int, detail: Optional[dict]) -> dict:
    # 1. Node level (15 pts)
    node_pts = (15 if total >= 16000 else 12 if total >= 13000
                else 8 if total >= 10000 else 4 if total >= 7000 else 0)

    # 2. Growth (20 pts)
    growth_pts = (20 if delta > 200 else 15 if delta > 0
                  else 10 if delta > -100 else 5 if delta > -500 else 0)

    # 3. Version currency (25 pts)
    ver_pts = 2
    currency_pct = 0.0
    if detail and detail.get("versions") and total:
        current = sum(c for v, c in detail["versions"]
                      if "Core 28." in v or "Core 27." in v or "Core 26." in v)
        currency_pct = current / total * 100
        ver_pts = (25 if currency_pct >= 60 else 18 if currency_pct >= 40
                   else 12 if currency_pct >= 20 else 6 if currency_pct >= 10 else 2)

    # 4. Geo diversity (20 pts)
    geo_pts = 10  # default moderate
    top_cc_pct = 0.0
    if detail and detail.get("countries") and total:
        top_cc_pct = detail["countries"][0][1] / total * 100
        geo_pts = (20 if top_cc_pct < 20 else 17 if top_cc_pct < 25
                   else 12 if top_cc_pct < 35 else 6 if top_cc_pct < 50 else 2)

    # 5. Privacy (10 pts)
    priv_pts = 3
    if detail and detail.get("net") and total:
        priv = detail["net"].get("tor", 0) + detail["net"].get("i2p", 0)
        priv_pct = priv / total * 100
        priv_pts = (10 if priv_pct >= 15 else 7 if priv_pct >= 8
                    else 5 if priv_pct >= 4 else 3 if priv_pct >= 1 else 1)

    # 6. Freshness (10 pts)
    fresh_pts = 10  # we just fetched it

    score = min(100, max(0, node_pts + growth_pts + ver_pts + geo_pts + priv_pts + fresh_pts))

    if score >= 75:
        label, colour = "STRONG", "#22c55e"
    elif score >= 45:
        label, colour = "MODERATE", "#f59e0b"
    else:
        label, colour = "WEAK", "#dc2626"

    # One-sentence reason
    if score >= 75:
        reason = f"Network running strong with {total:,} reachable nodes and healthy decentralisation."
    elif geo_pts < 10:
        reason = f"Geographic concentration: top country holds {top_cc_pct:.0f}% of reachable nodes."
    elif ver_pts < 10:
        reason = f"Version diversity gap: only {currency_pct:.0f}% of nodes on current major release."
    elif node_pts < 8:
        reason = f"Node count below typical level at {total:,} reachable nodes."
    elif detail is None:
        reason = f"Network stable with {total:,} reachable nodes. Detailed breakdown loading."
    else:
        reason = f"Network stable — {total:,} reachable nodes with moderate geographic spread."

    return {
        "score":  score,
        "label":  label,
        "colour": colour,
        "reason": reason,
        "components": {
            "node_level":       node_pts,
            "growth_trend":     growth_pts,
            "version_currency": ver_pts,
            "geo_diversity":    geo_pts,
            "privacy_nodes":    priv_pts,
            "data_freshness":   fresh_pts,
        },
    }


# ---------------------------------------------------------------------------
# Page route
# ---------------------------------------------------------------------------

@node_watch_bp.route("/node-watch")
def node_watch_page():
    return render_template("node_watch.html")


# ---------------------------------------------------------------------------
# API — summary
# ---------------------------------------------------------------------------

@node_watch_bp.route("/api/nodes/summary")
def api_nodes_summary():
    """
    Reachable count, IPv4/IPv6/Tor/I2P, 24h delta, Network Health Score.
    Cache: 5 min.
    """
    try:
        lst = _fetch_list()
        if not lst:
            stale = _raw["list"].get("data") or {}
            return jsonify({**stale, "stale": True, "error": "Bitnodes unavailable"}), 200

        total      = lst["total"]
        prev_total = lst["prev_total"]
        delta      = total - prev_total if prev_total else 0
        ts         = lst["timestamp"]

        # Try to get network-type breakdown from detail (may be None if rate-limited)
        detail = None
        snap_url = lst.get("snapshot_url")
        if snap_url:
            detail = _fetch_detail(snap_url)

        net = detail.get("net", {}) if detail else {}
        health = _health_score(total, delta, detail)

        data = {
            "reachable":    total,
            "ipv4":         net.get("ipv4", 0),
            "ipv6":         net.get("ipv6", 0),
            "tor":          net.get("tor",  0),
            "i2p":          net.get("i2p",  0),
            "timestamp":    ts,
            "delta_24h":    delta,
            "health":       health,
            "stale":        False,
            "detail_ready": detail is not None,
        }
    except Exception as exc:
        log.exception("api_nodes_summary error: %s", exc)
        data = {"error": str(exc), "stale": True, "reachable": 0, "delta_24h": 0}

    resp = make_response(jsonify(data))
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


# ---------------------------------------------------------------------------
# API — countries
# ---------------------------------------------------------------------------

@node_watch_bp.route("/api/nodes/countries")
def api_nodes_countries():
    """Top 15 countries by node count. Cache: 1 h."""
    try:
        lst    = _fetch_list()
        detail = None
        if lst and lst.get("snapshot_url"):
            detail = _fetch_detail(lst["snapshot_url"])

        total = (lst["total"] if lst else 0) or 1

        if not detail or not detail.get("countries"):
            stale = _raw["detail"].get("data") or {}
            return jsonify({
                "countries": [], "total": total,
                "stale": True,
                "note": "Country breakdown not yet available — Bitnodes rate-limit or loading."
            }), 200

        rows = []
        for cc, cnt in detail["countries"]:
            coords = CC_COORDS.get(cc)
            rows.append({
                "cc":   cc,
                "name": _CC_NAMES.get(cc, cc),
                "count": cnt,
                "pct":  round(cnt / total * 100, 1),
                "lat":  coords[0] if coords else None,
                "lng":  coords[1] if coords else None,
            })

        data = {"countries": rows, "total": total, "stale": False}
    except Exception as exc:
        log.exception("api_nodes_countries error: %s", exc)
        data = {"error": str(exc), "stale": True, "countries": []}

    resp = make_response(jsonify(data))
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


# ---------------------------------------------------------------------------
# API — versions
# ---------------------------------------------------------------------------

@node_watch_bp.route("/api/nodes/versions")
def api_nodes_versions():
    """Version distribution. Cache: 1 h."""
    try:
        lst    = _fetch_list()
        detail = None
        if lst and lst.get("snapshot_url"):
            detail = _fetch_detail(lst["snapshot_url"])

        total = (lst["total"] if lst else 0) or 1

        if not detail or not detail.get("versions"):
            return jsonify({
                "versions": [], "total": total,
                "stale": True,
                "note": "Version breakdown not yet available — Bitnodes rate-limit or loading."
            }), 200

        rows = []
        for ver, cnt in detail["versions"]:
            rows.append({
                "version": ver,
                "count":   cnt,
                "pct":     round(cnt / total * 100, 1),
                "current": ("28." in ver or "27." in ver or "26." in ver),
            })

        data = {"versions": rows, "total": total, "stale": False}
    except Exception as exc:
        log.exception("api_nodes_versions error: %s", exc)
        data = {"error": str(exc), "stale": True, "versions": []}

    resp = make_response(jsonify(data))
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


# ---------------------------------------------------------------------------
# API — history
# ---------------------------------------------------------------------------

@node_watch_bp.route("/api/nodes/history")
def api_nodes_history():
    """Node count history (~200 days). Cache: 24 h."""
    try:
        pts = _fetch_history()
        data = {"history": pts, "stale": not pts}
    except Exception as exc:
        log.exception("api_nodes_history error: %s", exc)
        data = {"error": str(exc), "stale": True, "history": []}

    resp = make_response(jsonify(data))
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp
