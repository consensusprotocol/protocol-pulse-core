#!/usr/bin/env python3
"""Clip Selector — uses Claude to pick the 5 best moments from transcribed videos.

Analyzes all transcripts and selects timestamp ranges for the most compelling
clips, along with host setup/reaction dialogue suggestions.
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta

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
- INTRO AVOIDANCE: Never select a clip starting at 0:00 unless the transcript shows
  substantive speech begins within the first 3 seconds. Prefer clips starting at 30s+
  into the video to skip channel intros, jingles, and logos. Clips starting in the
  first 10 seconds of a video almost always contain branding — avoid them.
- CRITICAL — AD READ DETECTION: NEVER select a timestamp range that contains
  an ad read, sponsorship mention, or promotional segment. Ad reads are identified by:
  * "This episode is brought to you by..."
  * "Thanks to our sponsor..."
  * "Use code [X] at [URL]"
  * "Go to [domain].com/[show]"
  * "Check out [product]" with a URL
  * Any mention of a promo code, discount, or affiliate link
  * Host reading from a script about a product/service they're paid to mention
  If a transcript segment contains these patterns, SKIP it and find the next
  compelling moment that is actual content, not advertising.
- SEGMENT CONTINUITY: Never select a clip that starts mid-ad-read or ends
  mid-thought. The clip must begin and end at natural content boundaries.
  A clip that begins with ad-read content is invalid, full stop.
- Pick from DIFFERENT channels when possible (variety matters)
- NEVER select more than 1 clip from the same YouTube video (unique video_id per clip)
- NEVER select 2 clips from the same channel back-to-back — vary the source
- If forced to use the same channel twice, clips must be different videos on different topics
- Each clip should be 20-40 seconds long (the best moment, not the full segment)
- Rank 1 = most dramatic/important (this becomes the cold open teaser)
- The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
- Avoid dead air, filler words, or mid-sentence cuts
- When specifying clip end times, always allow 3-4 seconds of buffer AFTER the key statement ends so the narrator never interrupts a sentence in progress
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
      "host_setup": "What Jessica should say to introduce this clip (1-2 sentences, conversational)",
      "host_react": "What the hosts should discuss after this clip (2-3 sentences of banter)"
    }}
  ],
  "episode_title": "Short punchy episode title based on top clip (5-8 words)",
  "cold_open": "Jessica's cold open teaser line about clip #1 — dramatic, hook the viewer (1 sentence)"
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


def _prune_old_episodes():
    """Remove episodes older than today from used_clips.json (R27 same-day expiry)."""
    data = _load_used_clips()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    before = len(data.get("episodes", []))
    data["episodes"] = [ep for ep in data.get("episodes", []) if ep.get("date", "") == today]
    after = len(data["episodes"])
    if after < before:
        logger.info(f"EPISODE MEMORY: Pruned {before - after} episodes from previous days")
        os.makedirs(os.path.dirname(USED_CLIPS_PATH), exist_ok=True)
        with open(USED_CLIPS_PATH, "w") as f:
            json.dump(data, f, indent=2)
    return data


def _get_recent_channels(max_episodes: int = 3) -> set:
    """Get channels used in the last N episode_memory entries for diversity penalty.

    ISSUE 5 FIX: Channels appearing in recent episodes get a 50% score reduction
    to force clip variety across episodes.
    """
    data = _load_used_clips()
    episodes = data.get("episodes", [])
    # Take the last N episodes (most recent)
    recent = episodes[-max_episodes:] if len(episodes) >= max_episodes else episodes
    channels = set()
    for ep in recent:
        channels.update(ep.get("channels", []))
    if channels:
        logger.info(f"DIVERSITY: {len(channels)} channels from last {len(recent)} episodes")
    return channels


def _get_recent_video_ids(max_episodes: int = 7) -> set:
    """Get video_ids used TODAY (same calendar day, UTC).

    R27: Same-day expiry — clips from any previous date are immediately eligible.
    """
    data = _load_used_clips()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    ids = set()
    for ep in data.get("episodes", []):
        if ep.get("date", "") == today:
            ids.update(ep.get("video_ids", []))
    logger.info(f"EPISODE MEMORY: {len(ids)} video_ids blocked (same-day only, {today})")
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
    # R27: Keep only today's episodes
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data["episodes"] = [ep for ep in data["episodes"] if ep.get("date", "") == today]
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
        if len(timestamped) > 1500:
            timestamped = timestamped[:1500] + "\n... [transcript truncated]"

        parts.append(
            f"--- VIDEO {i+1} ---\n"
            f"Channel: {v['channel']}\n"
            f"Title: {v['title']}\n"
            f"Video ID: {v['video_id']}\n"
            f"Duration: {v['duration']}s\n"
            f"Transcript:\n{timestamped}\n"
        )
    return "\n".join(parts)


def _parse_llm_json(text: str, label: str = "LLM") -> dict | None:
    """Parse JSON from LLM response — robust brace-counting parser.

    Strategy:
      1. Strip markdown fences
      2. Try direct json.loads
      3. Brace-counting: walk char-by-char extracting each complete {...} object
         that contains both "rank" and "video_id" keys (i.e. clip objects)
      4. Reassemble from collected clips + regex-extracted episode_title/cold_open
      5. Progressive boundary search as final fallback

    Returns parsed dict or None on failure.
    """
    if not text:
        return None

    # --- Step 1: Strip markdown fences ---
    import re as _re
    stripped = text
    if "```json" in stripped:
        stripped = stripped.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in stripped:
        stripped = stripped.split("```", 1)[1].split("```", 1)[0]
    stripped = stripped.strip()

    # --- Step 2: Direct parse ---
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # --- Step 3: Brace-counting extraction ---
    def _extract_objects(s: str) -> list:
        """Walk char-by-char, track brace depth, yield complete top-level objects."""
        objects = []
        i = 0
        in_string = False
        escape_next = False
        while i < len(s):
            if s[i] == '{' and not in_string:
                # Start of an object — track depth
                depth = 1
                start = i
                j = i + 1
                obj_in_string = False
                obj_escape = False
                while j < len(s) and depth > 0:
                    c = s[j]
                    if obj_escape:
                        obj_escape = False
                    elif c == '\\' and obj_in_string:
                        obj_escape = True
                    elif c == '"' and not obj_escape:
                        obj_in_string = not obj_in_string
                    elif not obj_in_string:
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                    j += 1
                if depth == 0:
                    candidate = s[start:j]
                    try:
                        obj = json.loads(candidate)
                        objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                i = j
            else:
                if escape_next:
                    escape_next = False
                elif s[i] == '\\' and in_string:
                    escape_next = True
                elif s[i] == '"':
                    in_string = not in_string
                i += 1
        return objects

    all_objects = _extract_objects(stripped)

    # Separate clip objects (have rank + video_id) from the wrapper
    clips = []
    wrapper = None
    for obj in all_objects:
        if "rank" in obj and "video_id" in obj:
            clips.append(obj)
        elif "clips" in obj:
            # This is a successfully parsed wrapper — use it directly
            return obj
        elif "episode_title" in obj or "cold_open" in obj:
            wrapper = obj

    if clips:
        # --- Step 4: Reassemble from clips + regex metadata ---
        episode_title = "Pulse Check"
        cold_open = ""

        if wrapper:
            episode_title = wrapper.get("episode_title", episode_title)
            cold_open = wrapper.get("cold_open", cold_open)
        else:
            # Try regex extraction from raw text
            m_title = _re.search(r'"episode_title"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped)
            if m_title:
                episode_title = m_title.group(1)
            m_cold = _re.search(r'"cold_open"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped)
            if m_cold:
                cold_open = m_cold.group(1)

        # Sort by rank to maintain order
        clips.sort(key=lambda c: c.get("rank", 999))
        result = {
            "episode_title": episode_title,
            "cold_open": cold_open,
            "clips": clips,
        }
        logger.warning(f"{label}: JSON repaired via brace-counting ({len(clips)} clips recovered)")
        return result

    # --- Step 5: Progressive boundary search (last resort) ---
    try:
        last_brace = stripped.rfind("}")
        if last_brace > 0:
            repaired = stripped[:last_brace + 1]
            if '"clips"' in repaired and not repaired.rstrip().endswith("]}"):
                repaired = repaired.rstrip().rstrip(",") + "]}"
            result = json.loads(repaired)
            logger.warning(f"{label}: JSON repaired (progressive boundary salvage)")
            return result
    except json.JSONDecodeError:
        pass

    logger.warning(f"{label}: JSON parse failed. Raw (first 500): {stripped[:500]}")
    return None


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

    from relay import call_llm, reload_env; reload_env()

    transcripts_text = _format_transcripts(videos)
    prompt = SELECTION_PROMPT.format(transcripts=transcripts_text)

    logger.info(f"Sending {len(videos)} transcripts for clip selection...")
    text = call_llm(prompt, max_tokens=8000)
    if text is None:
        logger.error("All LLM providers failed for clip selection")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

    try:
        result = _parse_llm_json(text, label="main selection")
        if result is None:
            logger.error(f"Failed to parse Claude response as JSON. Raw (first 500): {text[:500]}")
            return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

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
        recent_ids = _get_recent_video_ids(max_episodes=1)
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
        used_video_ids = {c.get("video_id", "") for c in clean_clips}

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
                    text2 = call_llm(reselect_prompt, max_tokens=8000)
                    if text2 is None:
                        raise RuntimeError("All LLM providers failed for re-selection")

                    extra = _parse_llm_json(text2, label="re-selection")
                    if extra is None:
                        # Retry once with fresh call
                        logger.warning("Re-selection JSON parse failed, retrying...")
                        text2 = call_llm(reselect_prompt, max_tokens=8000)
                        if text2 is not None:
                            extra = _parse_llm_json(text2, label="re-selection retry")
                    if extra is None:
                        logger.warning(f"Re-selection parse failed after retry. Raw (first 500): {(text2 or '')[:500]}")
                        extra = {"clips": []}
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

        # Render22 FIX 9: Clip diversity — no consecutive clips from same channel or speaker
        if len(clean_clips) > 1:
            reordered = [clean_clips[0]]
            remaining = list(clean_clips[1:])
            while remaining:
                prev_ch = reordered[-1].get("channel", "")
                # Find first clip from a different channel
                found = False
                for idx, c in enumerate(remaining):
                    if c.get("channel", "") != prev_ch:
                        reordered.append(remaining.pop(idx))
                        found = True
                        break
                if not found:
                    # No different channel available — take first remaining
                    reordered.append(remaining.pop(0))
                    logger.warning(f"  FIX 9: Consecutive same-channel unavoidable at position {len(reordered)}")
            clean_clips = reordered
            result["clips"] = clean_clips
            logger.info(f"  FIX 9: Clip order after diversity: {[c.get('channel', '') for c in clean_clips]}")

        # ISSUE 5 FIX: Channel diversity bonus — penalize channels from last 3 episodes by 50%
        recent_channels = _get_recent_channels(max_episodes=3)
        if recent_channels:
            logger.info(f"DIVERSITY: Penalizing {len(recent_channels)} recently-used channels: {sorted(recent_channels)}")
            for clip in clean_clips:
                ch = clip.get("channel", "")
                if ch in recent_channels:
                    clip["_diversity_penalty"] = True
            # Sort: non-penalized first (preserving relative order), penalized last
            non_penalized = [c for c in clean_clips if not c.get("_diversity_penalty")]
            penalized = [c for c in clean_clips if c.get("_diversity_penalty")]
            if non_penalized:
                # Only reorder if we have enough non-penalized clips to fill slots
                clean_clips = non_penalized + penalized
                result["clips"] = clean_clips
                logger.info(f"  DIVERSITY: {len(non_penalized)} fresh + {len(penalized)} penalized clips")

        # Score-based ranking (CLIP SCORER per PRODUCTION_DESIGN_LAWS)
        try:
            from utils.clip_scorer import rank_clips, _load_narrative_context
            narrative_ctx = _load_narrative_context()
            if narrative_ctx:
                dominant = narrative_ctx.get("dominant_narrative", "")
                if dominant:
                    logger.info(f"Episode narrative: {dominant}")
                # Filter clips that only match avoid_topics
                avoid = [t.lower() for t in narrative_ctx.get("avoid_topics", [])]
                if avoid:
                    pre_count = len(clean_clips)
                    clean_clips = [
                        c for c in clean_clips
                        if not all(
                            a in (c.get("quote", "") + " " + c.get("video_title", "")).lower()
                            for a in avoid
                        )
                    ]
                    if len(clean_clips) < pre_count:
                        logger.info(f"Narrative filter: removed {pre_count - len(clean_clips)} clips matching avoid_topics")
            clean_clips = rank_clips(clean_clips, narrative_context=narrative_ctx)
            logger.info("Clip scorer applied — clips re-ranked by intelligence score (narrative-aware)")
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
