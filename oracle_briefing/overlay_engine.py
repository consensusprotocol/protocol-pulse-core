#!/usr/bin/env python3
"""Overlay Engine — generates data visualization PNGs for Oracle Briefing.

All overlays are 1920x1080, dark theme, designed for right-side compositing (60% width).
"""
import os, sys, json
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Consistent dark theme
DARK_BG = "#0A0A0A"
SURFACE = "#141414"
RED = "#CC0000"
RED_LIGHT = "#FF3333"
GREEN = "#00CC66"
WHITE = "#FFFFFF"
GRAY = "#666666"
GRID = "#1A1A1A"

FONT_MONO = "DejaVu Sans Mono"
FONT_SANS = "DejaVu Sans"

WIDTH, HEIGHT = 1920, 1080
DPI = 100


def _setup_fig(title: str = ""):
    """Create a consistently styled figure."""
    fig, ax = plt.subplots(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=WHITE, labelsize=14)
    ax.spines["bottom"].set_color(GRAY)
    ax.spines["left"].set_color(GRAY)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.15, color=GRID)
    if title:
        ax.set_title(title, color=WHITE, fontsize=22, fontweight="bold",
                      fontfamily=FONT_SANS, pad=20)
    return fig, ax


def price_chart(btc_7d: list, current_price: float, change_24h: float,
                output_dir: str = "overlays") -> str:
    """Generate 7-day BTC price chart with trend line."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "price_chart.png")

    if not btc_7d or len(btc_7d) < 2:
        print("[overlay] No 7d data for price chart, generating placeholder")
        return _placeholder(out_path, "PRICE DATA\nUNAVAILABLE")

    timestamps = [p[0] for p in btc_7d]
    prices = [p[1] for p in btc_7d]

    # Determine color based on trend
    color = GREEN if prices[-1] >= prices[0] else RED_LIGHT

    fig, ax = _setup_fig()

    # Fill under curve
    ax.fill_between(range(len(prices)), prices, min(prices) * 0.998,
                     alpha=0.15, color=color)
    ax.plot(prices, color=color, linewidth=3, solid_capstyle="round")

    # Current price annotation
    ax.annotate(
        f"${current_price:,.0f}",
        xy=(len(prices) - 1, prices[-1]),
        fontsize=36, fontweight="bold", color=WHITE,
        fontfamily=FONT_MONO,
        xytext=(20, 20), textcoords="offset points",
        arrowprops=dict(arrowstyle="->", color=color, lw=2),
    )

    # 24h change badge
    change_color = GREEN if change_24h >= 0 else RED_LIGHT
    change_str = f"{change_24h:+.1f}%"
    ax.text(
        0.02, 0.95, change_str, transform=ax.transAxes,
        fontsize=28, fontweight="bold", color=change_color,
        fontfamily=FONT_MONO, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=DARK_BG, edgecolor=change_color, alpha=0.8),
    )

    # X-axis: day labels
    n = len(prices)
    step = max(1, n // 7)
    tick_positions = list(range(0, n, step))
    day_labels = []
    for i in tick_positions:
        if i < len(timestamps):
            dt = datetime.fromtimestamp(timestamps[i] / 1000, tz=timezone.utc)
            day_labels.append(dt.strftime("%b %d"))
        else:
            day_labels.append("")
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(day_labels, color=GRAY, fontsize=12)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.set_ylabel("")

    # Title
    ax.set_title("BITCOIN — 7 DAY", color=WHITE, fontsize=24,
                  fontweight="bold", fontfamily=FONT_SANS, pad=20)

    # Branding
    fig.text(0.98, 0.02, "PROTOCOL PULSE", fontsize=10, color=GRAY,
             fontfamily=FONT_MONO, ha="right", alpha=0.5)

    plt.tight_layout(pad=2)
    fig.savefig(out_path, facecolor=DARK_BG, dpi=DPI)
    plt.close(fig)
    print(f"[overlay] Price chart: {out_path}")
    return out_path


def mempool_viz(mempool_data: dict, output_dir: str = "overlays") -> str:
    """Generate mempool fee histogram visualization."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "mempool_viz.png")

    fig, ax = _setup_fig("MEMPOOL STATUS")

    fees = mempool_data
    categories = ["Economy", "Hour", "30 Min", "Priority"]
    values = [
        fees.get("economy_fee", 0),
        fees.get("hour_fee", 0),
        fees.get("half_hour_fee", 0),
        fees.get("fastest_fee", 0),
    ]
    colors = [GREEN, "#FFB800", "#FF6600", RED_LIGHT]

    bars = ax.barh(categories, values, color=colors, height=0.6, edgecolor="none")

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
            f"{val} sat/vB", va="center", ha="left",
            fontsize=20, fontweight="bold", color=WHITE, fontfamily=FONT_MONO,
        )

    ax.set_xlabel("")
    ax.tick_params(axis="y", labelsize=18, colors=WHITE)
    ax.set_xlim(0, max(values) * 1.4 if max(values) > 0 else 20)

    # TX count badge
    tx_count = fees.get("tx_count", 0)
    vsize_mb = fees.get("vsize", 0) / 1_000_000
    ax.text(
        0.98, 0.95,
        f"{tx_count:,} TXs\n{vsize_mb:,.0f} MB",
        transform=ax.transAxes, fontsize=22, fontweight="bold",
        color=WHITE, fontfamily=FONT_MONO,
        verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.4", facecolor=DARK_BG, edgecolor=GRAY, alpha=0.8),
    )

    fig.text(0.98, 0.02, "PROTOCOL PULSE", fontsize=10, color=GRAY,
             fontfamily=FONT_MONO, ha="right", alpha=0.5)

    plt.tight_layout(pad=2)
    fig.savefig(out_path, facecolor=DARK_BG, dpi=DPI)
    plt.close(fig)
    print(f"[overlay] Mempool viz: {out_path}")
    return out_path


