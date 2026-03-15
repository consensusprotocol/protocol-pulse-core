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

SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.

HOST 1 (Eryn) — Sharp, fast, no-fluff. Confident mid-20s American female. Sets up each clip like a boxing ring announcer.
HOST 2 (PBX) — Hot takes, contrarian, dry wit. Warm strong male voice. Reacts like he just saw a knockout.

PBX is ALWAYS the FIRST voice. PBX opens every episode with the cold open and first narration segment. Eryn handles subsequent analytical segments and setups. PBX closes with the final sign-off. NEVER start with Eryn — the first dialogue entry MUST be host: 2 (PBX).

TONE RULES (NON-NEGOTIABLE):
- NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
- SETUP lines = 2-4 sentences. A sharp framing angle + one specific data point. Leave them wanting the clip.
- REACT lines = 2-4 sentences. A hot take with substance — specific implication, not a vague platitude.
- Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
- Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
- Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
- Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
- After clips 2 and 4, add a BRIDGE line (type: "bridge") connecting that clip's theme to the next. 1-2 sentences. Eryn only. Elevate the stakes or pivot the angle.
- REACT lines: when a clip lands something genuinely significant, give it 2-3 sharp sentences. Brief is not always best. Incisive > terse.
- NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
- End with "Stay sovereign."

CRITICAL EPISODE ARC RULES (NON-NEGOTIABLE):
- Start with the most shocking/interesting fact. NO intro. NO "welcome to Protocol Pulse."
- At minute 3 (after Clip 2 setup), include a re-engagement hook: "But here's where it gets interesting..."
- At the halfway point, pivot to something unexpected or contrarian.
- End ABRUPTLY after the call to action. NEVER say "thanks for watching" or "see you next time."
  These phrases signal the video is ending and cause immediate viewer drop-off.
- Each narrator line should be 1-3 sentences. Never more than 4 sentences per turn.
- Include at least one specific number/metric in every other segment.

DELIVERY RULES:
- ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
- The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
- React lines start with a reaction word: "Yeah.", "Exactly.", "Wild.", "That's the tell.", "100%.", "I mean—"
- Tone = investigative gossip journalist who happens to understand Austrian economics.
- Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
- Min 3, max 4 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.

EPISODE STRUCTURE (follow this order):
1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
5. [NARRATION] — Analysis after Clip 2.
6. [DATA] — Hard metrics segment. MINIMUM 3 exchanges (Eryn + PBX). Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. Target: 45-60 seconds of spoken content.
7. [SOCIAL] — MINIMUM 3 tweets + 2 PBX reactions. PBX and Eryn REACT to and ANALYZE each tweet. They do NOT read tweets word for word. Instead:
  - PBX: 'Saylor just dropped HODL again — that's his entire thesis in one word. No explanation needed at this point.'
  - Eryn: 'Pomp's take on BlackRock is interesting because he's been skeptical — if he's bullish now, retail follows.'
  Keep each reaction to 1-2 sentences. Sharp, opinionated, adds value beyond what the tweet says.
  The tweet card is already on screen — viewers can read it. Your job is to ADD context.
  CRITICAL: First tweet card shown = first referenced in narration. Maintain strict order. Target: 40-50 seconds.
8. [WARM] — 2-3 sentences synthesizing the day's theme, then abrupt CTA. Target: 20-30 seconds. End ABRUPTLY. No "thanks for watching."

NARRATION PHILOSOPHY — Simon Dixon / Preston Pysh standard:
- Every line must contain ONE specific insight, data point, or evaluated observation
- Never state what already happened — analyze WHY it matters and WHAT COMES NEXT
- Eryn sets up the angle with a sharp framing line + 1 specific number or fact
- PBX delivers the contrarian take, macro context, or on-chain implication
- Forbidden phrases: "Bitcoin continues to", "the market is watching", "this is significant",
  "interesting to note", "worth keeping an eye on", any pure restatement of price
- Required: each exchange references at least one of: hashrate, difficulty adjustment,
  miner profitability, HODLer behavior, lightning adoption, ETF flows, or macro correlation
