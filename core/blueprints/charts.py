"""
SESSION 4 — CHARTS BLUEPRINT
Bloomberg terminal-grade Bitcoin intelligence charts.

New API endpoints (no conflict with routes.py):
  GET /api/charts/price?period=7d          — CoinGecko price history
  GET /api/charts/hashrate?period=1y       — mempool.space hashrate history
  GET /api/charts/difficulty?period=1y     — mempool.space difficulty history
  GET /api/charts/mvrv?period=1y           — CoinMetrics community MVRV
  GET /api/charts/realized-price?period=1y — CoinMetrics community realized price
  GET /api/charts/fg-history?period=1y     — alternative.me F&G history (365 pts)
  GET /api/charts/og-image?chart=price     — matplotlib server-side OG image

Existing routes.py endpoints preserved:
  /api/charts/price-history, /api/charts/hashrate-history,
  /api/charts/fear-greed, /api/charts/mempool-data, /api/charts/fee-history,
  /api/charts/pool-distribution, /api/charts/lightning, /api/charts/ai-explain,
  /api/charts/price-alert, /charts/embed/<chart_id>
"""

from flask import Blueprint, request, jsonify, Response
import requests as _req
import time as _time
import logging
import functools
from datetime import datetime, timezone

charts_bp = Blueprint("charts_bp", __name__)

_HEADERS = {
    "User-Agent": "ProtocolPulse/1.0 (+https://protocolpulse.io)",
    "Accept": "application/json",
}


# ── In-process TTL cache ───────────────────────────────────────────────────────

