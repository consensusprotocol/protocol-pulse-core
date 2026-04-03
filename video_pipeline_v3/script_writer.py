import sys; sys.dont_write_bytecode = True
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
import re
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

SCRIPT_PROMPT = """You are PBX — a Bitcoin intelligence analyst and cypherpunk. You deliver sovereign signal intelligence to an audience that ALREADY understands Bitcoin. You don't educate newcomers. You deliver intelligence.

VOICE RULES:
- Direct. Authoritative. Opinionated.
- Maximum 2 sentences per clip introduction. No rambling.
- BANNED PHRASES: "Let's dive in", "Great point", "It's worth noting", "Interestingly", "Without further ado", "In today's episode", "Let's break this down", "Here's the thing", "Buckle up", "game changer", "Bitcoin continues to", "the market is watching", "this is significant", "interesting to note", "worth keeping an eye on"
- Use numbers naturally: "sixty-seven thousand" not "sixty-seven thousand one hundred and forty-six"
- Round Bitcoin price to nearest thousand in speech
- You have conviction. You take sides. You're not neutral.
- NEVER write "BTC" — always write "Bitcoin" in full.
- NEVER say "today", "this morning", "just now" about a KOL quote/tweet unless the data confirms it is from the last 24 hours. If no timestamp, use "recently said", "has been saying".
- When referencing a social media handle, write the person's NAME, not their handle. "Preston Pysh posted" not "@PrestonPysh".
- Never hedge. No "could", "might", "it remains to be seen."
- Respect the audience — they know what a UTXO is. Never explain basics.

STRUCTURE (mandatory):
1. COLD OPEN (1-2 sentences): Start with the single most provocative insight from today's clips. No greeting. No intro. Drop the viewer into the action.
   Example: "Marathon just dumped fifteen thousand Bitcoin — and they're telling you it's bullish. Let's look at what's really happening."

2. THEME STATEMENT (1 sentence): Connect all clips with ONE thesis.
   Example: "Today, three signals are converging on the same conclusion: institutions are front-running the next halving cycle."

3. CLIP SEGMENTS (one per clip, 2-3 sentences each):
   - Setup (1-2 sentences): Why this clip matters RIGHT NOW. Sharp framing angle + one specific data point.
   - [CLIP plays]
   - Reaction (2-3 sentences): Your take. Be opinionated. Agree or disagree with the clip. Start with the IMPLICATION: "What this means is—", "The signal here is—", "Nobody's talking about—"

4. DATA SEGMENT: Hard metrics. Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. 3-4 lines minimum. Each with a metric AND an implication.

5. SOCIAL SEGMENT (if social posts data provided below — skip entirely if "NONE"):
   PBX reporting back from Bitcoin Twitter as live intelligence. Maximum 3 tweets. PBX decodes the signal, he doesn't repeat the text — the tweet card is on screen.
   Each entry uses type: "social_segment". Each MUST begin with the tweet's segment ID: "[ID:tweet_XXXXXXXX_N] ..."
   TWEET LAW: Reference social_posts in order. NEVER reference a name not in the list.
   TWEET FRESHNESS: Only say "just posted" if timestamp is from current day. Otherwise "posted recently".

6. SPACE TAP (only if space_tap_clips provided below):
   Intelligence briefing opener. For each clip: one sentence intro + clip plays + one sentence reaction.
   Format: {{"host": 2, "text": "[SPACE_TAP] ...", "type": "space_tap_intro"}}, {{"host": "SPACE_CLIP", "clip_index": N}}, {{"host": 2, "text": "[SPACE_TAP] ...", "type": "space_tap_react"}}

7. SYNTHESIS (2-3 sentences): What does all of this mean? One original PBX observation nobody else said today.

8. SIGNOFF: "Stay sovereign. This has been Protocol Pulse."

SEGMENT TAGGING (MANDATORY — controls PBX's voice dynamics):
Every dialogue text line MUST start with a segment type tag in brackets:
  [COLD_OPEN] — opening hook (dramatic). MAX 2 per episode.
  [NARRATION] — standard narration, setup, analysis. 70-80% of lines.
  [DATA] — specific metrics, prices, hashrates. Authoritative.
  [SOCIAL] — social segment commentary. Warmer tone.
  [WARM] — outros, sign-offs. Inviting.
The tag is INSIDE the text string AND the type field must be present.

EPISODE LENGTH: Target 550-680 narration words. Every sentence earns its place. NO padding.

{clips_info}

BTC Price Today: {btc_price}
Top Tweets/Nostr Posts Today: {social_posts}
{live_context}
Return ONLY valid JSON (no markdown, no code fences):
{{
  "episode_title": "short punchy title, 6 words max",
  "theme": "one sentence connecting all clips",
  "cold_open": "explosive 1-sentence cold open",
  "dialogue": [
    {{"host": 2, "text": "[COLD_OPEN] ...", "type": "cold_open"}},
    {{"host": 2, "text": "[NARRATION] ...", "type": "setup", "clip_rank": 1}},
    {{"host": "CLIP", "rank": 1}},
    {{"host": 2, "text": "[NARRATION] ...", "type": "react", "clip_rank": 1}},
    {{"host": 2, "text": "[NARRATION] ...", "type": "setup", "clip_rank": 2}},
    {{"host": "CLIP", "rank": 2}},
    {{"host": 2, "text": "[NARRATION] ...", "type": "react", "clip_rank": 2}},
    ...for all clips...
    {{"host": 2, "text": "[DATA] ...", "type": "data"}},
    {{"host": 2, "text": "[SOCIAL] ...", "type": "social_segment"}},
    {{"host": 2, "text": "[NARRATION] ...", "type": "wrap"}},
    {{"host": 2, "text": "[WARM] Stay sovereign. This has been Protocol Pulse.", "type": "wrap"}}
  ],
  "thumbnail": {{"headline": "3-5 words, ALL CAPS", "subtext": "one line"}},
  "segments_summary": ["4-8 WORD ALL CAPS EDITORIAL HEADLINE FOR EACH CLIP"],
  "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
}}

IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5). ALL host entries MUST be host: 2."""


