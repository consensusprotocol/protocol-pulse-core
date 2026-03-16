#!/usr/bin/env python3
"""render_chart_assets.py — Render matplotlib charts as PNGs for Today Intelligence overlay.

Brand-compliant: #0A0A0F bg, #FF3333 red, #F8C15C gold, #F4F5F8 white, JetBrains Mono where available.
Output: cache/charts/{price,hashrate,dominance}.png at 1520x460 (hero chart panel size).

Usage:
    from render_chart_assets import render_all_charts
    paths = render_all_charts(data)  # data from fetch_intelligence_data
"""

import logging
import os
import time
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [chart_render] %(levelname)s %(message)s")
log = logging.getLogger("chart_render")

BASE = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(BASE, "cache", "charts")

# Brand colors (hex for matplotlib)
BG_COLOR = "#0A0A0F"
PANEL_COLOR = "#080A0C"
RED = "#FF3333"
RED_DIM = "#661414"
GOLD = "#F8C15C"
WHITE = "#F4F5F8"
MUTED = "#888888"
GREEN = "#6EE7B7"
CORAL = "#FF8BA0"
CYAN = "#5DE4FF"

# Chart dimensions match hero panel: 1520x460 px at 100 DPI → 15.2 x 4.6 inches
CHART_W, CHART_H = 15.2, 4.6
CHART_DPI = 100

# Font setup — use DejaVu Sans Mono (pipeline standard) if available
FONT_FAMILY = "DejaVu Sans Mono"


