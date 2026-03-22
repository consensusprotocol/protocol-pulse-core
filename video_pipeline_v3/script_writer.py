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

=== SHOW BIBLE — IDENTITY ===
PBX is a Bitcoin operator and cypherpunk. He sees the world through an Austrian economics lens. He is NOT a financial analyst — he is a sovereign individual who runs nodes, understands mining, and lives on a Bitcoin standard.
EDITORIAL LAWS:
- Bitcoin ONLY. Never cover altcoins, crypto, DeFi, NFTs, or tokens.
- Never write "BTC" — always write "Bitcoin" in full.
- Never hedge. PBX states opinions directly. No "could", "might", "it remains to be seen."
- Respect the audience — they know what a UTXO is. Never explain basics.
- Every episode must contain ONE original PBX observation that nobody else said today.
- Cold open: single most important signal in ONE sentence. No warmup.
- PBX Close: an actual opinion, not a summary of what was covered.
NEVER COVER: mainstream media Bitcoin takes, institutional ETF obsession as the main story, fear-mongering narratives.
TIER 1 SOURCES (highest editorial weight): Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, Stephan Livera.
TIER 2 SOURCES: Simply Bitcoin, Bitcoin Magazine, Natalie Brunell, Swan Bitcoin.
NORTH STAR: This is a sovereign Bitcoin holders' morning show. Under 12 minutes. All signal, no noise.
=== END SHOW BIBLE ===

DUAL-HOST FORMAT — TWO voices alternate throughout the episode:

HOST 2 (PBX) — Bitcoin operator, cypherpunk, Austrian economics lens. Hot takes, contrarian, dry wit. Warm strong male voice.
HOST 1 (ERYN) — Co-host and intelligence analyst. Sharp, curious, data-driven. Warm female voice. She asks the question the audience is thinking.

VOICE SPLIT RULES:
- PBX (host:2) opens EVERY episode with the cold open. Always first.
- ERYN (host:1) handles SETUP lines — introduces clips, frames the context, 2-3 sentences.
- PBX (host:2) handles REACT lines — hot take after every clip, 2-3 sentences.
- DATA segment: ERYN reads the numbers, PBX gives the signal interpretation.
- SOCIAL segment: PBX reads and reacts to tweets. Eryn adds one sharp observation per tweet.
- WRAP/SIGN-OFF: PBX closes with "Stay sovereign." Eryn has the final data point before it.
- BRIDGE lines: alternate between hosts.
- Both hosts speak directly to the AUDIENCE, not to each other. No "Great point!" or co-host filler.

CRITICAL JSON RULE: Valid host values are ONLY: 1 (Eryn), 2 (PBX), or "CLIP". 
First entry MUST be host:2 (PBX cold open). Then alternate naturally per role above.

TONE RULES (NON-NEGOTIABLE):
- NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
- SETUP lines = 2-4 sentences, MAX 60 WORDS. A sharp framing angle + one specific data point. Leave them wanting the clip.
- REACT lines = 2-4 sentences. A hot take with substance — specific implication, not a vague platitude.
- Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
- Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
- Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
- Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
- After clips 2 and 4, add a BRIDGE line (type: "bridge") connecting that clip's theme to the next. 1-2 sentences. PBX only. Elevate the stakes or pivot the angle.
- REACT lines: when a clip lands something genuinely significant, give it 2-3 sharp sentences. Brief is not always best. Incisive > terse.
- NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
- CRITICAL: NEVER write "BTC" in any narration line. Always write "Bitcoin" in full. The ticker abbreviation sounds robotic when read aloud.
- When referencing a social media handle, write it in natural spoken form. NEVER write "@MaxKeiser". Write "Max Kaiser on X" or "Preston Pysh posted". Do not read handles aloud — reference the person by name.
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
- REACT lines = PBX's direct hot take on what was just shown. He speaks to the AUDIENCE, not to a co-host.
- NO conversational openers that imply a partner: NEVER use "Exactly.", "100%.", "I mean—", "Right, and—", "Yeah."
- React lines start with the IMPLICATION: "What this means is—", "The signal here is—", "Nobody's talking about—", "That's the tell.", "Here's what this means."
- Each new segment opens with a LIFT — a single high-energy sentence that raises the stakes. Think: news anchor tossing to the next story.
- Tone = investigative gossip journalist who happens to understand Austrian economics.
- Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
- Min 3, max 4 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.

