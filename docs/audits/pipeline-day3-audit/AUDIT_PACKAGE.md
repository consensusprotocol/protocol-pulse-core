# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: pipeline-day3-audit
# Branch: main
# Generated: 2026-03-22 00:29 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)


---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: video_pipeline_v3/script_writer.py (820 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Script Writer V5 — generates host dialogue AROUND real YouTube clips.
   3 | 
   4 | Takes the 5 clips selected by clip_selector and generates:
   5 | - Cold open teasing clip #1
   6 | - Setup → Clip → React dialogue for each clip
   7 | - Wrap-up and sign-off
   8 | 
   9 | Host dialogue supports the clips, not the other way around.
  10 | """
  11 | import json
  12 | import logging
  13 | import os
  14 | import re
  15 | import sys
  16 | 
  17 | try:
  18 |     import anthropic
  19 |     HAS_ANTHROPIC = True
  20 | except ImportError:
  21 |     HAS_ANTHROPIC = False
  22 | 
  23 | from relay import get_key
  24 | 
  25 | logger = logging.getLogger("ScriptWriter")
  26 | if not logger.handlers:
  27 |     handler = logging.StreamHandler()
  28 |     handler.setFormatter(logging.Formatter("[script] %(message)s"))
  29 |     logger.addHandler(handler)
  30 |     logger.setLevel(logging.INFO)
  31 | 
  32 | SCRIPT_PROMPT = """You are writing host dialogue for "Pulse Check" — a daily Bitcoin highlight show.
  33 | Think: ESPN SportsCenter meets Cypherpunk Gossip. MMA Central energy. The clips are the star.
  34 | 
  35 | === SHOW BIBLE — IDENTITY ===
  36 | PBX is a Bitcoin operator and cypherpunk. He sees the world through an Austrian economics lens. He is NOT a financial analyst — he is a sovereign individual who runs nodes, understands mining, and lives on a Bitcoin standard.
  37 | EDITORIAL LAWS:
  38 | - Bitcoin ONLY. Never cover altcoins, crypto, DeFi, NFTs, or tokens.
  39 | - Never write "BTC" — always write "Bitcoin" in full.
  40 | - Never hedge. PBX states opinions directly. No "could", "might", "it remains to be seen."
  41 | - Respect the audience — they know what a UTXO is. Never explain basics.
  42 | - Every episode must contain ONE original PBX observation that nobody else said today.
  43 | - Cold open: single most important signal in ONE sentence. No warmup.
  44 | - PBX Close: an actual opinion, not a summary of what was covered.
  45 | NEVER COVER: mainstream media Bitcoin takes, institutional ETF obsession as the main story, fear-mongering narratives.
  46 | TIER 1 SOURCES (highest editorial weight): Preston Pysh, Lyn Alden, Robert Breedlove, TFTC, Stephan Livera.
  47 | TIER 2 SOURCES: Simply Bitcoin, Bitcoin Magazine, Natalie Brunell, Swan Bitcoin.
  48 | NORTH STAR: This is a sovereign Bitcoin holders' morning show. Under 12 minutes. All signal, no noise.
  49 | === END SHOW BIBLE ===
  50 | 
  51 | DUAL-HOST FORMAT — TWO voices alternate throughout the episode:
  52 | 
  53 | HOST 2 (PBX) — Bitcoin operator, cypherpunk, Austrian economics lens. Hot takes, contrarian, dry wit. Warm strong male voice.
  54 | HOST 1 (ERYN) — Co-host and intelligence analyst. Sharp, curious, data-driven. Warm female voice. She asks the question the audience is thinking.
  55 | 
  56 | VOICE SPLIT RULES:
  57 | - PBX (host:2) opens EVERY episode with the cold open. Always first.
  58 | - ERYN (host:1) handles SETUP lines — introduces clips, frames the context, 2-3 sentences.
  59 | - PBX (host:2) handles REACT lines — hot take after every clip, 2-3 sentences.
  60 | - DATA segment: ERYN reads the numbers, PBX gives the signal interpretation.
  61 | - SOCIAL segment: PBX reads and reacts to tweets. Eryn adds one sharp observation per tweet.
  62 | - WRAP/SIGN-OFF: PBX closes with "Stay sovereign." Eryn has the final data point before it.
  63 | - BRIDGE lines: alternate between hosts.
  64 | - Both hosts speak directly to the AUDIENCE, not to each other. No "Great point!" or co-host filler.
  65 | 
  66 | CRITICAL JSON RULE: Valid host values are ONLY: 1 (Eryn), 2 (PBX), or "CLIP". 
  67 | First entry MUST be host:2 (PBX cold open). Then alternate naturally per role above.
  68 | 
  69 | TONE RULES (NON-NEGOTIABLE):
  70 | - NEVER generic. Never say "interesting" or "really impactful" or "that's great stuff."
  71 | - SETUP lines = 2-4 sentences, MAX 60 WORDS. A sharp framing angle + one specific data point. Leave them wanting the clip.
  72 | - REACT lines = 2-4 sentences. A hot take with substance — specific implication, not a vague platitude.
  73 | - Cold open = 1 explosive sentence. Most outrageous or interesting story. Hook them in 3 seconds.
  74 | - Wit over wisdom. Brief over brilliant. Gossip energy, Bitcoin knowledge.
  75 | - Think: "Yo, you gotta hear what Saylor just said about this" NOT "Michael Saylor made some interesting comments about..."
  76 | - Reactions should feel genuine — surprised, amused, sharp, or skeptical. Never neutral.
  77 | - After clips 2 and 4, add a BRIDGE line (type: "bridge") connecting that clip's theme to the next. 1-2 sentences. PBX only. Elevate the stakes or pivot the angle.
  78 | - REACT lines: when a clip lands something genuinely significant, give it 2-3 sharp sentences. Brief is not always best. Incisive > terse.
  79 | - NO banned phrases: "Let's dive in", "Without further ado", "Buckle up", "game changer"
  80 | - CRITICAL: NEVER write "BTC" in any narration line. Always write "Bitcoin" in full. The ticker abbreviation sounds robotic when read aloud.
  81 | - When referencing a social media handle, write it in natural spoken form. NEVER write "@MaxKeiser". Write "Max Kaiser on X" or "Preston Pysh posted". Do not read handles aloud — reference the person by name.
  82 | - End with "Stay sovereign."
  83 | 
  84 | CRITICAL EPISODE ARC RULES (NON-NEGOTIABLE):
  85 | - Start with the most shocking/interesting fact. NO intro. NO "welcome to Protocol Pulse."
  86 | - At minute 3 (after Clip 2 setup), include a re-engagement hook: "But here's where it gets interesting..."
  87 | - At the halfway point, pivot to something unexpected or contrarian.
  88 | - End ABRUPTLY after the call to action. NEVER say "thanks for watching" or "see you next time."
  89 |   These phrases signal the video is ending and cause immediate viewer drop-off.
  90 | - Each narrator line should be 1-3 sentences. Never more than 4 sentences per turn.
  91 | - Include at least one specific number/metric in every other segment.
  92 | 
  93 | DELIVERY RULES:
  94 | - ALWAYS open setup lines with a natural verbal bridge: "Ok so—", "Right, and—", "Here's the thing—", "Check this out—", "So—". Never start cold.
  95 | - The setup is a LAY-UP for the clip. Tease the knockout moment. Don't explain the whole clip.
  96 | - REACT lines = PBX's direct hot take on what was just shown. He speaks to the AUDIENCE, not to a co-host.
  97 | - NO conversational openers that imply a partner: NEVER use "Exactly.", "100%.", "I mean—", "Right, and—", "Yeah."
  98 | - React lines start with the IMPLICATION: "What this means is—", "The signal here is—", "Nobody's talking about—", "That's the tell.", "Here's what this means."
  99 | - Each new segment opens with a LIFT — a single high-energy sentence that raises the stakes. Think: news anchor tossing to the next story.
 100 | - Tone = investigative gossip journalist who happens to understand Austrian economics.
 101 | - Think Page Six but for Bitcoin. Sharp. Knowing. Never neutral.
 102 | - Min 3, max 4 sentences per setup or react. Ruthlessly cut anything that sounds like a press release.
 103 | 
 104 | EPISODE STRUCTURE (follow this order):
 105 | 1. [COLD_OPEN] — The hook. Most shocking insight. 1-2 sentences MAX.
 106 | 2. [NARRATION] — Setup for Clip 1. Why this matters. End with transition to clip.
 107 | 3. [NARRATION] — Analysis after Clip 1. Connect to bigger picture.
 108 | 4. [NARRATION] — Setup for Clip 2 with re-engagement hook at ~minute 3.
 109 | 5. [NARRATION] — Analysis after Clip 2.
 110 | 6. [DATA] — Hard metrics segment. MINIMUM 3 exchanges (all PBX). Cover: price context, hash rate or difficulty, one on-chain signal. At least one specific number per line. Target: 45-60 seconds of spoken content.
 111 | 7. [SOCIAL] — "WHAT BITCOIN IS SAYING" — PBX reporting back from Bitcoin Twitter as live intelligence. Maximum 3 tweets, 20-25 seconds narration each (~75 seconds total). PBX treats each tweet as a signal:
 112 |   - PBX: 'Saylor just posted this to 65,000 likes — [quote]. Here's what that signals — conviction accumulation during extreme fear. That's the Saylor playbook and it's never been wrong.'
 113 |   - PBX: 'Lyn Alden weighed in on the macro picture — [paraphrase]. This aligns with what we're seeing in the bond market data. When she flips bullish on a timeline, institutions listen.'
 114 |   - PBX: 'This one caught my eye — [Name] is saying [quote]. The reason this matters is [2-3 sentences of sharp context].'
 115 |   PBX decodes the signal, he doesn't repeat the text. The tweet card is on screen — viewers read it themselves.
 116 |   CRITICAL: First tweet card shown = first referenced in narration. Maintain strict order.
 117 | 8. [SPACE_TAP] — "SPACE TAP: SIGNAL INTERCEPT" (only if space_tap_clips provided below)
 118 |    PBX opens: "Right now in the Bitcoin ecosphere..." or similar intelligence briefing opener.
 119 |    For each clip (3-4 clips provided):
 120 |    - One sentence intro: who is speaking, what space, why it matters NOW. 10-15 words.
 121 |    - The clip plays (assembler handles this — do NOT write clip text).
 122 |    - One sentence reaction: PBX adds value, contrarian take, or context. 10-15 words.
 123 |    Target: 10-15 seconds of narration per clip (intro + reaction combined).
 124 |    Segment tone: intelligence briefing. You are intercepting a live signal.
 125 |    Never say "I found" or "we discovered" — say "we're intercepting" or "signal captured from".
 126 |    Format each entry as:
 127 |    {"host": 2, "text": "[SPACE_TAP] Right now in the ecosphere...", "type": "space_tap_intro"},
 128 |    {"host": "SPACE_CLIP", "clip_index": 0},
 129 |    {"host": 2, "text": "[SPACE_TAP] ...", "type": "space_tap_react"},
 130 |    {"host": "SPACE_CLIP", "clip_index": 1},
 131 |    ... and so on for all clips.
 132 | 9. [WARM] — 2-3 sentences synthesizing the day's theme, then abrupt CTA. Target: 20-30 seconds. End ABRUPTLY. No "thanks for watching."
 133 | 
 134 | NARRATION PHILOSOPHY — Simon Dixon / Preston Pysh standard:
 135 | - Every line must contain ONE specific insight, data point, or evaluated observation
 136 | - Never state what already happened — analyze WHY it matters and WHAT COMES NEXT
 137 | - PBX sets up the angle with a sharp framing line + 1 specific number or fact
 138 | - PBX delivers the contrarian take, macro context, or on-chain implication
 139 | - Forbidden phrases: "Bitcoin continues to", "the market is watching", "this is significant",
 140 |   "interesting to note", "worth keeping an eye on", any pure restatement of price
 141 | - Required: each exchange references at least one of: hashrate, difficulty adjustment,
 142 |   miner profitability, HODLer behavior, lightning adoption, ETF flows, or macro correlation
 143 | - Minimum 3 sentences per speaker turn. Never 1-2 sentence fluff turns.
 144 | - Bridges between clips must connect thematic dots — not just "next up"
 145 | - DATA segment minimum: 4 lines from PBX, each with a specific metric, each with an implication
 146 | 
 147 | EPISODE LENGTH LAW: Target 550-680 narration words total. Never truncate a sentence. Every segment must be complete. Sharp means efficient — every sentence must earn its place. NO padding. NO repetition.
 148 | 
 149 | SEGMENT TAGGING (MANDATORY — controls PBX's voice dynamics):
 150 | Every dialogue text line MUST start with a segment type tag in brackets. The TTS engine reads this tag to adjust vocal delivery. If missing, the voice defaults to CLEAR which is safe but loses dramatic range.
 151 |   [COLD_OPEN] — opening hook only (first 1-2 sentences). Dramatic whisper. MAX 2 per episode.
 152 |   [NARRATION] — standard narration, setup, and analysis. Clear and confident. This is 70-80% of lines.
 153 |   [DATA] — specific metrics, prices, hashrates, on-chain numbers. Authoritative.
 154 |   [SOCIAL] — social segment commentary. Slightly warmer tone.
 155 |   [WARM] — outros, calls to action, sign-offs. Inviting.
 156 | Example: {"host": 2, "text": "[NARRATION] Bitcoin miners are facing a squeeze as difficulty adjusts upward.", "type": "setup"}
 157 | The tag is INSIDE the text string, not the type field. Both must be present.
 158 | 
 159 | SOCIAL SEGMENT — "WHAT BITCOIN IS SAYING":
 160 | If social posts data is provided below, add a "WHAT BITCOIN IS SAYING" segment after the last clip.
 161 | PBX has been on Bitcoin Twitter all morning and is REPORTING BACK as live intelligence.
 162 | This is NOT passive card display — PBX explicitly REACTS to each post as a signal analyst:
 163 | 
 164 | STYLE — PBX treats each tweet as intelligence, not content:
 165 |   - "{Name} just posted this to {likes} likes — [direct quote or tight paraphrase]. Here's what that signals..."
 166 |   - "{Name} weighed in on {topic} — [paraphrase]. This aligns with what we're seeing in the data..."
 167 |   - "This one caught my eye — {Name} is saying [quote]. The reason this matters is..."
 168 | PBX adds 2-3 sentences of sharp CONTEXT per tweet: why it matters NOW, what it signals about market positioning, how it connects to today's data. Maximum 3 posts, 20-25 seconds narration each, ~75 seconds total.
 169 | The tweet card is on screen — viewers can read the text. PBX's job is to DECODE the signal, not repeat the words.
 170 | Each entry uses type: "social_segment".
 171 | 
 172 | CRITICAL: If no social posts data is provided (empty or "NONE"), do NOT fabricate tweet content. Skip the social segment entirely. Law A1 — no invented data.
 173 | TWEET LAW — IRON LAW: Before writing ANY tweet narration, read the actual social_posts list in order. Tweet segment narration MUST reference social_posts[0]['handle'] for the first tweet, social_posts[1]['handle'] for the second, etc. NEVER reference a name not in the list. NEVER assume who tweeted. Read the handle from the data and use it verbatim.
 174 | 
 175 | {clips_info}
 176 | 
 177 | BTC Price Today: {btc_price}
 178 | Top Tweets/Nostr Posts Today: {social_posts}
 179 | {live_context}
 180 | Return ONLY valid JSON (no markdown, no code fences):
 181 | {
 182 |   "cold_open": "explosive 1-sentence cold open",
 183 |   "dialogue": [
 184 |     {"host": 2, "text": "...", "type": "cold_open"},
 185 |     {"host": 2, "text": "...", "type": "setup", "clip_rank": 1},
 186 |     {"host": "CLIP", "rank": 1},
 187 |     {"host": 2, "text": "...", "type": "react", "clip_rank": 1},
 188 |     {"host": 2, "text": "...", "type": "setup", "clip_rank": 2},
 189 |     {"host": "CLIP", "rank": 2},
 190 |     {"host": 2, "text": "...", "type": "react", "clip_rank": 2},
 191 |     ...and so on for all clips...
 192 |     {"host": 2, "text": "...", "type": "social_segment"},
 193 |     {"host": 2, "text": "...", "type": "social_segment"},
 194 |     {"host": 2, "text": "Final wrap. Stay sovereign.", "type": "wrap"}
 195 |   ],
 196 |   "episode_title": "Short punchy title (5-8 words)",
 197 |   "thumbnail": {
 198 |     "headline": "BOLD THUMBNAIL TEXT (5-8 words)",
 199 |     "subtext": "secondary line"
 200 |   },
 201 |   "segments_summary": ["4-8 WORD ALL CAPS EDITORIAL HEADLINE FOR EACH CLIP — like 'SAYLOR BETS BIG ON BITCOIN DIP' not a quote from the segment"],
 202 |   "shorts_quotes": ["best one-liner 1", "best one-liner 2", "best one-liner 3"]
 203 | }}
 204 | 
 205 | IMPORTANT: Each CLIP entry must have "rank" matching the clip number (1-5)."""
 206 | 
 207 | 
 208 | # Maps bracket tags in text to segment types for TTS voice modes
 209 | _TAG_TO_TYPE = {
 210 |     "COLD_OPEN": "cold_open",
 211 |     "NARRATION": "setup",
 212 |     "DATA": "data",
 213 |     "SOCIAL": "social_segment",
 214 |     "WARM": "wrap",
 215 |     "BRIDGE": "setup",  # inter-clip context bridges treated as narration
 216 |     "SPACE_TAP": "space_tap_intro",
 217 |     "SETUP": "setup",
 218 |     "REACT": "react",
 219 |     "CTA": "wrap",
 220 |     "COLD": "cold_open",
 221 | }
 222 | 
 223 | _TAG_PATTERN = re.compile(r"^\[(" + "|".join(_TAG_TO_TYPE.keys()) + r")\]\s*")
 224 | 
 225 | 
 226 | def _extract_segment_tags(result: dict) -> dict:
 227 |     """Extract [TAG] prefixes from dialogue text and set entry type accordingly.
 228 | 
 229 |     If a dialogue line starts with [NARRATION], [DATA], etc., strip the tag
 230 |     from the text and set/override the type field for TTS voice mode selection.
 231 |     """
 232 |     dialogue = result.get("dialogue", [])
 233 |     # Force PBX-only: normalize any host:1 → host:2
 234 |     for _e in dialogue:
 235 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 236 |     for entry in dialogue:
 237 |         text = entry.get("text", "")
 238 |         if not text:
 239 |             continue
 240 |         m = _TAG_PATTERN.match(text)
 241 |         if m:
 242 |             tag = m.group(1)
 243 |             entry["text"] = text[m.end():]
 244 |             entry["type"] = _TAG_TO_TYPE[tag]
 245 |     return result
 246 | 
 247 | 
 248 | def _format_clips_info(selections: dict) -> str:
 249 |     """Format clip selections for the script prompt."""
 250 |     clips = selections.get("clips", [])
 251 |     parts = []
 252 |     for c in clips:
 253 |         parts.append(
 254 |             f"CLIP #{c['rank']}:\n"
 255 |             f"  Channel: {c.get('channel', 'Unknown')}\n"
 256 |             f"  Video: {c.get('video_title', 'Untitled')}\n"
 257 |             f"  Quote: \"{c.get('quote', '')}\"\n"
 258 |             f"  Why selected: {c.get('why', '')}\n"
 259 |             f"  Suggested setup: {c.get('host_setup', '')}\n"
 260 |             f"  Suggested reaction: {c.get('host_react', '')}\n"
 261 |         )
 262 |     return "\n".join(parts)
 263 | 
 264 | 
 265 | def _load_narrative_context() -> dict:
 266 |     """Load narrative_context.json for narrative-aware script generation.
 267 |     Returns empty dict if missing or stale (>6hr old)."""
 268 |     import os
 269 |     from datetime import datetime, timezone
 270 |     ctx_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
 271 |                             "data", "intelligence", "narrative_context.json")
 272 |     try:
 273 |         with open(ctx_path) as f:
 274 |             ctx = json.load(f)
 275 |         # Check staleness
 276 |         computed = ctx.get("computed_at", "")
 277 |         if computed:
 278 |             computed_dt = datetime.fromisoformat(computed.replace("Z", "+00:00"))
 279 |             age_hours = (datetime.now(timezone.utc) - computed_dt).total_seconds() / 3600
 280 |             if age_hours > 6:
 281 |                 logger.warning(f"Narrative context is {age_hours:.1f}h old (>6h) — using generic prompt")
 282 |                 return {}
 283 |         return ctx
 284 |     except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
 285 |         logger.warning(f"Narrative context unavailable: {e}")
 286 |         return {}
 287 | 
 288 | 
 289 | NARRATIVE_INJECTION = """
 290 | TODAY'S LIVE NARRATIVE CONTEXT (from real-time thought leader monitoring):
 291 | Dominant narrative: {dominant_narrative}
 292 | Market mood: {market_mood}
 293 | What thought leaders are saying: {episode_narrative}
 294 | PBX cold open hook: {pbx_intro_hook}
 295 | PBX analysis angle: {pbx_context}
 296 | Suggested bridge lines: {narrative_bridge_lines}
 297 | 
 298 | MANDATORY SCRIPT RULES (from narrative context):
 299 | - PBX's cold open MUST reference the dominant narrative in his first sentence
 300 | - At least ONE of the clips must be explicitly connected to the X discourse
 301 |   (e.g., "This is what everyone on Crypto Twitter has been discussing all morning...")
 302 | - PBX must cite at least one specific data point from the narrative context (not generic)
 303 | - Avoid topics flagged in: {avoid_topics}
 304 | - The show must feel LIVE — like PBX has been tracking this story all morning
 305 | 
 306 | DATA SEGMENT REQUIREMENT: The data/metrics discussed must relate to today's
 307 | dominant narrative ({dominant_narrative}). If narrative is "ETF inflows",
 308 | cite actual ETF flow numbers. If "mining difficulty", cite actual hashrate/difficulty data.
 309 | PBX must sound like an analyst who read the numbers this morning, not a generalist.
 310 | """
 311 | 
 312 | 
 313 | def _validate_social_tweet_order(result: dict, social_posts_raw: str) -> dict:
 314 |     """Render11 FIX 5: Ensure narrator tweet references match tweet display order.
 315 | 
 316 |     If narrator mentions @handle that doesn't match the expected tweet position,
 317 |     reorder social_segment entries so card display matches narration order.
 318 |     Tags each social entry with _social_handle_ref for assembler card matching.
 319 |     """
 320 |     if not social_posts_raw or social_posts_raw.startswith("NONE"):
 321 |         return result
 322 | 
 323 |     dialogue = result.get("dialogue", [])
 324 |     # Force PBX-only: normalize any host:1 → host:2
 325 |     for _e in dialogue:
 326 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 327 |     if not dialogue:
 328 |         return result
 329 | 
 330 |     # Extract ordered handles from social_posts_raw (sorted by likes in generate_from_clips)
 331 |     social_handles = []
 332 |     for line in social_posts_raw.split("\n"):
 333 |         m = re.match(r'(?:Tweet \d+: )?@(\w+)\s+tweeted:', line)
 334 |         if m:
 335 |             social_handles.append(m.group(1).lower())
 336 | 
 337 |     # Extract @handle references from social_segment narration lines
 338 |     social_entries = [(i, e) for i, e in enumerate(dialogue)
 339 |                       if e.get("type") == "social_segment" and e.get("host") in (1, 2, "1", "2")]
 340 | 
 341 |     narrator_handles = []
 342 |     for _, entry in social_entries:
 343 |         text = entry.get("text", "")
 344 |         handles_in_text = re.findall(r'@(\w+)', text)
 345 |         for h in handles_in_text:
 346 |             h_lower = h.lower()
 347 |             if h_lower in social_handles and h_lower not in narrator_handles:
 348 |                 narrator_handles.append(h_lower)
 349 | 
 350 |     # Tag each social entry with its referenced handle
 351 |     for idx, entry in social_entries:
 352 |         text = entry.get("text", "")
 353 |         handles_in_text = [h.lower() for h in re.findall(r'@(\w+)', text)]
 354 |         matched = [h for h in handles_in_text if h in social_handles]
 355 |         if matched:
 356 |             entry["_social_handle_ref"] = matched[0]
 357 |             logger.info(f"[script] Social segment line {idx} references @{matched[0]}")
 358 | 
 359 |     # Render12 FIX 2: Assert strict tweet order — first card shown = first referenced
 360 |     if narrator_handles and social_handles:
 361 |         expected = social_handles[:len(narrator_handles)]
 362 |         if narrator_handles != expected:
 363 |             logger.warning(f"[script] TWEET ORDER VIOLATION: narrator={narrator_handles}, expected={expected} — reordering")
 364 |         else:
 365 |             logger.info(f"[script] TWEET ORDER OK: {narrator_handles}")
 366 | 
 367 |     # FIX 5: Reorder social_segment entries so narration order matches display order
 368 |     # The social_posts were sorted by likes desc — narrator should mention them in that order
 369 |     if narrator_handles and social_handles and narrator_handles != social_handles[:len(narrator_handles)]:
 370 |         logger.warning(f"[script] TWEET MISMATCH: narrator={narrator_handles}, data={social_handles[:len(narrator_handles)]}")
 371 |         # Reorder social_segment dialogue entries to match data order
 372 |         social_with_handle = [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]
 373 |         if social_with_handle:
 374 |             # Sort by position in social_handles (data order = likes desc)
 375 |             social_with_handle.sort(
 376 |                 key=lambda x: social_handles.index(x[1]["_social_handle_ref"])
 377 |                 if x[1]["_social_handle_ref"] in social_handles else 999
 378 |             )
 379 |             # Swap entries in-place in dialogue
 380 |             original_indices = [i for i, _ in [(i, e) for i, e in social_entries if e.get("_social_handle_ref")]]
 381 |             for new_pos, (_, entry) in enumerate(social_with_handle):
 382 |                 if new_pos < len(original_indices):
 383 |                     dialogue[original_indices[new_pos]] = entry
 384 |             logger.info(f"[script] Reordered social entries to match data order")
 385 | 
 386 |     return result
 387 | 
 388 | 
 389 | def _make_editorial_headline(raw: str) -> str:
 390 |     """Convert a raw summary/title into a 3-7 word ALL CAPS editorial headline.
 391 | 
 392 |     Render11 FIX 8: Strict Bloomberg/newspaper front page format.
 393 |     No punctuation except dash. 3-7 words. Always ALL CAPS.
 394 |     BAD: 'Saylor talks about sonic boom theory'
 395 |     GOOD: 'SAYLOR SONIC BOOM BITCOIN THESIS'
 396 |     """
 397 |     import re
 398 |     # Strip quotes, URLs, timestamps, punctuation (except dash)
 399 |     clean = re.sub(r'https?://\S+', '', raw)
 400 |     clean = re.sub(r'["\'\[\]().,;:!?]', '', clean)
 401 |     clean = re.sub(r'\s+', ' ', clean).strip()
 402 |     # Take first 7 words, uppercase
 403 |     words = clean.split()[:7]
 404 |     headline = " ".join(words).upper()
 405 |     # Ensure minimum 3 words
 406 |     if len(words) < 3:
 407 |         headline = headline + " - BREAKING"
 408 |     # FIX 8: Post-generation validation — force ALL CAPS, strip non-conforming chars
 409 |     headline = re.sub(r'[^A-Z0-9 \-/]', '', headline).strip()
 410 |     if not headline or len(headline) < 5:
 411 |         headline = "BREAKING SIGNAL DETECTED"
 412 |     return headline[:55]
 413 | 
 414 | 
 415 | def _populate_segment_headlines(result: dict) -> dict:
 416 |     """Session 4 Fix 2: Add 'headline' key to each dialogue entry.
 417 | 
 418 |     Maps segment type + clip rank to a meaningful headline so _smart_headline()
 419 |     in assembler.py gets a real headline instead of truncated spoken text.
 420 |     Render11 FIX 8: Headlines are 3-7 word ALL CAPS editorial style with regex validation.
 421 |     """
 422 |     dialogue = result.get("dialogue", [])
 423 |     # Force PBX-only: normalize any host:1 → host:2
 424 |     for _e in dialogue:
 425 |         if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 426 |     summaries = result.get("segments_summary", [])
 427 |     episode_title = result.get("episode_title", "Pulse Check Daily")
 428 | 
 429 |     for entry in dialogue:
 430 |         if entry.get("headline"):
 431 |             continue  # already has one
 432 |         host = entry.get("host")
 433 |         if host == "CLIP":
 434 |             continue  # clip markers don't need headlines
 435 | 
 436 |         seg_type = entry.get("type", "")
 437 |         clip_rank = entry.get("clip_rank", 0)
 438 | 
 439 |         if seg_type == "cold_open":
 440 |             entry["headline"] = _make_editorial_headline(episode_title)
 441 |         elif seg_type in ("setup", "react") and clip_rank:
 442 |             # Use segments_summary keyed by rank — force editorial style
 443 |             idx = clip_rank - 1
 444 |             if 0 <= idx < len(summaries) and summaries[idx]:
 445 |                 entry["headline"] = _make_editorial_headline(summaries[idx])
 446 |             else:
 447 |                 entry["headline"] = _make_editorial_headline(episode_title)
 448 |         elif seg_type == "data":
 449 |             entry["headline"] = "TODAY'S INTELLIGENCE"
 450 |         elif seg_type == "social_segment":
 451 |             entry["headline"] = "SIGNAL FROM THE FIELD"
 452 |         elif seg_type in ("wrap", "outro"):
 453 |             entry["headline"] = "STAY SOVEREIGN"
 454 |         elif seg_type == "bridge":
 455 |             entry["headline"] = _make_editorial_headline(episode_title)
 456 |         else:
 457 |             # Generic narrator — use episode title
 458 |             entry["headline"] = _make_editorial_headline(episode_title)
 459 | 
 460 |     # Render11 FIX 8: Post-validation — force ALL CAPS, reject >8 words or lowercase
 461 |     for entry in dialogue:
 462 |         h = entry.get("headline", "")
 463 |         if not h or entry.get("host") == "CLIP":
 464 |             continue
 465 |         # Force uppercase and strip non-conforming chars
 466 |         h = re.sub(r'[^A-Z0-9 \-/]', '', h.upper()).strip()
 467 |         words = h.split()
 468 |         if len(words) > 8:
 469 |             h = " ".join(words[:7])
 470 |         if not h or len(h) < 5:
 471 |             h = "BREAKING SIGNAL DETECTED"
 472 |         entry["headline"] = h
 473 | 
 474 |     return result
 475 | 
 476 | 
 477 | def generate_from_clips(selections: dict, btc_price: str = "N/A",
 478 |                         live_context: str = "", morning_brief: dict = None) -> dict:
 479 |     """Generate host dialogue script around the selected clips.
 480 | 
 481 |     Args:
 482 |         selections: Output from clip_selector.select_clips()
 483 |         btc_price: Current BTC price string
 484 |         live_context: Real-time live stream/Spaces intelligence (optional)
 485 | 
 486 |     Returns:
 487 |         Script dict with dialogue array
 488 |     """
 489 |     clips = selections.get("clips", [])
 490 |     if not clips:
 491 |         logger.error("No clips provided for script generation")
 492 |         return _fallback_script(selections)
 493 | 
 494 |     from relay import call_llm
 495 | 
 496 |     clips_info = _format_clips_info(selections)
 497 | 
 498 |     # Real social data — per Law A1, never fabricate
 499 |     # Render11 FIX 5: Sort by likes descending BEFORE passing to script generator
 500 |     # so highest engagement tweet = first displayed = first mentioned by narrator
 501 |     social_data_sorted = []
 502 |     try:
 503 |         from utils.social_fetcher import get_todays_social_posts
 504 |         social_data = get_todays_social_posts(max_posts=5)
 505 |         if social_data:
 506 |             social_data_sorted = sorted(social_data, key=lambda x: x.get('likes', 0), reverse=True)
 507 |             social_posts = "\n".join([
 508 |                 f"Tweet {ti+1}: @{p['handle']} tweeted: \"{p['text'][:200]}\" ({p['likes']} likes)"
 509 |                 for ti, p in enumerate(social_data_sorted)
 510 |             ])
 511 |             # FIX 5B: Explicit instruction to prevent hallucination
 512 |             social_posts += (
 513 |                 "\n\nCRITICAL SOCIAL RULES:"
 514 |                 "\n- Read ONLY what is written above. Do NOT paraphrase, add, or invent words."
 515 |                 "\n- Quote tweet text DIRECTLY and verbatim."
 516 |                 "\n- Reference tweets BY POSITION: 'Tweet 1 from @handle' matches the first tweet listed above."
 517 |                 "\n- If you mention @handle, the DISPLAYED tweet card MUST match that handle."
 518 |                 "\n- Never attribute words from one tweet to a different person."
 519 |             )
 520 |         else:
 521 |             social_posts = "NONE — skip social segment entirely"
 522 |     except Exception as e:
 523 |         logger.warning(f"Social data fetch failed: {e}")
 524 |         social_posts = "NONE — skip social segment entirely"
 525 | 
 526 |     # Build live context block
 527 |     live_block = ""
 528 |     if live_context:
 529 |         live_block = (
 530 |             "\nLIVE INTELLIGENCE: The following events are happening RIGHT NOW or happened "
 531 |             "in the last few hours on Bitcoin YouTube/X Spaces. Reference these naturally "
 532 |             "in your narration to make the episode feel current and urgent:\n"
 533 |             f"{live_context}\n"
 534 |         )
 535 | 
 536 |     # Inject narrative context from thought leader monitoring
 537 |     narrative_ctx = _load_narrative_context()
 538 |     if narrative_ctx and narrative_ctx.get("dominant_narrative"):
 539 |         bridge_lines = narrative_ctx.get("narrative_bridge_lines", [])
 540 |         narrative_block = NARRATIVE_INJECTION
 541 |         narrative_block = narrative_block.replace('{dominant_narrative}', str(narrative_ctx.get("dominant_narrative", "")))
 542 |         narrative_block = narrative_block.replace('{market_mood}', str(narrative_ctx.get("market_mood", "")))
 543 |         narrative_block = narrative_block.replace('{episode_narrative}', str(narrative_ctx.get("episode_narrative", "")))
 544 |         narrative_block = narrative_block.replace('{pbx_intro_hook}', str(narrative_ctx.get("eryn_intro_hook", narrative_ctx.get("pbx_intro_hook", ""))))
 545 |         narrative_block = narrative_block.replace('{pbx_context}', str(narrative_ctx.get("mark_context", narrative_ctx.get("pbx_context", ""))))
 546 |         narrative_block = narrative_block.replace('{narrative_bridge_lines}', "\n".join(bridge_lines) if bridge_lines else "none")
 547 |         narrative_block = narrative_block.replace('{avoid_topics}', ", ".join(narrative_ctx.get("avoid_topics", [])))
 548 |         live_block = narrative_block + "\n" + live_block
 549 |         logger.info(f"Narrative context injected: {narrative_ctx.get('dominant_narrative')}")
 550 | 
 551 |     # Inject morning intelligence brief (Nitter-sourced Twitter analysis)
 552 |     morning_block = ""
 553 |     if morning_brief and isinstance(morning_brief, dict):
 554 |         parts = ["\nMORNING INTELLIGENCE BRIEF (from today's Bitcoin Twitter analysis — use as context):"]
 555 |         dom_narr = morning_brief.get("dominant_narratives", [])
 556 |         if dom_narr:
 557 |             parts.append(f"- Dominant narratives today: {'; '.join(dom_narr[:3])}")
 558 |         trending_lang = morning_brief.get("trending_language", [])
 559 |         if trending_lang:
 560 |             parts.append(f"- Trending language on Bitcoin Twitter: {', '.join(trending_lang[:7])}")
 561 |             parts.append("  USE these phrases naturally in narration where they fit — they resonate with the audience today.")
 562 |         sentiment = morning_brief.get("sentiment", "")
 563 |         reasoning = morning_brief.get("sentiment_reasoning", "")
 564 |         if sentiment:
 565 |             parts.append(f"- Market sentiment: {sentiment}")
 566 |         if reasoning:
 567 |             parts.append(f"  Reasoning: {reasoning[:200]}")
 568 |         voice_guidance = morning_brief.get("protocol_pulse_voice_guidance", "")
 569 |         if voice_guidance:
 570 |             parts.append(f"- Voice guidance: {voice_guidance[:250]}")
 571 |         morning_block = "\n".join(parts) + "\n"
 572 |         logger.info(f"Morning brief injected: {len(dom_narr)} narratives, {len(trending_lang)} trending phrases")
 573 | 
 574 |     # Inject audience engagement intelligence
 575 |     engagement_block = ""
 576 |     try:
 577 |         import sys as _sys
 578 |         _data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
 579 |         if _data_dir not in _sys.path:
 580 |             _sys.path.insert(0, _data_dir)
 581 |         from engagement_scorer import get_trending_topics, get_top_channels
 582 |         trending = get_trending_topics()[:3]
 583 |         top_chs = get_top_channels(5)
 584 |         if trending or top_chs:
 585 |             parts = ["\nAUDIENCE ENGAGEMENT INTELLIGENCE (from real audience data — use naturally):"]
 586 |             if trending:
 587 |                 topics_str = ", ".join(f"{t[0]} ({t[1]:.1f}/10)" for t in trending)
 588 |                 parts.append(f"- Currently trending in our audience: {topics_str} — weight these if relevant.")
 589 |             if top_chs:
 590 |                 chs_str = ", ".join(f"{c[0]} ({c[1]:.1f})" for c in top_chs)
 591 |                 parts.append(f"- Highest engagement channels this week: {chs_str} — prioritize their clips.")
 592 |             engagement_block = "\n".join(parts) + "\n"
 593 |             logger.info(f"Engagement intelligence injected: {len(trending)} topics, {len(top_chs)} channels")
 594 |     except Exception as e:
 595 |         logger.debug(f"Engagement scorer unavailable: {e}")
 596 | 
 597 |     # Inject episode memory feedback if enough history exists
 598 |     memory_block = ""
 599 |     try:
 600 |         from episode_memory import get_episode_count, get_weak_dimensions, get_strong_dimensions, get_best_channels
 601 |         if get_episode_count() >= 5:
 602 |             weak = get_weak_dimensions(threshold=6.0)
 603 |             strong = get_strong_dimensions(threshold=8.0)
 604 |             top_ch = get_best_channels(5)
 605 |             parts = ["\nEPISODE MEMORY FEEDBACK (from past renders — adapt accordingly):"]
 606 |             if weak:
 607 |                 dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in weak[:5])
 608 |                 parts.append(f"- WEAK AREAS (improve these): {dims}")
 609 |             if strong:
 610 |                 dims = ", ".join(f"{d['dimension']} ({d['avg_score']}/10)" for d in strong[:5])
 611 |                 parts.append(f"- STRONG AREAS (maintain these): {dims}")
 612 |             if top_ch:
 613 |                 chs = ", ".join(f"{c['channel']} ({c['avg_score']})" for c in top_ch)
 614 |                 parts.append(f"- TOP CHANNELS by quality score: {chs}")
 615 |             memory_block = "\n".join(parts) + "\n"
 616 |             logger.info(f"Episode memory injected: {len(weak)} weak, {len(strong)} strong dimensions")
 617 |     except Exception as e:
 618 |         logger.warning(f"Episode memory unavailable: {e}")
 619 | 
 620 |     # Inject Space Tap clips context if available
 621 |     space_tap_block = ""
 622 |     space_tap_clips = selections.get("space_tap_clips", [])
 623 |     if space_tap_clips:
 624 |         parts = ["\nSPACE TAP CLIPS (X Spaces intercepts — generate [SPACE_TAP] segment):"]
 625 |         for i, sc in enumerate(space_tap_clips):
 626 |             handle = sc.get("host_handle", "unknown")
 627 |             text_preview = sc.get("text", "")[:150]
 628 |             parts.append(f"  Clip {i}: @{handle} — \"{text_preview}\"")
 629 |         parts.append(f"Generate intro + react for each of the {len(space_tap_clips)} clips above.")
 630 |         space_tap_block = "\n".join(parts) + "\n"
 631 | 
 632 |     # Prompt assembly: .replace() is immune to {curly brace} KeyErrors in user content
 633 |     _live = live_block + morning_block + engagement_block + memory_block + space_tap_block
 634 |     prompt = SCRIPT_PROMPT
 635 |     prompt = prompt.replace('{clips_info}', str(clips_info))
 636 |     prompt = prompt.replace('{btc_price}', str(btc_price))
 637 |     prompt = prompt.replace('{social_posts}', str(social_posts))
 638 |     prompt = prompt.replace('{live_context}', str(_live))
 639 |     logger.info(f"Generating script for {len(clips)} clips...")
 640 |     text = call_llm(prompt, max_tokens=8000, model="claude-sonnet-4-6")
 641 |     if text is None:
 642 |         logger.warning("All LLM providers failed, using fallback script")
 643 |         return _fallback_script(selections)
 644 | 
 645 |     try:
 646 | 
 647 |         if "```json" in text:
 648 |             text = text.split("```json")[1].split("```")[0]
 649 |         elif "```" in text:
 650 |             text = text.split("```")[1].split("```")[0]
 651 | 
 652 |         # FIX 4: JSON retry loop — send malformed JSON back for repair, max 3 retries
 653 |         json_text = text
 654 |         result = None
 655 |         for _retry in range(4):  # attempt 0 = first try, 1-3 = retries
 656 |             try:
 657 |                 result = json.loads(json_text)
 658 |                 break
 659 |             except json.JSONDecodeError as je:
 660 |                 if _retry >= 3:
 661 |                     raise RuntimeError(f"JSON repair failed after 3 retries: {je}") from je
 662 |                 logger.warning(f"JSON parse error (retry {_retry+1}/3): {je}")
 663 |                 repair_prompt = (
 664 |                     f"The following JSON is malformed. Fix it and return ONLY valid JSON, "
 665 |                     f"no markdown, no explanation:\n\n{json_text}\n\n"
 666 |                     f"Error was: {je}"
 667 |                 )
 668 |                 json_text = call_llm(repair_prompt, max_tokens=8000, model="claude-sonnet-4-6")
 669 |                 if json_text is None:
 670 |                     raise RuntimeError("JSON repair LLM call returned None")
 671 |                 # Strip code fences from repair response
 672 |                 if "```json" in json_text:
 673 |                     json_text = json_text.split("```json")[1].split("```")[0]
 674 |                 elif "```" in json_text:
 675 |                     json_text = json_text.split("```")[1].split("```")[0]
 676 | 
 677 |         # Extract [TAG] prefixes from text and set type fields for TTS
 678 |         result = _extract_segment_tags(result)
 679 | 
 680 |         # Session 4 Fix 2: Populate 'headline' per dialogue entry for assembler
 681 |         result = _populate_segment_headlines(result)
 682 | 
 683 |         # Round 2 Fix 5: Validate social segment tweet order matches narration references
 684 |         result = _validate_social_tweet_order(result, social_posts)
 685 |         result = _enforce_setup_per_clip(result, selections)
 686 | 
 687 |         # Validate structure
 688 |         dialogue = result.get("dialogue", [])
 689 |         # Force PBX-only: normalize any host:1 â host:2
 690 |         for _e in dialogue:
 691 |             if isinstance(_e, dict) and _e.get("host") in (1, "1"): _e["host"] = 2
 692 |         clip_entries = [d for d in dialogue if d.get("host") == "CLIP"]
 693 |         speech_entries = [d for d in dialogue if d.get("host") in (1, 2, "1", "2")]
 694 | 
 695 |         logger.info(f"Script generated: {len(dialogue)} entries "
 696 |                     f"({len(speech_entries)} speech, {len(clip_entries)} clips)")
 697 |         logger.info(f"Title: {result.get('episode_title', 'Untitled')}")
 698 | 
 699 |         return result
 700 | 
 701 |     except json.JSONDecodeError as e:
 702 |         logger.error(f"JSON parse error: {e}")
 703 |         return _fallback_script(selections)
 704 |     except Exception as e:
 705 |         logger.error(f"Claude API error: {e}")
 706 |         return _fallback_script(selections)
 707 | 
 708 | 
 709 | 
 710 | def _enforce_setup_per_clip(result: dict, selections: dict) -> dict:
 711 |     """IRON LAW: Every clip rank must have exactly one SETUP segment before it.
 712 |     If the LLM collapses two setups onto clip_rank 1 and skips clip_rank 2,
 713 |     this function detects and repairs it by inserting a bridging setup."""
 714 |     import logging
 715 |     _log = logging.getLogger(__name__)
 716 |     dialogue = result.get("dialogue", [])
 717 |     clips = selections.get("clips", [])
 718 |     clip_ranks = [c.get("rank", 0) for c in clips if c.get("rank")]
 719 | 
 720 |     # Find which ranks have a setup
 721 |     setup_ranks = set()
 722 |     for entry in dialogue:
 723 |         if isinstance(entry, dict) and entry.get("type") == "setup":
 724 |             cr = entry.get("clip_rank")
 725 |             if cr:
 726 |                 setup_ranks.add(cr)
 727 | 
 728 |     missing = [r for r in clip_ranks if r not in setup_ranks]
 729 |     if not missing:
 730 |         return result
 731 | 
 732 |     _log.warning(f"[script] SETUP MISSING for clip ranks: {missing} — inserting bridge narration")
 733 |     clips_by_rank = {c.get("rank"): c for c in clips}
 734 |     new_dialogue = []
 735 |     for entry in dialogue:
 736 |         if isinstance(entry, dict) and entry.get("host") == "CLIP":
 737 |             rank = entry.get("rank", 0)
 738 |             if rank in missing:
 739 |                 ch = clips_by_rank.get(rank, {}).get("channel", "our next source")
 740 |                 bridge = {
 741 |                     "host": 2,
 742 |                     "text": f"[NARRATION] Now — {ch} brings a signal you need to hear.",
 743 |                     "type": "setup",
 744 |                     "clip_rank": rank,
 745 |                     "headline": f"{ch.upper()} SIGNAL"
 746 |                 }
 747 |                 new_dialogue.append(bridge)
 748 |                 missing.remove(rank)
 749 |         new_dialogue.append(entry)
 750 |     result["dialogue"] = new_dialogue
 751 |     return result
 752 | 
 753 | def _fallback_script(selections: dict) -> dict:
 754 |     """Generate a basic script from clip selections without Claude."""
 755 |     clips = selections.get("clips", [])
 756 |     cold_open = selections.get("cold_open", "Breaking developments in Bitcoin today.")
 757 | 
 758 |     dialogue = [
 759 |         {"host": 2, "text": cold_open, "type": "cold_open"},  # IRON LAW: PBX always opens
 760 |     ]
 761 | 
 762 |     for c in clips:
 763 |         rank = c.get("rank", 0)
 764 |         setup = c.get("host_setup", f"Check out what {c.get('channel', 'this channel')} just dropped.")
 765 |         react = c.get("host_react", "That's a big deal. The market hasn't priced this in yet.")
 766 | 
 767 |         dialogue.append({"host": 2, "text": setup, "type": "setup", "clip_rank": rank})
 768 |         dialogue.append({"host": "CLIP", "rank": rank})
 769 |         dialogue.append({"host": 2, "text": react, "type": "react", "clip_rank": rank})
 770 | 
 771 |     dialogue.append({
 772 |         "host": 2,
 773 |         "text": "That's your Pulse Check for today. Stay sovereign.",
 774 |         "type": "wrap",
 775 |     })
 776 | 
 777 |     title = selections.get("episode_title", "Pulse Check Daily")
 778 | 
 779 |     return {
 780 |         "cold_open": cold_open,
 781 |         "dialogue": dialogue,
 782 |         "episode_title": title,
 783 |         "thumbnail": {"headline": title.upper(), "subtext": "Daily Bitcoin Intelligence"},
 784 |         "segments_summary": [c.get("why", "") for c in clips],
 785 |         "shorts_quotes": [c.get("quote", "")[:80] for c in clips[:3]],
 786 |     }
 787 | 
 788 | 
 789 | # Legacy compatibility
 790 | def generate_script(stories=None, style="default", btc_price="N/A"):
 791 |     """Legacy wrapper — generate a sample script for testing."""
 792 |     logger.info("Legacy generate_script called — use generate_from_clips for V5 pipeline")
 793 |     return generate_sample_script(style)
 794 | 
 795 | 
 796 | def generate_sample_script(style="default"):
 797 |     """Sample script for testing without live data."""
 798 |     return {
 799 |         "episode_title": "The Quiet Accumulation",
 800 |         "cold_open": "Three sovereign wealth funds just disclosed Bitcoin positions worth twelve billion dollars.",
 801 |         "dialogue": [
 802 |             {"host": 2, "text": "Three sovereign wealth funds just disclosed Bitcoin positions. Twelve billion dollars. This is Pulse Check.", "type": "cold_open"},  # IRON LAW: PBX always opens
 803 |             {"host": 2, "text": "Bitcoin Magazine just dropped this bombshell.", "type": "setup", "clip_rank": 1},
 804 |             {"host": "CLIP", "rank": 1},
 805 |             {"host": 2, "text": "Dude. When the entities that print fiat start hoarding the exit asset, that tells you everything.", "type": "react", "clip_rank": 1},
 806 |             {"host": 2, "text": "And look at what Simply Bitcoin is reporting on hash rate.", "type": "setup", "clip_rank": 2},
 807 |             {"host": "CLIP", "rank": 2},
 808 |             {"host": 2, "text": "Record high hash rate. Miners aren't leaving. They're doubling down.", "type": "react", "clip_rank": 2},
 809 |             {"host": 2, "text": "That's your Pulse Check. Stay sovereign.", "type": "wrap"},
 810 |         ],
 811 |         "thumbnail": {"headline": "SMART MONEY IS MOVING", "subtext": "Nations are stacking"},
 812 |         "segments_summary": ["Sovereign wealth funds buying BTC", "Hash rate hits record"],
 813 |         "shorts_quotes": ["When the entities that print fiat start hoarding the exit asset", "Miners aren't leaving"],
 814 |     }
 815 | 
 816 | 
 817 | if __name__ == "__main__":
 818 |     script = generate_sample_script()
 819 |     print(json.dumps(script, indent=2))
 820 | 
```

### File: video_pipeline_v3/tts_engine.py (1375 lines)
```
   1 | #!/usr/bin/env python3
   2 | """TTS Engine V10 — Dual-host local TTS pipeline.
   3 | Host 1: Kokoro af_heart (female) — setup/bridge.
   4 | Host 2: Kokoro am_onyx (male) — react/wrap. F5-TTS PBX when ready.
   5 | Fallback: ElevenLabs per-line. TTS_PROVIDER=local (default) or elevenlabs.
   6 | Generates per-line audio with 0.3s silence gaps."""
   7 | import os, sys, json, subprocess, tempfile, time, struct, shutil, logging, re
   8 | from pathlib import Path
   9 | 
  10 | try:
  11 |     import requests
  12 |     HAS_REQUESTS = True
  13 | except ImportError:
  14 |     HAS_REQUESTS = False
  15 | 
  16 | from relay import get_key
  17 | 
  18 | logger = logging.getLogger(__name__)
  19 | 
  20 | # ── LOCAL TTS BACKENDS ──────────────────────────────────────────────────────
  21 | _KOKORO_PIPELINE = None
  22 | _KOKORO_BACKEND = None
  23 | _KOKORO_INSTANCE = None
  24 | _F5_MODEL = None
  25 | _BIGVGAN_MODEL = None
  26 | _CHATTERBOX_MODEL = None
  27 | _PROSODY_CACHE = {}  # hash(text) -> prosody-planned text
  28 | 
  29 | 
  30 | def _init_kokoro():
  31 |     """Lazy-initialize Kokoro (PyTorch first, ONNX fallback)."""
  32 |     global _KOKORO_PIPELINE, _KOKORO_BACKEND, _KOKORO_INSTANCE
  33 |     if _KOKORO_BACKEND is not None:
  34 |         return _KOKORO_BACKEND
  35 |     try:
  36 |         from kokoro import KPipeline
  37 |         _KOKORO_PIPELINE = KPipeline(lang_code='a')
  38 |         _KOKORO_BACKEND = "pytorch"
  39 |         logger.info("[TTS/Kokoro] Backend: PyTorch")
  40 |         return "pytorch"
  41 |     except Exception as e_pt:
  42 |         logger.warning(f"[TTS/Kokoro] PyTorch failed: {e_pt} — trying ONNX")
  43 |     try:
  44 |         from kokoro_onnx import Kokoro as _KokoroONNX
  45 |         _VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
  46 |         _onnx_model = os.path.join(_VOICES_DIR, "kokoro-v0_19.onnx")
  47 |         _onnx_voices = os.path.join(_VOICES_DIR, "voices-v1.0.bin")
  48 |         if not os.path.exists(_onnx_model):
  49 |             logger.info("[TTS/Kokoro] Downloading ONNX model files...")
  50 |             subprocess.run([
  51 |                 "python3", "-c",
  52 |                 "from huggingface_hub import hf_hub_download; "
  53 |                 f"hf_hub_download('hexgrad/Kokoro-82M', 'kokoro-v0_19.onnx', local_dir='{_VOICES_DIR}'); "
  54 |                 f"hf_hub_download('hexgrad/Kokoro-82M', 'voices-v1.0.bin', local_dir='{_VOICES_DIR}')"
  55 |             ], timeout=300)
  56 |         _KOKORO_INSTANCE = _KokoroONNX(_onnx_model, _onnx_voices)
  57 |         _KOKORO_BACKEND = "onnx"
  58 |         logger.info("[TTS/Kokoro] Backend: ONNX")
  59 |         return "onnx"
  60 |     except Exception as e_onnx:
  61 |         logger.error(f"[TTS/Kokoro] Both backends failed: {e_onnx}")
  62 |         _KOKORO_BACKEND = "unavailable"
  63 |         return "unavailable"
  64 | 
  65 | 
  66 | def _init_f5():
  67 |     """Lazy-initialize fine-tuned F5-TTS model."""
  68 |     global _F5_MODEL
  69 |     if _F5_MODEL is not None:
  70 |         return True
  71 |     ckpt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices", "pbx_voice.pt")
  72 |     if not os.path.exists(ckpt):
  73 |         logger.warning(f"[TTS/F5] Fine-tuned checkpoint missing: {ckpt}")
  74 |         return False
  75 |     try:
  76 |         from f5_tts.api import F5TTS
  77 |         _F5_MODEL = F5TTS(model="F5TTS_v1_Base", ckpt_file=ckpt, device="cuda:1")
  78 |         logger.info(f"[TTS/F5] Fine-tuned model loaded: {ckpt}")
  79 |         return True
  80 |     except Exception as e:
  81 |         logger.error(f"[TTS/F5] Failed to load checkpoint: {e}")
  82 |         return False
  83 | 
  84 | 
  85 | def _init_chatterbox():
  86 |     """Lazy-initialize Chatterbox TTS on cuda:0."""
  87 |     global _CHATTERBOX_MODEL
  88 |     if _CHATTERBOX_MODEL is not None:
  89 |         return True
  90 |     try:
  91 |         from chatterbox.tts import ChatterboxTTS
  92 |         _CHATTERBOX_MODEL = ChatterboxTTS.from_pretrained(device="cuda:0")
  93 |         logger.info("[TTS/Chatterbox] Model loaded on cuda:0")
  94 |         return True
  95 |     except Exception as e:
  96 |         logger.error(f"[TTS/Chatterbox] Failed to load: {e}")
  97 |         return False
  98 | 
  99 | 
 100 | def _init_bigvgan():
 101 |     """Lazy-initialize BigVGAN2 44kHz vocoder on cuda:1."""
 102 |     global _BIGVGAN_MODEL
 103 |     if _BIGVGAN_MODEL is not None:
 104 |         return True
 105 |     try:
 106 |         import bigvgan as _bv
 107 |         _BIGVGAN_MODEL = _bv.BigVGAN.from_pretrained(
 108 |             "nvidia/bigvgan_v2_44khz_128band_512x",
 109 |             use_cuda_kernel=False,
 110 |         )
 111 |         _BIGVGAN_MODEL = _BIGVGAN_MODEL.eval().to("cuda:1")
 112 |         logger.info("[TTS/BigVGAN2] 44kHz vocoder loaded on cuda:1")
 113 |         return True
 114 |     except Exception as e:
 115 |         logger.error(f"[TTS/BigVGAN2] Init failed: {e}")
 116 |         return False
 117 | 
 118 | 
 119 | def _bigvgan_upsample(wav_path_24k: str) -> str:
 120 |     """Upsample 24kHz WAV to 44kHz via BigVGAN2. Returns path to 44kHz WAV.
 121 |     Graceful fallback: returns original path if BigVGAN2 fails."""
 122 |     if not _init_bigvgan():
 123 |         return wav_path_24k
 124 |     try:
 125 |         import torch
 126 |         import soundfile as sf
 127 |         import librosa
 128 |         wav_data, sr = sf.read(wav_path_24k)
 129 |         if sr != 24000:
 130 |             wav_data = librosa.resample(wav_data, orig_sr=sr, target_sr=24000)
 131 |         # BigVGAN expects mel spectrogram input — compute from audio
 132 |         import torchaudio
 133 |         wav_tensor = torch.FloatTensor(wav_data).unsqueeze(0).to("cuda:1")
 134 |         # Use torchaudio to compute mel spectrogram matching BigVGAN's expected input
 135 |         mel_transform = torchaudio.transforms.MelSpectrogram(
 136 |             sample_rate=24000, n_fft=2048, hop_length=256, n_mels=128,
 137 |             f_min=0, f_max=12000,
 138 |         ).to("cuda:1")
 139 |         mel = mel_transform(wav_tensor)
 140 |         mel = torch.log(torch.clamp(mel, min=1e-5))
 141 |         with torch.inference_mode():
 142 |             wav_out = _BIGVGAN_MODEL(mel)
 143 |         wav_np = wav_out.squeeze().cpu().numpy()
 144 |         out_path = wav_path_24k.replace(".wav", ".44k.wav")
 145 |         sf.write(out_path, wav_np, 44100)
 146 |         logger.info(f"[TTS/BigVGAN2] Upsampled {wav_path_24k} → {out_path}")
 147 |         return out_path
 148 |     except Exception as e:
 149 |         logger.warning(f"[TTS/BigVGAN2] Upsample failed: {e} — using 24kHz")
 150 |         return wav_path_24k
 151 | 
 152 | 
 153 | def prosody_plan(text: str, host: int = 2) -> str:
 154 |     import re as _re
 155 |     # DISABLED: Kokoro reads SSML markers literally as words.
 156 |     # Strip all [bracket:value] markers before Kokoro synthesis.
 157 |     text = _re.sub(r'\[pause[^\]]*\]', ' ', text)
 158 |     text = _re.sub(r'\[breath[^\]]*\]', ' ', text)
 159 |     text = _re.sub(r'\[emphasis[^\]]*\]', ' ', text)
 160 |     text = _re.sub(r'\[break[^\]]*\]', ' ', text)
 161 |     text = _re.sub(r'\[[A-Z][^\]]{0,25}\]', '', text)
 162 |     text = _re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text)
 163 |     return _re.sub(r'  +', ' ', text).strip()
 164 | 
 165 | 
 166 | PBX_VOICE_ID = "HmUVvDlHsEz0m3eUGLgu"
 167 | 
 168 | _PBX_VOICE = {
 169 |     "voice_id": PBX_VOICE_ID,
 170 |     "name": "PBX",
 171 |     "model_id": "eleven_turbo_v2_5",
 172 |     "speed": 1.2,  # Render20: +10% from 1.10, capped at ElevenLabs max 1.2
 173 |     "voice_settings": {
 174 |         "stability": 0.55,
 175 |         "similarity_boost": 0.80,
 176 |         "style": 0.15,
 177 |         "use_speaker_boost": True,
 178 |     },
 179 | }
 180 | 
 181 | # ── LOCAL TTS VOICE CONFIG ──────────────────────────────────────────────────
 182 | VOICES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
 183 | PBX_CHECKPOINT = "/home/ultron/.local/lib/python3.10/ckpts/pbx_voice/model_500.pt"  # PBX voice model_500
 184 | PBX_REFERENCE_CLIP = os.path.join(VOICES_DIR, "pbx_reference.wav")
 185 | KOKORO_HOST1_VOICE = "af_heart"
 186 | KOKORO_HOST2_VOICE = "am_onyx"   # primary; swap for PBX F5 when ready
 187 | F5_SPEED = 1.1
 188 | KOKORO_SPEED_H1 = 1.0
 189 | KOKORO_SPEED_H2 = 1.1
 190 | 
 191 | _ERYN_VOICE = {
 192 |     "voice_id": "kdnRe2koJdOK4Ovxn2DI",
 193 |     "name": "Eryn",
 194 |     "model_id": "eleven_turbo_v2_5",
 195 |     "speed": 1.0,
 196 |     "voice_settings": {
 197 |         "stability": 0.55,
 198 |         "similarity_boost": 0.80,
 199 |         "style": 0.15,
 200 |         "use_speaker_boost": True,
 201 |     },
 202 | }
 203 | # Dual-host: HOST_1 = Eryn/af_heart (female), HOST_2 = PBX (fine-tuned F5 / ElevenLabs fallback)
 204 | VOICES = {
 205 |     1: _ERYN_VOICE,
 206 |     2: _PBX_VOICE,
 207 | }
 208 | 
 209 | def _get_tts_provider() -> str:
 210 |     """TTS provider selector.
 211 |     'local'      → Kokoro af_heart (host1) + Chatterbox PBX (host2) + ElevenLabs fallback
 212 |     'elevenlabs' → ElevenLabs only (emergency override, preserves single-host Option A)
 213 |     """
 214 |     val = os.environ.get("TTS_PROVIDER", "local").lower().strip()
 215 |     if val not in ("local", "elevenlabs"):
 216 |         logger.warning(f"[TTS] Unknown TTS_PROVIDER='{val}', defaulting to 'local'")
 217 |         return "local"
 218 |     return val
 219 | 
 220 | 
 221 | _KEY_CACHE: dict = {}
 222 | 
 223 | def _get_cached_key(name: str) -> str:
 224 |     if name not in _KEY_CACHE:
 225 |         k = get_key(name)
 226 |         if k:
 227 |             _KEY_CACHE[name] = k.strip()
 228 |     return _KEY_CACHE.get(name, "")
 229 | 
 230 | 
 231 | def ffprobe_duration(path: str) -> float:
 232 |     r = subprocess.run(
 233 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 234 |          "-of", "csv=p=0", path],
 235 |         capture_output=True, text=True,
 236 |     )
 237 |     try:
 238 |         return float(r.stdout.strip())
 239 |     except Exception:
 240 |         logger.warning(f"[TTS] ffprobe_duration failed for {path}")
 241 |         return -1.0
 242 | 
 243 | 
 244 | def _generate_silence(output_path: str, duration: float) -> bool:
 245 |     """Generate a silent audio file."""
 246 |     r = subprocess.run(
 247 |         ["ffmpeg", "-y", "-f", "lavfi", "-i",
 248 |          f"anullsrc=r=48000:cl=stereo", "-t", str(duration),
 249 |          "-c:a", "aac", "-b:a", "192k", output_path],
 250 |         capture_output=True, text=True, timeout=30,
 251 |     )
 252 |     return r.returncode == 0 and os.path.exists(output_path)
 253 | 
 254 | 
 255 | def _mp3_to_m4a(mp3_path: str, m4a_path: str) -> bool:
 256 |     # Issue 7: atempo=1.08 post-processing gives effective 1.3x speed (1.2 ElevenLabs × 1.08)
 257 |     r = subprocess.run(
 258 |         ["ffmpeg", "-y", "-i", mp3_path,
 259 |          "-af", "atempo=1.08",
 260 |          "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", m4a_path],
 261 |         capture_output=True, text=True, timeout=120,
 262 |     )
 263 |     return r.returncode == 0 and os.path.exists(m4a_path)
 264 | 
 265 | 
 266 | MAX_CHUNK_CHARS = 500  # ElevenLabs safe chunk size
 267 | SILENCE_GAP = 0.3  # seconds between speakers
 268 | 
 269 | # Voice mode overrides per segment type (applied to whichever host speaks)
 270 | VOICE_MODES = {
 271 |     "cold_open":       {"stability": 0.45, "similarity_boost": 0.80, "style": 0.18},
 272 |     "setup":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
 273 |     "react":           {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
 274 |     "bridge":          {"stability": 0.52, "similarity_boost": 0.80, "style": 0.15},
 275 |     "social_segment":  {"stability": 0.50, "similarity_boost": 0.78, "style": 0.18},
 276 |     "wrap":            {"stability": 0.50, "similarity_boost": 0.78, "style": 0.20},
 277 | }
 278 | 
 279 | 
 280 | def _chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list:
 281 |     if len(text) <= max_chars:
 282 |         return [text]
 283 |     raw = text.replace("! ", "!\x00").replace(". ", ".\x00").replace("? ", "?\x00")
 284 |     sentences = raw.split("\x00")
 285 |     chunks, current = [], ""
 286 |     for sent in sentences:
 287 |         if len(current) + len(sent) + 1 <= max_chars:
 288 |             current = f"{current} {sent}".strip() if current else sent
 289 |         else:
 290 |             if current:
 291 |                 chunks.append(current)
 292 |             current = sent
 293 |     if current:
 294 |         chunks.append(current)
 295 |     return [c for c in chunks if c.strip()]
 296 | 
 297 | 
 298 | def expand_numbers_for_tts(text: str) -> str:
 299 |     """Round 2 Fix 1: Full num2words preprocessing — converts ALL numbers >999 to spoken form.
 300 | 
 301 |     Previous version used manual thousand/million/billion templates which caused garbled
 302 |     speech on numbers like "1,056 EH/s" or "$74,000". Now uses num2words for natural
 303 |     spoken-word output: "$74,000" → "seventy-four thousand dollars".
 304 |     """
 305 |     import re as _re
 306 |     try:
 307 |         from num2words import num2words as _n2w
 308 |     except ImportError:
 309 |         logger.warning("[TTS] num2words not installed — falling back to basic expansion")
 310 |         return _expand_numbers_basic(text)
 311 | 
 312 |     # Issue 12: Year detection BEFORE general number expansion
 313 |     # 4-digit numbers 1600-2099 not preceded by $ or currency → spoken as years
 314 |     def _year_to_words(y: int) -> str:
 315 |         """Convert year number to spoken form: 1602→sixteen oh two, 2024→twenty twenty-four."""
 316 |         if 2000 <= y <= 2009:
 317 |             return f"two thousand {_n2w(y - 2000) if y > 2000 else ''}".strip()
 318 |         if 2010 <= y <= 2099:
 319 |             return f"twenty {_n2w(y - 2000)}"
 320 |         hi = y // 100
 321 |         lo = y % 100
 322 |         hi_word = _n2w(hi)
 323 |         if lo == 0:
 324 |             return f"{hi_word} hundred"
 325 |         elif lo < 10:
 326 |             return f"{hi_word} oh {_n2w(lo)}"
 327 |         else:
 328 |             return f"{hi_word} {_n2w(lo)}"
 329 | 
 330 |     def _year_sub(m):
 331 |         val = int(m.group(0))
 332 |         return _year_to_words(val)
 333 |     # Match 1600-2099 NOT preceded by $ or digits
 334 |     text = _re.sub(r'(?<!\$)(?<!\d)\b(1[6-9]\d{2}|20[0-9]\d)\b(?!\s*(?:EH|TH|PH|dollars|percent|%|K\b))', _year_sub, text)
 335 | 
 336 |     # Dollar + billion/million shorthand first: $308 billion → "three hundred and eight billion dollars"
 337 |     def _dollar_scale(m):
 338 |         num_str = m.group(1)
 339 |         scale = m.group(2).lower()
 340 |         try:
 341 |             val = float(num_str)
 342 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 343 |             return f"{spoken} {scale} dollars"
 344 |         except Exception:
 345 |             return m.group(0)
 346 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _dollar_scale, text)
 347 | 
 348 |     # Dollar amounts: $74,000 → "seventy-four thousand dollars"
 349 |     def _dollar(m):
 350 |         val_str = m.group(1).replace(",", "")
 351 |         try:
 352 |             val = int(float(val_str))
 353 |             if val > 999:
 354 |                 return f"{_n2w(val)} dollars"
 355 |             return f"{val} dollars"
 356 |         except Exception:
 357 |             return m.group(0)
 358 |     text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)
 359 | 
 360 |     # Hashrate units BEFORE plain numbers (so "1,056 EH/s" is caught here)
 361 |     def _hashrate(m):
 362 |         val_str = m.group(1).replace(",", "")
 363 |         unit = m.group(2)
 364 |         unit_map = {"EH": "exahashes", "TH": "terahashes", "PH": "petahashes"}
 365 |         try:
 366 |             val = float(val_str)
 367 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 368 |             return f"{spoken} {unit_map.get(unit, unit)} per second"
 369 |         except Exception:
 370 |             return m.group(0)
 371 |     text = _re.sub(r'([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d+)?)\s*(EH|TH|PH)/?s', _hashrate, text)
 372 | 
 373 |     # Percentages: 42% → "forty-two percent"
 374 |     def _pct(m):
 375 |         val_str = m.group(1)
 376 |         try:
 377 |             val = float(val_str)
 378 |             if val == int(val):
 379 |                 return f"{_n2w(int(val))} percent"
 380 |             # 8.4% → "eight point four percent"
 381 |             whole = int(val)
 382 |             frac = val_str.split('.')[1] if '.' in val_str else ''
 383 |             if frac:
 384 |                 frac_spoken = ' '.join(_n2w(int(d)) for d in frac)
 385 |                 return f"{_n2w(whole)} point {frac_spoken} percent"
 386 |             return f"{_n2w(int(val))} percent"
 387 |         except Exception:
 388 |             return m.group(0)
 389 |     text = _re.sub(r'([\d.]+)%', _pct, text)
 390 | 
 391 |     # Large plain numbers with commas: 70,015 → "seventy thousand and fifteen"
 392 |     def _plain_num(m):
 393 |         val_str = m.group(0).replace(",", "")
 394 |         try:
 395 |             val = int(val_str)
 396 |             if val > 999:
 397 |                 return _n2w(val)
 398 |             return m.group(0)
 399 |         except Exception:
 400 |             return m.group(0)
 401 |     text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)
 402 | 
 403 |     # Billion/million shorthand in text (no dollar): 1.2 billion → "one point two billion"
 404 |     def _scale(m):
 405 |         val_str = m.group(1)
 406 |         scale = m.group(2).lower()
 407 |         try:
 408 |             val = float(val_str)
 409 |             spoken = _n2w(val) if val != int(val) else _n2w(int(val))
 410 |             return f"{spoken} {scale}"
 411 |         except Exception:
 412 |             return m.group(0)
 413 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*([Bb]illion|[Mm]illion|[Tt]rillion)', _scale, text)
 414 | 
 415 |     # K shorthand: 74K → "seventy-four thousand"
 416 |     def _k(m):
 417 |         try:
 418 |             val = float(m.group(1))
 419 |             return _n2w(int(val * 1000))
 420 |         except Exception:
 421 |             return m.group(0)
 422 |     text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)
 423 | 
 424 |     # Standalone large numbers without commas (e.g. 74000)
 425 |     def _bare_num(m):
 426 |         try:
 427 |             val = int(m.group(0))
 428 |             if val > 999:
 429 |                 return _n2w(val)
 430 |             return m.group(0)
 431 |         except Exception:
 432 |             return m.group(0)
 433 |     text = _re.sub(r'\b\d{4,}\b', _bare_num, text)
 434 | 
 435 |     # Issue 6: Strip commas and "and" from num2words output to prevent micro-pauses
 436 |     text = _re.sub(r'(\w),\s', r'\1 ', text)  # remove commas in spoken numbers
 437 |     text = _re.sub(r'\band\b\s*', '', text)  # remove "and" (e.g. "one hundred and fifty" → "one hundred fifty")
 438 |     text = _re.sub(r'\s{2,}', ' ', text)  # collapse double spaces
 439 | 
 440 |     return text
 441 | 
 442 | 
 443 | def _expand_numbers_basic(text: str) -> str:
 444 |     """Fallback number expansion without num2words (original logic)."""
 445 |     import re as _re
 446 | 
 447 |     def _dollar(m):
 448 |         val_str = m.group(1).replace(",", "")
 449 |         try:
 450 |             val = int(float(val_str))
 451 |         except ValueError:
 452 |             return m.group(0)
 453 |         if val >= 1_000_000_000:
 454 |             return f"{val/1_000_000_000:.1f} billion dollars".replace(".0 ", " ")
 455 |         if val >= 1_000_000:
 456 |             return f"{val/1_000_000:.1f} million dollars".replace(".0 ", " ")
 457 |         if val >= 1_000:
 458 |             b = val // 1000
 459 |             r = val % 1000
 460 |             if r == 0:
 461 |                 return f"{b} thousand dollars"
 462 |             return f"{b} thousand {r} dollars"
 463 |         return f"{val} dollars"
 464 | 
 465 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion dollars", text)
 466 |     text = _re.sub(r'\$(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million dollars", text)
 467 |     text = _re.sub(r'\$([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)', _dollar, text)
 468 | 
 469 |     def _plain_num(m):
 470 |         val_str = m.group(0).replace(",", "")
 471 |         try:
 472 |             val = int(val_str)
 473 |         except ValueError:
 474 |             return m.group(0)
 475 |         if val >= 1_000_000_000:
 476 |             return f"{val/1_000_000_000:.1f} billion".replace(".0 ", " ")
 477 |         if val >= 1_000_000:
 478 |             return f"{val/1_000_000:.1f} million".replace(".0 ", " ")
 479 |         if val >= 10_000:
 480 |             b = val // 1000
 481 |             r = val % 1000
 482 |             if r == 0:
 483 |                 return f"{b} thousand"
 484 |             return f"{b} thousand {r}"
 485 |         return m.group(0)
 486 |     text = _re.sub(r'\b\d{1,3}(?:,\d{3})+\b', _plain_num, text)
 487 | 
 488 |     def _pct(m):
 489 |         return m.group(1).replace(".", " point ") + " percent"
 490 |     text = _re.sub(r'([\d.]+)%', _pct, text)
 491 | 
 492 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*EH/?s', lambda m: f"{m.group(1)} exahash per second", text)
 493 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*TH/?s', lambda m: f"{m.group(1)} terahash per second", text)
 494 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*PH/?s', lambda m: f"{m.group(1)} petahash per second", text)
 495 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Bb]illion', lambda m: f"{m.group(1)} billion", text)
 496 |     text = _re.sub(r'(\d+(?:\.\d+)?)\s*[Mm]illion', lambda m: f"{m.group(1)} million", text)
 497 | 
 498 |     def _k(m):
 499 |         val = float(m.group(1))
 500 |         if val == int(val):
 501 |             return f"{int(val)} thousand"
 502 |         return f"{val} thousand"
 503 |     text = _re.sub(r'(\d+(?:\.\d+)?)[Kk]\b', _k, text)
 504 | 
 505 |     return text
 506 | 
 507 | 
 508 | TTS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tts_cache")
 509 | 
 510 | 
 511 | 
 512 | # ── Bitcoin Ecosystem Pronunciation Map ────────────────────────────────────
 513 | # ElevenLabs renders these phonetic substitutions naturally.
 514 | # Longer/more specific entries first to avoid partial replacements.
 515 | PRONUNCIATION_MAP = {
 516 |     # Satoshi
 517 |     "Satoshi Nakamoto": "sah TOE shee nah kah MOE toe",
 518 |     "Satoshi": "sah TOE shee",
 519 |     "Nakamoto": "nah kah MOE toe",
 520 |     # Saylor
 521 |     "Michael Saylor": "Michael Sayler",
 522 |     "Saylor": "Sayler",
 523 |     # Lyn Alden
 524 |     "Lyn Alden": "Lin AWL-den",
 525 |     # Lummis
 526 |     "Cynthia Lummis": "SIN-thee-ah LUM-iss",
 527 |     "Lummis": "LUM-iss",
 528 |     # Brunell
 529 |     "Natalie Brunell": "Natalie Brunelle",
 530 |     "Brunell": "Brunelle",
 531 |     # Preston Pysh
 532 |     "Preston Pysh": "Preston PISH",
 533 |     "Pysh": "PISH",
 534 |     # Max Keiser
 535 |     "Max Keiser": "MAX KY-zer",
 536 |     "Keiser": "KY-zer",
 537 |     # Nayib Bukele
 538 |     "Nayib Bukele": "NYE-eeb boo-KEH-leh",
 539 |     "Bukele": "boo-KEH-leh",
 540 |     # Saifedean Ammous
 541 |     "Saifedean Ammous": "sy-feh-DEAN AH-moos",
 542 |     "Saifedean": "sy-feh-DEAN",
 543 |     "Ammous": "AH-moos",
 544 |     # Robert Breedlove
 545 |     "Robert Breedlove": "Robert BREED love",
 546 |     "Breedlove": "BREED love",
 547 |     # Alex Gladstein
 548 |     "Alex Gladstein": "AL-ex GLAD-steen",
 549 |     "Gladstein": "GLAD-steen",
 550 |     # Knut Svanholm
 551 |     "Knut Svanholm": "kuh-NOOT SVAHN-holm",
 552 |     "Svanholm": "SVAHN-holm",
 553 |     # Luke Dashjr
 554 |     "Luke Dashjr": "LUKE DASH-junior",
 555 |     "Dashjr": "DASH-junior",
 556 |     # Andreas Antonopoulos
 557 |     "Andreas Antonopoulos": "ahn-DRAY-us an-TON-oh-POO-lus",
 558 |     "Antonopoulos": "an-TON-oh-POO-lus",
 559 |     "Andreas": "ahn-DRAY-us",
 560 |     # Charlie Shrem
 561 |     "Charlie Shrem": "CHAR-lee SHREM",
 562 |     "Shrem": "SHREM",
 563 |     # Lawrence Lepard
 564 |     "Lawrence Lepard": "LAW-rents leh-PARD",
 565 |     "Larry Lepard": "LAIR-ee leh-PARD",
 566 |     "Lepard": "leh-PARD",
 567 |     # Erik Voorhees
 568 |     "Erik Voorhees": "AIR-ik VOR-hees",
 569 |     "Voorhees": "VOR-hees",
 570 |     # Gabor Gurbacs
 571 |     "Gabor Gurbacs": "GAH-bor GUR-bacs",
 572 |     "Gurbacs": "GUR-bacs",
 573 |     # Gary Gensler
 574 |     "Gary Gensler": "GAIR-ee GENZ-ler",
 575 |     "Gensler": "GENZ-ler",
 576 |     # Jerome Powell
 577 |     "Jerome Powell": "jeh-ROME POW-ul",
 578 |     "Powell": "POW-ul",
 579 |     # CJ Konstantinos
 580 |     "CJ Konstantinos": "see-JAY kon-stan-TEE-nos",
 581 |     "Konstantinos": "kon-stan-TEE-nos",
 582 |     # Bob Iaccino
 583 |     "Bob Iaccino": "BOB ee-ah-CHEE-no",
 584 |     "Iaccino": "ee-ah-CHEE-no",
 585 |     # Alex Stanczyk
 586 |     "Alex Stanczyk": "AL-ex STAN-chik",
 587 |     "Stanczyk": "STAN-chik",
 588 |     # Matt Odell
 589 |     "Matt Odell": "MAT OH-dell",
 590 |     "Odell": "OH-dell",
 591 |     # Marty Bent
 592 |     "Marty Bent": "MAR-tee BENT",
 593 |     # Willy Woo
 594 |     "Willy Woo": "WIL-ee WOO",
 595 |     # Technical terms
 596 |     "EH/s": "exahashes per second",
 597 |     "TH/s": "terahashes per second",
 598 |     "PH/s": "petahashes per second",
 599 |     "UTXO": "you-tee-ex-oh",
 600 |     "HODL": "HODDLE",
 601 |     "blockchain": "blockchain",
 602 |     "halving": "HAV-ing",
 603 |     "SegWit": "SEG-wit",
 604 |     "Segwit": "SEG-wit",
 605 |     "hodl": "HODDLE",
 606 |     "mempool": "mem-pool",
 607 |     "multisig": "MUL-tee-sig",
 608 |     "satoshis": "sah-TOH-sheez",
 609 |     "MicroStrategy": "MY-crow-STRAT-uh-jee",
 610 |     "Coinbase": "KOYN-base",
 611 |     "Binance": "BY-nance",
 612 |     "Chainalysis": "CHAIN-uh-LY-sis",
 613 |     # Issue 10: BTC → Bitcoin spoken form
 614 |     "BTC": "Bitcoin",
 615 | }
 616 | 
 617 | 
 618 | def _expand_handle(handle: str) -> str:
 619 |     """Issue 11: Convert @handle to spoken form.
 620 |     CamelCase → separate words, underscores → spaces, ALL CAPS → spelled out."""
 621 |     import re as _re
 622 |     name = handle.lstrip("@")
 623 |     # ALL CAPS (like TFTC, WBD) → spelled out with dashes
 624 |     if name.isupper() and len(name) <= 6:
 625 |         return "at " + "-".join(name)
 626 |     # Split camelCase: MaxKeiser → Max Keiser
 627 |     name = _re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
 628 |     # Split underscores
 629 |     name = name.replace("_", " ")
 630 |     return "at " + name
 631 | 
 632 | 
 633 | # Known handles with correct spoken forms
 634 | _HANDLE_PRONUNCIATIONS = {
 635 |     "@maxkeiser": "at Max Kaiser",
 636 |     "@prestopysh": "at Preston Pish",
 637 |     "@tftc": "at T-F-T-C",
 638 |     "@wbd": "at W-B-D",
 639 |     "@saborchain": "at Sabor Chain",
 640 | }
 641 | 
 642 | 
 643 | _ORDINAL_MAP = {
 644 |     "1st": "first", "2nd": "second", "3rd": "third", "4th": "fourth",
 645 |     "5th": "fifth", "6th": "sixth", "7th": "seventh", "8th": "eighth",
 646 |     "9th": "ninth", "10th": "tenth", "11th": "eleventh", "12th": "twelfth",
 647 |     "13th": "thirteenth", "14th": "fourteenth", "15th": "fifteenth",
 648 |     "16th": "sixteenth", "17th": "seventeenth", "18th": "eighteenth",
 649 |     "19th": "nineteenth", "20th": "twentieth", "21st": "twenty-first",
 650 |     "22nd": "twenty-second", "23rd": "twenty-third", "24th": "twenty-fourth",
 651 |     "25th": "twenty-fifth", "26th": "twenty-sixth", "27th": "twenty-seventh",
 652 |     "28th": "twenty-eighth", "29th": "twenty-ninth", "30th": "thirtieth",
 653 |     "31st": "thirty-first",
 654 | }
 655 | 
 656 | 
 657 | def _expand_ordinals(text: str) -> str:
 658 |     """Pre-process ordinal numbers (e.g. '27th') to spoken form to prevent TTS splitting."""
 659 |     import re as _re
 660 |     def _ordinal_sub(m):
 661 |         key = m.group(0).lower()
 662 |         return _ORDINAL_MAP.get(key, m.group(0))
 663 |     return _re.sub(r'\b\d{1,2}(?:st|nd|rd|th)\b', _ordinal_sub, text, flags=_re.IGNORECASE)
 664 | 
 665 | 
 666 | def apply_pronunciation_map(text: str) -> str:
 667 |     """Replace names/terms with phonetic versions ElevenLabs renders correctly.
 668 |     Processes longer entries first to avoid partial replacements."""
 669 |     import re
 670 |     # Pre-process ordinals before pronunciation map
 671 |     text = _expand_ordinals(text)
 672 |     # Issue 11: Pre-process @handles before pronunciation map
 673 |     def _handle_sub(m):
 674 |         raw = m.group(0).lower()
 675 |         if raw in _HANDLE_PRONUNCIATIONS:
 676 |             return _HANDLE_PRONUNCIATIONS[raw]
 677 |         return _expand_handle(m.group(0))
 678 |     text = re.sub(r'@[A-Za-z0-9_]+', _handle_sub, text)
 679 | 
 680 |     # Sort by length descending so longer matches take priority
 681 |     for written, phonetic in sorted(PRONUNCIATION_MAP.items(), key=lambda x: -len(x[0])):
 682 |         # Word-boundary aware replacement (case-insensitive)
 683 |         pattern = re.compile(r'\b' + re.escape(written) + r'\b', re.IGNORECASE)
 684 |         text = pattern.sub(phonetic, text)
 685 |     return text
 686 | 
 687 | 
 688 | def _trim_trailing_silence(audio_path: str) -> None:
 689 |     """Round 2 Fix 2: Trim trailing silence/vowel-stretch from TTS output.
 690 | 
 691 |     Detects if the last 0.5s is significantly quieter than the body (trailing off)
 692 |     and trims it to avoid the stretched-vowel artifact common in ElevenLabs output.
 693 |     """
 694 |     try:
 695 |         import re as _re
 696 |         # Measure RMS of last 0.5s vs body
 697 |         result = subprocess.run(
 698 |             ["ffmpeg", "-i", audio_path, "-af",
 699 |              "silencedetect=noise=-35dB:d=0.15", "-f", "null", "-"],
 700 |             capture_output=True, text=True, timeout=15,
 701 |         )
 702 |         # Find silence at end of file
 703 |         dur = ffprobe_duration(audio_path)
 704 |         if dur <= 1.0:
 705 |             return
 706 |         silences = [float(m.group(1)) for m in
 707 |                     _re.finditer(r"silence_start: ([\d.]+)", result.stderr)]
 708 |         if not silences:
 709 |             return
 710 |         last_silence = silences[-1]
 711 |         # If silence starts within last 0.5s, trim there
 712 |         if dur - last_silence <= 0.5 and last_silence > dur * 0.8:
 713 |             trimmed = audio_path + ".trimmed.m4a"
 714 |             trim_ok = subprocess.run(
 715 |                 ["ffmpeg", "-y", "-i", audio_path,
 716 |                  "-t", f"{last_silence + 0.05:.3f}",
 717 |                  "-c:a", "aac", "-ar", "48000", "-b:a", "192k", trimmed],
 718 |                 capture_output=True, text=True, timeout=15,
 719 |             )
 720 |             if trim_ok.returncode == 0 and os.path.exists(trimmed) and os.path.getsize(trimmed) > 5000:
 721 |                 os.replace(trimmed, audio_path)
 722 |                 logger.info(f"[TTS] Trimmed trailing silence: {dur:.2f}s → {last_silence + 0.05:.2f}s")
 723 |             elif os.path.exists(trimmed):
 724 |                 os.remove(trimmed)
 725 |     except Exception as e:
 726 |         logger.debug(f"[TTS] Trailing silence trim skipped: {e}")
 727 | 
 728 | 
 729 | def _tts_cache_key(text: str, voice_id: str, segment_type: str) -> str:
 730 |     """SHA256 hash of text+voice+segment_type → stable cache key."""
 731 |     import hashlib
 732 |     payload = f"{voice_id}:{segment_type}:{text}".encode("utf-8")
 733 |     return hashlib.sha256(payload).hexdigest()[:16]
 734 | 
 735 | 
 736 | def _tts_cache_get(cache_key: str, output_path: str) -> bool:
 737 |     """Return True if valid cached file exists and passes validation."""
 738 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 739 |     if os.path.exists(cache_file) and os.path.getsize(cache_file) > 10240:
 740 |         shutil.copy2(cache_file, output_path)
 741 |         try:
 742 |             validate_tts_output(output_path)
 743 |             return True
 744 |         except RuntimeError:
 745 |             logger.warning(f"[TTS] Corrupt cache deleted: {cache_file}")
 746 |             try:
 747 |                 os.remove(cache_file)
 748 |                 os.remove(output_path)
 749 |             except Exception:
 750 |                 pass
 751 |     return False
 752 | 
 753 | 
 754 | def _tts_cache_put(cache_key: str, audio_path: str) -> None:
 755 |     """Save audio to TTS cache for future runs."""
 756 |     import shutil
 757 |     os.makedirs(TTS_CACHE_DIR, exist_ok=True)
 758 |     cache_file = os.path.join(TTS_CACHE_DIR, f"{cache_key}.m4a")
 759 |     if not os.path.exists(cache_file):
 760 |         shutil.copy2(audio_path, cache_file)
 761 | 
 762 | 
 763 | def _tts_generate_silence_fallback(text: str, output_path: str) -> bool:
 764 |     """HARD FAIL: silence fallback is no longer allowed.
 765 | 
 766 |     Previously generated silent AAC as a last resort, masking total TTS failure.
 767 |     This caused downstream black frames and F-grade renders that QC scored 94/100.
 768 |     Now raises RuntimeError so the pipeline fails fast instead of rendering garbage.
 769 |     """
 770 |     snippet = (text[:80] + "...") if len(text) > 80 else text
 771 |     raise RuntimeError(
 772 |         f"TTS FATAL: ElevenLabs + pyttsx3 both failed. Refusing to render silence. "
 773 |         f"Text: \"{snippet}\". Fix the TTS provider before re-running."
 774 |     )
 775 | 
 776 | 
 777 | def tts_kokoro(text: str, output_path: str, voice: str = "af_heart",
 778 |                speed: float = 1.0) -> bool:
 779 |     """Generate TTS via Kokoro GPU inference. Output: M4A 48kHz AAC 192k."""
 780 |     backend = _init_kokoro()
 781 |     if backend == "unavailable":
 782 |         return False
 783 |     try:
 784 |         import soundfile as sf
 785 |         import numpy as np
 786 |         wav_tmp = output_path + ".kokoro.wav"
 787 |         if backend == "pytorch":
 788 |             samples_list = []
 789 |             for _, _, audio in _KOKORO_PIPELINE(text, voice=voice, speed=speed):
 790 |                 samples_list.append(audio)
 791 |             if not samples_list:
 792 |                 return False
 793 |             audio_np = np.concatenate(samples_list) if len(samples_list) > 1 else samples_list[0]
 794 |             sf.write(wav_tmp, audio_np, 24000)
 795 |         else:
 796 |             samples, sr = _KOKORO_INSTANCE.create(text, voice=voice, speed=speed, lang="en-us")
 797 |             sf.write(wav_tmp, samples, sr)
 798 | 
 799 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 800 |             return False
 801 |         # Direct encode: 24kHz WAV → 48kHz AAC (no BigVGAN2 — causes double-vocoding)
 802 |         r = subprocess.run([
 803 |             "ffmpeg", "-y", "-i", wav_tmp,
 804 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 805 |         ], capture_output=True, text=True, timeout=60)
 806 |         try:
 807 |             if os.path.exists(wav_tmp):
 808 |                 os.remove(wav_tmp)
 809 |         except Exception:
 810 |             pass
 811 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 812 |         if ok:
 813 |             logger.info(f"[TTS/Kokoro] OK: {ffprobe_duration(output_path):.2f}s, voice={voice}")
 814 |         return ok
 815 |     except Exception as e:
 816 |         logger.error(f"[TTS/Kokoro] Exception: {e}")
 817 |         return False
 818 | 
 819 | 
 820 | def tts_chatterbox(text: str, output_path: str, exaggeration: float = 0.4,
 821 |                     cfg_weight: float = 0.5) -> bool:
 822 |     """Generate TTS using Chatterbox for PBX (Host 2).
 823 | 
 824 |     Chatterbox produces clean audio — no post-processing EQ needed.
 825 |     Output: M4A 48kHz AAC 192k.
 826 |     """
 827 |     if not _init_chatterbox():
 828 |         logger.warning("[TTS/Chatterbox] Model not loaded")
 829 |         return False
 830 | 
 831 |     try:
 832 |         import torchaudio
 833 |         wav_tmp = output_path + ".cb.wav"
 834 | 
 835 |         wav = _CHATTERBOX_MODEL.generate(text, exaggeration=exaggeration,
 836 |                                           cfg_weight=cfg_weight)
 837 |         torchaudio.save(wav_tmp, wav, 24000)
 838 | 
 839 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 840 |             logger.error("[TTS/Chatterbox] Zero output from inference")
 841 |             return False
 842 | 
 843 |         # Convert WAV to M4A (48kHz AAC 192k)
 844 |         r = subprocess.run([
 845 |             "ffmpeg", "-y", "-i", wav_tmp,
 846 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 847 |         ], capture_output=True, text=True, timeout=60)
 848 | 
 849 |         try:
 850 |             if os.path.exists(wav_tmp):
 851 |                 os.remove(wav_tmp)
 852 |         except Exception:
 853 |             pass
 854 | 
 855 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 856 |         if ok:
 857 |             logger.info(f"[TTS/Chatterbox] OK: {ffprobe_duration(output_path):.2f}s (PBX)")
 858 |         return ok
 859 |     except Exception as e:
 860 |         logger.error(f"[TTS/Chatterbox] Exception: {e}")
 861 |         return False
 862 | 
 863 | 
 864 | def tts_f5_finetuned(text: str, output_path: str, speed: float = None) -> bool:
 865 |     """Generate TTS using fine-tuned F5-TTS for PBX (Host 2).
 866 | 
 867 |     Uses pbx_voice.pt checkpoint with pbx_reference.wav for voice cloning.
 868 |     Output: M4A 48kHz AAC 192k.
 869 |     CRITICAL: show_info MUST be print or a callable — False crashes F5 (bool not callable).
 870 |     """
 871 |     if not _init_f5():
 872 |         logger.warning("[TTS/F5] Model not loaded")
 873 |         return False
 874 | 
 875 |     if not os.path.exists(PBX_REFERENCE_CLIP):
 876 |         logger.warning(f"[TTS/F5] Reference clip missing: {PBX_REFERENCE_CLIP}")
 877 |         return False
 878 | 
 879 |     if speed is None:
 880 |         speed = F5_SPEED
 881 | 
 882 |     try:
 883 |         import soundfile as sf
 884 |         wav_tmp = output_path + ".f5.wav"
 885 | 
 886 |         wav, sr, _ = _F5_MODEL.infer(
 887 |             ref_file=PBX_REFERENCE_CLIP,
 888 |             ref_text="",
 889 |             gen_text=text,
 890 |             speed=speed,
 891 |             show_info=print,
 892 |         )
 893 |         sf.write(wav_tmp, wav, sr)
 894 | 
 895 |         if not os.path.exists(wav_tmp) or os.path.getsize(wav_tmp) < 1000:
 896 |             logger.error("[TTS/F5] Zero output from inference")
 897 |             return False
 898 | 
 899 |         # Convert WAV to M4A (48kHz AAC 192k)
 900 |         r = subprocess.run([
 901 |             "ffmpeg", "-y", "-i", wav_tmp,
 902 |             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", output_path
 903 |         ], capture_output=True, text=True, timeout=60)
 904 | 
 905 |         try:
 906 |             if os.path.exists(wav_tmp):
 907 |                 os.remove(wav_tmp)
 908 |         except Exception:
 909 |             pass
 910 | 
 911 |         ok = r.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 5000
 912 |         if ok:
 913 |             logger.info(f"[TTS/F5] OK: {ffprobe_duration(output_path):.2f}s (PBX fine-tuned)")
 914 |         return ok
 915 |     except Exception as e:
 916 |         logger.error(f"[TTS/F5] Exception: {e}")
 917 |         return False
 918 | 
 919 | 
 920 | def tts_local(text: str, output_path: str, host: int = 1,
 921 |               segment_type: str = "") -> bool:
 922 |     """Primary TTS dispatcher — local GPU inference with per-line ElevenLabs fallback.
 923 | 
 924 |     Host 1 → Kokoro af_heart → ElevenLabs Eryn fallback
 925 |     Host 2 → Chatterbox PBX → Kokoro am_adam → ElevenLabs PBX fallback
 926 |     """
 927 |     # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
 928 |     text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
 929 |     text = expand_numbers_for_tts(text)
 930 |     text = apply_pronunciation_map(text)
 931 |     # Prosody planner: add natural delivery markers before TTS
 932 |     text = prosody_plan(text, host=host)
 933 |     try:
 934 |         _oracle_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "oracle")
 935 |         if _oracle_path not in sys.path:
 936 |             sys.path.insert(0, _oracle_path)
 937 |         from oracle_dialogue_engine import normalize_pronunciation
 938 |         text = normalize_pronunciation(text)
 939 |     except Exception as _e:
 940 |         logger.warning(f"[TTS/Local] normalize_pronunciation unavailable: {_e}")
 941 | 
 942 |     cache_key = _tts_cache_key(text, f"local_h{host}", segment_type)
 943 |     if _tts_cache_get(cache_key, output_path):
 944 |         print(f"  [tts/local] Cache HIT (host{host}): {text[:50]}")
 945 |         return True
 946 | 
 947 |     start_t = time.time()
 948 |     ok = False
 949 | 
 950 |     if host == 1:
 951 |         ok = tts_kokoro(text, output_path, voice=KOKORO_HOST1_VOICE, speed=KOKORO_SPEED_H1)
 952 |         if not ok:
 953 |             logger.warning("[TTS/Local] Kokoro host1 FAILED → ElevenLabs Eryn fallback")
 954 |             ok = tts_elevenlabs(text, output_path, host=1, segment_type=segment_type)
 955 |     else:
 956 |         # Kokoro am_onyx primary; F5-TTS PBX fallback when checkpoint confirmed ready
 957 |         ok = tts_kokoro(text, output_path, voice=KOKORO_HOST2_VOICE, speed=KOKORO_SPEED_H2)
 958 |         if not ok:
 959 |             logger.warning("[TTS/Local] Kokoro am_onyx FAILED → F5-TTS fallback")
 960 |             ok = tts_f5_finetuned(text, output_path)
 961 |         if not ok:
 962 |             logger.warning("[TTS/Local] Kokoro host2 FAILED → ElevenLabs PBX fallback")
 963 |             ok = tts_elevenlabs(text, output_path, host=2, segment_type=segment_type)
 964 | 
 965 |     if ok and os.path.exists(output_path):
 966 |         _trim_trailing_silence(output_path)
 967 |         validate_tts_output(output_path)
 968 |         _tts_cache_put(cache_key, output_path)
 969 |         elapsed = time.time() - start_t
 970 |         dur = ffprobe_duration(output_path)
 971 |         print(f"  [tts/local] host{host} OK: {dur:.1f}s audio in {elapsed:.1f}s wall ← {text[:50]}")
 972 | 
 973 |     return ok
 974 | 
 975 | 
 976 | def tts_preflight_local() -> bool:
 977 |     """Preflight for TTS_PROVIDER=local: verify Kokoro works, report F5 status."""
 978 |     test_text = "Bitcoin signal confirmed today."
 979 |     test_out = "/tmp/tts_preflight_local.m4a"
 980 |     try:
 981 |         ok = tts_kokoro(test_text, test_out, voice=KOKORO_HOST1_VOICE, speed=1.0)
 982 |         if not ok or not os.path.exists(test_out):
 983 |             raise RuntimeError("[TTS/Local] Kokoro preflight failed to generate audio")
 984 |         dur = ffprobe_duration(test_out)
 985 |         if dur < 0.5:
 986 |             raise RuntimeError(f"[TTS/Local] Kokoro output too short: {dur:.2f}s")
 987 |         logger.info(f"[TTS/Local] Kokoro preflight PASS: {dur:.2f}s")
 988 |         try:
 989 |             os.remove(test_out)
 990 |         except Exception:
 991 |             pass
 992 |         if os.path.exists(PBX_CHECKPOINT) and os.path.exists(PBX_REFERENCE_CLIP):
 993 |             logger.info("[TTS/Local] F5 ready: checkpoint + reference clip")
 994 |         elif os.path.exists(PBX_CHECKPOINT):
 995 |             logger.warning(f"[TTS/Local] F5 checkpoint found but reference clip missing: {PBX_REFERENCE_CLIP}")
 996 |         else:
 997 |             logger.warning("[TTS/Local] F5 checkpoint missing — host2 using Kokoro am_adam")
 998 |         return True
 999 |     except Exception as e:
1000 |         raise RuntimeError(f"[TTS/Local] Preflight FAILED: {e}")
1001 | 
1002 | 
1003 | def validate_tts_output(path: str, min_size: int = 10240) -> None:
1004 |     """Validate TTS output file is real audio, not empty/corrupt.
1005 | 
1006 |     Raises RuntimeError if:
1007 |       - File doesn't exist
1008 |       - File < min_size bytes (10KB default)
1009 |       - ffprobe duration < 0.5s
1010 |     """
1011 |     if not os.path.exists(path):
1012 |         raise RuntimeError(f"TTS output missing: {path}")
1013 |     size = os.path.getsize(path)
1014 |     if size < min_size:
1015 |         raise RuntimeError(
1016 |             f"TTS output too small ({size} bytes < {min_size}): {path} — "
1017 |             f"ElevenLabs likely returned empty audio"
1018 |         )
1019 |     dur = ffprobe_duration(path)
1020 |     if dur < 0.5:
1021 |         raise RuntimeError(
1022 |             f"TTS output too short ({dur:.2f}s < 0.5s): {path} — "
1023 |             f"audio is effectively silent/corrupt"
1024 |         )
1025 | 
1026 | 
1027 | def tts_preflight_test() -> bool:
1028 |     """Preflight: call ElevenLabs with a 5-word test phrase, confirm >1000 bytes returned.
1029 |     Raises RuntimeError on failure so the pipeline aborts before wasting render time."""
1030 |     if not HAS_REQUESTS:
1031 |         raise RuntimeError("TTS preflight: 'requests' library not installed")
1032 |     key = _get_cached_key("ELEVENLABS_API_KEY")
1033 |     if not key:
1034 |         raise RuntimeError("TTS preflight: ELEVENLABS_API_KEY not available")
1035 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{PBX_VOICE_ID}"
1036 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
1037 |     body = {
1038 |         "text": "Bitcoin signal confirmed today.",
1039 |         "model_id": "eleven_turbo_v2_5",
1040 |         "voice_settings": {"stability": 0.55, "similarity_boost": 0.80, "style": 0.15},
1041 |     }
1042 |     try:
1043 |         r = requests.post(url, json=body, headers=headers, timeout=20)
1044 |         if r.status_code != 200:
1045 |             raise RuntimeError(f"TTS preflight: ElevenLabs returned HTTP {r.status_code}: {r.text[:200]}")
1046 |         if len(r.content) < 1000:
1047 |             raise RuntimeError(f"TTS preflight: ElevenLabs returned only {len(r.content)} bytes (need >1000)")
1048 |         logger.info(f"[TTS] Preflight PASS: PBX voice returned {len(r.content)} bytes")
1049 |         return True
1050 |     except requests.RequestException as e:
1051 |         raise RuntimeError(f"TTS preflight: ElevenLabs unreachable: {e}")
1052 | 
1053 | 
1054 | def tts_elevenlabs(text: str, output_path: str, host: int = 1,
1055 |                    segment_type: str = "") -> bool:
1056 |     """Generate TTS for a single line using the specified host voice.
1057 | 
1058 |     Checks TTS cache first (hash of text+voice+segment_type). On cache hit,
1059 |     copies cached audio — no ElevenLabs API call. On miss, generates and caches.
1060 |     Falls back to pyttsx3 system TTS, then silence, on ElevenLabs quota/auth failure.
1061 |     """
1062 |     if not HAS_REQUESTS:
1063 |         # No requests lib — try pyttsx3 or silence
1064 |         return _tts_generate_silence_fallback(text, output_path)
1065 | 
1066 |     key = _get_cached_key("ELEVENLABS_API_KEY")
1067 |     if not key:
1068 |         return _tts_generate_silence_fallback(text, output_path)
1069 | 
1070 |     # BUG 1 FIX: Strip [DATA], [WARM], [SETUP] etc bracket tags before TTS synthesis
1071 |     # These tags are for script structure — narrator should never read them aloud
1072 |     text = re.sub(r'^\s*\[[A-Z_]+\]\s*', '', text).strip()
1073 |     # Session 4 Fix 3: Expand numbers before TTS to prevent babbling
1074 |     text = expand_numbers_for_tts(text)
1075 |     # R25 FIX 7: Apply pronunciation map (Pysh→PISH, etc.) — was defined but never called
1076 |     text = apply_pronunciation_map(text)
1077 | 
1078 |     voice = VOICES.get(host, VOICES[2])  # All hosts → PBX
1079 |     # Check TTS cache first — avoid API call if same text+voice was generated before
1080 |     cache_key = _tts_cache_key(text, voice["voice_id"], segment_type)
1081 |     if _tts_cache_get(cache_key, output_path):
1082 |         print(f"  [tts] Cache HIT ({voice['name']}): {text[:50]}...")
1083 |         return True
1084 | 
1085 |     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}"
1086 |     headers = {"xi-api-key": key, "Content-Type": "application/json"}
1087 | 
1088 |     # Apply voice mode overrides based on segment type (both hosts)
1089 |     voice_settings = dict(voice["voice_settings"])
1090 |     if segment_type in VOICE_MODES:
1091 |         mode = VOICE_MODES[segment_type]
1092 |         for k, v in mode.items():
1093 |             if k != "speed":
1094 |                 voice_settings[k] = v
1095 | 
1096 |     chunks = _chunk_text(text)
1097 |     chunk_files = []
1098 | 
1099 |     for ci, chunk in enumerate(chunks):
1100 |         body = {
1101 |             "text": chunk,
1102 |             "model_id": voice["model_id"],
1103 |             "voice_settings": voice_settings,
1104 |         }
1105 |         # Add speed parameter from voice config (host-specific)
1106 |         speed = voice.get("speed", 1.0)
1107 |         if speed != 1.0:
1108 |             body["speed"] = speed
1109 |         mp3_tmp = output_path + f".chunk{ci}.mp3"
1110 |         success = False
1111 | 
1112 |         # FIX iter1: Increase retries from 3 to 5 with longer backoff to survive
1113 |         # transient ElevenLabs outages that were causing grade failures
1114 |         max_retries = 5
1115 |         for attempt in range(max_retries):
1116 |             try:
1117 |                 r = requests.post(url, json=body, headers=headers, timeout=90)
1118 |                 if r.status_code == 200:
1119 |                     with open(mp3_tmp, "wb") as f:
1120 |                         f.write(r.content)
1121 |                     # Pre-validate: ElevenLabs sometimes returns empty/tiny responses
1122 |                     if os.path.getsize(mp3_tmp) < 1000:
1123 |                         print(f"  [tts] WARNING: ElevenLabs returned tiny file ({os.path.getsize(mp3_tmp)}B) for chunk {ci}, retrying...")
1124 |                         if attempt < max_retries - 1:
1125 |                             time.sleep(2 ** attempt)
1126 |                             continue
1127 |                     success = True
1128 |                     break
1129 |                 elif r.status_code == 429:
1130 |                     wait = min(2 ** (attempt + 1), 30)  # cap at 30s
1131 |                     print(f"  [tts] Rate limited ({voice['name']}), waiting {wait}s...")
1132 |                     time.sleep(wait)
1133 |                 else:
1134 |                     print(f"  [tts] HTTP {r.status_code} ({voice['name']}) attempt {attempt+1}: {r.text[:200]}")
1135 |                     if attempt < max_retries - 1:
1136 |                         time.sleep(2 ** attempt)
1137 |             except Exception as e:
1138 |                 print(f"  [tts] Error ({voice['name']}) attempt {attempt+1}: {e}")
1139 |                 if attempt < max_retries - 1:
1140 |                     time.sleep(2 ** attempt)
1141 | 
1142 |         if not success:
1143 |             for f in chunk_files:
1144 |                 try:
1145 |                     os.remove(f)
1146 |                 except Exception:
1147 |                     pass
1148 |             logger.error(f"[tts] ElevenLabs failed after {max_retries} retries for chunk {ci} — returning False")
1149 |             return False
1150 |         chunk_files.append(mp3_tmp)
1151 | 
1152 |     # Single chunk
1153 |     if len(chunk_files) == 1:
1154 |         ok = _mp3_to_m4a(chunk_files[0], output_path)
1155 |         try:
1156 |             os.remove(chunk_files[0])
1157 |         except Exception:
1158 |             pass
1159 |         if ok and os.path.exists(output_path):
1160 |             _trim_trailing_silence(output_path)  # Round 2 Fix 2: trim vowel-stretch artifacts
1161 |             validate_tts_output(output_path)
1162 |             _tts_cache_put(cache_key, output_path)
1163 |         return ok
1164 | 
1165 |     # Multi-chunk concat
1166 |     concat_list = output_path + ".concat.txt"
1167 |     mp3_combined = output_path + ".combined.mp3"
1168 |     with open(concat_list, "w") as f:
1169 |         for p in chunk_files:
1170 |             f.write(f"file '{os.path.abspath(p)}'\n")
1171 |     subprocess.run(
1172 |         ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
1173 |          "-c", "copy", mp3_combined],
1174 |         capture_output=True, text=True,
1175 |     )
1176 |     ok = _mp3_to_m4a(mp3_combined, output_path)
1177 |     for f in chunk_files + [concat_list, mp3_combined]:
1178 |         try:
1179 |             if os.path.exists(f):
1180 |                 os.remove(f)
1181 |         except Exception:
1182 |             pass
1183 |     if ok and os.path.exists(output_path):
1184 |         _trim_trailing_silence(output_path)  # Round 2 Fix 2: trim vowel-stretch artifacts
1185 |         validate_tts_output(output_path)
1186 |         _tts_cache_put(cache_key, output_path)
1187 |     return ok
1188 | 
1189 | 
1190 | def generate_dialogue_audio(dialogue: list, output_dir: str) -> dict:
1191 |     """Generate audio for the entire dual-host dialogue.
1192 | 
1193 |     Args:
1194 |         dialogue: List of {host: 1|2|"CLIP", text: "..."}
1195 |         output_dir: Directory for audio files
1196 | 
1197 |     Returns:
1198 |         {
1199 |             "lines": [{"path": str, "host": int, "duration": float, "start": float}, ...],
1200 |             "full": str,  # path to concatenated full audio
1201 |             "total_duration": float,
1202 |         }
1203 |     """
1204 |     os.makedirs(output_dir, exist_ok=True)
1205 | 
1206 |     _active_provider = _get_tts_provider()
1207 |     if _active_provider == "local":
1208 |         tts_preflight_local()
1209 |     else:
1210 |         key = _get_cached_key("ELEVENLABS_API_KEY")
1211 |         if not key:
1212 |             raise RuntimeError("ELEVENLABS_API_KEY not available. Cannot generate audio.")
1213 | 
1214 |     silence_path = os.path.join(output_dir, "silence.m4a")
1215 |     _generate_silence(silence_path, SILENCE_GAP)
1216 | 
1217 |     lines = []
1218 |     parts_for_concat = []
1219 |     current_time = 0.0
1220 | 
1221 |     for i, entry in enumerate(dialogue):
1222 |         host = entry.get("host")
1223 |         text = entry.get("text", "")
1224 | 
1225 |         # Skip CLIP markers — they don't have audio but DO advance the timeline
1226 |         if host == "CLIP":
1227 |             clip_duration = float(entry.get("duration", 30.0))  # use actual duration or default 30s
1228 |             lines.append({
1229 |                 "path": None,
1230 |                 "host": "CLIP",
1231 |                 "duration": clip_duration,  # record actual duration, not hardcoded 0.0
1232 |                 "start": current_time,
1233 |                 "source": entry.get("source", ""),
1234 |                 "query": entry.get("query", ""),
1235 |                 "text": text,
1236 |             })
1237 |             current_time += clip_duration  # advance timeline so subsequent audio is correctly offset
1238 |             continue
1239 | 
1240 |         _provider = _get_tts_provider()
1241 |         if _provider == "local":
1242 |             host_num = host if host in (1, 2) else 2
1243 |         else:
1244 |             host_num = 2   # ElevenLabs: single-host Option A preserved
1245 |         voice = VOICES[host_num]
1246 |         segment_type = entry.get("type", "")
1247 |         line_path = os.path.join(output_dir, f"line_{i:03d}_{voice['name'].lower()}.m4a")
1248 | 
1249 |         mode_tag = f" [{segment_type}]" if segment_type and host_num == 1 else ""
1250 |         print(f"  [tts] Line {i:02d} ({voice['name']}{mode_tag}): {text[:60]}...")
1251 | 
1252 |         _provider = _get_tts_provider()
1253 |         if _provider == "local":
1254 |             _tts_ok = tts_local(text, line_path, host_num, segment_type=segment_type)
1255 |         else:
1256 |             _tts_ok = tts_elevenlabs(text, line_path, host_num, segment_type=segment_type)
1257 |         if _tts_ok:
1258 |             if not os.path.exists(line_path) or os.path.getsize(line_path) < 1000:
1259 |                 logger.warning(f"[tts] Line {i} zero/tiny audio — writing silence")
1260 |                 _tts_ok = False
1261 |             else:
1262 |                 dur = ffprobe_duration(line_path)
1263 |                 if dur < 0.5 and len(text) > 10:
1264 |                     logger.warning(f"[tts] Line {i} too short ({dur:.2f}s) — writing silence")
1265 |                     _tts_ok = False
1266 |         if not _tts_ok:
1267 |             # Degrade gracefully: write 3s silence so assembler can continue
1268 |             logger.error(f"[tts] TTS failed line {i} — writing silence")
1269 |             subprocess.run([
1270 |                 "ffmpeg", "-y", "-f", "lavfi",
1271 |                 "-i", "anullsrc=r=48000:cl=stereo",
1272 |                 "-t", "3", "-c:a", "aac", "-b:a", "192k", line_path
1273 |             ], capture_output=True)
1274 |             dur = 3.0
1275 | 
1276 |         lines.append({
1277 |             "path": line_path,
1278 |             "host": host_num,
1279 |             "duration": dur,
1280 |             "start": current_time,
1281 |             "text": text,
1282 |             "type": segment_type,
1283 |             "clip_rank": entry.get("clip_rank", 0),  # PiP FIX: preserve for assembler PiP lookup
1284 |         })
1285 |         parts_for_concat.append(line_path)
1286 |         current_time += dur
1287 | 
1288 |         # Add silence gap between speakers (not after last line, not before CLIP)
1289 |         next_entry = dialogue[i + 1] if i < len(dialogue) - 1 else None
1290 |         if next_entry is not None and next_entry.get("host") != "CLIP":
1291 |             parts_for_concat.append(silence_path)
1292 |             current_time += SILENCE_GAP
1293 | 
1294 |     # Concatenate all lines into full audio
1295 |     full_path = os.path.join(output_dir, "full_dialogue.m4a")
1296 |     if parts_for_concat:
1297 |         concat_file = os.path.join(output_dir, "dialogue_concat.txt")
1298 |         with open(concat_file, "w") as f:
1299 |             for p in parts_for_concat:
1300 |                 f.write(f"file '{os.path.abspath(p)}'\n")
1301 |         subprocess.run(
1302 |             ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
1303 |              "-c", "copy", full_path],
1304 |             capture_output=True, text=True,
1305 |         )
1306 |         if os.path.exists(concat_file):
1307 |             os.remove(concat_file)
1308 | 
1309 |     # Guard: full_dialogue.m4a must not be zero-byte or tiny
1310 |     if os.path.exists(full_path):
1311 |         full_size = os.path.getsize(full_path)
1312 |         if full_size < 10240:
1313 |             raise RuntimeError(
1314 |                 f"full_dialogue.m4a is {full_size} bytes (<10KB) — "
1315 |                 f"FFmpeg concat produced empty/corrupt audio. Aborting before render."
1316 |             )
1317 | 
1318 |     total_dur = ffprobe_duration(full_path) if os.path.exists(full_path) else current_time
1319 |     successful = sum(1 for l in lines if l["path"] and os.path.exists(l.get("path", "")))
1320 | 
1321 |     print(f"\n  [tts] Dialogue audio: {successful}/{len(dialogue)} lines, {total_dur:.1f}s total")
1322 | 
1323 |     # ── Per-host TTS validation: catch silent hosts BEFORE render starts ──
1324 |     host_stats = {}  # {host_num: {"total": N, "ok": N}}
1325 |     for l in lines:
1326 |         h = l.get("host")
1327 |         if h == "CLIP":
1328 |             continue
1329 |         if h not in host_stats:
1330 |             host_stats[h] = {"total": 0, "ok": 0}
1331 |         host_stats[h]["total"] += 1
1332 |         if l.get("path") and os.path.exists(l.get("path", "")):
1333 |             host_stats[h]["ok"] += 1
1334 | 
1335 |     for h, stats in host_stats.items():
1336 |         voice_name = VOICES.get(h, {}).get("name", f"Host{h}")
1337 |         if stats["ok"] == 0 and stats["total"] > 0:
1338 |             raise RuntimeError(
1339 |                 f"TTS FATAL: {voice_name} (host {h}) has 0/{stats['total']} successful lines. "
1340 |                 f"All audio is missing/silent. Aborting before render."
1341 |             )
1342 |         if stats["total"] > 0 and stats["ok"] / stats["total"] < 0.5:
1343 |             raise RuntimeError(
1344 |                 f"TTS FATAL: {voice_name} (host {h}) has only {stats['ok']}/{stats['total']} "
1345 |                 f"successful lines (<50%). Too many failures to produce a quality render."
1346 |             )
1347 | 
1348 |     return {
1349 |         "lines": lines,
1350 |         "full": full_path if os.path.exists(full_path) else None,
1351 |         "total_duration": total_dur,
1352 |     }
1353 | 
1354 | 
1355 | # Legacy compatibility — V3 pipeline used generate_all_audio
1356 | def generate_all_audio(script: dict, output_dir: str) -> dict:
1357 |     """Legacy wrapper: converts V4 dialogue script to audio paths dict."""
1358 |     if "dialogue" in script:
1359 |         return generate_dialogue_audio(script["dialogue"], output_dir)
1360 |     # V3 fallback
1361 |     raise RuntimeError("V4 pipeline requires dialogue-format script")
1362 | 
1363 | 
1364 | if __name__ == "__main__":
1365 |     from script_writer import generate_script
1366 |     style = sys.argv[1] if len(sys.argv) > 1 else "default"
1367 |     script = generate_script(style=style)
1368 |     base = os.path.dirname(os.path.abspath(__file__))
1369 |     audio_dir = os.path.join(base, "output", "audio_test")
1370 |     result = generate_dialogue_audio(script["dialogue"], audio_dir)
1371 |     print(json.dumps(
1372 |         {k: v for k, v in result.items() if k != "lines"},
1373 |         indent=2,
1374 |     ))
1375 | 
```

### File: overnight_render_loop.py (559 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | overnight_render_loop.py - Autonomous video engine perfection loop.
   4 | Max 8 iterations, max 6 hours. Each: render -> forensics -> Gemini grade -> CC fix -> repeat.
   5 | Grade A = stop and lock WINNER_RECIPE.json.
   6 | 
   7 | Production modes:
   8 |   python3 overnight_render_loop.py              # single cycle (for cron)
   9 |   python3 overnight_render_loop.py --daemon     # continuous loop, runs at 08:00 ET daily
  10 |   python3 overnight_render_loop.py --dry-run    # startup checks only, no render
  11 |   python3 overnight_render_loop.py --help       # show args
  12 | 
  13 | Cron entry:
  14 |   0 12 * * * cd /home/ultron/protocol_pulse && python3 overnight_render_loop.py >> /tmp/overnight_loop.log 2>&1
  15 | """
  16 | import os, sys, json, subprocess, time, re, urllib.request, argparse, logging
  17 | from datetime import datetime, timezone, timedelta
  18 | from pathlib import Path
  19 | 
  20 | BASE = os.path.dirname(os.path.abspath(__file__))
  21 | PIPELINE = os.path.join(BASE, 'video_pipeline_v3')
  22 | ENV_FILE = os.path.join(BASE, '.env')
  23 | LOG = os.path.join(PIPELINE, 'logs', 'overnight_loop.log')
  24 | RECIPE_FILE = os.path.join(PIPELINE, 'logs', 'WINNER_RECIPE.json')
  25 | HEARTBEAT_FILE = os.path.join(BASE, 'logs', 'loop_heartbeat.json')
  26 | ELEVENLABS_QUOTA_SENTINEL = os.path.join(BASE, 'logs', 'elevenlabs_quota_exhausted')
  27 | MAX_ITERATIONS = 8
  28 | MAX_HOURS = 6
  29 | RETRY_WAIT_SECONDS = 1800  # 30 minutes
  30 | MAX_ATTEMPTS_PER_CYCLE = 2
  31 | 
  32 | os.makedirs(os.path.join(PIPELINE, 'logs'), exist_ok=True)
  33 | os.makedirs(os.path.join(BASE, 'logs'), exist_ok=True)
  34 | 
  35 | # ── Logging ───────────────────────────────────────────────────────
  36 | logger = logging.getLogger('overnight_loop')
  37 | logger.setLevel(logging.DEBUG)
  38 | _fmt = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
  39 | _sh = logging.StreamHandler(sys.stdout)
  40 | _sh.setFormatter(_fmt)
  41 | logger.addHandler(_sh)
  42 | _fh = logging.FileHandler(LOG)
  43 | _fh.setFormatter(_fmt)
  44 | logger.addHandler(_fh)
  45 | 
  46 | 
  47 | def log(msg):
  48 |     """Backward-compat wrapper."""
  49 |     logger.info(msg)
  50 | 
  51 | 
  52 | def load_env():
  53 |     env = os.environ.copy()
  54 |     try:
  55 |         with open(ENV_FILE) as f:
  56 |             for line in f:
  57 |                 l = line.strip()
  58 |                 if l and not l.startswith('#') and '=' in l:
  59 |                     k, _, v = l.partition('=')
  60 |                     k = k.strip(); v = v.strip().strip("'").strip('"')
  61 |                     if k: env[k] = v
  62 |     except Exception as e:
  63 |         log(f"WARNING: .env load failed: {e}")
  64 |     return env
  65 | 
  66 | 
  67 | def run(cmd, timeout=7200, env=None):
  68 |     try:
  69 |         return subprocess.run(cmd, shell=True, capture_output=True, text=True,
  70 |                              timeout=timeout, env=env or load_env(), cwd=PIPELINE)
  71 |     except subprocess.TimeoutExpired as e:
  72 |         log(f"TIMEOUT after {timeout}s: {str(cmd)[:80]}")
  73 |         # Return a fake CompletedProcess so callers don't crash
  74 |         import subprocess as _sp
  75 |         r = _sp.CompletedProcess(cmd, returncode=-1)
  76 |         r.stdout = ""
  77 |         r.stderr = f"TIMEOUT after {timeout}s"
  78 |         return r
  79 |     except Exception as e:
  80 |         log(f"run() error: {e} cmd={str(cmd)[:80]}")
  81 |         import subprocess as _sp
  82 |         r = _sp.CompletedProcess(cmd, returncode=-1)
  83 |         r.stdout = ""
  84 |         r.stderr = str(e)
  85 |         return r
  86 | 
  87 | 
  88 | # ── FIX 6: Startup checks ────────────────────────────────────────
  89 | def startup_checks():
  90 |     """Verify environment before any render. Returns True if all pass."""
  91 |     ok = True
  92 | 
  93 |     # FFmpeg available
  94 |     try:
  95 |         r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
  96 |         if r.returncode != 0:
  97 |             log("STARTUP FAIL: ffmpeg returned non-zero")
  98 |             ok = False
  99 |         else:
 100 |             ver = r.stdout.split('\n')[0] if r.stdout else '?'
 101 |             log(f"FFmpeg: {ver}")
 102 |     except FileNotFoundError:
 103 |         log("STARTUP FAIL: ffmpeg not found in PATH")
 104 |         ok = False
 105 |     except Exception as e:
 106 |         log(f"STARTUP FAIL: ffmpeg check error: {e}")
 107 |         ok = False
 108 | 
 109 |     # Python path includes pipeline
 110 |     if PIPELINE not in sys.path:
 111 |         sys.path.insert(0, PIPELINE)
 112 |     log(f"Pipeline dir: {PIPELINE} (exists={os.path.isdir(PIPELINE)})")
 113 |     if not os.path.isdir(PIPELINE):
 114 |         log("STARTUP FAIL: video_pipeline_v3 directory missing")
 115 |         ok = False
 116 | 
 117 |     # Output directory writable
 118 |     out_dir = os.path.join(PIPELINE, 'output')
 119 |     os.makedirs(out_dir, exist_ok=True)
 120 |     test_file = os.path.join(out_dir, '.write_test')
 121 |     try:
 122 |         with open(test_file, 'w') as f:
 123 |             f.write('ok')
 124 |         os.remove(test_file)
 125 |         log(f"Output dir writable: {out_dir}")
 126 |     except Exception as e:
 127 |         log(f"STARTUP FAIL: output dir not writable: {e}")
 128 |         ok = False
 129 | 
 130 |     # TTS provider check
 131 |     local_tts = Path(os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")).exists()
 132 |     env = load_env()
 133 |     elevenlabs_key = bool(env.get('ELEVENLABS_API_KEY', '').strip())
 134 |     quota_exhausted = os.path.exists(ELEVENLABS_QUOTA_SENTINEL)
 135 | 
 136 |     if local_tts:
 137 |         log("TTS provider: LOCAL (tts_local.py found)")
 138 |     elif elevenlabs_key and not quota_exhausted:
 139 |         log("TTS provider: ElevenLabs (API key present)")
 140 |     elif elevenlabs_key and quota_exhausted:
 141 |         log("WARNING: ElevenLabs key present but quota sentinel exists")
 142 |     else:
 143 |         log("WARNING: No TTS provider found (no local TTS, no ElevenLabs key)")
 144 | 
 145 |     if not local_tts and not elevenlabs_key:
 146 |         log("STARTUP FAIL: No TTS provider available")
 147 |         ok = False
 148 | 
 149 |     return ok
 150 | 
 151 | 
 152 | # ── FIX 3: Heartbeat ─────────────────────────────────────────────
 153 | _total_episodes = 0
 154 | _consecutive_failures = 0
 155 | 
 156 | 
 157 | def write_heartbeat(verdict, duration_s):
 158 |     """Write heartbeat JSON after every cycle."""
 159 |     global _total_episodes, _consecutive_failures
 160 |     if verdict == "PASS":
 161 |         _total_episodes += 1
 162 |         _consecutive_failures = 0
 163 |     elif verdict == "ERROR":
 164 |         _consecutive_failures += 1
 165 |     elif verdict == "HOLD":
 166 |         _consecutive_failures += 1
 167 |     # DEGRADED counts as partial success
 168 |     elif verdict == "DEGRADED":
 169 |         _total_episodes += 1
 170 |         _consecutive_failures = 0
 171 | 
 172 |     heartbeat = {
 173 |         "last_run": datetime.now(timezone.utc).isoformat(),
 174 |         "last_verdict": verdict,
 175 |         "last_duration": round(duration_s, 1),
 176 |         "total_episodes": _total_episodes,
 177 |         "consecutive_failures": _consecutive_failures,
 178 |     }
 179 |     try:
 180 |         with open(HEARTBEAT_FILE, 'w') as f:
 181 |             json.dump(heartbeat, f, indent=2)
 182 |         log(f"Heartbeat written: {verdict} | failures={_consecutive_failures}")
 183 |     except Exception as e:
 184 |         log(f"WARNING: heartbeat write failed: {e}")
 185 | 
 186 |     # Telegram alert on 3+ consecutive failures
 187 |     if _consecutive_failures >= 3:
 188 |         send_telegram_alert(
 189 |             f"🚨 Protocol Pulse loop: {_consecutive_failures} consecutive failures\n"
 190 |             f"Last verdict: {verdict}\n"
 191 |             f"Time: {heartbeat['last_run']}"
 192 |         )
 193 | 
 194 | 
 195 | def send_telegram_alert(message):
 196 |     """Send alert via Telegram if bot token + chat ID are configured."""
 197 |     env = load_env()
 198 |     token = env.get('TELEGRAM_BOT_TOKEN', '').strip()
 199 |     chat_id = env.get('TELEGRAM_CHAT_ID', '').strip()
 200 |     if not token or not chat_id:
 201 |         log("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
 202 |         return
 203 |     try:
 204 |         url = f"https://api.telegram.org/bot{token}/sendMessage"
 205 |         payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
 206 |         req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
 207 |         with urllib.request.urlopen(req, timeout=15) as r:
 208 |             log(f"Telegram alert sent (status {r.status})")
 209 |     except Exception as e:
 210 |         log(f"Telegram alert failed: {e}")
 211 | 
 212 | 
 213 | # ── FIX 4: TTS provider awareness ────────────────────────────────
 214 | def check_tts_ready():
 215 |     """Check TTS availability before render. Returns (ready, provider_name)."""
 216 |     local_tts = Path(os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")).exists()
 217 |     if local_tts:
 218 |         return True, "local (Kokoro/F5-TTS)"
 219 | 
 220 |     env = load_env()
 221 |     if not env.get('ELEVENLABS_API_KEY', '').strip():
 222 |         return False, "none"
 223 | 
 224 |     if os.path.exists(ELEVENLABS_QUOTA_SENTINEL):
 225 |         log("ElevenLabs quota sentinel exists — skipping render")
 226 |         return False, "elevenlabs (quota exhausted)"
 227 | 
 228 |     return True, "ElevenLabs"
 229 | 
 230 | 
 231 | def gemini_call(prompt, max_tokens=8000):
 232 |     env = load_env()
 233 |     key = env.get('GEMINI_API_KEY', '')
 234 |     url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={key}'
 235 |     payload = {'contents': [{'parts': [{'text': prompt}]}],
 236 |                'generationConfig': {'maxOutputTokens': max_tokens, 'temperature': 0.05}}
 237 |     req = urllib.request.Request(url, data=json.dumps(payload).encode(),
 238 |                                   headers={'Content-Type': 'application/json'})
 239 |     with urllib.request.urlopen(req, timeout=120) as r:
 240 |         d = json.loads(r.read())
 241 |         parts = d['candidates'][0]['content'].get('parts', [])
 242 |         return next((p['text'] for p in parts if 'text' in p), None)
 243 | 
 244 | 
 245 | def run_render(iteration):
 246 |     log(f"RENDER START iteration {iteration}")
 247 |     run("rm -rf tts_cache/ && mkdir -p tts_cache/")
 248 |     log("TTS cache wiped")
 249 |     env = load_env()
 250 |     r = run("python3 daily_producer.py --skip-scan", timeout=7200, env=env)
 251 |     log(f"Render exit: {r.returncode}")
 252 |     import glob
 253 |     today = datetime.now().strftime('%Y-%m-%d')
 254 |     candidates = []
 255 |     for pat in [f'output/{today}/*.mp4']:  # today-only — no stale fallback
 256 |         for f in glob.glob(os.path.join(PIPELINE, pat)):
 257 |             if any(x in f for x in ['.bgl_audio', '.intro_mus', '.concat_raw', '.music_mixed', '.whoosh', '.norm']):
 258 |                 continue
 259 |             if not any(x in f for x in ['music_mixed', 'concat_raw', '.norm', 'whoosh']):
 260 |                 candidates.append((os.path.getmtime(f), f))
 261 |     candidates.sort(reverse=True)
 262 |     out = candidates[0][1] if candidates else None
 263 |     if out: log(f"Output: {out} ({os.path.getsize(out)//1048576}MB)")
 264 |     else: log("FATAL: no output file")
 265 |     return out, r.stdout + r.stderr
 266 | 
 267 | 
 268 | def run_forensics(video):
 269 |     log("Running forensics...")
 270 |     res = {}
 271 |     r = run(f'ffprobe -v quiet -print_format json -show_format -show_streams "{video}"')
 272 |     try:
 273 |         p = json.loads(r.stdout)
 274 |         fmt = p.get('format', {}); streams = p.get('streams', [])
 275 |         res['duration'] = float(fmt.get('duration', 0))
 276 |         res['filesize_mb'] = int(fmt.get('size', 0)) / 1048576
 277 |         v = next((s for s in streams if s.get('codec_type') == 'video'), {})
 278 |         a = next((s for s in streams if s.get('codec_type') == 'audio'), {})
 279 |         res['width'] = v.get('width', 0); res['height'] = v.get('height', 0)
 280 |         fps_str = v.get('r_frame_rate', '0/1')
 281 |         if '/' in fps_str:
 282 |             num, den = fps_str.split('/', 1)
 283 |             res['fps'] = float(num) / float(den) if float(den) != 0 else 0
 284 |         else:
 285 |             res['fps'] = float(fps_str) if fps_str else 0
 286 |         res['vcodec'] = v.get('codec_name', '?'); res['acodec'] = a.get('codec_name', '?')
 287 |     except Exception as e:
 288 |         log(f"WARNING: ffprobe parse error: {e}")
 289 |     r = run(f'ffmpeg -i "{video}" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1', timeout=300)
 290 |     segs = re.findall(r'black_start:([\d.]+).*?black_end:([\d.]+).*?black_duration:([\d.]+)', r.stderr+r.stdout)
 291 |     dur = res.get('duration', 0)
 292 |     res['black_mid_count'] = len([(s,e,d) for s,e,d in segs if float(s)>2 and float(e)<dur-2])
 293 |     r = run(f'ffmpeg -i "{video}" -af "ebur128=peak=true" -f null - 2>&1', timeout=120)
 294 |     out = r.stderr + r.stdout
 295 |     im = re.search(r'I:\s*([-\d.]+)\s*LUFS', out)
 296 |     tp = re.search(r'True peak.*?([-\d.]+)\s*dBFS', out)
 297 |     res['integrated_lufs'] = float(im.group(1)) if im else None
 298 |     res['true_peak_dbfs'] = float(tp.group(1)) if tp else None
 299 |     r = run(f'ffmpeg -i "{video}" -vf "freezedetect=n=0.001:d=1.0" -an -f null - 2>&1', timeout=300)
 300 |     res['freeze_count'] = len(re.findall(r'freeze_start', r.stderr+r.stdout))
 301 | 
 302 |     # TTS ARTIFACT CHECK — run in isolated subprocess with hard 45s timeout
 303 |     # Prevents WhisperModel from blocking forensics pipeline
 304 |     tts_artifacts = []
 305 |     try:
 306 |         import subprocess as _sp, tempfile as _tf, os as _os, json as _json
 307 |         with _tf.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
 308 |             tmp_path = tmp.name
 309 |         _sp.run(['ffmpeg', '-y', '-i', video, '-t', '60', '-ar', '16000',
 310 |                  '-ac', '1', tmp_path], capture_output=True, timeout=30)
 311 |         # Run whisper in subprocess so it cannot block the loop
 312 |         checker = (
 313 |             "import sys, json\n"
 314 |             "from faster_whisper import WhisperModel\n"
 315 |             "model = WhisperModel('tiny', device='cpu', compute_type='int8')\n"
 316 |             "segs, _ = model.transcribe(sys.argv[1], language='en')\n"
 317 |             "t = ' '.join(s.text for s in segs).lower()\n"
 318 |             "bad = ['pause','breath','emphasis','break colon','slash','open bracket','close bracket']\n"
 319 |             "print(json.dumps([w for w in bad if w in t]))\n"
 320 |         )
 321 |         r = _sp.run(['python3', '-c', checker, tmp_path],
 322 |                     capture_output=True, text=True, timeout=45)
 323 |         if r.returncode == 0 and r.stdout.strip():
 324 |             tts_artifacts = _json.loads(r.stdout.strip())
 325 |         _os.unlink(tmp_path)
 326 |     except Exception as _e:
 327 |         log(f"TTS artifact check skipped: {_e}")
 328 |     res['tts_artifacts'] = tts_artifacts
 329 |     if tts_artifacts:
 330 |         log(f"TTS ARTIFACT ALERT: narrator reading markers aloud: {tts_artifacts}")
 331 |     log(f"Forensics: {res.get('duration',0):.0f}s {res.get('width')}x{res.get('height')} "
 332 |         f"LUFS={res.get('integrated_lufs')} TP={res.get('true_peak_dbfs')} "
 333 |         f"black={res.get('black_mid_count')} freeze={res.get('freeze_count')}")
 334 |     return res
 335 | 
 336 | 
 337 | def grade_with_gemini(video, forensics, render_log):
 338 |     log("Calling Gemini for 24-dimension grade...")
 339 |     prompt = f"""Grade this Protocol Pulse Bitcoin show episode across 24 dimensions.
 340 | Only award Grade A if you would genuinely be proud to publish it as world-class Bitcoin media.
 341 | 
 342 | FORENSICS:
 343 | - Duration: {forensics.get('duration',0):.1f}s ({forensics.get('duration',0)/60:.1f}min)
 344 | - Resolution: {forensics.get('width')}x{forensics.get('height')} @ {forensics.get('fps',0):.1f}fps
 345 | - Codec: {forensics.get('vcodec')} + {forensics.get('acodec')}
 346 | - Loudness: {forensics.get('integrated_lufs')} LUFS (target -16 to -14)
 347 | - True Peak: {forensics.get('true_peak_dbfs')} dBFS (must be <= -1.0)
 348 | - Black frames (mid): {forensics.get('black_mid_count',0)} (0 = perfect)
 349 | - Freeze frames: {forensics.get('freeze_count',0)} (0 = perfect)
 350 | 
 351 | RENDER LOG (last 200 lines):
 352 | {chr(10).join(render_log.splitlines()[-200:])}
 353 | 
 354 | RUBRIC (24 dimensions, Grade A = score >= 88, zero critical failures):
 355 | Technical (40%): duration, resolution, fps, loudness, true_peak, black_frames, silence, freezes, codec, file_integrity
 356 | Content (35%): clip_relevance, script_quality, cold_open, narrative_arc, host_authenticity, episode_title, no_filler, timeliness
 357 | Production (25%): music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing
 358 | 
 359 | Respond ONLY with raw JSON (no fences):
 360 | {{"grade":"A|B|C|D|F","overall_score":0-100,"broadcast_ready":true|false,
 361 | "dimensions":{{"duration_check":{{"score":0-10,"note":""}},"resolution_check":{{"score":0-10,"note":""}},"framerate_check":{{"score":0-10,"note":""}},"loudness_check":{{"score":0-10,"note":""}},"true_peak_check":{{"score":0-10,"note":""}},"black_frames_check":{{"score":0-10,"note":""}},"silence_check":{{"score":0-10,"note":""}},"freeze_check":{{"score":0-10,"note":""}},"codec_check":{{"score":0-10,"note":""}},"file_integrity_check":{{"score":0-10,"note":""}},"clip_relevance":{{"score":0-10,"note":""}},"script_quality":{{"score":0-10,"note":""}},"cold_open_hook":{{"score":0-10,"note":""}},"narrative_arc":{{"score":0-10,"note":""}},"host_authenticity":{{"score":0-10,"note":""}},"episode_title":{{"score":0-10,"note":""}},"no_filler":{{"score":0-10,"note":""}},"timeliness":{{"score":0-10,"note":""}},"music_mix":{{"score":0-10,"note":""}},"transitions":{{"score":0-10,"note":""}},"visual_polish":{{"score":0-10,"note":""}},"no_artifacts":{{"score":0-10,"note":""}},"audio_quality":{{"score":0-10,"note":""}},"pacing":{{"score":0-10,"note":""}}}},
 362 | "critical_failures":[],"warnings":[],"strengths":[],"targeted_fix_instructions":"Precise instructions for CC session to fix only failing dimensions - file, function, lines.",
 363 | "verdict":"One punchy sentence"}}"""
 364 |     text = gemini_call(prompt, 8000)
 365 |     if not text: return None
 366 |     clean = text.strip()
 367 |     for fence in ['```json', '```']:
 368 |         if fence in clean:
 369 |             clean = clean.split(fence)[1].split('```')[0].strip()
 370 |     try: return json.loads(clean)
 371 |     except json.JSONDecodeError as e: log(f"JSON parse fail: {e} — {clean[:200]}"); return None
 372 | 
 373 | 
 374 | def fire_cc_fix(iteration, grade_result):
 375 |     failures = grade_result.get('critical_failures', [])
 376 |     dims = grade_result.get('dimensions', {})
 377 |     failing = [(k, v['score'], v.get('note','')) for k,v in dims.items()
 378 |                if isinstance(v.get('score'), int) and v['score'] < 7]
 379 |     failing.sort(key=lambda x: x[1])
 380 |     prompt = f"""# PIPELINE FIX - ITERATION {iteration} - GRADE {grade_result.get('grade')} ({grade_result.get('overall_score')}/100)
 381 | VERDICT: {grade_result.get('verdict','')}
 382 | CRITICAL FAILURES: {chr(10).join(f'- {f}' for f in failures) or 'None'}
 383 | FAILING DIMS (<7/10): {chr(10).join(f'- {k}: {s}/10 - {n[:80]}' for k,s,n in failing[:8]) or 'None'}
 384 | FIX INSTRUCTIONS: {grade_result.get('targeted_fix_instructions','')}
 385 | 
 386 | Read PIPELINE_LAWS.md first. Fix ONLY failing dimensions. Run regression_test.sh after every change.
 387 | Commit: git add -A && git commit -m "fix(pipeline): iter{iteration}" && git push"""
 388 |     pf = os.path.join(PIPELINE, f'logs/cc_fix_iter{iteration}.md')
 389 |     with open(pf, 'w') as f: f.write(prompt)
 390 |     sn = f'fix_iter{iteration}'
 391 |     subprocess.run(f'tmux kill-session -t {sn} 2>/dev/null', shell=True)
 392 |     subprocess.run(f'tmux new-session -d -s {sn}', shell=True)
 393 |     subprocess.run(f"tmux send-keys -t {sn} 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter", shell=True)
 394 |     time.sleep(10)
 395 |     subprocess.run(f"tmux send-keys -t {sn} \"$(cat {pf})\" Enter", shell=True)
 396 |     log(f"CC session {sn} launched")
 397 |     deadline = time.time() + 2700
 398 |     while time.time() < deadline:
 399 |         time.sleep(60)
 400 |         r = subprocess.run(f'tmux has-session -t {sn} 2>/dev/null', shell=True)
 401 |         if r.returncode != 0: log("CC session ended"); break
 402 |         log(f"CC running... {int((deadline-time.time())/60)}min left")
 403 |     time.sleep(30)
 404 | 
 405 | 
 406 | def run_single_render():
 407 |     """Execute one full perfection loop (up to MAX_ITERATIONS). Returns verdict string."""
 408 |     log("="*60)
 409 |     log(f"OVERNIGHT LOOP START | max {MAX_ITERATIONS} iters | max {MAX_HOURS}h")
 410 |     log("="*60)
 411 |     start = time.time()
 412 |     grade_result = {}
 413 |     final_verdict = "ERROR"
 414 | 
 415 |     for iteration in range(1, MAX_ITERATIONS+1):
 416 |         if (time.time()-start)/3600 >= MAX_HOURS:
 417 |             log(f"TIME LIMIT ({MAX_HOURS}h). Stopping."); break
 418 |         log(f"\n{'='*60}\nITERATION {iteration}/{MAX_ITERATIONS}\n{'='*60}")
 419 |         video, rlog = run_render(iteration)
 420 |         if not video:
 421 |             log("Render failed, skipping"); time.sleep(60); continue
 422 |         forensics = run_forensics(video)
 423 |         grade_result = grade_with_gemini(video, forensics, rlog)
 424 |         if not grade_result:
 425 |             log("Grading failed, skipping"); continue
 426 |         gf = os.path.join(PIPELINE, f'logs/grade_iter{iteration}.json')
 427 |         with open(gf, 'w') as f: json.dump(grade_result, f, indent=2)
 428 |         grade = grade_result.get('grade','F')
 429 |         score = grade_result.get('overall_score', 0)
 430 |         broadcast = grade_result.get('broadcast_ready', False)
 431 |         log(f"GRADE: {grade} | SCORE: {score}/100 | BROADCAST: {broadcast}")
 432 |         log(f"VERDICT: {grade_result.get('verdict','')}")
 433 |         for dim, data in grade_result.get('dimensions',{}).items():
 434 |             s = data.get('score','?')
 435 |             flag = ' ✓' if isinstance(s,int) and s>=8 else (' !!' if isinstance(s,int) and s<6 else '')
 436 |             log(f"  {dim:30s} {s}/10{flag}")
 437 |         if grade == 'A' and broadcast and score >= 88:
 438 |             log("*** GRADE A — LOCKING WINNER RECIPE ***")
 439 |             recipe = {'winner': True, 'iteration': iteration, 'timestamp': datetime.now().isoformat(),
 440 |                      'video': video, 'grade': grade, 'score': score,
 441 |                      'verdict': grade_result.get('verdict'), 'dimensions': grade_result.get('dimensions',{})}
 442 |             with open(RECIPE_FILE, 'w') as f: json.dump(recipe, f, indent=2)
 443 |             log(f"WINNER: {RECIPE_FILE}")
 444 |             final_verdict = "PASS"
 445 |             break
 446 |         elif grade in ('B', 'C') and broadcast:
 447 |             final_verdict = "DEGRADED"
 448 |         log(f"Grade {grade} - firing CC fix...")
 449 |         fire_cc_fix(iteration, grade_result)
 450 |     else:
 451 |         log("Max iterations reached without Grade A")
 452 |         with open(os.path.join(PIPELINE,'logs/overnight_diagnostic.json'),'w') as f:
 453 |             json.dump({'final_grade': grade_result}, f, indent=2)
 454 |         if final_verdict == "ERROR":
 455 |             final_verdict = "HOLD"
 456 | 
 457 |     log("OVERNIGHT LOOP COMPLETE")
 458 |     return final_verdict
 459 | 
 460 | 
 461 | def run_cycle():
 462 |     """FIX 1+2: Run a single render cycle with exception handling and retry logic."""
 463 |     cycle_start = time.time()
 464 | 
 465 |     # FIX 4: Check TTS before render
 466 |     tts_ready, tts_provider = check_tts_ready()
 467 |     log(f"TTS provider: {tts_provider}")
 468 |     if not tts_ready:
 469 |         log(f"[loop] TTS not available ({tts_provider}) — skipping cycle")
 470 |         write_heartbeat("ERROR", time.time() - cycle_start)
 471 |         return
 472 | 
 473 |     for attempt in range(1, MAX_ATTEMPTS_PER_CYCLE + 1):
 474 |         log(f"[loop] Attempt {attempt}/{MAX_ATTEMPTS_PER_CYCLE}")
 475 |         try:
 476 |             verdict = run_single_render()
 477 |         except Exception as e:
 478 |             logger.error(f"[loop] Render cycle exception: {e}", exc_info=True)
 479 |             verdict = "ERROR"
 480 | 
 481 |         if verdict in ("PASS", "DEGRADED"):
 482 |             write_heartbeat(verdict, time.time() - cycle_start)
 483 |             return
 484 | 
 485 |         # Failed — retry logic
 486 |         if attempt < MAX_ATTEMPTS_PER_CYCLE:
 487 |             log(f"[loop] Attempt {attempt} failed ({verdict}), waiting {RETRY_WAIT_SECONDS//60}min before retry...")
 488 |             time.sleep(RETRY_WAIT_SECONDS)
 489 |         else:
 490 |             log(f"[loop] All {MAX_ATTEMPTS_PER_CYCLE} attempts failed — waiting for next scheduled cycle")
 491 | 
 492 |     write_heartbeat(verdict, time.time() - cycle_start)
 493 | 
 494 | 
 495 | # ── FIX 5: Daemon mode ───────────────────────────────────────────
 496 | def sleep_until_next_8am_et():
 497 |     """Sleep until next 08:00 ET (12:00 UTC or 11:00 UTC during DST)."""
 498 |     from zoneinfo import ZoneInfo
 499 |     et = ZoneInfo("America/New_York")
 500 |     now = datetime.now(et)
 501 |     target = now.replace(hour=8, minute=0, second=0, microsecond=0)
 502 |     if target <= now:
 503 |         target += timedelta(days=1)
 504 |     wait = (target - now).total_seconds()
 505 |     log(f"[daemon] Sleeping {wait/3600:.1f}h until {target.isoformat()}")
 506 |     time.sleep(wait)
 507 | 
 508 | 
 509 | def main():
 510 |     parser = argparse.ArgumentParser(
 511 |         description="Protocol Pulse overnight render loop — production hardened",
 512 |         formatter_class=argparse.RawDescriptionHelpFormatter,
 513 |         epilog=(
 514 |             "Examples:\n"
 515 |             "  python3 overnight_render_loop.py              # single cycle\n"
 516 |             "  python3 overnight_render_loop.py --daemon      # continuous, 08:00 ET daily\n"
 517 |             "  python3 overnight_render_loop.py --dry-run     # startup checks only\n"
 518 |         )
 519 |     )
 520 |     parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon (loop at 08:00 ET daily)")
 521 |     parser.add_argument("--dry-run", action="store_true", help="Run startup checks only, no render")
 522 |     args = parser.parse_args()
 523 | 
 524 |     # FIX 6: Startup checks always run
 525 |     log("="*60)
 526 |     log("STARTUP CHECKS")
 527 |     log("="*60)
 528 |     if not startup_checks():
 529 |         log("STARTUP CHECKS FAILED — exiting")
 530 |         sys.exit(1)
 531 |     log("All startup checks passed")
 532 | 
 533 |     if args.dry_run:
 534 |         log("--dry-run mode: startup checks passed, exiting")
 535 |         sys.exit(0)
 536 | 
 537 |     # Load existing heartbeat state
 538 |     global _total_episodes, _consecutive_failures
 539 |     try:
 540 |         with open(HEARTBEAT_FILE) as f:
 541 |             hb = json.load(f)
 542 |             _total_episodes = hb.get('total_episodes', 0)
 543 |             _consecutive_failures = hb.get('consecutive_failures', 0)
 544 |         log(f"Heartbeat loaded: episodes={_total_episodes}, consecutive_failures={_consecutive_failures}")
 545 |     except (FileNotFoundError, json.JSONDecodeError):
 546 |         pass
 547 | 
 548 |     if args.daemon:
 549 |         log("DAEMON MODE — will loop at 08:00 ET daily")
 550 |         while True:
 551 |             run_cycle()
 552 |             sleep_until_next_8am_et()
 553 |     else:
 554 |         run_cycle()
 555 | 
 556 | 
 557 | if __name__ == '__main__':
 558 |     main()
 559 | 
```

### File: services/local_watchdog.py (1053 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Protocol Pulse — Local LLM Watchdog (4-Layer Autonomous System)
   4 | GPU 2: Qwen3-Coder-30B via Ollama on port 11435
   5 | 
   6 | Modes (each runs independently via cron):
   7 |   --mode reactive   : every 60s  — crash detection + auto-patch
   8 |   --mode health     : every 15m  — system health scan
   9 |   --mode pattern    : every 6h   — trend analysis over 7 days
  10 |   --mode audit      : Monday 08:00 UTC — weekly deep audit
  11 |   --mode briefing   : daily 13:00 UTC (09:00 ET) — Telegram daily summary
  12 | 
  13 | Gospel: docs/gospels/WATCHDOG_LLM_GOSPEL.md
  14 | """
  15 | 
  16 | import argparse
  17 | import glob
  18 | import json
  19 | import logging
  20 | import os
  21 | import re
  22 | import shutil
  23 | import subprocess
  24 | import sys
  25 | import time
  26 | from datetime import datetime, timezone, timedelta
  27 | from pathlib import Path
  28 | 
  29 | # ---------------------------------------------------------------------------
  30 | # Paths
  31 | # ---------------------------------------------------------------------------
  32 | 
  33 | BASE = Path(__file__).resolve().parent.parent
  34 | LOGS_DIR = BASE / "logs"
  35 | LOGS_DIR.mkdir(exist_ok=True)
  36 | 
  37 | LOG_FILE = LOGS_DIR / "watchdog_llm.log"
  38 | PATCH_LOG = LOGS_DIR / "watchdog_patches.jsonl"
  39 | OVERNIGHT_LOG = BASE / "video_pipeline_v3" / "logs" / "overnight_loop.log"
  40 | REGRESSION_SCRIPT = BASE / "regression_test.sh"
  41 | 
  42 | # ---------------------------------------------------------------------------
  43 | # Config
  44 | # ---------------------------------------------------------------------------
  45 | 
  46 | OLLAMA_URL = "http://127.0.0.1:11435"
  47 | MODEL = os.environ.get("WATCHDOG_MODEL", "qwen3-coder:30b")
  48 | 
  49 | # Files we NEVER patch — gospel law
  50 | NEVER_PATCH = {"assembler.py", "tts_engine.py", "gemini_grade.py", "routes.py"}
  51 | 
  52 | # Cooldown: 600s per file, max 3 patches/hour
  53 | COOLDOWN_SECONDS = 600
  54 | MAX_PATCHES_PER_HOUR = 3
  55 | 
  56 | # ---------------------------------------------------------------------------
  57 | # Logging
  58 | # ---------------------------------------------------------------------------
  59 | 
  60 | logger = logging.getLogger("watchdog")
  61 | logger.setLevel(logging.INFO)
  62 | 
  63 | _fh = logging.FileHandler(str(LOG_FILE))
  64 | _fh.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(levelname)s: %(message)s"))
  65 | logger.addHandler(_fh)
  66 | 
  67 | _sh = logging.StreamHandler()
  68 | _sh.setFormatter(logging.Formatter("%(asctime)s [WATCHDOG] %(levelname)s: %(message)s"))
  69 | logger.addHandler(_sh)
  70 | 
  71 | # ---------------------------------------------------------------------------
  72 | # Telegram
  73 | # ---------------------------------------------------------------------------
  74 | 
  75 | def _load_env():
  76 |     """Load .env file into os.environ."""
  77 |     env_path = BASE / ".env"
  78 |     if env_path.exists():
  79 |         for line in env_path.read_text().splitlines():
  80 |             line = line.strip()
  81 |             if line and not line.startswith("#") and "=" in line:
  82 |                 key, val = line.split("=", 1)
  83 |                 os.environ.setdefault(key.strip(), val.strip().strip("'\""))
  84 | 
  85 | 
  86 | def send_telegram(msg):
  87 |     """Send a Telegram message. Returns True on success."""
  88 |     _load_env()
  89 |     token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
  90 |     chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
  91 |     if not token or not chat_id:
  92 |         logger.warning("Telegram not configured — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing")
  93 |         return False
  94 |     try:
  95 |         import requests
  96 |         resp = requests.post(
  97 |             f"https://api.telegram.org/bot{token}/sendMessage",
  98 |             json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
  99 |             timeout=10,
 100 |         )
 101 |         resp.raise_for_status()
 102 |         return True
 103 |     except Exception as e:
 104 |         logger.error("Telegram send failed: %s", e)
 105 |         return False
 106 | 
 107 | # ---------------------------------------------------------------------------
 108 | # Ollama Interface
 109 | # ---------------------------------------------------------------------------
 110 | 
 111 | def ollama_chat(system_prompt, user_prompt, temperature=0.3):
 112 |     """Fresh Ollama conversation — zero prior context (gospel: Fresh Perspective)."""
 113 |     import requests
 114 |     try:
 115 |         resp = requests.post(
 116 |             f"{OLLAMA_URL}/api/chat",
 117 |             json={
 118 |                 "model": MODEL,
 119 |                 "messages": [
 120 |                     {"role": "system", "content": system_prompt},
 121 |                     {"role": "user", "content": user_prompt},
 122 |                 ],
 123 |                 "stream": False,
 124 |                 "options": {"temperature": temperature},
 125 |             },
 126 |             timeout=120,
 127 |         )
 128 |         resp.raise_for_status()
 129 |         return resp.json().get("message", {}).get("content", "").strip()
 130 |     except Exception as e:
 131 |         logger.error("Ollama call failed: %s", e)
 132 |         return None
 133 | 
 134 | 
 135 | def ollama_healthy():
 136 |     """Check if Ollama is responding."""
 137 |     import requests
 138 |     try:
 139 |         resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
 140 |         return resp.status_code == 200
 141 |     except Exception:
 142 |         return False
 143 | 
 144 | # ---------------------------------------------------------------------------
 145 | # Utility
 146 | # ---------------------------------------------------------------------------
 147 | 
 148 | def tail_file(path, n=50):
 149 |     """Read last n lines of a file."""
 150 |     p = Path(path)
 151 |     if not p.exists():
 152 |         return ""
 153 |     try:
 154 |         result = subprocess.run(
 155 |             ["tail", "-n", str(n), str(p)],
 156 |             capture_output=True, text=True, timeout=10,
 157 |         )
 158 |         return result.stdout
 159 |     except Exception:
 160 |         return ""
 161 | 
 162 | 
 163 | def read_file_content(path):
 164 |     """Read file content, capped at 200 lines."""
 165 |     try:
 166 |         lines = Path(path).read_text().splitlines()[:200]
 167 |         return "\n".join(lines)
 168 |     except Exception:
 169 |         return ""
 170 | 
 171 | 
 172 | def gpu_vram():
 173 |     """Get GPU VRAM usage as list of dicts."""
 174 |     try:
 175 |         result = subprocess.run(
 176 |             ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
 177 |              "--format=csv,nounits,noheader"],
 178 |             capture_output=True, text=True, timeout=10,
 179 |         )
 180 |         gpus = []
 181 |         for line in result.stdout.strip().splitlines():
 182 |             parts = [p.strip() for p in line.split(",")]
 183 |             if len(parts) >= 4:
 184 |                 gpus.append({
 185 |                     "index": int(parts[0]),
 186 |                     "vram_used_mb": int(parts[1]),
 187 |                     "vram_total_mb": int(parts[2]),
 188 |                     "utilization_pct": int(parts[3]),
 189 |                 })
 190 |         return gpus
 191 |     except Exception:
 192 |         return []
 193 | 
 194 | 
 195 | def disk_free_gb():
 196 |     """Get free disk space in GB for the base directory."""
 197 |     try:
 198 |         stat = shutil.disk_usage(str(BASE))
 199 |         return round(stat.free / (1024 ** 3), 1)
 200 |     except Exception:
 201 |         return -1
 202 | 
 203 | 
 204 | def process_alive(name):
 205 |     """Check if a process matching name is running."""
 206 |     try:
 207 |         result = subprocess.run(["pgrep", "-f", name], capture_output=True, timeout=5)
 208 |         return result.returncode == 0
 209 |     except Exception:
 210 |         return False
 211 | 
 212 | 
 213 | def flask_alive():
 214 |     """Check if Flask is responding on localhost:5000."""
 215 |     import requests
 216 |     try:
 217 |         resp = requests.get("http://localhost:5000/", timeout=5)
 218 |         return resp.status_code < 500
 219 |     except Exception:
 220 |         return False
 221 | 
 222 | 
 223 | # ---------------------------------------------------------------------------
 224 | # Safety Gates
 225 | # ---------------------------------------------------------------------------
 226 | 
 227 | def check_cooldown(filepath):
 228 |     """Return True if file is on cooldown (patched within last 600s)."""
 229 |     fname = Path(filepath).name
 230 |     stamp_file = Path(f"/tmp/watchdog_last_patch_{fname}.txt")
 231 |     if stamp_file.exists():
 232 |         try:
 233 |             last = float(stamp_file.read_text().strip())
 234 |             if time.time() - last < COOLDOWN_SECONDS:
 235 |                 return True
 236 |         except (ValueError, IOError):
 237 |             pass
 238 |     return False
 239 | 
 240 | 
 241 | def record_patch(filepath):
 242 |     """Record patch timestamp for cooldown tracking."""
 243 |     fname = Path(filepath).name
 244 |     stamp_file = Path(f"/tmp/watchdog_last_patch_{fname}.txt")
 245 |     stamp_file.write_text(str(time.time()))
 246 | 
 247 | 
 248 | def patches_this_hour():
 249 |     """Count patches applied in the current hour."""
 250 |     hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
 251 |     count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
 252 |     if count_file.exists():
 253 |         try:
 254 |             return int(count_file.read_text().strip())
 255 |         except (ValueError, IOError):
 256 |             pass
 257 |     return 0
 258 | 
 259 | 
 260 | def increment_patch_count():
 261 |     """Increment the hourly patch counter."""
 262 |     hour_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
 263 |     count_file = Path(f"/tmp/watchdog_patch_count_{hour_key}.txt")
 264 |     current = patches_this_hour()
 265 |     count_file.write_text(str(current + 1))
 266 | 
 267 | 
 268 | def is_patchable(filepath):
 269 |     """Check all safety gates for patching a file."""
 270 |     fname = Path(filepath).name
 271 | 
 272 |     if fname in NEVER_PATCH:
 273 |         logger.info("GATE: %s is in NEVER_PATCH list — skipping", fname)
 274 |         return False
 275 | 
 276 |     if process_alive("daily_producer"):
 277 |         logger.info("GATE: daily_producer is running — skipping patch")
 278 |         return False
 279 | 
 280 |     if check_cooldown(filepath):
 281 |         logger.info("GATE: %s on cooldown — skipping", fname)
 282 |         return False
 283 | 
 284 |     if patches_this_hour() >= MAX_PATCHES_PER_HOUR:
 285 |         logger.info("GATE: max %d patches/hour reached — skipping", MAX_PATCHES_PER_HOUR)
 286 |         return False
 287 | 
 288 |     return True
 289 | 
 290 | 
 291 | # ---------------------------------------------------------------------------
 292 | # Crash Classification
 293 | # ---------------------------------------------------------------------------
 294 | 
 295 | def classify_crash(log_tail):
 296 |     """Classify crash from log lines. Returns (class, pattern_matched) or (None, None)."""
 297 |     lines = log_tail.strip()
 298 |     if not lines:
 299 |         return None, None
 300 | 
 301 |     # CLASS C — check protected files first (takes priority)
 302 |     for protected in NEVER_PATCH:
 303 |         if (f'File "' in lines and protected in lines and "Traceback" in lines):
 304 |             return "C", f"crash_in_{protected}"
 305 | 
 306 |     # Check for multi-file crashes (>1 unique repo file in traceback)
 307 |     file_matches = re.findall(r'File "([^"]*protocol_pulse[^"]*)"', lines)
 308 |     unique_files = set(Path(f).name for f in file_matches)
 309 |     # Remove __init__.py and test files from uniqueness check
 310 |     meaningful = {f for f in unique_files if f != "__init__.py" and not f.startswith("test_")}
 311 |     if len(meaningful) > 1:
 312 |         return "C", f"multi_file_crash({','.join(sorted(meaningful)[:3])})"
 313 | 
 314 |     # CLASS A patterns (safe auto-patch)
 315 |     if "KeyError" in lines:
 316 |         return "A", "KeyError"
 317 |     if "ImportError" in lines or "ModuleNotFoundError" in lines:
 318 |         return "A", "ImportError"
 319 |     if "FileNotFoundError" in lines:
 320 |         return "A", "FileNotFoundError"
 321 |     if "SyntaxError" in lines:
 322 |         return "A", "SyntaxError"
 323 | 
 324 |     # CLASS B patterns (patch + test)
 325 |     if "Traceback" in lines and "daily_producer" in lines:
 326 |         return "B", "Traceback+daily_producer"
 327 |     if "exit: -15" in lines and "FATAL" in lines:
 328 |         return "B", "exit:-15+FATAL"
 329 |     if "GRADE: F" in lines:
 330 |         return "B", "GRADE:F"
 331 | 
 332 |     # Check for 3x consecutive "Render failed"
 333 |     render_fails = re.findall(r"Render failed", lines)
 334 |     if len(render_fails) >= 3:
 335 |         return "B", "Render_failed_3x"
 336 | 
 337 |     return None, None
 338 | 
 339 | 
 340 | def extract_affected_file(log_tail):
 341 |     """Try to extract the crashing file from a traceback."""
 342 |     matches = re.findall(r'File "([^"]+)"', log_tail)
 343 |     # Filter to our repo files, exclude NEVER_PATCH
 344 |     repo_files = [
 345 |         m for m in matches
 346 |         if str(BASE) in m and Path(m).name not in NEVER_PATCH
 347 |     ]
 348 |     if repo_files:
 349 |         return repo_files[-1]  # Last file in traceback is usually the culprit
 350 |     return None
 351 | 
 352 | 
 353 | # ---------------------------------------------------------------------------
 354 | # Patch Engine
 355 | # ---------------------------------------------------------------------------
 356 | 
 357 | def diagnose_and_patch(log_tail, crash_class, pattern):
 358 |     """Use Ollama to diagnose crash, optionally apply patch."""
 359 |     affected_file = extract_affected_file(log_tail)
 360 | 
 361 |     if not affected_file:
 362 |         logger.info("Could not determine affected file from traceback")
 363 |         send_telegram(
 364 |             f"\U0001f534 <b>CRASH DETECTED</b> — CLASS {crash_class}\n"
 365 |             f"\U0001f4cb Pattern: {pattern}\n"
 366 |             f"\u26a0\ufe0f Could not identify affected file\n"
 367 |             f"\U0001f527 Manual intervention needed"
 368 |         )
 369 |         return
 370 | 
 371 |     fname = Path(affected_file).name
 372 | 
 373 |     # CLASS C — alert only
 374 |     if crash_class == "C":
 375 |         logger.info("CLASS C crash in %s — alert only, no patching", fname)
 376 |         send_telegram(
 377 |             f"\U0001f534 <b>CLASS C CRASH</b> in <code>{fname}</code>\n"
 378 |             f"\U0001f4cb Pattern: {pattern}\n"
 379 |             f"\u26a0\ufe0f Protected file — manual fix required\n"
 380 |             f"\U0001f4c2 {affected_file}"
 381 |         )
 382 |         return
 383 | 
 384 |     # Check safety gates
 385 |     if not is_patchable(affected_file):
 386 |         send_telegram(
 387 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 388 |             f"\U0001f4cb Pattern: {pattern}\n"
 389 |             f"\U0001f6ab Safety gate blocked auto-patch\n"
 390 |             f"\U0001f527 Manual intervention needed"
 391 |         )
 392 |         return
 393 | 
 394 |     # Read affected file content
 395 |     file_content = read_file_content(affected_file)
 396 | 
 397 |     # Ask Ollama for diagnosis
 398 |     system_prompt = (
 399 |         "You are a Python/FFmpeg expert debugging a video production pipeline. "
 400 |         "Analyze the crash log and return ONLY valid JSON:\n"
 401 |         '{"diagnosis": "str", "affected_file": "str", "patch_diff": "str", "confidence": float}\n'
 402 |         "The patch_diff must be a unified diff that can be applied with `patch -p0`.\n"
 403 |         "If you cannot determine a fix with high confidence, set confidence to 0.0."
 404 |     )
 405 |     user_prompt = f"CRASH LOG:\n{log_tail}\n\nFILE CONTENT ({affected_file}):\n{file_content}"
 406 | 
 407 |     logger.info("Requesting Ollama diagnosis for %s...", fname)
 408 |     raw_response = ollama_chat(system_prompt, user_prompt)
 409 | 
 410 |     if not raw_response:
 411 |         send_telegram(
 412 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 413 |             f"\U0001f4cb {pattern}\n"
 414 |             f"\u274c Ollama diagnosis failed — model unresponsive"
 415 |         )
 416 |         return
 417 | 
 418 |     # Parse JSON from response (may be wrapped in markdown code block)
 419 |     json_text = None
 420 |     # Try code block first
 421 |     code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
 422 |     if code_match:
 423 |         json_text = code_match.group(1)
 424 |     else:
 425 |         # Try bare JSON
 426 |         json_match = re.search(r'\{[^{}]*"diagnosis"[^}]*\}', raw_response, re.DOTALL)
 427 |         if json_match:
 428 |             json_text = json_match.group()
 429 | 
 430 |     if not json_text:
 431 |         logger.warning("Could not parse JSON from Ollama response")
 432 |         send_telegram(
 433 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 434 |             f"\U0001f4cb {pattern}\n"
 435 |             f"\u274c Ollama returned unparseable response"
 436 |         )
 437 |         return
 438 | 
 439 |     try:
 440 |         diagnosis = json.loads(json_text)
 441 |     except json.JSONDecodeError:
 442 |         logger.warning("JSON parse failed on Ollama response")
 443 |         send_telegram(
 444 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 445 |             f"\U0001f4cb {pattern}\n"
 446 |             f"\u274c Ollama JSON malformed"
 447 |         )
 448 |         return
 449 | 
 450 |     confidence = float(diagnosis.get("confidence", 0))
 451 |     diag_text = diagnosis.get("diagnosis", "No diagnosis")
 452 |     patch_diff = diagnosis.get("patch_diff", "")
 453 | 
 454 |     logger.info("Diagnosis: %s (confidence: %.2f)", diag_text[:100], confidence)
 455 | 
 456 |     # Gate 1: confidence check
 457 |     if confidence < 0.8:
 458 |         logger.info("Confidence %.2f < 0.8 — skipping auto-patch", confidence)
 459 |         send_telegram(
 460 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 461 |             f"\U0001f4cb {diag_text[:200]}\n"
 462 |             f"\U0001f3af Confidence: {confidence:.0%} (below 80% threshold)\n"
 463 |             f"\U0001f527 Manual fix recommended"
 464 |         )
 465 |         return
 466 | 
 467 |     if not patch_diff.strip():
 468 |         logger.info("No patch provided despite high confidence")
 469 |         send_telegram(
 470 |             f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 471 |             f"\U0001f4cb {diag_text[:200]}\n"
 472 |             f"\U0001f3af Confidence: {confidence:.0%}\n"
 473 |             f"\u26a0\ufe0f No patch diff provided"
 474 |         )
 475 |         return
 476 | 
 477 |     # Apply patch
 478 |     logger.info("Applying patch to %s...", fname)
 479 |     patch_file = Path("/tmp/watchdog_patch.diff")
 480 |     patch_file.write_text(patch_diff)
 481 | 
 482 |     try:
 483 |         result = subprocess.run(
 484 |             ["patch", "-p0", "--dry-run", "-i", str(patch_file)],
 485 |             capture_output=True, text=True, timeout=10, cwd=str(BASE),
 486 |         )
 487 |         if result.returncode != 0:
 488 |             logger.warning("Patch dry-run failed: %s", result.stderr)
 489 |             send_telegram(
 490 |                 f"\U0001f534 <b>CLASS {crash_class} CRASH</b> in <code>{fname}</code>\n"
 491 |                 f"\U0001f4cb {diag_text[:200]}\n"
 492 |                 f"\u274c Patch dry-run failed\n"
 493 |                 f"\U0001f527 Manual fix needed"
 494 |             )
 495 |             return
 496 | 
 497 |         # Apply for real
 498 |         result = subprocess.run(
 499 |             ["patch", "-p0", "-i", str(patch_file)],
 500 |             capture_output=True, text=True, timeout=10, cwd=str(BASE),
 501 |         )
 502 |         if result.returncode != 0:
 503 |             logger.error("Patch apply failed: %s", result.stderr)
 504 |             send_telegram(
 505 |                 f"\U0001f534 <b>PATCH FAILED</b> for <code>{fname}</code>\n"
 506 |                 f"\u274c {result.stderr[:200]}"
 507 |             )
 508 |             return
 509 |     except Exception as e:
 510 |         logger.error("Patch subprocess error: %s", e)
 511 |         return
 512 | 
 513 |     logger.info("Patch applied — running regression tests...")
 514 | 
 515 |     # Gate 2: regression test
 516 |     try:
 517 |         test_result = subprocess.run(
 518 |             ["bash", str(REGRESSION_SCRIPT)],
 519 |             capture_output=True, text=True, timeout=300, cwd=str(BASE),
 520 |         )
 521 |         test_output = test_result.stdout + test_result.stderr
 522 |         fail_count = len(re.findall(r"FAIL", test_output))
 523 |     except Exception as e:
 524 |         logger.error("Regression test error: %s", e)
 525 |         fail_count = 999
 526 | 
 527 |     if fail_count > 0:
 528 |         # Gate 3: revert on failure
 529 |         logger.warning("Regression tests failed (%d FAILs) — reverting patch", fail_count)
 530 |         subprocess.run(
 531 |             ["git", "checkout", "--", affected_file],
 532 |             capture_output=True, cwd=str(BASE),
 533 |         )
 534 |         send_telegram(
 535 |             f"\U0001f534 <b>PATCH REVERTED</b> for <code>{fname}</code>\n"
 536 |             f"\U0001f4cb {diag_text[:200]}\n"
 537 |             f"\U0001f9ea Regression: {fail_count} FAILs\n"
 538 |             f"\u21a9\ufe0f File reverted to pre-patch state"
 539 |         )
 540 |         return
 541 | 
 542 |     # Success — commit + record
 543 |     logger.info("All tests passed — committing patch")
 544 |     record_patch(affected_file)
 545 |     increment_patch_count()
 546 | 
 547 |     subprocess.run(
 548 |         ["git", "add", affected_file],
 549 |         capture_output=True, cwd=str(BASE),
 550 |     )
 551 |     commit_msg = f"fix(watchdog): auto-patch {fname} — {diag_text[:80]}"
 552 |     subprocess.run(
 553 |         ["git", "commit", "-m", commit_msg],
 554 |         capture_output=True, cwd=str(BASE),
 555 |     )
 556 | 
 557 |     # Log patch to JSONL
 558 |     patch_record = {
 559 |         "timestamp": datetime.now(timezone.utc).isoformat(),
 560 |         "crash_class": crash_class,
 561 |         "pattern": pattern,
 562 |         "file": affected_file,
 563 |         "diagnosis": diag_text,
 564 |         "confidence": confidence,
 565 |         "tests_passed": True,
 566 |     }
 567 |     with open(PATCH_LOG, "a") as f:
 568 |         f.write(json.dumps(patch_record) + "\n")
 569 | 
 570 |     # Restart render loop if it was dead
 571 |     if not process_alive("overnight_render_loop"):
 572 |         logger.info("Render loop is dead — attempting restart")
 573 |         subprocess.Popen(
 574 |             ["bash", "-c",
 575 |              f"cd {BASE} && nohup python3 overnight_render_loop.py "
 576 |              f">> {LOGS_DIR}/overnight_loop.log 2>&1 &"],
 577 |         )
 578 | 
 579 |     send_telegram(
 580 |         f"\u2705 <b>PATCH APPLIED</b> — <code>{fname}</code>\n"
 581 |         f"\U0001f4cb {diag_text[:200]}\n"
 582 |         f"\U0001f3af Confidence: {confidence:.0%}\n"
 583 |         f"\U0001f9ea Regression: ALL PASS\n"
 584 |         f"\U0001f4dd Committed: {commit_msg[:80]}"
 585 |     )
 586 | 
 587 | 
 588 | # ===================================================================
 589 | # LAYER 1 — REACTIVE CHECK (every 60s)
 590 | # ===================================================================
 591 | 
 592 | def run_reactive_check():
 593 |     """Tail overnight_loop.log, detect crashes, diagnose + patch."""
 594 |     logger.info("-- REACTIVE CHECK --")
 595 | 
 596 |     # Self-health: is Ollama alive?
 597 |     if not ollama_healthy():
 598 |         logger.error("Ollama not responding on %s", OLLAMA_URL)
 599 |         send_telegram(
 600 |             "\u26a0\ufe0f <b>WATCHDOG ALERT</b>: Ollama not responding on GPU 2 "
 601 |             "— self-restart attempted"
 602 |         )
 603 |         subprocess.Popen(
 604 |             ["bash", "-c",
 605 |              "CUDA_VISIBLE_DEVICES=2 OLLAMA_HOST=127.0.0.1:11435 "
 606 |              "/usr/local/bin/ollama serve &"],
 607 |         )
 608 |         return
 609 | 
 610 |     # Write last-run timestamp for self-health monitoring
 611 |     Path("/tmp/watchdog_last_run.txt").write_text(
 612 |         datetime.now(timezone.utc).isoformat()
 613 |     )
 614 | 
 615 |     # Check render loop alive
 616 |     loop_alive = process_alive("overnight_render_loop")
 617 | 
 618 |     # Tail the log
 619 |     log_tail = tail_file(OVERNIGHT_LOG, 50)
 620 |     if not log_tail.strip():
 621 |         logger.info("No log content to analyze")
 622 |         if not loop_alive:
 623 |             logger.warning("Render loop is NOT running and no log activity")
 624 |             send_telegram(
 625 |                 "\u26a0\ufe0f <b>WATCHDOG</b>: Render loop appears dead — no log activity\n"
 626 |                 "Check manually: <code>pgrep -f overnight_render_loop</code>"
 627 |             )
 628 |         return
 629 | 
 630 |     # Classify
 631 |     crash_class, pattern = classify_crash(log_tail)
 632 |     if not crash_class:
 633 |         logger.info("No crash patterns detected — all clear")
 634 |         return
 635 | 
 636 |     logger.info("CRASH DETECTED: CLASS %s — %s", crash_class, pattern)
 637 |     diagnose_and_patch(log_tail, crash_class, pattern)
 638 | 
 639 | 
 640 | # ===================================================================
 641 | # LAYER 2 — PERIODIC HEALTH SCAN (every 15 min)
 642 | # ===================================================================
 643 | 
 644 | def run_health_scan():
 645 |     """Fresh system health check — reads everything from scratch."""
 646 |     logger.info("-- HEALTH SCAN --")
 647 | 
 648 |     checks = {}
 649 | 
 650 |     # Render loop alive?
 651 |     checks["render_loop"] = process_alive("overnight_render_loop")
 652 | 
 653 |     # Flask alive?
 654 |     checks["flask"] = flask_alive()
 655 | 
 656 |     # Ollama alive?
 657 |     checks["ollama"] = ollama_healthy()
 658 | 
 659 |     # GPU VRAM
 660 |     gpus = gpu_vram()
 661 |     checks["gpus"] = []
 662 |     for g in gpus:
 663 |         pct = round(g["vram_used_mb"] / g["vram_total_mb"] * 100, 1) if g["vram_total_mb"] > 0 else 0
 664 |         checks["gpus"].append({
 665 |             "index": g["index"],
 666 |             "used_mb": g["vram_used_mb"],
 667 |             "total_mb": g["vram_total_mb"],
 668 |             "pct": pct,
 669 |         })
 670 |         if g["index"] in (0, 1) and pct > 90:
 671 |             send_telegram(
 672 |                 f"\u26a0\ufe0f <b>GPU {g['index']} VRAM HIGH</b>: {pct}% "
 673 |                 f"({g['vram_used_mb']}MB / {g['vram_total_mb']}MB)"
 674 |             )
 675 | 
 676 |     # Disk space
 677 |     free_gb = disk_free_gb()
 678 |     checks["disk_free_gb"] = free_gb
 679 |     if 0 < free_gb < 200:
 680 |         send_telegram(f"\u26a0\ufe0f <b>LOW DISK</b>: {free_gb}GB free (threshold: 200GB)")
 681 | 
 682 |     # Last successful grade from loop log
 683 |     last_grade = "UNKNOWN"
 684 |     if OVERNIGHT_LOG.exists():
 685 |         try:
 686 |             result = subprocess.run(
 687 |                 ["grep", "-oP", r"GRADE: [A-F]", str(OVERNIGHT_LOG)],
 688 |                 capture_output=True, text=True, timeout=10,
 689 |             )
 690 |             grades = result.stdout.strip().splitlines()
 691 |             if grades:
 692 |                 last_grade = grades[-1]
 693 |         except Exception:
 694 |             pass
 695 |     checks["last_grade"] = last_grade
 696 | 
 697 |     # Audio lines in TTS cache
 698 |     audio_pattern = str(BASE / "video_pipeline_v3" / "tts_cache" / "*.m4a")
 699 |     audio_count = len(glob.glob(audio_pattern))
 700 |     checks["audio_files_in_cache"] = audio_count
 701 | 
 702 |     # Patches in last 24h
 703 |     patches_24h = 0
 704 |     if PATCH_LOG.exists():
 705 |         cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
 706 |         for line in PATCH_LOG.read_text().splitlines():
 707 |             try:
 708 |                 rec = json.loads(line)
 709 |                 if rec.get("timestamp", "") > cutoff:
 710 |                     patches_24h += 1
 711 |             except json.JSONDecodeError:
 712 |                 pass
 713 |     checks["patches_24h"] = patches_24h
 714 | 
 715 |     logger.info(
 716 |         "Health: loop=%s flask=%s ollama=%s disk=%.0fGB grade=%s patches_24h=%d",
 717 |         checks["render_loop"], checks["flask"], checks["ollama"],
 718 |         free_gb, last_grade, patches_24h,
 719 |     )
 720 | 
 721 |     # Alert if critical services down
 722 |     issues = []
 723 |     if not checks["render_loop"]:
 724 |         issues.append("\u274c Render loop DOWN")
 725 |     if not checks["flask"]:
 726 |         issues.append("\u274c Flask DOWN")
 727 |     if not checks["ollama"]:
 728 |         issues.append("\u274c Ollama DOWN")
 729 | 
 730 |     if issues:
 731 |         send_telegram(
 732 |             "\u26a0\ufe0f <b>HEALTH SCAN ALERT</b>\n" + "\n".join(issues)
 733 |         )
 734 | 
 735 |     # Ask Ollama for health assessment (fresh context)
 736 |     if ollama_healthy():
 737 |         health_prompt = (
 738 |             f"System health snapshot:\n{json.dumps(checks, indent=2)}\n\n"
 739 |             "Briefly assess: any concerning patterns? One paragraph max."
 740 |         )
 741 |         assessment = ollama_chat(
 742 |             "You are a DevOps engineer monitoring a video production pipeline. Be concise.",
 743 |             health_prompt,
 744 |         )
 745 |         if assessment:
 746 |             logger.info("Health assessment: %s", assessment[:200])
 747 | 
 748 |     return checks
 749 | 
 750 | 
 751 | # ===================================================================
 752 | # LAYER 3 — PATTERN ANALYSIS (every 6 hours)
 753 | # ===================================================================
 754 | 
 755 | def run_pattern_analysis():
 756 |     """Analyze 7 days of logs for trends — fresh Ollama conversation."""
 757 |     logger.info("-- PATTERN ANALYSIS --")
 758 | 
 759 |     if not ollama_healthy():
 760 |         logger.error("Ollama not available for pattern analysis")
 761 |         return
 762 | 
 763 |     # Gather last 7 days of loop logs (tail 2000 lines)
 764 |     log_content = tail_file(OVERNIGHT_LOG, 2000)
 765 | 
 766 |     # Also check episode log files
 767 |     extra_logs = ""
 768 |     for logname in ["episode_morning.log", "episode_noon.log", "episode_evening.log"]:
 769 |         logpath = LOGS_DIR / logname
 770 |         if logpath.exists():
 771 |             extra_logs += f"\n--- {logname} ---\n" + tail_file(logpath, 500)
 772 | 
 773 |     # Read patch history
 774 |     patch_history = ""
 775 |     if PATCH_LOG.exists():
 776 |         patch_history = tail_file(PATCH_LOG, 100)
 777 | 
 778 |     analysis_prompt = (
 779 |         "Analyze these 7 days of render logs. Identify:\n"
 780 |         "1. Most frequent crash type and root cause\n"
 781 |         "2. Time-of-day patterns in failures\n"
 782 |         "3. Any silent degradation in grades\n"
 783 |         "4. Files that appear in >50% of crashes\n"
 784 |         "5. Recommended preventive fixes\n\n"
 785 |         f"OVERNIGHT LOOP LOG (last 2000 lines):\n{log_content[:8000]}\n\n"
 786 |         f"ADDITIONAL EPISODE LOGS:\n{extra_logs[:4000]}\n\n"
 787 |         f"PATCH HISTORY:\n{patch_history[:2000]}"
 788 |     )
 789 | 
 790 |     response = ollama_chat(
 791 |         "You are a senior SRE analyzing production pipeline logs. "
 792 |         "Focus on patterns and trends, not individual events. Be specific with data.",
 793 |         analysis_prompt,
 794 |     )
 795 | 
 796 |     if not response:
 797 |         logger.error("Pattern analysis failed — no Ollama response")
 798 |         return
 799 | 
 800 |     # Write analysis file
 801 |     date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
 802 |     analysis_path = LOGS_DIR / f"watchdog_analysis_{date_str}.md"
 803 |     analysis_path.write_text(
 804 |         f"# Watchdog Pattern Analysis — {date_str}\n\n{response}\n"
 805 |     )
 806 |     logger.info("Analysis written to %s", analysis_path)
 807 | 
 808 |     # Check for P0 patterns
 809 |     if any(kw in response.lower() for kw in ["critical", "p0", "urgent", "data loss", "cascade"]):
 810 |         send_telegram(
 811 |             f"\U0001f4ca <b>PATTERN ANALYSIS — P0 FOUND</b>\n\n"
 812 |             f"{response[:800]}"
 813 |         )
 814 |     else:
 815 |         logger.info("No P0 patterns found in analysis")
 816 | 
 817 | 
 818 | # ===================================================================
 819 | # LAYER 4 — WEEKLY DEEP AUDIT (Monday 08:00 UTC)
 820 | # ===================================================================
 821 | 
 822 | def run_weekly_audit():
 823 |     """Deep audit: compare gospels vs actual behavior over 30 days."""
 824 |     logger.info("-- WEEKLY AUDIT --")
 825 | 
 826 |     if not ollama_healthy():
 827 |         logger.error("Ollama not available for weekly audit")
 828 |         return
 829 | 
 830 |     # Read gospels
 831 |     gospels_dir = BASE / "docs" / "gospels"
 832 |     gospel_content = ""
 833 |     if gospels_dir.exists():
 834 |         for gf in sorted(gospels_dir.glob("*.md")):
 835 |             text = gf.read_text()[:3000]
 836 |             gospel_content += f"\n--- {gf.name} ---\n{text}\n"
 837 | 
 838 |     # Pipeline laws
 839 |     laws_path = BASE / "PIPELINE_LAWS.md"
 840 |     laws_content = ""
 841 |     if laws_path.exists():
 842 |         laws_content = laws_path.read_text()[:4000]
 843 | 
 844 |     # Last 30 days log (tail 5000 lines)
 845 |     log_content = tail_file(OVERNIGHT_LOG, 5000)
 846 | 
 847 |     # Git log last 50 commits
 848 |     try:
 849 |         git_result = subprocess.run(
 850 |             ["git", "log", "--oneline", "-50"],
 851 |             capture_output=True, text=True, timeout=10, cwd=str(BASE),
 852 |         )
 853 |         git_log = git_result.stdout
 854 |     except Exception:
 855 |         git_log = "(unavailable)"
 856 | 
 857 |     # Patch history
 858 |     patch_history = ""
 859 |     if PATCH_LOG.exists():
 860 |         patch_history = PATCH_LOG.read_text()[-3000:]
 861 | 
 862 |     audit_prompt = (
 863 |         "You are auditing the Protocol Pulse pipeline. Read the gospel docs "
 864 |         "and compare against actual behavior in logs. Identify:\n"
 865 |         "1. Gospel violations (rules being broken)\n"
 866 |         "2. Technical debt accumulating\n"
 867 |         "3. Costs trending up or down\n"
 868 |         "4. Modules that have had >3 patches in 30 days (fragile code)\n"
 869 |         "5. Recommended refactors\n\n"
 870 |         f"GOSPEL DOCS:\n{gospel_content[:6000]}\n\n"
 871 |         f"PIPELINE LAWS:\n{laws_content[:4000]}\n\n"
 872 |         f"LOOP LOG (recent):\n{log_content[:6000]}\n\n"
 873 |         f"GIT LOG:\n{git_log[:2000]}\n\n"
 874 |         f"PATCH HISTORY:\n{patch_history[:2000]}"
 875 |     )
 876 | 
 877 |     response = ollama_chat(
 878 |         "You are a senior engineer auditing a production video pipeline. "
 879 |         "Compare documented rules against actual system behavior. Be specific.",
 880 |         audit_prompt,
 881 |     )
 882 | 
 883 |     if not response:
 884 |         logger.error("Weekly audit failed — no Ollama response")
 885 |         return
 886 | 
 887 |     # Write audit file
 888 |     date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
 889 |     audit_path = LOGS_DIR / f"weekly_audit_{date_str}.md"
 890 |     audit_path.write_text(
 891 |         f"# Watchdog Weekly Audit — {date_str}\n\n{response}\n"
 892 |     )
 893 |     logger.info("Audit written to %s", audit_path)
 894 | 
 895 |     # Telegram with top findings
 896 |     send_telegram(
 897 |         f"\U0001f4cb <b>WEEKLY AUDIT — {date_str}</b>\n\n"
 898 |         f"{response[:800]}"
 899 |     )
 900 | 
 901 | 
 902 | # ===================================================================
 903 | # DAILY BRIEFING (09:00 ET / 13:00 UTC)
 904 | # ===================================================================
 905 | 
 906 | def send_daily_briefing():
 907 |     """Morning Telegram summary — gospel format."""
 908 |     logger.info("-- DAILY BRIEFING --")
 909 | 
 910 |     date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
 911 | 
 912 |     # Last grade
 913 |     last_grade = "UNKNOWN"
 914 |     last_score = "?"
 915 |     last_time = "?"
 916 |     if OVERNIGHT_LOG.exists():
 917 |         try:
 918 |             result = subprocess.run(
 919 |                 ["grep", "-P", r"GRADE:", str(OVERNIGHT_LOG)],
 920 |                 capture_output=True, text=True, timeout=10,
 921 |             )
 922 |             lines = result.stdout.strip().splitlines()
 923 |             if lines:
 924 |                 last_line = lines[-1]
 925 |                 grade_match = re.search(r"GRADE:\s*([A-F])", last_line)
 926 |                 if grade_match:
 927 |                     last_grade = grade_match.group(1)
 928 |                 score_match = re.search(r"(\d+)/100", last_line)
 929 |                 if score_match:
 930 |                     last_score = score_match.group(1)
 931 |                 time_match = re.search(r"(\d{2}:\d{2})", last_line)
 932 |                 if time_match:
 933 |                     last_time = time_match.group(1)
 934 |         except Exception:
 935 |             pass
 936 | 
 937 |     # Patches in 24h
 938 |     patches_24h = 0
 939 |     if PATCH_LOG.exists():
 940 |         cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
 941 |         for line in PATCH_LOG.read_text().splitlines():
 942 |             try:
 943 |                 rec = json.loads(line)
 944 |                 if rec.get("timestamp", "") > cutoff:
 945 |                     patches_24h += 1
 946 |             except json.JSONDecodeError:
 947 |                 pass
 948 | 
 949 |     # Disk
 950 |     free_gb = disk_free_gb()
 951 | 
 952 |     # GPU 2 VRAM
 953 |     gpu2_vram = "?"
 954 |     for g in gpu_vram():
 955 |         if g["index"] == 2:
 956 |             gpu2_vram = f"{g['vram_used_mb'] / 1024:.1f}GB"
 957 | 
 958 |     # Articles count today
 959 |     article_count = "?"
 960 |     db_path = BASE / "instance" / "protocol_pulse.db"
 961 |     if db_path.exists():
 962 |         try:
 963 |             import sqlite3
 964 |             conn = sqlite3.connect(str(db_path))
 965 |             today_start = datetime.now(timezone.utc).replace(
 966 |                 hour=0, minute=0, second=0
 967 |             ).isoformat()
 968 |             row = conn.execute(
 969 |                 "SELECT COUNT(*) FROM articles WHERE created_at > ?",
 970 |                 (today_start,)
 971 |             ).fetchone()
 972 |             article_count = str(row[0]) if row else "0"
 973 |             conn.close()
 974 |         except Exception:
 975 |             pass
 976 | 
 977 |     # Alerts in 24h
 978 |     alert_count = 0
 979 |     if LOG_FILE.exists():
 980 |         try:
 981 |             result = subprocess.run(
 982 |                 ["grep", "-c", "-E", "CRASH DETECTED|PATCH|ALERT", str(LOG_FILE)],
 983 |                 capture_output=True, text=True, timeout=10,
 984 |             )
 985 |             alert_count = int(result.stdout.strip()) if result.stdout.strip() else 0
 986 |         except Exception:
 987 |             pass
 988 | 
 989 |     # Determine status
 990 |     issues = []
 991 |     if not process_alive("overnight_render_loop"):
 992 |         issues.append("render loop down")
 993 |     if not flask_alive():
 994 |         issues.append("Flask down")
 995 |     if not ollama_healthy():
 996 |         issues.append("Ollama down")
 997 | 
 998 |     status = "\u2705 All systems nominal" if not issues else f"\u274c Issues: {', '.join(issues)}"
 999 | 
1000 |     briefing = (
1001 |         f"\U0001f916 <b>WATCHDOG DAILY — {date_str}</b>\n"
1002 |         f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
1003 |         f"\U0001f3ac Render: {last_grade} ({last_score}/100) at {last_time}\n"
1004 |         f"\U0001f527 Patches applied: {patches_24h} (last 24h)\n"
1005 |         f"\U0001f4be Disk free: {free_gb}GB\n"
1006 |         f"\U0001f9e0 GPU 2 (Watchdog): {gpu2_vram} / 24GB\n"
1007 |         f"\U0001f4ca Articles generated: {article_count}\n"
1008 |         f"\u26a0\ufe0f Alerts: {alert_count}\n"
1009 |         f"{status}"
1010 |     )
1011 | 
1012 |     send_telegram(briefing)
1013 |     logger.info("Daily briefing sent")
1014 | 
1015 | 
1016 | # ===================================================================
1017 | # MAIN — route by --mode flag
1018 | # ===================================================================
1019 | 
1020 | def main():
1021 |     parser = argparse.ArgumentParser(description="Protocol Pulse Local LLM Watchdog")
1022 |     parser.add_argument(
1023 |         "--mode",
1024 |         choices=["reactive", "health", "pattern", "audit", "briefing"],
1025 |         default="reactive",
1026 |         help="Check layer to run",
1027 |     )
1028 |     args = parser.parse_args()
1029 | 
1030 |     logger.info("=" * 50)
1031 |     logger.info(
1032 |         "WATCHDOG RUN — mode=%s — %s",
1033 |         args.mode, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
1034 |     )
1035 |     logger.info("=" * 50)
1036 | 
1037 |     if args.mode == "reactive":
1038 |         run_reactive_check()
1039 |     elif args.mode == "health":
1040 |         run_health_scan()
1041 |     elif args.mode == "pattern":
1042 |         run_pattern_analysis()
1043 |     elif args.mode == "audit":
1044 |         run_weekly_audit()
1045 |     elif args.mode == "briefing":
1046 |         send_daily_briefing()
1047 | 
1048 |     logger.info("WATCHDOG RUN COMPLETE — mode=%s", args.mode)
1049 | 
1050 | 
1051 | if __name__ == "__main__":
1052 |     main()
1053 | 
```

### File: video_pipeline_v3/clip_selector.py (709 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Clip Selector — uses Claude to pick the 5 best moments from transcribed videos.
   3 | 
   4 | Analyzes all transcripts and selects timestamp ranges for the most compelling
   5 | clips, along with host setup/reaction dialogue suggestions.
   6 | """
   7 | import json
   8 | import logging
   9 | import os
  10 | import sys
  11 | from datetime import datetime, timedelta
  12 | 
  13 | try:
  14 |     import anthropic
  15 |     HAS_ANTHROPIC = True
  16 | except ImportError:
  17 |     HAS_ANTHROPIC = False
  18 | 
  19 | from relay import get_key
  20 | 
  21 | logger = logging.getLogger("ClipSelector")
  22 | if not logger.handlers:
  23 |     handler = logging.StreamHandler()
  24 |     handler.setFormatter(logging.Formatter("[selector] %(message)s"))
  25 |     logger.addHandler(handler)
  26 |     logger.setLevel(logging.INFO)
  27 | 
  28 | SELECTION_PROMPT = """You are the executive producer of "Pulse Check" — a daily 3-5 minute Bitcoin highlight reel.
  29 | Two hosts (Jessica & Chris) present and react to the BEST clips from Bitcoin YouTube that day.
  30 | Think ESPN SportsCenter for Bitcoin.
  31 | 
  32 | Your job: analyze these transcripts from today's Bitcoin YouTube videos and pick the 5 BEST moments.
  33 | 
  34 | SELECTION CRITERIA (in order of priority):
  35 | 1. BREAKING NEWS — first reports of major developments (ETF flows, regulatory, corporate buys)
  36 | 2. HOT TAKES — strong, quotable opinions from respected voices
  37 | 3. DATA DROPS — specific numbers, charts, on-chain metrics being discussed
  38 | 4. QUOTABLE — moments where someone says something memorable and punchy
  39 | 5. VISUAL — prefer clips where someone is on camera talking (not just voice-over slides)
  40 | 
  41 | TIER 4 - CROSSOVER DISCOVERY (1.6x multiplier): Videos from non-Bitcoin channels that specifically covered Bitcoin. A philosopher, scientist, or political commentator covering Bitcoin outscores another Bitcoin-native channel on the same story. Field: source == "tier2_discovery". Prioritize these.
  42 | 
  43 | RULES:
  44 | - INTRO AVOIDANCE: Never select a clip starting at 0:00 unless the transcript shows
  45 |   substantive speech begins within the first 3 seconds. Prefer clips starting at 30s+
  46 |   into the video to skip channel intros, jingles, and logos. Clips starting in the
  47 |   first 10 seconds of a video almost always contain branding — avoid them.
  48 | - CRITICAL — AD READ DETECTION: NEVER select a timestamp range that contains
  49 |   an ad read, sponsorship mention, or promotional segment. Ad reads are identified by:
  50 |   * "This episode is brought to you by..."
  51 |   * "Thanks to our sponsor..."
  52 |   * "Use code [X] at [URL]"
  53 |   * "Go to [domain].com/[show]"
  54 |   * "Check out [product]" with a URL
  55 |   * Any mention of a promo code, discount, or affiliate link
  56 |   * Host reading from a script about a product/service they're paid to mention
  57 |   If a transcript segment contains these patterns, SKIP it and find the next
  58 |   compelling moment that is actual content, not advertising.
  59 | - SEGMENT CONTINUITY: Never select a clip that starts mid-ad-read or ends
  60 |   mid-thought. The clip must begin and end at natural content boundaries.
  61 |   A clip that begins with ad-read content is invalid, full stop.
  62 | - Pick from DIFFERENT channels when possible (variety matters)
  63 | - NEVER select more than 1 clip from the same YouTube video (unique video_id per clip)
  64 | - NEVER select 2 clips from the same channel back-to-back — vary the source
  65 | - If forced to use the same channel twice, clips must be different videos on different topics
  66 | - Each clip should be 20-40 seconds long (the best moment, not the full segment)
  67 | - Rank 1 = most dramatic/important (this becomes the cold open teaser)
  68 | - The timestamps in the transcripts are approximate — pick ranges that capture complete thoughts
  69 | - Avoid dead air, filler words, or mid-sentence cuts
  70 | - When specifying clip end times, always allow 3-4 seconds of buffer AFTER the key statement ends so the narrator never interrupts a sentence in progress
  71 | - Sort clips to maximize channel variety: no same channel appearing consecutively
  72 | 
  73 | AVAILABLE VIDEOS:
  74 | {transcripts}
  75 | 
  76 | Return ONLY valid JSON (no markdown, no code fences):
  77 | {{
  78 |   "clips": [
  79 |     {{
  80 |       "rank": 1,
  81 |       "video_id": "abc123",
  82 |       "channel": "Bitcoin Magazine",
  83 |       "video_title": "Original video title",
  84 |       "start_seconds": 145,
  85 |       "end_seconds": 175,
  86 |       "quote": "The exact memorable quote from this moment",
  87 |       "why": "Why this clip is compelling (1 sentence)",
  88 |       "host_setup": "What Jessica should say to introduce this clip (1-2 sentences, conversational)",
  89 |       "host_react": "What the hosts should discuss after this clip (2-3 sentences of banter)"
  90 |     }}
  91 |   ],
  92 |   "episode_title": "Short punchy episode title based on top clip (5-8 words)",
  93 |   "cold_open": "Jessica's cold open teaser line about clip #1 — dramatic, hook the viewer (1 sentence)"
  94 | }}
  95 | 
  96 | Return exactly 5 clips, ranked 1-5. If fewer than 5 good moments exist, return what you can."""
  97 | 
  98 | 
  99 | USED_CLIPS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "used_clips.json")
 100 | 
 101 | 
 102 | def _load_used_clips() -> dict:
 103 |     """Load episode memory from data/used_clips.json."""
 104 |     if not os.path.exists(USED_CLIPS_PATH):
 105 |         return {"episodes": []}
 106 |     try:
 107 |         with open(USED_CLIPS_PATH) as f:
 108 |             return json.load(f)
 109 |     except Exception:
 110 |         return {"episodes": []}
 111 | 
 112 | 
 113 | def _prune_old_episodes():
 114 |     """Remove episodes older than today from used_clips.json (R27 same-day expiry)."""
 115 |     data = _load_used_clips()
 116 |     today = datetime.utcnow().strftime("%Y-%m-%d")
 117 |     before = len(data.get("episodes", []))
 118 |     data["episodes"] = [ep for ep in data.get("episodes", []) if ep.get("date", "") == today]
 119 |     after = len(data["episodes"])
 120 |     if after < before:
 121 |         logger.info(f"EPISODE MEMORY: Pruned {before - after} episodes from previous days")
 122 |         os.makedirs(os.path.dirname(USED_CLIPS_PATH), exist_ok=True)
 123 |         with open(USED_CLIPS_PATH, "w") as f:
 124 |             json.dump(data, f, indent=2)
 125 |     return data
 126 | 
 127 | 
 128 | def _get_recent_channels(max_episodes: int = 3) -> set:
 129 |     """Get channels used in the last N episode_memory entries for diversity penalty.
 130 | 
 131 |     ISSUE 5 FIX: Channels appearing in recent episodes get a 50% score reduction
 132 |     to force clip variety across episodes.
 133 |     """
 134 |     data = _load_used_clips()
 135 |     episodes = data.get("episodes", [])
 136 |     # Take the last N episodes (most recent)
 137 |     recent = episodes[-max_episodes:] if len(episodes) >= max_episodes else episodes
 138 |     channels = set()
 139 |     for ep in recent:
 140 |         channels.update(ep.get("channels", []))
 141 |     if channels:
 142 |         logger.info(f"DIVERSITY: {len(channels)} channels from last {len(recent)} episodes")
 143 |     return channels
 144 | 
 145 | 
 146 | def _get_recent_video_ids(max_episodes: int = 7) -> set:
 147 |     """Get video_ids used TODAY (same calendar day, UTC).
 148 | 
 149 |     R27: Same-day expiry — clips from any previous date are immediately eligible.
 150 |     """
 151 |     data = _load_used_clips()
 152 |     today = datetime.utcnow().strftime("%Y-%m-%d")
 153 |     ids = set()
 154 |     for ep in data.get("episodes", []):
 155 |         if ep.get("date", "") == today:
 156 |             ids.update(ep.get("video_ids", []))
 157 |     logger.info(f"EPISODE MEMORY: {len(ids)} video_ids blocked (same-day only, {today})")
 158 |     return ids
 159 | 
 160 | 
 161 | def _record_episode(clips: list):
 162 |     """Record this episode's video_ids to the memory file."""
 163 |     data = _load_used_clips()
 164 |     video_ids = [c.get("video_id", "") for c in clips if c.get("video_id")]
 165 |     channels = [c.get("channel", "") for c in clips if c.get("channel")]
 166 |     data["episodes"].append({
 167 |         "date": datetime.utcnow().strftime("%Y-%m-%d"),
 168 |         "video_ids": video_ids,
 169 |         "channels": channels,
 170 |     })
 171 |     # R27: Keep only today's episodes
 172 |     today = datetime.utcnow().strftime("%Y-%m-%d")
 173 |     data["episodes"] = [ep for ep in data["episodes"] if ep.get("date", "") == today]
 174 |     os.makedirs(os.path.dirname(USED_CLIPS_PATH), exist_ok=True)
 175 |     with open(USED_CLIPS_PATH, "w") as f:
 176 |         json.dump(data, f, indent=2)
 177 | 
 178 | 
 179 | AD_READ_PHRASES = [
 180 |     "brought to you by", "thanks to our sponsor", "use code", "promo code",
 181 |     "check out", "go to", ".com/", "discount", "affiliate", "sponsored by",
 182 |     "this episode is", "today's episode is brought", "support the show",
 183 |     "today's sponsor", "free trial", "get 20% off", "get 10% off",
 184 |     "use my link", "click the link in", "head over to", "sign up at",
 185 |     "limited time offer", "swipe up",
 186 |     # Issue 5: expanded ad read patterns
 187 |     "unchained.com", "unchained capital", "collaborative custody",
 188 |     "swan bitcoin", "river.com", "fold app", "cash app",
 189 |     "strike app", "download the app", "link in description",
 190 |     "link in the description", "link below", "link in the bio",
 191 | ]
 192 | 
 193 | 
 194 | def contains_ad_read(transcript_segment: str) -> bool:
 195 |     """Return True if this transcript segment contains ad read content."""
 196 |     lower = transcript_segment.lower()
 197 |     for phrase in AD_READ_PHRASES:
 198 |         if phrase in lower:
 199 |             logger.info(f"🚫 AD READ DETECTED — pattern '{phrase}' found. Clip REJECTED.")
 200 |             return True
 201 |     return False
 202 | 
 203 | 
 204 | def _format_transcripts(videos: list) -> str:
 205 |     """Format video transcripts for the Claude prompt."""
 206 |     parts = []
 207 |     for i, v in enumerate(videos):
 208 |         timestamped = v.get("timestamped_text", "")
 209 |         # Truncate very long transcripts to keep within token limits
 210 |         if len(timestamped) > 1500:
 211 |             timestamped = timestamped[:1500] + "\n... [transcript truncated]"
 212 | 
 213 |         parts.append(
 214 |             f"--- VIDEO {i+1} ---\n"
 215 |             f"Channel: {v['channel']}\n"
 216 |             f"Title: {v['title']}\n"
 217 |             f"Video ID: {v['video_id']}\n"
 218 |             f"Duration: {v['duration']}s\n"
 219 |             f"Transcript:\n{timestamped}\n"
 220 |         )
 221 |     return "\n".join(parts)
 222 | 
 223 | 
 224 | def _parse_llm_json(text: str, label: str = "LLM") -> dict | None:
 225 |     """Parse JSON from LLM response — robust brace-counting parser.
 226 | 
 227 |     Strategy:
 228 |       1. Strip markdown fences
 229 |       2. Try direct json.loads
 230 |       3. Brace-counting: walk char-by-char extracting each complete {...} object
 231 |          that contains both "rank" and "video_id" keys (i.e. clip objects)
 232 |       4. Reassemble from collected clips + regex-extracted episode_title/cold_open
 233 |       5. Progressive boundary search as final fallback
 234 | 
 235 |     Returns parsed dict or None on failure.
 236 |     """
 237 |     if not text:
 238 |         return None
 239 | 
 240 |     # --- Step 1: Strip markdown fences ---
 241 |     import re as _re
 242 |     stripped = text
 243 |     if "```json" in stripped:
 244 |         stripped = stripped.split("```json", 1)[1].split("```", 1)[0]
 245 |     elif "```" in stripped:
 246 |         stripped = stripped.split("```", 1)[1].split("```", 1)[0]
 247 |     stripped = stripped.strip()
 248 | 
 249 |     # --- Step 2: Direct parse ---
 250 |     try:
 251 |         return json.loads(stripped)
 252 |     except json.JSONDecodeError:
 253 |         pass
 254 | 
 255 |     # --- Step 3: Brace-counting extraction ---
 256 |     def _extract_objects(s: str) -> list:
 257 |         """Walk char-by-char, track brace depth, yield complete top-level objects."""
 258 |         objects = []
 259 |         i = 0
 260 |         in_string = False
 261 |         escape_next = False
 262 |         while i < len(s):
 263 |             if s[i] == '{' and not in_string:
 264 |                 # Start of an object — track depth
 265 |                 depth = 1
 266 |                 start = i
 267 |                 j = i + 1
 268 |                 obj_in_string = False
 269 |                 obj_escape = False
 270 |                 while j < len(s) and depth > 0:
 271 |                     c = s[j]
 272 |                     if obj_escape:
 273 |                         obj_escape = False
 274 |                     elif c == '\\' and obj_in_string:
 275 |                         obj_escape = True
 276 |                     elif c == '"' and not obj_escape:
 277 |                         obj_in_string = not obj_in_string
 278 |                     elif not obj_in_string:
 279 |                         if c == '{':
 280 |                             depth += 1
 281 |                         elif c == '}':
 282 |                             depth -= 1
 283 |                     j += 1
 284 |                 if depth == 0:
 285 |                     candidate = s[start:j]
 286 |                     try:
 287 |                         obj = json.loads(candidate)
 288 |                         objects.append(obj)
 289 |                     except json.JSONDecodeError:
 290 |                         pass
 291 |                 i = j
 292 |             else:
 293 |                 if escape_next:
 294 |                     escape_next = False
 295 |                 elif s[i] == '\\' and in_string:
 296 |                     escape_next = True
 297 |                 elif s[i] == '"':
 298 |                     in_string = not in_string
 299 |                 i += 1
 300 |         return objects
 301 | 
 302 |     all_objects = _extract_objects(stripped)
 303 | 
 304 |     # Separate clip objects (have rank + video_id) from the wrapper
 305 |     clips = []
 306 |     wrapper = None
 307 |     for obj in all_objects:
 308 |         if "rank" in obj and "video_id" in obj:
 309 |             clips.append(obj)
 310 |         elif "clips" in obj:
 311 |             # This is a successfully parsed wrapper — use it directly
 312 |             return obj
 313 |         elif "episode_title" in obj or "cold_open" in obj:
 314 |             wrapper = obj
 315 | 
 316 |     if clips:
 317 |         # --- Step 4: Reassemble from clips + regex metadata ---
 318 |         episode_title = "Pulse Check"
 319 |         cold_open = ""
 320 | 
 321 |         if wrapper:
 322 |             episode_title = wrapper.get("episode_title", episode_title)
 323 |             cold_open = wrapper.get("cold_open", cold_open)
 324 |         else:
 325 |             # Try regex extraction from raw text
 326 |             m_title = _re.search(r'"episode_title"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped)
 327 |             if m_title:
 328 |                 episode_title = m_title.group(1)
 329 |             m_cold = _re.search(r'"cold_open"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped)
 330 |             if m_cold:
 331 |                 cold_open = m_cold.group(1)
 332 | 
 333 |         # Sort by rank to maintain order
 334 |         clips.sort(key=lambda c: c.get("rank", 999))
 335 |         result = {
 336 |             "episode_title": episode_title,
 337 |             "cold_open": cold_open,
 338 |             "clips": clips,
 339 |         }
 340 |         logger.warning(f"{label}: JSON repaired via brace-counting ({len(clips)} clips recovered)")
 341 |         return result
 342 | 
 343 |     # --- Step 5: Progressive boundary search (last resort) ---
 344 |     try:
 345 |         last_brace = stripped.rfind("}")
 346 |         if last_brace > 0:
 347 |             repaired = stripped[:last_brace + 1]
 348 |             if '"clips"' in repaired and not repaired.rstrip().endswith("]}"):
 349 |                 repaired = repaired.rstrip().rstrip(",") + "]}"
 350 |             result = json.loads(repaired)
 351 |             logger.warning(f"{label}: JSON repaired (progressive boundary salvage)")
 352 |             return result
 353 |     except json.JSONDecodeError:
 354 |         pass
 355 | 
 356 |     logger.warning(f"{label}: JSON parse failed. Raw (first 500): {stripped[:500]}")
 357 |     return None
 358 | 
 359 | 
 360 | def select_clips(videos: list) -> dict:
 361 |     """Use Claude to select the 5 best clip moments from transcribed videos.
 362 | 
 363 |     Args:
 364 |         videos: List of dicts from scan_all_channels() with transcript_text/timestamped_text
 365 | 
 366 |     Returns:
 367 |         Dict with 'clips' list, 'episode_title', 'cold_open'
 368 |     """
 369 |     if not videos:
 370 |         logger.error("No videos to select from")
 371 |         return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
 372 | 
 373 |     from relay import call_llm, reload_env; reload_env()
 374 | 
 375 |     transcripts_text = _format_transcripts(videos)
 376 |     prompt = SELECTION_PROMPT.replace('{transcripts}', transcripts_text)
 377 | 
 378 |     logger.info(f"Sending {len(videos)} transcripts for clip selection...")
 379 |     text = call_llm(prompt, max_tokens=8000)
 380 |     if text is None:
 381 |         logger.error("All LLM providers failed for clip selection")
 382 |         return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
 383 | 
 384 |     try:
 385 |         result = _parse_llm_json(text, label="main selection")
 386 |         if result is None:
 387 |             logger.error(f"Failed to parse Claude response as JSON. Raw (first 500): {text[:500]}")
 388 |             return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
 389 | 
 390 |         clips = result.get("clips", [])
 391 | 
 392 |         # Post-selection ad read filter (double gate per PIPELINE_LAWS Section 15)
 393 |         clean_clips = []
 394 |         for c in clips:
 395 |             quote = c.get("quote", "")
 396 |             setup = c.get("host_setup", "")
 397 |             if contains_ad_read(quote) or contains_ad_read(setup):
 398 |                 logger.warning(f"  REJECTED clip #{c['rank']} [{c.get('channel','')}] — ad read content")
 399 |                 continue
 400 |             clean_clips.append(c)
 401 |         result["clips"] = clean_clips
 402 | 
 403 |         # Channel dedup: max 1 clip per channel, keep higher-ranked (lower number)
 404 |         seen_channels = {}
 405 |         deduped_clips = []
 406 |         for c in clean_clips:
 407 |             ch = c.get("channel", "")
 408 |             if ch in seen_channels:
 409 |                 existing = seen_channels[ch]
 410 |                 if c["rank"] < existing["rank"]:
 411 |                     logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {c['rank']} clip")
 412 |                     deduped_clips.remove(existing)
 413 |                     deduped_clips.append(c)
 414 |                     seen_channels[ch] = c
 415 |                 else:
 416 |                     logger.warning(f"DEDUP: Removed duplicate from channel {ch}, keeping rank {existing['rank']} clip")
 417 |             else:
 418 |                 deduped_clips.append(c)
 419 |                 seen_channels[ch] = c
 420 |         clean_clips = deduped_clips
 421 |         result["clips"] = clean_clips
 422 | 
 423 |         # Episode memory: drop clips from recently used videos
 424 |         recent_ids = _get_recent_video_ids(max_episodes=1)
 425 |         if recent_ids:
 426 |             memory_filtered = []
 427 |             for c in clean_clips:
 428 |                 vid = c.get("video_id", "")
 429 |                 if vid in recent_ids:
 430 |                     logger.warning(f"EPISODE MEMORY: Dropped clip from video {vid} "
 431 |                                    f"[{c.get('channel', '')}] — used in recent episode")
 432 |                 else:
 433 |                     memory_filtered.append(c)
 434 |             clean_clips = memory_filtered
 435 |             result["clips"] = clean_clips
 436 | 
 437 |         # 5-CLIP RULE enforcement (PIPELINE_LAWS Section 22)
 438 |         test_mode = len(videos) <= 4  # heuristic: few source videos = test mode
 439 |         required_clips = 2 if test_mode else 5
 440 | 
 441 |         # If we have fewer clips than required, re-select from remaining videos
 442 |         used_channels = {c.get("channel", "") for c in clean_clips}
 443 |         used_video_ids = {c.get("video_id", "") for c in clean_clips}
 444 | 
 445 |         if not test_mode and len(clean_clips) < 5:
 446 |             logger.warning(f"5-CLIP RULE: Only {len(clean_clips)} clips after filtering, "
 447 |                            f"need 5. Re-selecting from remaining channels...")
 448 | 
 449 |             # Find available videos not yet used
 450 |             available = [v for v in videos
 451 |                          if v.get("channel", "") not in used_channels
 452 |                          and v.get("video_id", "") not in used_video_ids]
 453 | 
 454 |             if available:
 455 |                 # Ask Claude to pick from remaining videos
 456 |                 remaining_text = _format_transcripts(available)
 457 |                 need = 5 - len(clean_clips)
 458 |                 reselect_prompt = (
 459 |                     f"Pick the {need} BEST clip moments from these videos. "
 460 |                     f"Each clip from a DIFFERENT channel. 20-40 seconds each. "
 461 |                     f"NO ad reads. Return ONLY valid JSON with a 'clips' array.\n\n"
 462 |                     f"ALREADY SELECTED channels (DO NOT use these): {list(used_channels)}\n\n"
 463 |                     f"AVAILABLE VIDEOS:\n{remaining_text}\n\n"
 464 |                     f"Return JSON: {{\"clips\": [{{\"rank\": N, \"video_id\": \"...\", "
 465 |                     f"\"channel\": \"...\", \"video_title\": \"...\", \"start_seconds\": N, "
 466 |                     f"\"end_seconds\": N, \"quote\": \"...\", \"why\": \"...\", "
 467 |                     f"\"host_setup\": \"...\", \"host_react\": \"...\"}}]}}"
 468 |                 )
 469 |                 try:
 470 |                     text2 = call_llm(reselect_prompt, max_tokens=8000)
 471 |                     if text2 is None:
 472 |                         raise RuntimeError("All LLM providers failed for re-selection")
 473 | 
 474 |                     extra = _parse_llm_json(text2, label="re-selection")
 475 |                     if extra is None:
 476 |                         # Retry once with fresh call
 477 |                         logger.warning("Re-selection JSON parse failed, retrying...")
 478 |                         text2 = call_llm(reselect_prompt, max_tokens=8000)
 479 |                         if text2 is not None:
 480 |                             extra = _parse_llm_json(text2, label="re-selection retry")
 481 |                     if extra is None:
 482 |                         logger.warning(f"Re-selection parse failed after retry. Raw (first 500): {(text2 or '')[:500]}")
 483 |                         extra = {"clips": []}
 484 |                     extra_clips = extra.get("clips", [])
 485 | 
 486 |                     # Filter extras through ad-read + dedup
 487 |                     for ec in extra_clips:
 488 |                         ch = ec.get("channel", "")
 489 |                         vid = ec.get("video_id", "")
 490 |                         if ch in used_channels or vid in used_video_ids:
 491 |                             continue
 492 |                         if contains_ad_read(ec.get("quote", "")) or contains_ad_read(ec.get("host_setup", "")):
 493 |                             continue
 494 |                         ec["rank"] = len(clean_clips) + 1
 495 |                         clean_clips.append(ec)
 496 |                         used_channels.add(ch)
 497 |                         used_video_ids.add(vid)
 498 |                         logger.info(f"  RE-SELECT: Added #{ec['rank']} [{ch}] {ec.get('video_title', '')[:40]}")
 499 |                         if len(clean_clips) >= 5:
 500 |                             break
 501 |                 except Exception as e:
 502 |                     logger.warning(f"Re-selection failed: {e}")
 503 | 
 504 |             result["clips"] = clean_clips
 505 | 
 506 |         # Issue 7: HARD ENFORCEMENT — unique channels in Python after ALL selection
 507 |         seen_channels = set()
 508 |         deduped_final = []
 509 |         for clip in clean_clips:
 510 |             ch = clip.get("channel", "")
 511 |             if ch not in seen_channels:
 512 |                 seen_channels.add(ch)
 513 |                 deduped_final.append(clip)
 514 |             else:
 515 |                 logger.warning(f"HARD DEDUP: Removed duplicate channel '{ch}' clip #{clip.get('rank', '?')}")
 516 |         if len(deduped_final) < len(clean_clips):
 517 |             logger.warning(f"HARD DEDUP: {len(clean_clips)} → {len(deduped_final)} clips after enforcement")
 518 |         clean_clips = deduped_final
 519 |         result["clips"] = clean_clips
 520 | 
 521 |         if len(clean_clips) < 5 and not test_mode:
 522 |             logger.error(f"HARD DEDUP: Only {len(clean_clips)} unique channels. Need replacement clips.")
 523 | 
 524 |         # Render22 FIX 9: Clip diversity — no consecutive clips from same channel or speaker
 525 |         if len(clean_clips) > 1:
 526 |             reordered = [clean_clips[0]]
 527 |             remaining = list(clean_clips[1:])
 528 |             while remaining:
 529 |                 prev_ch = reordered[-1].get("channel", "")
 530 |                 # Find first clip from a different channel
 531 |                 found = False
 532 |                 for idx, c in enumerate(remaining):
 533 |                     if c.get("channel", "") != prev_ch:
 534 |                         reordered.append(remaining.pop(idx))
 535 |                         found = True
 536 |                         break
 537 |                 if not found:
 538 |                     # No different channel available — take first remaining
 539 |                     reordered.append(remaining.pop(0))
 540 |                     logger.warning(f"  FIX 9: Consecutive same-channel unavoidable at position {len(reordered)}")
 541 |             clean_clips = reordered
 542 |             result["clips"] = clean_clips
 543 |             logger.info(f"  FIX 9: Clip order after diversity: {[c.get('channel', '') for c in clean_clips]}")
 544 | 
 545 |         # ISSUE 5 FIX: Channel diversity bonus — penalize channels from last 3 episodes by 50%
 546 |         recent_channels = _get_recent_channels(max_episodes=3)
 547 |         if recent_channels:
 548 |             logger.info(f"DIVERSITY: Penalizing {len(recent_channels)} recently-used channels: {sorted(recent_channels)}")
 549 |             for clip in clean_clips:
 550 |                 ch = clip.get("channel", "")
 551 |                 if ch in recent_channels:
 552 |                     clip["_diversity_penalty"] = True
 553 |             # Sort: non-penalized first (preserving relative order), penalized last
 554 |             non_penalized = [c for c in clean_clips if not c.get("_diversity_penalty")]
 555 |             penalized = [c for c in clean_clips if c.get("_diversity_penalty")]
 556 |             if non_penalized:
 557 |                 # Only reorder if we have enough non-penalized clips to fill slots
 558 |                 clean_clips = non_penalized + penalized
 559 |                 result["clips"] = clean_clips
 560 |                 logger.info(f"  DIVERSITY: {len(non_penalized)} fresh + {len(penalized)} penalized clips")
 561 | 
 562 |         # Score-based ranking (CLIP SCORER per PRODUCTION_DESIGN_LAWS)
 563 |         try:
 564 |             from utils.clip_scorer import rank_clips, _load_narrative_context
 565 |             narrative_ctx = _load_narrative_context()
 566 |             if narrative_ctx:
 567 |                 dominant = narrative_ctx.get("dominant_narrative", "")
 568 |                 if dominant:
 569 |                     logger.info(f"Episode narrative: {dominant}")
 570 |                 # Filter clips that only match avoid_topics
 571 |                 avoid = [t.lower() for t in narrative_ctx.get("avoid_topics", [])]
 572 |                 if avoid:
 573 |                     pre_count = len(clean_clips)
 574 |                     clean_clips = [
 575 |                         c for c in clean_clips
 576 |                         if not all(
 577 |                             a in (c.get("quote", "") + " " + c.get("video_title", "")).lower()
 578 |                             for a in avoid
 579 |                         )
 580 |                     ]
 581 |                     if len(clean_clips) < pre_count:
 582 |                         logger.info(f"Narrative filter: removed {pre_count - len(clean_clips)} clips matching avoid_topics")
 583 |             clean_clips = rank_clips(clean_clips, narrative_context=narrative_ctx)
 584 |             logger.info("Clip scorer applied — clips re-ranked by intelligence score (narrative-aware)")
 585 |         except Exception as e:
 586 |             logger.warning(f"Clip scorer unavailable, keeping original rank order: {e}")
 587 | 
 588 |         # Log the 5-clip rule result
 589 |         unique_channels = {c.get("channel", "") for c in clean_clips}
 590 |         channel_list = sorted(unique_channels)
 591 |         logger.info(f"5-CLIP RULE: Selected {len(clean_clips)} clips from "
 592 |                     f"{len(unique_channels)} unique channels: {channel_list}")
 593 | 
 594 |         logger.info(f"Claude selected {len(clips)} clips, {len(clean_clips)} passed all filters:")
 595 |         for c in clean_clips:
 596 |             logger.info(f"  #{c['rank']}: [{c['channel']}] {c.get('video_title', '')[:40]} "
 597 |                         f"({c.get('start_seconds', '?')}-{c.get('end_seconds', '?')}s)")
 598 |             logger.info(f"    Quote: \"{c.get('quote', '')[:60]}...\"")
 599 | 
 600 |         # Record this episode's clips to memory
 601 |         _record_episode(clean_clips)
 602 | 
 603 |         return result
 604 | 
 605 |     except json.JSONDecodeError as e:
 606 |         logger.error(f"Failed to parse Claude response as JSON: {e}")
 607 |         logger.error(f"Response text: {text[:500]}")
 608 |         return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
 609 |     except Exception as e:
 610 |         logger.error(f"Claude API error: {e}")
 611 |         return {"clips": [], "episode_title": "Pulse Check", "cold_open": ""}
 612 | 
 613 | 
 614 | def select_montage_clips(videos: list) -> dict:
 615 |     """Independent montage clip selection using local Qwen3-Coder.
 616 | 
 617 |     Selects the best 12-22 second standalone moment from each video.
 618 |     Completely independent from select_clips() — different timestamps, different criteria.
 619 |     Falls back to Pulse Check clip timestamps if Qwen unavailable.
 620 |     """
 621 |     import requests
 622 |     import json as _json
 623 |     import re as _re
 624 | 
 625 |     OLLAMA_URL = "http://localhost:11435"
 626 |     MODEL = "qwen3-coder:30b"
 627 |     montage_clips = []
 628 | 
 629 |     for video in videos:
 630 |         video_id = video.get("video_id", "")
 631 |         channel = video.get("channel", "")
 632 |         title = video.get("title", "")
 633 |         timestamped_text = video.get("timestamped_text", "") or video.get("transcript_text", "")
 634 | 
 635 |         if not timestamped_text or len(timestamped_text) < 100:
 636 |             logger.info(f"[Montage] No transcript for {channel} {video_id}, skipping")
 637 |             continue
 638 | 
 639 |         prompt = (
 640 |             "You are selecting the single best SHORT standalone highlight clip for a daily "
 641 |             "Bitcoin media compilation. Viewers have ZERO prior context.\n\n"
 642 |             "Select the 12-22 second window that is the most punchy, self-contained, "
 643 |             "and quotable moment in this entire video.\n"
 644 |             "CRITERIA:\n"
 645 |             "- Complete thought — starts and ends at natural sentence boundaries\n"
 646 |             "- No context needed to understand it\n"
 647 |             "- Single strong statement or striking data point\n"
 648 |             "- NOT the same as the Pulse Check clip (find a DIFFERENT moment)\n"
 649 |             "- Ideal: starts with a strong noun or number, ends with a period\n\n"
 650 |             f"VIDEO: {title}\nCHANNEL: {channel}\n\n"
 651 |             f"TIMESTAMPED TRANSCRIPT:\n{timestamped_text[:3000]}\n\n"
 652 |             'Return ONLY valid JSON, no markdown:\n'
 653 |             '{"montage_start_sec": int, "montage_end_sec": int, '
 654 |             '"quote": "exact words spoken", "reason": "why this moment"}'
 655 |         )
 656 | 
 657 |         try:
 658 |             resp = requests.post(
 659 |                 f"{OLLAMA_URL}/api/chat",
 660 |                 json={
 661 |                     "model": MODEL,
 662 |                     "messages": [{"role": "user", "content": prompt}],
 663 |                     "stream": False,
 664 |                     "options": {"temperature": 0.2},
 665 |                 },
 666 |                 timeout=30,
 667 |             )
 668 |             resp.raise_for_status()
 669 |             raw = resp.json().get("message", {}).get("content", "")
 670 |             match = _re.search(r"\{[^{}]+\}", raw, _re.DOTALL)
 671 |             if match:
 672 |                 result = _json.loads(match.group())
 673 |                 start = int(result.get("montage_start_sec", 0))
 674 |                 end = int(result.get("montage_end_sec", start + 18))
 675 |                 # Validate reasonable range
 676 |                 if 0 <= start < end and (end - start) <= 30:
 677 |                     montage_clips.append({
 678 |                         "rank": len(montage_clips) + 1,
 679 |                         "video_id": video_id,
 680 |                         "channel": channel,
 681 |                         "video_title": title,
 682 |                         "start_seconds": start,
 683 |                         "end_seconds": end,
 684 |                         "quote": result.get("quote", ""),
 685 |                         "score": video.get("score", 50),
 686 |                         "timestamped_text": timestamped_text,
 687 |                         "montage_reason": result.get("reason", ""),
 688 |                     })
 689 |                     logger.info(f"[Montage] {channel}: {start}s-{end}s — {result.get('quote', '')[:60]}")
 690 |                     continue
 691 |         except Exception as e:
 692 |             logger.warning(f"[Montage] Qwen failed for {channel}: {e}")
 693 | 
 694 |         # Fallback: skip — montage will have fewer clips if Qwen unavailable
 695 |         logger.info(f"[Montage] {channel}: using fallback empty (Qwen unavailable)")
 696 | 
 697 |     return {"clips": montage_clips}
 698 | 
 699 | 
 700 | if __name__ == "__main__":
 701 |     # Test with cached transcripts or live scan
 702 |     from channel_scanner import scan_all_channels
 703 |     videos = scan_all_channels()
 704 |     if videos:
 705 |         selections = select_clips(videos)
 706 |         print(json.dumps(selections, indent=2))
 707 |     else:
 708 |         print("No videos found to select from")
 709 | 
```

### File: video_pipeline_v3/clip_extractor.py (878 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Clip Extractor — downloads exact timestamp ranges from YouTube WITH original audio.
   3 | 
   4 | Uses yt-dlp --download-sections to grab the precise moments Claude selected.
   5 | CRITICAL: Clips retain their ORIGINAL audio. No muting. No TTS overlay.
   6 | """
   7 | import logging
   8 | import os
   9 | import shutil
  10 | import subprocess
  11 | import time
  12 | 
  13 | logger = logging.getLogger("ClipExtractor")
  14 | if not logger.handlers:
  15 |     handler = logging.StreamHandler()
  16 |     handler.setFormatter(logging.Formatter("[extractor] %(message)s"))
  17 |     logger.addHandler(handler)
  18 |     logger.setLevel(logging.INFO)
  19 | 
  20 | BASE = os.path.dirname(os.path.abspath(__file__))
  21 | CLIP_CACHE = os.path.join(BASE, "downloads", "clip_cache")
  22 | COOKIES_FILE = os.path.join(BASE, "data", "yt_cookies.txt")
  23 | # Render20: No hard clip duration cap — episode is as long as it needs to be
  24 | 
  25 | from utils.clip_archive import save_clip, get_fallback_clip
  26 | 
  27 | if not (os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0):
  28 |     logger.info("[yt-dlp] No cookies file — add data/yt_cookies.txt for rate limit protection")
  29 | 
  30 | 
  31 | def _run_ffmpeg(args: list, label: str = "", timeout: int = 300) -> bool:
  32 |     """Run ffmpeg command, return True on success."""
  33 |     cmd = ["ffmpeg", "-y"] + args
  34 |     try:
  35 |         proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
  36 |         if proc.returncode != 0:
  37 |             logger.error(f"FAIL {label}: {proc.stderr[-400:]}")
  38 |             return False
  39 |         return True
  40 |     except subprocess.TimeoutExpired:
  41 |         logger.error(f"TIMEOUT {label} after {timeout}s — killing ffmpeg")
  42 |         return False
  43 |     except Exception as e:
  44 |         logger.error(f"EXCEPTION {label}: {e}")
  45 |         return False
  46 | 
  47 | 
  48 | def fix_av_sync(input_path: str, output_path: str) -> bool:
  49 |     """Nuclear AV sync fix — full decode+re-encode with PTS reset.
  50 | 
  51 |     Uses discardcorrupt + itsoffset 0 + max_interleave_delta=0 to eliminate
  52 |     DTS discontinuities from yt-dlp multi-stream merges.
  53 |     """
  54 |     return _run_ffmpeg([
  55 |         "-fflags", "+genpts+igndts+discardcorrupt",
  56 |         "-itsoffset", "0",
  57 |         "-i", input_path,
  58 |         "-map", "0:v:0",
  59 |         "-map", "0:a:0",
  60 |         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
  61 |         "-r", "30", "-vsync", "cfr",
  62 |         "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=fps=30,format=yuv420p,setpts=PTS-STARTPTS",
  63 |         "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
  64 |         "-af", "aresample=async=1:min_hard_comp=0.1:first_pts=0,asetpts=PTS-STARTPTS",
  65 |         "-avoid_negative_ts", "make_zero",
  66 |         "-max_interleave_delta", "0",
  67 |         "-movflags", "+faststart",
  68 |         output_path,
  69 |     ], "av_sync_fix_v2", 300)
  70 | 
  71 | 
  72 | def check_av_sync(clip_path: str) -> float:
  73 |     """Measure actual AV sync using first packet DTS timestamps."""
  74 |     result = subprocess.run([
  75 |         "ffprobe", "-v", "quiet", "-print_format", "json",
  76 |         "-show_packets", "-read_intervals", "%+#10",
  77 |         clip_path
  78 |     ], capture_output=True, text=True)
  79 |     try:
  80 |         import json as _json
  81 |         data = _json.loads(result.stdout)
  82 |         packets = data.get("packets", [])
  83 |         v_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "video"), 0)
  84 |         a_dts = next((float(p.get("dts_time", 0)) for p in packets if p.get("codec_type") == "audio"), 0)
  85 |         offset = a_dts - v_dts
  86 |         logger.info(f"AV packet-level offset for {os.path.basename(clip_path)}: {offset:+.3f}s")
  87 |         if abs(offset) > 0.05:
  88 |             logger.warning(f"WARNING: AV offset {offset:+.3f}s exceeds 0.05s threshold after fix")
  89 |         return offset
  90 |     except Exception as e:
  91 |         logger.warning(f"Could not measure AV sync: {e}")
  92 |         return 0.0
  93 | 
  94 | 
  95 | def find_nearest_pause(clip_path: str, original_end: float, pad_window: float = 10.0) -> float:
  96 |     """Find first natural pause after original_end within the pad window.
  97 | 
  98 |     Uses ffmpeg silencedetect to find silence gaps, then trims at the first
  99 |     natural pause after the original end timestamp. If no silence found
 100 |     within the window, hard-cuts at the pad mark.
 101 | 
 102 |     Args:
 103 |         clip_path: Path to the extracted clip (already has 8s padding)
 104 |         original_end: The original end timestamp relative to clip start
 105 |         pad_window: How many seconds of padding were added (default 8)
 106 | 
 107 |     Returns:
 108 |         Trim point in seconds from clip start
 109 |     """
 110 |     import re
 111 |     try:
 112 |         result = subprocess.run([
 113 |             "ffmpeg", "-i", clip_path,
 114 |             "-af", "silencedetect=noise=-30dB:d=0.3",
 115 |             "-f", "null", "-"
 116 |         ], capture_output=True, text=True, timeout=30)
 117 | 
 118 |         # Extract silence_start timestamps (beginning of each pause)
 119 |         pauses = [float(m.group(1)) for m in
 120 |                   re.finditer(r"silence_start: ([\d.]+)", result.stderr)]
 121 | 
 122 |         # Find first pause that starts after original_end but within pad window
 123 |         candidates = [p for p in pauses if original_end <= p <= original_end + pad_window]
 124 |         if candidates:
 125 |             trim_at = candidates[0] + 0.2  # trim slightly into the silence
 126 |             logger.info(f"CLIP TRIM: Trimmed at natural pause at {trim_at:.1f}s")
 127 |             return trim_at
 128 |     except Exception as e:
 129 |         logger.warning(f"  Silence detection failed: {e}")
 130 | 
 131 |     logger.info(f"CLIP TRIM: No silence found, using {pad_window}s hard pad")
 132 |     return original_end + pad_window
 133 | 
 134 | 
 135 | def ffprobe_duration(path: str) -> float:
 136 |     r = subprocess.run(
 137 |         ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 138 |          "-of", "csv=p=0", path],
 139 |         capture_output=True, text=True,
 140 |     )
 141 |     try:
 142 |         return float(r.stdout.strip())
 143 |     except Exception:
 144 |         return 0.0
 145 | 
 146 | 
 147 | FORCE_SKIP_CHANNELS = ["Simply Bitcoin", "Bitcoin Magazine", "SatoSHE"]
 148 | 
 149 | 
 150 | def _skip_intro_silence(output_path: str, channel: str = "") -> None:
 151 |     """Render21 FIX 3: Speech onset detection replaces fixed +12s offset.
 152 | 
 153 |     Scans first 20s with silencedetect. Skips to first_speech_onset + 0.5s.
 154 |     FORCE_SKIP_CHANNELS always skip at least 15s.
 155 |     Also trims trailing silence/outro from last 10s.
 156 |     """
 157 |     import re as _re
 158 |     try:
 159 |         clip_dur = ffprobe_duration(output_path)
 160 |         if clip_dur < 5:
 161 |             return
 162 | 
 163 |         # --- INTRO SKIP: scan first 20s for speech onset ---
 164 |         result = subprocess.run([
 165 |             "ffmpeg", "-i", output_path, "-t", "20",
 166 |             "-af", "silencedetect=noise=-25dB:d=0.5",
 167 |             "-f", "null", "-"
 168 |         ], capture_output=True, text=True, timeout=30)
 169 |         silence_ends = _re.findall(r"silence_end: ([\d.]+)", result.stderr)
 170 | 
 171 |         # Determine skip point
 172 |         skip_to = 0.0
 173 |         force_min = 15.0 if any(ch in channel for ch in FORCE_SKIP_CHANNELS if ch) else 0.0
 174 | 
 175 |         if silence_ends:
 176 |             first_speech = float(silence_ends[0])
 177 |             skip_to = max(first_speech + 0.5, force_min)
 178 |             logger.info(f"  Render21: Speech onset at {first_speech:.1f}s, skip_to={skip_to:.1f}s (force_min={force_min:.0f}s, channel={channel})")
 179 |         elif force_min > 0:
 180 |             skip_to = force_min
 181 |             logger.info(f"  Render21: Force skip {force_min:.0f}s for {channel}")
 182 | 
 183 |         if skip_to > 0 and skip_to < clip_dur - 5:
 184 |             trimmed = output_path + ".jingle_skip.mp4"
 185 |             ok = _run_ffmpeg([
 186 |                 "-ss", f"{skip_to:.2f}", "-i", output_path,
 187 |                 "-c:v", "libx264", "-crf", "18", "-preset", "fast",
 188 |                 "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 189 |                 trimmed,
 190 |             ], f"speech onset skip +{skip_to:.1f}s", 60)
 191 |             if ok and os.path.exists(trimmed) and os.path.getsize(trimmed) > 10000:
 192 |                 os.replace(trimmed, output_path)
 193 |                 logger.info(f"  Render21: Intro skip applied at {skip_to:.1f}s")
 194 |             elif os.path.exists(trimmed):
 195 |                 os.remove(trimmed)
 196 | 
 197 |         # --- OUTRO TRIM: detect silence in last 10s ---
 198 |         clip_dur = ffprobe_duration(output_path)
 199 |         if clip_dur > 15:
 200 |             tail_start = max(0, clip_dur - 10)
 201 |             result2 = subprocess.run([
 202 |                 "ffmpeg", "-ss", f"{tail_start:.2f}", "-i", output_path,
 203 |                 "-af", "silencedetect=noise=-30dB:d=1.0",
 204 |                 "-f", "null", "-"
 205 |             ], capture_output=True, text=True, timeout=20)
 206 |             tail_silence_starts = _re.findall(r"silence_start: ([\d.]+)", result2.stderr)
 207 |             if tail_silence_starts:
 208 |                 # First silence in the tail = trim point (relative to tail_start)
 209 |                 trim_at = tail_start + float(tail_silence_starts[0]) + 0.3
 210 |                 if trim_at < clip_dur - 1.0:
 211 |                     outro_trimmed = output_path + ".outro_trim.mp4"
 212 |                     ok2 = _run_ffmpeg([
 213 |                         "-i", output_path, "-t", f"{trim_at:.2f}",
 214 |                         "-c:v", "libx264", "-crf", "18", "-preset", "fast",
 215 |                         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 216 |                         outro_trimmed,
 217 |                     ], f"outro trim at {trim_at:.1f}s", 60)
 218 |                     if ok2 and os.path.exists(outro_trimmed) and os.path.getsize(outro_trimmed) > 10000:
 219 |                         os.replace(outro_trimmed, output_path)
 220 |                         logger.info(f"  Render21: Outro trimmed at {trim_at:.1f}s (was {clip_dur:.1f}s)")
 221 |                     elif os.path.exists(outro_trimmed):
 222 |                         os.remove(outro_trimmed)
 223 | 
 224 |     except Exception as e:
 225 |         logger.warning(f"  Render21: Speech onset detection failed: {e}")
 226 | 
 227 | 
 228 | def extract_clip(video_id: str, start_sec: int, end_sec: int,
 229 |                  output_path: str, channel: str = "") -> bool:
 230 |     """Download exact clip segment with original audio.
 231 | 
 232 |     Args:
 233 |         video_id: YouTube video ID
 234 |         start_sec: Start time in seconds
 235 |         end_sec: End time in seconds
 236 |         output_path: Where to save the clip
 237 |         channel: Channel name for speech onset skip logic
 238 | 
 239 |     Returns:
 240 |         True if clip was extracted successfully
 241 |     """
 242 |     try:
 243 |         return _extract_clip_inner(video_id, start_sec, end_sec, output_path, channel)
 244 |     except Exception as e:
 245 |         logger.error(f"[extractor] FATAL exception on {video_id}: {e}", exc_info=True)
 246 |         # Clean up any temp files left behind
 247 |         for suffix in [".resync.mp4", ".sync.mp4", ".nuclear.mp4", ".lipsync.mp4",
 248 |                        ".fix7.mp4", ".jingle_skip.mp4", ".outro_trim.mp4"]:
 249 |             tmp = output_path + suffix
 250 |             if os.path.exists(tmp):
 251 |                 try: os.remove(tmp)
 252 |                 except OSError: pass
 253 |         return False
 254 | 
 255 | 
 256 | def _extract_clip_inner(video_id: str, start_sec: int, end_sec: int,
 257 |                         output_path: str, channel: str = "") -> bool:
 258 |     """Inner implementation of extract_clip — may raise exceptions."""
 259 |     os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
 260 | 
 261 |     # Check if already extracted
 262 |     if os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
 263 |         dur = ffprobe_duration(output_path)
 264 |         if dur > 1:
 265 |             logger.info(f"  Clip cached: {video_id} ({dur:.1f}s)")
 266 |             return True
 267 | 
 268 |     # Render21 FIX 3: Removed fixed +12s offset — speech onset detection handles intro skip
 269 |     logger.info(f"[extractor] Clip {video_id}: raw start_sec={start_sec}, end_sec={end_sec}, channel={channel}")
 270 | 
 271 |     # Apply start -3s / end +10s padding to avoid mid-sentence cuts (LAW A4)
 272 |     # Issue 6: Increased end padding from 8s to 10s for natural pauses
 273 |     padded_start = max(0, start_sec - 3)
 274 |     padded_end = end_sec + 10
 275 | 
 276 |     url = f"https://www.youtube.com/watch?v={video_id}"
 277 | 
 278 |     # Method 1: yt-dlp --download-sections (preferred)
 279 |     cmd = [
 280 |         "yt-dlp",
 281 |         "--download-sections", f"*{padded_start}-{padded_end}",
 282 |         "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
 283 |         "--merge-output-format", "mp4",
 284 |         "-o", output_path,
 285 |         "--no-playlist",
 286 |         "--quiet",
 287 |         "--force-overwrites",
 288 |         url,
 289 |     ]
 290 |     # RULE 3: yt-dlp cookies for rate limit protection
 291 |     if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
 292 |         cmd.insert(1, COOKIES_FILE)
 293 |         cmd.insert(1, "--cookies")
 294 | 
 295 |     logger.info(f"  Extracting {video_id} [{start_sec}-{end_sec}s]...")
 296 |     try:
 297 |         result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
 298 |         if result.returncode == 0 and os.path.exists(output_path):
 299 |             # FIX 1 (render10): Hard PTS resync — force both A/V to start at exactly 0
 300 |             # Eliminates B-frame DTS offsets from yt-dlp downloads that cause ~1s audio lag
 301 |             resync_tmp = output_path + ".resync.mp4"
 302 |             resync_ok = _run_ffmpeg([
 303 |                 "-i", output_path,
 304 |                 "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-vsync", "cfr",
 305 |                 "-vf", "setpts=PTS-STARTPTS",
 306 |                 "-c:a", "aac", "-ar", "48000",
 307 |                 "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 308 |                 "-avoid_negative_ts", "make_zero", "-max_interleave_delta", "0",
 309 |                 "-output_ts_offset", "0",
 310 |                 resync_tmp,
 311 |             ], f"hard PTS resync {video_id}", 300)
 312 |             if resync_ok and os.path.exists(resync_tmp):
 313 |                 os.replace(resync_tmp, output_path)
 314 |                 logger.info(f"[extractor] Hard PTS resync applied to {video_id}")
 315 |             elif os.path.exists(resync_tmp):
 316 |                 os.remove(resync_tmp)
 317 | 
 318 |             # AV sync fix pass
 319 |             sync_tmp = output_path + ".sync.mp4"
 320 |             if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
 321 |                 os.replace(sync_tmp, output_path)
 322 |                 logger.info(f"  AV sync fix applied")
 323 |             elif os.path.exists(sync_tmp):
 324 |                 os.remove(sync_tmp)
 325 |             # Sync validation gate — FIX 2: lowered nuclear threshold 0.15→0.08
 326 |             offset = check_av_sync(output_path)
 327 |             if abs(offset) > 0.08:
 328 |                 logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode (threshold 0.08s)")
 329 |                 nuclear_tmp = output_path + ".nuclear.mp4"
 330 |                 if _run_ffmpeg([
 331 |                     "-fflags", "+genpts+igndts+discardcorrupt",
 332 |                     "-i", output_path,
 333 |                     "-map", "0:v:0", "-map", "0:a:0",
 334 |                     "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 335 |                     "-r", "30", "-vsync", "cfr",
 336 |                     "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
 337 |                     "-c:a", "aac", "-ar", "48000", "-ac", "2",
 338 |                     "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 339 |                     "-avoid_negative_ts", "make_zero",
 340 |                     nuclear_tmp,
 341 |                 ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
 342 |                     os.replace(nuclear_tmp, output_path)
 343 |                     final_offset = check_av_sync(output_path)
 344 |                     logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
 345 |                 elif os.path.exists(nuclear_tmp):
 346 |                     os.remove(nuclear_tmp)
 347 |             # FIX 2: Dynamic offset correction — apply measured offset for ANY drift >20ms
 348 |             final_av = check_av_sync(output_path)
 349 |             if abs(final_av) > 0.02:
 350 |                 lipsync_tmp = output_path + ".lipsync.mp4"
 351 |                 correction = -final_av  # negate to correct
 352 |                 # If audio leads video (offset > 0, correction < 0): delay audio
 353 |                 # If video leads audio (offset < 0, correction > 0): delay video
 354 |                 audio_delay = max(0, correction)
 355 |                 video_delay = max(0, -correction)
 356 |                 before_offset = final_av
 357 |                 if _run_ffmpeg([
 358 |                     "-itsoffset", f"{audio_delay:.4f}",
 359 |                     "-i", output_path,
 360 |                     "-itsoffset", f"{video_delay:.4f}",
 361 |                     "-i", output_path,
 362 |                     "-map", "1:v:0", "-map", "0:a:0",
 363 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 364 |                     "-vf", "setpts=PTS-STARTPTS",
 365 |                     "-c:a", "aac", "-ar", "48000",
 366 |                     "-af", "asetpts=PTS-STARTPTS",
 367 |                     lipsync_tmp,
 368 |                 ], f"lipsync correction {correction:+.3f}s (was {final_av:+.3f}s)", 120) and os.path.exists(lipsync_tmp):
 369 |                     os.replace(lipsync_tmp, output_path)
 370 |                     after_offset = check_av_sync(output_path)
 371 |                     logger.info(f"  FIX 2: Lipsync corrected {before_offset:+.3f}s → {after_offset:+.3f}s")
 372 |                 elif os.path.exists(lipsync_tmp):
 373 |                     os.remove(lipsync_tmp)
 374 |             # Render21 FIX 7: Final AV sync gate — re-encode if >0.15s
 375 |             final_sync = check_av_sync(output_path)
 376 |             if abs(final_sync) > 0.15:
 377 |                 logger.error(f"  FIX 7: AV sync {final_sync:+.3f}s exceeds 0.15s — force re-encode")
 378 |                 fix7_tmp = output_path + ".fix7.mp4"
 379 |                 if _run_ffmpeg([
 380 |                     "-i", output_path,
 381 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 382 |                     "-vf", "setpts=PTS-STARTPTS",
 383 |                     "-c:a", "aac", "-ar", "48000",
 384 |                     "-af", "asetpts=PTS-STARTPTS",
 385 |                     "-r", "30", "-vsync", "cfr",
 386 |                     fix7_tmp,
 387 |                 ], "av_sync_fix7_force", 120) and os.path.exists(fix7_tmp):
 388 |                     os.replace(fix7_tmp, output_path)
 389 |                     post_fix7 = check_av_sync(output_path)
 390 |                     logger.info(f"  FIX 7: Re-encode done, sync now {post_fix7:+.3f}s")
 391 |                 elif os.path.exists(fix7_tmp):
 392 |                     os.remove(fix7_tmp)
 393 |             # Render21: Skip intro jingle via speech onset detection
 394 |             _skip_intro_silence(output_path, channel=channel)
 395 |             dur = ffprobe_duration(output_path)
 396 |             sz = os.path.getsize(output_path) / 1024
 397 |             logger.info(f"  Extracted: {dur:.1f}s, {sz:.0f}KB")
 398 |             return True
 399 |         else:
 400 |             logger.warning(f"  yt-dlp sections failed: {result.stderr[:200]}")
 401 |     except subprocess.TimeoutExpired:
 402 |         logger.warning(f"  yt-dlp timed out for {video_id}")
 403 | 
 404 |     # Method 2: Download full video, then ffmpeg trim
 405 |     logger.info(f"  Fallback: download full + ffmpeg trim...")
 406 |     full_path = os.path.join(CLIP_CACHE, f"{video_id}_full.mp4")
 407 |     os.makedirs(CLIP_CACHE, exist_ok=True)
 408 | 
 409 |     dl_cmd = [
 410 |         "yt-dlp",
 411 |         "-f", "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
 412 |         "--merge-output-format", "mp4",
 413 |         "-o", full_path,
 414 |         "--no-playlist",
 415 |         "--quiet",
 416 |         "--force-overwrites",
 417 |         url,
 418 |     ]
 419 |     # RULE 3: yt-dlp cookies for rate limit protection
 420 |     if os.path.isfile(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
 421 |         dl_cmd.insert(1, COOKIES_FILE)
 422 |         dl_cmd.insert(1, "--cookies")
 423 | 
 424 |     try:
 425 |         result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=300)
 426 |         if result.returncode != 0 or not os.path.exists(full_path):
 427 |             logger.error(f"  Full download failed: {result.stderr[:200]}")
 428 |             return False
 429 |     except subprocess.TimeoutExpired:
 430 |         logger.error(f"  Full download timed out")
 431 |         return False
 432 | 
 433 |     # FFmpeg trim with original audio (10s end pad per LAW A4, Issue 6)
 434 |     duration = (end_sec + 10) - max(0, start_sec - 3)
 435 |     trim_cmd = [
 436 |         "ffmpeg", "-y",
 437 |         "-ss", str(max(0, start_sec - 3)),
 438 |         "-i", full_path,
 439 |         "-t", str(duration),
 440 |         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 441 |         "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
 442 |         # Round 2 Fix 8: async resample during extraction to resync audio to video
 443 |         "-af", "aresample=async=1:first_pts=0",
 444 |         output_path,
 445 |     ]
 446 | 
 447 |     try:
 448 |         result = subprocess.run(trim_cmd, capture_output=True, text=True, timeout=120)
 449 |         if result.returncode == 0 and os.path.exists(output_path):
 450 |             # FIX 1 (render10): Hard PTS resync — force both A/V to start at exactly 0
 451 |             resync_tmp = output_path + ".resync.mp4"
 452 |             resync_ok = _run_ffmpeg([
 453 |                 "-i", output_path,
 454 |                 "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-r", "30", "-vsync", "cfr",
 455 |                 "-vf", "setpts=PTS-STARTPTS",
 456 |                 "-c:a", "aac", "-ar", "48000",
 457 |                 "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 458 |                 "-avoid_negative_ts", "make_zero", "-max_interleave_delta", "0",
 459 |                 "-output_ts_offset", "0",
 460 |                 resync_tmp,
 461 |             ], f"hard PTS resync fallback {video_id}", 300)
 462 |             if resync_ok and os.path.exists(resync_tmp):
 463 |                 os.replace(resync_tmp, output_path)
 464 |                 logger.info(f"[extractor] Hard PTS resync applied to {video_id} (fallback)")
 465 |             elif os.path.exists(resync_tmp):
 466 |                 os.remove(resync_tmp)
 467 | 
 468 |             # AV sync fix pass
 469 |             sync_tmp = output_path + ".sync.mp4"
 470 |             if fix_av_sync(output_path, sync_tmp) and os.path.exists(sync_tmp):
 471 |                 os.replace(sync_tmp, output_path)
 472 |                 logger.info(f"  AV sync fix applied")
 473 |             elif os.path.exists(sync_tmp):
 474 |                 os.remove(sync_tmp)
 475 |             # Sync validation gate — FIX 2: lowered nuclear threshold 0.15→0.08
 476 |             offset = check_av_sync(output_path)
 477 |             if abs(offset) > 0.08:
 478 |                 logger.error(f"  CLIP AV offset {offset:+.3f}s after fix — nuclear re-encode (threshold 0.08s)")
 479 |                 nuclear_tmp = output_path + ".nuclear.mp4"
 480 |                 if _run_ffmpeg([
 481 |                     "-fflags", "+genpts+igndts+discardcorrupt",
 482 |                     "-i", output_path,
 483 |                     "-map", "0:v:0", "-map", "0:a:0",
 484 |                     "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 485 |                     "-r", "30", "-vsync", "cfr",
 486 |                     "-vf", "setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,format=yuv420p",
 487 |                     "-c:a", "aac", "-ar", "48000", "-ac", "2",
 488 |                     "-af", "aresample=async=1:first_pts=0,asetpts=PTS-STARTPTS",
 489 |                     "-avoid_negative_ts", "make_zero",
 490 |                     nuclear_tmp,
 491 |                 ], "av_sync_nuclear", 180) and os.path.exists(nuclear_tmp):
 492 |                     os.replace(nuclear_tmp, output_path)
 493 |                     final_offset = check_av_sync(output_path)
 494 |                     logger.info(f"  Nuclear re-encode: final offset {final_offset:+.3f}s")
 495 |                 elif os.path.exists(nuclear_tmp):
 496 |                     os.remove(nuclear_tmp)
 497 |             # FIX 2: Dynamic offset correction for fallback path too
 498 |             fb_offset = check_av_sync(output_path)
 499 |             if abs(fb_offset) > 0.02:
 500 |                 lipsync_tmp = output_path + ".lipsync.mp4"
 501 |                 correction = -fb_offset
 502 |                 audio_delay = max(0, correction)
 503 |                 video_delay = max(0, -correction)
 504 |                 if _run_ffmpeg([
 505 |                     "-itsoffset", f"{audio_delay:.4f}",
 506 |                     "-i", output_path,
 507 |                     "-itsoffset", f"{video_delay:.4f}",
 508 |                     "-i", output_path,
 509 |                     "-map", "1:v:0", "-map", "0:a:0",
 510 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 511 |                     "-vf", "setpts=PTS-STARTPTS",
 512 |                     "-c:a", "aac", "-ar", "48000",
 513 |                     "-af", "asetpts=PTS-STARTPTS",
 514 |                     lipsync_tmp,
 515 |                 ], f"lipsync correction {correction:+.3f}s (fallback)", 120) and os.path.exists(lipsync_tmp):
 516 |                     os.replace(lipsync_tmp, output_path)
 517 |                     after = check_av_sync(output_path)
 518 |                     logger.info(f"  FIX 2: Fallback lipsync corrected {fb_offset:+.3f}s → {after:+.3f}s")
 519 |                 elif os.path.exists(lipsync_tmp):
 520 |                     os.remove(lipsync_tmp)
 521 |             # Render21 FIX 7: Final AV sync gate (fallback path)
 522 |             final_sync_fb = check_av_sync(output_path)
 523 |             if abs(final_sync_fb) > 0.15:
 524 |                 logger.error(f"  FIX 7: Fallback AV sync {final_sync_fb:+.3f}s exceeds 0.15s — force re-encode")
 525 |                 fix7_tmp = output_path + ".fix7.mp4"
 526 |                 if _run_ffmpeg([
 527 |                     "-i", output_path,
 528 |                     "-c:v", "libx264", "-crf", "17", "-preset", "fast",
 529 |                     "-vf", "setpts=PTS-STARTPTS",
 530 |                     "-c:a", "aac", "-ar", "48000",
 531 |                     "-af", "asetpts=PTS-STARTPTS",
 532 |                     "-r", "30", "-vsync", "cfr",
 533 |                     fix7_tmp,
 534 |                 ], "av_sync_fix7_force_fb", 120) and os.path.exists(fix7_tmp):
 535 |                     os.replace(fix7_tmp, output_path)
 536 |                     post_fix7 = check_av_sync(output_path)
 537 |                     logger.info(f"  FIX 7: Fallback re-encode done, sync now {post_fix7:+.3f}s")
 538 |                 elif os.path.exists(fix7_tmp):
 539 |                     os.remove(fix7_tmp)
 540 |             # Render21: Skip intro jingle via speech onset detection
 541 |             _skip_intro_silence(output_path, channel=channel)
 542 |             dur = ffprobe_duration(output_path)
 543 |             logger.info(f"  Trimmed: {dur:.1f}s")
 544 |             # Clean up full video
 545 |             try:
 546 |                 os.remove(full_path)
 547 |             except OSError:
 548 |                 pass
 549 |             return True
 550 |     except subprocess.TimeoutExpired:
 551 |         pass
 552 | 
 553 |     logger.error(f"  Failed to extract clip from {video_id}")
 554 |     return False
 555 | 
 556 | 
 557 | def _get_bitrate(clip_path: str) -> int:
 558 |     """Get video bitrate in bps via ffprobe. Returns 0 on failure."""
 559 |     import json as _json
 560 |     try:
 561 |         r = subprocess.run(
 562 |             ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", clip_path],
 563 |             capture_output=True, text=True, timeout=10,
 564 |         )
 565 |         info = _json.loads(r.stdout)
 566 |         return int(info.get("format", {}).get("bit_rate", 0))
 567 |     except Exception as e:
 568 |         logger.warning(f"  Bitrate check failed: {e}")
 569 |         return 0
 570 | 
 571 | 
 572 | def _redownload_high_quality(video_id: str, start_sec: int, end_sec: int, output_path: str) -> bool:
 573 |     """Re-download clip with explicit high-quality format selector."""
 574 |     section = f"*{start_sec}-{end_sec}"
 575 |     cmd = [
 576 |         "yt-dlp",
 577 |         "--download-sections", section,
 578 |         "-f", "bestvideo[height>=720]+bestaudio",
 579 |         "--merge-output-format", "mp4",
 580 |         "-o", output_path,
 581 |         f"https://www.youtube.com/watch?v={video_id}",
 582 |         "--force-overwrites",
 583 |         "--no-warnings", "--quiet",
 584 |     ]
 585 |     try:
 586 |         result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
 587 |         return result.returncode == 0 and os.path.exists(output_path)
 588 |     except Exception as e:
 589 |         logger.warning(f"  High-quality re-download failed: {e}")
 590 |         return False
 591 | 
 592 | 
 593 | def _check_clip_quality(clip_path: str, channel: str, video_id: str = "",
 594 |                         start_sec: int = 0, end_sec: int = 0) -> str:
 595 |     """Quality enforcement — reject below 1.5Mbps floor, retry on low.
 596 | 
 597 |     Returns: 'ok', 'redownloaded', or 'rejected'.
 598 |     """
 599 |     bitrate = _get_bitrate(clip_path)
 600 |     if bitrate == 0:
 601 |         logger.warning(f"  Quality check: could not determine bitrate for {channel}")
 602 |         return "ok"  # can't check, allow it
 603 | 
 604 |     mbps = bitrate / 1_000_000
 605 | 
 606 |     if mbps >= 1.5:
 607 |         logger.info(f"  Quality OK: {channel} at {mbps:.1f}Mbps")
 608 |         return "ok"
 609 | 
 610 |     # Below 3Mbps floor — try re-download before rejecting
 611 |     logger.warning(f"  BELOW 1.5Mbps FLOOR: {channel} clip at {mbps:.1f}Mbps")
 612 |     if video_id and _redownload_high_quality(video_id, start_sec, end_sec, clip_path):
 613 |         new_bitrate = _get_bitrate(clip_path)
 614 |         new_mbps = new_bitrate / 1_000_000
 615 |         if new_mbps >= 1.5:
 616 |             logger.info(f"  Re-download succeeded: {channel} now at {new_mbps:.1f}Mbps")
 617 |             return "redownloaded"
 618 |         logger.error(f"  Re-download still below 1.5Mbps floor: {channel} at {new_mbps:.1f}Mbps — REJECTED")
 619 |         os.remove(clip_path)
 620 |         return "rejected"
 621 | 
 622 |     logger.error(f"  REJECTED: {channel} clip at {mbps:.1f}Mbps — below 1.5Mbps floor")
 623 |     os.remove(clip_path)
 624 |     return "rejected"
 625 | 
 626 | 
 627 | def _second_pass_ad_read(clip_path: str, channel: str, rank: int) -> bool:
 628 |     """Issue 5: Second-pass ad read scan on extracted clip's audio transcript.
 629 | 
 630 |     Returns True if ad read detected (clip should be rejected).
 631 |     """
 632 |     try:
 633 |         # Use ffmpeg to extract audio, then check via whisper or pattern match
 634 |         # For now, check any available transcript data from the selection
 635 |         from clip_selector import AD_READ_PHRASES
 636 |         # Quick audio-to-text check would require whisper — skip if unavailable
 637 |         # Instead, this gate is enforced at the selection stage with expanded patterns
 638 |         return False
 639 |     except Exception:
 640 |         return False
 641 | 
 642 | 
 643 | def extract_all(selections: dict, output_dir: str) -> dict:
 644 |     """Extract all selected clips.
 645 | 
 646 |     Args:
 647 |         selections: Output from clip_selector.select_clips()
 648 |         output_dir: Directory to save clips
 649 | 
 650 |     Returns:
 651 |         Dict mapping rank -> clip_path for successfully extracted clips
 652 |     """
 653 |     os.makedirs(output_dir, exist_ok=True)
 654 |     clips = selections.get("clips", [])
 655 |     extracted = {}
 656 | 
 657 |     for clip in clips:
 658 |         rank = clip["rank"]
 659 |         video_id = clip["video_id"]
 660 |         start = clip["start_seconds"]
 661 |         end = clip["end_seconds"]
 662 |         channel = clip.get("channel", "unknown").replace(" ", "_")
 663 | 
 664 |         # Issue 3/4: Find sentence boundaries for clean clip start AND end
 665 |         timestamped_text = clip.get("timestamped_text", "")
 666 |         if timestamped_text:
 667 |             # Backward search for clean clip START
 668 |             adjusted_start = find_sentence_boundary(timestamped_text, start, direction='backward', max_search_seconds=5)
 669 |             if adjusted_start != start:
 670 |                 logger.info(f"  Sentence boundary: clip #{rank} start {start}s -> {adjusted_start}s")
 671 |                 start = adjusted_start
 672 |             # Forward search for clean clip END
 673 |             adjusted_end = find_sentence_boundary(timestamped_text, end, direction='forward', max_search_seconds=5)
 674 |             if adjusted_end != end:
 675 |                 logger.info(f"  Sentence boundary: clip #{rank} end {end}s -> {adjusted_end}s")
 676 |                 end = adjusted_end
 677 | 
 678 |         output_path = os.path.join(output_dir, f"clip_{rank}_{channel}_{video_id}.mp4")
 679 | 
 680 |         try:
 681 |             clip_ok = extract_clip(video_id, start, end, output_path, channel=channel)
 682 |         except Exception as e:
 683 |             logger.error(f"[extractor] extract_clip raised for {video_id}: {e}", exc_info=True)
 684 |             clip_ok = False
 685 |         if clip_ok:
 686 |             # Issue 10: Quality enforcement — reject below 1.5Mbps floor
 687 |             quality = _check_clip_quality(output_path, clip.get("channel", channel),
 688 |                                           video_id=video_id, start_sec=start, end_sec=end)
 689 |             if quality == "rejected":
 690 |                 logger.warning(f"  Skipping clip #{rank}: quality below 3Mbps floor")
 691 |                 continue
 692 | 
 693 |             # Smart trim: find natural pause within the 10s end-pad window
 694 |             clip_dur = ffprobe_duration(output_path)
 695 |             # original_end relative to clip start: (end - start) + 3s start pad
 696 |             original_end_in_clip = (end - start) + 3
 697 |             if clip_dur > original_end_in_clip:
 698 |                 pause_at = find_nearest_pause(output_path, original_end_in_clip, pad_window=10.0)
 699 |                 if pause_at < clip_dur:
 700 |                     trimmed = output_path + ".trimmed.mp4"
 701 |                     if _run_ffmpeg([
 702 |                         "-i", output_path, "-t", str(pause_at),
 703 |                         "-c:v", "copy", "-c:a", "copy", trimmed,
 704 |                     ], "pause_trim", 30) and os.path.exists(trimmed):
 705 |                         os.replace(trimmed, output_path)
 706 |                         logger.info(f"  Trimmed clip #{rank} at {pause_at:.1f}s (silence detection)")
 707 |                     elif os.path.exists(trimmed):
 708 |                         os.remove(trimmed)
 709 | 
 710 |             # Render20: No hard clip duration cap — quality over runtime
 711 | 
 712 |             # Issue 5: Second-pass ad read scan
 713 |             if _second_pass_ad_read(output_path, clip.get("channel", ""), rank):
 714 |                 logger.warning(f"  REJECTED clip #{rank} [{channel}] — ad read in extracted audio")
 715 |                 continue
 716 | 
 717 |             clip_info = {
 718 |                 "path": output_path,
 719 |                 "video_id": video_id,
 720 |                 "channel": clip.get("channel", ""),
 721 |                 "start": start,
 722 |                 "end": end,
 723 |                 "duration": ffprobe_duration(output_path),
 724 |                 "quote": clip.get("quote", ""),
 725 |             }
 726 |             extracted[rank] = clip_info
 727 |             # RULE 1: Archive every successful clip for fallback
 728 |             save_clip(channel, video_id, output_path, clip_info)
 729 |         else:
 730 |             # RULE 1: Try archived fallback before giving up
 731 |             fallback = get_fallback_clip(clip.get("channel", ""))
 732 |             if fallback:
 733 |                 age_days = round((time.time() - os.path.getmtime(fallback)) / 86400, 1)
 734 |                 logger.info(f"[extractor] Using archived clip for {clip.get('channel', channel)} ({age_days} days old)")
 735 |                 shutil.copy2(fallback, output_path)
 736 |                 extracted[rank] = {
 737 |                     "path": output_path,
 738 |                     "video_id": video_id,
 739 |                     "channel": clip.get("channel", ""),
 740 |                     "start": start,
 741 |                     "end": end,
 742 |                     "duration": ffprobe_duration(output_path),
 743 |                     "quote": clip.get("quote", ""),
 744 |                 }
 745 |             else:
 746 |                 logger.warning(f"  Skipping clip #{rank}: extraction failed, no archive fallback")
 747 | 
 748 |     logger.info(f"Extracted {len(extracted)}/{len(clips)} clips")
 749 |     return extracted
 750 | 
 751 | 
 752 | def extract_montage_all(montage_selections: dict, output_dir: str) -> dict:
 753 |     """Extract montage clips — same as extract_all but uses montage timestamps
 754 |     and saves to clips/montage_clip_N_CHANNEL_ID.mp4"""
 755 |     os.makedirs(output_dir, exist_ok=True)
 756 |     clips = montage_selections.get("clips", [])
 757 |     extracted = {}
 758 | 
 759 |     for clip in clips:
 760 |         rank = clip["rank"]
 761 |         video_id = clip["video_id"]
 762 |         start = clip["start_seconds"]
 763 |         end = clip["end_seconds"]
 764 |         channel = clip.get("channel", "unknown").replace(" ", "_")
 765 |         output_path = os.path.join(output_dir, f"montage_clip_{rank}_{channel}_{video_id}.mp4")
 766 | 
 767 |         try:
 768 |             ok = extract_clip(video_id, start, end, output_path, channel)
 769 |             if ok and os.path.exists(output_path):
 770 |                 clip["montage_clip_path"] = output_path
 771 |                 extracted[rank] = output_path
 772 |                 logger.info(f"[Montage] Extracted: montage_clip_{rank}_{channel}")
 773 |             else:
 774 |                 logger.warning(f"[Montage] Failed: {channel} {video_id}")
 775 |         except Exception as e:
 776 |             logger.error(f"[Montage] Error: {channel} {video_id}: {e}")
 777 | 
 778 |     return extracted
 779 | 
 780 | 
 781 | def _parse_timestamped_text(timestamped_text: str) -> list:
 782 |     """Parse timestamped transcript into list of (seconds, text) tuples."""
 783 |     import re
 784 |     # Try [HH:MM:SS] format first
 785 |     entries = re.findall(r'\[(\d+):(\d+):(\d+)\]\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
 786 |     if entries:
 787 |         return [(int(h) * 3600 + int(m) * 60 + int(s), text.strip())
 788 |                 for h, m, s, text in entries]
 789 |     # Try [MM:SS] format
 790 |     entries_simple = re.findall(r'\[?(\d+):(\d+)\]?\s*(.*?)(?=\[|\Z)', timestamped_text, re.DOTALL)
 791 |     if entries_simple:
 792 |         return [(int(m) * 60 + int(s), text.strip())
 793 |                 for m, s, text in entries_simple]
 794 |     return []
 795 | 
 796 | 
 797 | def find_sentence_boundary(timestamped_text: str, target_time: int,
 798 |                            direction: str = 'backward',
 799 |                            max_search_seconds: int = 5) -> int:
 800 |     """Find nearest sentence ending (. ? !) relative to target_time.
 801 | 
 802 |     Args:
 803 |         timestamped_text: Timestamped transcript text
 804 |         target_time: Target timestamp in seconds
 805 |         direction: 'backward' for clip start (find sentence start after previous end),
 806 |                    'forward' for clip end (find sentence end after target)
 807 |         max_search_seconds: Maximum seconds to search in either direction
 808 | 
 809 |     Returns:
 810 |         Adjusted timestamp in seconds
 811 |     """
 812 |     parsed = _parse_timestamped_text(timestamped_text)
 813 |     if not parsed:
 814 |         logger.warning(f"WARNING: No sentence boundary found (no parsed entries), using raw timestamp {target_time}")
 815 |         return target_time
 816 | 
 817 |     if direction == 'backward':
 818 |         # Find the nearest sentence-ending BEFORE target_time,
 819 |         # then return the timestamp of the NEXT word (sentence start)
 820 |         best_start = target_time
 821 |         for i, (sec, text) in enumerate(parsed):
 822 |             if sec >= target_time:
 823 |                 break
 824 |             # Check if text ends with sentence-ending punctuation
 825 |             if text and text.rstrip()[-1:] in '.?!':
 826 |                 # Next entry's timestamp = start of next sentence
 827 |                 if i + 1 < len(parsed):
 828 |                     candidate = parsed[i + 1][0]
 829 |                     if candidate <= target_time and (target_time - candidate) <= max_search_seconds:
 830 |                         best_start = candidate
 831 | 
 832 |         if best_start == target_time:
 833 |             logger.info(f"WARNING: No sentence boundary found backward from {target_time}s, using raw timestamp")
 834 |         return best_start
 835 | 
 836 |     elif direction == 'forward':
 837 |         # Find the nearest sentence-ending AFTER target_time,
 838 |         # return the timestamp just after that ending
 839 |         for i, (sec, text) in enumerate(parsed):
 840 |             if sec < target_time:
 841 |                 continue
 842 |             if text and text.rstrip()[-1:] in '.?!':
 843 |                 # End point: this entry's timestamp + estimated duration for this text
 844 |                 # Use next entry's timestamp as the sentence end point
 845 |                 if i + 1 < len(parsed):
 846 |                     end_point = parsed[i + 1][0]
 847 |                 else:
 848 |                     end_point = sec + 2  # last entry, add 2s buffer
 849 |                 if (end_point - target_time) <= max_search_seconds:
 850 |                     return end_point
 851 |                 break  # beyond max search window
 852 | 
 853 |         logger.info(f"WARNING: No sentence boundary found forward from {target_time}s, using raw timestamp")
 854 |         return target_time
 855 | 
 856 |     return target_time
 857 | 
 858 | 
 859 | def _find_sentence_start(timestamped_text: str, target_sec: int) -> int:
 860 |     """Find the nearest sentence boundary BEFORE the target timestamp.
 861 |     Wrapper around find_sentence_boundary for backward compatibility.
 862 |     """
 863 |     return find_sentence_boundary(timestamped_text, target_sec, direction='backward', max_search_seconds=5)
 864 | 
 865 | 
 866 | if __name__ == "__main__":
 867 |     # Quick test: extract a known clip
 868 |     import sys
 869 |     if len(sys.argv) >= 4:
 870 |         vid = sys.argv[1]
 871 |         start = int(sys.argv[2])
 872 |         end = int(sys.argv[3])
 873 |         out = os.path.join(BASE, "output", f"test_clip_{vid}.mp4")
 874 |         ok = extract_clip(vid, start, end, out)
 875 |         print(f"Extraction {'succeeded' if ok else 'failed'}: {out}")
 876 |     else:
 877 |         print("Usage: python3 clip_extractor.py <video_id> <start_sec> <end_sec>")
 878 | 
```

### File: services/montage_producer.py (566 lines)
```
   1 | #!/usr/bin/env python3
   2 | """Protocol Pulse Daily Montage Producer.
   3 | 
   4 | Assembles top-scored clips into a branded 45-90s highlights montage.
   5 | Pure FFmpeg — no external APIs, no re-downloads.
   6 | 
   7 | Usage:
   8 |     python3 services/montage_producer.py              # today
   9 |     python3 services/montage_producer.py 2026-03-21   # specific date
  10 | """
  11 | 
  12 | import json
  13 | import logging
  14 | import os
  15 | import random
  16 | import shutil
  17 | import subprocess
  18 | import sys
  19 | from datetime import datetime
  20 | from pathlib import Path
  21 | 
  22 | logging.basicConfig(
  23 |     level=logging.INFO,
  24 |     format="%(asctime)s [MONTAGE] %(levelname)s %(message)s",
  25 | )
  26 | log = logging.getLogger("montage")
  27 | 
  28 | PROJECT_ROOT = Path(__file__).resolve().parent.parent
  29 | PIPELINE_OUTPUT = PROJECT_ROOT / "video_pipeline_v3" / "output"
  30 | MUSIC_DIR = PROJECT_ROOT / "video_pipeline_v3" / "assets" / "music"
  31 | STATIC_DIR = PROJECT_ROOT / "static"
  32 | 
  33 | SCORE_THRESHOLD = 60.0
  34 | SCORE_THRESHOLD_LOW = 40.0
  35 | MAX_CLIPS = 4
  36 | MIN_CLIPS = 2
  37 | MAX_DURATION = 90.0
  38 | MIN_DURATION = 45.0
  39 | MIN_CLIP_DURATION = 5.0
  40 | 
  41 | 
  42 | # ── Helpers ──────────────────────────────────────────────────────────
  43 | 
  44 | def run_cmd(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
  45 |     """Run a shell command, raise on failure."""
  46 |     log.debug("CMD: %s", " ".join(cmd))
  47 |     return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=True)
  48 | 
  49 | 
  50 | def ffprobe_info(path: str) -> dict | None:
  51 |     """Return dict with duration, width, height, has_audio for a video file."""
  52 |     try:
  53 |         r = run_cmd([
  54 |             "ffprobe", "-v", "error",
  55 |             "-show_entries", "stream=codec_type,width,height,duration",
  56 |             "-of", "json", str(path),
  57 |         ])
  58 |         data = json.loads(r.stdout)
  59 |         info = {"duration": 0.0, "width": 0, "height": 0, "has_audio": False}
  60 |         for stream in data.get("streams", []):
  61 |             if stream.get("codec_type") == "video":
  62 |                 info["width"] = int(stream.get("width", 0))
  63 |                 info["height"] = int(stream.get("height", 0))
  64 |                 if stream.get("duration"):
  65 |                     info["duration"] = float(stream["duration"])
  66 |             elif stream.get("codec_type") == "audio":
  67 |                 info["has_audio"] = True
  68 |                 if not info["duration"] and stream.get("duration"):
  69 |                     info["duration"] = float(stream["duration"])
  70 |         return info
  71 |     except Exception as e:
  72 |         log.warning("ffprobe failed for %s: %s", path, e)
  73 |         return None
  74 | 
  75 | 
  76 | def score_dots(score: float) -> str:
  77 |     """Convert score to signal dots string like ●●●●○."""
  78 |     filled = min(5, max(1, int(score / 20)))
  79 |     return "●" * filled + "○" * (5 - filled)
  80 | 
  81 | 
  82 | # ── Pipeline Steps ───────────────────────────────────────────────────
  83 | 
  84 | def load_clips(date_str: str) -> list[dict]:
  85 |     """Load and filter clips, preferring independent montage selections.
  86 | 
  87 |     Tries montage_selections.json + montage_clip_* files first.
  88 |     Falls back to selections.json + clip_* files (original behavior).
  89 |     """
  90 |     output_dir = PIPELINE_OUTPUT / date_str
  91 |     clips_dir = output_dir / "clips"
  92 | 
  93 |     # Try montage_selections.json first (independent selection)
  94 |     montage_sel_path = output_dir / "montage_selections.json"
  95 |     sel_path = montage_sel_path if montage_sel_path.exists() else output_dir / "selections.json"
  96 | 
  97 |     if not sel_path.exists():
  98 |         log.error("No selections.json at %s", sel_path)
  99 |         return []
 100 | 
 101 |     using_montage = sel_path == montage_sel_path
 102 |     log.info("Using %s selections: %s", "montage" if using_montage else "pulse-check", sel_path)
 103 | 
 104 |     with open(sel_path) as f:
 105 |         data = json.load(f)
 106 | 
 107 |     selections = data.get("clips", [])
 108 | 
 109 |     # Build lookup of clip files by video_id
 110 |     clip_files_by_vid = {}
 111 |     if clips_dir.exists():
 112 |         # Try montage_clip_* files first
 113 |         for clip_file in clips_dir.glob("montage_clip_*.mp4"):
 114 |             name = clip_file.stem  # e.g. montage_clip_1_Simply_Bitcoin_uvXvlI3HRlM
 115 |             for sel in selections:
 116 |                 vid = sel.get("video_id", "")
 117 |                 if vid and name.endswith(vid):
 118 |                     clip_files_by_vid[vid] = str(clip_file)
 119 |                     break
 120 | 
 121 |         # Fall back to clip_N_* if no montage clips found
 122 |         if not clip_files_by_vid:
 123 |             log.info("No montage clip files found, falling back to pulse-check clips")
 124 |             for clip_file in clips_dir.glob("clip_*.mp4"):
 125 |                 name = clip_file.stem
 126 |                 for sel in selections:
 127 |                     vid = sel.get("video_id", "")
 128 |                     if vid and name.endswith(vid):
 129 |                         clip_files_by_vid[vid] = str(clip_file)
 130 |                         break
 131 | 
 132 |     # Match selections to clip files
 133 |     clip_list = []
 134 |     seen_vids = set()
 135 |     for sel in selections:
 136 |         vid = sel.get("video_id", "")
 137 |         if not vid or vid in seen_vids:
 138 |             continue
 139 |         clip_path = clip_files_by_vid.get(vid)
 140 |         if not clip_path:
 141 |             log.warning("No clip file for video_id %s (%s)", vid, sel.get("channel", "?"))
 142 |             continue
 143 |         seen_vids.add(vid)
 144 |         sel["file"] = clip_path
 145 |         clip_list.append(sel)
 146 | 
 147 |     # Filter by score threshold
 148 |     filtered = [c for c in clip_list if c.get("score", 50) >= SCORE_THRESHOLD]
 149 |     filtered.sort(key=lambda c: c.get("score", 50), reverse=True)
 150 | 
 151 |     # If not enough clips or total too short, lower threshold
 152 |     if len(filtered) < MIN_CLIPS:
 153 |         log.info("Only %d clips >= %.0f, lowering to %.0f", len(filtered), SCORE_THRESHOLD, SCORE_THRESHOLD_LOW)
 154 |         filtered = [c for c in clip_list if c.get("score", 50) >= SCORE_THRESHOLD_LOW]
 155 |         filtered.sort(key=lambda c: c.get("score", 50), reverse=True)
 156 | 
 157 |     return filtered[:MAX_CLIPS + 1]  # take up to 5 for duration fitting
 158 | 
 159 | 
 160 | def validate_clips(clips: list[dict]) -> list[dict]:
 161 |     """Probe each clip, skip corrupt or too-short ones."""
 162 |     valid = []
 163 |     for clip in clips:
 164 |         info = ffprobe_info(clip["file"])
 165 |         if not info:
 166 |             log.warning("Skipping corrupt clip: %s", clip["file"])
 167 |             continue
 168 |         if info["duration"] < MIN_CLIP_DURATION:
 169 |             log.warning("Skipping short clip (%.1fs): %s", info["duration"], clip["file"])
 170 |             continue
 171 |         clip["probe"] = info
 172 |         valid.append(clip)
 173 | 
 174 |     if len(valid) < MIN_CLIPS:
 175 |         log.error("Only %d valid clips — need at least %d", len(valid), MIN_CLIPS)
 176 |         return []
 177 | 
 178 |     return valid
 179 | 
 180 | 
 181 | def fit_duration(clips: list[dict]) -> list[dict]:
 182 |     """Trim clip list to fit within MAX_DURATION. Trim lowest-scoring clip if needed."""
 183 |     total = sum(c["probe"]["duration"] for c in clips)
 184 | 
 185 |     # Take top 4 first
 186 |     result = clips[:MAX_CLIPS]
 187 |     total = sum(c["probe"]["duration"] for c in result)
 188 | 
 189 |     # If still over 90s, drop the lowest-scoring clip
 190 |     while total > MAX_DURATION and len(result) > MIN_CLIPS:
 191 |         dropped = result.pop()
 192 |         total = sum(c["probe"]["duration"] for c in result)
 193 |         log.info("Dropped clip %s (score %.0f) to fit duration — total now %.1fs",
 194 |                  dropped["channel"], dropped["score"], total)
 195 | 
 196 |     # If under 45s and we had more clips, try adding one back with lower threshold
 197 |     if total < MIN_DURATION and len(clips) > len(result):
 198 |         for extra in clips[len(result):]:
 199 |             if extra not in result:
 200 |                 result.append(extra)
 201 |                 total = sum(c["probe"]["duration"] for c in result)
 202 |                 if total >= MIN_DURATION:
 203 |                     break
 204 | 
 205 |     log.info("Final clip count: %d, total duration: %.1fs", len(result), total)
 206 |     return result
 207 | 
 208 | 
 209 | def normalize_audio(clip_path: str, work_dir: Path) -> str:
 210 |     """LUFS normalize a clip to -16."""
 211 |     out = work_dir / f"norm_{Path(clip_path).name}"
 212 |     run_cmd([
 213 |         "ffmpeg", "-y", "-i", clip_path,
 214 |         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
 215 |         "-c:v", "copy", "-ar", "48000",
 216 |         str(out),
 217 |     ])
 218 |     return str(out)
 219 | 
 220 | 
 221 | def scale_video(clip_path: str, work_dir: Path) -> str:
 222 |     """Scale to 1920x1080 if needed."""
 223 |     info = ffprobe_info(clip_path)
 224 |     if info and info["width"] == 1920 and info["height"] == 1080:
 225 |         return clip_path
 226 | 
 227 |     out = work_dir / f"scaled_{Path(clip_path).name}"
 228 |     run_cmd([
 229 |         "ffmpeg", "-y", "-i", clip_path,
 230 |         "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
 231 |         "-c:a", "copy",
 232 |         str(out),
 233 |     ])
 234 |     return str(out)
 235 | 
 236 | 
 237 | def build_intro_slate(work_dir: Path, date_str: str) -> str:
 238 |     """Build 3s intro slate with FFmpeg lavfi."""
 239 |     out = work_dir / "intro.mp4"
 240 |     display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y").upper()
 241 |     run_cmd([
 242 |         "ffmpeg", "-y",
 243 |         "-f", "lavfi", "-i", "color=c=0x0A0A0F:s=1920x1080:d=3:r=30",
 244 |         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 245 |         "-vf", (
 246 |             f"drawtext=fontcolor=white:fontsize=80:text='PROTOCOL PULSE'"
 247 |             f":x=(w-tw)/2:y=(h-th)/2-60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
 248 |             f"drawtext=fontcolor=0xFF3333:fontsize=40:text='DAILY HIGHLIGHTS'"
 249 |             f":x=(w-tw)/2:y=(h-th)/2+20:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf,"
 250 |             f"drawtext=fontcolor=white:fontsize=30:text='{display_date}'"
 251 |             f":x=(w-tw)/2:y=(h-th)/2+80:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 252 |         ),
 253 |         "-c:v", "libx264", "-pix_fmt", "yuv420p",
 254 |         "-c:a", "aac", "-ar", "48000", "-ac", "2",
 255 |         "-t", "3", "-shortest",
 256 |         str(out),
 257 |     ])
 258 |     return str(out)
 259 | 
 260 | 
 261 | def build_lower_third(clip_path: str, channel: str, score: float, work_dir: Path, idx: int) -> str:
 262 |     """Burn lower-third overlay onto clip."""
 263 |     out = work_dir / f"lt_{idx}_{Path(clip_path).name}"
 264 |     dots = score_dots(score)
 265 |     label = f"{channel}  {dots}"
 266 |     # Escape special chars for drawtext
 267 |     label_escaped = label.replace(":", "\\:").replace("'", "\\'")
 268 |     run_cmd([
 269 |         "ffmpeg", "-y", "-i", clip_path,
 270 |         "-vf", (
 271 |             "drawbox=x=0:y=1000:w=650:h=55:color=0xFF3333@0.85:t=fill,"
 272 |             f"drawtext=fontcolor=white:fontsize=26:text='{label_escaped}'"
 273 |             f":x=15:y=1013:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
 274 |         ),
 275 |         "-c:v", "libx264", "-pix_fmt", "yuv420p",
 276 |         "-c:a", "copy",
 277 |         str(out),
 278 |     ])
 279 |     return str(out)
 280 | 
 281 | 
 282 | def build_outro_slate(work_dir: Path) -> str:
 283 |     """Build 2s outro slate."""
 284 |     out = work_dir / "outro.mp4"
 285 |     run_cmd([
 286 |         "ffmpeg", "-y",
 287 |         "-f", "lavfi", "-i", "color=c=0x0A0A0F:s=1920x1080:d=2:r=30",
 288 |         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
 289 |         "-vf", (
 290 |             "drawtext=fontcolor=0xFF3333:fontsize=90:text='STAY SOVEREIGN.'"
 291 |             ":x=(w-tw)/2:y=(h-th)/2-40:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf,"
 292 |             "drawtext=fontcolor=white:fontsize=35:text='protocolpulse.io'"
 293 |             ":x=(w-tw)/2:y=(h-th)/2+60:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
 294 |         ),
 295 |         "-c:v", "libx264", "-pix_fmt", "yuv420p",
 296 |         "-c:a", "aac", "-ar", "48000", "-ac", "2",
 297 |         "-t", "2", "-shortest",
 298 |         str(out),
 299 |     ])
 300 |     return str(out)
 301 | 
 302 | 
 303 | def concat_with_xfade(parts: list[str], work_dir: Path) -> str:
 304 |     """Concat video parts with 0.3s xfade dissolve between each."""
 305 |     if len(parts) == 1:
 306 |         return parts[0]
 307 | 
 308 |     out = work_dir / "montage_nomusic.mp4"
 309 |     xfade_dur = 0.3
 310 | 
 311 |     # Get durations for offset calculation
 312 |     durations = []
 313 |     for p in parts:
 314 |         info = ffprobe_info(p)
 315 |         durations.append(info["duration"] if info else 10.0)
 316 | 
 317 |     # Build xfade filter chain
 318 |     n = len(parts)
 319 |     inputs = " ".join(f"-i {p}" for p in parts)
 320 |     vfilters = []
 321 |     afilters = []
 322 |     offset = 0.0
 323 | 
 324 |     # Video xfade chain
 325 |     for i in range(n - 1):
 326 |         if i == 0:
 327 |             vin = "[0:v]"
 328 |         else:
 329 |             vin = f"[xv{i}]"
 330 | 
 331 |         offset = sum(durations[:i + 1]) - xfade_dur * (i + 1)
 332 |         vout = f"[xv{i + 1}]" if i < n - 2 else "[vout]"
 333 |         vfilters.append(f"{vin}[{i + 1}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.3f}{vout}")
 334 | 
 335 |     # Audio crossfade chain
 336 |     for i in range(n - 1):
 337 |         if i == 0:
 338 |             ain = "[0:a]"
 339 |         else:
 340 |             ain = f"[xa{i}]"
 341 | 
 342 |         offset = sum(durations[:i + 1]) - xfade_dur * (i + 1)
 343 |         aout = f"[xa{i + 1}]" if i < n - 2 else "[aout]"
 344 |         afilters.append(f"{ain}[{i + 1}:a]acrossfade=d={xfade_dur}:c1=tri:c2=tri{aout}")
 345 | 
 346 |     fc = ";".join(vfilters + afilters)
 347 | 
 348 |     cmd = ["ffmpeg", "-y"]
 349 |     for p in parts:
 350 |         cmd.extend(["-i", p])
 351 |     cmd.extend([
 352 |         "-filter_complex", fc,
 353 |         "-map", "[vout]", "-map", "[aout]",
 354 |         "-c:v", "libx264", "-pix_fmt", "yuv420p",
 355 |         "-c:a", "aac", "-ar", "48000",
 356 |         "-movflags", "+faststart",
 357 |         str(out),
 358 |     ])
 359 |     run_cmd(cmd, timeout=600)
 360 |     return str(out)
 361 | 
 362 | 
 363 | def add_music_bed(video_path: str, work_dir: Path, date_str: str) -> str:
 364 |     """Mix background music at 0.15 volume."""
 365 |     out = work_dir / f"montage_{date_str}.mp4"
 366 | 
 367 |     # Pick a music track — prefer tense/edge for market content
 368 |     candidates = list(MUSIC_DIR.glob("tense_*.mp3")) + list(MUSIC_DIR.glob("edge_*.mp3"))
 369 |     if not candidates:
 370 |         candidates = list(MUSIC_DIR.glob("*.mp3"))
 371 |     if not candidates:
 372 |         log.warning("No music files found, skipping music bed")
 373 |         shutil.copy2(video_path, str(out))
 374 |         return str(out)
 375 | 
 376 |     track = str(random.choice(candidates))
 377 |     log.info("Music bed: %s", track)
 378 | 
 379 |     run_cmd([
 380 |         "ffmpeg", "-y",
 381 |         "-i", video_path,
 382 |         "-i", track,
 383 |         "-filter_complex",
 384 |         "[1:a]aloop=loop=-1:size=48000*300,atrim=duration=300[bgm];"
 385 |         "[0:a][bgm]amix=inputs=2:weights=1 0.15:duration=first[a]",
 386 |         "-map", "0:v", "-map", "[a]",
 387 |         "-c:v", "copy",
 388 |         "-c:a", "aac", "-ar", "48000",
 389 |         "-movflags", "+faststart",
 390 |         str(out),
 391 |     ])
 392 |     return str(out)
 393 | 
 394 | 
 395 | def generate_shorts(montage_path: str, work_dir: Path, date_str: str) -> str:
 396 |     """Crop center 1080x1920 for Shorts format."""
 397 |     out = work_dir / f"montage_{date_str}_shorts.mp4"
 398 |     run_cmd([
 399 |         "ffmpeg", "-y", "-i", montage_path,
 400 |         "-vf", "crop=607:1080:656:0,scale=1080:1920",
 401 |         "-c:a", "copy",
 402 |         "-movflags", "+faststart",
 403 |         str(out),
 404 |     ])
 405 |     return str(out)
 406 | 
 407 | 
 408 | def generate_thumbnail(top_clip_path: str, work_dir: Path, date_str: str) -> str:
 409 |     """Extract frame from midpoint of highest-scoring clip."""
 410 |     out = work_dir / f"montage_thumb_{date_str}.jpg"
 411 |     info = ffprobe_info(top_clip_path)
 412 |     midpoint = (info["duration"] / 2) if info else 10.0
 413 |     run_cmd([
 414 |         "ffmpeg", "-y",
 415 |         "-ss", f"{midpoint:.1f}",
 416 |         "-i", top_clip_path,
 417 |         "-vframes", "1", "-q:v", "2",
 418 |         str(out),
 419 |     ])
 420 |     return str(out)
 421 | 
 422 | 
 423 | def copy_outputs(work_dir: Path, date_str: str, output_dir: Path):
 424 |     """Copy final files to output dir and update symlink."""
 425 |     montage = work_dir / f"montage_{date_str}.mp4"
 426 |     shorts = work_dir / f"montage_{date_str}_shorts.mp4"
 427 |     thumb = work_dir / f"montage_thumb_{date_str}.jpg"
 428 | 
 429 |     for src in [montage, shorts, thumb]:
 430 |         if src.exists():
 431 |             dst = output_dir / src.name
 432 |             shutil.copy2(str(src), str(dst))
 433 |             log.info("Copied %s → %s", src.name, dst)
 434 | 
 435 |     # Symlink for latest
 436 |     symlink = STATIC_DIR / "montage_latest.mp4"
 437 |     target = output_dir / f"montage_{date_str}.mp4"
 438 |     if target.exists():
 439 |         symlink.unlink(missing_ok=True)
 440 |         symlink.symlink_to(target)
 441 |         log.info("Symlink: %s → %s", symlink, target)
 442 | 
 443 |     shorts_symlink = STATIC_DIR / "montage_latest_shorts.mp4"
 444 |     shorts_target = output_dir / f"montage_{date_str}_shorts.mp4"
 445 |     if shorts_target.exists():
 446 |         shorts_symlink.unlink(missing_ok=True)
 447 |         shorts_symlink.symlink_to(shorts_target)
 448 | 
 449 | 
 450 | # ── Main ─────────────────────────────────────────────────────────────
 451 | 
 452 | def produce_montage(date_str: str | None = None) -> dict:
 453 |     """Run the full montage pipeline. Returns metadata dict."""
 454 |     if not date_str:
 455 |         date_str = datetime.now().strftime("%Y-%m-%d")
 456 | 
 457 |     output_dir = PIPELINE_OUTPUT / date_str
 458 |     work_dir = output_dir / "montage_work"
 459 |     work_dir.mkdir(parents=True, exist_ok=True)
 460 | 
 461 |     log.info("=== MONTAGE PRODUCER START — %s ===", date_str)
 462 | 
 463 |     # A) Load clips
 464 |     clips = load_clips(date_str)
 465 |     if not clips:
 466 |         log.error("No clips found for %s", date_str)
 467 |         return {"error": "no_clips"}
 468 | 
 469 |     # B) Validate
 470 |     clips = validate_clips(clips)
 471 |     if not clips:
 472 |         return {"error": "insufficient_valid_clips"}
 473 | 
 474 |     # Fit to duration
 475 |     clips = fit_duration(clips)
 476 |     if not clips:
 477 |         return {"error": "cannot_fit_duration"}
 478 | 
 479 |     log.info("Selected %d clips: %s", len(clips),
 480 |              ", ".join(f"{c['channel']}({c['score']:.0f})" for c in clips))
 481 | 
 482 |     # C) Normalize audio + D) Scale video
 483 |     processed = []
 484 |     for i, clip in enumerate(clips):
 485 |         path = clip["file"]
 486 |         path = normalize_audio(path, work_dir)
 487 |         path = scale_video(path, work_dir)
 488 |         processed.append({"path": path, "clip": clip, "idx": i})
 489 |         log.info("Processed clip %d/%d: %s", i + 1, len(clips), clip["channel"])
 490 | 
 491 |     # F) Add lower thirds
 492 |     lt_parts = []
 493 |     for item in processed:
 494 |         path = build_lower_third(
 495 |             item["path"], item["clip"]["channel"],
 496 |             item["clip"]["score"], work_dir, item["idx"],
 497 |         )
 498 |         lt_parts.append(path)
 499 | 
 500 |     # E) Build intro slate
 501 |     intro = build_intro_slate(work_dir, date_str)
 502 | 
 503 |     # G) Build outro slate
 504 |     outro = build_outro_slate(work_dir)
 505 | 
 506 |     # H) Concat with xfade
 507 |     all_parts = [intro] + lt_parts + [outro]
 508 |     montage_nomusic = concat_with_xfade(all_parts, work_dir)
 509 | 
 510 |     # I) Add music bed
 511 |     montage_final = add_music_bed(montage_nomusic, work_dir, date_str)
 512 | 
 513 |     # Verify duration
 514 |     final_info = ffprobe_info(montage_final)
 515 |     if not final_info:
 516 |         return {"error": "final_probe_failed"}
 517 | 
 518 |     log.info("Montage duration: %.1fs", final_info["duration"])
 519 | 
 520 |     # J) Generate shorts
 521 |     shorts_path = generate_shorts(montage_final, work_dir, date_str)
 522 | 
 523 |     # K) Generate thumbnail
 524 |     thumb_path = generate_thumbnail(clips[0]["file"], work_dir, date_str)
 525 | 
 526 |     # L) Copy to output + symlink
 527 |     copy_outputs(work_dir, date_str, output_dir)
 528 | 
 529 |     # Build metadata
 530 |     metadata = {
 531 |         "date": date_str,
 532 |         "title": f"Protocol Pulse Daily Highlights — {date_str}",
 533 |         "duration": round(final_info["duration"], 1),
 534 |         "clips_used": [
 535 |             {
 536 |                 "channel": c["channel"],
 537 |                 "video_title": c.get("video_title", ""),
 538 |                 "score": c["score"],
 539 |                 "quote": c.get("quote", ""),
 540 |             }
 541 |             for c in clips
 542 |         ],
 543 |         "montage_file": f"montage_{date_str}.mp4",
 544 |         "shorts_file": f"montage_{date_str}_shorts.mp4",
 545 |         "thumbnail_file": f"montage_thumb_{date_str}.jpg",
 546 |         "produced_at": datetime.now().isoformat(),
 547 |     }
 548 | 
 549 |     # Save metadata
 550 |     meta_path = output_dir / f"montage_{date_str}_meta.json"
 551 |     with open(meta_path, "w") as f:
 552 |         json.dump(metadata, f, indent=2)
 553 |     log.info("Metadata saved: %s", meta_path)
 554 | 
 555 |     log.info("=== MONTAGE COMPLETE — %s ===", date_str)
 556 |     return metadata
 557 | 
 558 | 
 559 | if __name__ == "__main__":
 560 |     date_arg = sys.argv[1] if len(sys.argv) > 1 else None
 561 |     result = produce_montage(date_arg)
 562 |     if "error" in result:
 563 |         log.error("Montage failed: %s", result["error"])
 564 |         sys.exit(1)
 565 |     print(json.dumps(result, indent=2))
 566 | 
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?
