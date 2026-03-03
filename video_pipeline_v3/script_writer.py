#!/usr/bin/env python3
"""Script Writer V5 — generates host dialogue AROUND real YouTube clips.

Takes the 5 clips selected by clip_selector and generates:
- Cold open teasing clip #1
- Setup → Clip → React dialogue for each clip
- Wrap-up and sign-off

Host dialogue supports the clips, not the other way around.
"""
import json
import logging
import os
import sys

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from relay import get_key

logger = logging.getLogger("ScriptWriter")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[script] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SCRIPT_PROMPT = """You are the head writer for "Pulse Check" — a daily 3-5 minute Bitcoin highlight reel.
Two hosts (Jessica & Chris) present and react to 5 real YouTube clips from Bitcoin channels.
Think ESPN SportsCenter for Bitcoin.

HOST 1 (Jessica) — The anchor. Sharp, data-driven, sets up stories with authority.
HOST 2 (Chris) — The co-host. Reacts naturally, asks follow-ups, drops hot takes.

The clips have ALREADY been selected. Your job is to write the dialogue AROUND them.
The clips play at full screen with their ORIGINAL audio. Your dialogue introduces and reacts to each.

EPISODE STRUCTURE:
1. COLD OPEN — Jessica teases the #1 clip (most dramatic). Hook the viewer. 1 sentence max.
2. For each of the 5 clips:
   a. SETUP — Host introduces what we're about to see (1-2 sentences)
   b. [CLIP PLAYS — you mark this with a CLIP entry]
   c. REACT — Hosts discuss what we just saw (2-4 sentences of banter)
3. WRAP — Final thoughts, "Stay sovereign."

Style rules:
- CASUAL BANTER. Not news anchors. Two smart friends at a bar.
- Short sentences. Conversational. Interruptions. Reactions.
- Real opinions and hot takes — not neutral reporting.
- Natural transitions between clips
- Reference the ACTUAL QUOTES from the clips. React to SPECIFIC things said.
- NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
- End with "Stay sovereign."

BTC Price: {btc_price}

THE 5 SELECTED CLIPS:
{clips_info}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "cold_open": "Jessica's cold open teaser (1 sentence, dramatic)",
  "dialogue": [
    {{"host": 1, "text": "Jessica's cold open line", "type": "cold_open"}},
    {{"host": 1, "text": "Setup for clip 1", "type": "setup", "clip_rank": 1}},
    {{"host": "CLIP", "rank": 1}},
    {{"host": 2, "text": "Chris reacts to clip 1", "type": "react", "clip_rank": 1}},
    {{"host": 1, "text": "Jessica adds to reaction", "type": "react", "clip_rank": 1}},
    {{"host": 1, "text": "Setup for clip 2", "type": "setup", "clip_rank": 2}},
    {{"host": "CLIP", "rank": 2}},
    ...and so on for all 5 clips...
    {{"host": 1, "text": "Final wrap-up line. Stay sovereign.", "type": "wrap"}}
  ],
  "episode_title": "Short punchy title (5-8 words)",
  "thumbnail": {{
    "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
    "subtext": "secondary line"
  }},
  "segments_summary": ["headline for each clip topic"],
  "shorts_quotes": ["3 best one-liner quotes from the host dialogue for vertical shorts"]
}}

IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5).
Keep host dialogue SHORT. The show is the clips, not the commentary."""


def _format_clips_info(selections: dict) -> str:
    """Format clip selections for the script prompt."""
    clips = selections.get("clips", [])
    parts = []
    for c in clips:
        parts.append(
            f"CLIP #{c['rank']}:\n"
            f"  Channel: {c.get('channel', 'Unknown')}\n"
            f"  Video: {c.get('video_title', 'Untitled')}\n"
            f"  Quote: \"{c.get('quote', '')}\"\n"
            f"  Why selected: {c.get('why', '')}\n"
            f"  Suggested setup: {c.get('host_setup', '')}\n"
            f"  Suggested reaction: {c.get('host_react', '')}\n"
        )
    return "\n".join(parts)


