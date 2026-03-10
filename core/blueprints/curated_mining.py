"""
SESSION 18 — CURATED MINING LANDING PAGE
==========================================
Routes:
  GET  /curated-mining              → high-ticket conversion landing page
  GET  /api/mining/estimate         → interactive calculator backend

This is a standalone conversion page for Consensus Protocol LLC's white-glove
Bitcoin mining setup service. Does NOT modify /mining (Mining Intelligence Hub).
"""
import logging
from flask import Blueprint, render_template, request, jsonify

logger = logging.getLogger(__name__)

curated_mining_bp = Blueprint("curated_mining", __name__)


def _get_btc_price() -> float:
    """Fetch live BTC price. Falls back to 95000 on error."""
    try:
        import requests as _req
        r = _req.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=8,
        )
        if r.ok:
            return float(r.json()["bitcoin"]["usd"])
    except Exception as exc:
        logger.warning("curated_mining: BTC price fetch failed: %s", exc)
    return 95000.0


@curated_mining_bp.route("/curated-mining")
def curated_mining():
    """Curated Mining — white-glove Bitcoin mining setup landing page."""
    return render_template("curated_mining.html")


@curated_mining_bp.route("/api/mining/estimate")
def mining_estimate():
    """
    Interactive mining calculator API.
    GET /api/mining/estimate?budget=50000&power_cost=0.065
    Returns monthly BTC, monthly profit (USD), and estimated payback period.
    """
    try:
        budget = float(request.args.get("budget", 50000))
        power_cost = float(request.args.get("power_cost", 0.065))

        # Clamp inputs to sane ranges
        budget = max(10000.0, min(budget, 5_000_000.0))
        power_cost = max(0.01, min(power_cost, 0.30))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameters"}), 400

    btc_price = _get_btc_price()

    # Hardware assumptions: Antminer S21 Pro @ $8/TH
    price_per_th = 8.0
    hashrate_th = budget / price_per_th  # TH/s purchased
    efficiency_j_per_th = 15.0           # J/TH (S21 Pro)
    power_watts = hashrate_th * efficiency_j_per_th

    # Network constants (conservative estimates)
    network_hash_eh = 700.0   # EH/s
    block_reward = 3.125      # BTC (post-4th halving)
    blocks_per_day = 144

    # Mining math
    daily_btc = (hashrate_th / (network_hash_eh * 1e6)) * block_reward * blocks_per_day
    daily_power_cost_usd = (power_watts / 1000.0) * 24.0 * power_cost

    monthly_btc = daily_btc * 30
    monthly_revenue_usd = monthly_btc * btc_price
    monthly_power_usd = daily_power_cost_usd * 30
    monthly_profit_usd = monthly_revenue_usd - monthly_power_usd

    payback_months = None
    if monthly_profit_usd > 0:
        payback_months = round(budget / monthly_profit_usd, 1)

    return jsonify({
        "monthly_btc": round(monthly_btc, 6),
        "monthly_revenue_usd": round(monthly_revenue_usd, 2),
        "monthly_power_cost_usd": round(monthly_power_usd, 2),
        "monthly_profit_usd": round(monthly_profit_usd, 2),
        "payback_months": payback_months,
        "btc_price": btc_price,
        "hashrate_th": round(hashrate_th, 2),
        "power_watts": round(power_watts, 0),
        "disclaimer": "Estimates only. Based on current network difficulty and stated power cost. Not financial advice.",
    })