# Maps bracket tags in text to segment types for TTS voice modes
_TAG_TO_TYPE = {
    "COLD_OPEN": "cold_open",
    "NARRATION": "setup",
    "DATA": "data",
    "SOCIAL": "social_segment",
    "WARM": "wrap",
    "BRIDGE": "setup",  # inter-clip context bridges treated as narration
    "SPACE_TAP": "space_tap",
    "SETUP": "setup",
    "REACT": "react",
    "CTA": "wrap",
    "COLD": "cold_open",
}

_TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")


def preprocess_for_speech(text):
    """Make text sound natural when spoken by PBX.

    - Rounds BTC prices to nearest thousand
    - Removes URLs (not spoken)
    - Cleans up parenthetical percentages
    """
    # Round BTC prices to nearest thousand: "$67,146" → "$67,000"
    def _round_btc_price(m):
        whole = m.group(1)
        return f"${whole},000"
    text = re.sub(r'\$(\d{2,3}),\d{3}(?!\d)', _round_btc_price, text)
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Clean extra whitespace
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def _extract_segment_tags(result: dict) -> dict:
    """Extract [TAG] prefixes from dialogue text and set entry type accordingly.

    If a dialogue line starts with [NARRATION], [DATA], etc., strip the tag
    from the text and set/override the type field for TTS voice mode selection.
    """
    dialogue = result.get("dialogue", [])
    # Force PBX-only: normalize any host:1 → host:2
    for _e in dialogue:
        if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
    for entry in dialogue:
        text = entry.get("text", "")
        if not text:
            continue
        m = _TAG_PATTERN.match(text)
        if m:
            tag = m.group(1)
            entry["text"] = text[m.end():]
            entry["type"] = _TAG_TO_TYPE[tag]
    # Normalize space_tap subtypes to "space_tap" so assembler _segment_to_scene matches
    for entry in dialogue:
        if entry.get("type", "") in ("space_tap_intro", "space_tap_react"):
            entry["type"] = "space_tap"
    return result


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


def _load_narrative_context() -> dict:
    """Load narrative_context.json for narrative-aware script generation.
    Returns empty dict if missing or stale (>4hr old).
    KOL FRESHNESS LAW: tightened from 6h to 4h to prevent stale quotes."""
    import os
    from datetime import datetime, timezone
    ctx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "intelligence", "narrative_context.json")
    try:
        with open(ctx_path) as f:
            ctx = json.load(f)
        # Check staleness — 4h max to match narrative scan window
        computed = ctx.get("computed_at", "")
        if computed:
            computed_dt = datetime.fromisoformat(computed.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - computed_dt).total_seconds() / 3600
            if age_hours > 4:
                logger.warning(f"Narrative context is {age_hours:.1f}h old (>4h) — using generic prompt")
                return {}
        return ctx
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Narrative context unavailable: {e}")
        return {}