def hashrate_chart(hashrate_data: dict, output_dir: str = "overlays") -> str:
    """Generate hashrate / difficulty visualization."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "hashrate_chart.png")

    hr_eh = hashrate_data.get("hashrate_eh", 0)
    epochs = hashrate_data.get("difficulty_epochs", [])

    fig, ax = _setup_fig("NETWORK HASHRATE")

    if epochs and len(epochs) > 1:
        diffs = [e.get("difficulty", e.get("difficultyChange", 0)) for e in epochs[-10:]]
        x = list(range(len(diffs)))
        colors_list = [GREEN if d >= 0 else RED_LIGHT for d in diffs]
        ax.bar(x, diffs, color=colors_list, width=0.7, edgecolor="none")
        ax.set_ylabel("Difficulty Adjustment %", color=GRAY, fontsize=14)
        ax.axhline(y=0, color=GRAY, linewidth=1, alpha=0.5)
    else:
        # Just show the hashrate number prominently
        ax.text(
            0.5, 0.5, f"{hr_eh} EH/s",
            transform=ax.transAxes, fontsize=72, fontweight="bold",
            color=RED_LIGHT, fontfamily=FONT_MONO,
            ha="center", va="center",
        )
        ax.text(
            0.5, 0.3, "NETWORK HASHRATE",
            transform=ax.transAxes, fontsize=24,
            color=GRAY, fontfamily=FONT_SANS,
            ha="center", va="center",
        )
        ax.set_xticks([])
        ax.set_yticks([])

    # Hashrate badge
    ax.text(
        0.02, 0.95, f"{hr_eh} EH/s",
        transform=ax.transAxes, fontsize=28, fontweight="bold",
        color=WHITE, fontfamily=FONT_MONO, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.3", facecolor=DARK_BG, edgecolor=RED, alpha=0.8),
    )

    fig.text(0.98, 0.02, "PROTOCOL PULSE", fontsize=10, color=GRAY,
             fontfamily=FONT_MONO, ha="right", alpha=0.5)

    plt.tight_layout(pad=2)
    fig.savefig(out_path, facecolor=DARK_BG, dpi=DPI)
    plt.close(fig)
    print(f"[overlay] Hashrate chart: {out_path}")
    return out_path


def fng_gauge(fng_data: dict, output_dir: str = "overlays") -> str:
    """Generate Fear & Greed gauge visualization."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "fng_gauge.png")

    value = fng_data.get("value", 50)
    label = fng_data.get("label", "Neutral")

    fig = plt.figure(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    fig.patch.set_facecolor(DARK_BG)
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor(DARK_BG)

    # Semi-circle gauge
    theta = np.linspace(np.pi, 0, 100)
    r = np.ones(100)

    # Color gradient: red (fear) → yellow → green (greed)
    colors_arr = plt.cm.RdYlGn(np.linspace(0, 1, 100))
    for i in range(99):
        ax.fill_between([theta[i], theta[i + 1]], 0.6, 1.0,
                        color=colors_arr[i], alpha=0.7)

    # Needle
    needle_angle = np.pi - (value / 100) * np.pi
    ax.plot([needle_angle, needle_angle], [0, 0.95], color=WHITE, linewidth=4,
            solid_capstyle="round")
    ax.plot(needle_angle, 0.95, "o", color=WHITE, markersize=10)

    ax.set_ylim(0, 1.3)
    ax.set_xlim(0, np.pi)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines["polar"].set_visible(False)

    # Value text
    fig.text(0.5, 0.25, str(value), fontsize=80, fontweight="bold",
             color=WHITE, fontfamily=FONT_MONO, ha="center", va="center")
    fig.text(0.5, 0.12, label.upper(), fontsize=28, fontweight="bold",
             color=GRAY, fontfamily=FONT_SANS, ha="center", va="center")
    fig.text(0.5, 0.93, "FEAR & GREED INDEX", fontsize=24, fontweight="bold",
             color=WHITE, fontfamily=FONT_SANS, ha="center", va="center")
    fig.text(0.98, 0.02, "PROTOCOL PULSE", fontsize=10, color=GRAY,
             fontfamily=FONT_MONO, ha="right", alpha=0.5)

    fig.savefig(out_path, facecolor=DARK_BG, dpi=DPI)
    plt.close(fig)
    print(f"[overlay] FNG gauge: {out_path}")
    return out_path


def article_screenshot(url: str, output_dir: str = "overlays") -> str:
    """Take a Playwright screenshot of a Protocol Pulse article."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "article_screenshot.png")

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(url, timeout=15000, wait_until="networkidle")
            page.screenshot(path=out_path, full_page=False)
            browser.close()
        print(f"[overlay] Article screenshot: {out_path}")
        return out_path
    except Exception as e:
        print(f"[overlay] Screenshot error: {e}")
        return _placeholder(out_path, "ARTICLE\nSCREENSHOT\nUNAVAILABLE")


def _placeholder(out_path: str, text: str) -> str:
    """Generate a placeholder overlay with text."""
    fig, ax = plt.subplots(figsize=(WIDTH / DPI, HEIGHT / DPI), dpi=DPI)
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(SURFACE)
    ax.text(0.5, 0.5, text, transform=ax.transAxes, fontsize=36,
            color=GRAY, fontfamily=FONT_MONO, ha="center", va="center",
            linespacing=1.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(0.98, 0.02, "PROTOCOL PULSE", fontsize=10, color=GRAY,
             fontfamily=FONT_MONO, ha="right", alpha=0.5)
    plt.tight_layout()
    fig.savefig(out_path, facecolor=DARK_BG, dpi=DPI)
    plt.close(fig)
    return out_path


def generate_all_overlays(data: dict, output_dir: str = "overlays") -> dict:
    """Generate all overlay images from data and return paths."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    paths["price_chart"] = price_chart(
        data.get("btc_7d", []),
        data["btc"]["price"],
        data["btc"]["change_24h"],
        output_dir,
    )
    paths["mempool_viz"] = mempool_viz(data["mempool"], output_dir)
    paths["hashrate_chart"] = hashrate_chart(data["hashrate"], output_dir)
    paths["fng_gauge"] = fng_gauge(data["fng"], output_dir)

    # Article screenshot if we have articles
    articles = data.get("articles", [])
    if articles and articles[0].get("slug"):
        slug = articles[0]["slug"]
        url = f"https://protocolpulse.replit.app/article/{slug}"
        paths["article_screenshot"] = article_screenshot(url, output_dir)

    return paths


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from briefing_writer import SAMPLE_DATA, fetch_all_data

    test_mode = "--test" in sys.argv
    data = SAMPLE_DATA if test_mode else fetch_all_data()
    out = "overlays_test" if test_mode else "overlays"

    print(f"=== Overlay Engine ({'TEST' if test_mode else 'LIVE'}) ===\n")
    paths = generate_all_overlays(data, out)
    print(f"\nGenerated {len(paths)} overlays:")
    for name, path in paths.items():
        size = os.path.getsize(path) if os.path.exists(path) else 0
        print(f"  {name}: {path} ({size / 1024:.0f} KB)")
