"""social_card_renderer — Phase 2 of program.md v3.

Render branded tweet/Nostr cards to PNG via a persistent Playwright browser,
so ffmpeg can overlay them as image assets instead of building text in
filtergraphs. Also captures actual X screenshots when a live URL is available.

Public API:
    render_post(post, cache_dir) -> str   # returns PNG path or ""
    render_posts(posts, cache_dir) -> list[dict]  # mutates posts with screenshot_path
    shutdown()                            # tears down persistent browser

Cache key: SHA256(post_id or seg_id or text)[:12] + ".png"
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading

logger = logging.getLogger("SocialCardRenderer")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[social_card] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

_BROWSER = None
_PW = None
_LOCK = threading.Lock()

CARD_W = 1360
CARD_MIN_H = 240
CARD_MAX_H = 520

_HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html, body {{
    margin: 0; padding: 0; background: transparent;
    font-family: 'JetBrains Mono', 'Menlo', 'Consolas', monospace;
    color: #F4F5F8;
  }}
  .card {{
    width: {W}px; min-height: {H}px; box-sizing: border-box;
    background: #050607;
    border: 2px solid #CC2222;
    border-left: 8px solid #CC2222;
    padding: 22px 28px 22px 30px;
    position: relative;
  }}
  .top-bar {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 14px;
  }}
  .handle {{
    color: #CC2222; font-weight: 700; font-size: 22px; letter-spacing: 0.3px;
  }}
  .platform {{
    color: #F4F5F8; font-size: 14px; opacity: 0.75; font-weight: 600;
    padding: 2px 8px; border: 1px solid #CC2222; border-radius: 3px;
  }}
  .tweet {{
    color: #F4F5F8; font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    font-size: {FS}px; line-height: 1.36; letter-spacing: 0.1px;
    word-wrap: break-word; overflow-wrap: break-word;
    margin-bottom: 18px; font-weight: 500;
  }}
  .stats {{
    display: flex; justify-content: space-between; align-items: center;
    color: #CC2222; font-size: 13px; opacity: 0.9;
    border-top: 1px solid rgba(204, 34, 34, 0.25);
    padding-top: 10px;
  }}
  .stats .metrics span {{ margin-right: 18px; }}
  .stats .watermark {{ color: #555; font-size: 11px; letter-spacing: 2px; }}
  .corner {{
    position: absolute; width: 12px; height: 12px; border-color: #CC2222;
    border-style: solid;
  }}
  .c-tr {{ top: 4px; right: 4px; border-width: 2px 2px 0 0; }}
  .c-bl {{ bottom: 4px; left: 4px; border-width: 0 0 2px 2px; }}
</style></head>
<body>
  <div class="card">
    <div class="top-bar">
      <div class="handle">{HANDLE}</div>
      <div class="platform">{PLATFORM}</div>
    </div>
    <div class="tweet">{TEXT}</div>
    <div class="stats">
      <div class="metrics">{METRICS}</div>
      <div class="watermark">PROTOCOL PULSE</div>
    </div>
    <div class="corner c-tr"></div>
    <div class="corner c-bl"></div>
  </div>
</body></html>"""


def _get_browser():
    global _BROWSER, _PW
    if _BROWSER is not None:
        return _BROWSER
    with _LOCK:
        if _BROWSER is not None:
            return _BROWSER
        from playwright.sync_api import sync_playwright
        _PW = sync_playwright().start()
        _BROWSER = _PW.chromium.launch(headless=True, args=[
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-sandbox",
        ])
        logger.info("Playwright chromium launched (persistent)")
        return _BROWSER


def shutdown():
    global _BROWSER, _PW
    with _LOCK:
        try:
            if _BROWSER is not None:
                _BROWSER.close()
        except Exception:
            pass
        try:
            if _PW is not None:
                _PW.stop()
        except Exception:
            pass
        _BROWSER = None
        _PW = None


def _cache_key(post: dict) -> str:
    for k in ("seg_id", "id", "tweet_url", "url"):
        v = post.get(k)
        if v:
            return hashlib.sha256(str(v).encode()).hexdigest()[:12]
    text = post.get("text") or post.get("content") or ""
    handle = post.get("handle") or post.get("author") or ""
    return hashlib.sha256(f"{handle}|{text}".encode()).hexdigest()[:12]


def _fmt_stats(post: dict) -> str:
    likes = post.get("likes", 0)
    rts = post.get("retweets", 0)
    likes_int = likes if isinstance(likes, int) else 0
    rts_int = rts if isinstance(rts, int) else 0
    if likes_int == 0 and rts_int == 0:
        return "<span>via " + _platform_label(post) + "</span>"
    parts = []
    if likes_int:
        parts.append(f"<span>{likes_int:,} likes</span>")
    if rts_int:
        parts.append(f"<span>{rts_int:,} RTs</span>")
    return "".join(parts)


def _platform_label(post: dict) -> str:
    src = (post.get("platform") or post.get("source") or "").lower()
    if "nostr" in src or post.get("npub"):
        return "NOSTR"
    return "X"