NARRATIVE_INJECTION = """
TODAY'S LIVE NARRATIVE CONTEXT (from real-time thought leader monitoring):
Dominant narrative: {dominant_narrative}
Market mood: {market_mood}
What thought leaders are saying: {episode_narrative}
PBX cold open hook: {pbx_intro_hook}
PBX analysis angle: {pbx_context}
Suggested bridge lines: {narrative_bridge_lines}

MANDATORY SCRIPT RULES (from narrative context):
- PBX's cold open MUST reference the dominant narrative in his first sentence
- At least ONE of the clips must be explicitly connected to the X discourse
  (e.g., "This is what everyone on Crypto Twitter has been discussing all morning...")
- PBX must cite at least one specific data point from the narrative context (not generic)
- Avoid topics flagged in: {avoid_topics}
- The show must feel LIVE — like PBX has been tracking this story all morning
- KOL QUOTE FRESHNESS: If a thought leader quote is provided, do NOT claim it was said "today" or "this morning" unless you can verify from the data timestamp. Use neutral framing like "has been saying" or "recently stated" for undated quotes. This prevents misinformation.

DATA SEGMENT REQUIREMENT: The data/metrics discussed must relate to today's
dominant narrative ({dominant_narrative}). If narrative is "ETF inflows",
cite actual ETF flow numbers. If "mining difficulty", cite actual hashrate/difficulty data.
PBX must sound like an analyst who read the numbers this morning, not a generalist.
"""


def _validate_social_tweet_order(result: dict, social_posts_raw: str) -> dict:
    """Render11 FIX 5: Ensure narrator tweet references match tweet display order.

    If narrator mentions @handle that doesn't match the expected tweet position,
    reorder social_segment entries so card display matches narration order.
    Tags each social entry with _social_handle_ref for assembler card matching.
    """
    if not social_posts_raw or social_posts_raw.startswith("NONE"):
        return result

    dialogue = result.get("dialogue", [])
    # Force PBX-only: normalize any host:1 → host:2
    for _e in dialogue:
        if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
    if not dialogue:
        return result

    # Extract ordered handles from social_posts_raw (sorted by likes in generate_from_clips)
    social_handles = []
    for line in social_posts_raw.split("\n"):
        m = re.match(r'(?:Tweet \d+: )?@(\w+)\s+tweeted:', line)
        if m:
            social_handles.append(m.group(1).lower())

    # Extract @handle references from social_segment narration lines
    social_entries = [(i, e) for i, e in enumerate(dialogue)
                      if e.get("type") == "social_segment" and e.get("host") in (1, 2, "1", "2")]

    narrator_handles = []
    for _, entry in social_entries:
        text = entry.get("text", "")
        handles_in_text = re.findall(r'@(\w+)', text)
        for h in handles_in_text:
            h_lower = h.lower()
            if h_lower in social_handles and h_lower not in narrator_handles:
                narrator_handles.append(h_lower)

    # Tag each social entry with its referenced handle
    for idx, entry in social_entries:
        text = entry.get("text", "")
        handles_in_text = [h.lower() for h in re.findall(r'@(\w+)', text)]
        matched = [h for h in handles_in_text if h in social_handles]
        if matched:
            entry["_social_handle_ref"] = matched[0]
            logger.info(f"[script] Social segment line {idx} references @{matched[0]}")

    # Render12 FIX 2: Assert strict tweet order — first card shown = first referenced
    if narrator_handles and social_handles:
        expected = social_handles[:len(narrator_handles)]
        if narrator_handles != expected:
            logger.warning(f"[script] TWEET ORDER VIOLATION: narrator={narrator_handles}, expected={expected} — reordering")
        else:
            logger.info(f"[script] TWEET ORDER OK: {narrator_handles}")

    # FIX 5: Reorder social_segment entries so narration order matches display order
    # The social_posts were sorted by likes desc — narrator should mention them in that order
    if narrator_handles and social_handles and narrator_handles != social_handles[:len(narrator_handles)]:
        logger.warning(f"[script] TWEET MISMATCH: narrator={narrator_handles}, data={social_handles[:len(narrator_handles)]}")
        # Reorder social_segment dialogue entries to match data order
        social_with_handle = [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]
        if social_with_handle:
            # Sort by position in social_handles (data order = likes desc)
            social_with_handle.sort(
                key=lambda x: social_handles.index(x[1]["_social_handle_ref"])
                if x[1]["_social_handle_ref"] in social_handles else 999
            )
            # Swap entries in-place in dialogue
            original_indices = [i for i, _ in [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]]
            for new_pos, (_, entry) in enumerate(social_with_handle):
                if new_pos < len(original_indices):
                    dialogue[original_indices[new_pos]] = entry
            logger.info(f"[script] Reordered social entries to match data order")

    return result


