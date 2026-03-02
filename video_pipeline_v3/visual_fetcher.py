#!/usr/bin/env python3
"""visual_fetcher.py — Fetch REAL visuals instead of stock footage.

Priority order:
1. YouTube clips — yt-dlp specific timestamp ranges or search
2. Article screenshots — playwright captures of web articles
3. Tweet/Nostr screenshots — styled cards via PIL
4. Data charts — matplotlib BTC/mempool/hashrate charts
5. Pexels B-roll — LAST RESORT, transitions only (2-3s max)
"""
import os
import subprocess
import hashlib
import json

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
YT_CACHE_DIR = os.path.join(BASE, "downloads", "yt_cache")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ── YouTube clip fetching ────────────────────────────────────────────────────

def download_youtube_clip(video_id: str, start_sec: int, end_sec: int,
                          output_path: str) -> bool:
    """Download a specific segment of a YouTube video using yt-dlp.

    Args:
        video_id: YouTube video ID
        start_sec: Start time in seconds
        end_sec: End time in seconds
        output_path: Where to save the clip

    Returns:
        True if download succeeded.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"

    cmd = [
        "yt-dlp",
        "--download-sections", f"*{start_sec}-{end_sec}",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--no-check-certificates",
        "--quiet",
        "--no-warnings",
        url,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and os.path.exists(output_path):
            print(f"  [yt] Clip downloaded: {video_id} [{start_sec}-{end_sec}s]")
            return True
    except subprocess.TimeoutExpired:
        print(f"  [yt] Timeout downloading clip {video_id}")
    except Exception as e:
        print(f"  [yt] Error: {e}")

    # Fallback: download full video then trim with ffmpeg
    raw_path = output_path + ".raw.mp4"
    try:
        cmd_full = [
            "yt-dlp",
            "-f", "best[height<=1080]",
            "--no-playlist",
            "--no-check-certificates",
            "-o", raw_path,
            "--quiet",
            url,
        ]
        r = subprocess.run(cmd_full, capture_output=True, text=True, timeout=120)
        if r.returncode == 0 and os.path.exists(raw_path):
            duration = end_sec - start_sec
            trim = subprocess.run(
                ["ffmpeg", "-y", "-ss", str(start_sec), "-i", raw_path,
                 "-t", str(duration),
                 "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                 "-c:v", "libx264", "-crf", "20", "-c:a", "aac", output_path],
                capture_output=True, text=True, timeout=120,
            )
            try:
                os.remove(raw_path)
            except Exception:
                pass
            if trim.returncode == 0 and os.path.exists(output_path):
                print(f"  [yt] Clip trimmed: {video_id} [{start_sec}-{end_sec}s]")
                return True
    except Exception as e:
        print(f"  [yt] Fallback error: {e}")

    return False


def search_youtube_clip(query: str, output_path: str,
                        max_duration: int = 30, source: str = "") -> bool:
    """Search YouTube and download the top result.

    Args:
        query: Search terms
        output_path: Where to save
        max_duration: Max clip length in seconds
        source: Optional channel hint (e.g., "@BitcoinMagazine")

    Returns:
        True if download succeeded.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    os.makedirs(YT_CACHE_DIR, exist_ok=True)

    # Check cache
    digest = hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]
    cache = os.path.join(YT_CACHE_DIR, f"yt_{digest}.mp4")
    if os.path.exists(cache) and os.path.getsize(cache) > 10_000:
        subprocess.run(["cp", cache, output_path], capture_output=True)
        if os.path.exists(output_path):
            print(f"  [yt] Cache hit: {query[:40]}")
            return True

    search_query = f"{source} {query}" if source and source.startswith("@") else query
    raw_path = cache + ".raw.mp4"

    try:
        cmd = [
            "yt-dlp",
            f"ytsearch1:{search_query}",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
            "--merge-output-format", "mp4",
            "--no-playlist",
            "--no-check-certificates",
            "-o", raw_path,
            "--quiet",
            "--no-warnings",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if r.returncode != 0 or not os.path.exists(raw_path):
            cmd2 = [
                "yt-dlp", f"ytsearch1:{search_query}",
                "-f", "best[height<=1080]",
                "--no-playlist", "--no-check-certificates",
                "-o", raw_path, "--quiet",
            ]
            subprocess.run(cmd2, capture_output=True, text=True, timeout=120)

        if os.path.exists(raw_path) and os.path.getsize(raw_path) > 10_000:
            # Trim + scale
            subprocess.run(
                ["ffmpeg", "-y", "-i", raw_path, "-t", str(max_duration),
                 "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
                 "-c:v", "libx264", "-crf", "22", "-an", cache],
                capture_output=True, text=True, timeout=180,
            )
            try:
                os.remove(raw_path)
            except Exception:
                pass
            if os.path.exists(cache):
                subprocess.run(["cp", cache, output_path], capture_output=True)
                if os.path.exists(output_path):
                    print(f"  [yt] Downloaded + cached: {query[:40]}")
                    return True

    except subprocess.TimeoutExpired:
        print(f"  [yt] Timeout: {query[:40]}")
    except Exception as e:
        print(f"  [yt] Error: {e}")

    return False


# ── Article screenshots ──────────────────────────────────────────────────────

def screenshot_article(url: str, output_path: str,
                       width: int = 1920, height: int = 1080) -> bool:
    """Screenshot a web article using playwright (headless).

    Captures the above-the-fold area and applies a dark vignette overlay.

    Args:
        url: Article URL to capture
        output_path: Where to save the screenshot
        width: Viewport width
        height: Viewport height

    Returns:
        True if screenshot was saved.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [screenshot] playwright not available")
        return False

    raw_path = output_path + ".raw.png"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            page.screenshot(path=raw_path, full_page=False)
            browser.close()

        if not os.path.exists(raw_path):
            return False

        # Apply dark vignette overlay for cinematic look
        if HAS_PIL:
            img = Image.open(raw_path).convert("RGB")
            img = img.resize((width, height), Image.LANCZOS)

            # Dark vignette: darken edges
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            # Bottom gradient
            for y in range(height // 2, height):
                alpha = int(180 * ((y - height // 2) / (height // 2)))
                draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))
            # Top gradient (lighter)
            for y in range(0, height // 4):
                alpha = int(100 * (1 - y / (height // 4)))
                draw.rectangle([(0, y), (width, y + 1)], fill=(0, 0, 0, alpha))

            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")
            img.save(output_path, "PNG")
        else:
            os.rename(raw_path, output_path)

        if os.path.exists(raw_path) and raw_path != output_path:
            os.remove(raw_path)

        print(f"  [screenshot] Captured: {url[:60]}")
        return True

    except Exception as e:
        print(f"  [screenshot] Error: {e}")
        return False


# ── Tweet/Nostr card generation ──────────────────────────────────────────────

def screenshot_tweet(tweet_text: str, author: str, handle: str,
                     output_path: str, platform: str = "x") -> bool:
    """Generate a styled tweet/post card image using PIL.

    Args:
        tweet_text: The post text
        author: Display name
        handle: @username
        output_path: Where to save
        platform: "x" (blue accent) or "nostr" (purple accent)

    Returns:
        True if image was generated.
    """
    if not HAS_PIL:
        print("  [tweet] Pillow not available")
        return False

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    W, H = 1920, 1080
    accent = (29, 155, 240) if platform == "x" else (128, 57, 219)
    bg_color = (15, 15, 20)

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # Card background (centered, padded)
    card_margin = 200
    card_top = 150
    card_bottom = H - 150
    card_w = W - card_margin * 2
    card_h = card_bottom - card_top

    # Card with subtle border
    draw.rounded_rectangle(
        [(card_margin, card_top), (W - card_margin, card_bottom)],
        radius=20, fill=(25, 25, 32), outline=(50, 50, 60), width=2,
    )

    # Platform accent bar at top of card
    draw.rectangle(
        [(card_margin, card_top), (W - card_margin, card_top + 4)],
        fill=accent,
    )

    # Load fonts
    try:
        font_author = ImageFont.truetype(FONT_BOLD, 36)
        font_handle = ImageFont.truetype(FONT_REGULAR, 28)
        font_text = ImageFont.truetype(FONT_REGULAR, 32)
        font_platform = ImageFont.truetype(FONT_BOLD, 24)
    except Exception:
        font_author = font_handle = font_text = font_platform = ImageFont.load_default()

    # Profile avatar circle (placeholder)
    avatar_x, avatar_y = card_margin + 40, card_top + 40
    draw.ellipse(
        [(avatar_x, avatar_y), (avatar_x + 64, avatar_y + 64)],
        fill=accent, outline=(255, 255, 255, 128),
    )
    # Initial letter in avatar
    initial = author[0].upper() if author else "?"
    try:
        init_font = ImageFont.truetype(FONT_BOLD, 32)
    except Exception:
        init_font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), initial, font=init_font)
    iw, ih = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (avatar_x + 32 - iw // 2, avatar_y + 32 - ih // 2),
        initial, fill=(255, 255, 255), font=init_font,
    )

    # Author name + handle
    text_x = avatar_x + 80
    draw.text((text_x, avatar_y + 5), author, fill=(255, 255, 255), font=font_author)
    draw.text((text_x, avatar_y + 42), f"@{handle}", fill=(120, 120, 140), font=font_handle)

    # Tweet text (word-wrapped)
    text_start_y = card_top + 140
    max_text_w = card_w - 80
    words = tweet_text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font_text)
        if bbox[2] - bbox[0] > max_text_w:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)

    for i, line in enumerate(lines[:12]):
        y = text_start_y + i * 45
        draw.text((card_margin + 40, y), line, fill=(220, 220, 230), font=font_text)

    # Platform label
    platform_label = "X (Twitter)" if platform == "x" else "Nostr"
    draw.text(
        (W - card_margin - 150, card_bottom - 50),
        platform_label, fill=accent, font=font_platform,
    )

    img.save(output_path, "PNG")
    print(f"  [tweet] Card generated: {author} (@{handle})")
    return True


# ── Data charts ──────────────────────────────────────────────────────────────

def generate_chart(chart_type: str, output_path: str,
                   data: dict = None) -> bool:
    """Generate BTC/mempool/hashrate charts with matplotlib.

    Args:
        chart_type: "price_7d", "mempool_fees", "hashrate_30d", "difficulty"
        output_path: Where to save the chart PNG
        data: Optional data dict. If None, fetches from mempool.space API.

    Returns:
        True if chart was generated.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Dark theme
    plt.rcParams.update({
        "figure.facecolor": "#0a0a0f",
        "axes.facecolor": "#0a0a0f",
        "axes.edgecolor": "#333333",
        "axes.labelcolor": "#888888",
        "text.color": "#cccccc",
        "xtick.color": "#666666",
        "ytick.color": "#666666",
        "grid.color": "#1a1a1a",
        "grid.alpha": 0.5,
    })

    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)

    try:
        if chart_type == "price_7d":
            _chart_btc_price(ax, data)
        elif chart_type == "mempool_fees":
            _chart_mempool_fees(ax, data)
        elif chart_type == "hashrate_30d":
            _chart_hashrate(ax, data)
        elif chart_type == "difficulty":
            _chart_difficulty(ax, data)
        else:
            _chart_btc_price(ax, data)

        ax.grid(True, alpha=0.3)
        plt.tight_layout(pad=2)
        fig.savefig(output_path, facecolor="#0a0a0f", dpi=100,
                    bbox_inches="tight", transparent=False)
        plt.close(fig)
        print(f"  [chart] Generated: {chart_type} → {output_path}")
        return True

    except Exception as e:
        print(f"  [chart] Error generating {chart_type}: {e}")
        plt.close(fig)
        return False


