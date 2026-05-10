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

SELECTION_SYSTEM = (
    "You are a Bitcoin video clip selector. Respond ONLY with valid JSON. No markdown, no explanation. "
    "Return a JSON object with keys: clips (array), episode_title (string), cold_open (string). "
    "Each clip has: rank, video_id, channel, video_title, start_seconds, end_seconds, quote, why, host_setup, host_react."
)

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

TIER 4 - CROSSOVER DISCOVERY (1.6x multiplier): Videos from non-Bitcoin channels that specifically covered Bitcoin. A philosopher, scientist, or political commentator covering Bitcoin outscores another Bitcoin-native channel on the same story. Field: source == "tier2_discovery". Prioritize these.

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
- When specifying clip end times, always allow 6-8 seconds of buffer AFTER the key statement ends so the narrator never interrupts a sentence in progress
- Sort clips to maximize channel variety: no same channel appearing consecutively

AVAILABLE VIDEOS:
{transcripts}

Return exactly 5 clips, ranked 1-5. If fewer than 5 good moments exist, return what you can."""


USED_CLIPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "used_clips.json")
LAST_GOOD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "last_good_selection.json")


def _load_used_clips() -> dict:
    """Load episode memory from data/used_clips.json. Auto-heals corrupt files."""
    from validators import validate_json_file
    data, errors = validate_json_file(USED_CLIPS_PATH, dict, ["episodes"])
    for e in errors:
        logger.warning(f"USED_CLIPS: {e}")
    return data


def _prune_old_episodes():
    """Remove episodes older than 3 days from used_clips.json.

    Changed from R27 same-day expiry to 3-day window to prevent the same clips
    appearing across consecutive daily renders.
    """
    data = _load_used_clips()
    cutoff = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
    before = len(data.get("episodes", []))
    data["episodes"] = [ep for ep in data.get("episodes", []) if ep.get("date", "") >= cutoff]
    after = len(data["episodes"])
    if after < before:
        logger.info(f"EPISODE MEMORY: Pruned {before - after} episodes older than 3 days (cutoff {cutoff})")
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
    """Get video_ids used in the last 3 days (UTC).

    Changed from R27 same-day to 3-day window. Clips used in the last 3 days
    are HARD BLOCKED — they must not appear in new selections.
    """
    data = _load_used_clips()
    cutoff = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
    ids = set()
    for ep in data.get("episodes", []):
        if ep.get("date", "") >= cutoff:
            ids.update(ep.get("video_ids", []))
    logger.info(f"EPISODE MEMORY: {len(ids)} video_ids HARD BLOCKED (3-day window, cutoff {cutoff})")
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
    # Keep 3-day window (was R27 same-day)
    cutoff = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")
    data["episodes"] = [ep for ep in data["episodes"] if ep.get("date", "") >= cutoff]
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
    # V15 FIX: Host intro/outro detection — prevent show intros bleeding into clips
    "welcome to the show", "welcome back to", "welcome to the channel",
    "hey everyone welcome", "what's up everyone", "what is up everyone",
    "welcome to bitcoin magazine", "welcome to simply bitcoin",
    "welcome to another episode", "thanks for joining", "thanks for tuning in",
    "hit that subscribe", "hit the subscribe", "smash that like",
    "hit the like button", "don't forget to subscribe", "make sure to subscribe",
    "bell icon", "notification bell", "let me know in the comments",
    "let us know in the comments", "comment section below",
    "this is your host", "i'm your host", "my name is",
    "before we get started", "before we get into it", "before we jump in",
    "let's get right into it", "let's jump right in", "let's get into it",
    "without further ado", "let's dive in", "let's dive right in",
]


def contains_ad_read(transcript_segment: str) -> bool:
    """Return True if this transcript segment contains ad read content."""
    lower = transcript_segment.lower()
    for phrase in AD_READ_PHRASES:
        if phrase in lower:
            logger.info(f"🚫 AD READ DETECTED — pattern '{phrase}' found. Clip REJECTED.")
            return True
    return False


def score_clip(clip: dict, transcript_score: float = 0.5) -> float:
    """Multi-dimensional clip scoring (V4 audit consensus).

    Weights:
      40% semantic relevance (from AI selection)
      20% audio clarity (Whisper logprob)
      15% resolution preference
      15% recency
      10% channel tier
    """
    score = 0.0

    # Semantic relevance (from AI selection) — 40%
    score += 0.4 * transcript_score

    # Audio energy (higher logprob = clearer speech) — 20%
    avg_logprob = clip.get('avg_logprob', -1.0)
    audio_score = max(0, min(1, (avg_logprob + 0.5) / 0.5))
    score += 0.2 * audio_score

    # Resolution preference — 15%
    height = clip.get('height', 720)
    res_score = 1.0 if height >= 1080 else 0.7 if height >= 720 else 0.3
    score += 0.15 * res_score

    # Recency — 15%
    age_hours = clip.get('age_hours', 48)
    recency_score = max(0, 1 - (age_hours / 72))  # 0-72h scale
    score += 0.15 * recency_score

    # Channel tier bonus — 10%
    tier = clip.get('tier', 3)
    tier_score = {1: 1.0, 2: 0.7, 3: 0.4}.get(tier, 0.4)
    score += 0.1 * tier_score

    return round(score, 3)


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
            f"Views: {v.get('view_count', 0):,} | Uploaded: {v.get('upload_date', 'unknown')}\n"
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
        if "video_id" in obj and ("rank" in obj or "channel" in obj):
            clips.append(obj)
        elif "clips" in obj:
            # This is a successfully parsed wrapper — use it directly
            return obj
        elif "episode_title" in obj or "cold_open" in obj:
            wrapper = obj

    # Auto-assign rank if Claude omitted it
    for i, c in enumerate(clips):
        if "rank" not in c:
            c["rank"] = i + 1

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

    from relay import call_llm, reload_env, get_key; reload_env()

    transcripts_text = _format_transcripts(videos)
    prompt = SELECTION_PROMPT.replace('{transcripts}', transcripts_text)

    logger.info(f"Sending {len(videos)} transcripts for clip selection...")

    # Prefilled response approach: force Claude to start with JSON, not markdown
    # Respects relay.py spend cap sentinel to avoid burning credits
    from relay import _check_spend_cap_sentinel, _set_spend_cap_sentinel
    text = None
    anthropic_key = get_key("ANTHROPIC_API_KEY", required=False)
    if HAS_ANTHROPIC and anthropic_key and not _check_spend_cap_sentinel():
        try:
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                system=SELECTION_SYSTEM,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "{"},  # Prefill forces JSON start
                ],
            )
            # Prepend the "{" back since it was consumed as prefill
            text = "{" + resp.content[0].text
            logger.info("Clip selection: Anthropic prefilled JSON succeeded")
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ['529', 'credit_balance_too_low',
                                            'spend_limit_exceeded', 'insufficient_quota',
                                            'payment_required', '402']):
                _set_spend_cap_sentinel(str(e))
            logger.warning(f"Clip selection: Anthropic prefilled call failed: {e}")

    # Fallback to generic call_llm (Grok/Gemini)
    if text is None:
        text = call_llm(prompt, max_tokens=8000)

    if text is None:
        logger.error("All LLM providers failed for clip selection")
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

    try:
        result = _parse_llm_json(text, label="main selection")
        if result is None:
            logger.error(f"Failed to parse Claude response as JSON. Raw (first 500): {text[:500]}")
            return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}

        # Handle both dict and list responses from Claude
        if isinstance(result, list):
            clips = result
            result = {"clips": clips, "episode_title": "Pulse Check", "cold_open": ""}
        else:
            clips = result.get("clips", [])

        # Post-selection ad read filter (double gate per PIPELINE_LAWS Section 15)
        clean_clips = []
        for c in clips:
            quote = c.get("quote", "")
            setup = c.get("host_setup", "")
            if contains_ad_read(quote) or contains_ad_read(setup):
                logger.warning(f"  REJECTED clip #{c.get('rank', 0)} [{c.get('channel','')}] — ad read content")
                continue
            clean_clips.append(c)
        result["clips"] = clean_clips

        # Auto-assign rank if missing (Claude sometimes omits)
        for i, c in enumerate(clean_clips):
            if "rank" not in c:
                c["rank"] = i + 1
        
        # Channel dedup: max 1 clip per channel, keep higher-ranked (lower number)
        seen_channels = {}
        deduped_clips = []
        for c in clean_clips:
            ch = c.get("channel", "")
            if ch in seen_channels:
                existing = seen_channels[ch]
                if c.get("rank", 999) < existing.get("rank", 999):
                    logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {c.get('rank', 0)} clip")
                    deduped_clips.remove(existing)
                    deduped_clips.append(c)
                    seen_channels[ch] = c
                else:
                    logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {existing.get('rank', 0)} clip")
            else:
                deduped_clips.append(c)
                seen_channels[ch] = c
        clean_clips = deduped_clips
        result["clips"] = clean_clips

        # Episode memory: HARD BLOCK clips from videos used in last 3 days
        recent_ids = _get_recent_video_ids()
        if recent_ids:
            memory_filtered = []
            for c in clean_clips:
                vid = c.get("video_id", "")
                if vid in recent_ids:
                    logger.warning(f"CLIP DIVERSITY: Rejected {vid} [{c.get('channel', '')}] "
                                   f"— used in last 3 days. HARD BLOCKED.")
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
                    # Handle list response (Claude sometimes returns bare array)
                    if isinstance(extra, list):
                        extra = {"clips": extra}
                    extra_clips = extra.get("clips", []) if isinstance(extra, dict) else []

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
                        logger.info(f"  RE-SELECT: Added #{ec.get('rank', 0)} [{ch}] {ec.get('video_title', '')[:40]}")
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
            logger.info(f"  #{c.get('rank', 0)}: [{c.get('channel', '?')}] {c.get('video_title', '')[:40]} "
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
        # DEBUG: dump raw response for diagnosis
        import traceback
        traceback.print_exc()
        try:
            with open('/tmp/claude_clip_response_debug.txt', 'w') as dbg:
                dbg.write(str(text[:2000]) if 'text' in dir() else 'text not defined')
        except: pass
        return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}


def _save_last_good_selection(result):
    """Cache a successful clip selection for fallback use."""
    try:
        os.makedirs(os.path.dirname(LAST_GOOD_PATH), exist_ok=True)
        with open(LAST_GOOD_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save last good selection: {e}")


def _load_last_good_selection():
    """Load the last successful clip selection."""
    if os.path.exists(LAST_GOOD_PATH):
        try:
            with open(LAST_GOOD_PATH) as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("clips"):
                return data
        except Exception:
            pass
    return None


def _select_clips_local(videos, max_clips=5):
    """Fallback: use local Qwen model for clip selection."""
    import requests as _req
    # V42: moved to after pre-filter below
    # V36 FIX: Load used clips to inject into Qwen prompt for variety
    _used_vids = []
    _used_channels = []
    try:
        _udata = _load_used_clips()
        for ep in _udata.get("episodes", []):
            _used_vids.extend(ep.get("video_ids", []))
            _used_channels.extend(ep.get("channels", []))
    except Exception:
        pass
    _avoid = ""
    if _used_vids:
        _avoid = f"\nBLOCKED video_ids (MUST NOT select these — already used in last 3 days): {', '.join(set(_used_vids))}\n"
    if _used_channels:
        _avoid += f"DEPRIORITIZE these channels (recently featured): {', '.join(set(_used_channels[-10:]))}\n"

    # V36 FIX: Shuffle transcripts for variety across renders
    import random
    # V53 FIX: Pre-filter stale videos BEFORE sending to Qwen
    # Videos with parseable upload_date older than 7 days are excluded
    # Videos with no upload_date are kept (can't verify without slow lookup)
    from datetime import datetime, timedelta
    _cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
    _fresh_pool = []
    _stale_count = 0
    for v in videos:
        vid_id = v.get("video_id", "")
        if vid_id in set(_used_vids):
            continue  # already used
        ud = v.get("upload_date", "")
        if ud and len(ud) == 8 and ud < _cutoff:
            _stale_count += 1
            continue  # known stale — don't even show to Qwen
        _fresh_pool.append(v)
    if len(_fresh_pool) < 5:
        _fresh_pool = [v for v in videos if v.get("video_id", "") not in set(_used_vids)]
    logger.info(f"FRESHNESS PRE-FILTER: {len(videos)} total, {_stale_count} stale removed, {len(_fresh_pool)} fresh pool")
    random.shuffle(_fresh_pool)
    _shuffled_videos = _fresh_pool[:15]
    logger.info(f"CLIP DIVERSITY: {len(videos)} total, {len(_used_vids)} blocked, {len(_eligible)} eligible, sending {len(_shuffled_videos)} to Qwen")
    random.shuffle(_shuffled_videos)
    transcripts_text = _format_transcripts(_shuffled_videos)

    prompt = (
        f"You are a viral clip scout for a Bitcoin intelligence show. Find the {max_clips} most COMPELLING moments from these videos.\n"
        f"\n"
        f"VIRAL MOMENT CRITERIA (rank candidates on these):\n"
        f"- CONTROVERSY: Bold claims others would disagree with\n"
        f"- SPECIFICITY: Concrete numbers, predictions, data points — not vague takes\n"
        f"- QUOTABILITY: Could you tweet this 10-word quote and get engagement?\n"
        f"- EMOTION: Speaker is passionate, angry, incredulous, or fired up\n"
        f"- NOVELTY: A take NOT everyone is already saying\n"
        f"\n"
        f"SELECTION RULES:\n"
        f"- Each clip from a DIFFERENT channel. 35-50 seconds each.\n"
        f"- NO ad reads, NO show intros, NO generic pleasantries, NO 'welcome to the show'.\n"
        f"- COMPLETE THOUGHT: Speaker MUST finish their argument. Never cut before conclusion.\n"
        f"- PREFER videos with HIGH view counts — those topics resonate with audience.\n"
        f"- PREFER videos uploaded in last 48 hours — but anything within 7 days is acceptable.\n"
        f"- REJECT any video uploaded more than 7 days ago — stale content destroys credibility.\n"
        f"- Find the MOMENT that makes someone stop scrolling — not just any 40 seconds about Bitcoin.\n"
        f"- The WHY field must explain what makes this moment VIRAL, not just summarize the topic.\n"
        f"- Criticism and contrarian takes are WELCOME — we want honest signal, not echo chamber.\n"
        f"{_avoid}\n"
        f"{transcripts_text[:8000]}\n\n"
        f'Return ONLY valid JSON. No markdown. No explanation. No thinking tags. Just the JSON object:\n'
        f'{{"clips": [{{"rank": 1, "video_id": "...", '
        f'"channel": "...", "video_title": "...", "start_seconds": N, '
        f'"end_seconds": N, "quote": "...", "why": "...", '
        f'"host_setup": "...", "host_react": "..."}}]}}'
    )
    try:
        resp = _req.post(
            "http://localhost:11434/api/chat",
            json={"model": "qwen3-coder:30b", "messages": [{"role": "system", "content": "Respond with valid JSON only. No thinking. No markdown. No explanation."}, {"role": "user", "content": prompt}],
                  "stream": False, "options": {"temperature": 0.7}},
            timeout=240,
        )
        resp.raise_for_status()
        raw = resp.json().get("message", {}).get("content", "")
        from validators import validate_api_response, validate_clip_response
        parsed, _ = validate_api_response(raw)
        if parsed:
            result, _ = validate_clip_response(parsed)
            # HARD BLOCK: Remove any clips with video_ids used in last 3 days
            blocked_ids = _get_recent_video_ids()
            if blocked_ids and result.get("clips"):
                before_count = len(result["clips"])
                result["clips"] = [
                    c for c in result["clips"]
                    if c.get("video_id", "") not in blocked_ids
                ]
                rejected = before_count - len(result["clips"])
                if rejected:
                    logger.warning(f"CLIP DIVERSITY: Qwen post-filter rejected {rejected} clips (3-day block)")
            return result
    except Exception as e:
        logger.warning(f"Local Qwen clip selection failed: {e}")
    return {"clips": []}




def _enforce_min_clip_duration(result, min_sec=20):
    clips = result.get("clips", [])
    for c in clips:
        # V38 FIX: Normalize field names — Qwen uses start_seconds/end_seconds,
        # extractor uses start_seconds/end_seconds, but old code checked start_sec/end_sec
        if "start_seconds" in c and "start_sec" not in c:
            c["start_sec"] = c["start_seconds"]
        if "end_seconds" in c and "end_sec" not in c:
            c["end_sec"] = c["end_seconds"]
        start = c.get("start_seconds", c.get("start_sec", 0))
        end = c.get("end_seconds", c.get("end_sec", 0))
        dur = end - start
        if dur < min_sec:
            logger.warning(f"SHORT CLIP FIX: {c.get('channel','?')} {dur}s at {start}s -> expanding to {min_sec}s")
            c["end_seconds"] = start + min_sec
            c["end_sec"] = start + min_sec
        # Ensure both field names are present for downstream consumers
        c["start_sec"] = c.get("start_seconds", c.get("start_sec", 0))
        c["end_sec"] = c.get("end_seconds", c.get("end_sec", 0))
        c["start_seconds"] = c["start_sec"]
        c["end_seconds"] = c["end_sec"]
    result["clips"] = clips
    return result

def _enforce_channel_diversity(result: dict) -> dict:
    """V29 FIX: Hard post-selection channel dedup. No two clips from the same channel. EVER."""
    clips = result.get("clips", [])
    if not clips:
        return result
    seen = {}
    unique = []
    for c in clips:
        ch = c.get("channel", "unknown")
        if ch not in seen:
            seen[ch] = c
            unique.append(c)
        else:
            logger.warning(f"CHANNEL DEDUP: Dropped duplicate from {ch} (rank {c.get('rank', '?')})")
    # Re-rank
    for i, c in enumerate(unique):
        c["rank"] = i + 1
    result["clips"] = unique
    return result


def _enforce_video_id_diversity(result: dict, videos: list = None) -> dict:
    """Final diversity gate: reject any clip whose video_id was used in last 3 days.

    If a clip is rejected, attempt to find a replacement from the same channel
    (different video) or from a different channel entirely.
    """
    blocked_ids = _get_recent_video_ids()
    if not blocked_ids:
        return result

    clips = result.get("clips", [])

    # Pre-scan: collect channels and video_ids of clips that will survive
    surviving_ids = set()
    surviving_channels = set()
    for c in clips:
        vid = c.get("video_id", "")
        if vid not in blocked_ids:
            surviving_ids.add(vid)
            surviving_channels.add(c.get("channel", ""))

    clean = []
    used_channels = set(surviving_channels)
    used_ids = set(surviving_ids)

    for c in clips:
        vid = c.get("video_id", "")
        ch = c.get("channel", "")
        if vid in blocked_ids:
            # Try to find replacement from available videos
            replacement = None
            if videos:
                for v in videos:
                    rv = v.get("video_id", "")
                    rc = v.get("channel", "")
                    if rv not in blocked_ids and rv not in used_ids and rc not in used_channels:
                        replacement = {
                            "rank": c.get("rank", len(clean) + 1),
                            "video_id": rv,
                            "channel": rc,
                            "video_title": v.get("title", ""),
                            "start_seconds": 30,
                            "end_seconds": 65,
                            "quote": (v.get("transcript_text", "") or v.get("timestamped_text", ""))[:200],
                            "why": "Diversity replacement — original clip was used in last 3 days",
                            "host_setup": "",
                            "host_react": "",
                        }
                        break
            if replacement:
                logger.info(f"CLIP DIVERSITY: Rejected {vid} — used in last 3 days. Replaced with {replacement['video_id']}")
                clean.append(replacement)
                used_channels.add(replacement["channel"])
                used_ids.add(replacement["video_id"])
            else:
                logger.warning(f"CLIP DIVERSITY: Rejected {vid} — used in last 3 days. No replacement found.")
        else:
            clean.append(c)
            used_channels.add(ch)
            used_ids.add(vid)

    result["clips"] = clean
    return result



def _enforce_freshness(result, max_age_hours=168):
    clips = result.get("clips", [])
    if not clips:
        return result
    from datetime import datetime, timedelta
    import subprocess
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cutoff_str = cutoff.strftime("%Y%m%d")
    verified = []
    for clip in clips:
        vid_id = clip.get("video_id", "")
        try:
            r = subprocess.run(
                ["yt-dlp", "--print", "%(upload_date)s", "--no-download",
                 "https://www.youtube.com/watch?v=" + vid_id],
                capture_output=True, text=True, timeout=15
            )
            date_str = r.stdout.strip()
            if date_str and date_str != "NA" and date_str >= cutoff_str:
                clip["upload_date"] = date_str
                verified.append(clip)
                logger.info(f"  FRESHNESS VERIFIED: {clip.get('channel','')} {vid_id} uploaded {date_str}")
            elif date_str and date_str != "NA":
                logger.warning(f"  FRESHNESS REJECTED: {clip.get('channel','')} {vid_id} uploaded {date_str} older than {max_age_hours}h")
            else:
                verified.append(clip)
                logger.warning(f"  FRESHNESS UNVERIFIED: {clip.get('channel','')} {vid_id} no date, allowing")
        except Exception as e:
            verified.append(clip)
            logger.warning(f"  FRESHNESS CHECK FAILED: {vid_id} {e}")
    logger.info(f"  FRESHNESS GATE: {len(verified)}/{len(clips)} clips passed")
    result["clips"] = verified
    return result

def select_clips_with_fallback(videos, max_clips=5):
    """Try Claude, then Qwen, then last known good, then random. NEVER return 0 clips."""

    # Attempt 1: Claude API (primary)
    try:
        result = select_clips(videos)
        if result.get("clips"):
            _save_last_good_selection(result)
            logger.info(f"FALLBACK CHAIN: Claude succeeded — {len(result['clips'])} clips")
            result = _enforce_freshness(_enforce_channel_diversity(_enforce_min_clip_duration(result)))
            return _enforce_video_id_diversity(result, videos)
        logger.warning("FALLBACK CHAIN: Claude returned 0 clips, trying Qwen...")
    except Exception as e:
        logger.error(f"FALLBACK CHAIN: Claude failed: {e}")

    # Attempt 2: Local Qwen via Ollama
    try:
        result = _select_clips_local(videos, max_clips)
        if result.get("clips"):
            _save_last_good_selection(result)
            _record_episode(result["clips"])  # V36 FIX: Record Qwen clips to prevent repeats
            logger.info(f"FALLBACK CHAIN: Qwen succeeded — {len(result['clips'])} clips")
            result = _enforce_freshness(_enforce_channel_diversity(_enforce_min_clip_duration(result)))
            return _enforce_video_id_diversity(result, videos)
        logger.warning("FALLBACK CHAIN: Qwen returned 0 clips, trying last known good...")
    except Exception as e:
        logger.error(f"FALLBACK CHAIN: Qwen failed: {e}")

    # Attempt 3: Last known good selection — FILTER against used_clips
    last_good = _load_last_good_selection()
    if last_good and last_good.get("clips"):
        blocked_ids = _get_recent_video_ids()
        filtered_clips = [c for c in last_good["clips"] if c.get("video_id", "") not in blocked_ids]
        rejected = len(last_good["clips"]) - len(filtered_clips)
        if rejected:
            logger.warning(f"FALLBACK CHAIN: Filtered {rejected} stale clips from last_known_good")
        if filtered_clips:
            last_good["clips"] = filtered_clips
            logger.warning(f"FALLBACK CHAIN: Using LAST KNOWN GOOD — {len(filtered_clips)} clips (after diversity filter)")
            return _enforce_channel_diversity(_enforce_min_clip_duration(last_good))
        else:
            logger.warning("FALLBACK CHAIN: last_known_good ALL clips blocked by 3-day window, skipping")

    # Attempt 4: Random selection (absolute last resort)
    logger.error("FALLBACK CHAIN: ALL methods failed — random selection")
    import random
    shuffled = list(videos)
    random.shuffle(shuffled)
    clips = []
    seen_channels = set()
    for v in shuffled:
        ch = v.get("channel", "")
        if ch in seen_channels:
            continue
        seen_channels.add(ch)
        text = v.get("transcript_text", v.get("timestamped_text", ""))
        clips.append({
            "rank": len(clips) + 1,
            "video_id": v.get("video_id", ""),
            "channel": ch,
            "video_title": v.get("title", ""),
            "start_seconds": 15,
            "end_seconds": 45,
            "quote": text[:200] if text else "",
            "why": "Fallback random selection",
            "host_setup": "",
            "host_react": "",
        })
        if len(clips) >= max_clips:
            break
    return {"clips": clips, "episode_title": "Pulse Check", "cold_open": ""}


def select_montage_clips(videos: list) -> dict:
    # P0: Single Qwen health check
    try:
        import requests as _mreq
        _r = _mreq.get("http://localhost:11434/api/tags", timeout=3)
        _models = _r.json().get("models", [])
        if not _models:
            logger.warning("MONTAGE SKIP: Qwen not loaded")
            return {"clips": []}
    except Exception:
        logger.warning("MONTAGE SKIP: Ollama unreachable")
        return {"clips": []}

    """Independent montage clip selection using local Qwen3-Coder.

    Selects the best 12-22 second standalone moment from each video.
    Completely independent from select_clips() — different timestamps, different criteria.
    Falls back to Pulse Check clip timestamps if Qwen unavailable.
    """
    import requests
    import json as _json
    import re as _re

    OLLAMA_URL = "http://localhost:11434"
    MODEL = "qwen3-coder:30b"
    montage_clips = []

    for video in videos:
        video_id = video.get("video_id", "")
        channel = video.get("channel", "")
        title = video.get("title", "")
        timestamped_text = video.get("timestamped_text", "") or video.get("transcript_text", "")

        if not timestamped_text or len(timestamped_text) < 100:
            logger.info(f"[Montage] No transcript for {channel} {video_id}, skipping")
            continue

        prompt = (
            "You are selecting the single best SHORT standalone highlight clip for a daily "
            "Bitcoin media compilation. Viewers have ZERO prior context.\n\n"
            "Select the 12-22 second window that is the most punchy, self-contained, "
            "and quotable moment in this entire video.\n"
            "CRITERIA:\n"
            "- Complete thought — starts and ends at natural sentence boundaries\n"
            "- No context needed to understand it\n"
            "- Single strong statement or striking data point\n"
            "- NOT the same as the Pulse Check clip (find a DIFFERENT moment)\n"
            "- Ideal: starts with a strong noun or number, ends with a period\n\n"
            f"VIDEO: {title}\nCHANNEL: {channel}\n\n"
            f"TIMESTAMPED TRANSCRIPT:\n{timestamped_text[:3000]}\n\n"
            'Return ONLY valid JSON, no markdown:\n'
            '{"montage_start_sec": int, "montage_end_sec": int, '
            '"quote": "exact words spoken", "reason": "why this moment"}'
        )

        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODEL,
                    "messages": [{"role": "system", "content": "Respond with valid JSON only. No thinking. No markdown. No explanation."}, {"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=30,
            )
            resp.raise_for_status()
            raw = resp.json().get("message", {}).get("content", "")
            match = _re.search(r"\{[^{}]+\}", raw, _re.DOTALL)
            if match:
                result = _json.loads(match.group())
                start = int(result.get("montage_start_sec", 0))
                end = int(result.get("montage_end_sec", start + 18))
                # Validate reasonable range
                if 0 <= start < end and (end - start) <= 30:
                    montage_clips.append({
                        "rank": len(montage_clips) + 1,
                        "video_id": video_id,
                        "channel": channel,
                        "video_title": title,
                        "start_seconds": start,
                        "end_seconds": end,
                        "quote": result.get("quote", ""),
                        "score": video.get("score", 50),
                        "timestamped_text": timestamped_text,
                        "montage_reason": result.get("reason", ""),
                    })
                    logger.info(f"[Montage] {channel}: {start}s-{end}s — {result.get('quote', '')[:60]}")
                    continue
        except Exception as e:
            logger.warning(f"[Montage] Qwen failed for {channel}: {e}")

        # Fallback: skip — montage will have fewer clips if Qwen unavailable
        logger.info(f"[Montage] {channel}: using fallback empty (Qwen unavailable)")


    return {"clips": montage_clips}


if __name__ == "__main__":
    # Test with cached transcripts or live scan
    from channel_scanner import scan_all_channels
    videos = scan_all_channels()
    if videos:
        selections = select_clips(videos)
        print(json.dumps(selections, indent=2))
    else:
        print("No videos found to select from")
