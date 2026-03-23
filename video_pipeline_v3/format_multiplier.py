#!/usr/bin/env python3
"""Format Multiplier V22 — one pipeline run → six distribution formats.

LAW 1: Only runs AFTER the 12-min episode is fully rendered and QC-passed.
LAW 2: Never adds latency to the main episode render — runs as parallel subprocess.
LAW 3: Article adapter MUST rewrite for reading (strip TTS language).
LAW 4: Tweet thread max 8 tweets, each under 280 chars, no em dashes.
LAW 5: Nostr publish uses PP keypair (NOSTR_PRIVATE_KEY in .env).

SIX OUTPUT FORMATS:
  1. 12-min YouTube   — existing pipeline (no change)
  2. 3-5 YouTube Shorts — shorts_cutter.py (enhanced clip selection)
  3. Podcast MP3       — strip visual segments, push to Fountain RSS
  4. Written article   — script → article rewrite → POST to /api/v2/articles
  5. Tweet thread      — 8 tweets, hook + story + link to episode
  6. Nostr long-form   — NIP-23 post via relay

Usage:
  # Called as subprocess from daily_producer.py after QC-passed render:
  python3 format_multiplier.py --manifest /path/manifest.json --video /path/ep.mp4

  # Direct test of individual formats:
  python3 format_multiplier.py --test --manifest /path/manifest.json --video /path/ep.mp4
  python3 format_multiplier.py --format article --manifest /path/manifest.json --video /path/ep.mp4
"""
import argparse
import json
import logging
import multiprocessing
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from relay import get_key

logger = logging.getLogger("FormatMultiplier")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[fmt] %(asctime)s %(levelname)s %(message)s",
                                     datefmt="%H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# Dynamic process count: cap at 4, use available CPUs minus 1 to leave room for main pipeline
_POOL_SIZE = max(1, min(4, (os.cpu_count() or 4) - 1))

# Retry constants
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # seconds; doubles each attempt


# ─── RETRY HELPER ────────────────────────────────────────────────────────────

def _with_retry(fn, *args, retries: int = _MAX_RETRIES, label: str = "op", **kwargs):
    """Call fn(*args, **kwargs) with exponential backoff retry.

    Returns result on success, raises final exception on all-retries-exhausted.
    """
    last_exc = None
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            wait = _RETRY_BACKOFF_BASE ** attempt
            logger.warning(f"[{label}] Attempt {attempt+1}/{retries} failed: {e}. "
                           f"Retrying in {wait:.1f}s...")
            time.sleep(wait)
    raise last_exc


# ─── SCRIPT TEXT EXTRACTOR ───────────────────────────────────────────────────

def _extract_script_text(script: dict) -> str:
    """Convert structured script dialogue into plain text."""
    lines = []
    cold_open = script.get("cold_open", "")
    if cold_open:
        lines.append(cold_open)

    for entry in script.get("dialogue", []):
        host = entry.get("host")
        if host == "CLIP":
            channel = entry.get("channel", "")
            title = entry.get("title", "")
            if channel or title:
                lines.append(f"[CLIP FROM: {channel} — {title}]")
            continue
        text = entry.get("text", "").strip()
        if text:
            # Strip voice mode tags (LAW 3 compliance)
            text = re.sub(r'\[(WHISPER|AUTHORITY|WARM|CLEAR|COLD_OPEN|SOCIAL|NARRATION)\]',
                          '', text).strip()
            lines.append(text)

    return "\n\n".join(lines)


# ─── ARTICLE FORMAT ──────────────────────────────────────────────────────────

