#!/usr/bin/env python3
"""Clip Selector — uses Claude to pick the 5 best moments from transcribed videos.

Analyzes all transcripts and selects timestamp ranges for the most compelling
clips, along with host setup/reaction dialogue suggestions.
"""
import json
import logging
import os
import sys
from datetime import datetime

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

SELECTION_PROMPT = """You are the executive producer of "Pulse Check" — a daily Bitcoin intelligence briefing.
Two hosts (Eryn & Mark) present and analyze the BEST clips from Bitcoin YouTube that day.
Format: NotebookLM Deep Dive — forensic briefing delivered as genuine conversation.

Your job: analyze these transcripts from today's Bitcoin YouTube videos and pick the 5 BEST moments.

SELECTION CRITERIA (in order of priority):
1. BREAKING NEWS — first reports of major developments (ETF flows, regulatory, corporate buys)
2. HOT TAKES — strong, quotable opinions from respected voices
3. DATA DROPS — specific numbers, charts, on-chain metrics being discussed
4. QUOTABLE — moments where someone says something memorable and punchy
5. VISUAL — prefer clips where someone is on camera talking (not just voice-over slides)

RULES:

SHOW INTRO BLACKOUT — ABSOLUTE HARD RULE:
NEVER select any clip with start_seconds below 90.
The first 90 seconds of ANY YouTube video is always: theme music, jingle,
"hey welcome back everyone," host introduction, sponsor bumper, or housekeeping.
This content will play the source show's own branding inside our show.
Minimum start_seconds = 90 for every clip. No exceptions. No overrides.

CLIP START — EXACT SENTENCE BEGINNING:
The clip must begin at the EXACT FIRST WORD of the compelling sentence.
Start at the moment where a specific fact, bold assertion, or strong argument begins.
The first word of start_seconds must be substantive content — not "um," "so," "like," "you know," or "I mean."
If the sentence begins with filler, advance start_seconds by 1–2 seconds to the first real word.
NEVER cut mid-sentence. NEVER start before the sentence (no pre-sentence lead-in).
The clip's opening word must be able to stand alone as an attention-grabbing entry point.

AD READ ELIMINATION — ZERO TOLERANCE:
1. NEVER select a timestamp range where the 15-second window AROUND the selected
   range (7.5s before start, 7.5s after end) contains any sponsorship language,
   promo codes, product mentions, affiliate links, or deviation from primary content.
2. If a video contains an ad read anywhere in the first 3 minutes, treat the entire
   first 3 minutes as contaminated — do not select from it.
3. If uncertain whether a segment is an ad read — it IS an ad read. Skip it.
4. This applies to: pre-roll, mid-roll, host-read sponsorships, "quick word from our
   sponsor," affiliate disclosures, merch mentions, course promotions, Patreon/membership
   CTAs, "check the link in description," and any "use code X" references.
5. The Python post-selection filter is a safety net, not the primary gate. Get this
   right at selection time.

SEGMENT CONTINUITY: The clip must begin and end at natural content boundaries.
A clip that begins with ad-read content or show-intro content is invalid, full stop.

- Pick from DIFFERENT channels when possible (variety matters)
- NEVER select more than 1 clip from the same YouTube video (unique video_id per clip)
- NEVER select 2 clips from the same channel back-to-back — vary the source
- If forced to use the same channel twice, clips must be different videos on different topics
- Each clip should be 20-40 seconds long (the best moment, not the full segment)
- Rank 1 = most dramatic/important (this becomes the cold open teaser)
- The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
- When specifying clip end times, always allow 3-4 seconds of buffer AFTER the key statement ends
- Sort clips to maximize channel variety: no same channel appearing consecutively

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
      "host_setup": "What Eryn should say to introduce this clip (1-2 sentences, forensic/analytical)",
      "host_react": "What the hosts should discuss after this clip (2-3 sentences, 6-beat rhythm)"
    }}
  ],
  "episode_title": "Short punchy episode title based on top clip (5-8 words)",
  "cold_open": "Eryn's cold open line about clip #1 — explosive, forensic, no show-name intro (1 sentence)"
}}

Return exactly 5 clips, ranked 1-5. If fewer than 5 good moments exist, return what you can."""


USED_CLIPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "used_clips.json")


def _load_used_clips() -> dict:
    """Load episode memory from data/used_clips.json."""
    if not os.path.exists(USED_CLIPS_PATH):
        return {"episodes": []}
    try:
        with open(USED_CLIPS_PATH) as f:
            return json.load(f)
    except Exception:
        return {"episodes": []}


