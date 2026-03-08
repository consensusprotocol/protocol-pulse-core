#!/usr/bin/env python3
"""chart_capture.py — TradingView chart screenshot capture.
Uses playwright (headless) to capture clean chart images.
"""
import asyncio
import os
import time
from pathlib import Path

CHART_CACHE = os.path.join(os.path.dirname(__file__), "assets", "charts")
os.makedirs(CHART_CACHE, exist_ok=True)

CHARTS = {
    "btc_usd_1d": "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT&interval=D&theme=dark",
    "btc_usd_4h": "https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT&interval=240&theme=dark",
    "btc_dominance": "https://www.tradingview.com/chart/?symbol=BTC.D&interval=D&theme=dark",
    "total_mcap": "https://www.tradingview.com/chart/?symbol=TOTAL&interval=D&theme=dark",
}


async def capture_chart(chart_key: str, width=1920, height=1080) -> str:
    """Capture a TradingView chart and return path to PNG."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        os.system("pip install playwright --break-system-packages -q && playwright install chromium --with-deps")
        from playwright.async_api import async_playwright

    url = CHARTS.get(chart_key, CHARTS["btc_usd_1d"])
    out_path = os.path.join(CHART_CACHE, f"{chart_key}_{int(time.time())}.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-gpu", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page(viewport={"width": width, "height": height})

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(4000)

        # Hide UI chrome — we want just the chart
        await page.evaluate("document.querySelectorAll('.tv-header, .tv-main-panel__toolbar, .chart-gui-wrapper .toolbar-top, .chart-controls-bar').forEach(e => { if (e) e.style.display = 'none'; });")
        await page.wait_for_timeout(500)

        await page.screenshot(path=out_path, full_page=False)
        await browser.close()

    return out_path


def get_chart(chart_key: str = "btc_usd_1d") -> str:
    """Synchronous wrapper. Returns path to chart PNG, cached up to 10 min."""
    # Check cache first (valid for 10 minutes)
    for f in sorted(Path(CHART_CACHE).glob(f"{chart_key}_*.png"), reverse=True):
        try:
            age = time.time() - int(f.stem.split("_")[-1])
            if age < 600:
                return str(f)
        except (ValueError, IndexError):
            continue
    # Capture fresh
    try:
        return asyncio.run(capture_chart(chart_key))
    except Exception as e:
        print(f"  [chart] TradingView capture failed: {e}")
        return ""


if __name__ == "__main__":
    path = get_chart("btc_usd_1d")
    print(f"Chart captured: {path}")