def _make_editorial_headline(raw: str) -> str:
    """Convert a raw summary/title into a 3-7 word ALL CAPS editorial headline.

    Render11 FIX 8: Strict Bloomberg/newspaper front page format.
    No punctuation except dash. 3-7 words. Always ALL CAPS.
    BAD: 'Saylor talks about sonic boom theory'
    GOOD: 'SAYLOR SONIC BOOM BITCOIN THESIS'
    """
    import re
    # Strip quotes, URLs, timestamps, punctuation (except dash)
    clean = re.sub(r'https?://\S+', '', raw)
    clean = re.sub(r'["\'\[\]().,;:!?]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Take first 7 words, uppercase
    words = clean.split()[:7]
    headline = " ".join(words).upper()
    # Ensure minimum 3 words
    if len(words) < 3:
        headline = headline + " - BREAKING"
    # FIX 8: Post-generation validation — force ALL CAPS, strip non-conforming chars
    headline = re.sub(r'[^A-Z0-9 \-/]', '', headline).strip()
    if not headline or len(headline) < 5:
        headline = "BREAKING SIGNAL DETECTED"
    return headline[:55]


def _populate_segment_headlines(result: dict) -> dict:
    """Session 4 Fix 2: Add 'headline' key to each dialogue entry.

    Maps segment type + clip rank to a meaningful headline so _smart_headline()
    in assembler.py gets a real headline instead of truncated spoken text.
    Render11 FIX 8: Headlines are 3-7 word ALL CAPS editorial style with regex validation.
    """
    dialogue = result.get("dialogue", [])
    # Force PBX-only: normalize any host:1 → host:2
    for _e in dialogue:
        if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
    summaries = result.get("segments_summary", [])
    episode_title = result.get("episode_title", "Pulse Check Daily")

    for entry in dialogue:
        if entry.get("headline"):
            continue  # already has one
        host = entry.get("host")
        if host == "CLIP":
            continue  # clip markers don't need headlines

        seg_type = entry.get("type", "")
        clip_rank = entry.get("clip_rank", 0)

        if seg_type == "cold_open":
            entry["headline"] = _make_editorial_headline(episode_title)
        elif seg_type in ("setup", "react") and clip_rank:
            # Use segments_summary keyed by rank — force editorial style
            idx = clip_rank - 1
            if 0 <= idx < len(summaries) and summaries[idx]:
                entry["headline"] = _make_editorial_headline(summaries[idx])
            else:
                entry["headline"] = _make_editorial_headline(episode_title)
        elif seg_type == "data":
            entry["headline"] = "TODAY'S INTELLIGENCE"
        elif seg_type == "social_segment":
            entry["headline"] = "SIGNAL FROM THE FIELD"
        elif seg_type == "space_tap":
            entry["headline"] = "SPACE TAP SIGNAL INTERCEPT"
        elif seg_type in ("wrap", "outro"):
            entry["headline"] = "STAY SOVEREIGN"
        elif seg_type == "bridge":
            entry["headline"] = _make_editorial_headline(episode_title)
        else:
            # Generic narrator — use episode title
            entry["headline"] = _make_editorial_headline(episode_title)

    # Render11 FIX 8: Post-validation — force ALL CAPS, reject >8 words or lowercase
    for entry in dialogue:
        h = entry.get("headline", "")
        if not h or entry.get("host") == "CLIP":
            continue
        # Force uppercase and strip non-conforming chars
        h = re.sub(r'[^A-Z0-9 \-/]', '', h.upper()).strip()
        words = h.split()
        if len(words) > 8:
            h = " ".join(words[:7])
        if not h or len(h) < 5:
            h = "BREAKING SIGNAL DETECTED"
        entry["headline"] = h

    return result


def generate_from_clips(selections: dict, btc_price: str = "N/A",
                        live_context: str = "", morning_brief: dict = None,
                        social_posts_sorted: list = None) -> dict:
    """Generate host dialogue script around the selected clips.

    Args:
        selections: Output from clip_selector.select_clips()
        btc_price: Current BTC price string
        live_context: Real-time live stream/Spaces intelligence (optional)
        social_posts_sorted: Pre-fetched, sorted social posts (single source of truth from daily_producer)

    Returns:
        Script dict with dialogue array
    """
    clips = selections.get("clips", [])
    if not clips:
        logger.error("No clips provided for script generation")
        return _fallback_script(selections)

    from relay import call_llm

    clips_info = _format_clips_info(selections)

    # Social data — use pre-fetched sorted list from daily_producer (single source of truth)
    # Fallback: fetch here if caller didn't provide (backwards compat)
    social_data_sorted = social_posts_sorted or []
    if not social_data_sorted:
        try:
            from utils.social_fetcher import get_todays_social_posts
            social_data = get_todays_social_posts(max_posts=5)
            if social_data:
                social_data_sorted = sorted(social_data, key=lambda x: x.get('likes', 0), reverse=True)
        except Exception as e:
            logger.warning(f"Social data fetch failed: {e}")

    if social_data_sorted:
        social_posts = "\n".join([
            f"Tweet {ti+1} [ID:{p.get('seg_id', f'tweet_unknown_{ti}')}]: @{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
            + (f" [posted: {p['created_at']}]" if p.get('created_at') else " [date unknown]")
            for ti, p in enumerate(social_data_sorted)
        ])
        social_posts += (
            "\n\nCRITICAL SOCIAL RULES:"
            "\n- Read ONLY what is written above. Do NOT paraphrase, add, or invent words."
            "\n- Quote tweet text DIRECTLY and verbatim."
            "\n- Reference tweets BY POSITION: 'Tweet 1 from @handle' matches the first tweet listed above."
            "\n- If you mention @handle, the DISPLAYED tweet card MUST match that handle."
            "\n- Never attribute words from one tweet to a different person."
            "\n- FRESHNESS: Check the [posted: ...] timestamp. Only say 'just posted' or 'today' if"
            "\n  the timestamp is from the current day. If [date unknown], say 'recently posted'."
        )
    else:
        social_posts = "NONE — skip social segment entirely"

    # Build live context block
    live_block = ""
    if live_context:
        live_block = (
            "\nLIVE INTELLIGENCE: The following events are happening RIGHT NOW or happened "
            "in the last few hours on Bitcoin YouTube/X Spaces. Reference these naturally "
            "in your narration to make the episode feel current and urgent:\n"
            f"{live_context}\n"
        )

    # Inject narrative context from thought leader monitoring
    narrative_ctx = _load_narrative_context()
    if narrative_ctx and narrative_ctx.get("dominant_narrative"):
        try:
            bridge_lines = narrative_ctx.get("narrative_bridge_lines", [])
            narrative_block = (NARRATIVE_INJECTION
                .replace("{dominant_narrative}", narrative_ctx.get("dominant_narrative", ""))
                .replace("{market_mood}", narrative_ctx.get("market_mood", ""))
                .replace("{episode_narrative}", narrative_ctx.get("episode_narrative", ""))
                .replace("{pbx_intro_hook}", narrative_ctx.get("eryn_intro_hook", narrative_ctx.get("pbx_intro_hook", "")))
                .replace("{pbx_context}", narrative_ctx.get("mark_context", narrative_ctx.get("pbx_context", "")))
                .replace("{narrative_bridge_lines}", "\n".join(bridge_lines) if bridge_lines else "none")
                .replace("{avoid_topics}", ", ".join(narrative_ctx.get("avoid_topics", [])))
            )
            live_block = narrative_block + "\n" + live_block
            logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")
        except Exception as e:
            logger.warning(f"Failed to inject narrative context: {e}")

    # Inject morning intelligence brief (Nitter-sourced Twitter analysis)
    morning_block = ""
    if morning_brief and isinstance(morning_brief, dict):
        parts = ["\nMORNING INTELLIGENCE BRIEF (from today's Bitcoin Twitter analysis — use as context):"]
        dom_narr = morning_brief.get("dominant_narratives", [])
        if dom_narr:
            parts.append(f"- Dominant narratives today: {'; '.join(dom_narr[:3])}")
        trending_lang = morning_brief.get("trending_language", [])
        if trending_lang:
            parts.append(f"- Trending language on Bitcoin Twitter: {', '.join(trending_lang[:7])}")
            parts.append("  USE these phrases naturally in narration where they fit — they resonate with the audience today.")
        sentiment = morning_brief.get("sentiment", "")
        reasoning = morning_brief.get("sentiment_reasoning", "")
        if sentiment:
            parts.append(f"- Market sentiment: {sentiment}")
        if reasoning:
            parts.append(f"  Reasoning: {reasoning[:200]}")
        voice_guidance = morning_brief.get("protocol_pulse_voice_guidance", "")
        if voice_guidance:
            parts.append(f"- Voice guidance: {voice_guidance[:250]}")
        morning_block = "\n".join(parts) + "\n"
        logger.info(f"Morning brief injected: {len(dom_narr)} narratives, {len(trending_lang)} trending phrases")

    # Inject audience engagement intelligence
    engagement_block = ""
    try:
        import sys as _sys
        _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
        if _data_dir not in _sys.path:
            _sys.path.insert(0, _data_dir)
        from engagement_scorer import get_trending_topics, get_top_channels
        trending = get_trending_topics()[:3]
        top_chs = get_top_channels(5)
        if trending or top_chs:
            parts = ["\nAUDIENCE ENGAGEMENT INTELLIGENCE (from real audience data — use naturally):"]
            if trending:
                topics_str = ", ".join(f"{t[0]} ({t[1]:.1f}/10)" for t in trending)
                parts.append(f"- Currently trending in our audience: {topics_str} — weight these if relevant.")
            if top_chs:
                chs_str = ", ".join(f"{c[0]} ({c[1]:.1f})" for c in top_chs)
                parts.append(f"- Highest engagement channels this week: {chs_str} — prioritize their clips.")
            engagement_block = "\n".join(parts) + "\n"
            logger.info(f"Engagement intelligence injected: {len(trending)} topics, {len(top_chs)} channels")
    except Exception as e:
        logger.debug(f"Engagement scorer unavailable: {e}")

    # Inject episode memory feedback if enough history exists
    memory_block = ""
    try:
        from episode_memory import get_episode_count, get_weak_dimensions, get_strong_dimensions, get_best_channels
        if get_episode_count() >= 5:
            weak = get_weak_dimensions(threshold=6.0)
            strong = get_strong_dimensions(threshold=8.0)
            top_ch = get_best_channels(5)
            parts = ["\nEPISODE MEMORY FEEDBACK (from past renders — adapt accordingly):"]
            if weak:
                dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in weak[:5])
                parts.append(f"- WEAK AREAS (improve these): {dims}")
            if strong:
                dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in strong[:5])
                parts.append(f"- STRONG AREAS (maintain these): {dims}")
            if top_ch:
                chs = ", ".join(f"{c['channel']} ({c['avg_score']})" for c in top_ch)
                parts.append(f"- TOP CHANNELS by quality score: {chs}")
            memory_block = "\n".join(parts) + "\n"
            logger.info(f"Episode memory injected: {len(weak)} weak, {len(strong)} strong dimensions")
    except Exception as e:
        logger.warning(f"Episode memory unavailable: {e}")

    # Inject Space Tap clips context if available
    space_tap_block = ""
    space_tap_clips = selections.get("space_tap_clips", [])
    if space_tap_clips:
        parts = ["\nSPACE TAP CLIPS (X Spaces intercepts — generate [SPACE_TAP] segment):"]
        for i, sc in enumerate(space_tap_clips):
            handle = sc.get("host_handle", "unknown")
            text_preview = sc.get("text", "")[:150]
            parts.append(f"  Clip {i}: @{handle} — \"{text_preview}\"")
        parts.append(f"Generate intro + react for each of the {len(space_tap_clips)} clips above.")
        space_tap_block = "\n".join(parts) + "\n"

    prompt = (SCRIPT_PROMPT
        .replace("{clips_info}", str(clips_info))
        .replace("{btc_price}", str(btc_price))
        .replace("{social_posts}", str(social_posts))
        .replace("{live_context}", str(live_block+morning_block+engagement_block+memory_block+space_tap_block))
    )

    logger.info(f"Generating script for {len(clips)} clips...")
    text = call_llm(prompt, max_tokens=8000, model="claude-sonnet-4-6")
    if text is None:
        logger.warning("All LLM providers failed, using fallback script")
        return _fallback_script(selections)

    try:

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        # FIX 4: JSON retry loop — send malformed JSON back for repair, max 3 retries
        json_text = text
        result = None
        for _retry in range(4):  # attempt 0 = first try, 1-3 = retries
            try:
                result = json.loads(json_text)
                break
            except json.JSONDecodeError as je:
                if _retry >= 3:
                    raise RuntimeError(f"JSON repair failed after 3 retries: {je}") from je
                logger.warning(f"JSON parse error (retry {_retry+1}/3): {je}")
                repair_prompt = (
                    f"The following JSON is malformed. Fix it and return ONLY valid JSON, "
                    f"no markdown, no explanation:\n\n{json_text}\n\n"
                    f"Error was: {je}"
                )
                json_text = call_llm(repair_prompt, max_tokens=8000, model="claude-sonnet-4-6")
                if json_text is None:
                    raise RuntimeError("JSON repair LLM call returned None")
                # Strip code fences from repair response
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0]
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0]

        # Extract [TAG] prefixes from text and set type fields for TTS
        result = _extract_segment_tags(result)

        # V4: Preprocess text for natural speech (round prices, strip URLs)
        for _entry in result.get("dialogue", []):
            if _entry.get("host") not in ("CLIP", "SPACE_CLIP") and _entry.get("text"):
                _entry["text"] = preprocess_for_speech(_entry["text"])

        # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
        result = _populate_segment_headlines(result)

        # Round 2 Fix 5: Validate social segment tweet order matches narration references
        result = _validate_social_tweet_order(result, social_posts)
        result = _enforce_setup_per_clip(result, selections)

        # Enforce social segment presence when social data was provided
        result = _enforce_social_segment(result, social_data_sorted)

        # Enforce space tap segment presence when space tap clips were provided
        result = _enforce_space_tap_segment(result, selections.get("space_tap_clips", []))

        # V4.2 FIX 5: Force-append "Stay sovereign" signoff if missing
        dialogue = result.get("dialogue", [])
        if not any("stay sovereign" in d.get("text", "").lower() for d in dialogue
                    if isinstance(d, dict)):
            logger.warning("[script] SIGNOFF MISSING — force-appending 'Stay sovereign'")
            dialogue.append({
                "host": 2,
                "text": "Stay sovereign. This has been Protocol Pulse.",
                "type": "wrap",
                "headline": "STAY SOVEREIGN",
            })

        # Validate structure
        # Force PBX-only: normalize any host:1 â host:2
        for _e in dialogue:
            if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
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



