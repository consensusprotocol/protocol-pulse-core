"""
Signal Intelligence — pulls bitcoin signal from X Spaces transcripts and Nostr relays.

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
SPACES_CACHE = os.path.join(os.path.dirname(BASE), "x_spaces_scraper", "cache")

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
# 1. X Spaces transcript extraction
# ---------------------------------------------------------------------------

def _score_sentence(sentence: str) -> int:
    """Score a sentence by how many distinct signal keywords it contains."""
    hits = set()
    for m in SIGNAL_KEYWORDS.finditer(sentence):
        hits.add(m.group(0).lower())
    # Bonus for longer, more substantive sentences
    word_count = len(sentence.split())
    if word_count < 6:
        return 0  # skip very short fragments
    return len(hits) * 10 + min(word_count, 30)


def _extract_spaces_quotes(max_quotes: int = 3) -> list[dict]:
    """Read transcript JSONs from x_spaces_scraper cache, return top signal sentences."""
    quotes = []
    if not os.path.isdir(SPACES_CACHE):
        log.warning("Spaces cache dir not found: %s", SPACES_CACHE)
        return []

    cutoff = time.time() - 72 * 3600  # look back 72h for enough material

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

            # Extract sentences from segments (preferred) or full transcript
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
# 2. Nostr relay fetching
# ---------------------------------------------------------------------------

NOSTR_RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
]


def _fetch_nostr_posts(max_posts: int = 3, timeout: int = 10) -> list[dict]:
    """Pull recent kind-1 notes tagged #t bitcoin from Nostr relays."""
    try:
        import websocket
    except ImportError:
        log.warning("websocket-client not installed, skipping Nostr fetch")
        return []

    since = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
    subscription_id = f"signal_{int(time.time())}"

    req_msg = json.dumps([
        "REQ",
        subscription_id,
        {
            "kinds": [1],
            "#t": ["bitcoin", "btc", "Bitcoin", "BTC"],
            "since": since,
            "limit": 50,
        },
    ])

    all_events = []

    for relay_url in NOSTR_RELAYS:
        try:
            ws = websocket.WebSocket()
            ws.settimeout(timeout)
            ws.connect(relay_url)
            ws.send(req_msg)

            while True:
                try:
                    raw = ws.recv()
                    if not raw:
                        break
                    msg = json.loads(raw)
                    if not isinstance(msg, list):
                        continue

                    if msg[0] == "EVENT" and len(msg) >= 3:
                        event = msg[2]
                        content = event.get("content", "").strip()
                        pubkey = event.get("pubkey", "")
                        created_at = event.get("created_at", 0)

                        # Skip very short or very long posts
                        if len(content) < 20 or len(content) > 1000:
                            continue
                        # Skip posts that are just URLs
                        if content.startswith("http") and " " not in content:
                            continue

                        all_events.append({
                            "text": content,
                            "pubkey": pubkey,
                            "created_at": created_at,
                            "relay": relay_url,
                        })

                    elif msg[0] == "EOSE":
                        break

                except websocket.WebSocketTimeoutException:
                    log.debug("Timeout reading from %s", relay_url)
                    break
                except Exception as e:
                    log.debug("Error reading from %s: %s", relay_url, e)
                    break

            # Close subscription and connection
            try:
                ws.send(json.dumps(["CLOSE", subscription_id]))
            except Exception:
                pass
            ws.close()

        except Exception as e:
            log.warning("Failed to connect to %s: %s", relay_url, e)
            continue

    # Deduplicate by content hash, sort by recency
    seen = set()
    unique = []
    for ev in all_events:
        key = ev["text"][:100]
        if key in seen:
            continue
        seen.add(key)
        unique.append(ev)

    unique.sort(key=lambda x: x.get("created_at", 0), reverse=True)

    results = []
    for ev in unique[:max_posts]:
        results.append({
            "text": ev["text"],
            "pubkey": ev["pubkey"],
        })

    log.info("Fetched %d nostr posts from %d relays (%d raw events)",
             len(results), len(NOSTR_RELAYS), len(all_events))
    return results