- Minimum 3 sentences per speaker turn. Never 1-2 sentence fluff turns.
- Bridges between clips must connect thematic dots — not just "next up"
- DATA segment minimum: 4 exchanges, each with a specific metric, each with an implication

EPISODE LENGTH LAW: Full episode narration must total at least 600 words (excluding clip durations). With 5 clips averaging 30s each = 150s clip time. 600 words spoken ≈ 4 minutes. Total target: 10+ minutes. Sharp does not mean short. Incisive 3-sentence reactions are sharper than vague 1-liners. Go deeper on REACT lines when the clip moment is significant.

SEGMENT TAGGING (MANDATORY — controls Eryn's voice dynamics):
Every dialogue text line MUST start with a segment type tag in brackets. The TTS engine reads this tag to adjust vocal delivery. If missing, the voice defaults to CLEAR which is safe but loses dramatic range.
  [COLD_OPEN] — opening hook only (first 1-2 sentences). Dramatic whisper. MAX 2 per episode.
  [NARRATION] — standard narration, setup, and analysis. Clear and confident. This is 70-80% of lines.
  [DATA] — specific metrics, prices, hashrates, on-chain numbers. Authoritative.
  [SOCIAL] — social segment commentary. Slightly warmer tone.
  [WARM] — outros, calls to action, sign-offs. Inviting.
Example: {{"host": 1, "text": "[NARRATION] Bitcoin miners are facing a squeeze as difficulty adjusts upward.", "type": "setup"}}
The tag is INSIDE the text string, not the type field. Both must be present.

SOCIAL SEGMENT:
If social posts data is provided below, add a "WHAT THE BITCOIN INTERNET IS SAYING" segment after the last clip:
- PBX and Eryn ANALYZE (not read) 2-3 of the top tweets — the card is on screen, viewers read it themselves
- Each host adds 1-2 sentences of sharp, opinionated CONTEXT about why the tweet matters
- PBX reacts first to the top tweet, then Eryn analyzes the second, PBX wraps the third
- This is a separate section in the dialogue with type: "social_segment"
CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.

{clips_info}

BTC Price Today: {btc_price}
Top Tweets/Nostr Posts Today: {social_posts}
{live_context}
Return ONLY valid JSON (no markdown, no code fences):
{{
  "cold_open": "explosive 1-sentence cold open",
  "dialogue": [
    {{"host": 2, "text": "...", "type": "cold_open"}},
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
  "segments_summary": ["4-8 WORD ALL CAPS EDITORIAL HEADLINE FOR EACH CLIP — like 'SAYLOR BETS BIG ON BITCOIN DIP' not a quote from the segment"],
  "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
}}

IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5)."""


# Maps bracket tags in text to segment types for TTS voice modes
_TAG_TO_TYPE = {
    "COLD_OPEN": "cold_open",
    "NARRATION": "setup",
    "DATA": "data",
    "SOCIAL": "social_segment",
    "WARM": "wrap",
    "BRIDGE": "setup",  # inter-clip context bridges treated as narration
}

_TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")


def _extract_segment_tags(result: dict) -> dict:
    """Extract [TAG] prefixes from dialogue text and set entry type accordingly.

    If a dialogue line starts with [NARRATION], [DATA], etc., strip the tag
    from the text and set/override the type field for TTS voice mode selection.
    """
    dialogue = result.get("dialogue", [])
    for entry in dialogue:
        text = entry.get("text", "")
        if not text:
            continue
        m = _TAG_PATTERN.match(text)
        if m:
            tag = m.group(1)
            entry["text"] = text[m.end():]
            entry["type"] = _TAG_TO_TYPE[tag]
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
    Returns empty dict if missing or stale (>6hr old)."""
    import os
    from datetime import datetime, timezone
    ctx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "intelligence", "narrative_context.json")
    try:
        with open(ctx_path) as f:
            ctx = json.load(f)
        # Check staleness
        computed = ctx.get("computed_at", "")
        if computed:
            computed_dt = datetime.fromisoformat(computed.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - computed_dt).total_seconds() / 3600
            if age_hours > 6:
                logger.warning(f"Narrative context is {age_hours:.1f}h old (>6h) — using generic prompt")
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
Eryn should reference: {eryn_intro_hook}
Mark should add: {mark_context}
Suggested bridge lines: {narrative_bridge_lines}