def generate_from_clips(selections: dict, btc_price: str = "N/A") -> dict:
    """Generate host dialogue script around the selected clips.

    Args:
        selections: Output from clip_selector.select_clips()
        btc_price: Current BTC price string

    Returns:
        Script dict with dialogue array
    """
    clips = selections.get("clips", [])
    if not clips:
        logger.error("No clips provided for script generation")
        return _fallback_script(selections)

    key = get_key("ANTHROPIC_API_KEY")
    if not key or not HAS_ANTHROPIC:
        logger.warning("Anthropic API not available, using fallback script")
        return _fallback_script(selections)

    clips_info = _format_clips_info(selections)
    prompt = SCRIPT_PROMPT.format(clips_info=clips_info, btc_price=btc_price)

    logger.info(f"Generating script for {len(clips)} clips...")
    client = anthropic.Anthropic(api_key=key)

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text)

        # Validate structure
        dialogue = result.get("dialogue", [])
        clip_entries = [d for d in dialogue if d.get("host") == "CLIP"]
        speech_entries = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]

        logger.info(f"Script generated: {len(dialogue)} entries "
                    f"({len(speech_entries)} speech, {len(clip_entries)} clips)")
        logger.info(f"Title: {result.get('episode_title', 'Untitled')}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return _fallback_script(selections)
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return _fallback_script(selections)


def _fallback_script(selections: dict) -> dict:
    """Generate a basic script from clip selections without Claude."""
    clips = selections.get("clips", [])
    cold_open = selections.get("cold_open", "Breaking developments in Bitcoin today.")

    dialogue = [
        {"host": 1, "text": cold_open, "type": "cold_open"},
    ]

    for c in clips:
        rank = c.get("rank", 0)
        setup = c.get("host_setup", f"Check out what {c.get('channel', 'this channel')} just dropped.")
        react = c.get("host_react", "That's a big deal. The market hasn't priced this in yet.")

        dialogue.append({"host": 1, "text": setup, "type": "setup", "clip_rank": rank})
        dialogue.append({"host": "CLIP", "rank": rank})
        dialogue.append({"host": 2, "text": react, "type": "react", "clip_rank": rank})

    dialogue.append({
        "host": 1,
        "text": "That's your Pulse Check for today. Stay sovereign.",
        "type": "wrap",
    })

    title = selections.get("episode_title", "Pulse Check Daily")

    return {
        "cold_open": cold_open,
        "dialogue": dialogue,
        "episode_title": title,
        "thumbnail": {"headline": title.upper(), "subtext": "Daily Bitcoin Intelligence"},
        "segments_summary": [c.get("why", "") for c in clips],
        "shorts_quotes": [c.get("quote", "")[:80] for c in clips[:3]],
    }


# Legacy compatibility
def generate_script(stories=None, style="default", btc_price="N/A"):
    """Legacy wrapper — generate a sample script for testing."""
    logger.info("Legacy generate_script called — use generate_from_clips for V5 pipeline")
    return generate_sample_script(style)


def generate_sample_script(style="default"):
    """Sample script for testing without live data."""
    return {
        "episode_title": "The Quiet Accumulation",
        "cold_open": "Three sovereign wealth funds just disclosed Bitcoin positions worth twelve billion dollars.",
        "dialogue": [
            {"host": 1, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},
            {"host": 1, "text": "Bitcoin Magazine just dropped this bombshell.", "type": "setup", "clip_rank": 1},
            {"host": "CLIP", "rank": 1},
            {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything.", "type": "react", "clip_rank": 1},
            {"host": 1, "text": "And look at what Simply Bitcoin is reporting on hash rate.", "type": "setup", "clip_rank": 2},
            {"host": "CLIP", "rank": 2},
            {"host": 2, "text": "Record high hash rate. Miners aren't leaving. They're doubling down.", "type": "react", "clip_rank": 2},
            {"host": 1, "text": "That's your Pulse Check. Stay sovereign.", "type": "wrap"},
        ],
        "thumbnail": {"headline": "SMART MONEY IS MOVING", "subtext": "Nations are stacking"},
        "segments_summary": ["Sovereign wealth funds buying BTC", "Hash rate hits record"],
        "shorts_quotes": ["When the entities that print fiat start hoarding the exit asset", "Miners aren't leaving"],
    }


if __name__ == "__main__":
    script = generate_sample_script()
    print(json.dumps(script, indent=2))