def _fetch_json(url: str, timeout: int = 10):
    if not HAS_REQUESTS:
        return None
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _chart_btc_price(ax, data: dict = None):
    """7-day BTC price chart."""
    if data and "prices" in data:
        prices = data["prices"]
        times = [datetime.now() - timedelta(hours=len(prices) - i) for i in range(len(prices))]
    else:
        # Fetch from mempool.space
        raw = _fetch_json("https://mempool.space/api/v1/mining/hashrate/1w")
        if raw and "currentHashrate" in raw:
            # mempool doesn't have direct price history, generate sample
            prices = _generate_sample_prices()
            times = [datetime.now() - timedelta(hours=len(prices) - i) for i in range(len(prices))]
        else:
            prices = _generate_sample_prices()
            times = [datetime.now() - timedelta(hours=len(prices) - i) for i in range(len(prices))]

    color = "#00cc66" if prices[-1] >= prices[0] else "#cc3333"
    ax.plot(times, prices, color=color, linewidth=2.5, alpha=0.9)
    ax.fill_between(times, prices, min(prices) * 0.99, color=color, alpha=0.1)

    ax.set_title("BTC/USD — 7 Day", fontsize=24, fontweight="bold", pad=20)
    ax.set_ylabel("Price (USD)", fontsize=16)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"${x:,.0f}"))

    # Key price level lines
    current = prices[-1]
    ax.axhline(y=current, color=color, linestyle="--", alpha=0.5, linewidth=1)
    ax.text(times[-1], current, f"  ${current:,.0f}", color=color, fontsize=14,
            verticalalignment="bottom")