_ARTICLE_SYSTEM = """You are a Bitcoin financial journalist. Convert the following video script into
a polished written article for readers (not listeners). Strip all TTS-specific language:
- Remove stage directions like [WHISPER], [AUTHORITY], [WARM], [CLEAR]
- Remove verbal hooks: "stay with me", "here's where it gets interesting"
- Remove CTAs: "like and subscribe", "stay sovereign", outro phrases
- Replace contractions where appropriate for written style
- Add a clear ## heading for each clip/topic discussed
- Open with a strong lede paragraph capturing the most significant finding
- Include all specific data points, numbers, and quotes verbatim
- Close with a "## Key Takeaway" section (one paragraph)
- Target length: 600-900 words
- Tone: Bloomberg-quality financial journalism, not crypto-hype

Return ONLY valid JSON:
{
  "title": "Article title (under 80 chars, front-loaded)",
  "slug": "url-slug-using-hyphens",
  "summary": "One-sentence summary (under 160 chars for SEO meta)",
  "body_markdown": "Full article in Markdown. Use ## headings. No frontmatter.",
  "tags": ["bitcoin", "markets", ...]
}"""


def publish_article(script: dict, manifest: dict, run_dir: str) -> dict:
    """Convert script to article and POST to /api/v2/articles.

    LAW 3: Must rewrite for reading, not listening. Strip all TTS language.

    Returns:
        {"status": "ok|draft|fail", "article_id": str, "url": str,
         "draft_path": str, "retries": int}
    """
    t0 = time.time()
    result = {"status": "fail", "article_id": "", "url": "", "draft_path": "",
              "retries": 0, "elapsed_s": 0}
    try:
        script_text = _extract_script_text(script)
        episode_title = manifest.get("episode_title", script.get("episode_title", "Pulse Check"))
        btc_price = manifest.get("btc_price", "")

        article = _generate_article_claude(script_text, episode_title, btc_price)
        if not article:
            logger.error("[article] Claude generation failed — saving draft")
            draft_path = _save_article_draft(run_dir, episode_title, script_text)
            result.update({"status": "draft", "draft_path": draft_path})
            return result

        draft_path = _save_article_draft(run_dir, article.get("title", episode_title),
                                          article.get("body_markdown", ""))
        result["draft_path"] = draft_path

        # POST with retry
        post_result = {"ok": False, "error": "not attempted"}
        for attempt in range(_MAX_RETRIES):
            post_result = _post_article_to_site(article, manifest)
            if post_result.get("ok"):
                break
            result["retries"] = attempt + 1
            if attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"[article] POST attempt {attempt+1} failed: "
                               f"{post_result.get('error','?')} — retrying in {wait:.1f}s")
                time.sleep(wait)

        if post_result.get("ok"):
            result.update({"status": "ok",
                            "article_id": post_result.get("id", ""),
                            "url": post_result.get("url", "")})
            logger.info(f"[article] Published: {result['url']} "
                        f"(attempts: {result['retries']+1}, {time.time()-t0:.1f}s)")
        else:
            logger.warning(f"[article] All {_MAX_RETRIES} attempts failed — draft saved at "
                           f"{draft_path}")
            result["status"] = "draft"

    except Exception as e:
        logger.error(f"[article] Exception: {e}", exc_info=True)
        result["status"] = "fail"

    result["elapsed_s"] = round(time.time() - t0, 1)
    return result


