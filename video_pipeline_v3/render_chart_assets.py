#!/usr/bin/env python3
"""render_chart_assets.py — Render matplotlib charts as PNGs for Today Intelligence overlay.

All charts: 1520x460px, 96 DPI, transparent=True, bg #06070b, no axis spines.
Output: cache/charts/{price_chart,hashrate_chart,dominance_chart}.png

Usage:
    from render_chart_assets import render_all
    render_all(data)  # data from fetch_intelligence_data
"""

import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [chart_render] %(levelname)s %(message)s")
log = logging.getLogger("chart_render")

BASE = os.path.dirname(os.path.abspath(__file__))
CHART_DIR = os.path.join(BASE, "cache", "charts")

# Brand colors
BG_COLOR = "#06070b"
GOLD = "#f8c15c"
WHITE = "#f4f5f8"
GREEN = "#00ff9d"
CYAN = "#4af8f8"
DIM = "#444444"

# 1520x460 at 96 DPI
CHART_W = 1520 / 96
CHART_H = 460 / 96
CHART_DPI = 96


def _setup_matplotlib():
    """Configure matplotlib for headless rendering."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "text.color": WHITE,
        "xtick.color": DIM,
        "ytick.color": DIM,
        "font.family": "monospace",
        "font.size": 11,
    })
    return plt


def render_price_chart(data: dict) -> str:
    """Gold line + fill, 7d hourly price, latest price top-right white bold."""
    plt = _setup_matplotlib()
    import matplotlib.dates as mdates

    output_path = os.path.join(CHART_DIR, "price_chart.png")
    price_7d = data.get("price_7d", [])

    if not price_7d or len(price_7d) < 2:
        return _render_placeholder(plt, "BITCOIN PRICE — NO DATA", output_path)

    timestamps = [datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc) for p in price_7d]
    prices = [p[1] for p in price_7d]

    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)

    # Gold line + fill under
    ax.plot(timestamps, prices, color=GOLD, linewidth=2.0, zorder=3)
    ax.fill_between(timestamps, prices, min(prices) * 0.998, color=GOLD, alpha=0.15, zorder=2)

    # No axis spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Title top-left gold
    ax.set_title("BITCOIN PRICE 7 DAY", color=GOLD, fontsize=14, fontweight="bold", loc="left", pad=10)

    # Latest price top-right white bold
    latest_price = prices[-1]
    ax.text(0.98, 0.92, f"${latest_price:,.0f}", transform=ax.transAxes,
            fontsize=18, fontweight="bold", color=WHITE, ha="right", va="top")

    # Source bottom-right dim
    ax.text(0.99, 0.03, "COINGECKO", transform=ax.transAxes,
            fontsize=8, color=DIM, ha="right", va="bottom")

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.tick_params(axis="both", length=0)

    plt.tight_layout(pad=0.5)
    os.makedirs(CHART_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, transparent=True,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    log.info("Price chart saved: %s (%d points, $%s)", output_path, len(prices), f"{latest_price:,.0f}")
    return output_path


def render_hashrate_chart(data: dict) -> str:
    """Green area + line, hashrate 30d in EH/s, current EH/s top-right."""
    plt = _setup_matplotlib()
    import matplotlib.dates as mdates

    output_path = os.path.join(CHART_DIR, "hashrate_chart.png")
    hashrate_30d = data.get("hashrate_30d", [])

    if not hashrate_30d or len(hashrate_30d) < 2:
        return _render_placeholder(plt, "NETWORK HASHRATE — NO DATA", output_path)

    # Downsample to daily averages (API returns per-block data)
    daily_buckets = defaultdict(list)
    for h in hashrate_30d:
        day = datetime.fromtimestamp(h.get("timestamp", 0), tz=timezone.utc).date()
        daily_buckets[day].append(h.get("avgHashrate", 0) / 1e18)
    sorted_days = sorted(daily_buckets.keys())[-30:]
    timestamps = [datetime(d.year, d.month, d.day, tzinfo=timezone.utc) for d in sorted_days]
    hashrates_eh = [sum(daily_buckets[d]) / len(daily_buckets[d]) for d in sorted_days]

    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)

    # Green area + line
    ax.plot(timestamps, hashrates_eh, color=GREEN, linewidth=2.0, zorder=3)
    ax.fill_between(timestamps, hashrates_eh, min(hashrates_eh) * 0.998,
                    color=GREEN, alpha=0.12, zorder=2)

    # No axis spines
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Title top-left gold
    ax.set_title("NETWORK HASHRATE 30 DAY", color=GOLD, fontsize=14, fontweight="bold", loc="left", pad=10)

    # Current EH/s top-right white bold
    latest_hr = hashrates_eh[-1]
    ax.text(0.98, 0.92, f"{latest_hr:,.0f} EH/s", transform=ax.transAxes,
            fontsize=18, fontweight="bold", color=WHITE, ha="right", va="top")

    # Source bottom-right dim
    ax.text(0.99, 0.03, "MEMPOOL.SPACE", transform=ax.transAxes,
            fontsize=8, color=DIM, ha="right", va="bottom")

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
    ax.tick_params(axis="both", length=0)

    plt.tight_layout(pad=0.5)
    os.makedirs(CHART_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, transparent=True,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    log.info("Hashrate chart saved: %s (%d daily points, %s EH/s)", output_path, len(hashrates_eh), f"{latest_hr:,.0f}")
    return output_path


def render_dominance_chart(data: dict) -> str:
    """Horizontal progress bar, cyan fill to btc_dominance %, large centered number."""
    plt = _setup_matplotlib()

    output_path = os.path.join(CHART_DIR, "dominance_chart.png")
    btc_dom = data.get("btc_dominance", 0.0)

    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)

    # No axes at all
    ax.axis("off")

    # Title top-left cyan
    ax.text(0.01, 0.92, "BTC MARKET DOMINANCE", transform=ax.transAxes,
            fontsize=14, fontweight="bold", color=CYAN, ha="left", va="top")

    # Large centered number — 52px equivalent (fontsize in matplotlib points ≈ px * 0.75)
    ax.text(0.5, 0.55, f"{btc_dom:.1f}%", transform=ax.transAxes,
            fontsize=52, fontweight="bold", color=WHITE, ha="center", va="center")

    # Horizontal progress bar (full width, centered vertically)
    bar_y = 0.18
    bar_h = 0.12
    # Dark background bar (full width)
    from matplotlib.patches import FancyBboxPatch
    bg_bar = FancyBboxPatch((0.02, bar_y), 0.96, bar_h, transform=ax.transAxes,
                            boxstyle="round,pad=0.005", facecolor="#1a1a2e", edgecolor="none",
                            zorder=1)
    ax.add_patch(bg_bar)
    # Cyan fill bar (proportional to dominance)
    fill_w = 0.96 * (btc_dom / 100.0)
    fill_bar = FancyBboxPatch((0.02, bar_y), fill_w, bar_h, transform=ax.transAxes,
                              boxstyle="round,pad=0.005", facecolor=CYAN, edgecolor="none",
                              alpha=0.85, zorder=2)
    ax.add_patch(fill_bar)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    plt.tight_layout(pad=0.5)
    os.makedirs(CHART_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, transparent=True,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    log.info("Dominance chart saved: %s (BTC %.1f%%)", output_path, btc_dom)
    return output_path


def _render_placeholder(plt, title: str, output_path: str) -> str:
    """Branded placeholder when data is unavailable."""
    fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), dpi=CHART_DPI)
    ax.text(0.5, 0.5, title, ha="center", va="center", fontsize=20, color=DIM, fontweight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    os.makedirs(CHART_DIR, exist_ok=True)
    fig.savefig(output_path, dpi=CHART_DPI, facecolor=BG_COLOR, transparent=True,
                bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return output_path


def render_all(data: dict) -> None:
    """Render all 3 charts from intelligence data. Creates cache/charts/ dir."""
    os.makedirs(CHART_DIR, exist_ok=True)
    render_price_chart(data)
    render_hashrate_chart(data)
    render_dominance_chart(data)
    log.info("All 3 charts rendered to %s", CHART_DIR)


if __name__ == "__main__":
    from fetch_intelligence_data import fetch_all
    data = fetch_all()
    render_all(data)
    for name in ["price_chart.png", "hashrate_chart.png", "dominance_chart.png"]:
        path = os.path.join(CHART_DIR, name)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {name}: {size // 1024}KB")