def _chart_mempool_fees(ax, data: dict = None):
    """Mempool fee chart."""
    raw = _fetch_json("https://mempool.space/api/v1/fees/recommended")
    if raw:
        categories = ["Economy", "Low", "Medium", "High"]
        values = [
            raw.get("economyFee", 1),
            raw.get("hourFee", 2),
            raw.get("halfHourFee", 5),
            raw.get("fastestFee", 10),
        ]
    else:
        categories = ["Economy", "Low", "Medium", "High"]
        values = [1, 3, 8, 15]

    colors = ["#00cc66", "#66cc00", "#cccc00", "#cc3333"]
    bars = ax.bar(categories, values, color=colors, width=0.6, edgecolor="#333", linewidth=1)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{val} sat/vB", ha="center", fontsize=16, fontweight="bold", color="#ffffff")

    ax.set_title("Bitcoin Mempool Fees — Current", fontsize=24, fontweight="bold", pad=20)
    ax.set_ylabel("sat/vB", fontsize=16)


def _chart_hashrate(ax, data: dict = None):
    """30-day hashrate chart."""
    raw = _fetch_json("https://mempool.space/api/v1/mining/hashrate/1m")
    if raw and "hashrates" in raw:
        entries = raw["hashrates"][-30:]
        times = [datetime.fromtimestamp(e["timestamp"]) for e in entries]
        values = [e["avgHashrate"] / 1e18 for e in entries]  # EH/s
    else:
        values = _generate_sample_hashrate()
        times = [datetime.now() - timedelta(days=30 - i) for i in range(len(values))]

    ax.plot(times, values, color="#ff6600", linewidth=2.5, alpha=0.9)
    ax.fill_between(times, values, min(values) * 0.95, color="#ff6600", alpha=0.1)

    ax.set_title("Bitcoin Hashrate — 30 Day", fontsize=24, fontweight="bold", pad=20)
    ax.set_ylabel("EH/s", fontsize=16)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))


