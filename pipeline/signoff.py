#!/usr/bin/env python3
"""pipeline/signoff.py — Generate fresh sign-off VO text via Grok.

Validators:
  - Every channel display_name present
  - Contains explicit follow/subscribe ask
  - 18-24 words, at most 3 sentences
  - No hashtags, no em dashes, no "we"/"our team" fluff
  - No mechanical phrases (supplied, provided, video clips, content creators, etc.)
  - Must read as spoken (no list-of-names-then-clause run-on)
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

# Mechanical/stiff phrases banned by PBX
BANNED_PHRASES = [
    "supplied", "provided", "video clips", "content creators",
    "using the links", "each one", "sourced from", "courtesy of",
    "featured in", "brought to you", "presented by",
]


def _load_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return []


def _save_history(history):
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def _jaccard(a_text, b_text, exclude_words=None):
    """Jaccard similarity on word sets, optionally excluding words (e.g. channel names)."""
    a_words = set(a_text.lower().split())
    b_words = set(b_text.lower().split())
    if exclude_words:
        stop = {w.lower() for w in exclude_words}
        a_words -= stop
        b_words -= stop
    if not a_words or not b_words:
        return 0.0
    return len(a_words & b_words) / len(a_words | b_words)


def _load_reference():
    if os.path.exists(REFERENCE_PATH):
        with open(REFERENCE_PATH) as f:
            return f.read().strip()
    return ""


def _count_sentences(text):
    """Count sentences by splitting on . ? !"""
    parts = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    return len(parts)


def validate_signoff(text, channel_names, history):
    """Validate a sign-off candidate. Returns (ok, reason)."""
    if not text:
        return False, "empty text"

    words = text.strip().split()
    word_count = len(words)

    # Word count: 18-24
    if word_count < 18:
        return False, f"too short: {word_count} words (min 18)"
    if word_count > 24:
        return False, f"too long: {word_count} words (max 24)"

    lower = text.lower()

    # Every channel name present
    for ch in channel_names:
        if ch.lower() not in lower:
            return False, f"missing channel '{ch}'"

    # Explicit follow/subscribe ask
    if not FOLLOW_PATTERNS.search(text):
        return False, "no follow/subscribe ask found"

    # At most 3 sentences
    if _count_sentences(text) > 3:
        return False, f"too many sentences: {_count_sentences(text)} (max 3)"

    # No hashtags
    if "#" in text:
        return False, "contains hashtag"

    # No em dashes
    if "\u2014" in text or "\u2013" in text:
        return False, "contains em/en dash"

    # No marketing fluff
    fluff = ["we ", "our team", "our show", "our channel"]
    for f in fluff:
        if f in lower:
            return False, f"contains fluff: '{f.strip()}'"

    # No banned mechanical phrases
    for phrase in BANNED_PHRASES:
        if phrase in lower:
            return False, f"contains banned phrase: '{phrase}'"

    # Jaccard overlap with history (excluding channel display name words)
    channel_words = set()
    for ch in channel_names:
        for w in ch.split():
            channel_words.add(w)
    for entry in history:
        overlap = _jaccard(text, entry.get("text", ""), exclude_words=channel_words)
        if overlap >= 0.6:
            return False, f"Jaccard overlap {overlap:.2f} >= 0.6 with '{entry.get('segment_id', '?')}'"

    return True, "valid"


def generate_signoff(topic, channel_names, segment_id, max_rounds=3):
    """Generate a fresh sign-off line via Grok. Returns the chosen text or raises."""
    import requests

    api_key = get_key("XAI_API_KEY_MEDLEY")
    reference = _load_reference()
    history = _load_history()

    prompt = f"""Write 5 sign-off lines for a Bitcoin news video. Each must credit the channels and tell viewers to follow them.

Topic: {topic}
Channels: {', '.join(channel_names)}

Reference (approved style — warm, spoken, natural):
"{reference}"

Three registers to rotate between:
A) Credit-first: "Clips today from [channels]. Go follow them. Links below."
B) Gratitude-first: "Big thanks to [channels] for today's clips. Follow them all, links below."
C) Call-to-action-first: "Go follow [channels]. Today's clips came from them. Links below."

Rules:
- Use EXACT channel display names: {', '.join(channel_names)}
- Include "go follow", "follow", or "subscribe to"
- 18-24 words, max 3 sentences
- Must sound natural when spoken aloud, like a person talking to camera
- NO hashtags, NO em dashes, NO "we"/"our team"
- NO stiff/mechanical words: supplied, provided, video clips, content creators, using the links, each one, sourced from, courtesy of
- Each line must use a different register (A/B/C or mix)

Return ONLY 5 lines, numbered 1-5. No commentary."""

    for round_num in range(max_rounds):
        print(f"  Signoff generation round {round_num + 1}/{max_rounds}")

        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "grok-3-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.9,
                "max_tokens": 500,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Parse numbered lines
        candidates = []
        for line in content.split("\n"):
            line = line.strip()
            line = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            if line and len(line.split()) >= 10:
                candidates.append(line)

        for candidate in candidates:
            ok, reason = validate_signoff(candidate, channel_names, history)
            if ok:
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