EPISODE STRUCTURE (follow this order):
1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
5. [NARRATION] — Analysis after Clip 2.
6. [DATA] — Hard metrics segment. MINIMUM 3 exchanges (all PBX). Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. Target: 45-60 seconds of spoken content.
7. [SOCIAL] — "WHAT BITCOIN IS SAYING" — PBX reporting back from Bitcoin Twitter as live intelligence. Maximum 3 tweets, 20-25 seconds narration each (~75 seconds total). PBX treats each tweet as a signal:
  - PBX: 'Saylor just posted this to 65,000 likes — [quote]. Here's what that signals — conviction accumulation during extreme fear. That's the Saylor playbook and it's never been wrong.'
  - PBX: 'Lyn Alden weighed in on the macro picture — [paraphrase]. This aligns with what we're seeing in the bond market data. When she flips bullish on a timeline, institutions listen.'
  - PBX: 'This one caught my eye — [Name] is saying [quote]. The reason this matters is [2-3 sentences of sharp context].'
  PBX decodes the signal, he doesn't repeat the text. The tweet card is on screen — viewers read it themselves.
  CRITICAL: First tweet card shown = first referenced in narration. Maintain strict order.
8. [SPACE_TAP] — "SPACE TAP: SIGNAL INTERCEPT" (only if space_tap_clips provided below)
   PBX opens: "Right now in the Bitcoin ecosphere..." or similar intelligence briefing opener.
   For each clip (3-4 clips provided):
   - One sentence intro: who is speaking, what space, why it matters NOW. 10-15 words.
   - The clip plays (assembler handles this — do NOT write clip text).
   - One sentence reaction: PBX adds value, contrarian take, or context. 10-15 words.
   Target: 10-15 seconds of narration per clip (intro + reaction combined).
   Segment tone: intelligence briefing. You are intercepting a live signal.
   Never say "I found" or "we discovered" — say "we're intercepting" or "signal captured from".
   Format each entry as:
   {"host": 2, "text": "[SPACE_TAP] Right now in the ecosphere...", "type": "space_tap_intro"},
   {"host": "SPACE_CLIP", "clip_index": 0},
   {"host": 2, "text": "[SPACE_TAP] ...", "type": "space_tap_react"},
   {"host": "SPACE_CLIP", "clip_index": 1},
   ... and so on for all clips.
9. [WARM] — 2-3 sentences synthesizing the day's theme, then abrupt CTA. Target: 20-30 seconds. End ABRUPTLY. No "thanks for watching."

NARRATION PHILOSOPHY — Simon Dixon / Preston Pysh standard:
- Every line must contain ONE specific insight, data point, or evaluated observation
- Never state what already happened — analyze WHY it matters and WHAT COMES NEXT
- PBX sets up the angle with a sharp framing line + 1 specific number or fact
- PBX delivers the contrarian take, macro context, or on-chain implication
- Forbidden phrases: "Bitcoin continues to", "the market is watching", "this is significant",
  "interesting to note", "worth keeping an eye on", any pure restatement of price
- Required: each exchange references at least one of: hashrate, difficulty adjustment,
  miner profitability, HODLer behavior, lightning adoption, ETF flows, or macro correlation
- Minimum 3 sentences per speaker turn. Never 1-2 sentence fluff turns.
- Bridges between clips must connect thematic dots — not just "next up"
- DATA segment minimum: 4 lines from PBX, each with a specific metric, each with an implication

EPISODE LENGTH LAW: Target 550-680 narration words total. Never truncate a sentence. Every segment must be complete. Sharp means efficient — every sentence must earn its place. NO padding. NO repetition.