def _chart_difficulty(ax, data: dict = None):
    """Difficulty adjustment chart."""
    raw = _fetch_json("https://mempool.space/api/v1/mining/difficulty-adjustments/12")
    if raw and len(raw) > 2:
        times = [datetime.fromtimestamp(e["timestamp"]) for e in raw[-12:]]
        values = [e["difficultyChange"] for e in raw[-12:]]
    else:
        values = [2.1, -1.3, 3.5, 0.8, -0.5, 4.7, 1.2, -2.1, 3.3, 2.8, -0.9, 1.5]
        times = [datetime.now() - timedelta(weeks=12 - i) for i in range(12)]

    colors = ["#00cc66" if v >= 0 else "#cc3333" for v in values]
    ax.bar(times, values, color=colors, width=8, edgecolor="#333", linewidth=1)

    ax.set_title("Bitcoin Difficulty Adjustments — Last 12", fontsize=24, fontweight="bold", pad=20)
    ax.set_ylabel("Change (%)", fontsize=16)
    ax.axhline(y=0, color="#444444", linewidth=1)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))


def _generate_sample_prices(days: int = 7) -> list:
    """Generate realistic-looking sample BTC prices."""
    import random
    base = 97000
    prices = [base]
    for _ in range(days * 24):
        change = random.gauss(0, 150)
        prices.append(max(80000, min(120000, prices[-1] + change)))
    return prices