def _fontsize_for(text: str) -> int:
    n = len(text or "")
    if n > 220:
        return 26
    if n > 140:
        return 30
    if n > 90:
        return 36
    return 42


_html_escape_re = re.compile(r'[&<>"\']')
_html_escape_map = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}


def _esc(s: str) -> str:
    return _html_escape_re.sub(lambda m: _html_escape_map[m.group(0)], s or "")


def _linkify_newlines(s: str) -> str:
    """Preserve intentional newlines from tweet formatting as <br>."""
    return _esc(s).replace("\n", "<br>")


def render_template_card(post: dict, out_path: str) -> bool:
    """Render an HTML template card to PNG. Returns True on success."""
    handle = post.get("handle") or post.get("author") or "unknown"
    if not handle.startswith("@") and not handle.startswith("npub"):
        handle = f"@{handle}"
    text_raw = post.get("text") or post.get("content") or ""
    fontsize = _fontsize_for(text_raw)
    html = _HTML_TEMPLATE.format(
        W=CARD_W,
        H=CARD_MIN_H,
        FS=fontsize,
        HANDLE=_esc(handle),
        PLATFORM=_platform_label(post),
        TEXT=_linkify_newlines(text_raw),
        METRICS=_fmt_stats(post),
    )
    try:
        browser = _get_browser()
        context = browser.new_context(
            viewport={"width": CARD_W + 40, "height": CARD_MAX_H + 40},
            device_scale_factor=2,  # crisp on 1080p
        )
        page = context.new_page()
        page.set_content(html, wait_until="load")
        locator = page.locator(".card")
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        locator.screenshot(path=out_path, omit_background=True)
        context.close()
        if os.path.exists(out_path) and os.path.getsize(out_path) > 512:
            return True
        return False
    except Exception as e:
        logger.warning(f"Template card render failed for {handle}: {e}")
        return False


def render_live_screenshot(post: dict, out_path: str, timeout_ms: int = 12000) -> bool:
    """Capture the actual tweet element from x.com. Returns True on success."""
    url = post.get("tweet_url") or post.get("url")
    if not url or "x.com" not in url and "twitter.com" not in url:
        return False
    try:
        browser = _get_browser()
        context = browser.new_context(
            viewport={"width": 1280, "height": 1400},
            device_scale_factor=2,
        )
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        try:
            page.wait_for_selector('article[data-testid="tweet"]', timeout=timeout_ms)
        except Exception:
            context.close()
            return False
        tweet_el = page.query_selector('article[data-testid="tweet"]')
        if not tweet_el:
            context.close()
            return False
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        tweet_el.screenshot(path=out_path)
        context.close()
        return os.path.exists(out_path) and os.path.getsize(out_path) > 1024
    except Exception as e:
        logger.warning(f"Live SS failed for {url}: {e}")
        return False


def render_post(post: dict, cache_dir: str, prefer_live: bool = True) -> str:
    """Render one post to PNG, using cache. Returns path or ''.

    prefer_live: try actual X screenshot first (better authenticity),
                 fall back to template on failure or missing URL.
    """
    os.makedirs(cache_dir, exist_ok=True)
    key = _cache_key(post)
    out_path = os.path.join(cache_dir, f"card_{key}.png")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 512:
        return out_path

    ok = False
    if prefer_live and (post.get("tweet_url") or post.get("url")):
        ok = render_live_screenshot(post, out_path)
        if ok:
            logger.info(f"  LIVE SS: {post.get('handle', '?')} -> {os.path.basename(out_path)}")
    if not ok:
        ok = render_template_card(post, out_path)
        if ok:
            logger.info(f"  TEMPLATE: {post.get('handle', '?')} -> {os.path.basename(out_path)}")
    return out_path if ok else ""


def render_posts(posts: list, cache_dir: str, prefer_live: bool = True) -> list:
    """Render all posts, mutating each with screenshot_path key."""
    if not posts:
        return posts
    for p in posts:
        if p.get("screenshot_path") and os.path.exists(p["screenshot_path"]):
            continue
        path = render_post(p, cache_dir, prefer_live=prefer_live)
        if path:
            p["screenshot_path"] = path
    # Tear down browser after batch to release RAM (matters on constrained GPU boxes).
    shutdown()
    return posts


if __name__ == "__main__":
    # Smoke test
    import json
    posts = [
        {"handle": "saylor", "text": "Bitcoin is digital gold. Convert your treasury before it's too late.", "likes": 8420, "retweets": 1210, "seg_id": "test_saylor"},
        {"handle": "npub1abc", "content": "Sovereign money is not a request. It's a return.", "likes": 0, "retweets": 0, "platform": "nostr", "seg_id": "test_nostr"},
        {"handle": "hodlonaut", "text": "STAY HUMBLE. STACK SATS.", "likes": 500, "retweets": 42, "seg_id": "test_hodl"},
    ]
    out = render_posts(posts, "/tmp/pp_card_test")
    for p in out:
        print(p.get("handle"), "->", p.get("screenshot_path"))