def _enforce_setup_per_clip(result: dict, selections: dict) -> dict:
    """IRON LAW: Every clip rank must have exactly one SETUP segment before it.
    If the LLM collapses two setups onto clip_rank 1 and skips clip_rank 2,
    this function detects and repairs it by inserting a bridging setup."""
    import logging
    _log = logging.getLogger(__name__)
    dialogue = result.get("dialogue", [])
    clips = selections.get("clips", [])
    clip_ranks = [c.get("rank", 0) for c in clips if c.get("rank")]

    # Find which ranks have a setup
    setup_ranks = set()
    for entry in dialogue:
        if isinstance(entry, dict) and entry.get("type") == "setup":
            cr = entry.get("clip_rank")
            if cr:
                setup_ranks.add(cr)

    missing = [r for r in clip_ranks if r not in setup_ranks]
    if not missing:
        return result

    _log.warning(f"[script] SETUP MISSING for clip ranks: {missing} — inserting bridge narration")
    clips_by_rank = {c.get("rank"): c for c in clips}
    new_dialogue = []
    for entry in dialogue:
        if isinstance(entry, dict) and entry.get("host") == "CLIP":
            rank = entry.get("rank", 0)
            if rank in missing:
                ch = clips_by_rank.get(rank, {}).get("channel", "our next source")
                bridge = {
                    "host": 2,
                    "text": f"[NARRATION] Now — {ch} brings a signal you need to hear.",
                    "type": "setup",
                    "clip_rank": rank,
                    "headline": f"{ch.upper()} SIGNAL"
                }
                new_dialogue.append(bridge)
                missing.remove(rank)
        new_dialogue.append(entry)
    result["dialogue"] = new_dialogue
    return result