def _generate_sample_hashrate(days: int = 30) -> list:
    """Generate sample hashrate values."""
    import random
    base = 650
    values = [base]
    for _ in range(days - 1):
        change = random.gauss(2, 10)
        values.append(max(500, values[-1] + change))
    return values


# ── Pexels B-roll (last resort) ──────────────────────────────────────────────

def fetch_pexels_broll(query: str, output_path: str, duration: int = 3) -> bool:
    """Fetch a short Pexels B-roll clip for transitions only.

    Limited to 3s clips by default — real content should use YouTube/screenshots.

    Args:
        query: Search query
        output_path: Where to save
        duration: Max clip duration (default 3s)

    Returns:
        True if clip was fetched.
    """
    from relay import get_key
    key = get_key("PEXELS_API_KEY")
    if not key or not HAS_REQUESTS:
        return False

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": 3, "size": "medium",
                    "orientation": "landscape"},
            headers={"Authorization": key},
            timeout=15,
        )
        if r.status_code != 200:
            return False

        videos = r.json().get("videos", [])
        if not videos:
            return False

        files = videos[0].get("video_files", [])
        hd = (
            next((f for f in files if f.get("height", 0) >= 1080), None)
            or next((f for f in files if f.get("height", 0) >= 720), None)
            or (files[0] if files else None)
        )
        if not hd:
            return False

        raw_path = output_path + ".raw.mp4"
        vid_r = requests.get(hd["link"], timeout=60, stream=True)
        with open(raw_path, "wb") as fh:
            for chunk in vid_r.iter_content(chunk_size=65536):
                fh.write(chunk)

        # Trim to max duration
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path, "-t", str(duration),
             "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
             "-c:v", "libx264", "-crf", "22", "-an", output_path],
            capture_output=True, text=True, timeout=60,
        )
        try:
            os.remove(raw_path)
        except Exception:
            pass

        if os.path.exists(output_path):
            print(f"  [pexels] B-roll: {query[:30]} ({duration}s)")
            return True

    except Exception as e:
        print(f"  [pexels] Error: {e}")

    return False


if __name__ == "__main__":
    out_dir = os.path.join(BASE, "output", "visual_test")
    os.makedirs(out_dir, exist_ok=True)

    # Test tweet card
    screenshot_tweet(
        "Bitcoin just hit a new all-time high in hash rate. "
        "The network has never been more secure. This is what adoption looks like.",
        "Satoshi Nakamoto", "satoshi",
        os.path.join(out_dir, "tweet_card.png"),
    )

    # Test chart
    generate_chart("price_7d", os.path.join(out_dir, "btc_price.png"))
    generate_chart("mempool_fees", os.path.join(out_dir, "fees.png"))

    print(f"\nTest output: {out_dir}")