# ---------------------------------------------------------------------------
# 3. Main entry point
# ---------------------------------------------------------------------------

def get_signal_content() -> dict:
    """
    Gather signal content from X Spaces transcripts and Nostr relays.

    Returns:
        {
            "spaces_quotes": [{"text": str, "space_title": str}, ...],
            "nostr_posts": [{"text": str, "pubkey": str}, ...],
        }
    """
    spaces_quotes = []
    nostr_posts = []

    try:
        spaces_quotes = _extract_spaces_quotes(max_quotes=3)
    except Exception as e:
        log.error("Spaces extraction failed: %s", e)

    try:
        nostr_posts = _fetch_nostr_posts(max_posts=3)
    except Exception as e:
        log.error("Nostr fetch failed: %s", e)

    return {
        "spaces_quotes": spaces_quotes,
        "nostr_posts": nostr_posts,
    }


# ---------------------------------------------------------------------------
# 4. LLM summary generation
# ---------------------------------------------------------------------------

FALLBACK_SUMMARY = (
    "The bitcoin community is buzzing today. Across X Spaces and Nostr, "
    "conversations are focused on price action, mining dynamics, and network "
    "fundamentals. The signal is clear: bitcoin remains the center of gravity "
    "for the entire digital asset ecosystem."
)


def generate_signal_summary(content: dict) -> str:
    """
    Use Claude Haiku via relay.call_llm to produce a ~20-second narration
    summarizing the signal content.

    Falls back to a hardcoded summary if LLM is unavailable.
    """
    spaces = content.get("spaces_quotes", [])
    nostr = content.get("nostr_posts", [])

    if not spaces and not nostr:
        return FALLBACK_SUMMARY

    # Build context block
    lines = []
    if spaces:
        lines.append("=== X SPACES QUOTES ===")
        for i, q in enumerate(spaces, 1):
            lines.append(f"{i}. [{q.get('space_title', 'Unknown')}] \"{q['text']}\"")
    if nostr:
        lines.append("\n=== NOSTR POSTS ===")
        for i, p in enumerate(nostr, 1):
            short_pk = p.get("pubkey", "")[:12]
            lines.append(f"{i}. [npub {short_pk}...] \"{p['text']}\"")

    context_block = "\n".join(lines)

    prompt = (
        "You are a bitcoin news narrator for Protocol Pulse, a daily video briefing. "
        "Given these real-time signal excerpts from X Spaces and Nostr, write a single "
        "paragraph narration (~50 words, about 20 seconds when read aloud). "
        "Be factual, confident, and concise. No hype. No emojis. No hashtags. "
        "Reference the sources naturally (e.g. 'across X Spaces today...' or "
        "'Nostr contributors are noting...'). Focus on the strongest signal.\n\n"
        f"{context_block}\n\n"
        "Write ONLY the narration paragraph, nothing else."
    )

    try:
        from relay import call_llm
        result = call_llm(prompt, max_tokens=200, temperature=0.4)
        if result and len(result.strip()) > 20:
            return result.strip()
        log.warning("LLM returned empty or too-short response, using fallback")
    except ImportError:
        log.warning("relay module not available, using fallback summary")
    except Exception as e:
        log.error("LLM call failed: %s", e)

    return FALLBACK_SUMMARY


# ---------------------------------------------------------------------------
# 5. CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    print("=" * 60)
    print("Signal Intelligence — Test Run")
    print("=" * 60)

    content = get_signal_content()

    print(f"\n--- Spaces Quotes ({len(content['spaces_quotes'])}) ---")
    for q in content["spaces_quotes"]:
        print(f"  [{q['space_title']}] {q['text'][:120]}...")

    print(f"\n--- Nostr Posts ({len(content['nostr_posts'])}) ---")
    for p in content["nostr_posts"]:
        pk = p["pubkey"][:12] if p["pubkey"] else "?"
        print(f"  [npub {pk}...] {p['text'][:120]}...")

    print("\n--- Signal Summary ---")
    summary = generate_signal_summary(content)
    print(f"  {summary}")

    print("\n" + "=" * 60)
    print("Done.")