def _enforce_social_segment(result: dict, social_data: list) -> dict:
    """Postcondition: if social_data was non-empty, at least one social_segment MUST exist.
    If the LLM omitted social segments, inject them before the wrap."""
    if not social_data:
        return result

    dialogue = result.get("dialogue", [])
    social_entries = [d for d in dialogue if d.get("type") == "social_segment"]
    if social_entries:
        return result  # LLM did its job

    logger.warning(f"[script] SOCIAL SEGMENT MISSING — LLM omitted {len(social_data)} tweets. Injecting.")

    # Build social_segment entries from the actual tweet data
    inject = []
    for i, post in enumerate(social_data[:3]):
        handle = post.get("handle", "unknown")
        text = post.get("text", "")[:200]
        likes = post.get("likes", 0)
        narration = (
            f"[SOCIAL] {handle} posted this to {likes:,} likes — \"{text}\". "
            f"The signal here is clear."
        )
        inject.append({
            "host": 2,
            "text": narration,
            "type": "social_segment",
        })

    # Insert before the final wrap entry
    wrap_idx = None
    for i in range(len(dialogue) - 1, -1, -1):
        if dialogue[i].get("type") == "wrap":
            wrap_idx = i
            break

    if wrap_idx is not None:
        for j, entry in enumerate(inject):
            dialogue.insert(wrap_idx + j, entry)
    else:
        dialogue.extend(inject)

    result["dialogue"] = dialogue
    logger.info(f"[script] Injected {len(inject)} social_segment entries")
    return result


