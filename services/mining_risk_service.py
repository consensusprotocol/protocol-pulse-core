"""
Mining Risk by Geography — real-time risk factors for deployment by location.
Used by /mining-risk and /api/mining-risk. Factors: regulatory, energy, stability, composite.
Data sources: public indices, hashrate distribution estimates, energy/cost proxies.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Risk scale: 0 (lowest risk) to 100 (highest risk). Composite = weighted average.
# Weights: regulatory 40%, energy_cost 30%, stability 30%.
# Based on public knowledge: regulatory clarity, energy affordability/reliability, political stability.
MINING_RISK_REGIONS = [
    {"code": "US", "name": "United States", "region": "North America",
     "regulatory_risk": 35, "energy_cost_risk": 25, "stability_risk": 20,
     "hashrate_share_est": 38, "note": "State-by-state variation; TX, KY, WY favorable."},
    {"code": "CN", "name": "China", "region": "Asia",
     "regulatory_risk": 95, "energy_cost_risk": 15, "stability_risk": 45,
     "hashrate_share_est": 15, "note": "Ban in 2021; off-the-books mining remains."},
    {"code": "KZ", "name": "Kazakhstan", "region": "Central Asia",
     "regulatory_risk": 55, "energy_cost_risk": 30, "stability_risk": 50,
     "hashrate_share_est": 13, "note": "Power shortages and regulatory pressure since 2022."},
    {"code": "CA", "name": "Canada", "region": "North America",
     "regulatory_risk": 30, "energy_cost_risk": 20, "stability_risk": 15,
     "hashrate_share_est": 6, "note": "Hydro-rich provinces; clear provincial frameworks."},
    {"code": "MX", "name": "Mexico", "region": "North America",
     "regulatory_risk": 50, "energy_cost_risk": 35, "stability_risk": 45,
     "hashrate_share_est": 1, "note": "Growing mining presence; regulatory clarity evolving; competitive power in some regions."},
    {"code": "RU", "name": "Russia", "region": "Europe",
     "regulatory_risk": 60, "energy_cost_risk": 15, "stability_risk": 70,
     "hashrate_share_est": 4, "note": "Uncertain legal status; cheap power in Siberia."},
    {"code": "MY", "name": "Malaysia", "region": "Southeast Asia",
     "regulatory_risk": 50, "energy_cost_risk": 35, "stability_risk": 35,
     "hashrate_share_est": 4, "note": "Mixed signals; some states mining-friendly."},
    {"code": "IR", "name": "Iran", "region": "Middle East",
     "regulatory_risk": 85, "energy_cost_risk": 10, "stability_risk": 80,
     "hashrate_share_est": 2, "note": "Sanctions and power curbs; high sovereign risk."},
    {"code": "NO", "name": "Norway", "region": "Europe",
     "regulatory_risk": 25, "energy_cost_risk": 40, "stability_risk": 10,
     "hashrate_share_est": 1, "note": "Clean hydro; high electricity cost."},
    {"code": "GB", "name": "United Kingdom", "region": "Europe",
     "regulatory_risk": 40, "energy_cost_risk": 65, "stability_risk": 18,
     "hashrate_share_est": 0, "note": "Regulated; expensive power."},
    {"code": "DE", "name": "Germany", "region": "Europe",
     "regulatory_risk": 45, "energy_cost_risk": 70, "stability_risk": 15,
     "hashrate_share_est": 0, "note": "High energy costs; strict climate rules."},
    {"code": "SG", "name": "Singapore", "region": "Southeast Asia",
     "regulatory_risk": 70, "energy_cost_risk": 80, "stability_risk": 12,
     "hashrate_share_est": 0, "note": "MAS restrictions; very high power cost."},
    {"code": "ET", "name": "Ethiopia", "region": "Africa",
     "regulatory_risk": 55, "energy_cost_risk": 20, "stability_risk": 55,
     "hashrate_share_est": 0, "note": "Cheap hydro; regulatory uncertainty."},
    {"code": "PY", "name": "Paraguay", "region": "South America",
     "regulatory_risk": 45, "energy_cost_risk": 15, "stability_risk": 45,
     "hashrate_share_est": 0, "note": "Itaipu surplus; growing mining interest."},
    {"code": "IS", "name": "Iceland", "region": "Europe",
     "regulatory_risk": 30, "energy_cost_risk": 35, "stability_risk": 8,
     "hashrate_share_est": 0, "note": "Geothermal; cold climate; stable."},
    {"code": "SE", "name": "Sweden", "region": "Europe",
     "regulatory_risk": 35, "energy_cost_risk": 45, "stability_risk": 10,
     "hashrate_share_est": 0, "note": "Nordic hydro; ESG scrutiny."},
]

# Weights for composite risk (0–100, higher = riskier)
WEIGHT_REGULATORY = 0.40
WEIGHT_ENERGY = 0.30
WEIGHT_STABILITY = 0.30


def _composite_risk(regulatory: int, energy: int, stability: int) -> int:
    return round(WEIGHT_REGULATORY * regulatory + WEIGHT_ENERGY * energy + WEIGHT_STABILITY * stability)


def get_regions_with_risk() -> List[Dict[str, Any]]:
    """Return all regions with composite risk score and labels."""
    out = []
    for r in MINING_RISK_REGIONS:
        composite = _composite_risk(
            r["regulatory_risk"],
            r["energy_cost_risk"],
            r["stability_risk"],
        )
        out.append({
            "code": r["code"],
            "name": r["name"],
            "region": r["region"],
            "regulatory_risk": r["regulatory_risk"],
            "energy_cost_risk": r["energy_cost_risk"],
            "stability_risk": r["stability_risk"],
            "composite_risk": composite,
            "risk_label": _risk_label(composite),
            "hashrate_share_est": r.get("hashrate_share_est", 0),
            "note": r.get("note", ""),
        })
    return sorted(out, key=lambda x: x["composite_risk"], reverse=True)


def _risk_label(score: int) -> str:
    if score >= 70:
        return "Very High"
    if score >= 55:
        return "High"
    if score >= 40:
        return "Medium"
    if score >= 25:
        return "Low"
    return "Very Low"


def get_live_network_metrics() -> Dict[str, Any]:
    """Fetch live hashrate and difficulty from mempool.space for real-time context."""
    import requests
    try:
        hashrate_res = requests.get(
            "https://mempool.space/api/v1/mining/hashrate/1m",
            timeout=8,
        )
        diff_res = requests.get(
            "https://mempool.space/api/v1/difficulty-adjustment",
            timeout=8,
        )
        hashrate_data = hashrate_res.json() if hashrate_res.ok else {}
        diff_data = diff_res.json() if diff_res.ok else {}
        current_hashrate = hashrate_data.get("currentHashrate") or 0
        # currentHashrate in H/s; convert to EH/s
        hashrate_eh = (current_hashrate / 1e18) if current_hashrate else 0
        # difficulty from hashrate endpoint (has currentDifficulty); fallback to diff endpoint
        difficulty = hashrate_data.get("currentDifficulty") or diff_data.get("currentDifficulty") or 0
        progress = diff_data.get("progressPercent") or 0
        return {
            "hashrate_eh": round(hashrate_eh, 2),
            "hashrate_raw": current_hashrate,
            "difficulty": difficulty,
            "difficulty_progress_percent": round(progress, 1),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.warning("Mining risk: failed to fetch network metrics: %s", e)
        return {
            "hashrate_eh": 0,
            "hashrate_raw": 0,
            "difficulty": 0,
            "difficulty_progress_percent": 0,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "error": str(e),
        }


def get_location_risk(location_id: str) -> Optional[Dict[str, Any]]:
    key = (location_id or "").strip().lower()
    if not key:
        return None
    for region in get_regions_with_risk():
        code = str(region.get("code") or "").lower()
        name = str(region.get("name") or "").lower().replace(" ", "_")
        rid = f"{code}_{name}".strip("_")
        if key in {code, rid, name}:
            return region
    if key == "us_texas":
        return next((r for r in get_regions_with_risk() if str(r.get("code") or "").upper() == "US"), None)
    return None


def compare_locations(location_ids: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for lid in location_ids or []:
        row = get_location_risk(lid)
        if row:
            out.append(row)
    return out


def get_external_risk_signals() -> Dict[str, Any]:
    """
    Best-effort external telemetry map.
    Falls back to mock/degraded fields when providers or keys are unavailable.
    """
    import requests

    signals: Dict[str, Any] = {"status": "ok", "sources": {}}
    try:
        # Public CBECI country map (Bitcoin mining share estimates)
        cbeci = requests.get("https://ccaf.io/cbeci/api/v1/data/country", timeout=12)
        signals["sources"]["cbeci"] = {"ok": cbeci.ok, "status_code": cbeci.status_code}
    except Exception as e:
        signals["sources"]["cbeci"] = {"ok": False, "error": str(e)}

    try:
        # GDACS public RSS as geopolitical alert proxy.
        gdacs = requests.get("https://www.gdacs.org/xml/rss.xml", timeout=12)
        signals["sources"]["gdacs"] = {"ok": gdacs.ok, "status_code": gdacs.status_code}
    except Exception as e:
        signals["sources"]["gdacs"] = {"ok": False, "error": str(e)}

    # EIA/World Bank APIs can require specific tokens or schemas; expose degraded mode explicitly.
    signals["sources"]["eia"] = {"ok": False, "mocked": True, "reason": "api key not configured"}
    signals["sources"]["world_bank"] = {"ok": False, "mocked": True, "reason": "api key not configured"}
    if any(not (src or {}).get("ok", False) for src in signals["sources"].values()):
        signals["status"] = "degraded"
    signals["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return signals


def snapshot_all() -> Dict[str, Any]:
    """
    Persist one risk snapshot row per location to `mining_snapshot`.
    """
    from app import db
    import models

    inserted = 0
    now = datetime.utcnow()
    for region in get_regions_with_risk():
        code = str(region.get("code") or "").lower()
        name = str(region.get("name") or "").lower().replace(" ", "_")
        rid = f"{code}_{name}".strip("_")
        row = models.MiningSnapshot(
            location_id=rid,
            location_name=region.get("name"),
            overall_score=float(region.get("composite_risk") or 0),
            political_score=float(region.get("regulatory_risk") or 0),
            economic_score=float(region.get("energy_cost_risk") or 0),
            operational_score=float(region.get("stability_risk") or 0),
            factors_json=str(region),
            captured_at=now,
        )
        db.session.add(row)
        inserted += 1
    db.session.commit()
    return {"success": True, "inserted": inserted, "captured_at": now.isoformat()}
