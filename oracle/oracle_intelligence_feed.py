"""
Oracle Intelligence Feed — Reads articles from DB, generates live daily brief via Claude.
Renders briefing video through cache_render_helper.py.
"""

import os
import json
import time
import sqlite3
import logging
import threading
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger("oracle_intelligence_feed")

ORACLE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ORACLE_DIR, "..", "instance", "protocol_pulse.db")
CACHE_DIR = os.path.join(ORACLE_DIR, "cache")
RESPONSES_DIR = os.path.join(CACHE_DIR, "responses")
BRIEF_PATH = os.path.join(RESPONSES_DIR, "DAILY_BRIEF_LIVE.mp4")
RENDER_HELPER = os.path.join(ORACLE_DIR, "cache_render_helper.py")

REFRESH_INTERVAL = 3600  # 1 hour


def _get_anthropic_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        env_path = os.path.join(ORACLE_DIR, "..", ".env")
        if os.path.exists(env_path):
            for line in open(env_path):
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.strip().split("=", 1)[1].strip().strip("\"'")
    return key


def _get_recent_articles(limit=5):
    """Fetch recent articles from the DB (last 24h)."""
    if not os.path.exists(DB_PATH):
        logger.warning(f"[INTEL] DB not found: {DB_PATH}")
        return []

    cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT title, summary, published_at FROM articles "
            "WHERE published_at > ? ORDER BY published_at DESC LIMIT ?",
            (cutoff, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"[INTEL] DB error: {e}")
        return []


def _generate_briefing_text(articles):
    """Call Claude Haiku to generate a verbal briefing from headlines."""
    import requests

    api_key = _get_anthropic_key()
    if not api_key:
        logger.error("[INTEL] No ANTHROPIC_API_KEY")
        return None

    headlines = "\n".join(
        f"- {a['title']}" + (f": {a['summary'][:120]}" if a.get('summary') else "")
        for a in articles
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": (
                    "You are the Oracle, a Bitcoin intelligence AI. Write a 75-second verbal briefing "
                    "in first person based on these headlines. Direct, confident, no filler. Sound like "
                    "a human analyst:\n\n" + headlines
                ),
            }],
        },
        timeout=30,
    )

    if resp.status_code != 200:
        logger.error(f"[INTEL] Claude error {resp.status_code}: {resp.text[:200]}")
        return None

    return resp.json()["content"][0]["text"]


def _render_brief(text):
    """Render briefing text to video via cache_render_helper."""
    os.makedirs(RESPONSES_DIR, exist_ok=True)
    try:
        logger.info(f"[INTEL] Rendering daily brief ({len(text)} chars)...")
        t0 = time.time()
        result = subprocess.run(
            ["python3", RENDER_HELPER, "--text", text, "--out", BRIEF_PATH],
            capture_output=True, text=True, timeout=180,
            cwd=ORACLE_DIR,
        )
        elapsed = time.time() - t0
        if result.returncode != 0:
            logger.error(f"[INTEL] Render failed: {result.stderr[-300:]}")
            return False
        logger.info(f"[INTEL] Daily brief rendered in {elapsed:.1f}s")
        return True
    except Exception as e:
        logger.error(f"[INTEL] Render error: {e}")
        return False


def refresh_daily_brief():
    """Full refresh: fetch articles -> Claude briefing -> render video."""
    articles = _get_recent_articles(5)
    if not articles:
        logger.warning("[INTEL] No recent articles — skipping brief generation")
        return False

    logger.info(f"[INTEL] {len(articles)} articles found, generating briefing...")
    text = _generate_briefing_text(articles)
    if not text:
        logger.warning("[INTEL] Briefing text generation failed")
        return False

    return _render_brief(text)


def get_daily_brief():
    """Return path to the daily brief mp4, or None if not ready."""
    if os.path.exists(BRIEF_PATH) and os.path.getsize(BRIEF_PATH) > 0:
        return BRIEF_PATH
    return None


def start_intelligence_feed():
    """Start background thread that refreshes the daily brief every REFRESH_INTERVAL."""
    def _loop():
        # Initial refresh
        try:
            refresh_daily_brief()
        except Exception as e:
            logger.error(f"[INTEL] Initial refresh error: {e}")

        while True:
            time.sleep(REFRESH_INTERVAL)
            try:
                refresh_daily_brief()
            except Exception as e:
                logger.error(f"[INTEL] Refresh error: {e}")

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info(f"[INTEL] Intelligence feed started (interval={REFRESH_INTERVAL}s)")