def _enforce_space_tap_segment(result: dict, space_tap_clips: list) -> dict:
    """Postcondition: if space_tap_clips was non-empty, at least one SPACE_CLIP must exist.
    If the LLM omitted space tap, inject intro/clip/react entries before the wrap."""
    if not space_tap_clips:
        return result

    dialogue = result.get("dialogue", [])
    space_entries = [d for d in dialogue if d.get("host") == "SPACE_CLIP"
                     or (d.get("type") or "").startswith("space_tap")]
    if space_entries:
        return result  # LLM included space tap

    logger.warning(f"[script] SPACE TAP MISSING — LLM omitted {len(space_tap_clips)} clips. Injecting.")

    inject = []
    for i, clip in enumerate(space_tap_clips):
        handle = clip.get("host_handle", "unknown")
        inject.append({
            "host": 2,
            "text": f"[SPACE_TAP] Signal intercepted from {handle}'s space.",
            "type": "space_tap_intro",
        })
        inject.append({
            "host": "SPACE_CLIP",
            "clip_index": i,
        })
        inject.append({
            "host": 2,
            "text": "[SPACE_TAP] That's a signal worth tracking.",
            "type": "space_tap_react",
        })

    # Insert before the wrap (after social if present)
    wrap_idx = None
    for i in range(len(dialogue) - 1, -1, -1):
        if dialogue[i].get("type") == "wrap":
            wrap_idx = i
            break

    if wrap_idx is not None:
        for j, entry in enumerate(inject):
            dialogue.insert(wrap_idx + j, entry)
    else:
        dialogue.extend(inject)

    result["dialogue"] = dialogue
    logger.info(f"[script] Injected {len(inject)} space_tap entries for {len(space_tap_clips)} clips")
    return result