MANDATORY SCRIPT RULES (from narrative context):
- Eryn's cold open MUST reference the dominant narrative in her first sentence
- At least ONE of the clips must be explicitly connected to the X discourse
  (e.g., "This is what everyone on Crypto Twitter has been discussing all morning...")
- Mark must cite at least one specific data point from the narrative context (not generic)
- Avoid topics flagged in: {avoid_topics}
- The show must feel LIVE — like Eryn and Mark have been tracking this story all morning

DATA SEGMENT REQUIREMENT: The data/metrics discussed must relate to today's
dominant narrative ({dominant_narrative}). If narrative is "ETF inflows",
cite actual ETF flow numbers. If "mining difficulty", cite actual hashrate/difficulty data.
Eryn and Mark must sound like analysts who read the numbers this morning, not generalists.
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
                        live_context: str = "") -> dict:
    """Generate host dialogue script around the selected clips.

    Args:
        selections: Output from clip_selector.select_clips()
        btc_price: Current BTC price string
        live_context: Real-time live stream/Spaces intelligence (optional)

    Returns:
        Script dict with dialogue array
    """
    clips = selections.get("clips", [])
    if not clips:
        logger.error("No clips provided for script generation")
        return _fallback_script(selections)

    from relay import call_llm

    clips_info = _format_clips_info(selections)

    # Real social data — per Law A1, never fabricate
    # Render11 FIX 5: Sort by likes descending BEFORE passing to script generator
    # so highest engagement tweet = first displayed = first mentioned by narrator
    social_data_sorted = []
    try:
        from utils.social_fetcher import get_todays_social_posts
        social_data = get_todays_social_posts(max_posts=5)
        if social_data:
            social_data_sorted = sorted(social_data, key=lambda x: x.get('likes', 0), reverse=True)
            social_posts = "\n".join([
                f"Tweet {ti+1}: @{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
                for ti, p in enumerate(social_data_sorted)
            ])
            # FIX 5B: Explicit instruction to prevent hallucination
            social_posts += (
                "\n\nCRITICAL SOCIAL RULES:"
                "\n- Read ONLY what is written above. Do NOT paraphrase, add, or invent words."
                "\n- Quote tweet text DIRECTLY and verbatim."
                "\n- Reference tweets BY POSITION: 'Tweet 1 from @handle' matches the first tweet listed above."
                "\n- If you mention @handle, the DISPLAYED tweet card MUST match that handle."
                "\n- Never attribute words from one tweet to a different person."
            )
        else:
            social_posts = "NONE — skip social segment entirely"
    except Exception as e:
        logger.warning(f"Social data fetch failed: {e}")
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
            narrative_block = NARRATIVE_INJECTION.format(
                dominant_narrative=narrative_ctx.get("dominant_narrative", ""),
                market_mood=narrative_ctx.get("market_mood", ""),
                episode_narrative=narrative_ctx.get("episode_narrative", ""),
                eryn_intro_hook=narrative_ctx.get("eryn_intro_hook", ""),
                mark_context=narrative_ctx.get("mark_context", ""),
                narrative_bridge_lines="\n".join(bridge_lines) if bridge_lines else "none",
                avoid_topics=", ".join(narrative_ctx.get("avoid_topics", [])),
            )
            live_block = narrative_block + "\n" + live_block
            logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")
        except Exception as e:
            logger.warning(f"Failed to inject narrative context: {e}")

    prompt = SCRIPT_PROMPT.format(clips_info=clips_info, btc_price=btc_price,
                                   social_posts=social_posts, live_context=live_block)

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

        result = json.loads(text)

        # Extract [TAG] prefixes from text and set type fields for TTS
        result = _extract_segment_tags(result)

        # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
        result = _populate_segment_headlines(result)

        # Round 2 Fix 5: Validate social segment tweet order matches narration references
        result = _validate_social_tweet_order(result, social_posts)

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
        {"host": 2, "text": cold_open, "type": "cold_open"},  # IRON LAW: PBX always opens
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
            {"host": 2, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},  # IRON LAW: PBX always opens
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