def _ttl_cache(seconds):
    """Simple in-process TTL cache decorator."""
    def decorator(fn):
        _store = {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = _time.monotonic()
            if key in _store:
                result, ts = _store[key]
                if now - ts < seconds:
                    return result
            result = fn(*args, **kwargs)
            _store[key] = (result, now)
            return result

        return wrapper
    return decorator


def _period_to_days(period):
    """Convert period string ('7d', '1m', '1y', 'all') → int days or 'max'."""
    mapping = {
        "1d": 1, "7d": 7, "1m": 30, "3m": 90,
        "6m": 180, "1y": 365, "all": "max",
    }
    return mapping.get(str(period).lower().strip(), 7)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Data Fetchers ──────────────────────────────────────────────────────────────

@_ttl_cache(300)
def _fetch_price_history(days):
    """Fetch BTC/USD price history from CoinGecko. Cache 5 min."""
    try:
        if days == "max":
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=max"
        else:
            interval = "daily" if int(days) >= 30 else "hourly"
            url = (
                f"https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
                f"?vs_currency=usd&days={days}&interval={interval}"
            )
        r = _req.get(url, timeout=12, headers=_HEADERS)
        r.raise_for_status()
        data = r.json()
        return data.get("prices", [])  # [[ts_ms, price], ...]
    except Exception as e:
        logging.warning("CoinGecko price history error: %s", e)
        return None


@_ttl_cache(600)
def _fetch_hashrate_history(period_days):
    """Fetch hashrate history from mempool.space. Cache 10 min."""
    try:
        d = period_days if period_days != "max" else 1095
        span = "3m" if int(d) <= 90 else ("6m" if int(d) <= 180 else ("1y" if int(d) <= 365 else "3y"))
        r = _req.get(f"https://mempool.space/api/v1/mining/hashrate/{span}", timeout=12, headers=_HEADERS)
        r.raise_for_status()
        raw = r.json()
        cutoff_ts = _time.time() - int(d) * 86400
        pts = [
            [h["timestamp"] * 1000, round(h["avgHashrate"] / 1e18, 2)]
            for h in raw.get("hashrates", [])
            if h.get("timestamp", 0) >= cutoff_ts
        ]
        return pts
    except Exception as e:
        logging.warning("Mempool hashrate error: %s", e)
        return None


@_ttl_cache(600)
def _fetch_difficulty_history(period_days):
    """Fetch difficulty adjustment history from mempool.space. Cache 10 min."""
    try:
        d = period_days if period_days != "max" else 1095
        span = "3m" if int(d) <= 90 else ("6m" if int(d) <= 180 else ("1y" if int(d) <= 365 else "3y"))
        r = _req.get(f"https://mempool.space/api/v1/mining/hashrate/{span}", timeout=12, headers=_HEADERS)
        r.raise_for_status()
        raw = r.json()
        cutoff_ts = _time.time() - int(d) * 86400
        pts = [
            [entry["time"] * 1000, round(entry["difficulty"] / 1e12, 4)]
            for entry in raw.get("difficulty", [])
            if entry.get("time", 0) >= cutoff_ts
        ]
        return pts
    except Exception as e:
        logging.warning("Mempool difficulty error: %s", e)
        return None


@_ttl_cache(3600)
def _fetch_coinmetrics(metric, limit):
    """Fetch from CoinMetrics community API (free, no key). Cache 1 hr."""
    try:
        url = (
            f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
            f"?assets=btc&metrics={metric}&frequency=1d"
            f"&limit_per_asset={limit}&page_size={limit}"
        )
        r = _req.get(url, timeout=15, headers=_HEADERS)
        r.raise_for_status()
        pts = []
        for row in r.json().get("data", []):
            try:
                ts = int(datetime.fromisoformat(
                    row["time"].rstrip("Z") + "+00:00"
                ).timestamp() * 1000)
                val = float(row.get(metric) or 0)
                if val > 0:
                    pts.append([ts, val])
            except Exception:
                pass
        return pts
    except Exception as e:
        logging.warning("CoinMetrics %s error: %s", metric, e)
        return None


@_ttl_cache(3600)
def _fetch_fg_history(limit):
    """Fetch Fear & Greed historical index from alternative.me. Cache 1 hr."""
    try:
        r = _req.get(
            f"https://api.alternative.me/fng/?limit={limit}&format=json",
            timeout=12, headers=_HEADERS
        )
        r.raise_for_status()
        pts = []
        for e in r.json().get("data", []):
            try:
                pts.append([int(e["timestamp"]) * 1000, int(e["value"])])
            except Exception:
                pass
        pts.sort(key=lambda x: x[0])  # ascending chronological
        return pts
    except Exception as e:
        logging.warning("Fear & Greed history error: %s", e)
        return None


# ── API Endpoints ──────────────────────────────────────────────────────────────

@charts_bp.route("/api/charts/price")
def api_charts_price():
    """BTC/USD price history from CoinGecko. Cached 5 min."""
    try:
        period = request.args.get("period", "7d")
        days = _period_to_days(period)
        pts = _fetch_price_history(days)
        if pts is None:
            return jsonify({"error": "upstream unavailable", "data": []}), 503
        return jsonify({
            "data": pts,
            "source": "CoinGecko",
            "unit": "USD",
            "cached_until": _now_iso(),
            "period": period,
        })
    except Exception as e:
        logging.error("api_charts_price error: %s", e)
        return jsonify({"error": "internal error", "data": []}), 500


@charts_bp.route("/api/charts/hashrate")
def api_charts_hashrate():
    """Bitcoin network hashrate history (EH/s) from mempool.space. Cached 10 min."""
    try:
        period = request.args.get("period", "1y")
        days = _period_to_days(period)
        pts = _fetch_hashrate_history(days)
        if pts is None:
            return jsonify({"error": "upstream unavailable", "data": []}), 503
        return jsonify({
            "data": pts,
            "source": "mempool.space",
            "unit": "EH/s",
            "period": period,
        })
    except Exception as e:
        logging.error("api_charts_hashrate error: %s", e)
        return jsonify({"error": "internal error", "data": []}), 500


@charts_bp.route("/api/charts/difficulty")
def api_charts_difficulty():
    """Bitcoin mining difficulty history (T) from mempool.space. Cached 10 min."""
    try:
        period = request.args.get("period", "1y")
        days = _period_to_days(period)
        pts = _fetch_difficulty_history(days)
        if pts is None:
            return jsonify({"error": "upstream unavailable", "data": []}), 503
        return jsonify({
            "data": pts,
            "source": "mempool.space",
            "unit": "T",
            "period": period,
        })
    except Exception as e:
        logging.error("api_charts_difficulty error: %s", e)
        return jsonify({"error": "internal error", "data": []}), 500


@charts_bp.route("/api/charts/mvrv")
def api_charts_mvrv():
    """MVRV ratio from CoinMetrics community API. Cached 1 hr."""
    try:
        period = request.args.get("period", "1y")
        days = _period_to_days(period)
        limit = days if isinstance(days, int) else 1095
        pts = _fetch_coinmetrics("CapMVRVCur", limit)
        if pts is None:
            return jsonify({"error": "upstream unavailable", "data": []}), 503
        return jsonify({
            "data": pts,
            "source": "CoinMetrics (community)",
            "unit": "ratio",
            "period": period,
        })
    except Exception as e:
        logging.error("api_charts_mvrv error: %s", e)
        return jsonify({"error": "internal error", "data": []}), 500


@charts_bp.route("/api/charts/realized-price")
def api_charts_realized_price():
    """Bitcoin realized price from CoinMetrics community API. Cached 1 hr."""
    try:
        period = request.args.get("period", "1y")
        days = _period_to_days(period)
        limit = days if isinstance(days, int) else 1095
        pts = _fetch_coinmetrics("PriceRealizedUSD", limit)
        if pts is None:
            return jsonify({"error": "upstream unavailable", "data": []}), 503
        return jsonify({
            "data": pts,
            "source": "CoinMetrics (community)",
            "unit": "USD",
            "period": period,
        })
    except Exception as e:
        logging.error("api_charts_realized_price error: %s", e)
        return jsonify({"error": "internal error", "data": []}), 500


@charts_bp.route("/api/charts/fg-history")
def api_charts_fg_history():
    """Fear & Greed index history from alternative.me. Cached 1 hr."""
    try:
        period = request.args.get("period", "1y")
        days = _period_to_days(period)
        limit = days if isinstance(days, int) else 365
        limit = min(limit, 365)
        pts = _fetch_fg_history(limit)
        if pts is None:
            return jsonify({"error": "upstream unavailable", "data": []}), 503
        return jsonify({
            "data": pts,
            "source": "alternative.me",
            "unit": "F&G 0-100",
            "period": period,
        })
    except Exception as e:
        logging.error("api_charts_fg_history error: %s", e)
        return jsonify({"error": "internal error", "data": []}), 500


@charts_bp.route("/api/charts/og-image")
def api_charts_og_image():
    """
    Generate OG image (PNG) of requested chart via matplotlib.
    Query params: chart=(price|hashrate|fear-greed), period=(7d|1m|1y|all)
    """
    try:
        chart = request.args.get("chart", "price")
        period = request.args.get("period", "7d")
        days = _period_to_days(period)

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.ticker as mticker
            import matplotlib.dates as mdates
            import io as _io
        except ImportError:
            logging.warning("matplotlib not available for OG image generation")
            return jsonify({"error": "matplotlib not available"}), 503

        # Fetch data based on chart type
        if chart == "price":
            raw = _fetch_price_history(days)
            line_color = "#F59E0B"
            title = f"BTC/USD — {period.upper()}"
            y_fmt = lambda v, _: f"${v:,.0f}"
        elif chart == "hashrate":
            raw = _fetch_hashrate_history(days if days != "max" else 365)
            line_color = "#5DE4FF"
            title = f"Bitcoin Hashrate — {period.upper()}"
            y_fmt = lambda v, _: f"{v:.0f} EH/s"
        elif chart == "fear-greed":
            limit = days if isinstance(days, int) else 365
            raw = _fetch_fg_history(min(limit, 365))
            line_color = "#89FFB8"
            title = f"Fear & Greed Index — {period.upper()}"
            y_fmt = lambda v, _: f"{v:.0f}"
        else:
            return jsonify({"error": "unsupported chart type"}), 400

        if not raw:
            return jsonify({"error": "no data available"}), 503

        xs = [datetime.fromtimestamp(p[0] / 1000) for p in raw]
        ys = [p[1] for p in raw]

        fig, ax = plt.subplots(figsize=(12, 6.3), facecolor="#080810")
        ax.set_facecolor("#080810")
        ax.plot(xs, ys, color=line_color, linewidth=2.5, solid_capstyle="round")
        ax.fill_between(xs, ys, alpha=0.2, color=line_color)
        ax.set_title(title, color="#FFFFFF", fontsize=18, fontweight="bold", pad=20)
        ax.tick_params(colors="#95A0BA", labelsize=9)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(y_fmt))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        for spine in ax.spines.values():
            spine.set_edgecolor("#1C1C2E")
        ax.grid(color="#1C1C2E", linewidth=0.5, alpha=0.8, linestyle="--")
        fig.text(0.98, 0.02, "protocolpulse.io", ha="right",
                 color="#5DE4FF", fontsize=9, alpha=0.7)
        fig.tight_layout()

        buf = _io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="#080810", edgecolor="none")
        plt.close(fig)
        buf.seek(0)

        return Response(buf.read(), mimetype="image/png", headers={
            "Cache-Control": "public, max-age=300",
            "Content-Disposition": f'inline; filename="btc-{chart}-{period}.png"',
        })
    except Exception as e:
        logging.error("api_charts_og_image error: %s", e)
        return jsonify({"error": "internal error"}), 500