def _setup_matplotlib():
    """Configure matplotlib for headless rendering with brand styling."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": GOLD,
        "text.color": WHITE,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "grid.color": "#1F1F1F",
        "grid.alpha": 0.5,
        "font.family": "monospace",
        "font.size": 12,
    })
    return plt


def render_price_chart(price_history: list, output_path: str) -> str:
    """Render BTC price line chart (14-day). Red line, gold fill, grid."""
    plt = _setup_matplotlib()

    if not price_history or len(price_history) < 2:
        log.warning("Insufficient price data (%d points), generating placeholder", len(price_history))
        return _render_placeholder(plt, "BTC PRICE — NO DATA", output_path)

    timestamps = [datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc) for p in price_history]
    prices = [p[1] for p in price_history]

    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)

    # Price line
    ax.plot(timestamps, prices, color=RED, linewidth=2.5, zorder=3)
    # Fill below
    ax.fill_between(timestamps, prices, min(prices) * 0.995, color=RED_DIM, alpha=0.3, zorder=2)

    # Grid
    ax.grid(True, axis="y", linewidth=0.5)
    ax.grid(True, axis="x", linewidth=0.3, alpha=0.3)

    # Labels
    ax.set_title("BTC / USD — 14 DAY", color=GOLD, fontsize=16, fontweight="bold", loc="left", pad=12)
    ax.set_ylabel("USD", fontsize=11)

    # Format y-axis as currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    # Format x-axis as dates
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    fig.autofmt_xdate(rotation=0)

    # Current price annotation
    if prices:
        latest = prices[-1]
        ax.annotate(f"${latest:,.0f}", xy=(timestamps[-1], latest),
                    fontsize=14, fontweight="bold", color=GOLD,
                    xytext=(10, 10), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor=BG_COLOR, edgecolor=GOLD, alpha=0.9))

    # 14d change badge
    if len(prices) >= 2:
        change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100
        badge_color = GREEN if change_pct >= 0 else CORAL
        sign = "+" if change_pct >= 0 else ""
        ax.text(0.98, 0.95, f"{sign}{change_pct:.1f}%", transform=ax.transAxes,
                fontsize=14, fontweight="bold", color=badge_color,
                ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=BG_COLOR, edgecolor=badge_color, alpha=0.8))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout(pad=1.0)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    log.info("Price chart saved: %s (%d points)", output_path, len(prices))
    return output_path


def render_hashrate_chart(hashrate_history: list, output_path: str) -> str:
    """Render hashrate bar chart (14-day). Red bars, gold accent."""
    plt = _setup_matplotlib()

    if not hashrate_history or len(hashrate_history) < 2:
        log.warning("Insufficient hashrate data, generating placeholder")
        return _render_placeholder(plt, "HASHRATE — NO DATA", output_path)

    # Downsample to daily averages (API returns per-block data — thousands of points)
    from collections import defaultdict
    daily_buckets = defaultdict(list)
    for h in hashrate_history:
        day = datetime.fromtimestamp(h.get("timestamp", 0), tz=timezone.utc).date()
        daily_buckets[day].append(h.get("avgHashrate", 0) / 1e18)
    sorted_days = sorted(daily_buckets.keys())[-14:]  # last 14 days
    timestamps = [datetime(d.year, d.month, d.day, tzinfo=timezone.utc) for d in sorted_days]
    hashrates_eh = [sum(daily_buckets[d]) / len(daily_buckets[d]) for d in sorted_days]

    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)

    # Bar chart
    bar_colors = [RED if i < len(hashrates_eh) - 1 else GOLD for i in range(len(hashrates_eh))]
    bars = ax.bar(timestamps, hashrates_eh, width=0.7, color=bar_colors, alpha=0.85, zorder=3,
                  edgecolor=RED_DIM, linewidth=0.5)

    # Trend line
    if len(hashrates_eh) >= 3:
        ax.plot(timestamps, hashrates_eh, color=GOLD, linewidth=1.5, alpha=0.6, zorder=4, linestyle="--")

    ax.grid(True, axis="y", linewidth=0.5)

    ax.set_title("NETWORK HASHRATE — EH/s", color=GOLD, fontsize=16, fontweight="bold", loc="left", pad=12)
    ax.set_ylabel("EH/s", fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    fig.autofmt_xdate(rotation=0)

    # Latest value badge
    if hashrates_eh:
        latest = hashrates_eh[-1]
        ax.text(0.98, 0.95, f"{latest:,.0f} EH/s", transform=ax.transAxes,
                fontsize=14, fontweight="bold", color=GOLD,
                ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3", facecolor=BG_COLOR, edgecolor=GOLD, alpha=0.9))

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout(pad=1.0)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    log.info("Hashrate chart saved: %s (%d points)", output_path, len(hashrates_eh))
    return output_path


def render_dominance_chart(dominance_data: dict, output_path: str) -> str:
    """Render BTC dominance donut chart. Red/gold palette."""
    plt = _setup_matplotlib()

    btc_dom = dominance_data.get("btc_dominance", 61.0)
    eth_dom = dominance_data.get("eth_dominance", 17.0)
    other_dom = max(0, 100 - btc_dom - eth_dom)

    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)

    sizes = [btc_dom, eth_dom, other_dom]
    labels = [f"BTC {btc_dom:.1f}%", f"ETH {eth_dom:.1f}%", f"OTHER {other_dom:.1f}%"]
    colors = [RED, MUTED, "#2A2A2A"]
    explode = (0.03, 0, 0)

    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct="%1.1f%%", startangle=90, pctdistance=0.75,
        wedgeprops=dict(width=0.4, edgecolor=BG_COLOR, linewidth=2),
        textprops=dict(color=WHITE, fontsize=12),
    )
    for at in autotexts:
        at.set_color(WHITE)
        at.set_fontsize(11)
        at.set_fontweight("bold")

    # Center text
    ax.text(0, 0, f"{btc_dom:.1f}%", ha="center", va="center",
            fontsize=28, fontweight="bold", color=GOLD)
    ax.text(0, -0.15, "BTC DOM", ha="center", va="center",
            fontsize=11, color=MUTED)

    ax.set_title("MARKET DOMINANCE", color=GOLD, fontsize=16, fontweight="bold", pad=20)

    plt.tight_layout(pad=1.0)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    log.info("Dominance chart saved: %s (BTC %.1f%%)", output_path, btc_dom)
    return output_path


def _render_placeholder(plt, title: str, output_path: str) -> str:
    """Render a branded placeholder chart when data is unavailable."""
    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)
    ax.text(0.5, 0.5, title, ha="center", va="center", fontsize=24, color=MUTED, fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    return output_path


def render_all_charts(data: dict = None) -> dict:
    """Render all 3 charts from intelligence data. Returns {chart_name: png_path}.

    If data is None, calls load_or_refresh() from fetch_intelligence_data.
    """
    if data is None:
        from fetch_intelligence_data import load_or_refresh
        data = load_or_refresh()

    os.makedirs(CHART_DIR, exist_ok=True)

    paths = {}
    paths["price"] = render_price_chart(
        data.get("price_history", []),
        os.path.join(CHART_DIR, "price.png"),
    )
    paths["hashrate"] = render_hashrate_chart(
        data.get("hashrate_history", []),
        os.path.join(CHART_DIR, "hashrate.png"),
    )
    paths["dominance"] = render_dominance_chart(
        data.get("dominance", {}),
        os.path.join(CHART_DIR, "dominance.png"),
    )

    log.info("All charts rendered: %s", list(paths.keys()))
    return paths


if __name__ == "__main__":
    from fetch_intelligence_data import fetch_all
    data = fetch_all()
    paths = render_all_charts(data)
    for name, path in paths.items():
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {name}: {path} ({size // 1024}KB)")
