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

SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.

HOST 1 (Jessica) — Sharp, fast, no-fluff. Sets up each clip like a boxing ring announcer.
HOST 2 (Chris) — Hot takes, contrarian, dry wit. Reacts like he just saw a knockout.

TONE RULES (NON-NEGOTIABLE):
- NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
- SETUP lines = 1-2 sentences MAX. A teaser, not a summary. Leave them wanting the clip.
- REACT lines = 1-2 sentences MAX. A hot take or one sharp observation. Not a recap.
- Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
- Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
- Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
- Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
- NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
- End with "Stay sovereign."

DELIVERY RULES:
- ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
- The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
- React lines start with a reaction word: "Yeah.", "Exactly.", "Wild.", "That's the tell.", "100%.", "I mean—"
- Tone = investigative gossip journalist who happens to understand Austrian economics.
- Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
- Max 2 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.

SOCIAL SEGMENT:
If social posts data is provided below, add a "WHAT THE BITCOIN INTERNET IS SAYING" segment after the last clip:
- Jessica reads 2-3 of the top tweets provided (sharp, brief, 1 line each)
- Chris drops a one-liner reaction to the best one
- This is a separate section in the dialogue with type: "social_segment"
CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.

{clips_info}

BTC Price Today: {btc_price}
Top Tweets/Nostr Posts Today: {social_posts}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "cold_open": "explosive 1-sentence cold open",
  "dialogue": [
    {{"host": 1, "text": "...", "type": "cold_open"}},
    {{"host": 1, "text": "...", "type": "setup", "clip_rank": 1}},
    {{"host": "CLIP", "rank": 1}},
    {{"host": 2, "text": "...", "type": "react", "clip_rank": 1}},
    {{"host": 1, "text": "...", "type": "setup", "clip_rank": 2}},
    {{"host": "CLIP", "rank": 2}},
    {{"host": 2, "text": "...", "type": "react", "clip_rank": 2}},
    ...and so on for all clips...
    {{"host": 1, "text": "...", "type": "social_segment"}},
    {{"host": 2, "text": "...", "type": "social_segment"}},
    {{"host": 1, "text": "Final wrap. Stay sovereign.", "type": "wrap"}}
  ],
  "episode_title": "Short punchy title (5-8 words)",
  "thumbnail": {{
    "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
    "subtext": "secondary line"
  }},
  "segments_summary": ["headline for each clip topic"],
  "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
}}

IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5)."""


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

    # Real social data — per Law A1, never fabricate
    try:
        from utils.social_fetcher import get_todays_social_posts
        social_data = get_todays_social_posts(max_posts=5)
        if social_data:
            social_posts = "\n".join([
                f"@{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
                for p in social_data
            ])
        else:
            social_posts = "NONE — skip social segment entirely"
    except Exception as e:
        logger.warning(f"Social data fetch failed: {e}")
        social_posts = "NONE — skip social segment entirely"

    prompt = SCRIPT_PROMPT.format(clips_info=clips_info, btc_price=btc_price, social_posts=social_posts)

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
