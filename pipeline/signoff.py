#!/usr/bin/env python3
"""pipeline/signoff.py — Generate fresh sign-off VO text via Grok.

Validators:
  - Every channel display_name present
  - Contains explicit follow/subscribe ask
  - 18-28 words
  - No hashtags, no em dashes, no "we"/"our team" fluff
  - Jaccard word-set overlap < 0.6 with every entry in signoff_history.json

Usage:
    from pipeline.signoff import generate_signoff
    text = generate_signoff("Dollar Hegemony", ["Bitcoin Magazine", "The Bitcoin Layer", "BTC Sessions"], "seg_v2")
"""
import json
import os
import re
import sys
import datetime

sys.path.insert(0, "/home/ultron/protocol_pulse/video_pipeline_v3")
from relay import get_key

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "signoff_history.json")
REFERENCE_PATH = os.path.join(os.path.dirname(__file__), "signoff_reference.txt")

FOLLOW_PATTERNS = re.compile(
    r"\b(go follow|follow|subscribe to|check out|subscribe)\b", re.IGNORECASE
)


def _load_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return []


def _save_history(history):
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def _jaccard(a_text, b_text):
    a_words = set(a_text.lower().split())
    b_words = set(b_text.lower().split())
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / len(a_words | b_words)


def _load_reference():
    if os.path.exists(REFERENCE_PATH):
        with open(REFERENCE_PATH) as f:
            return f.read().strip()
    return ""


def validate_signoff(text, channel_names, history):
    """Validate a sign-off candidate. Returns (ok, reason)."""
    if not text:
        return False, "empty text"

    words = text.strip().split()
    word_count = len(words)

    # Word count: 18-28
    if word_count < 18:
        return False, f"too short: {word_count} words (min 18)"
    if word_count > 28:
        return False, f"too long: {word_count} words (max 28)"

    lower = text.lower()

    # Every channel name present
    for ch in channel_names:
        if ch.lower() not in lower:
            return False, f"missing channel '{ch}'"

    # Explicit follow/subscribe ask
    if not FOLLOW_PATTERNS.search(text):
        return False, "no follow/subscribe ask found"

    # No hashtags
    if "#" in text:
        return False, "contains hashtag"

    # No em dashes
    if "\u2014" in text or "—" in text:
        return False, "contains em dash"

    # No marketing fluff
    fluff = ["we ", "our team", "our show", "our channel"]
    for f in fluff:
        if f in lower:
            return False, f"contains fluff: '{f.strip()}'"

    # Jaccard overlap with history
    for entry in history:
        overlap = _jaccard(text, entry.get("text", ""))
        if overlap >= 0.6:
            return False, f"Jaccard overlap {overlap:.2f} >= 0.6 with '{entry.get('segment_id', '?')}'"

    return True, "valid"


def generate_signoff(topic, channel_names, segment_id, max_rounds=2):
    """Generate a fresh sign-off line via Grok. Returns the chosen text or raises."""
    import requests

    api_key = get_key("XAI_API_KEY_MEDLEY")
    reference = _load_reference()
    history = _load_history()

    prompt = f"""Generate exactly 3 sign-off lines for a Bitcoin news video segment.

Topic: {topic}
Channels to credit: {', '.join(channel_names)}

Reference style (do NOT copy verbatim — vary phrasing each time):
"{reference}"

Rules for EACH line:
- Thank/credit every channel by their EXACT display name: {', '.join(channel_names)}
- Include an explicit ask to follow or subscribe (e.g. "go follow", "follow", "subscribe to")
- 18-28 words exactly
- No hashtags, no em dashes (—), no "we"/"our team"/"our show" marketing fluff
- Natural, conversational tone
- Each line must be distinct in structure

Return ONLY 3 lines, one per line, numbered 1-3. No other text."""

    for round_num in range(max_rounds):
        print(f"  Signoff generation round {round_num + 1}/{max_rounds}")

        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "grok-3-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Parse numbered lines
        candidates = []
        for line in content.split("\n"):
            line = line.strip()
            # Strip leading numbers like "1." "2." "3."
            line = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            if line and len(line.split()) >= 10:
                candidates.append(line)

        for candidate in candidates:
            ok, reason = validate_signoff(candidate, channel_names, history)
            if ok:
                # Append to history
                history.append({
                    "text": candidate,
                    "segment_id": segment_id,
                    "date": datetime.date.today().isoformat(),
                    "topic": topic,
                })
                _save_history(history)
                print(f"  Signoff chosen: {candidate}")
                return candidate
            else:
                print(f"    Rejected: {reason} — '{candidate[:60]}...'")

    raise RuntimeError(f"STOP: no valid sign-off after {max_rounds} rounds")