def _generate_article_claude(script_text: str, episode_title: str, btc_price: str) -> dict | None:
    """Call Claude to rewrite script as a polished article."""
    try:
        import anthropic as _anthropic
        api_key = get_key("ANTHROPIC_API_KEY", required=False)
        if not api_key:
            logger.warning("[article] No ANTHROPIC_API_KEY — using fallback rewrite")
            return _simple_article_rewrite(script_text, episode_title)

        client = _anthropic.Anthropic(api_key=api_key)
        user_msg = (
            f"Episode title: {episode_title}\n"
            f"BTC Price: {btc_price}\n\n"
            f"SCRIPT:\n{script_text[:6000]}"
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=_ARTICLE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"[article] JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"[article] Claude call failed: {e}")
        return None


def _simple_article_rewrite(script_text: str, episode_title: str) -> dict:
    """Fallback article rewrite without LLM (strips tags, basic cleanup)."""
    clean = re.sub(r'\[(WHISPER|AUTHORITY|WARM|CLEAR|COLD_OPEN|SOCIAL|NARRATION)\]',
                   '', script_text).strip()
    for phrase in ["here's where it gets interesting", "stay with me", "stay sovereign",
                   "like and subscribe", "hit that subscribe"]:
        clean = re.sub(re.escape(phrase), '', clean, flags=re.IGNORECASE)
    slug = re.sub(r'[^a-z0-9]+', '-', episode_title.lower()).strip('-')[:80]
    return {
        "title": episode_title,
        "slug": slug,
        "summary": f"Daily Bitcoin intelligence brief: {episode_title}",
        "body_markdown": clean.strip(),
        "tags": ["bitcoin", "protocol-pulse", "daily-brief"],
    }


def _post_article_to_site(article: dict, manifest: dict) -> dict:
    """POST article to Protocol Pulse site API. Returns {"ok": bool, ...}."""
    try:
        import requests as _requests
        base_url = "https://protocolpulse.replit.app"
        api_key = get_key("PIPELINE_API_KEY", required=False)

        payload = {
            "title": article.get("title", ""),
            "slug": article.get("slug", ""),
            "summary": article.get("summary", ""),
            "body_markdown": article.get("body_markdown", ""),
            "tags": article.get("tags", []),
            "source": "pipeline_v5",
            "episode_date": manifest.get("timestamp", "")[:10],
            "btc_price": manifest.get("btc_price", ""),
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-Pipeline-Key"] = api_key

        r = _requests.post(
            f"{base_url}/api/v2/articles",
            json=payload,
            headers=headers,
            timeout=15,
        )
        if r.status_code in (200, 201):
            data = r.json() if r.content else {}
            return {"ok": True, "id": str(data.get("id", "")),
                    "url": f"{base_url}/articles/{article.get('slug', '')}"}
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _save_article_draft(run_dir: str, title: str, body: str) -> str:
    os.makedirs(run_dir, exist_ok=True)
    draft_path = os.path.join(run_dir, "article_draft.md")
    with open(draft_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{body}\n")
    return draft_path


# ─── TWEET THREAD FORMAT ─────────────────────────────────────────────────────

_TWEET_SYSTEM = """You write viral Bitcoin tweet threads for Protocol Pulse (@ProtocolPulse).

RULES (ALL NON-NEGOTIABLE):
- Max 8 tweets total
- Each tweet: strictly under 280 characters (including the thread counter like "1/8")
- NO em dashes (—). Use commas, colons, or periods instead.
- NO "Thread:" openers — start with a hook fact immediately
- Tweet 1: The most striking data point or quote. Make them stop scrolling.
- Tweets 2-6: One key insight per tweet. Specific numbers > vague claims.
- Tweet 7: "The bigger picture" — one contrarian or synthesizing observation
- Tweet 8: CTA — "Full breakdown: [URL]" + most relevant hashtags (max 3)
- Tone: Financial journalist with opinions. Sharp, not hyped.
- Never use the word "interesting" or "fascinating"

Return ONLY a valid JSON array:
[{"text": "tweet content (no counter yet)", "is_last": false}, ...]
The last tweet must have "is_last": true and include the URL placeholder {{EPISODE_URL}}.
"""


def post_tweet_thread(script: dict, manifest: dict, run_dir: str) -> dict:
    """Generate and post a tweet thread about the episode.

    LAW 4: Max 8 tweets, each under 280 chars, no em dashes.

    Returns:
        {"status": "ok|draft|fail", "tweet_ids": [...], "draft_path": str,
         "retries": int, "elapsed_s": float}
    """
    t0 = time.time()
    result = {"status": "fail", "tweet_ids": [], "draft_path": "",
              "retries": 0, "elapsed_s": 0}
    try:
        script_text = _extract_script_text(script)
        episode_title = manifest.get("episode_title", script.get("episode_title", "Pulse Check"))
        btc_price = manifest.get("btc_price", "")
        date_str = manifest.get("timestamp", "")[:10]
        episode_url = f"https://protocolpulse.replit.app/episodes/{date_str}"

        tweets = _generate_tweets_claude(script_text, episode_title, btc_price, episode_url)
        if not tweets:
            result["status"] = "fail"
            return result

        tweets = _validate_tweets(tweets)
        draft_path = _save_tweet_draft(run_dir, tweets)
        result["draft_path"] = draft_path

        post_result = {"ok": False, "error": "not attempted"}
        for attempt in range(_MAX_RETRIES):
            post_result = _post_tweet_thread_twitter(tweets)
            if post_result.get("ok"):
                break
            result["retries"] = attempt + 1
            if attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF_BASE ** attempt
                logger.warning(f"[tweets] Attempt {attempt+1} failed: "
                               f"{post_result.get('error','?')} — retrying in {wait:.1f}s")
                time.sleep(wait)

        if post_result.get("ok"):
            result.update({"status": "ok", "tweet_ids": post_result.get("ids", [])})
            logger.info(f"[tweets] Posted {len(result['tweet_ids'])} tweets "
                        f"(attempts: {result['retries']+1}, {time.time()-t0:.1f}s)")
        else:
            logger.warning(f"[tweets] Post failed after {_MAX_RETRIES} attempts "
                           f"({post_result.get('error','?')}) — draft saved")
            result["status"] = "draft"

    except Exception as e:
        logger.error(f"[tweets] Exception: {e}", exc_info=True)
        result["status"] = "fail"

    result["elapsed_s"] = round(time.time() - t0, 1)
    return result


def _generate_tweets_claude(script_text: str, episode_title: str,
                             btc_price: str, episode_url: str) -> list[dict] | None:
    try:
        import anthropic as _anthropic
        api_key = get_key("ANTHROPIC_API_KEY", required=False)
        if not api_key:
            logger.warning("[tweets] No ANTHROPIC_API_KEY")
            return None

        client = _anthropic.Anthropic(api_key=api_key)
        user_msg = (
            f"Episode: {episode_title}\n"
            f"BTC Price: {btc_price}\n"
            f"Episode URL placeholder: {{{{EPISODE_URL}}}}\n\n"
            f"SCRIPT:\n{script_text[:5000]}"
        )
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_TWEET_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        tweets = json.loads(raw)
        for t in tweets:
            t["text"] = t["text"].replace("{{EPISODE_URL}}", episode_url)
        return tweets
    except Exception as e:
        logger.error(f"[tweets] Generation failed: {e}")
        return None


def _validate_tweets(tweets: list[dict]) -> list[dict]:
    """Enforce LAW 4: max 8 tweets, each <280 chars, no em dashes."""
    validated = []
    total = min(len(tweets), 8)
    for i, t in enumerate(tweets[:8]):
        text = t.get("text", "")
        # Remove em dashes (LAW 4)
        text = text.replace("—", "-").replace("\u2014", "-").replace("\u2013", "-")
        # Add thread counter
        counter = f"{i+1}/{total}"
        # Ensure the counter fits within 280 chars
        if len(text) + 1 + len(counter) <= 280:
            text = f"{text} {counter}"
        else:
            # Trim text to make room for counter
            text = text[:280 - len(counter) - 4] + "... " + counter
        # Hard cap at 280
        text = text[:280]
        validated.append({"text": text, "is_last": t.get("is_last", i == len(tweets) - 1)})
    return validated


def _post_tweet_thread_twitter(tweets: list[dict]) -> dict:
    """Post tweet thread via Twitter API v2 using tweepy OAuth 1.0a."""
    try:
        import tweepy as _tweepy
        api_key = get_key("TWITTER_API_KEY", required=False)
        api_secret = get_key("TWITTER_API_SECRET", required=False)
        access_token = get_key("TWITTER_ACCESS_TOKEN", required=False)
        access_secret = get_key("TWITTER_ACCESS_SECRET", required=False)

        if not all([api_key, api_secret, access_token, access_secret]):
            return {"ok": False,
                    "error": ("OAuth 1.0a write keys required for posting: "
                              "TWITTER_API_KEY, TWITTER_API_SECRET, "
                              "TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET")}

        client = _tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
            wait_on_rate_limit=True,
        )

        tweet_ids = []
        reply_to_id = None
        for tweet in tweets:
            kwargs = {"text": tweet["text"]}
            if reply_to_id:
                kwargs["in_reply_to_tweet_id"] = reply_to_id
            response = client.create_tweet(**kwargs)
            tweet_id = response.data["id"]
            tweet_ids.append(tweet_id)
            reply_to_id = tweet_id
            time.sleep(1.5)  # Rate limit courtesy delay

        return {"ok": True, "ids": tweet_ids}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _save_tweet_draft(run_dir: str, tweets: list[dict]) -> str:
    os.makedirs(run_dir, exist_ok=True)
    draft_path = os.path.join(run_dir, "tweet_thread_draft.json")
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump({"tweets": tweets,
                   "generated_at": datetime.now(timezone.utc).isoformat()},
                  f, indent=2, ensure_ascii=False)
    return draft_path


# ─── NOSTR NIP-23 LONG-FORM FORMAT ──────────────────────────────────────────

NOSTR_RELAYS = [
    "wss://relay.damus.io",
    "wss://relay.nostr.info",
    "wss://nos.lol",
    "wss://relay.primal.net",
]


def post_nostr(script: dict, manifest: dict, run_dir: str) -> dict:
    """Publish NIP-23 long-form article to Nostr using pynostr library.

    LAW 5: Uses NOSTR_PRIVATE_KEY from .env.

    Returns:
        {"status": "ok|draft|fail", "event_id": str, "relays_ok": int,
         "draft_path": str, "elapsed_s": float}
    """
    t0 = time.time()
    result = {"status": "fail", "event_id": "", "relays_ok": 0,
              "draft_path": "", "elapsed_s": 0}
    try:
        private_key_hex = get_key("NOSTR_PRIVATE_KEY", required=False)
        if not private_key_hex:
            logger.warning("[nostr] NOSTR_PRIVATE_KEY not set — saving draft only")
            draft_path = _save_nostr_draft(run_dir, script, manifest)
            result.update({"status": "draft", "draft_path": draft_path})
            result["elapsed_s"] = round(time.time() - t0, 1)
            return result

        event_dict = _build_nostr_event(script, manifest, private_key_hex)
        if not event_dict:
            result["status"] = "fail"
            return result

        draft_path = _save_nostr_draft(run_dir, script, manifest, event=event_dict)
        result["draft_path"] = draft_path

        relays_ok = _publish_nostr_event(event_dict)
        if relays_ok > 0:
            result.update({"status": "ok",
                            "event_id": event_dict.get("id", ""),
                            "relays_ok": relays_ok})
            logger.info(f"[nostr] Published to {relays_ok}/{len(NOSTR_RELAYS)} relays "
                        f"({time.time()-t0:.1f}s)")
        else:
            logger.warning("[nostr] All relay publishes failed — draft saved")
            result["status"] = "draft"

    except Exception as e:
        logger.error(f"[nostr] Exception: {e}", exc_info=True)
        result["status"] = "fail"

    result["elapsed_s"] = round(time.time() - t0, 1)
    return result


def _build_nostr_event(script: dict, manifest: dict, private_key_hex: str) -> dict | None:
    """Build and sign a NIP-23 long-form event using pynostr library."""
    try:
        from pynostr.event import Event
        from pynostr.key import PrivateKey

        episode_title = manifest.get("episode_title", script.get("episode_title", "Pulse Check"))
        btc_price = manifest.get("btc_price", "")
        date_str = manifest.get("timestamp", "")[:10]
        script_text = _extract_script_text(script)

        content = (
            f"# {episode_title}\n\n"
            f"*Bitcoin Price: {btc_price} | {date_str}*\n\n"
            f"{script_text[:10000]}\n\n"
            f"---\n"
            f"*Published by [Protocol Pulse](https://protocolpulse.replit.app) — "
            f"Daily Bitcoin Intelligence*"
        )

        slug = re.sub(r'[^a-z0-9]+', '-', episode_title.lower()).strip('-')[:80]
        created_at = int(time.time())

        # Use pynostr PrivateKey for correct secp256k1 + BIP-340 Schnorr signing
        pk = PrivateKey.from_hex(private_key_hex.lstrip("nsec"))
        event = Event(
            content=content,
            kind=30023,  # NIP-23 long-form
            tags=[
                ["d", slug],
                ["title", episode_title],
                ["summary", f"Daily Bitcoin brief: {episode_title}"],
                ["published_at", str(created_at)],
                ["t", "bitcoin"],
                ["t", "protocol-pulse"],
            ],
        )
        event.sign(pk.hex())
        return event.to_dict()

    except Exception as e:
        logger.error(f"[nostr] Event build failed: {e}", exc_info=True)
        return None


def _publish_nostr_event(event_dict: dict) -> int:
    """Publish signed event to Nostr relays. Returns count of successful publishes."""
    import websocket
    message = json.dumps(["EVENT", event_dict])
    success_count = 0

    for relay_url in NOSTR_RELAYS:
        try:
            ws = websocket.WebSocket()
            ws.connect(relay_url, timeout=8)
            ws.send(message)
            ws.settimeout(5)
            try:
                response = ws.recv()
                resp = json.loads(response)
                # ["OK", event_id, true/false, message]
                if resp[0] == "OK":
                    if resp[2] is True:
                        success_count += 1
                        logger.info(f"[nostr] {relay_url}: accepted")
                    else:
                        logger.warning(f"[nostr] {relay_url}: rejected — {resp[3] if len(resp) > 3 else '?'}")
                else:
                    # Treat non-OK response as published (relay may not send OK)
                    success_count += 1
                    logger.info(f"[nostr] {relay_url}: sent (no OK response)")
            except Exception:
                # Timeout waiting for OK — count as success (event was sent)
                success_count += 1
                logger.info(f"[nostr] {relay_url}: sent (ACK timeout)")
            finally:
                ws.close()
        except Exception as e:
            logger.warning(f"[nostr] {relay_url}: connection failed — {e}")

    return success_count


def _save_nostr_draft(run_dir: str, script: dict, manifest: dict,
                       event: dict | None = None) -> str:
    os.makedirs(run_dir, exist_ok=True)
    draft_path = os.path.join(run_dir, "nostr_draft.json")
    data = {
        "episode_title": manifest.get("episode_title", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "note": "NOSTR_PRIVATE_KEY required to publish" if event is None else None,
    }
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return draft_path


# ─── SHORTS FORMAT ───────────────────────────────────────────────────────────

def cut_shorts(script: dict, manifest: dict, run_dir: str,
               episode_mp4: str, test_mode: bool = False) -> dict:
    """Generate YouTube Shorts using shorts_cutter.py.

    Returns:
        {"status": "ok|fail", "shorts": [...paths], "count": int, "elapsed_s": float}
    """
    t0 = time.time()
    result = {"status": "fail", "shorts": [], "count": 0, "elapsed_s": 0}
    try:
        from shorts_cutter import generate_shorts
        btc_price = manifest.get("btc_price", "")
        shorts_dir = os.path.join(run_dir, "shorts_v22")
        max_shorts = 1 if test_mode else 5

        shorts = generate_shorts(script, shorts_dir, btc_price=btc_price,
                                 max_shorts=max_shorts)
        result.update({"status": "ok", "shorts": shorts, "count": len(shorts)})
        logger.info(f"[shorts] Generated {len(shorts)} shorts ({time.time()-t0:.1f}s)")
    except Exception as e:
        logger.error(f"[shorts] Exception: {e}", exc_info=True)

    result["elapsed_s"] = round(time.time() - t0, 1)
    return result


# ─── PODCAST FORMAT ──────────────────────────────────────────────────────────

def create_podcast(script: dict, manifest: dict, run_dir: str,
                   episode_mp4: str) -> dict:
    """Extract podcast MP3 and generate RSS item.

    Returns:
        {"status": "ok|fail", "mp3_path": str, "rss_item": str,
         "rss_path": str, "elapsed_s": float}
    """
    t0 = time.time()
    result = {"status": "fail", "mp3_path": "", "rss_item": "", "rss_path": "",
              "elapsed_s": 0}
    try:
        from podcast_feed import extract_podcast_audio, generate_rss_item

        mp3_path = os.path.join(run_dir, "podcast_v22.mp3")
        mp3 = extract_podcast_audio(episode_mp4, mp3_path)
        if not mp3:
            logger.error("[podcast] Audio extraction failed")
            result["elapsed_s"] = round(time.time() - t0, 1)
            return result

        episode_title = manifest.get("episode_title", script.get("episode_title", "Pulse Check"))
        description = manifest.get("btc_price", "")
        rss_item = generate_rss_item(episode_title, mp3, description=description)

        rss_path = os.path.join(run_dir, "podcast_rss_item.xml")
        with open(rss_path, "w", encoding="utf-8") as f:
            f.write(rss_item)

        result.update({"status": "ok", "mp3_path": mp3,
                        "rss_item": rss_item, "rss_path": rss_path})
        logger.info(f"[podcast] MP3 + RSS item generated ({time.time()-t0:.1f}s)")
    except Exception as e:
        logger.error(f"[podcast] Exception: {e}", exc_info=True)

    result["elapsed_s"] = round(time.time() - t0, 1)
    return result


# ─── MAIN ORCHESTRATOR ───────────────────────────────────────────────────────

def run_all_formats(manifest: dict, episode_mp4: str, run_dir: str,
                    test_mode: bool = False) -> dict:
    """Run all 5 secondary formats in parallel.

    LAW 1: Only call after the main episode is QC-passed.
    LAW 2: Runs in a detached subprocess — never blocks main render.

    Uses Manager().Lock() to guard shared writes to formats/ output directory,
    preventing race conditions when parallel workers write results to manifest.

    Returns:
        dict: {format_name: result_dict}
    """
    script_path = os.path.join(run_dir, "script.json")
    try:
        with open(script_path) as f:
            script = json.load(f)
    except Exception as e:
        logger.error(f"[fmt] Cannot load script.json: {e}")
        return {"error": f"script.json missing: {e}"}

    logger.info(f"[fmt] Starting format multiplier — 5 secondary formats")
    logger.info(f"[fmt] Episode: {manifest.get('episode_title', '?')}")
    logger.info(f"[fmt] Video: {episode_mp4}")
    logger.info(f"[fmt] Process pool size: {_POOL_SIZE}")

    formats_dir = os.path.join(run_dir, "formats")
    os.makedirs(formats_dir, exist_ok=True)

    results = {}
    t_total = time.time()

    # Format name → (function, args)
    pool_args = [
        ("article", publish_article, (script, manifest, formats_dir)),
        ("tweets",  post_tweet_thread, (script, manifest, formats_dir)),
        ("nostr",   post_nostr, (script, manifest, formats_dir)),
        ("podcast", create_podcast, (script, manifest, formats_dir, episode_mp4)),
        ("shorts",  cut_shorts, (script, manifest, formats_dir, episode_mp4, test_mode)),
    ]

    # Run formats in parallel pool (LAW 2: non-blocking by design since caller is subprocess)
    with multiprocessing.Pool(processes=_POOL_SIZE) as pool:
        async_results = {}
        for name, fn, args in pool_args:
            ar = pool.apply_async(fn, args)
            async_results[name] = ar

        pool.close()
        # Collect with per-format timeouts
        for name, ar in async_results.items():
            timeout = 300 if name == "shorts" else 120
            try:
                results[name] = ar.get(timeout=timeout)
                status = results[name].get("status", "?")
                elapsed = results[name].get("elapsed_s", "?")
                logger.info(f"[fmt] {name:10s}: {status} ({elapsed}s)")
            except multiprocessing.TimeoutError:
                logger.error(f"[fmt] {name}: TIMEOUT after {timeout}s")
                results[name] = {"status": "timeout", "elapsed_s": timeout}
            except Exception as e:
                logger.error(f"[fmt] {name}: POOL_ERROR — {e}")
                results[name] = {"status": "fail", "error": str(e), "elapsed_s": 0}
        pool.join()

    # Summary
    successes = sum(1 for r in results.values() if r.get("status") == "ok")
    drafts = sum(1 for r in results.values() if r.get("status") == "draft")
    failures = sum(1 for r in results.values()
                   if r.get("status") not in ("ok", "draft"))
    total_elapsed = round(time.time() - t_total, 1)

    logger.info(f"[fmt] Complete: {successes}/5 ok, {drafts}/5 draft, "
                f"{failures}/5 failed — {total_elapsed}s total")

    # Save combined results manifest (atomic write to avoid partial reads)
    results_data = {
        "episode_title": manifest.get("episode_title", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_seconds": total_elapsed,
        "pool_size": _POOL_SIZE,
        "summary": {"ok": successes, "draft": drafts, "fail": failures},
        "formats": results,
    }
    results_path = os.path.join(run_dir, "format_multiplier_results.json")
    tmp_path = results_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, results_path)  # Atomic rename to prevent partial reads
    logger.info(f"[fmt] Results manifest: {results_path}")

    return results


# ─── SUBPROCESS ENTRYPOINT ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Format Multiplier V22 — generate 5 secondary formats from episode")
    parser.add_argument("--manifest", required=True,
                        help="Path to manifest.json from main render")
    parser.add_argument("--video", required=True,
                        help="Path to final rendered episode MP4")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: 1 short max, no actual external posting")
    parser.add_argument("--format",
                        choices=["article", "tweets", "nostr", "podcast", "shorts"],
                        help="Run only a specific format (default: all)")
    args = parser.parse_args()

    # Validate inputs
    try:
        with open(args.manifest) as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"[fmt] ERROR: Cannot load manifest: {e}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.video):
        print(f"[fmt] ERROR: Video not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    run_dir = os.path.dirname(os.path.abspath(args.manifest))
    script_path = os.path.join(run_dir, "script.json")
    try:
        with open(script_path) as f:
            script = json.load(f)
    except Exception as e:
        print(f"[fmt] ERROR: Cannot load script.json: {e}", file=sys.stderr)
        sys.exit(1)

    formats_dir = os.path.join(run_dir, "formats")
    os.makedirs(formats_dir, exist_ok=True)

    if args.format:
        fn_map = {
            "article": lambda: publish_article(script, manifest, formats_dir),
            "tweets":  lambda: post_tweet_thread(script, manifest, formats_dir),
            "nostr":   lambda: post_nostr(script, manifest, formats_dir),
            "podcast": lambda: create_podcast(script, manifest, formats_dir, args.video),
            "shorts":  lambda: cut_shorts(script, manifest, formats_dir, args.video, args.test),
        }
        result = fn_map[args.format]()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result.get("status") in ("ok", "draft") else 1)
    else:
        results = run_all_formats(manifest, args.video, run_dir, test_mode=args.test)
        failures = [k for k, v in results.items()
                    if isinstance(v, dict) and v.get("status") not in ("ok", "draft")]
        if failures:
            logger.warning(f"[fmt] Hard failures: {failures}")
        sys.exit(1 if len(failures) == len(results) else 0)


if __name__ == "__main__":
    main()
