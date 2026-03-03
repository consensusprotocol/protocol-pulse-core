#!/usr/bin/env python3
"""Clip Selector — uses Claude to pick the 5 best moments from transcribed videos.

Analyzes all transcripts and selects timestamp ranges for the most compelling
clips, along with host setup/reaction dialogue suggestions.
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

logger = logging.getLogger("ClipSelector")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[selector] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SELECTION_PROMPT = """You are the executive producer of "Pulse Check" — a daily 3-5 minute Bitcoin highlight reel.
Two hosts (Jessica & Chris) present and react to the BEST clips from Bitcoin YouTube that day.
Think ESPN SportsCenter for Bitcoin.

Your job: analyze these transcripts from today's Bitcoin YouTube videos and pick the 5 BEST moments.

SELECTION CRITERIA (in order of priority):
1. BREAKING NEWS — first reports of major developments (ETF flows, regulatory, corporate buys)
2. HOT TAKES — strong, quotable opinions from respected voices
3. DATA DROPS — specific numbers, charts, on-chain metrics being discussed
4. QUOTABLE — moments where someone says something memorable and punchy
5. VISUAL — prefer clips where someone is on camera talking (not just voice-over slides)

RULES:
- Pick from DIFFERENT channels when possible (variety matters)
- Each clip should be 20-40 seconds long. The best moment, not the full segment.
- Rank 1 = most dramatic/important (this becomes the cold open teaser)
- The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
- Avoid dead air, filler words, or mid-sentence cuts

AVAILABLE VIDEOS:
{transcripts}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "clips": [
    {{
      "rank": 1,
      "video_id": "abc123",
      "channel": "Bitcoin Magazine",
      "video_title": "Original video title",
      "start_seconds": 145,
      "end_seconds": 175,
      "quote": "The exact memorable quote from this moment",
      "why": "Why this clip is compelling (1 sentence)",
      "host_setup": "What Jessica should say to introduce this clip (1-2 sentences, conversational)",
      "host_react": "What the hosts should discuss after this clip (2-3 sentences of banter)"
    }}
  ],
  "episode_title": "Short punchy episode title based on top clip (5-8 words)",
  "cold_open": "Jessica's cold open teaser line about clip #1 — dramatic, hook the viewer (1 sentence)"
}}

Return exactly 5 clips, ranked 1-5. If fewer than 5 good moments exist, return what you can."""


def _format_transcripts(videos: list) -> str:
    """Format video transcripts for the Claude prompt."""
    parts = []
    for i, v in enumerate(videos):
        timestamped = v.get("timestamped_text", "")
        # Truncate very long transcripts to keep within token limits
        if len(timestamped) > 8000:
            timestamped = timestamped[:8000] + "\n... [transcript truncated]"

        parts.append(
            f"--- VIDEO {i+1} ---\n"
            f"Channel: {v['channel']}\n"
            f"Title: {v['title']}\n"
            f"Video ID: {v['video_id']}\n"
            f"Duration: {v['duration']}s\n"
            f"Transcript:\n{timestamped}\n"
        )
    return "\n".join(parts)


def select_clips(videos: list) -> dict:
    """Use Claude to select the 5 best clip moments from transcribed videos.

    Args:
        videos: List of dicts from scan_all_channels() with transcript_text/timestamped_text

    Returns:
        Dict with 'clips' list, 'episode_title', 'cold_open'
    """
    if not videos:
        logger.error("No videos to select from")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

    key = get_key("ANTHROPIC_API_KEY")
    if not key or not HAS_ANTHROPIC:
        logger.error("Anthropic API not available")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

    transcripts_text = _format_transcripts(videos)
    prompt = SELECTION_PROMPT.format(transcripts=transcripts_text)

    logger.info(f"Sending {len(videos)} transcripts to Claude for clip selection...")
    client = anthropic.Anthropic(api_key=key)

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        # Strip markdown fences if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text)

        clips = result.get("clips", [])
        logger.info(f"Claude selected {len(clips)} clips:")
        for c in clips:
            logger.info(f"  #{c['rank']}: [{c['channel']}] {c.get('video_title', '')[:40]} "
                        f"({c['start_seconds']}-{c['end_seconds']}s)")
            logger.info(f"    Quote: \"{c.get('quote', '')[:60]}...\"")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response text: {text[:500]}")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}


if __name__ == "__main__":
    # Test with cached transcripts or live scan
    from channel_scanner import scan_all_channels
    videos = scan_all_channels()
    if videos:
        selections = select_clips(videos)
        print(json.dumps(selections, indent=2))
    else:
        print("No videos found to select from")