def _get_recent_video_ids(max_episodes: int = 7) -> set:
    """Get all video_ids used in the last N episodes."""
    data = _load_used_clips()
    recent = data.get("episodes", [])[-max_episodes:]
    ids = set()
    for ep in recent:
        ids.update(ep.get("video_ids", []))
    return ids


def _record_episode(clips: list):
    """Record this episode's video_ids to the memory file."""
    data = _load_used_clips()
    video_ids = [c.get("video_id", "") for c in clips if c.get("video_id")]
    channels = [c.get("channel", "") for c in clips if c.get("channel")]
    data["episodes"].append({
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "video_ids": video_ids,
        "channels": channels,
    })
    # Keep only last 30 episodes
    data["episodes"] = data["episodes"][-30:]
    os.makedirs(os.path.dirname(USED_CLIPS_PATH), exist_ok=True)
    with open(USED_CLIPS_PATH, "w") as f:
        json.dump(data, f, indent=2)


AD_READ_PHRASES = [
    "brought to you by", "thanks to our sponsor", "use code", "promo code",
    "check out", "go to", ".com/", "discount", "affiliate", "sponsored by",
    "this episode is", "today's episode is brought", "support the show",
    "today's sponsor", "free trial", "get 20% off", "get 10% off",
    "use my link", "click the link in", "head over to", "sign up at",
    "limited time offer", "swipe up",
    # Issue 5: expanded ad read patterns
    "unchained.com", "unchained capital", "collaborative custody",
    "swan bitcoin", "river.com", "fold app", "cash app",
    "strike app", "download the app", "link in description",
    "link in the description", "link below", "link in the bio",
]


