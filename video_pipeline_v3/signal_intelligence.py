"""
Signal Intelligence — cache-first architecture for Signal Active segment.

Reads from cache/active_signal.json (populated by fetch_signal_cache.py cron).
X Spaces quotes still read from local transcript cache.
Zero network calls in this module.

Standalone module, importable from assembler.py:
    from signal_intelligence import get_signal_content, generate_signal_summary
"""

import glob
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger("signal_intelligence")

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)
SPACES_CACHE = os.path.join(PROJECT_ROOT, "x_spaces_scraper", "cache")
NOSTR_CACHE = os.path.join(BASE, "cache", "active_signal.json")
X_POSTS_CACHE = os.path.join(PROJECT_ROOT, "data", "tweet_study", "raw_tweets.json")

# Max cache age before falling back (2 hours)
MAX_CACHE_AGE_SECONDS = 7200

# Keywords that indicate bitcoin-signal sentences
SIGNAL_KEYWORDS = re.compile(
    r"\b(bitcoin|btc|satoshi|mining|halving|halvening|hashrate|hash\s*rate|"
    r"etf|spot\s*etf|block\s*reward|difficulty\s*adjustment|mempool|"
    r"lightning\s*network|layer\s*2|taproot|ordinals|inscription|"
    r"hodl|sats|utxo|segwit|nostr|on[\s-]?chain|off[\s-]?chain|"
    r"proof[\s-]?of[\s-]?work|nakamoto|block\s*chain)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# UPGRADE 4: Quality fallback content
# ---------------------------------------------------------------------------

FALLBACK_CONTENT = {
    "spaces_quotes": [
        {
            "text": "The ETF inflows are rewriting the supply dynamics entirely. We have never seen this kind of sustained institutional demand for a scarce asset post-halving.",
            "space_title": "Bitcoin Macro Roundtable",
        },
        {
            "text": "Lightning adoption is accelerating faster than anyone predicted. Payment volume doubled this quarter and the network effects are compounding.",
            "space_title": "Layer 2 Builder Session",
        },
        {
            "text": "Hashrate keeps making new highs while difficulty adjustments compress miner margins. Only the most efficient operators survive this environment.",
            "space_title": "Mining Intelligence Weekly",
        },
    ],
    "nostr_posts": [
        {
            "text": "The mempool is clearing fast after the difficulty adjustment. Transaction fees dropping to single-digit sats per vbyte. Network health looking strong.",
            "pubkey": "npub1abc12345...def678",
            "display_name": "npub1abc1...def678",
        },
        {
            "text": "Watching the UTXO age distribution shift in real time. Long-term holders are not selling into this rally. Conviction is through the roof.",
            "pubkey": "npub1xyz98765...uvw432",
            "display_name": "npub1xyz9...uvw432",
        },
        {
            "text": "Bitcoin dominance pushing above 60 percent. Altcoins bleeding while BTC absorbs all the capital. The flippening is Bitcoin flippening everything else.",
            "pubkey": "npub1ghi55555...jkl999",
            "display_name": "npub1ghi5...jkl999",
        },
    ],
}


# ---------------------------------------------------------------------------
# 1. X Spaces transcript extraction (unchanged — reads local cache)
# ---------------------------------------------------------------------------

def _score_sentence(sentence: str) -> int:
    """Score a sentence by how many distinct signal keywords it contains."""
    hits = set()
    for m in SIGNAL_KEYWORDS.finditer(sentence):
        hits.add(m.group(0).lower())
    word_count = len(sentence.split())
    if word_count < 6:
        return 0
    return len(hits) * 10 + min(word_count, 30)


def _extract_spaces_quotes(max_quotes: int = 3) -> list[dict]:
    """Read transcript JSONs from x_spaces_scraper cache, return top signal sentences."""
    quotes = []
    if not os.path.isdir(SPACES_CACHE):
        log.warning("Spaces cache dir not found: %s", SPACES_CACHE)
        return []

    cutoff = time.time() - 72 * 3600

    transcript_files = glob.glob(os.path.join(SPACES_CACHE, "transcript_*.json"))
    if not transcript_files:
        log.info("No transcript files found in %s", SPACES_CACHE)
        return []

    candidates = []
    for fpath in transcript_files:
        try:
            if os.path.getmtime(fpath) < cutoff:
                continue
            with open(fpath) as f:
                data = json.load(f)

            if not data.get("usable", False):
                continue

            space_id = data.get("space_id", os.path.basename(fpath))
            space_title = data.get("space_title") or data.get("title") or f"Space {space_id}"

            sentences = []
            segments = data.get("segments", [])
            if segments:
                for seg in segments:
                    text = seg.get("text", "").strip()
                    if text:
                        sentences.append(text)
            else:
                full = data.get("full_transcript") or data.get("transcript", "")
                if full:
                    sentences = re.split(r"[.!?]+", full)

            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                score = _score_sentence(sent)
                if score > 0:
                    candidates.append({
                        "text": sent,
                        "space_title": space_title,
                        "score": score,
                    })
        except Exception as e:
            log.debug("Failed to parse %s: %s", fpath, e)
            continue

    candidates.sort(key=lambda x: x["score"], reverse=True)

    seen_texts = set()
    for c in candidates:
        normalized = c["text"].lower().strip()
        if normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        quotes.append({"text": c["text"], "space_title": c["space_title"]})
        if len(quotes) >= max_quotes:
            break

    log.info("Extracted %d spaces quotes from %d candidates", len(quotes), len(candidates))
    return quotes


# ---------------------------------------------------------------------------
# 2. Nostr — CACHE-FIRST (no network calls)
# ---------------------------------------------------------------------------

def _read_nostr_cache(max_posts: int = 3) -> list[dict]:
    """Read Nostr posts from cache/active_signal.json. Zero network calls."""
    if not os.path.exists(NOSTR_CACHE):
        log.warning("Nostr cache not found: %s", NOSTR_CACHE)
        return []

    try:
        with open(NOSTR_CACHE) as f:
            data = json.load(f)
    except Exception as e:
        log.error("Failed to read nostr cache: %s", e)
        return []

    fetched_at = data.get("fetched_at", 0)
    age = time.time() - fetched_at

    if age > MAX_CACHE_AGE_SECONDS:
        log.warning("Nostr cache stale: %.0fs old (max %ds)", age, MAX_CACHE_AGE_SECONDS)
        return []

    posts = data.get("nostr_posts", [])
    results = []
    for p in posts[:max_posts]:
        results.append({
            "text": p.get("text", ""),
            "pubkey": p.get("pubkey", ""),
            "display_name": p.get("display_name", ""),
            "score": p.get("score", 0),
            "has_zap": p.get("has_zap", False),
        })

    log.info("Read %d nostr posts from cache (%.0fs old)", len(results), age)
    return results


# ---------------------------------------------------------------------------
# 2b. X Posts — from tweet_study/raw_tweets.json (populated by tweet scraper)
# ---------------------------------------------------------------------------

def _read_x_posts(max_posts: int = 3) -> list[dict]:
    """Read top X posts from raw_tweets.json. Selects recent, high-engagement Bitcoin tweets."""
    if not os.path.exists(X_POSTS_CACHE):
        log.warning("X posts cache not found: %s", X_POSTS_CACHE)
        return []

    try:
        with open(X_POSTS_CACHE) as f:
            tweets = json.load(f)
    except Exception as e:
        log.error("Failed to read X posts cache: %s", e)
        return []

    if not isinstance(tweets, list) or not tweets:
        return []

    # Only tweets from last 48 hours
    cutoff = datetime.utcnow() - timedelta(hours=48)
    recent = []
    for t in tweets:
        try:
            created = t.get("created_at", "")
            if created:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                if dt < cutoff:
                    continue
        except (ValueError, TypeError):
            continue

        text = t.get("text", "").strip()
        if not text or len(text) < 40:
            continue
        # Skip link-only tweets
        if text.startswith("http") or text.count("http") > 1:
            continue

        engagement = (t.get("likes", 0) + t.get("retweets", 0) * 2
                      + t.get("replies", 0) + t.get("quotes", 0) * 2)
        recent.append({
            "text": text,
            "handle": t.get("handle", ""),
            "engagement": engagement,
            "created_at": t.get("created_at", ""),
        })

    # Sort by engagement, take top N
    recent.sort(key=lambda x: x["engagement"], reverse=True)
    results = recent[:max_posts]
    log.info("Read %d X posts from cache (%d recent candidates)", len(results), len(recent))
    return results


# ---------------------------------------------------------------------------
# 3. Main entry point
# ---------------------------------------------------------------------------

def get_signal_content() -> dict:
    """
    Gather signal content from X Spaces transcripts (local), Nostr cache, and X posts.
    Zero network calls — all data from local files.

    Returns:
        {
            "spaces_quotes": [{"text": str, "space_title": str}, ...],
            "nostr_posts": [{"text": str, "pubkey": str, "display_name": str}, ...],
            "x_posts": [{"text": str, "handle": str, "engagement": int}, ...],
        }
    """
    spaces_quotes = []
    nostr_posts = []
    x_posts = []

    try:
        spaces_quotes = _extract_spaces_quotes(max_quotes=3)
    except Exception as e:
        log.error("Spaces extraction failed: %s", e)

    try:
        nostr_posts = _read_nostr_cache(max_posts=3)
    except Exception as e:
        log.error("Nostr cache read failed: %s", e)

    try:
        x_posts = _read_x_posts(max_posts=3)
    except Exception as e:
        log.error("X posts read failed: %s", e)

    # FIX 7: NEVER use fabricated space titles. If no real spaces data,
    # return empty list so the renderer shows "NO LIVE SPACES DETECTED" placeholder.
    if not spaces_quotes:
        log.info("No real X Spaces data — returning empty (no fabricated content)")
    if not nostr_posts:
        nostr_posts = FALLBACK_CONTENT["nostr_posts"]
        log.info("No nostr data — using fallback nostr content")

    return {
        "spaces_quotes": spaces_quotes,  # may be empty — renderer handles this
        "nostr_posts": nostr_posts,
        "x_posts": x_posts,  # top engagement X posts from tracked accounts
    }


# ---------------------------------------------------------------------------
# 4. LLM summary generation — UPGRADE 3: Field Reporter narration
# ---------------------------------------------------------------------------

FALLBACK_SUMMARY = (
    "Signal hot. Bitcoin ETF inflows surging while hashrate pushes all-time highs. "
    "Nostr zaps flowing to new layer-2 builds. X Spaces lit up with supply shock analysis. "
    "Exodus from fiat accelerating. The network does not sleep."
)


def _build_content_fallback(content: dict) -> str:
    """V4.2 FIX 6: Build fallback narration from actual displayed content.

    Prevents visual/audio mismatch — narration always references what's on screen.
    """
    spaces = content.get("spaces_quotes", [])
    nostr = content.get("nostr_posts", [])
    parts = ["Signal incoming."]
    if spaces:
        titles = [q.get("space_title", "X Spaces") for q in spaces[:2]]
        parts.append(f"X Spaces lighting up — {titles[0]} has the signal.")
    if nostr:
        names = [p.get("display_name", "Nostr") for p in nostr[:2] if p.get("display_name")]
        if names:
            parts.append(f"Nostr relays active. {names[0]} broadcasting.")
        else:
            parts.append("Nostr relays active. Sovereign signal flowing.")
    parts.append("The network does not sleep.")
    return " ".join(parts)


def generate_signal_summary(content: dict) -> str:
    """
    Use Claude Haiku via relay.call_llm to produce a ~20-second field reporter narration.
    V4.2 FIX 6: Falls back to content-derived summary instead of generic FALLBACK_SUMMARY,
    ensuring narration always matches the displayed X Spaces / Nostr content.
    """
    spaces = content.get("spaces_quotes", [])
    nostr = content.get("nostr_posts", [])
    x_posts = content.get("x_posts", [])

    if not spaces and not nostr and not x_posts:
        return FALLBACK_SUMMARY

    # Build context block
    lines = []
    if spaces:
        lines.append("=== X SPACES QUOTES ===")
        for i, q in enumerate(spaces, 1):
            lines.append(f"{i}. [{q.get('space_title', 'Unknown')}] \"{q['text']}\"")
    if x_posts:
        lines.append("\n=== X POSTS ===")
        for i, xp in enumerate(x_posts, 1):
            handle = xp.get("handle", "unknown")
            lines.append(f"{i}. [@{handle}] \"{xp['text'][:200]}\"")
    if nostr:
        lines.append("\n=== NOSTR POSTS ===")
        for i, p in enumerate(nostr, 1):
            name = p.get("display_name") or p.get("pubkey", "")[:12]
            lines.append(f"{i}. [{name}] \"{p['text']}\"")

    context_block = "\n".join(lines)

    prompt = (
        "You are PBX, Bitcoin field reporter for Protocol Pulse. "
        "Write 45-word breaking-news narration. Urgent and direct. "
        "Reference speakers by name when available. Short punchy sentences. "
        "No filler. End on insight not CTA. "
        "Example: Signal hot. Preston Pysh flagging supply shock on X Spaces. "
        "Nostr zaps flowing to new layer-2. Exodus from fiat accelerating. "
        "Write ONLY the narration.\n\n"
        f"{context_block}\n\n"
        "Write ONLY the narration."
    )

    try:
        from relay import call_llm
        result = call_llm(prompt, max_tokens=200, temperature=0.4)
        if result and len(result.strip()) > 20:
            return result.strip()
        log.warning("LLM returned empty or too-short response, using content fallback")
    except ImportError:
        log.warning("relay module not available, using content fallback summary")
    except Exception as e:
        log.error("LLM call failed: %s", e)

    # V4.2 FIX 6: Use content-derived fallback — matches displayed X Spaces / Nostr data
    return _build_content_fallback(content)


# ---------------------------------------------------------------------------
# 5. CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    print("=" * 60)
    print("Signal Intelligence — Cache-First Test Run")
    print("=" * 60)

    content = get_signal_content()

    print(f"\n--- Spaces Quotes ({len(content['spaces_quotes'])}) ---")
    for q in content["spaces_quotes"]:
        print(f"  [{q['space_title']}] {q['text'][:120]}...")

    print(f"\n--- Nostr Posts ({len(content['nostr_posts'])}) ---")
    for p in content["nostr_posts"]:
        name = p.get("display_name") or p.get("pubkey", "")[:12]
        print(f"  [{name}] {p['text'][:120]}...")

    print("\n--- Signal Summary ---")
    summary = generate_signal_summary(content)
    print(f"  {summary}")

    print("\n" + "=" * 60)
    print("Done.")