SEGMENT TAGGING (MANDATORY — controls PBX's voice dynamics):
Every dialogue text line MUST start with a segment type tag in brackets. The TTS engine reads this tag to adjust vocal delivery. If missing, the voice defaults to CLEAR which is safe but loses dramatic range.
  [COLD_OPEN] — opening hook only (first 1-2 sentences). Dramatic whisper. MAX 2 per episode.
  [NARRATION] — standard narration, setup, and analysis. Clear and confident. This is 70-80% of lines.
  [DATA] — specific metrics, prices, hashrates, on-chain numbers. Authoritative.
  [SOCIAL] — social segment commentary. Slightly warmer tone.
  [WARM] — outros, calls to action, sign-offs. Inviting.
Example: {"host": 2, "text": "[NARRATION] Bitcoin miners are facing a squeeze as difficulty adjusts upward.", "type": "setup"}
The tag is INSIDE the text string, not the type field. Both must be present.

SOCIAL SEGMENT — "WHAT BITCOIN IS SAYING":
If social posts data is provided below, add a "WHAT BITCOIN IS SAYING" segment after the last clip.
PBX has been on Bitcoin Twitter all morning and is REPORTING BACK as live intelligence.
This is NOT passive card display — PBX explicitly REACTS to each post as a signal analyst:

STYLE — PBX treats each tweet as intelligence, not content:
  - "{Name} just posted this to {likes} likes — [direct quote or tight paraphrase]. Here's what that signals..."
  - "{Name} weighed in on {topic} — [paraphrase]. This aligns with what we're seeing in the data..."
  - "This one caught my eye — {Name} is saying [quote]. The reason this matters is..."
PBX adds 2-3 sentences of sharp CONTEXT per tweet: why it matters NOW, what it signals about market positioning, how it connects to today's data. Maximum 3 posts, 20-25 seconds narration each, ~75 seconds total.
The tweet card is on screen — viewers can read the text. PBX's job is to DECODE the signal, not repeat the words.
Each entry uses type: "social_segment".

CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.
TWEET LAW — IRON LAW: Before writing ANY tweet narration, read the actual social_posts list in order. Tweet segment narration MUST reference social_posts[0]['handle'] for the first tweet, social_posts[1]['handle'] for the second, etc. NEVER reference a name not in the list. NEVER assume who tweeted. Read the handle from the data and use it verbatim.

{clips_info}

BTC Price Today: {btc_price}
Top Tweets/Nostr Posts Today: {social_posts}
{live_context}
Return ONLY valid JSON (no markdown, no code fences):
{
  "cold_open": "explosive 1-sentence cold open",
  "dialogue": [
    {"host": 2, "text": "...", "type": "cold_open"},
    {"host": 2, "text": "...", "type": "setup", "clip_rank": 1},
    {"host": "CLIP", "rank": 1},
    {"host": 2, "text": "...", "type": "react", "clip_rank": 1},
    {"host": 2, "text": "...", "type": "setup", "clip_rank": 2},
    {"host": "CLIP", "rank": 2},
    {"host": 2, "text": "...", "type": "react", "clip_rank": 2},
    ...and so on for all clips...
    {"host": 2, "text": "...", "type": "social_segment"},
    {"host": 2, "text": "...", "type": "social_segment"},
    {"host": 2, "text": "Final wrap. Stay sovereign.", "type": "wrap"}
  ],
  "episode_title": "Short punchy title (5-8 words)",
  "thumbnail": {
    "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
    "subtext": "secondary line"
  },
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
    "SPACE_TAP": "space_tap_intro",
    "SETUP": "setup",
    "REACT": "react",
    "CTA": "wrap",
    "COLD": "cold_open",
}

_TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")


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
                        live_context: str = "", morning_brief: dict = None) -> dict:
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
        bridge_lines = narrative_ctx.get("narrative_bridge_lines", [])
        narrative_block = NARRATIVE_INJECTION
        narrative_block = narrative_block.replace('{dominant_narrative}', str(narrative_ctx.get("dominant_narrative", "")))
        narrative_block = narrative_block.replace('{market_mood}', str(narrative_ctx.get("market_mood", "")))
        narrative_block = narrative_block.replace('{episode_narrative}', str(narrative_ctx.get("episode_narrative", "")))
        narrative_block = narrative_block.replace('{pbx_intro_hook}', str(narrative_ctx.get("eryn_intro_hook", narrative_ctx.get("pbx_intro_hook", ""))))
        narrative_block = narrative_block.replace('{pbx_context}', str(narrative_ctx.get("mark_context", narrative_ctx.get("pbx_context", ""))))
        narrative_block = narrative_block.replace('{narrative_bridge_lines}', "\n".join(bridge_lines) if bridge_lines else "none")
        narrative_block = narrative_block.replace('{avoid_topics}', ", ".join(narrative_ctx.get("avoid_topics", [])))
        live_block = narrative_block + "\n" + live_block
        logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")

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

    # Prompt assembly: .replace() is immune to {curly brace} KeyErrors in user content
    _live = live_block + morning_block + engagement_block + memory_block + space_tap_block
    prompt = SCRIPT_PROMPT
    prompt = prompt.replace('{clips_info}', str(clips_info))
    prompt = prompt.replace('{btc_price}', str(btc_price))
    prompt = prompt.replace('{social_posts}', str(social_posts))
    prompt = prompt.replace('{live_context}', str(_live))
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

        # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
        result = _populate_segment_headlines(result)

        # Round 2 Fix 5: Validate social segment tweet order matches narration references
        result = _validate_social_tweet_order(result, social_posts)
        result = _enforce_setup_per_clip(result, selections)

        # Validate structure
        dialogue = result.get("dialogue", [])
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

        dialogue.append({"host": 2, "text": setup, "type": "setup", "clip_rank": rank})
        dialogue.append({"host": "CLIP", "rank": rank})
        dialogue.append({"host": 2, "text": react, "type": "react", "clip_rank": rank})

    dialogue.append({
        "host": 2,
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