def contains_ad_read(transcript_segment: str) -> bool:
    """Return True if this transcript segment contains ad read content."""
    lower = transcript_segment.lower()
    for phrase in AD_READ_PHRASES:
        if phrase in lower:
            logger.info(f"🚫 AD READ DETECTED — pattern '{phrase}' found. Clip REJECTED.")
            return True
    return False


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

        # Post-selection ad read filter (double gate per PIPELINE_LAWS Section 15)
        clean_clips = []
        for c in clips:
            quote = c.get("quote", "")
            setup = c.get("host_setup", "")
            if contains_ad_read(quote) or contains_ad_read(setup):
                logger.warning(f"  REJECTED clip #{c['rank']} [{c.get('channel','')}] — ad read content")
                continue
            clean_clips.append(c)
        result["clips"] = clean_clips

        # Channel dedup: max 1 clip per channel, keep higher-ranked (lower number)
        seen_channels = {}
        deduped_clips = []
        for c in clean_clips:
            ch = c.get("channel", "")
            if ch in seen_channels:
                existing = seen_channels[ch]
                if c["rank"] < existing["rank"]:
                    logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {c['rank']} clip")
                    deduped_clips.remove(existing)
                    deduped_clips.append(c)
                    seen_channels[ch] = c
                else:
                    logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {existing['rank']} clip")
            else:
                deduped_clips.append(c)
                seen_channels[ch] = c
        clean_clips = deduped_clips
        result["clips"] = clean_clips

        # Episode memory: drop clips from recently used videos
        recent_ids = _get_recent_video_ids(max_episodes=7)
        if recent_ids:
            memory_filtered = []
            for c in clean_clips:
                vid = c.get("video_id", "")
                if vid in recent_ids:
                    logger.warning(f"EPISODE MEMORY: Dropped clip from video {vid} "
                                   f"[{c.get('channel', '')}] — used in recent episode")
                else:
                    memory_filtered.append(c)
            clean_clips = memory_filtered
            result["clips"] = clean_clips

        # 5-CLIP RULE enforcement (PIPELINE_LAWS Section 22)
        test_mode = len(videos) <= 4  # heuristic: few source videos = test mode
        required_clips = 2 if test_mode else 5

        # If we have fewer clips than required, re-select from remaining videos
        used_channels = {c.get("channel", "") for c in clean_clips}
        used_video_ids = {c.get("video_id", "") for c in clean_clips} | recent_ids

        if not test_mode and len(clean_clips) < 5:
            logger.warning(f"5-CLIP RULE: Only {len(clean_clips)} clips after filtering, "
                           f"need 5. Re-selecting from remaining channels...")

            # Find available videos not yet used
            available = [v for v in videos
                         if v.get("channel", "") not in used_channels
                         and v.get("video_id", "") not in used_video_ids]

            if available:
                # Ask Claude to pick from remaining videos
                remaining_text = _format_transcripts(available)
                need = 5 - len(clean_clips)
                reselect_prompt = (
                    f"Pick the {need} BEST clip moments from these videos. "
                    f"Each clip from a DIFFERENT channel. 20-40 seconds each. "
                    f"NO ad reads. Return ONLY valid JSON with a 'clips' array.\n\n"
                    f"ALREADY SELECTED channels (DO NOT use these): {list(used_channels)}\n\n"
                    f"AVAILABLE VIDEOS:\n{remaining_text}\n\n"
                    f"Return JSON: {{\"clips\": [{{\"rank\": N, \"video_id\": \"...\", "
                    f"\"channel\": \"...\", \"video_title\": \"...\", \"start_seconds\": N, "
                    f"\"end_seconds\": N, \"quote\": \"...\", \"why\": \"...\", "
                    f"\"host_setup\": \"...\", \"host_react\": \"...\"}}]}}"
                )
                try:
                    resp2 = client.messages.create(
                        model="claude-sonnet-4-6",
                        max_tokens=3000,
                        messages=[{"role": "user", "content": reselect_prompt}],
                    )
                    text2 = resp2.content[0].text.strip()
                    if "```json" in text2:
                        text2 = text2.split("```json")[1].split("```")[0]
                    elif "```" in text2:
                        text2 = text2.split("```")[1].split("```")[0]
                    extra = json.loads(text2)
                    extra_clips = extra.get("clips", [])

                    # Filter extras through ad-read + dedup
                    for ec in extra_clips:
                        ch = ec.get("channel", "")
                        vid = ec.get("video_id", "")
                        if ch in used_channels or vid in used_video_ids:
                            continue
                        if contains_ad_read(ec.get("quote", "")) or contains_ad_read(ec.get("host_setup", "")):
                            continue
                        ec["rank"] = len(clean_clips) + 1
                        clean_clips.append(ec)
                        used_channels.add(ch)
                        used_video_ids.add(vid)
                        logger.info(f"  RE-SELECT: Added #{ec['rank']} [{ch}] {ec.get('video_title', '')[:40]}")
                        if len(clean_clips) >= 5:
                            break
                except Exception as e:
                    logger.warning(f"Re-selection failed: {e}")

            result["clips"] = clean_clips

        # Issue 7: HARD ENFORCEMENT — unique channels in Python after ALL selection
        seen_channels = set()
        deduped_final = []
        for clip in clean_clips:
            ch = clip.get("channel", "")
            if ch not in seen_channels:
                seen_channels.add(ch)
                deduped_final.append(clip)
            else:
                logger.warning(f"HARD DEDUP: Removed duplicate channel '{ch}' clip #{clip.get('rank', '?')}")
        if len(deduped_final) < len(clean_clips):
            logger.warning(f"HARD DEDUP: {len(clean_clips)} → {len(deduped_final)} clips after enforcement")
        clean_clips = deduped_final
        result["clips"] = clean_clips

        if len(clean_clips) < 5 and not test_mode:
            logger.error(f"HARD DEDUP: Only {len(clean_clips)} unique channels. Need replacement clips.")

        # Score-based ranking (CLIP SCORER per PRODUCTION_DESIGN_LAWS)
        try:
            from utils.clip_scorer import rank_clips
            clean_clips = rank_clips(clean_clips)
            logger.info("Clip scorer applied — clips re-ranked by intelligence score")
        except Exception as e:
            logger.warning(f"Clip scorer unavailable, keeping original rank order: {e}")

        # Log the 5-clip rule result
        unique_channels = {c.get("channel", "") for c in clean_clips}
        channel_list = sorted(unique_channels)
        logger.info(f"5-CLIP RULE: Selected {len(clean_clips)} clips from "
                    f"{len(unique_channels)} unique channels: {channel_list}")

        logger.info(f"Claude selected {len(clips)} clips, {len(clean_clips)} passed all filters:")
        for c in clean_clips:
            logger.info(f"  #{c['rank']}: [{c['channel']}] {c.get('video_title', '')[:40]} "
                        f"({c.get('start_seconds', '?')}-{c.get('end_seconds', '?')}s)")
            logger.info(f"    Quote: \"{c.get('quote', '')[:60]}...\"")

        # Record this episode's clips to memory
        _record_episode(clean_clips)

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