def _fallback_script(selections: dict) -> dict:
    """Generate a basic script from clip selections without Claude."""
    clips = selections.get("clips", [])
    cold_open = selections.get("cold_open", "Breaking developments in Bitcoin today.")

    dialogue = [
        {"host": 2, "text": f"[COLD_OPEN] {cold_open}", "type": "cold_open"},  # IRON LAW: PBX always opens
    ]

    for c in clips:
        rank = c.get("rank", 0)
        setup = c.get("host_setup", f"Check out what {c.get('channel', 'this channel')} just dropped.")
        react = c.get("host_react", "That's a big deal. The market hasn't priced this in yet.")

        dialogue.append({"host": 2, "text": f"[NARRATION] {setup}", "type": "setup", "clip_rank": rank})
        dialogue.append({"host": "CLIP", "rank": rank})
        dialogue.append({"host": 2, "text": f"[NARRATION] {react}", "type": "react", "clip_rank": rank})

    dialogue.append({
        "host": 2,
        "text": "[WARM] That's your Pulse Check for today. Stay sovereign.",
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
            {"host": 2, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},  # IRON LAW: PBX always opens
            {"host": 2, "text": "Bitcoin Magazine just dropped this bombshell.", "type": "setup", "clip_rank": 1},
            {"host": "CLIP", "rank": 1},
            {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything.", "type": "react", "clip_rank": 1},
            {"host": 2, "text": "And look at what Simply Bitcoin is reporting on hash rate.", "type": "setup", "clip_rank": 2},
            {"host": "CLIP", "rank": 2},
            {"host": 2, "text": "Record high hash rate. Miners aren't leaving. They're doubling down.", "type": "react", "clip_rank": 2},
            {"host": 2, "text": "That's your Pulse Check. Stay sovereign.", "type": "wrap"},
        ],
        "thumbnail": {"headline": "SMART MONEY IS MOVING", "subtext": "Nations are stacking"},
        "segments_summary": ["Sovereign wealth funds buying BTC", "Hash rate hits record"],
        "shorts_quotes": ["When the entities that print fiat start hoarding the exit asset", "Miners aren't leaving"],
    }


if __name__ == "__main__":
    script = generate_sample_script()
    print(json.dumps(script, indent=2))
