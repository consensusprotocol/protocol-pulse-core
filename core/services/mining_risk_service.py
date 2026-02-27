"""
Mining Risk by Geography — real-time risk factors for deployment by location.
Used by /mining-risk and /api/mining-risk.

This version reads from core/config/mining_locations.json, which contains
18+ detailed locations with factor scores. Higher factor scores mean
"better" fundamentals; we invert them into risk scores (0–100, higher = riskier).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """Load mining_locations.json from core/config."""
    try:
        base = Path(__file__).resolve().parents[1]
        cfg_path = base / "config" / "mining_locations.json"
        if not cfg_path.exists():
            logger.warning("Mining risk config missing at %s", cfg_path)
            return {}
        with cfg_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # pragma: no cover
        logger.error("Failed to load mining risk config: %s", e)
        return {}


def _risk_from_scores(category_scores: Dict[str, float], factor_weights: Dict[str, float]) -> float:
    """
    Convert category factor scores (0–100, higher=better) into a single
    risk value (0–100, higher=riskier) using weighted average and inversion.
    """
    if not category_scores:
        return 50.0

    total = 0.0
    weight_sum = 0.0
    for k, v in category_scores.items():
        w = factor_weights.get(k, 0.0)
        if w <= 0:
            continue
        total += float(v) * w
        weight_sum += w

    if weight_sum <= 0:
        score = sum(category_scores.values()) / max(len(category_scores), 1)
    else:
        score = total / weight_sum

    # invert: high score (good) → low risk
    return max(0.0, min(100.0, 100.0 - score))


def _composite_risk(
    political_risk: float,
    economic_risk: float,
    operational_risk: float,
    weights: Dict[str, float],
) -> int:
    return round(
        (weights.get("political", 0.3) * political_risk)
        + (weights.get("economic", 0.35) * economic_risk)
        + (weights.get("operational", 0.35) * operational_risk)
    )


def get_regions_with_risk() -> List[Dict[str, Any]]:
    """
    Return all locations with composite risk score and labels.

    Output schema matches the original UI expectations:
    - code, name, region
    - regulatory_risk (political), energy_cost_risk (economic), stability_risk (operational)
    - composite_risk, risk_label, note
    """
    cfg = _load_config()
    locations = cfg.get("locations") or []
    risk_weights = cfg.get("risk_weights") or {"political": 0.30, "economic": 0.35, "operational": 0.35}
    factor_weights = cfg.get("factor_weights") or {}

    out: List[Dict[str, Any]] = []

    for loc in locations:
        scores = loc.get("scores") or {}
        political_scores = scores.get("political") or {}
        economic_scores = scores.get("economic") or {}
        operational_scores = scores.get("operational") or {}

        pol_w = factor_weights.get("political") or {}
        eco_w = factor_weights.get("economic") or {}
        op_w = factor_weights.get("operational") or {}

        political_risk = _risk_from_scores(political_scores, pol_w)
        economic_risk = _risk_from_scores(economic_scores, eco_w)
        operational_risk = _risk_from_scores(operational_scores, op_w)

        composite = _composite_risk(
            political_risk,
            economic_risk,
            operational_risk,
            risk_weights,
        )

        out.append(
            {
                "code": loc.get("id"),
                "name": loc.get("name"),
                "region": loc.get("region"),
                "regulatory_risk": round(political_risk),
                "energy_cost_risk": round(economic_risk),
                "stability_risk": round(operational_risk),
                "composite_risk": composite,
                "risk_label": _risk_label(composite),
                "hashrate_share_est": (loc.get("real_time_data") or {}).get("current_hashrate_share", 0),
                "note": loc.get("notes", ""),
            }
        )

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
