# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: stage-fix
# Branch: main
# Generated: 2026-03-24 19:36 UTC
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

### File: services/stage_brief_pipeline.py (827 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Stage Brief Pipeline — 3x/day Oracle Stage brief generation with intel extraction.
   4 | 
   5 | Schedule: 06:00 UTC (morning), 14:00 UTC (midday), 22:00 UTC (evening)
   6 | 
   7 | Pipeline:
   8 | 1. Fetch live BTC data (price, mempool, hashrate, FNG, block height)
   9 | 2. Generate brief script via Claude Haiku
  10 | 3. Generate audio via Chatterbox TTS (avatar server /oracle/voice)
  11 | 4. Render avatar video via Wav2Lip (avatar server /generate)
  12 | 5. Save to video_pipeline_v3/data/stage_briefs/ + update latest.json
  13 | 6. Intel extraction: social clips, newsletter hook, sentiment signal,
  14 |    article seeds, oracle context — single Claude Haiku batch call
  15 | 7. Log to logs/brief_pipeline.log
  16 | """
  17 | 
  18 | import base64
  19 | import json
  20 | import logging
  21 | import os
  22 | import re
  23 | import shutil
  24 | import subprocess
  25 | import sys
  26 | import tempfile
  27 | import time
  28 | from datetime import datetime, timezone
  29 | 
  30 | import requests
  31 | 
  32 | # ---------------------------------------------------------------------------
  33 | # Paths
  34 | # ---------------------------------------------------------------------------
  35 | 
  36 | BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  37 | BRIEFS_DIR = os.path.join(BASE, "video_pipeline_v3", "data", "stage_briefs")
  38 | LOGS_DIR = os.path.join(BASE, "logs")
  39 | DATA_DIR = os.path.join(BASE, "data")
  40 | 
  41 | AVATAR_BASE = os.environ.get("AVATAR_BASE_URL", "http://localhost:8200")
  42 | CLAUDE_MODEL = "claude-haiku-4-5-20251001"
  43 | 
  44 | # ---------------------------------------------------------------------------
  45 | # Logging
  46 | # ---------------------------------------------------------------------------
  47 | 
  48 | os.makedirs(LOGS_DIR, exist_ok=True)
  49 | 
  50 | logger = logging.getLogger("stage_brief_pipeline")
  51 | logger.setLevel(logging.INFO)
  52 | 
  53 | _fh = logging.FileHandler(os.path.join(LOGS_DIR, "brief_pipeline.log"))
  54 | _fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
  55 | logger.addHandler(_fh)
  56 | 
  57 | _sh = logging.StreamHandler()
  58 | _sh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
  59 | logger.addHandler(_sh)
  60 | 
  61 | # ---------------------------------------------------------------------------
  62 | # Brief type labels
  63 | # ---------------------------------------------------------------------------
  64 | 
  65 | BRIEF_TYPES = {
  66 |     6: "morning",    # 06:00 UTC
  67 |     14: "midday",    # 14:00 UTC
  68 |     22: "evening",   # 22:00 UTC
  69 | }
  70 | 
  71 | BRIEF_SYSTEM_PROMPTS = {
  72 |     "morning": (
  73 |         "You are Oracle, a Bitcoin intelligence reporter delivering the morning brief. "
  74 |         "Cover overnight developments, Asia session moves, and what to watch for the day ahead. "
  75 |         "Write a punchy 90-second spoken brief (max 200 words). PBX voice: direct, confident, "
  76 |         "no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
  77 |     ),
  78 |     "midday": (
  79 |         "You are Oracle, a Bitcoin intelligence reporter delivering the midday brief. "
  80 |         "Cover US morning session action, any breaking news, and key on-chain signals. "
  81 |         "Write a punchy 90-second spoken brief (max 200 words). PBX voice: direct, confident, "
  82 |         "no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
  83 |     ),
  84 |     "evening": (
  85 |         "You are Oracle, a Bitcoin intelligence reporter delivering the evening brief. "
  86 |         "Wrap the day: US close action, daily high/low, key takeaways, what to watch overnight. "
  87 |         "Write a punchy 90-second spoken brief (max 200 words). PBX voice: direct, confident, "
  88 |         "no fluff. No 'Hello' or 'Welcome'. Start with the strongest insight."
  89 |     ),
  90 | }
  91 | 
  92 | # ---------------------------------------------------------------------------
  93 | # Data Gathering (standalone, no relay dependency)
  94 | # ---------------------------------------------------------------------------
  95 | 
  96 | def _fetch_btc_price():
  97 |     try:
  98 |         r = requests.get(
  99 |             "https://api.coingecko.com/api/v3/simple/price",
 100 |             params={"ids": "bitcoin", "vs_currencies": "usd",
 101 |                     "include_24hr_change": "true", "include_market_cap": "true",
 102 |                     "include_24hr_vol": "true"},
 103 |             timeout=10,
 104 |         )
 105 |         r.raise_for_status()
 106 |         d = r.json()["bitcoin"]
 107 |         return {
 108 |             "price": d["usd"],
 109 |             "change_24h": round(d.get("usd_24h_change", 0), 2),
 110 |             "market_cap": d.get("usd_market_cap", 0),
 111 |             "volume_24h": d.get("usd_24h_vol", 0),
 112 |         }
 113 |     except Exception as e:
 114 |         logger.warning("BTC price fetch failed: %s", e)
 115 |         return {"price": 0, "change_24h": 0, "market_cap": 0, "volume_24h": 0}
 116 | 
 117 | 
 118 | def _fetch_mempool():
 119 |     result = {"fastest_fee": 0, "half_hour_fee": 0, "hour_fee": 0,
 120 |               "economy_fee": 0, "tx_count": 0, "vsize": 0}
 121 |     try:
 122 |         r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
 123 |         r.raise_for_status()
 124 |         fees = r.json()
 125 |         result["fastest_fee"] = fees.get("fastestFee", 0)
 126 |         result["half_hour_fee"] = fees.get("halfHourFee", 0)
 127 |         result["hour_fee"] = fees.get("hourFee", 0)
 128 |         result["economy_fee"] = fees.get("economyFee", 0)
 129 |     except Exception as e:
 130 |         logger.warning("Fee fetch failed: %s", e)
 131 |     try:
 132 |         r = requests.get("https://mempool.space/api/mempool", timeout=10)
 133 |         r.raise_for_status()
 134 |         mp = r.json()
 135 |         result["tx_count"] = mp.get("count", 0)
 136 |         result["vsize"] = mp.get("vsize", 0)
 137 |     except Exception as e:
 138 |         logger.warning("Mempool fetch failed: %s", e)
 139 |     return result
 140 | 
 141 | 
 142 | def _fetch_fear_greed():
 143 |     try:
 144 |         r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
 145 |         r.raise_for_status()
 146 |         d = r.json()["data"][0]
 147 |         return {"value": int(d["value"]), "label": d["value_classification"]}
 148 |     except Exception as e:
 149 |         logger.warning("FNG fetch failed: %s", e)
 150 |         return {"value": 50, "label": "Neutral"}
 151 | 
 152 | 
 153 | def _fetch_hashrate():
 154 |     try:
 155 |         r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=15)
 156 |         r.raise_for_status()
 157 |         data = r.json()
 158 |         hr = data.get("hashrates", [])
 159 |         current_hr = hr[-1]["avgHashrate"] if hr else 0
 160 |         return {"hashrate_eh": round(current_hr / 1e18, 1)}
 161 |     except Exception as e:
 162 |         logger.warning("Hashrate fetch failed: %s", e)
 163 |         return {"hashrate_eh": 0}
 164 | 
 165 | 
 166 | def _fetch_block_height():
 167 |     try:
 168 |         r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
 169 |         r.raise_for_status()
 170 |         return int(r.text.strip())
 171 |     except Exception as e:
 172 |         logger.warning("Block height fetch failed: %s", e)
 173 |         return 0
 174 | 
 175 | 
 176 | def gather_intel():
 177 |     """Fetch all live data sources for brief generation."""
 178 |     logger.info("Fetching live data...")
 179 |     btc = _fetch_btc_price()
 180 |     mempool = _fetch_mempool()
 181 |     fng = _fetch_fear_greed()
 182 |     hashrate = _fetch_hashrate()
 183 |     block_height = _fetch_block_height()
 184 | 
 185 |     data = {
 186 |         "btc": btc,
 187 |         "mempool": mempool,
 188 |         "fng": fng,
 189 |         "hashrate": hashrate,
 190 |         "block_height": block_height,
 191 |         "timestamp": datetime.now(timezone.utc).isoformat(),
 192 |     }
 193 |     logger.info("BTC: $%s (%s%%), FNG: %s (%s), Hash: %s EH/s, Block: %s",
 194 |                 f"{btc['price']:,.0f}", f"{btc['change_24h']:+.1f}",
 195 |                 fng['value'], fng['label'],
 196 |                 hashrate['hashrate_eh'], f"{block_height:,}")
 197 |     return data
 198 | 
 199 | 
 200 | # ---------------------------------------------------------------------------
 201 | # API Key
 202 | # ---------------------------------------------------------------------------
 203 | 
 204 | def _get_anthropic_key():
 205 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
 206 |     if key:
 207 |         return key
 208 |     env_path = os.path.join(BASE, ".env")
 209 |     if os.path.exists(env_path):
 210 |         with open(env_path) as f:
 211 |             for line in f:
 212 |                 if line.startswith("ANTHROPIC_API_KEY="):
 213 |                     key = line.strip().split("=", 1)[1].strip("'\"")
 214 |                     os.environ["ANTHROPIC_API_KEY"] = key
 215 |                     return key
 216 |     raise RuntimeError("ANTHROPIC_API_KEY not set")
 217 | 
 218 | 
 219 | 
 220 | 
 221 | # ---------------------------------------------------------------------------
 222 | # Pulse Check Script Loader (multi-value intel reuse)
 223 | # ---------------------------------------------------------------------------
 224 | 
 225 | def _load_pulse_check_script():
 226 |     """Load the most recent Pulse Check script for intel reuse.
 227 |     
 228 |     The Pulse Check video pipeline compiles transcripts, clips, and narrative
 229 |     from 10+ Bitcoin sources into a daily script. This is the richest intel
 230 |     source we have — reuse it as the Stage brief's primary content backbone.
 231 |     Returns condensed script text or None if not available.
 232 |     """
 233 |     output_dir = os.path.join(BASE, "video_pipeline_v3", "output")
 234 |     if not os.path.exists(output_dir):
 235 |         return None
 236 | 
 237 |     # Find most recent script.json (skip test_ dirs, prefer dated dirs)
 238 |     candidates = []
 239 |     for d in os.listdir(output_dir):
 240 |         script_path = os.path.join(output_dir, d, "script.json")
 241 |         if os.path.exists(script_path):
 242 |             mtime = os.path.getmtime(script_path)
 243 |             candidates.append((mtime, script_path))
 244 | 
 245 |     if not candidates:
 246 |         return None
 247 | 
 248 |     # Most recent script
 249 |     candidates.sort(reverse=True)
 250 |     latest_path = candidates[0][1]
 251 |     age_hours = (datetime.now().timestamp() - candidates[0][0]) / 3600
 252 | 
 253 |     # Only use if <24 hours old — stale scripts mislead the brief
 254 |     if age_hours > 24:
 255 |         logger.info("Pulse Check script too old (%.1fh) — skipping", age_hours)
 256 |         return None
 257 | 
 258 |     try:
 259 |         with open(latest_path) as f:
 260 |             script_data = json.load(f)
 261 | 
 262 |         # Extract dialogue lines — the actual spoken content
 263 |         lines = []
 264 |         if isinstance(script_data, dict):
 265 |             # Try common script structures
 266 |             for key in ("segments", "dialogue", "lines", "script", "content"):
 267 |                 if key in script_data:
 268 |                     items = script_data[key]
 269 |                     if isinstance(items, list):
 270 |                         for item in items:
 271 |                             if isinstance(item, dict):
 272 |                                 text = item.get("text") or item.get("line") or item.get("content") or ""
 273 |                             elif isinstance(item, str):
 274 |                                 text = item
 275 |                             else:
 276 |                                 continue
 277 |                             if text and len(text) > 20:
 278 |                                 lines.append(text.strip())
 279 |                     break
 280 | 
 281 |         if not lines:
 282 |             # Fallback: flatten entire JSON to text
 283 |             raw = json.dumps(script_data)
 284 |             lines = [raw[:2000]]
 285 | 
 286 |         condensed = " ".join(lines)[:3000]  # cap at 3000 chars to stay within token budget
 287 |         logger.info("Pulse Check script loaded: %.1fh old, %d chars", age_hours, len(condensed))
 288 |         return condensed
 289 | 
 290 |     except Exception as e:
 291 |         logger.warning("Pulse Check script load failed: %s", e)
 292 |         return None
 293 | 
 294 | 
 295 | # ---------------------------------------------------------------------------
 296 | # Brief Script Generation
 297 | # ---------------------------------------------------------------------------
 298 | 
 299 | def generate_brief_script(data, brief_type="morning"):
 300 |     """Generate brief script via Claude Haiku."""
 301 |     api_key = _get_anthropic_key()
 302 | 
 303 |     btc = data["btc"]
 304 |     mempool = data["mempool"]
 305 |     fng = data["fng"]
 306 |     hashrate = data["hashrate"]
 307 | 
 308 |     user_prompt = (
 309 |         f"Current Bitcoin data:\n"
 310 |         f"- BTC Price: ${btc['price']:,.0f} ({btc['change_24h']:+.1f}% 24h)\n"
 311 |         f"- Market Cap: ${btc['market_cap']/1e9:,.0f}B\n"
 312 |         f"- 24h Volume: ${btc.get('volume_24h', 0)/1e9:,.1f}B\n"
 313 |         f"- Fear & Greed: {fng['value']} ({fng['label']})\n"
 314 |         f"- Hashrate: {hashrate['hashrate_eh']} EH/s\n"
 315 |         f"- Mempool: {mempool['tx_count']:,} txs, fastest fee {mempool['fastest_fee']} sat/vB\n"
 316 |         f"- Block Height: {data['block_height']:,}\n"
 317 |         f"- Timestamp: {data['timestamp']}\n\n"
 318 |         f"Generate a {brief_type} brief. Max 200 words, punchy, ready to speak."
 319 |     )
 320 | 
 321 |     # Multi-value intel reuse: enrich with Pulse Check script if available
 322 |     pulse_script = _load_pulse_check_script()
 323 |     if pulse_script:
 324 |         user_prompt += (
 325 |             f"\n\nContext from today's Pulse Check script "
 326 |             f"(use as primary narrative backbone):\n{pulse_script[:2000]}"
 327 |         )
 328 |         logger.info("[brief] Pulse Check script injected into prompt")
 329 |     else:
 330 |         logger.info("[brief] No Pulse Check script — using live data only")
 331 | 
 332 |     system = BRIEF_SYSTEM_PROMPTS.get(brief_type, BRIEF_SYSTEM_PROMPTS["morning"])
 333 | 
 334 |     resp = requests.post(
 335 |         "https://api.anthropic.com/v1/messages",
 336 |         headers={
 337 |             "x-api-key": api_key,
 338 |             "anthropic-version": "2023-06-01",
 339 |             "content-type": "application/json",
 340 |         },
 341 |         json={
 342 |             "model": CLAUDE_MODEL,
 343 |             "max_tokens": 400,
 344 |             "system": system,
 345 |             "messages": [{"role": "user", "content": user_prompt}],
 346 |         },
 347 |         timeout=30,
 348 |     )
 349 |     resp.raise_for_status()
 350 |     text = resp.json()["content"][0]["text"].strip()
 351 |     word_count = len(text.split())
 352 |     logger.info("Brief script: %d words (%s)", word_count, brief_type)
 353 |     return text
 354 | 
 355 | 
 356 | # ---------------------------------------------------------------------------
 357 | # Intel Extraction (5 tasks in one Haiku call)
 358 | # ---------------------------------------------------------------------------
 359 | 
 360 | EXTRACTION_SYSTEM = (
 361 |     "You are an intel extraction engine for Protocol Pulse. Given a Bitcoin brief script, "
 362 |     "extract ALL of the following in a single JSON response. Be precise and concise.\n\n"
 363 |     "Return ONLY valid JSON with these exact keys:\n"
 364 |     "{\n"
 365 |     '  "tweets": ["tweet1 (max 280 chars)", "tweet2", "tweet3"],\n'
 366 |     '  "newsletter_hook": "2-sentence hook with the most important insight",\n'
 367 |     '  "sentiment": {\n'
 368 |     '    "score": <-100 to +100>,\n'
 369 |     '    "bullish_signals": ["signal1", "signal2"],\n'
 370 |     '    "bearish_signals": ["signal1"],\n'
 371 |     '    "neutral_topics": ["topic1"]\n'
 372 |     '  },\n'
 373 |     '  "article_seeds": [\n'
 374 |     '    {"headline": "...", "angle": "...", "tags": ["bitcoin", "..."]}\n'
 375 |     '  ],\n'
 376 |     '  "oracle_bullets": ["bullet1", "bullet2", "bullet3"]\n'
 377 |     "}"
 378 | )
 379 | 
 380 | 
 381 | def extract_intel(brief_text, brief_type, timestamp_str):
 382 |     """Run all 5 intel extractions in a single Claude Haiku call."""
 383 |     api_key = _get_anthropic_key()
 384 | 
 385 |     resp = requests.post(
 386 |         "https://api.anthropic.com/v1/messages",
 387 |         headers={
 388 |             "x-api-key": api_key,
 389 |             "anthropic-version": "2023-06-01",
 390 |             "content-type": "application/json",
 391 |         },
 392 |         json={
 393 |             "model": CLAUDE_MODEL,
 394 |             "max_tokens": 1000,
 395 |             "system": EXTRACTION_SYSTEM,
 396 |             "messages": [{"role": "user", "content": f"Brief ({brief_type}):\n\n{brief_text}"}],
 397 |         },
 398 |         timeout=30,
 399 |     )
 400 |     resp.raise_for_status()
 401 |     raw = resp.json()["content"][0]["text"].strip()
 402 | 
 403 |     # Parse JSON from response (handle markdown code blocks)
 404 |     json_match = re.search(r'\{[\s\S]*\}', raw)
 405 |     if not json_match:
 406 |         logger.error("Intel extraction: no JSON found in response")
 407 |         return
 408 |     extracted = json.loads(json_match.group())
 409 | 
 410 |     now = datetime.now(timezone.utc)
 411 |     ts = now.strftime("%Y%m%d_%H%M")
 412 | 
 413 |     # a) Social clips
 414 |     tweets_dir = os.path.join(DATA_DIR, "social_queue")
 415 |     os.makedirs(tweets_dir, exist_ok=True)
 416 |     tweets = extracted.get("tweets", [])
 417 |     with open(os.path.join(tweets_dir, f"{ts}_tweets.json"), "w") as f:
 418 |         json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
 419 |                     "tweets": tweets}, f, indent=2)
 420 |     logger.info("Extracted %d tweets", len(tweets))
 421 | 
 422 |     # b) Newsletter hook
 423 |     hook_dir = os.path.join(DATA_DIR, "newsletter_queue")
 424 |     os.makedirs(hook_dir, exist_ok=True)
 425 |     hook = extracted.get("newsletter_hook", "")
 426 |     with open(os.path.join(hook_dir, f"{ts}_hook.json"), "w") as f:
 427 |         json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
 428 |                     "hook": hook}, f, indent=2)
 429 |     logger.info("Extracted newsletter hook: %s", hook[:80])
 430 | 
 431 |     # c) Sentiment signal
 432 |     sentiment_dir = os.path.join(DATA_DIR, "sentiment")
 433 |     os.makedirs(sentiment_dir, exist_ok=True)
 434 |     sentiment = extracted.get("sentiment", {})
 435 |     with open(os.path.join(sentiment_dir, f"{ts}_signal.json"), "w") as f:
 436 |         json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
 437 |                     **sentiment}, f, indent=2)
 438 |     logger.info("Sentiment score: %s", sentiment.get("score", "N/A"))
 439 | 
 440 |     # d) Article seeds
 441 |     seeds_dir = os.path.join(DATA_DIR, "article_seeds")
 442 |     os.makedirs(seeds_dir, exist_ok=True)
 443 |     seeds = extracted.get("article_seeds", [])
 444 |     with open(os.path.join(seeds_dir, f"{ts}_seeds.json"), "w") as f:
 445 |         json.dump({"generated_at": now.isoformat(), "brief_type": brief_type,
 446 |                     "seeds": seeds}, f, indent=2)
 447 |     logger.info("Extracted %d article seeds", len(seeds))
 448 | 
 449 |     # e) Oracle context
 450 |     ctx_dir = os.path.join(DATA_DIR, "oracle_context")
 451 |     os.makedirs(ctx_dir, exist_ok=True)
 452 |     bullets = extracted.get("oracle_bullets", [])
 453 |     ctx = {
 454 |         "generated_at": now.isoformat(),
 455 |         "brief_type": brief_type,
 456 |         "bullets": bullets,
 457 |         "sentiment_score": sentiment.get("score", 0),
 458 |         "brief_summary": brief_text[:300],
 459 |     }
 460 |     with open(os.path.join(ctx_dir, "latest_brief.json"), "w") as f:
 461 |         json.dump(ctx, f, indent=2)
 462 |     logger.info("Oracle context updated: %d bullets", len(bullets))
 463 | 
 464 |     return extracted
 465 | 
 466 | 
 467 | # ---------------------------------------------------------------------------
 468 | # TTS via Chatterbox (avatar server /oracle/voice)
 469 | # ---------------------------------------------------------------------------
 470 | 
 471 | def _generate_tts_chatterbox(text):
 472 |     """Generate TTS via Chatterbox on avatar server. Returns raw audio bytes.
 473 |     Retries up to 3 times with 10s delay between attempts.
 474 |     """
 475 |     for attempt in range(1, 4):
 476 |         try:
 477 |             logger.info("[TTS] Attempt %d/3 for %d chars of text", attempt, len(text))
 478 |             resp = requests.post(
 479 |                 f"{AVATAR_BASE}/oracle/voice",
 480 |                 json={"text": text},
 481 |                 timeout=300,
 482 |             )
 483 |             if resp.status_code == 200:
 484 |                 logger.info("[TTS] Chatterbox OK: %d bytes (attempt %d)", len(resp.content), attempt)
 485 |                 return resp.content
 486 |             logger.warning("[TTS] Chatterbox HTTP %d on attempt %d", resp.status_code, attempt)
 487 |         except requests.exceptions.Timeout:
 488 |             logger.warning("[TTS] Timeout on attempt %d/3", attempt)
 489 |         except requests.exceptions.ConnectionError as e:
 490 |             logger.warning("[TTS] Connection error on attempt %d/3: %s", attempt, e)
 491 |         except Exception as e:
 492 |             logger.warning("[TTS] Unexpected error on attempt %d/3: %s", attempt, e)
 493 |         if attempt < 3:
 494 |             logger.info("[TTS] Retrying in 10s...")
 495 |             time.sleep(10)
 496 |     raise RuntimeError("Chatterbox TTS failed after 3 attempts")
 497 | 
 498 | 
 499 | # ---------------------------------------------------------------------------
 500 | # Avatar Video Render
 501 | # ---------------------------------------------------------------------------
 502 | 
 503 | def _split_into_chunks(text, max_sentences=3):
 504 |     """Split text into chunks of ~max_sentences for the 30s avatar limit."""
 505 |     sentences = re.split(r'(?<=[.!?])\s+', text.strip())
 506 |     chunks = []
 507 |     current = []
 508 |     for s in sentences:
 509 |         current.append(s)
 510 |         if len(current) >= max_sentences:
 511 |             chunks.append(" ".join(current))
 512 |             current = []
 513 |     if current:
 514 |         chunks.append(" ".join(current))
 515 |     return chunks
 516 | 
 517 | 
 518 | def _render_avatar_chunk(audio_bytes):
 519 |     """Render a single chunk through Wav2Lip via avatar server.
 520 |     Retries up to 3 times with 10s delay. Timeout 300s per attempt.
 521 |     """
 522 |     is_wav = audio_bytes[:4] == b"RIFF"
 523 |     content_type = "audio/wav" if is_wav else "audio/mpeg"
 524 |     audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
 525 |     for attempt in range(1, 4):
 526 |         try:
 527 |             logger.info("[RENDER] Avatar chunk attempt %d/3 (%d bytes audio)", attempt, len(audio_bytes))
 528 |             resp = requests.post(
 529 |                 f"{AVATAR_BASE}/generate",
 530 |                 json={
 531 |                     "audio_base64": audio_b64,
 532 |                     "content_type": content_type,
 533 |                     "enable_blinks": True,
 534 |                     "enable_head_movement": True,
 535 |                     "fps": 30.0,
 536 |                 },
 537 |                 timeout=300,
 538 |             )
 539 |             resp.raise_for_status()
 540 |             duration = float(resp.headers.get("X-Duration", 0))
 541 |             logger.info("[RENDER] Avatar chunk OK: %d bytes, %.1fs (attempt %d)", len(resp.content), duration, attempt)
 542 |             return resp.content, duration
 543 |         except requests.exceptions.Timeout:
 544 |             logger.warning("[RENDER] Avatar chunk timeout on attempt %d/3", attempt)
 545 |         except requests.exceptions.ConnectionError as e:
 546 |             logger.warning("[RENDER] Avatar chunk connection error on attempt %d/3: %s", attempt, e)
 547 |         except Exception as e:
 548 |             logger.warning("[RENDER] Avatar chunk error on attempt %d/3: %s", attempt, e)
 549 |         if attempt < 3:
 550 |             logger.info("[RENDER] Retrying in 10s...")
 551 |             time.sleep(10)
 552 |     raise RuntimeError("Avatar render failed after 3 attempts")
 553 | 
 554 | 
 555 | def _render_audio_only_video(audio_bytes_list):
 556 |     """Fallback: combine audio chunks with static PBX image frame into an MP4.
 557 |     Used when avatar server is down — never returns blank.
 558 |     """
 559 |     logger.info("[FALLBACK] Generating audio-only video with static frame")
 560 |     static_img = os.path.join(BASE, "static", "img", "oracle_avatar_static.png")
 561 |     if not os.path.exists(static_img):
 562 |         # Try alternate paths
 563 |         for alt in [
 564 |             os.path.join(BASE, "oracle", "Proto_P_Avatar_1024.png"),
 565 |             os.path.join(BASE, "static", "oracle_avatar.png"),
 566 |         ]:
 567 |             if os.path.exists(alt):
 568 |                 static_img = alt
 569 |                 break
 570 | 
 571 |     tmpdir = tempfile.mkdtemp(prefix="stage_brief_fallback_")
 572 |     try:
 573 |         # Concatenate all audio chunks
 574 |         audio_paths = []
 575 |         for i, ab in enumerate(audio_bytes_list):
 576 |             p = os.path.join(tmpdir, f"audio_{i:03d}.wav")
 577 |             with open(p, "wb") as f:
 578 |                 f.write(ab)
 579 |             audio_paths.append(p)
 580 | 
 581 |         if len(audio_paths) == 1:
 582 |             combined_audio = audio_paths[0]
 583 |         else:
 584 |             concat_list = os.path.join(tmpdir, "audio_concat.txt")
 585 |             with open(concat_list, "w") as f:
 586 |                 for p in audio_paths:
 587 |                     f.write(f"file '{p}'\n")
 588 |             combined_audio = os.path.join(tmpdir, "combined.wav")
 589 |             subprocess.run([
 590 |                 "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 591 |                 "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1", combined_audio,
 592 |             ], capture_output=True, timeout=60)
 593 | 
 594 |         # Get audio duration
 595 |         probe = subprocess.run(
 596 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 597 |              "-of", "default=noprint_wrappers=1:nokey=1", combined_audio],
 598 |             capture_output=True, text=True, timeout=10,
 599 |         )
 600 |         duration = float(probe.stdout.strip()) if probe.stdout.strip() else 30.0
 601 | 
 602 |         # Create video: static image + audio
 603 |         output_path = os.path.join(tmpdir, "fallback.mp4")
 604 |         cmd = [
 605 |             "ffmpeg", "-y", "-loop", "1", "-i", static_img,
 606 |             "-i", combined_audio,
 607 |             "-c:v", "libx264", "-tune", "stillimage", "-crf", "23",
 608 |             "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
 609 |             "-pix_fmt", "yuv420p", "-shortest", "-movflags", "+faststart",
 610 |             output_path,
 611 |         ]
 612 |         result = subprocess.run(cmd, capture_output=True, timeout=120)
 613 |         if result.returncode != 0:
 614 |             logger.error("[FALLBACK] FFmpeg failed: %s", result.stderr.decode()[-500:])
 615 |             raise RuntimeError("Audio-only video generation failed")
 616 | 
 617 |         with open(output_path, "rb") as f:
 618 |             video_bytes = f.read()
 619 | 
 620 |         logger.info("[FALLBACK] Audio-only video: %d bytes, %.1fs", len(video_bytes), duration)
 621 |         return video_bytes, duration
 622 | 
 623 |     finally:
 624 |         shutil.rmtree(tmpdir, ignore_errors=True)
 625 | 
 626 | 
 627 | def render_avatar_video(brief_text):
 628 |     """Render full brief as avatar video, chunking for 30s limit.
 629 |     Falls back to audio-only with static image if avatar render fails.
 630 |     """
 631 |     chunks = _split_into_chunks(brief_text, max_sentences=3)
 632 |     logger.info("[RENDER] Split brief into %d chunks", len(chunks))
 633 | 
 634 |     # First generate all TTS audio (works even if avatar server is down)
 635 |     audio_chunks = []
 636 |     for i, chunk in enumerate(chunks):
 637 |         logger.info("[RENDER] TTS chunk %d/%d: %d words", i + 1, len(chunks), len(chunk.split()))
 638 |         audio = _generate_tts_chatterbox(chunk)
 639 |         audio_chunks.append(audio)
 640 | 
 641 |     # Try avatar render
 642 |     try:
 643 |         if len(chunks) == 1:
 644 |             video_bytes, duration = _render_avatar_chunk(audio_chunks[0])
 645 |             return video_bytes, duration
 646 | 
 647 |         tmpdir = tempfile.mkdtemp(prefix="stage_brief_")
 648 |         part_paths = []
 649 |         total_duration = 0.0
 650 | 
 651 |         try:
 652 |             for i, audio in enumerate(audio_chunks):
 653 |                 logger.info("[RENDER] Rendering avatar chunk %d/%d", i + 1, len(chunks))
 654 |                 video_bytes, dur = _render_avatar_chunk(audio)
 655 |                 total_duration += dur
 656 | 
 657 |                 part_path = os.path.join(tmpdir, f"part_{i:03d}.mp4")
 658 |                 with open(part_path, "wb") as f:
 659 |                     f.write(video_bytes)
 660 |                 part_paths.append(part_path)
 661 | 
 662 |             concat_list = os.path.join(tmpdir, "concat.txt")
 663 |             with open(concat_list, "w") as f:
 664 |                 for p in part_paths:
 665 |                     f.write(f"file '{p}'\n")
 666 | 
 667 |             output_path = os.path.join(tmpdir, "final.mp4")
 668 |             cmd = [
 669 |                 "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
 670 |                 "-c:v", "libx264", "-crf", "17", "-preset", "medium",
 671 |                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
 672 |                 "-pix_fmt", "yuv420p", "-r", "30", "-vsync", "cfr",
 673 |                 "-vf", "setpts=PTS-STARTPTS",
 674 |                 "-af", "asetpts=PTS-STARTPTS,aresample=async=1",
 675 |                 "-movflags", "+faststart",
 676 |                 output_path,
 677 |             ]
 678 |             result = subprocess.run(cmd, capture_output=True, timeout=120)
 679 |             if result.returncode != 0:
 680 |                 logger.error("FFmpeg concat failed: %s", result.stderr.decode()[-500:])
 681 |                 raise RuntimeError("FFmpeg concat failed")
 682 | 
 683 |             with open(output_path, "rb") as f:
 684 |                 final_bytes = f.read()
 685 | 
 686 |             return final_bytes, total_duration
 687 | 
 688 |         finally:
 689 |             shutil.rmtree(tmpdir, ignore_errors=True)
 690 | 
 691 |     except Exception as e:
 692 |         logger.warning("[RENDER] Avatar render failed: %s — falling back to audio-only video", e)
 693 |         return _render_audio_only_video(audio_chunks)
 694 | 
 695 | 
 696 | # ---------------------------------------------------------------------------
 697 | # Main Pipeline
 698 | # ---------------------------------------------------------------------------
 699 | 
 700 | def generate_brief(brief_type=None):
 701 |     """
 702 |     Full stage brief pipeline: gather -> script -> extract intel -> TTS -> render -> save.
 703 | 
 704 |     Args:
 705 |         brief_type: "morning", "midday", or "evening". Auto-detected from UTC hour if None.
 706 | 
 707 |     Returns:
 708 |         Path to generated MP4, or None on failure.
 709 |     """
 710 |     t0 = time.time()
 711 |     now = datetime.now(timezone.utc)
 712 | 
 713 |     if brief_type is None:
 714 |         hour = now.hour
 715 |         if hour < 10:
 716 |             brief_type = "morning"
 717 |         elif hour < 18:
 718 |             brief_type = "midday"
 719 |         else:
 720 |             brief_type = "evening"
 721 | 
 722 |     logger.info("=" * 60)
 723 |     logger.info("STAGE BRIEF PIPELINE — %s", brief_type.upper())
 724 |     logger.info("=" * 60)
 725 | 
 726 |     try:
 727 |         # 1. Gather fresh intel
 728 |         logger.info("[1/5] Fetching live data...")
 729 |         t1 = time.time()
 730 |         data = gather_intel()
 731 |         logger.info("[1/5] Live data fetched in %.1fs", time.time() - t1)
 732 | 
 733 |         # 2. Generate brief script via Claude
 734 |         logger.info("[2/5] Generating brief script via Claude %s...", CLAUDE_MODEL)
 735 |         t2 = time.time()
 736 |         brief_text = generate_brief_script(data, brief_type)
 737 |         logger.info("[2/5] Brief script generated in %.1fs: %d words", time.time() - t2, len(brief_text.split()))
 738 | 
 739 |         # 3. Intel extraction (cheap text-only, before TTS)
 740 |         logger.info("[3/5] Extracting intel downstream...")
 741 |         ts_str = now.strftime("%Y%m%d_%H%M")
 742 |         try:
 743 |             t3 = time.time()
 744 |             extracted = extract_intel(brief_text, brief_type, ts_str)
 745 |             logger.info("[3/5] Intel extracted in %.1fs", time.time() - t3)
 746 |         except Exception as e:
 747 |             logger.warning("[3/5] Intel extraction failed (non-fatal): %s", e)
 748 |             extracted = None
 749 | 
 750 |         # 4. TTS + Avatar render via Chatterbox
 751 |         logger.info("[4/5] Rendering avatar video (Chatterbox TTS + Wav2Lip) — avatar server: %s", AVATAR_BASE)
 752 |         t4 = time.time()
 753 |         video_bytes, duration = render_avatar_video(brief_text)
 754 |         logger.info("[4/5] Avatar video: %d bytes, %.1fs duration, rendered in %.1fs", len(video_bytes), duration, time.time() - t4)
 755 | 
 756 |         # 5. Save outputs
 757 |         logger.info("[5/5] Saving brief...")
 758 |         os.makedirs(BRIEFS_DIR, exist_ok=True)
 759 |         ts_file = now.strftime("%Y%m%d_%H%M")
 760 |         date_str = now.strftime("%Y-%m-%d")
 761 | 
 762 |         mp4_filename = f"brief_{ts_file}.mp4"
 763 |         mp4_path = os.path.join(BRIEFS_DIR, mp4_filename)
 764 | 
 765 |         with open(mp4_path, "wb") as f:
 766 |             f.write(video_bytes)
 767 | 
 768 |         file_size_mb = os.path.getsize(mp4_path) / (1024 * 1024)
 769 |         if file_size_mb > 150:
 770 |             logger.error("Brief MP4 too large: %.1fMB", file_size_mb)
 771 |             os.remove(mp4_path)
 772 |             return None
 773 | 
 774 |         # Write metadata
 775 |         meta = {
 776 |             "title": f"Oracle {brief_type.title()} Brief",
 777 |             "generated_at": now.isoformat(),
 778 |             "duration": round(duration, 1),
 779 |             "mp4_path": mp4_filename,
 780 |             "mp4_url": f"/data/stage_briefs/{mp4_filename}",
 781 |             "episode_date": date_str,
 782 |             "brief_type": brief_type,
 783 |             "script_summary": brief_text[:500],
 784 |             "word_count": len(brief_text.split()),
 785 |             "tts_provider": "chatterbox",
 786 |             "btc_price": data["btc"]["price"],
 787 |             "sentiment_score": (extracted or {}).get("sentiment", {}).get("score"),
 788 |         }
 789 |         meta_path = os.path.join(BRIEFS_DIR, f"brief_{ts_file}.json")
 790 |         with open(meta_path, "w") as f:
 791 |             json.dump(meta, f, indent=2)
 792 | 
 793 |         # Update latest.json
 794 |         latest_path = os.path.join(BRIEFS_DIR, "latest.json")
 795 |         with open(latest_path, "w") as f:
 796 |             json.dump(meta, f, indent=2)
 797 | 
 798 |         elapsed = round(time.time() - t0, 1)
 799 |         logger.info("Stage brief complete in %ss: %s", elapsed, mp4_filename)
 800 |         return mp4_path
 801 | 
 802 |     except Exception as e:
 803 |         logger.error("Stage brief pipeline failed: %s", e, exc_info=True)
 804 |         return None
 805 | 
 806 | 
 807 | # ---------------------------------------------------------------------------
 808 | # CLI
 809 | # ---------------------------------------------------------------------------
 810 | 
 811 | if __name__ == "__main__":
 812 |     import argparse
 813 |     parser = argparse.ArgumentParser(description="Stage Brief Pipeline")
 814 |     parser.add_argument("--type", choices=["morning", "midday", "evening"],
 815 |                         help="Brief type (auto-detected if omitted)")
 816 |     parser.add_argument("--test", action="store_true",
 817 |                         help="Run immediately regardless of schedule")
 818 |     args = parser.parse_args()
 819 | 
 820 |     result = generate_brief(brief_type=args.type)
 821 |     if result:
 822 |         print(f"\nSUCCESS: {result}")
 823 |         sys.exit(0)
 824 |     else:
 825 |         print("\nFAILED: Brief generation failed (check logs/brief_pipeline.log)")
 826 |         sys.exit(1)
 827 | 
```

### File: services/stage_broadcast_service.py (885 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | Stage Broadcast Service — Signal-driven queue for 24/7 autonomous Bitcoin broadcast.
   4 | 
   5 | Run via cron every 5 minutes:
   6 |   */5 * * * * python3 ~/protocol_pulse/services/stage_broadcast_service.py >> ~/protocol_pulse/logs/broadcast_service.log 2>&1
   7 | 
   8 | Polls 7 data sources, generates 30-90s spoken scripts via Claude Haiku,
   9 | writes to broadcast_queue.json with priority and TTL management.
  10 | """
  11 | 
  12 | import fcntl
  13 | import json
  14 | import logging
  15 | import os
  16 | import re
  17 | import sys
  18 | import time
  19 | import uuid
  20 | from datetime import datetime, timezone, timedelta
  21 | from pathlib import Path
  22 | 
  23 | import requests
  24 | 
  25 | # ---------------------------------------------------------------------------
  26 | # Paths
  27 | # ---------------------------------------------------------------------------
  28 | 
  29 | BASE = Path(__file__).resolve().parent.parent
  30 | QUEUE_PATH = BASE / "video_pipeline_v3" / "data" / "stage_briefs" / "broadcast_queue.json"
  31 | PRICE_CACHE = Path("/tmp/stage_last_price.json")
  32 | METRICS_CACHE = Path("/tmp/stage_last_metrics.json")
  33 | FILLER_STATE = BASE / "data" / "stage_briefs" / "filler_state.json"
  34 | LOGS_DIR = BASE / "logs"
  35 | DATA_DIR = BASE / "data"
  36 | 
  37 | CLAUDE_MODEL = "claude-haiku-4-5-20251001"
  38 | MAX_QUEUE_DEPTH = 15
  39 | 
  40 | # Local LLM offload — try Ollama on GPU 2 before Claude API
  41 | LOCAL_LLM_URL = "http://localhost:11435"
  42 | LOCAL_LLM_MODEL = os.environ.get("WATCHDOG_MODEL", "qwen3-coder:30b")
  43 | 
  44 | # ---------------------------------------------------------------------------
  45 | # Logging
  46 | # ---------------------------------------------------------------------------
  47 | 
  48 | LOGS_DIR.mkdir(exist_ok=True)
  49 | 
  50 | logger = logging.getLogger("stage_broadcast")
  51 | logger.setLevel(logging.INFO)
  52 | 
  53 | _fh = logging.FileHandler(str(LOGS_DIR / "broadcast_service.log"))
  54 | _fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
  55 | logger.addHandler(_fh)
  56 | 
  57 | _sh = logging.StreamHandler()
  58 | _sh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s"))
  59 | logger.addHandler(_sh)
  60 | 
  61 | # ---------------------------------------------------------------------------
  62 | # API Key
  63 | # ---------------------------------------------------------------------------
  64 | 
  65 | def _get_anthropic_key():
  66 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
  67 |     if key:
  68 |         return key
  69 |     env_path = BASE / ".env"
  70 |     if env_path.exists():
  71 |         for line in env_path.read_text().splitlines():
  72 |             if line.startswith("ANTHROPIC_API_KEY="):
  73 |                 key = line.split("=", 1)[1].strip("'\"")
  74 |                 os.environ["ANTHROPIC_API_KEY"] = key
  75 |                 return key
  76 |     raise RuntimeError("ANTHROPIC_API_KEY not set")
  77 | 
  78 | 
  79 | # ---------------------------------------------------------------------------
  80 | # Queue Management (file-locked atomic operations)
  81 | # ---------------------------------------------------------------------------
  82 | 
  83 | def _read_queue():
  84 |     """Read queue with file lock."""
  85 |     if not QUEUE_PATH.exists():
  86 |         return []
  87 |     try:
  88 |         with open(QUEUE_PATH, "r") as f:
  89 |             fcntl.flock(f, fcntl.LOCK_SH)
  90 |             data = json.load(f)
  91 |             fcntl.flock(f, fcntl.LOCK_UN)
  92 |         return data if isinstance(data, list) else []
  93 |     except (json.JSONDecodeError, IOError):
  94 |         return []
  95 | 
  96 | 
  97 | def _write_queue(items):
  98 |     """Write queue with exclusive file lock."""
  99 |     QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
 100 |     with open(QUEUE_PATH, "w") as f:
 101 |         fcntl.flock(f, fcntl.LOCK_EX)
 102 |         json.dump(items, f, indent=2)
 103 |         fcntl.flock(f, fcntl.LOCK_UN)
 104 | 
 105 | 
 106 | def _cleanup_queue(items):
 107 |     """Remove expired items and enforce max depth."""
 108 |     now = datetime.now(timezone.utc)
 109 |     valid = []
 110 |     for item in items:
 111 |         try:
 112 |             expires = datetime.fromisoformat(item["expires_at"].replace("Z", "+00:00"))
 113 |             if expires > now:
 114 |                 valid.append(item)
 115 |         except (KeyError, ValueError):
 116 |             continue
 117 |     # Sort by priority (1=highest)
 118 |     valid.sort(key=lambda x: x.get("priority", 5))
 119 |     return valid[:MAX_QUEUE_DEPTH]
 120 | 
 121 | 
 122 | def _add_to_queue(item):
 123 |     """Add item to queue if not duplicate type within TTL window."""
 124 |     items = _read_queue()
 125 |     items = _cleanup_queue(items)
 126 | 
 127 |     # Prevent duplicate types (except FILLER_INSIGHT)
 128 |     if item["type"] != "FILLER_INSIGHT":
 129 |         for existing in items:
 130 |             if existing["type"] == item["type"]:
 131 |                 logger.info("Skipping duplicate %s already in queue", item["type"])
 132 |                 return items
 133 | 
 134 |     if len(items) >= MAX_QUEUE_DEPTH:
 135 |         # Drop lowest priority
 136 |         items = items[:MAX_QUEUE_DEPTH - 1]
 137 | 
 138 |     items.append(item)
 139 |     items = _cleanup_queue(items)
 140 |     _write_queue(items)
 141 |     logger.info("Queued %s (pri=%d): %s", item["type"], item["priority"],
 142 |                 item["topic_preview"][:60])
 143 |     return items
 144 | 
 145 | 
 146 | # ---------------------------------------------------------------------------
 147 | # Data Fetching (patterns from stage_brief_pipeline.py)
 148 | # ---------------------------------------------------------------------------
 149 | 
 150 | def _fetch_btc_price():
 151 |     """Fetch BTC price — internal API first, CoinGecko fallback."""
 152 |     # Try internal price API first (no rate limits)
 153 |     try:
 154 |         resp = requests.get("http://localhost:5000/api/btc-price", timeout=5)
 155 |         if resp.status_code == 200:
 156 |             d = resp.json()
 157 |             price = d.get("price") or d.get("bitcoin", {}).get("usd")
 158 |             change = d.get("change_24h") or d.get("bitcoin", {}).get("usd_24h_change", 0)
 159 |             if price:
 160 |                 return {
 161 |                     "price": float(price),
 162 |                     "change_24h": round(float(change), 2),
 163 |                     "market_cap": d.get("market_cap", 0),
 164 |                 }
 165 |     except Exception as e:
 166 |         logger.warning("Internal price API failed: %s", e)
 167 | 
 168 |     # Fallback to CoinGecko
 169 |     try:
 170 |         resp = requests.get(
 171 |             "https://api.coingecko.com/api/v3/simple/price",
 172 |             params={"ids": "bitcoin", "vs_currencies": "usd",
 173 |                     "include_24hr_change": "true", "include_market_cap": "true"},
 174 |             timeout=10
 175 |         )
 176 |         if resp.status_code == 200:
 177 |             d = resp.json().get("bitcoin", {})
 178 |             return {
 179 |                 "price": d.get("usd", 0),
 180 |                 "change_24h": round(d.get("usd_24h_change", 0), 2),
 181 |                 "market_cap": d.get("usd_market_cap", 0),
 182 |             }
 183 |     except Exception as e:
 184 |         logger.warning("CoinGecko failed: %s", e)
 185 | 
 186 |     return None
 187 | 
 188 | 
 189 | def _fetch_mempool():
 190 |     try:
 191 |         r = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=10)
 192 |         r.raise_for_status()
 193 |         fees = r.json()
 194 |         r2 = requests.get("https://mempool.space/api/mempool", timeout=10)
 195 |         r2.raise_for_status()
 196 |         mp = r2.json()
 197 |         return {
 198 |             "fastest_fee": fees.get("fastestFee", 0),
 199 |             "hour_fee": fees.get("hourFee", 0),
 200 |             "tx_count": mp.get("count", 0),
 201 |         }
 202 |     except Exception as e:
 203 |         logger.warning("Mempool fetch failed: %s", e)
 204 |         return None
 205 | 
 206 | 
 207 | def _fetch_fear_greed():
 208 |     try:
 209 |         r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
 210 |         r.raise_for_status()
 211 |         d = r.json()["data"][0]
 212 |         return {"value": int(d["value"]), "label": d["value_classification"]}
 213 |     except Exception as e:
 214 |         logger.warning("FNG fetch failed: %s", e)
 215 |         return None
 216 | 
 217 | 
 218 | def _fetch_hashrate():
 219 |     try:
 220 |         r = requests.get("https://mempool.space/api/v1/mining/hashrate/3m", timeout=15)
 221 |         r.raise_for_status()
 222 |         hr = r.json().get("hashrates", [])
 223 |         current_hr = hr[-1]["avgHashrate"] if hr else 0
 224 |         return {"hashrate_eh": round(current_hr / 1e18, 1)}
 225 |     except Exception as e:
 226 |         logger.warning("Hashrate fetch failed: %s", e)
 227 |         return None
 228 | 
 229 | 
 230 | def _fetch_block_height():
 231 |     try:
 232 |         r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
 233 |         r.raise_for_status()
 234 |         return int(r.text.strip())
 235 |     except Exception:
 236 |         return 0
 237 | 
 238 | 
 239 | # ---------------------------------------------------------------------------
 240 | # Script Generation via Claude Haiku
 241 | # ---------------------------------------------------------------------------
 242 | 
 243 | ANCHOR_SYSTEM = (
 244 |     "You are Oracle — the female anchor of Protocol Pulse, a 24/7 sovereign Bitcoin broadcast. "
 245 |     "IDENTITY: You see the world through an Austrian economics lens. You are NOT a financial analyst — "
 246 |     "you are a sovereign individual who understands mining, nodes, and the Bitcoin standard. "
 247 |     "EDITORIAL LAWS: "
 248 |     "Bitcoin ONLY. Never mention altcoins, crypto, DeFi, NFTs, or tokens. "
 249 |     "Never write BTC — always say Bitcoin in full. "
 250 |     "Never hedge. State facts directly. No 'could', 'might', 'it remains to be seen'. "
 251 |     "Respect the audience — they know what a UTXO is. Never explain basics. "
 252 |     "Cold delivery: single most important signal first. No warmup. No greeting. No sign-off. "
 253 |     "TONE: Authoritative, sharp, dry wit. Intelligence briefing energy. "
 254 |     "Think: intercepting a live signal — not reading a press release. "
 255 |     "NEVER say: 'interesting', 'really impactful', 'game changer', 'let's dive in', 'buckle up'. "
 256 |     "Every segment must contain ONE specific data point or on-chain metric. "
 257 |     "Under 30 words. Two sentences maximum. Punchy and direct. "
 258 |     "End with forward signal — what to watch next, not a summary of what was just said."
 259 | )
 260 | 
 261 | 
 262 | def _generate_script_local(prompt):
 263 |     """Try local Ollama first — zero API cost."""
 264 |     try:
 265 |         resp = requests.post(
 266 |             f"{LOCAL_LLM_URL}/api/chat",
 267 |             json={
 268 |                 "model": LOCAL_LLM_MODEL,
 269 |                 "messages": [
 270 |                     {"role": "system", "content": ANCHOR_SYSTEM},
 271 |                     {"role": "user", "content": prompt},
 272 |                 ],
 273 |                 "stream": False,
 274 |                 "options": {"temperature": 0.7},
 275 |             },
 276 |             timeout=15,
 277 |         )
 278 |         resp.raise_for_status()
 279 |         text = resp.json().get("message", {}).get("content", "").strip()
 280 |         if len(text) > 10:
 281 |             logger.info("Script generated via LOCAL LLM")
 282 |             return text
 283 |     except Exception as e:
 284 |         logger.info("Local LLM failed (%s), falling back to API", e)
 285 |     return None
 286 | 
 287 | 
 288 | def _generate_script(segment_type, context_data):
 289 |     """Generate a broadcast script — local Ollama first, Claude Haiku fallback."""
 290 |     prompt = f"Segment type: {segment_type}\n\nData:\n{json.dumps(context_data, indent=2)}\n\n"
 291 |     prompt += "Generate a spoken broadcast script based on this data."
 292 | 
 293 |     # Try local LLM first (free)
 294 |     local_result = _generate_script_local(prompt)
 295 |     if local_result:
 296 |         import re as _re
 297 |         local_result = _re.sub(r'^#+\s+[^\n]*\n?', '', local_result, flags=_re.MULTILINE)
 298 |         local_result = _re.sub(r'^---+\s*', '', local_result, flags=_re.MULTILINE)
 299 |         return local_result.strip()
 300 | 
 301 |     # Fallback to Claude Haiku API
 302 |     logger.info("Script generated via API (Claude Haiku)")
 303 |     api_key = _get_anthropic_key()
 304 | 
 305 |     resp = requests.post(
 306 |         "https://api.anthropic.com/v1/messages",
 307 |         headers={
 308 |             "x-api-key": api_key,
 309 |             "anthropic-version": "2023-06-01",
 310 |             "content-type": "application/json",
 311 |         },
 312 |         json={
 313 |             "model": CLAUDE_MODEL,
 314 |             "max_tokens": 80,
 315 |             "system": ANCHOR_SYSTEM,
 316 |             "messages": [{"role": "user", "content": prompt}],
 317 |         },
 318 |         timeout=30,
 319 |     )
 320 |     resp.raise_for_status()
 321 |     import re as _re
 322 |     text = resp.json()["content"][0]["text"].strip()
 323 |     text = _re.sub(r'^#+\s+[^\n]*\n?', '', text, flags=_re.MULTILINE)
 324 |     text = _re.sub(r'^---+\s*', '', text, flags=_re.MULTILINE)
 325 |     text = text.strip()
 326 |     return text
 327 | 
 328 | 
 329 | def _make_queue_item(seg_type, priority, script, source_label, topic_preview, ttl_minutes):
 330 |     now = datetime.now(timezone.utc)
 331 |     return {
 332 |         "id": str(uuid.uuid4()),
 333 |         "type": seg_type,
 334 |         "priority": priority,
 335 |         "script": script,
 336 |         "source_label": source_label,
 337 |         "topic_preview": topic_preview,
 338 |         "generated_at": now.isoformat(),
 339 |         "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
 340 |     }
 341 | 
 342 | 
 343 | # ---------------------------------------------------------------------------
 344 | # Signal Checks (7 types)
 345 | # ---------------------------------------------------------------------------
 346 | 
 347 | def check_price_alert(btc_data):
 348 |     """PRICE_ALERT (pri=1): >0.8% move from cached price."""
 349 |     if not btc_data:
 350 |         return None
 351 | 
 352 |     current_price = btc_data["price"]
 353 |     cached_price = 0
 354 | 
 355 |     if PRICE_CACHE.exists():
 356 |         try:
 357 |             cached = json.loads(PRICE_CACHE.read_text())
 358 |             cached_price = cached.get("price", 0)
 359 |         except (json.JSONDecodeError, IOError):
 360 |             pass
 361 | 
 362 |     # Always update cache
 363 |     PRICE_CACHE.write_text(json.dumps({"price": current_price,
 364 |                                         "timestamp": datetime.now(timezone.utc).isoformat()}))
 365 | 
 366 |     if cached_price <= 0:
 367 |         logger.info("Price cache initialized at $%s", f"{current_price:,.0f}")
 368 |         return None
 369 | 
 370 |     pct_change = abs((current_price - cached_price) / cached_price) * 100
 371 |     if pct_change < 0.8:
 372 |         return None
 373 | 
 374 |     direction = "up" if current_price > cached_price else "down"
 375 |     logger.info("PRICE_ALERT: $%s → $%s (%.1f%% %s)",
 376 |                 f"{cached_price:,.0f}", f"{current_price:,.0f}", pct_change, direction)
 377 | 
 378 |     script = _generate_script("PRICE_ALERT", {
 379 |         "previous_price": cached_price,
 380 |         "current_price": current_price,
 381 |         "percent_change": round(pct_change, 2),
 382 |         "direction": direction,
 383 |         "change_24h": btc_data["change_24h"],
 384 |     })
 385 | 
 386 |     return _make_queue_item(
 387 |         "PRICE_ALERT", 1, script,
 388 |         "📡 PRICE ALERT",
 389 |         f"Bitcoin {'breaks' if direction == 'up' else 'drops to'} ${current_price:,.0f}",
 390 |         30,
 391 |     )
 392 | 
 393 | 
 394 | def check_thought_leader():
 395 |     """THOUGHT_LEADER (pri=2): Priority-1 handles from raw_tweets.json."""
 396 |     PRIORITY_HANDLES = {
 397 |         "saylor", "natbrunell", "jack", "gladstein", "prestonpysh",
 398 |         "martybent", "lynaldencontact", "jeffbooth", "odell", "aantonop", "adam3us",
 399 |     }
 400 | 
 401 |     tweets_path = DATA_DIR / "tweet_study" / "raw_tweets.json"
 402 |     if not tweets_path.exists():
 403 |         return None
 404 | 
 405 |     try:
 406 |         tweets = json.loads(tweets_path.read_text())
 407 |         if not isinstance(tweets, list):
 408 |             return None
 409 | 
 410 |         now = datetime.now(timezone.utc)
 411 |         cutoff = now - timedelta(hours=72)
 412 | 
 413 |         import random
 414 |         tweets_shuffled = tweets.copy()
 415 |         random.shuffle(tweets_shuffled)
 416 | 
 417 |         for tweet in tweets_shuffled:
 418 |             handle = (tweet.get("handle") or tweet.get("username") or "").lower().lstrip("@")
 419 |             if handle not in PRIORITY_HANDLES:
 420 |                 continue
 421 | 
 422 |             created = tweet.get("created_at") or tweet.get("timestamp") or ""
 423 |             if created:
 424 |                 try:
 425 |                     tweet_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
 426 |                     if tweet_time < cutoff:
 427 |                         continue
 428 |                 except (ValueError, TypeError):
 429 |                     pass
 430 | 
 431 |             text = tweet.get("text") or tweet.get("content") or ""
 432 |             if len(text) < 30:
 433 |                 continue
 434 | 
 435 |             logger.info("THOUGHT_LEADER: @%s — %s", handle, text[:80])
 436 |             script = _generate_script("THOUGHT_LEADER", {
 437 |                 "handle": handle,
 438 |                 "tweet_text": text[:500],
 439 |                 "context": "Priority Bitcoin thought leader tweet",
 440 |             })
 441 | 
 442 |             return _make_queue_item(
 443 |                 "THOUGHT_LEADER", 2, script,
 444 |                 f"🧠 @{handle.upper()}",
 445 |                 text[:80],
 446 |                 120,
 447 |             )
 448 |     except Exception as e:
 449 |         logger.warning("Thought leader check failed: %s", e)
 450 | 
 451 |     return None
 452 | 
 453 | 
 454 | def check_space_tap():
 455 |     """SPACE_TAP (pri=2): Fresh X Spaces clips."""
 456 |     spaces_cache = BASE / "x_spaces_scraper" / "cache"
 457 |     if not spaces_cache.exists():
 458 |         return None
 459 | 
 460 |     try:
 461 |         cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
 462 |         for f in sorted(spaces_cache.glob("*.json"), reverse=True):
 463 |             if f.name == "last_run.json":
 464 |                 continue
 465 |             mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
 466 |             if mtime < cutoff:
 467 |                 continue
 468 | 
 469 |             data = json.loads(f.read_text())
 470 |             title = data.get("space_title") or data.get("title") or "Live Space"
 471 |             transcript = data.get("transcript") or data.get("text") or ""
 472 |             if len(transcript) < 50:
 473 |                 continue
 474 | 
 475 |             logger.info("SPACE_TAP: %s", title[:60])
 476 |             script = _generate_script("SPACE_TAP", {
 477 |                 "space_title": title,
 478 |                 "transcript_excerpt": transcript[:800],
 479 |                 "context": "We intercepted a live Bitcoin space — here's the key signal.",
 480 |             })
 481 | 
 482 |             return _make_queue_item(
 483 |                 "SPACE_TAP", 2, script,
 484 |                 "🎙️ SPACE TAP",
 485 |                 title[:80],
 486 |                 240,
 487 |             )
 488 |     except Exception as e:
 489 |         logger.warning("Space tap check failed: %s", e)
 490 | 
 491 |     return None
 492 | 
 493 | 
 494 | def check_article_teaser():
 495 |     """ARTICLE_TEASER (pri=3): Recent articles from DB."""
 496 |     db_path = BASE / "instance" / "protocol_pulse.db"
 497 |     if not db_path.exists():
 498 |         return None
 499 | 
 500 |     try:
 501 |         import sqlite3
 502 |         conn = sqlite3.connect(str(db_path))
 503 |         conn.row_factory = sqlite3.Row
 504 |         cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
 505 |         row = conn.execute(
 506 |             "SELECT title, summary FROM articles WHERE created_at > ? ORDER BY RANDOM() LIMIT 1",
 507 |             (cutoff,)
 508 |         ).fetchone()
 509 |         conn.close()
 510 | 
 511 |         if not row:
 512 |             return None
 513 | 
 514 |         title = row["title"]
 515 |         summary = row["summary"] or ""
 516 |         logger.info("ARTICLE_TEASER: %s", title[:60])
 517 | 
 518 |         script = _generate_script("ARTICLE_TEASER", {
 519 |             "article_title": title,
 520 |             "article_summary": summary,
 521 |             "context": "Fresh from our editorial desk — tease this article without giving everything away.",
 522 |         })
 523 | 
 524 |         return _make_queue_item(
 525 |             "ARTICLE_TEASER", 3, script,
 526 |             "📰 FRESH INTEL",
 527 |             title[:80],
 528 |             240,
 529 |         )
 530 |     except Exception as e:
 531 |         logger.warning("Article teaser check failed: %s", e)
 532 |         return None
 533 | 
 534 | 
 535 | def check_metrics_pulse(btc_data):
 536 |     """METRICS_PULSE (pri=3): Network metrics every 20+ minutes."""
 537 |     if METRICS_CACHE.exists():
 538 |         try:
 539 |             cached = json.loads(METRICS_CACHE.read_text())
 540 |             last_ts = datetime.fromisoformat(cached["timestamp"].replace("Z", "+00:00"))
 541 |             if datetime.now(timezone.utc) - last_ts < timedelta(minutes=20):
 542 |                 return None
 543 |         except (json.JSONDecodeError, KeyError, ValueError):
 544 |             pass
 545 | 
 546 |     hashrate = _fetch_hashrate()
 547 |     fng = _fetch_fear_greed()
 548 |     mempool = _fetch_mempool()
 549 |     block_height = _fetch_block_height()
 550 | 
 551 |     if not any([hashrate, fng, mempool]):
 552 |         return None
 553 | 
 554 |     metrics = {
 555 |         "btc_price": btc_data["price"] if btc_data else 0,
 556 |         "change_24h": btc_data["change_24h"] if btc_data else 0,
 557 |         "hashrate_eh": hashrate["hashrate_eh"] if hashrate else 0,
 558 |         "fng_value": fng["value"] if fng else 50,
 559 |         "fng_label": fng["label"] if fng else "Neutral",
 560 |         "fastest_fee": mempool["fastest_fee"] if mempool else 0,
 561 |         "tx_count": mempool["tx_count"] if mempool else 0,
 562 |         "block_height": block_height,
 563 |     }
 564 | 
 565 |     METRICS_CACHE.write_text(json.dumps({
 566 |         "timestamp": datetime.now(timezone.utc).isoformat(),
 567 |         **metrics,
 568 |     }))
 569 | 
 570 |     logger.info("METRICS_PULSE: BTC $%s, FNG %s, Hash %s EH/s",
 571 |                 f"{metrics['btc_price']:,.0f}", metrics["fng_value"], metrics["hashrate_eh"])
 572 | 
 573 |     script = _generate_script("METRICS_PULSE", metrics)
 574 | 
 575 |     return _make_queue_item(
 576 |         "METRICS_PULSE", 3, script,
 577 |         "📊 METRICS PULSE",
 578 |         f"BTC ${metrics['btc_price']:,.0f} · FNG {metrics['fng_value']} · {metrics['hashrate_eh']} EH/s",
 579 |         240,
 580 |     )
 581 | 
 582 | 
 583 | def check_nostr_signal():
 584 |     """NOSTR_SIGNAL (pri=4): Narrative from Nostr discourse."""
 585 |     narrative_path = BASE / "video_pipeline_v3" / "data" / "intelligence" / "narrative_context.json"
 586 |     if not narrative_path.exists():
 587 |         return None
 588 | 
 589 |     try:
 590 |         data = json.loads(narrative_path.read_text())
 591 |         narrative = data.get("dominant_narrative") or data.get("narrative") or ""
 592 |         if not narrative:
 593 |             return None
 594 | 
 595 |         updated = data.get("updated_at") or data.get("generated_at") or ""
 596 |         if updated:
 597 |             try:
 598 |                 update_time = datetime.fromisoformat(updated.replace("Z", "+00:00"))
 599 |                 if datetime.now(timezone.utc) - update_time > timedelta(hours=4):
 600 |                     return None
 601 |             except (ValueError, TypeError):
 602 |                 pass
 603 | 
 604 |         logger.info("NOSTR_SIGNAL: %s", narrative[:60])
 605 |         script = _generate_script("NOSTR_SIGNAL", {
 606 |             "dominant_narrative": narrative,
 607 |             "themes": data.get("themes", []),
 608 |             "context": "This is the dominant discourse emerging from Bitcoin Nostr relays right now.",
 609 |         })
 610 | 
 611 |         return _make_queue_item(
 612 |             "NOSTR_SIGNAL", 4, script,
 613 |             "⚡ NOSTR SIGNAL",
 614 |             narrative[:80],
 615 |             240,
 616 |         )
 617 |     except Exception as e:
 618 |         logger.warning("Nostr signal check failed: %s", e)
 619 |         return None
 620 | 
 621 | 
 622 | # ---------------------------------------------------------------------------
 623 | # Filler Insights (20 pre-written, never repeat consecutively)
 624 | # ---------------------------------------------------------------------------
 625 | 
 626 | FILLER_INSIGHTS = [
 627 |     "Bitcoin is the only monetary network in history that operates with zero counterparty risk. Every ten minutes, a new block confirms that no single entity controls the ledger. That's not a feature — that's a paradigm shift in how humans coordinate value across trust boundaries.",
 628 |     "The Lightning Network processed more transactions last month than the entire Bitcoin base layer did in its first four years. Layer-two scaling isn't theoretical anymore — it's quietly becoming the rails for instant, near-free payments worldwide.",
 629 |     "Satoshi Nakamoto's last known communication was in December 2010. Fifteen years later, the protocol runs exactly as designed. No CEO, no board meetings, no emergency patches. The code is the constitution.",
 630 |     "Hash rate is the most honest signal in Bitcoin. Miners don't speculate — they commit capital, electricity, and hardware. When hash rate climbs to all-time highs, it means serious operators are betting their balance sheets on Bitcoin's future.",
 631 |     "There are only 21 million bitcoin. That's not a soft cap, not a target — it's a mathematical certainty enforced by every node on the network. In a world of infinite money printing, scarcity is the ultimate signal.",
 632 |     "The mempool is Bitcoin's waiting room. When fees spike, it means demand for block space exceeds supply. That's not a bug — it's proof that people value the security of final settlement enough to pay for it.",
 633 |     "Every four years, the block subsidy cuts in half. This halving mechanism is the most predictable monetary policy in human history. No central banker can override it. No politician can delay it.",
 634 |     "Running a full node costs less than a streaming subscription. For that price, you independently verify every transaction since the genesis block. That's sovereignty you can run on a Raspberry Pi.",
 635 |     "Bitcoin's difficulty adjustment is an engineering marvel. Every 2,016 blocks, the network recalibrates to maintain ten-minute block intervals regardless of how much hash power joins or leaves. Self-regulating monetary infrastructure.",
 636 |     "The Bitcoin network has been operational for over 99.98 percent of its existence. No bank, no government system, no tech company can match that uptime. Decentralization isn't just philosophy — it's resilience.",
 637 |     "Multisig wallets eliminate single points of failure. A two-of-three setup means no single key compromise can drain your funds. This is how institutions are beginning to custody billions in bitcoin.",
 638 |     "Bitcoin mining is increasingly powered by stranded energy — gas flares, excess hydro, curtailed wind and solar. Miners are becoming the buyer of last resort for energy that would otherwise be wasted.",
 639 |     "The UTXO model is Bitcoin's secret weapon for privacy and scalability. Unlike account-based systems, every transaction output is independent — enabling parallel validation and coin-level audit trails.",
 640 |     "Nostr is building the decentralized social layer that Bitcoin's monetary layer always needed. Censorship-resistant communication plus censorship-resistant money — that's the full stack of digital sovereignty.",
 641 |     "Time-chain analysis shows that long-term holders — wallets dormant for one year or more — consistently hold over sixty percent of all bitcoin supply. The conviction of this network's participants is unprecedented.",
 642 |     "Bitcoin script is intentionally limited. No Turing completeness, no complex smart contracts on the base layer. This constraint is a security feature — the monetary layer should be boring and bulletproof.",
 643 |     "The genesis block contains a Times headline about bank bailouts. Satoshi didn't just build software — they embedded a permanent protest against monetary manipulation into the first block ever mined.",
 644 |     "Coinjoin transactions are growing month over month. Privacy isn't optional in a sound money system — it's essential. Financial surveillance is incompatible with individual sovereignty.",
 645 |     "Bitcoin's energy consumption is a feature, not a bug. Proof of work converts physical energy into digital security. The cost of attacking the network must always exceed the cost of defending it.",
 646 |     "Every bitcoin transaction is a voluntary exchange. No chargebacks, no intermediaries, no permission required. For the first time in digital history, we have bearer assets that move at the speed of light.",
 647 | ]
 648 | 
 649 | 
 650 | def _generate_live_filler():
 651 |     """Generate a live Bitcoin intelligence filler segment using current data."""
 652 |     try:
 653 |         btc_data = _fetch_btc_price() or {}
 654 |         mempool = _fetch_mempool() or {}
 655 |         hashrate = _fetch_hashrate()
 656 |         fng = _fetch_fear_greed()
 657 | 
 658 |         price = btc_data.get("price", 0)
 659 |         change = btc_data.get("change_24h", 0)
 660 |         fee = mempool.get("fastest_fee", 0)
 661 |         hr = hashrate.get("hashrate_eh", 0) if hashrate else 0
 662 |         fg = fng.get("value", 0) if fng else 0
 663 | 
 664 |         context = f"""Current Bitcoin data:
 665 | - Price: ${price:,.0f} ({change:+.1f}% 24h)
 666 | - Fear & Greed: {fg}/100
 667 | - Hashrate: {hr:.0f} EH/s
 668 | - Mempool fast fee: {fee} sat/vbyte"""
 669 | 
 670 |         prompt = (
 671 |             f"{context}\n\n"
 672 |             "Write a 40-60 word spoken Bitcoin intelligence broadcast segment. "
 673 |             "Cold open with the most important signal from the data above. "
 674 |             "Austrian economics worldview. Sovereign individual framing. "
 675 |             "No greeting, no sign-off, no hedging. "
 676 |             "Bitcoin only. Never say 'BTC'. Never say 'interesting'. "
 677 |             "Every sentence must earn its place. "
 678 |             "End with a forward-looking statement."
 679 |         )
 680 |         script = _generate_script_local(prompt)
 681 |         if script and len(script) > 30:
 682 |             return script
 683 |     except Exception as e:
 684 |         logger.warning("[FILLER] _generate_live_filler error: %s", e)
 685 |     return None
 686 | 
 687 | 
 688 | def get_filler_insight():
 689 |     """Get next filler insight — live AI generation with static fallback."""
 690 |     last_idx = -1
 691 |     last_generated = 0
 692 |     if FILLER_STATE.exists():
 693 |         try:
 694 |             state = json.loads(FILLER_STATE.read_text())
 695 |             last_idx = state.get("idx", -1)
 696 |             last_generated = state.get("last_generated", 0)
 697 |         except (json.JSONDecodeError, IOError):
 698 |             pass
 699 | 
 700 |     # Ensure state directory exists
 701 |     FILLER_STATE.parent.mkdir(parents=True, exist_ok=True)
 702 | 
 703 |     # Try live AI generation if >30 min since last AI filler
 704 |     now_ts = time.time()
 705 |     if now_ts - last_generated > 1800:
 706 |         try:
 707 |             live_script = _generate_live_filler()
 708 |             if live_script:
 709 |                 FILLER_STATE.write_text(json.dumps({
 710 |                     "idx": last_idx,
 711 |                     "last_generated": now_ts
 712 |                 }))
 713 |                 logger.info("[FILLER] Live AI filler generated")
 714 |                 return _make_queue_item(
 715 |                     "FILLER_INSIGHT", 5, live_script,
 716 |                     "⚡ LIVE INSIGHT",
 717 |                     live_script[:80],
 718 |                     120,
 719 |                 )
 720 |         except Exception as e:
 721 |             logger.warning("[FILLER] Live generation failed, using static: %s", e)
 722 | 
 723 |     # Fall back to static rotation
 724 |     next_idx = (last_idx + 1) % len(FILLER_INSIGHTS)
 725 |     FILLER_STATE.write_text(json.dumps({
 726 |         "idx": next_idx,
 727 |         "last_generated": last_generated
 728 |     }))
 729 |     script = FILLER_INSIGHTS[next_idx]
 730 |     return _make_queue_item(
 731 |         "FILLER_INSIGHT", 5, script,
 732 |         "💡 INSIGHT",
 733 |         script[:80],
 734 |         240,
 735 |     )
 736 | 
 737 | 
 738 | def generate_filler_live():
 739 |     """Generate a filler insight for immediate use (called by consume endpoint)."""
 740 |     return get_filler_insight()
 741 | 
 742 | 
 743 | # ---------------------------------------------------------------------------
 744 | # Main Pipeline
 745 | # ---------------------------------------------------------------------------
 746 | 
 747 | def run():
 748 |     """Main broadcast service run — called by cron every 5 minutes."""
 749 |     t0 = time.time()
 750 |     logger.info("=" * 50)
 751 |     logger.info("BROADCAST SERVICE RUN — %s", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
 752 |     logger.info("=" * 50)
 753 | 
 754 |     # Clean expired items first
 755 |     items = _read_queue()
 756 |     items = _cleanup_queue(items)
 757 |     _write_queue(items)
 758 |     logger.info("Queue depth after cleanup: %d", len(items))
 759 | 
 760 |     # Fetch BTC price (shared across checks)
 761 |     btc_data = _fetch_btc_price()
 762 | 
 763 |     # Run signal checks in priority order
 764 |     new_items = 0
 765 | 
 766 |     # 1. PRICE_ALERT (pri=1)
 767 |     try:
 768 |         item = check_price_alert(btc_data)
 769 |         if item:
 770 |             _add_to_queue(item)
 771 |             new_items += 1
 772 |     except Exception as e:
 773 |         logger.error("Price alert check error: %s", e)
 774 | 
 775 |     # 2. THOUGHT_LEADER (pri=2) — max 1 per run
 776 |     try:
 777 |         item = check_thought_leader()
 778 |         if item:
 779 |             _add_to_queue(item)
 780 |             new_items += 1
 781 |     except Exception as e:
 782 |         logger.error("Thought leader check error: %s", e)
 783 | 
 784 |     # 3. SPACE_TAP (pri=2)
 785 |     try:
 786 |         item = check_space_tap()
 787 |         if item:
 788 |             _add_to_queue(item)
 789 |             new_items += 1
 790 |     except Exception as e:
 791 |         logger.error("Space tap check error: %s", e)
 792 | 
 793 |     # 4. ARTICLE_TEASER (pri=3)
 794 |     try:
 795 |         item = check_article_teaser()
 796 |         if item:
 797 |             _add_to_queue(item)
 798 |             new_items += 1
 799 |     except Exception as e:
 800 |         logger.error("Article teaser check error: %s", e)
 801 | 
 802 |     # 5. METRICS_PULSE (pri=3)
 803 |     try:
 804 |         item = check_metrics_pulse(btc_data)
 805 |         if item:
 806 |             _add_to_queue(item)
 807 |             new_items += 1
 808 |     except Exception as e:
 809 |         logger.error("Metrics pulse check error: %s", e)
 810 | 
 811 |     # 6. NOSTR_SIGNAL (pri=4)
 812 |     try:
 813 |         item = check_nostr_signal()
 814 |         if item:
 815 |             _add_to_queue(item)
 816 |             new_items += 1
 817 |     except Exception as e:
 818 |         logger.error("Nostr signal check error: %s", e)
 819 | 
 820 |     # 7. FILLER_INSIGHT (pri=5) — keep queue topped up to at least 4 items
 821 |     final_queue = _read_queue()
 822 |     final_queue = _cleanup_queue(final_queue)
 823 |     filler_added = 0
 824 |     while len(final_queue) < 4 and filler_added < 3:
 825 |         filler = get_filler_insight()
 826 |         _add_to_queue(filler)
 827 |         final_queue = _read_queue()
 828 |         final_queue = _cleanup_queue(final_queue)
 829 |         filler_added += 1
 830 |         logger.info("Added filler insight (%d in queue)", len(final_queue))
 831 | 
 832 |     final_queue = _read_queue()
 833 |     final_queue = _cleanup_queue(final_queue)
 834 |     elapsed = round(time.time() - t0, 1)
 835 |     logger.info("Run complete in %ss — %d new items, queue depth: %d",
 836 |                 elapsed, new_items, len(final_queue))
 837 | 
 838 |     return len(final_queue)
 839 | 
 840 | 
 841 | # ---------------------------------------------------------------------------
 842 | # CLI
 843 | # ---------------------------------------------------------------------------
 844 | 
 845 | if __name__ == "__main__":
 846 |     if "--prefill" in sys.argv:
 847 |         # Pre-fill queue with 8 items for low-traffic hours
 848 |         logger.info("PREFILL MODE — building deep queue")
 849 |         btc_data = _fetch_btc_price()
 850 |         prefill_count = 0
 851 |         # Try all signal types first
 852 |         for check_fn, args in [
 853 |             (check_metrics_pulse, (btc_data,)),
 854 |             (check_article_teaser, ()),
 855 |             (check_nostr_signal, ()),
 856 |             (check_thought_leader, ()),
 857 |             (check_article_teaser, ()),
 858 |             (check_nostr_signal, ()),
 859 |             (check_metrics_pulse, (btc_data,)),
 860 |             (check_article_teaser, ()),
 861 |         ]:
 862 |             try:
 863 |                 q = _read_queue()
 864 |                 if len(q) >= MAX_QUEUE_DEPTH:
 865 |                     break
 866 |                 item = check_fn(*args)
 867 |                 if item:
 868 |                     _add_to_queue(item)
 869 |                     prefill_count += 1
 870 |                     time.sleep(2)  # brief pause between API calls
 871 |             except Exception as e:
 872 |                 logger.warning("Prefill check error: %s", e)
 873 |         # Top up with live filler to reach 8 items
 874 |         q = _read_queue()
 875 |         while len(q) < 8:
 876 |             _add_to_queue(get_filler_insight())
 877 |             q = _read_queue()
 878 |             prefill_count += 1
 879 |         logger.info("PREFILL COMPLETE — %d items added, queue depth: %d",
 880 |                     prefill_count, len(_read_queue()))
 881 |     else:
 882 |         depth = run()
 883 |         print(f"Queue depth: {depth}")
 884 |         sys.exit(0)
 885 | 
```

### File: templates/stage.html (2359 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}Oracle Stage — Protocol Pulse Live{% endblock %}
   4 | {% block meta_description %}Bitcoin intelligence. Live. Oracle reports in real time on price, on-chain signals, partner channel transcripts, and Nostr discourse.{% endblock %}
   5 | 
   6 | {% block head %}
   7 | <meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover,interactive-widget=resizes-content">
   8 | <style>
   9 | /* ══════════════════════════════════════════════════════
  10 |    ORACLE STAGE — Broadcast Desk Layout
  11 |    Aesthetic: News control room meets Bitcoin terminal.
  12 |    Obsidian base, signal-red accents, gold data rails,
  13 |    Syne Mono headlines for that teletype authority.
  14 |    ══════════════════════════════════════════════════════ */
  15 | @import url('https://fonts.googleapis.com/css2?family=Syne+Mono&family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  16 | 
  17 | :root {
  18 |   --s-bg:        #04050a;
  19 |   --s-surface:   #080b12;
  20 |   --s-border:    rgba(255,59,95,.18);
  21 |   --s-red:       #ff3b5f;
  22 |   --s-gold:      #f8c15c;
  23 |   --s-green:     #2eff8a;
  24 |   --s-muted:     rgba(255,255,255,.28);
  25 |   --s-mono:      'Syne Mono', 'JetBrains Mono', monospace;
  26 |   --s-head:      'Syne', sans-serif;
  27 | }
  28 | 
  29 | /* Page shell */
  30 | body { background: var(--s-bg); }
  31 | .stage-wrap {
  32 |   min-height: 100vh;
  33 |   background: var(--s-bg);
  34 |   background-image:
  35 |     radial-gradient(ellipse 60% 40% at 20% 10%, rgba(255,59,95,.07) 0%, transparent 60%),
  36 |     radial-gradient(ellipse 50% 35% at 80% 80%, rgba(248,193,92,.04) 0%, transparent 60%),
  37 |     repeating-linear-gradient(0deg,   rgba(255,59,95,.025) 0px, transparent 1px, transparent 39px, rgba(255,59,95,.025) 40px),
  38 |     repeating-linear-gradient(90deg,  rgba(255,59,95,.025) 0px, transparent 1px, transparent 39px, rgba(255,59,95,.025) 40px);
  39 |   padding: 0 0 80px;
  40 | }
  41 | 
  42 | /* ── TOP STATUS BAR ─────────────────────────────────── */
  43 | .stage-topbar {
  44 |   position: sticky; top: 0; z-index: 200;
  45 |   background: rgba(4,5,10,.92);
  46 |   backdrop-filter: blur(16px);
  47 |   border-bottom: 1px solid var(--s-border);
  48 |   display: flex; align-items: center; gap: 0;
  49 |   height: 42px; overflow: hidden;
  50 | }
  51 | .stage-topbar__live {
  52 |   display: flex; align-items: center; gap: 8px;
  53 |   padding: 0 20px; border-right: 1px solid var(--s-border);
  54 |   flex-shrink: 0;
  55 | }
  56 | .stage-topbar__dot {
  57 |   width: 8px; height: 8px; border-radius: 50%;
  58 |   background: var(--s-red);
  59 |   box-shadow: 0 0 6px var(--s-red);
  60 |   animation: live-pulse 1.4s ease-in-out infinite;
  61 | }
  62 | @keyframes live-pulse {
  63 |   0%,100% { opacity:1; box-shadow: 0 0 6px var(--s-red); }
  64 |   50%      { opacity:.5; box-shadow: 0 0 14px var(--s-red); }
  65 | }
  66 | .stage-topbar__label {
  67 |   font-family: var(--s-mono); font-size: 11px; letter-spacing:.18em;
  68 |   color: var(--s-red); text-transform: uppercase;
  69 | }
  70 | .stage-topbar__ticker {
  71 |   flex: 1; overflow: hidden; display: flex; align-items: center;
  72 |   padding: 0 16px;
  73 | }
  74 | .stage-topbar__ticker-inner {
  75 |   display: flex; gap: 40px; white-space: nowrap;
  76 |   animation: ticker-scroll 40s linear infinite;
  77 | }
  78 | .stage-topbar__ticker-inner:hover { animation-play-state: paused; }
  79 | @media (max-width: 768px) {
  80 |   .stage-topbar__ticker-inner {
  81 |     animation-duration: 90s;
  82 |   }
  83 | }
  84 | @keyframes ticker-scroll {
  85 |   0%   { transform: translateX(0); }
  86 |   100% { transform: translateX(-50%); }
  87 | }
  88 | .ticker-item {
  89 |   font-family: var(--s-mono); font-size: 11px;
  90 |   color: rgba(255,255,255,.5); letter-spacing: .06em;
  91 | }
  92 | .ticker-item .ti-label { color: var(--s-muted); margin-right: 6px; }
  93 | .ticker-item .ti-val   { color: rgba(255,255,255,.85); }
  94 | .ticker-item .ti-up    { color: var(--s-green); }
  95 | .ticker-item .ti-down  { color: var(--s-red); }
  96 | .ticker-item .ti-sep   { color: var(--s-border); margin: 0 8px; }
  97 | .stage-topbar__time {
  98 |   font-family: var(--s-mono); font-size: 11px;
  99 |   color: var(--s-gold); letter-spacing: .1em;
 100 |   padding: 0 20px; border-left: 1px solid var(--s-border);
 101 |   flex-shrink: 0;
 102 | }
 103 | 
 104 | /* ── PAGE HEADER ──────────────────────────────────────  */
 105 | .stage-header {
 106 |   display: flex; align-items: center; justify-content: space-between;
 107 |   padding: 28px 32px 20px;
 108 |   border-bottom: 1px solid var(--s-border);
 109 | }
 110 | .stage-header__title {
 111 |   font-family: var(--s-head); font-size: 11px; font-weight: 700;
 112 |   letter-spacing: .3em; text-transform: uppercase;
 113 |   color: var(--s-red);
 114 | }
 115 | .stage-header__sub {
 116 |   font-family: var(--s-mono); font-size: 10px;
 117 |   color: rgba(255,255,255,.3); letter-spacing: .12em;
 118 |   margin-top: 3px;
 119 | }
 120 | .stage-header__right {
 121 |   display: flex; align-items: center; gap: 12px;
 122 | }
 123 | .stage-badge {
 124 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 125 |   padding: 4px 10px; border-radius: 3px;
 126 |   text-transform: uppercase;
 127 | }
 128 | .stage-badge--on  { background: rgba(255,59,95,.12); color: var(--s-red); border: 1px solid rgba(255,59,95,.3); }
 129 | .stage-badge--ok  { background: rgba(46,255,138,.08); color: var(--s-green); border: 1px solid rgba(46,255,138,.2); }
 130 | 
 131 | /* ── MAIN GRID ──────────────────────────────────────── */
 132 | .stage-grid {
 133 |   display: flex;
 134 |   flex-direction: column;
 135 |   align-items: center;
 136 |   gap: 0;
 137 |   max-width: 1400px;
 138 |   margin: 0 auto;
 139 |   padding: 0 24px;
 140 | }
 141 | 
 142 | /* ── MAIN CONTENT (centered) ────────────────────────── */
 143 | .stage-main {
 144 |   width: 100%;
 145 |   display: flex;
 146 |   flex-direction: column;
 147 |   align-items: center;
 148 |   padding: 24px 0 0;
 149 | }
 150 | 
 151 | /* ── AVATAR DESK ─────────────────────────────────────── */
 152 | .stage-desk {
 153 |   width: 60vw;
 154 |   max-width: 900px;
 155 |   min-width: 320px;
 156 |   margin: 0 auto;
 157 |   position: relative;
 158 | }
 159 | @media (max-width: 768px) {
 160 |   .stage-desk { width: 100%; max-width: 100%; }
 161 | }
 162 | .stage-avatar-wrap {
 163 |   width: 100%;
 164 |   position: relative;
 165 |   background: radial-gradient(circle at 50% 100%, rgba(255,59,95,.08) 0%, transparent 60%),
 166 |               #06080f url('/static/img/oracle_avatar_static.png') center top / cover no-repeat;
 167 |   border: 1px solid rgba(0, 255, 200, 0.15);
 168 |   border-radius: 8px;
 169 |   overflow: hidden;
 170 |   aspect-ratio: 3/4;
 171 |   display: flex; align-items: flex-end; justify-content: center;
 172 |   box-shadow: 0 0 40px rgba(220,38,38,0.2), 0 0 80px rgba(220,38,38,0.06);
 173 | }
 174 | .stage-avatar-wrap::before {
 175 |   content: '';
 176 |   position: absolute; inset: 0;
 177 |   background: linear-gradient(to top, rgba(4,5,10,.8) 0%, transparent 40%);
 178 |   z-index: 2; pointer-events: none;
 179 | }
 180 | /* Desk surface */
 181 | .stage-avatar-wrap::after {
 182 |   content: '';
 183 |   position: absolute; bottom: 0; left: 0; right: 0; height: 28%;
 184 |   background: linear-gradient(to top, #0d1017 0%, rgba(13,16,23,.5) 70%, transparent 100%);
 185 |   z-index: 3; pointer-events: none;
 186 | }
 187 | .stage-avatar-vid {
 188 |   position: absolute; inset: 0; width: 100%; height: 100%;
 189 |   object-fit: cover; object-position: center top;
 190 |   display: block; z-index: 1;
 191 | }
 192 | .stage-avatar-nameplate {
 193 |   position: absolute; bottom: 12px; left: 12px; z-index: 10;
 194 |   display: flex; align-items: center; gap: 8px;
 195 | }
 196 | .stage-avatar-nameplate__dot {
 197 |   width: 6px; height: 6px; border-radius: 50%;
 198 |   background: var(--s-red); box-shadow: 0 0 5px var(--s-red);
 199 |   animation: live-pulse 1.4s ease-in-out infinite;
 200 | }
 201 | .stage-avatar-nameplate__name {
 202 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 203 |   color: rgba(255,255,255,.9); text-transform: uppercase;
 204 | }
 205 | 
 206 | /* ── BRIEF PANEL (right of avatar) ─────────────────── */
 207 | .stage-brief {
 208 |   display: flex; flex-direction: column; gap: 16px;
 209 | }
 210 | .stage-brief__section-label {
 211 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .22em;
 212 |   text-transform: uppercase; color: var(--s-muted);
 213 |   margin-bottom: 4px; display: flex; align-items: center; gap: 8px;
 214 | }
 215 | .stage-brief__section-label::after {
 216 |   content: ''; flex: 1; height: 1px;
 217 |   background: linear-gradient(to right, var(--s-border), transparent);
 218 | }
 219 | .stage-brief__sentiment {
 220 |   display: flex; align-items: center; gap: 12px;
 221 |   padding: 14px 16px;
 222 |   background: var(--s-surface); border: 1px solid var(--s-border);
 223 |   border-radius: 6px;
 224 | }
 225 | .stage-brief__sentiment-bar-wrap {
 226 |   flex: 1; height: 4px; background: rgba(255,255,255,.08);
 227 |   border-radius: 2px; overflow: hidden;
 228 | }
 229 | .stage-brief__sentiment-bar {
 230 |   height: 100%; border-radius: 2px;
 231 |   background: linear-gradient(to right, var(--s-red), var(--s-gold), var(--s-green));
 232 |   transition: width .6s ease;
 233 | }
 234 | .stage-brief__sentiment-score {
 235 |   font-family: var(--s-mono); font-size: 22px; font-weight: 600;
 236 |   line-height: 1; color: #fff; min-width: 36px; text-align: right;
 237 | }
 238 | .stage-brief__sentiment-label {
 239 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .12em;
 240 |   text-transform: uppercase; margin-top: 2px;
 241 | }
 242 | 
 243 | /* Narrative card */
 244 | .stage-narrative {
 245 |   padding: 14px 16px;
 246 |   background: var(--s-surface); border: 1px solid var(--s-border);
 247 |   border-left: 3px solid var(--s-red); border-radius: 6px;
 248 |   font-family: var(--s-head); font-size: 14px; font-weight: 500;
 249 |   line-height: 1.5; color: rgba(255,255,255,.82);
 250 |   position: relative;
 251 | }
 252 | .stage-narrative::before {
 253 |   content: 'ORACLE NARRATIVE';
 254 |   font-family: var(--s-mono); font-size: 8px; letter-spacing: .22em;
 255 |   color: var(--s-red); display: block; margin-bottom: 6px;
 256 | }
 257 | 
 258 | /* Topics */
 259 | .stage-topics {
 260 |   display: flex; flex-wrap: wrap; gap: 6px;
 261 | }
 262 | .stage-topic {
 263 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 264 |   padding: 4px 10px; border-radius: 3px;
 265 |   text-transform: uppercase; border: 1px solid;
 266 | }
 267 | .stage-topic--bull  { background: rgba(46,255,138,.07);  color: var(--s-green); border-color: rgba(46,255,138,.2); }
 268 | .stage-topic--bear  { background: rgba(255,59,95,.07);   color: var(--s-red);   border-color: rgba(255,59,95,.2);  }
 269 | .stage-topic--neut  { background: rgba(248,193,92,.07);  color: var(--s-gold);  border-color: rgba(248,193,92,.2); }
 270 | 
 271 | /* Playback controls */
 272 | .stage-controls {
 273 |   display: flex; gap: 8px; align-items: center;
 274 | }
 275 | .stage-btn {
 276 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .12em;
 277 |   text-transform: uppercase; padding: 8px 16px;
 278 |   border-radius: 4px; cursor: pointer; border: 1px solid;
 279 |   transition: all .15s; flex-shrink: 0;
 280 | }
 281 | .stage-btn--primary {
 282 |   background: var(--s-red); color: #fff; border-color: var(--s-red);
 283 | }
 284 | .stage-btn--primary:hover { background: #ff1a40; }
 285 | .stage-btn--ghost {
 286 |   background: transparent; color: rgba(255,255,255,.6); border-color: var(--s-border);
 287 | }
 288 | .stage-btn--ghost:hover { border-color: rgba(255,255,255,.3); color: #fff; }
 289 | .stage-btn:disabled { opacity: .35; cursor: not-allowed; }
 290 | .stage-status {
 291 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .1em;
 292 |   color: var(--s-muted); flex: 1; text-align: right;
 293 | }
 294 | .stage-status.speaking { color: var(--s-green); }
 295 | 
 296 | /* ── BRIEFING COUNTDOWN ──────────────────────────────  */
 297 | .stage-brief-countdown {
 298 |   background: var(--s-surface);
 299 |   border: 1px solid var(--s-border);
 300 |   border-radius: 8px;
 301 |   padding: 14px 16px;
 302 | }
 303 | .stage-brief-countdown__row {
 304 |   display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
 305 | }
 306 | .stage-brief-countdown__dot {
 307 |   width: 8px; height: 8px; border-radius: 50%;
 308 |   background: var(--s-muted); flex-shrink: 0;
 309 | }
 310 | .stage-brief-countdown__dot.ready {
 311 |   background: var(--s-red);
 312 |   animation: live-pulse 1.4s infinite;
 313 | }
 314 | .stage-brief-countdown__label {
 315 |   font-family: var(--s-mono); font-size: 9px;
 316 |   letter-spacing: .15em; color: var(--s-muted);
 317 | }
 318 | .stage-brief-countdown__timer {
 319 |   font-family: var(--s-mono); font-size: 28px;
 320 |   font-weight: 700; color: var(--s-gold);
 321 |   letter-spacing: .05em; line-height: 1.1;
 322 |   margin-bottom: 4px;
 323 | }
 324 | .stage-brief-countdown__timer.ready {
 325 |   color: var(--s-red);
 326 |   animation: brief-flash 2s ease-in-out infinite;
 327 | }
 328 | .stage-brief-countdown__sub {
 329 |   font-family: var(--s-mono); font-size: 10px;
 330 |   color: var(--s-muted); letter-spacing: .08em;
 331 | }
 332 | .stage-brief-countdown__play {
 333 |   margin-top: 10px; width: 100%;
 334 | }
 335 | @keyframes brief-flash {
 336 |   0%, 100% { opacity: 1; }
 337 |   50% { opacity: .6; }
 338 | }
 339 | 
 340 | /* ── CHANNEL TRANSCRIPTS ─────────────────────────────  */
 341 | .stage-transcripts {
 342 |   display: grid;
 343 |   grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
 344 |   gap: 12px;
 345 | }
 346 | /* Mobile: prevent iOS zoom + horizontal scroll carousel */
 347 | @media (max-width: 640px) {
 348 |   body { position: fixed; width: 100%; overflow: hidden; }
 349 |   .stage-wrap { overflow-y: auto; -webkit-overflow-scrolling: touch; height: 100vh; }
 350 |   .stage-transcripts {
 351 |     display: flex;
 352 |     flex-direction: row;
 353 |     overflow-x: auto;
 354 |     scroll-snap-type: x mandatory;
 355 |     -webkit-overflow-scrolling: touch;
 356 |     gap: 10px;
 357 |     padding-bottom: 12px;
 358 |     /* hide scrollbar but keep functionality */
 359 |     scrollbar-width: none;
 360 |   }
 361 |   .stage-transcripts::-webkit-scrollbar { display: none; }
 362 |   .stage-tx-card {
 363 |     flex: 0 0 82vw;          /* show ~1.1 cards at once = peek of next */
 364 |     max-width: 300px;
 365 |     scroll-snap-align: start;
 366 |     scroll-snap-stop: always;
 367 |   }
 368 |   /* Scroll hint dots */
 369 |   .stage-transcripts-wrap {
 370 |     position: relative;
 371 |   }
 372 |   .stage-tx-scroll-hint {
 373 |     display: flex;
 374 |     justify-content: center;
 375 |     gap: 5px;
 376 |     margin-top: 10px;
 377 |   }
 378 |   .stage-tx-scroll-hint span {
 379 |     width: 5px; height: 5px;
 380 |     border-radius: 50%;
 381 |     background: rgba(255,59,95,.25);
 382 |     transition: background .2s;
 383 |   }
 384 |   .stage-tx-scroll-hint span.active {
 385 |     background: var(--s-red);
 386 |   }
 387 |   /* Fade right edge to hint scrollability */
 388 |   .stage-brief__section-label + .stage-transcripts-wrap::after {
 389 |     content: '';
 390 |     position: absolute;
 391 |     right: 0; top: 0; bottom: 12px;
 392 |     width: 32px;
 393 |     background: linear-gradient(to right, transparent, var(--s-bg));
 394 |     pointer-events: none;
 395 |   }
 396 | }
 397 | .stage-tx-card {
 398 |   background: var(--s-surface);
 399 |   border: 1px solid var(--s-border);
 400 |   border-radius: 6px;
 401 |   padding: 14px 16px;
 402 |   transition: border-color .15s, transform .15s;
 403 |   cursor: default;
 404 | }
 405 | .stage-tx-card:hover {
 406 |   border-color: rgba(255,59,95,.35);
 407 |   transform: translateY(-1px);
 408 | }
 409 | .stage-tx-card__channel {
 410 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .18em;
 411 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 5px;
 412 | }
 413 | .stage-tx-card__title {
 414 |   font-family: var(--s-head); font-size: 13px; font-weight: 600;
 415 |   color: rgba(255,255,255,.9); line-height: 1.35; margin-bottom: 8px;
 416 | }
 417 | .stage-tx-card__excerpt {
 418 |   font-family: var(--s-head); font-size: 12px; font-weight: 400;
 419 |   color: rgba(255,255,255,.42); line-height: 1.5;
 420 | }
 421 | .stage-tx-card__footer {
 422 |   margin-top: 10px; padding-top: 8px;
 423 |   border-top: 1px solid rgba(255,255,255,.05);
 424 |   display: flex; justify-content: space-between; align-items: center;
 425 | }
 426 | .stage-tx-card__read-btn {
 427 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 428 |   text-transform: uppercase; color: var(--s-gold);
 429 |   background: none; border: none; cursor: pointer; padding: 0;
 430 |   transition: color .1s;
 431 | }
 432 | .stage-tx-card__read-btn:hover { color: #fff; }
 433 | .stage-tx-card__sentiment {
 434 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .08em;
 435 |   text-transform: uppercase;
 436 | }
 437 | 
 438 | /* ── SIDEBAR (now full-width below strip) ────────────  */
 439 | .stage-sidebar {
 440 |   width: 100%;
 441 |   max-width: 1100px;
 442 |   margin: 16px auto 0;
 443 |   display: grid;
 444 |   grid-template-columns: 1fr 1fr;
 445 |   gap: 16px;
 446 |   border-left: none;
 447 | }
 448 | @media (max-width: 768px) {
 449 |   .stage-sidebar { grid-template-columns: 1fr; }
 450 | }
 451 | .stage-panel {
 452 |   border-bottom: 1px solid var(--s-border);
 453 |   flex-shrink: 0;
 454 | }
 455 | .stage-panel__header {
 456 |   padding: 12px 16px; display: flex; align-items: center; justify-content: space-between;
 457 |   background: rgba(8,11,18,.7);
 458 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 459 |   text-transform: uppercase; color: rgba(255,255,255,.4);
 460 | }
 461 | .stage-panel__header-dot {
 462 |   width: 5px; height: 5px; border-radius: 50%;
 463 |   margin-right: 7px; display: inline-block; vertical-align: middle;
 464 | }
 465 | .stage-panel__body { padding: 12px 16px; }
 466 | 
 467 | /* Price panel */
 468 | .stage-price-big {
 469 |   font-family: var(--s-head); font-size: 36px; font-weight: 800;
 470 |   color: #fff; line-height: 1; letter-spacing: -.02em;
 471 | }
 472 | .stage-price-label {
 473 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 474 |   color: var(--s-muted); margin-top: 4px; text-transform: uppercase;
 475 | }
 476 | .stage-price-change {
 477 |   font-family: var(--s-mono); font-size: 12px;
 478 |   margin-top: 8px;
 479 | }
 480 | 
 481 | /* Nostr feed */
 482 | .stage-signal-feed {
 483 |   overflow-y: auto;
 484 |   max-height: 380px;
 485 |   scrollbar-width: thin;
 486 |   scrollbar-color: rgba(255,59,95,.2) transparent;
 487 | }
 488 | .stage-signal-item {
 489 |   padding: 10px 0;
 490 |   border-bottom: 1px solid rgba(255,255,255,.04);
 491 | }
 492 | .stage-signal-item:last-child { border-bottom: none; }
 493 | .stage-signal-item__author {
 494 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 495 |   color: var(--s-gold); margin-bottom: 4px;
 496 |   white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
 497 | }
 498 | .stage-signal-item__text {
 499 |   font-family: var(--s-head); font-size: 12px;
 500 |   color: rgba(255,255,255,.6); line-height: 1.45;
 501 |   display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
 502 |   overflow: hidden;
 503 | }
 504 | 
 505 | /* Transcript reader overlay */
 506 | .stage-reader {
 507 |   display: none; position: fixed; inset: 0;
 508 |   z-index: 500; background: rgba(4,5,10,.95);
 509 |   backdrop-filter: blur(8px);
 510 |   overflow-y: auto;
 511 |   padding: 40px 24px;
 512 | }
 513 | .stage-reader.open { display: block; }
 514 | .stage-reader__inner {
 515 |   max-width: 680px; margin: 0 auto;
 516 |   background: var(--s-surface); border: 1px solid var(--s-border);
 517 |   border-radius: 8px; padding: 32px;
 518 | }
 519 | .stage-reader__close {
 520 |   font-family: var(--s-mono); font-size: 10px; letter-spacing: .14em;
 521 |   text-transform: uppercase; color: var(--s-muted);
 522 |   background: none; border: none; cursor: pointer;
 523 |   margin-bottom: 20px; display: flex; align-items: center; gap: 6px;
 524 |   transition: color .1s;
 525 | }
 526 | .stage-reader__close:hover { color: #fff; }
 527 | .stage-reader__channel {
 528 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .2em;
 529 |   text-transform: uppercase; color: var(--s-red); margin-bottom: 8px;
 530 | }
 531 | .stage-reader__title {
 532 |   font-family: var(--s-head); font-size: 22px; font-weight: 700;
 533 |   color: #fff; line-height: 1.3; margin-bottom: 16px;
 534 | }
 535 | .stage-reader__body {
 536 |   font-family: var(--s-head); font-size: 14px; font-weight: 400;
 537 |   color: rgba(255,255,255,.68); line-height: 1.7;
 538 |   white-space: pre-wrap; word-break: break-word;
 539 | }
 540 | 
 541 | /* ── INTERACTIVE MODE PANEL ─────────────────────────────  */
 542 | .stage-interactive-panel {
 543 |   display: none;
 544 |   background: var(--s-surface);
 545 |   border: 1px solid var(--s-border);
 546 |   border-radius: 8px;
 547 |   padding: 16px;
 548 |   margin-top: 12px;
 549 | }
 550 | .stage-interactive-panel.active { display: block; }
 551 | .stage-mode-badge {
 552 |   font-family: var(--s-mono); font-size: 11px; letter-spacing: .14em;
 553 |   text-transform: uppercase; padding: 5px 14px; border-radius: 4px;
 554 |   display: inline-flex; align-items: center; gap: 8px;
 555 |   transition: all .3s;
 556 | }
 557 | .stage-mode-badge.broadcast {
 558 |   background: rgba(255,59,95,.12); color: var(--s-red);
 559 |   border: 1px solid rgba(255,59,95,.3);
 560 | }
 561 | .stage-mode-badge.interactive {
 562 |   background: rgba(46,255,138,.08); color: var(--s-green);
 563 |   border: 1px solid rgba(46,255,138,.2);
 564 | }
 565 | .stage-chat-input {
 566 |   display: flex; gap: 8px; margin-top: 12px;
 567 | }
 568 | .stage-chat-input input {
 569 |   flex: 1; background: rgba(255,255,255,.05);
 570 |   border: 1px solid var(--s-border); border-radius: 4px;
 571 |   padding: 10px 14px; color: #fff;
 572 |   font-family: var(--s-head); font-size: 13px;
 573 |   outline: none; transition: border-color .15s;
 574 | }
 575 | .stage-chat-input input:focus {
 576 |   border-color: rgba(255,59,95,.5);
 577 | }
 578 | .stage-chat-input input::placeholder {
 579 |   color: rgba(255,255,255,.25);
 580 | }
 581 | .stage-mic-btn {
 582 |   width: 44px; height: 44px; border-radius: 50%;
 583 |   background: rgba(255,59,95,.12); border: 1px solid rgba(255,59,95,.3);
 584 |   color: var(--s-red); cursor: pointer;
 585 |   display: flex; align-items: center; justify-content: center;
 586 |   font-size: 18px; transition: all .15s; flex-shrink: 0;
 587 | }
 588 | .stage-mic-btn:hover { background: rgba(255,59,95,.2); }
 589 | .stage-mic-btn.recording {
 590 |   background: var(--s-red); color: #fff;
 591 |   animation: mic-pulse 1.4s infinite;
 592 | }
 593 | @keyframes floating-mic-pulse {
 594 |   0%   { box-shadow: 0 0 0 0 rgba(255,59,95,.6); }
 595 |   70%  { box-shadow: 0 0 0 18px rgba(255,59,95,0); }
 596 |   100% { box-shadow: 0 0 0 0 rgba(255,59,95,0); }
 597 | }
 598 | #floatingMicBtn.fmic-rec {
 599 |   background: rgba(255,59,95,.25) !important;
 600 |   border-color: #ff3b5f !important;
 601 |   animation: floating-mic-pulse 1s ease-out infinite;
 602 | }
 603 | @keyframes mic-pulse {
 604 |   0% { box-shadow: 0 0 0 0 rgba(255,59,95,.6); }
 605 |   70% { box-shadow: 0 0 0 16px rgba(255,59,95,0); }
 606 |   100% { box-shadow: 0 0 0 0 rgba(255,59,95,0); }
 607 | }
 608 | .stage-chat-history {
 609 |   max-height: 180px; overflow-y: auto; margin-top: 10px;
 610 |   scrollbar-width: thin; scrollbar-color: rgba(255,59,95,.2) transparent;
 611 | }
 612 | .stage-chat-msg {
 613 |   font-family: var(--s-head); font-size: 12px;
 614 |   line-height: 1.5; padding: 6px 0;
 615 |   border-bottom: 1px solid rgba(255,255,255,.04);
 616 | }
 617 | .stage-chat-msg.user { color: var(--s-gold); }
 618 | .stage-chat-msg.oracle { color: rgba(255,255,255,.7); }
 619 | .stage-between-badge {
 620 |   font-family: var(--s-mono); font-size: 9px; letter-spacing: .1em;
 621 |   color: var(--s-muted); text-transform: uppercase;
 622 |   margin-top: 8px;
 623 | }
 624 | 
 625 | /* Animations */
 626 | @keyframes fadeUp {
 627 |   from { opacity:0; transform:translateY(12px); }
 628 |   to   { opacity:1; transform:translateY(0); }
 629 | }
 630 | .stage-desk     { animation: fadeUp .5s ease both; }
 631 | .stage-tx-card  { animation: fadeUp .5s ease both; }
 632 | .stage-tx-card:nth-child(2) { animation-delay: .05s; }
 633 | .stage-tx-card:nth-child(3) { animation-delay: .10s; }
 634 | .stage-tx-card:nth-child(4) { animation-delay: .15s; }
 635 | .stage-tx-card:nth-child(5) { animation-delay: .20s; }
 636 | .stage-tx-card:nth-child(6) { animation-delay: .25s; }
 637 | 
 638 | /* Loading shimmer */
 639 | .shimmer {
 640 |   background: linear-gradient(90deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.08) 50%, rgba(255,255,255,.04) 100%);
 641 |   background-size: 200% 100%;
 642 |   animation: shimmer 1.5s infinite;
 643 | }
 644 | @keyframes shimmer {
 645 |   0%   { background-position: -200% 0; }
 646 |   100% { background-position: 200% 0; }
 647 | }
 648 | 
 649 | /* ── DATA STRIP (below avatar) ────────────────────── */
 650 | .stage-data-strip {
 651 |   display: grid;
 652 |   grid-template-columns: 1fr 2fr 1fr;
 653 |   gap: 16px;
 654 |   width: 100%;
 655 |   max-width: 1100px;
 656 |   margin: 16px auto 0;
 657 |   padding: 0;
 658 | }
 659 | @media (max-width: 768px) {
 660 |   .stage-data-strip { grid-template-columns: 1fr; padding: 0; }
 661 | }
 662 | 
 663 | /* ── BELOW-STRIP SECTIONS (timed briefing, transcripts) ── */
 664 | .stage-below-strip {
 665 |   width: 100%;
 666 |   max-width: 1100px;
 667 |   margin: 16px auto 0;
 668 |   display: flex; flex-direction: column; gap: 16px;
 669 | }
 670 | 
 671 | /* ── STAGE WAKE READINESS ──────────────────────────── */
 672 | #stage-tap-label { transition: opacity 0.5s; }
 673 | .stage-wake-ready #stage-tap-label { animation: none; }
 674 | 
 675 | /* ── HOLOGRAM TREATMENT (stage avatar only) ─────────── */
 676 | /* (merged into .stage-avatar-wrap above) */
 677 | .stage-avatar-scanline {
 678 |   position: absolute; inset: 0;
 679 |   background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.06) 2px, rgba(0,0,0,0.06) 4px);
 680 |   pointer-events: none; z-index: 10;
 681 |   animation: scanline-drift 8s linear infinite;
 682 | }
 683 | @keyframes scanline-drift {
 684 |   from { background-position: 0 0; }
 685 |   to   { background-position: 0 100px; }
 686 | }
 687 | @keyframes pulse-dot {
 688 |   0%, 100% { opacity: 1; }
 689 |   50%      { opacity: 0.3; }
 690 | }
 691 | </style>
 692 | {% endblock %}
 693 | 
 694 | {% block scripts %}
 695 | <script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js" integrity="sha384-irMFAaNSIMAylOGwQzBdH2aFMly/VSIY7JChJO2GJwGCYJF2f3+K0wn+tmFLBX1H" crossorigin="anonymous"></script>
 696 | {% endblock %}
 697 | {% block content %}
 698 | <div class="stage-wrap">
 699 | 
 700 |   <!-- TOP STATUS BAR -->
 701 |   <div class="stage-topbar">
 702 |     <div class="stage-topbar__live">
 703 |       <div class="stage-topbar__dot"></div>
 704 |       <span class="stage-topbar__label">On Air</span>
 705 |     </div>
 706 |     <div class="stage-topbar__ticker">
 707 |       <div class="stage-topbar__ticker-inner" id="tickerInner">
 708 |         <span class="ticker-item">
 709 |           <span class="ti-label">BITCOIN</span>
 710 |           <span class="ti-val" id="tickerPrice">Loading…</span>
 711 |         </span>
 712 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 713 |         <span class="ticker-item">
 714 |           <span class="ti-label">SENTIMENT</span>
 715 |           <span class="ti-val" id="tickerSentiment">—</span>
 716 |         </span>
 717 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 718 |         <span class="ticker-item">
 719 |           <span class="ti-label">ORACLE</span>
 720 |           <span class="ti-val" id="tickerOracle">Standing By</span>
 721 |         </span>
 722 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 723 |         <span class="ticker-item">
 724 |           <span class="ti-label">NETWORK</span>
 725 |           <span class="ti-val" id="tickerTopics">—</span>
 726 |         </span>
 727 |         <!-- Duplicate for seamless loop -->
 728 |         <span class="ticker-item">
 729 |           <span class="ti-label">BITCOIN</span>
 730 |           <span class="ti-val" id="tickerPrice2">Loading…</span>
 731 |         </span>
 732 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 733 |         <span class="ticker-item">
 734 |           <span class="ti-label">SENTIMENT</span>
 735 |           <span class="ti-val" id="tickerSentiment2">—</span>
 736 |         </span>
 737 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 738 |         <span class="ticker-item">
 739 |           <span class="ti-label">ORACLE</span>
 740 |           <span class="ti-val">Standing By</span>
 741 |         </span>
 742 |         <span class="ticker-item"><span class="ti-sep">·</span></span>
 743 |         <span class="ticker-item">
 744 |           <span class="ti-label">NETWORK</span>
 745 |           <span class="ti-val" id="tickerTopics2">—</span>
 746 |         </span>
 747 |       </div>
 748 |     </div>
 749 |     <div class="stage-topbar__time" id="stageTime">—</div>
 750 |   </div>
 751 | 
 752 |   <!-- HEADER -->
 753 |   <div class="stage-header">
 754 |     <div>
 755 |       <div class="stage-header__title">⚡ Oracle Stage</div>
 756 |       <div class="stage-header__sub">LIVE BITCOIN INTELLIGENCE BROADCAST — PROTOCOLPULSE.IO</div>
 757 |     </div>
 758 |     <div class="stage-header__right">
 759 |       <div class="stage-badge stage-badge--on">● On Air</div>
 760 |       <div class="stage-badge stage-badge--ok" id="avatarStatusBadge">● Avatar Ready</div>
 761 |     </div>
 762 |   </div>
 763 | 
 764 |   <!-- MAIN GRID -->
 765 |   <div class="stage-grid">
 766 | 
 767 |     <!-- CENTERED: Avatar panel -->
 768 |     <div class="stage-main">
 769 |       <div class="stage-desk">
 770 |         <!-- ON AIR Badge -->
 771 |         <div id="onAirBadge" style="display:flex;align-items:center;gap:8px;padding:8px 14px;background:rgba(255,59,95,.08);border:1px solid rgba(255,59,95,.25);border-radius:6px 6px 0 0;border-bottom:none;">
 772 |           <span style="width:8px;height:8px;border-radius:50%;background:var(--s-red);box-shadow:0 0 6px var(--s-red);animation:live-pulse 1.4s ease-in-out infinite;"></span>
 773 |           <span style="font-family:var(--s-mono);font-size:11px;letter-spacing:.18em;color:var(--s-red);text-transform:uppercase;font-weight:700;">ON AIR</span>
 774 |           <span id="signalSourceLabel" style="font-family:var(--s-mono);font-size:10px;color:rgba(255,255,255,.5);letter-spacing:.08em;margin-left:8px;">📡 INITIALIZING</span>
 775 |           <span id="sessionTimer" style="margin-left:auto;font-family:var(--s-mono);font-size:10px;color:var(--s-gold);letter-spacing:.08em;">Broadcasting for <span id="sessionTime">0:00</span></span>
 776 |         </div>
 777 |         <!-- Avatar -->
 778 |         <div class="stage-avatar-wrap">
 779 |           <video class="stage-avatar-vid" id="avatarVid"
 780 |                  playsinline webkit-playsinline preload="auto"
 781 |                  style="display:block;opacity:1;"></video>
 782 |           <div id="stage-wake" style="display:none;position:absolute;inset:0;z-index:100;background:rgba(4,5,10,.85);flex-direction:column;align-items:center;justify-content:center;gap:16px;cursor:pointer;border-radius:4px;" onclick="stageWake()">
 783 |             <div style="font-size:48px;">&#9889;</div>
 784 |             <div id="stage-tap-label" style="font-family:var(--s-mono);font-size:12px;color:rgba(255,255,255,.8);letter-spacing:.2em;text-transform:uppercase;">Signal Warming Up<span id="stage-tap-dots" style="display:inline-block;width:1.5em;text-align:left;">.</span></div>
 785 |           </div>
 786 |           <div class="stage-avatar-scanline"></div>
 787 |           <div class="stage-avatar-nameplate">
 788 |             <div class="stage-avatar-nameplate__dot"></div>
 789 |             <div class="stage-avatar-nameplate__name">Oracle — Protocol Pulse</div>
 790 |           </div>
 791 |           <div style="position:absolute;bottom:14px;right:14px;z-index:50;display:flex;flex-direction:column;align-items:center;gap:5px;">
 792 |             <button id="floatingMicBtn"
 793 |               onclick="toggleStageMic()"
 794 |               title="Tap to interrupt Oracle"
 795 |               style="width:48px;height:48px;border-radius:50%;background:rgba(13,16,23,.85);border:2px solid rgba(255,59,95,.5);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:20px;transition:all .2s;backdrop-filter:blur(12px);">
 796 |               <span id="fmicIcon">&#9889;</span>
 797 |               <span id="fmicStop" style="display:none;font-size:16px;">&#9632;</span>
 798 |             </button>
 799 |             <span id="fmicHint" style="font-family:var(--s-mono);font-size:8px;color:rgba(255,255,255,.5);letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;">interrupt</span>
 800 |             <button id="stage-cam-btn"
 801 |               onclick="handleStageCameraInterrupt()"
 802 |               title="Photo question"
 803 |               style="width:48px;height:48px;border-radius:50%;background:rgba(13,16,23,.85);border:1px solid rgba(255,255,255,.12);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;transition:all .2s;backdrop-filter:blur(12px);margin-top:4px;">
 804 |               &#128247;
 805 |             </button>
 806 |             <input type="file" id="stage-cam-input" accept="image/*"
 807 |               capture="environment" style="display:none;"
 808 |               onchange="handleStageCameraUpload(event)">
 809 |           </div>
 810 |         </div>
 811 |         <div style="font-family:monospace;font-size:11px;color:#00ffc8;letter-spacing:3px;border-top:1px solid rgba(0,255,200,0.2);padding:6px 12px;background:rgba(0,0,0,0.8)">
 812 |           <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#DC2626;margin-right:8px;animation:pulse-dot 1.5s infinite"></span>
 813 |           PROTOCOL PULSE / ACTIVE
 814 |         </div>
 815 |       </div>
 816 |     </div><!-- /stage-main -->
 817 | 
 818 |     <!-- DATA STRIP: sentiment | narrative | topics + controls -->
 819 |     <div class="stage-data-strip">
 820 |       <!-- Column 1: Sentiment -->
 821 |       <div>
 822 |         <div class="stage-brief__section-label">Market Sentiment</div>
 823 |         <div class="stage-brief__sentiment">
 824 |           <div>
 825 |             <div class="stage-brief__sentiment-score" id="sentimentScore" role="status" aria-live="polite">—</div>
 826 |             <div class="stage-brief__sentiment-label" id="sentimentLabel">Loading</div>
 827 |           </div>
 828 |           <div style="flex:1">
 829 |             <div class="stage-brief__sentiment-bar-wrap">
 830 |               <div class="stage-brief__sentiment-bar" id="sentimentBar" style="width:50%"></div>
 831 |             </div>
 832 |             <div style="display:flex;justify-content:space-between;margin-top:4px">
 833 |               <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-red)">BEARISH</span>
 834 |               <span style="font-family:var(--s-mono);font-size:8px;color:var(--s-green)">BULLISH</span>
 835 |             </div>
 836 |           </div>
 837 |         </div>
 838 |       </div>
 839 | 
 840 |       <!-- Column 2: Narrative -->
 841 |       <div>
 842 |         <div class="stage-narrative" id="narrativeText">Loading Oracle narrative…</div>
 843 |       </div>
 844 | 
 845 |       <!-- Column 3: Topics + Broadcast buttons -->
 846 |       <div>
 847 |         <div class="stage-brief__section-label">Active Topics</div>
 848 |         <div class="stage-topics" id="topicsWrap">
 849 |           <span class="stage-topic stage-topic--neut shimmer" style="width:100px;height:20px;">&nbsp;</span>
 850 |         </div>
 851 |         <div style="margin-top:12px">
 852 |           <div class="stage-brief__section-label">Oracle Broadcast</div>
 853 |           <div class="stage-controls">
 854 |             <button class="stage-btn stage-btn--primary" id="briefBtn" onclick="requestBrief()" aria-label="Request daily Bitcoin briefing">
 855 |               ▶ Daily Brief
 856 |             </button>
 857 |             <div class="stage-status" id="stageStatus">Ready</div>
 858 |           </div>
 859 |         </div>
 860 |       </div>
 861 |     </div><!-- /stage-data-strip -->
 862 | 
 863 |     <!-- TIMED BRIEFING + INTERACTIVE -->
 864 |     <div class="stage-below-strip">
 865 |       <!-- Timed Briefing Countdown -->
 866 |       <div>
 867 |         <div class="stage-brief__section-label">Timed Briefing</div>
 868 |         <div id="briefingCountdown" class="stage-brief-countdown">
 869 |           <div class="stage-brief-countdown__row">
 870 |             <div class="stage-brief-countdown__dot" id="briefDot"></div>
 871 |             <div class="stage-brief-countdown__label">NEXT BRIEFING</div>
 872 |           </div>
 873 |           <div class="stage-brief-countdown__timer" id="countdownTimer">&mdash;</div>
 874 |           <div class="stage-brief-countdown__sub" id="countdownSub">Checking schedule&hellip;</div>
 875 |           <button class="stage-btn stage-btn--primary stage-brief-countdown__play"
 876 |                   id="briefPlayBtn" style="display:none"
 877 |                   onclick="playLatestBrief()">&#9654; Play Brief</button>
 878 |         </div>
 879 |       </div>
 880 | 
 881 |       <!-- Mode switching -->
 882 |       <div>
 883 |         <div class="stage-brief__section-label">Stage Mode</div>
 884 |         <div id="stageModeBadge" class="stage-mode-badge broadcast">● ON AIR</div>
 885 |         <div class="stage-between-badge" id="betweenBadge" style="display:none">
 886 |           BETWEEN SEGMENTS — <span id="betweenCountdown">--:--</span> until next briefing
 887 |         </div>
 888 |       </div>
 889 | 
 890 |       <!-- Interactive Oracle Panel (visible between briefings) -->
 891 |       <div id="interactivePanel" class="stage-interactive-panel">
 892 |         <div style="font-family:var(--s-mono);font-size:9px;letter-spacing:.15em;color:var(--s-muted);text-transform:uppercase;margin-bottom:8px">Ask Oracle Anything</div>
 893 |         <div class="stage-chat-input">
 894 |           <input type="text" id="stageChatInput" placeholder="Ask about Bitcoin..."
 895 |                  onkeydown="if(event.key==='Enter')stageChat()">
 896 |           <button class="stage-mic-btn" id="stageMicBtn" onclick="toggleStageMic()" title="Tap to speak" aria-label="Push to speak — tap to ask Oracle a question" role="button">&#127908;</button>
 897 |           <button class="stage-btn stage-btn--primary" onclick="stageChat()" style="padding:8px 14px">&#9654;</button>
 898 |         </div>
 899 |         <div class="stage-chat-history" id="stageChatHistory"></div>
 900 |       </div>
 901 |     </div><!-- /stage-below-strip -->
 902 | 
 903 |     <!-- PARTNER CHANNEL INTELLIGENCE -->
 904 |     <div class="stage-below-strip">
 905 |       <div class="stage-brief__section-label">Partner Channel Intelligence</div>
 906 |       <div class="stage-transcripts-wrap">
 907 |         <div class="stage-transcripts" id="transcriptsGrid">
 908 |           <!-- Skeleton loaders -->
 909 |           {% for i in range(6) %}
 910 |           <div class="stage-tx-card shimmer" style="height:140px;"></div>
 911 |           {% endfor %}
 912 |         </div>
 913 |         <div id="txDots" class="stage-tx-scroll-hint"></div>
 914 |       </div>
 915 |     </div>
 916 | 
 917 |     <!-- SIDEBAR: Price + Nostr (now full-width row) -->
 918 |     <div class="stage-sidebar">
 919 | 
 920 |       <!-- Price Panel -->
 921 |       <div class="stage-panel">
 922 |         <div class="stage-panel__header">
 923 |           <span><span class="stage-panel__header-dot" style="background:var(--s-gold)"></span>Bitcoin Price</span>
 924 |           <span id="priceUpdated" style="font-size:8px;color:rgba(255,255,255,.2)">live</span>
 925 |         </div>
 926 |         <div class="stage-panel__body">
 927 |           <div class="stage-price-big" id="sidebarPrice" role="status" aria-live="polite">—</div>
 928 |           <div class="stage-price-label">USD</div>
 929 |           <div class="stage-price-change" id="sidebarSentimentLine" role="status" aria-live="polite">—</div>
 930 |         </div>
 931 |       </div>
 932 | 
 933 |       <!-- Nostr Signal Panel -->
 934 |       <div class="stage-panel" style="overflow:hidden;display:flex;flex-direction:column;">
 935 |         <div class="stage-panel__header">
 936 |           <span><span class="stage-panel__header-dot" style="background:var(--s-red);animation:live-pulse 1.4s infinite"></span>Nostr Signal</span>
 937 |           <span id="nostrCount" style="font-size:8px;color:rgba(255,255,255,.3)">0 posts</span>
 938 |         </div>
 939 |         <div class="stage-panel__body stage-signal-feed" id="nostrFeed">
 940 |           <div style="font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0">
 941 |             Loading signal…
 942 |           </div>
 943 |         </div>
 944 |       </div>
 945 | 
 946 |     </div><!-- /stage-sidebar -->
 947 |   </div><!-- /stage-grid -->
 948 | 
 949 |   <!-- BROADCAST TICKER (bottom strip) -->
 950 |   <div id="broadcastTicker" style="position:fixed;bottom:0;left:0;right:0;z-index:200;background:rgba(4,5,10,.95);border-top:1px solid var(--s-border);padding:8px 20px;display:flex;align-items:center;gap:12px;backdrop-filter:blur(8px);">
 951 |     <span style="font-family:var(--s-mono);font-size:9px;letter-spacing:.18em;color:var(--s-red);text-transform:uppercase;flex-shrink:0;font-weight:700;">UP NEXT</span>
 952 |     <div id="tickerContent" style="font-family:var(--s-mono);font-size:10px;color:rgba(255,255,255,.6);letter-spacing:.06em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;">Loading broadcast queue...</div>
 953 |   </div>
 954 | </div><!-- /stage-wrap -->
 955 | 
 956 | <!-- Transcript Reader Overlay -->
 957 | <div class="stage-reader" id="stageReader">
 958 |   <div class="stage-reader__inner">
 959 |     <button class="stage-reader__close" onclick="closeReader()">
 960 |       ← Back to Stage
 961 |     </button>
 962 |     <div class="stage-reader__channel" id="readerChannel"></div>
 963 |     <div class="stage-reader__title" id="readerTitle"></div>
 964 |     <div class="stage-reader__body" id="readerBody"></div>
 965 |   </div>
 966 | </div>
 967 | 
 968 | <script>
 969 | (function(){
 970 |   'use strict';
 971 | 
 972 |   // ── CONFIG ────────────────────────────────────────────
 973 |   var AVATAR_BASE = 'https://avatar.protocolpulse.io';
 974 |   var busy = false;
 975 |   var objURL = null;
 976 |   var _isMobileBrowser = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
 977 |   var vid = document.getElementById('avatarVid');
 978 |   var briefBtn = document.getElementById('briefBtn');
 979 |   var statusEl = document.getElementById('stageStatus');
 980 |   var badgeEl  = document.getElementById('avatarStatusBadge');
 981 | 
 982 |   // ── SAFE TEXT HELPER (P0.2: replaces old esc()) ────────
 983 |   // Use textContent for all plain text. For rare intentional HTML, use DOMPurify.
 984 |   function safeText(el, text) {
 985 |     if (el) el.textContent = String(text || '');
 986 |   }
 987 |   function cleanScript(raw){
 988 |     if(!raw) return '';
 989 |     return raw.replace(/^#+\s+[^\n]*/gm,'').replace(/^---+\s*$/gm,'').replace(/\*\*([^*]+)\*\*/g,'$1').replace(/\n{3,}/g,'\n\n').trim();
 990 |   }
 991 |   function safeHTML(el, html) {
 992 |     if (el && typeof DOMPurify !== 'undefined') {
 993 |       el.innerHTML = DOMPurify.sanitize(html, {ALLOWED_TAGS: ['span','b','em','strong'], ALLOWED_ATTR: ['style','class']});
 994 |     } else if (el) {
 995 |       el.textContent = String(html || '');
 996 |     }
 997 |   }
 998 | 
 999 |   // ── 429 HANDLER (P0.1: server-side rate limiting) ──────
1000 |   function handle429(resp) {
1001 |     if (resp.status === 429) {
1002 |       var retryAfter = resp.headers.get('Retry-After') || '30';
1003 |       var secs = parseInt(retryAfter, 10) || 30;
1004 |       setStatus('Too many requests — wait ' + secs + 's', 'var(--s-red)');
1005 |       return true;
1006 |     }
1007 |     return false;
1008 |   }
1009 | 
1010 |   // ── SESSION TIMER ─────────────────────────────────────
1011 |   var _sessionStart = Date.now();
1012 |   function updateSessionTimer() {
1013 |     var elapsed = Math.floor((Date.now() - _sessionStart) / 1000);
1014 |     var h = Math.floor(elapsed / 3600);
1015 |     var m = Math.floor((elapsed % 3600) / 60);
1016 |     var s = elapsed % 60;
1017 |     var el = document.getElementById('sessionTime');
1018 |     if (el) el.textContent = (h > 0 ? h + ':' : '') + pad(m) + ':' + pad(s);
1019 |   }
1020 | 
1021 |   // ── CLOCK ────────────────────────────────────────────
1022 |   function tick(){
1023 |     var now = new Date();
1024 |     safeText(document.getElementById('stageTime'), now.toUTCString().slice(17,22) + ' UTC');
1025 |     updateSessionTimer();
1026 |   }
1027 |   tick(); setInterval(tick, 1000);
1028 | 
1029 |   // ── LAST UPDATED INDICATOR (P1.4) ────────────────────
1030 |   var _lastIntelUpdate = 0;
1031 |   var _lastNostrUpdate = 0;
1032 |   function updateStaleness() {
1033 |     var now = Date.now();
1034 |     if (_lastIntelUpdate) {
1035 |       var ago = Math.floor((now - _lastIntelUpdate) / 1000);
1036 |       var el = document.getElementById('priceUpdated');
1037 |       if (el) el.textContent = ago < 10 ? 'just now' : ago + 's ago';
1038 |     }
1039 |   }
1040 |   setInterval(updateStaleness, 5000);
1041 | 
1042 |   // ── FETCH INTEL ───────────────────────────────────────
1043 |   function loadIntel(){
1044 |     fetch('/api/stage/intel')
1045 |     .then(function(r){ return r.json(); })
1046 |     .then(function(d){
1047 |       _lastIntelUpdate = Date.now();
1048 |       // price
1049 |       var price = d.price || '';
1050 |       updatePrice(price, d.price_float);
1051 |       // sentiment
1052 |       var score = d.sentiment_score || 50;
1053 |       var label = d.sentiment_label || 'neutral';
1054 |       safeText(document.getElementById('sentimentScore'), score);
1055 |       safeText(document.getElementById('sentimentLabel'), label.toUpperCase());
1056 |       document.getElementById('sentimentBar').style.width = score + '%';
1057 |       var sentColor = score > 60 ? 'var(--s-green)' : score < 40 ? 'var(--s-red)' : 'var(--s-gold)';
1058 |       document.getElementById('sentimentScore').style.color = sentColor;
1059 |       document.getElementById('sentimentLabel').style.color = sentColor;
1060 |       // ticker (P0.2: textContent only)
1061 |       safeText(document.getElementById('tickerPrice'), price);
1062 |       safeText(document.getElementById('tickerPrice2'), price);
1063 |       safeText(document.getElementById('tickerSentiment'), label.toUpperCase() + ' ' + score + '/100');
1064 |       safeText(document.getElementById('tickerSentiment2'), label.toUpperCase() + ' ' + score + '/100');
1065 |       // sidebar sentiment line (P0.2: was innerHTML, now safe DOM construction)
1066 |       var sentLine = document.getElementById('sidebarSentimentLine');
1067 |       if (sentLine) {
1068 |         sentLine.textContent = '';
1069 |         var span = document.createElement('span');
1070 |         span.style.cssText = 'color:'+sentColor+';font-family:var(--s-mono);font-size:11px';
1071 |         span.textContent = label.toUpperCase() + ' — ' + score + '/100';
1072 |         sentLine.appendChild(span);
1073 |       }
1074 |       // narrative
1075 |       if(d.narrative){
1076 |         safeText(document.getElementById('narrativeText'), d.narrative);
1077 |       }
1078 |       // topics
1079 |       if(d.topics){
1080 |         renderTopics(d.topics);
1081 |         var topicsText = d.topics.replace(/\([^)]+\)/g,'').replace(/,/g,' ·');
1082 |         safeText(document.getElementById('tickerTopics'), topicsText);
1083 |         safeText(document.getElementById('tickerTopics2'), topicsText);
1084 |       }
1085 |     })
1086 |     .catch(function(){
1087 |       safeText(document.getElementById('narrativeText'), 'Intel feed offline — retrying in 30s');
1088 |       safeText(document.getElementById('tickerOracle'), 'Offline');
1089 |     });
1090 |   }
1091 | 
1092 |   function updatePrice(priceStr, priceFloat){
1093 |     if(!priceStr) return;
1094 |     var fmt = priceFloat ? '$' + Number(priceFloat).toLocaleString('en-US',{maximumFractionDigits:0}) : priceStr;
1095 |     safeText(document.getElementById('sidebarPrice'), fmt);
1096 |     safeText(document.getElementById('tickerPrice'), fmt);
1097 |     safeText(document.getElementById('tickerPrice2'), fmt);
1098 |   }
1099 | 
1100 |   function renderTopics(topicsStr){
1101 |     var wrap = document.getElementById('topicsWrap');
1102 |     wrap.innerHTML = '';
1103 |     var parts = topicsStr.split(',');
1104 |     parts.forEach(function(t){
1105 |       t = t.trim();
1106 |       var cls = 'stage-topic--neut';
1107 |       if(t.indexOf('(bullish)')>=0 || t.indexOf('bullish')>=0) cls = 'stage-topic--bull';
1108 |       if(t.indexOf('(bearish)')>=0 || t.indexOf('bearish')>=0) cls = 'stage-topic--bear';
1109 |       var label = t.replace(/\s*\([^)]+\)\s*/g,'').trim();
1110 |       var span = document.createElement('span');
1111 |       span.className = 'stage-topic ' + cls;
1112 |       span.textContent = label;
1113 |       wrap.appendChild(span);
1114 |     });
1115 |   }
1116 | 
1117 |   // ── LOAD TRANSCRIPTS (P0.2: no innerHTML with external data) ───
1118 |   function loadTranscripts(){
1119 |     fetch('/api/stage/transcripts')
1120 |     .then(function(r){ return r.json(); })
1121 |     .then(function(data){
1122 |       renderTranscripts(data);
1123 |     })
1124 |     .catch(function(){
1125 |       renderTranscripts([]);
1126 |     });
1127 |   }
1128 | 
1129 |   function renderTranscripts(items){
1130 |     var grid = document.getElementById('transcriptsGrid');
1131 |     if(!items || !items.length){
1132 |       grid.textContent = '';
1133 |       var msg = document.createElement('div');
1134 |       msg.style.cssText = 'grid-column:1/-1;font-family:var(--s-mono);font-size:11px;color:var(--s-muted);padding:20px 0';
1135 |       msg.textContent = 'No transcript data available yet. Channel scan in progress.';
1136 |       grid.appendChild(msg);
1137 |       document.dispatchEvent(new CustomEvent('transcriptsRendered'));
1138 |       return;
1139 |     }
1140 |     grid.textContent = '';
1141 |     items.forEach(function(item){
1142 |       var sentCls = 'stage-topic--neut';
1143 |       var sentLabel = item.sentiment || 'neutral';
1144 |       if(sentLabel === 'bullish') sentCls = 'stage-topic--bull';
1145 |       if(sentLabel === 'bearish') sentCls = 'stage-topic--bear';
1146 |       var card = document.createElement('div');
1147 |       card.className = 'stage-tx-card';
1148 | 
1149 |       // P0.2: Build DOM elements, never innerHTML with external data
1150 |       var chDiv = document.createElement('div');
1151 |       chDiv.className = 'stage-tx-card__channel';
1152 |       chDiv.textContent = (item.channel || 'Unknown');
1153 |       card.appendChild(chDiv);
1154 | 
1155 |       var titleDiv = document.createElement('div');
1156 |       titleDiv.className = 'stage-tx-card__title';
1157 |       titleDiv.textContent = (item.title || '').slice(0, 70);
1158 |       card.appendChild(titleDiv);
1159 | 
1160 |       var excerptDiv = document.createElement('div');
1161 |       excerptDiv.className = 'stage-tx-card__excerpt';
1162 |       excerptDiv.textContent = (item.excerpt || item.transcript_snippet || '').slice(0, 120) + '…';
1163 |       card.appendChild(excerptDiv);
1164 | 
1165 |       var footer = document.createElement('div');
1166 |       footer.className = 'stage-tx-card__footer';
1167 |       var readBtn = document.createElement('button');
1168 |       readBtn.className = 'stage-tx-card__read-btn';
1169 |       readBtn.textContent = 'Read Brief →';
1170 |       readBtn.setAttribute('aria-label', 'Read full transcript for ' + (item.channel || 'this channel'));
1171 |       readBtn.addEventListener('click', function(){ openReader(this); });
1172 |       footer.appendChild(readBtn);
1173 |       var sentSpan = document.createElement('span');
1174 |       sentSpan.className = 'stage-topic ' + sentCls;
1175 |       sentSpan.textContent = sentLabel;
1176 |       footer.appendChild(sentSpan);
1177 |       card.appendChild(footer);
1178 | 
1179 |       // Store data on card
1180 |       card.dataset.channel = item.channel || '';
1181 |       card.dataset.title = item.title || '';
1182 |       card.dataset.body = item.transcript_text || item.excerpt || '';
1183 |       grid.appendChild(card);
1184 |     });
1185 |     // P0.4: Custom event instead of monkey-patching
1186 |     document.dispatchEvent(new CustomEvent('transcriptsRendered'));
1187 |   }
1188 | 
1189 |   // ── NOSTR SIGNAL ──────────────────────────────────────
1190 |   function loadNostr(){
1191 |     fetch('/api/stage/signal')
1192 |     .then(function(r){ return r.json(); })
1193 |     .then(function(d){
1194 |       _lastNostrUpdate = Date.now();
1195 |       var posts = d.nostr_posts || [];
1196 |       renderNostr(posts);
1197 |     })
1198 |     .catch(function(){
1199 |       renderNostr([]);
1200 |       safeText(document.getElementById('nostrCount'), 'offline');
1201 |     });
1202 |   }
1203 | 
1204 |   function renderNostr(posts){
1205 |     var feed = document.getElementById('nostrFeed');
1206 |     safeText(document.getElementById('nostrCount'), posts.length + ' posts');
1207 |     if(!posts.length){
1208 |       feed.textContent = '';
1209 |       var msg = document.createElement('div');
1210 |       msg.style.cssText = 'font-family:var(--s-mono);font-size:10px;color:var(--s-muted);text-align:center;padding:20px 0';
1211 |       msg.textContent = 'No signal yet — relay scanning…';
1212 |       feed.appendChild(msg);
1213 |       return;
1214 |     }
1215 |     feed.textContent = '';
1216 |     posts.slice(0,12).forEach(function(p){
1217 |       var item = document.createElement('div');
1218 |       item.className = 'stage-signal-item';
1219 |       var author = p.nip05 || p.display_name || 'anon';
1220 |       var aDiv = document.createElement('div');
1221 |       aDiv.className = 'stage-signal-item__author';
1222 |       aDiv.textContent = author.slice(0,50);
1223 |       var tDiv = document.createElement('div');
1224 |       tDiv.className = 'stage-signal-item__text';
1225 |       tDiv.textContent = (p.text||'').slice(0,180);
1226 |       item.appendChild(aDiv);
1227 |       item.appendChild(tDiv);
1228 |       feed.appendChild(item);
1229 |     });
1230 |   }
1231 | 
1232 |   // ── TRANSCRIPT READER ─────────────────────────────────
1233 |   window.openReader = function(btn){
1234 |     var card = btn.closest('.stage-tx-card');
1235 |     safeText(document.getElementById('readerChannel'), card.dataset.channel);
1236 |     safeText(document.getElementById('readerTitle'), card.dataset.title);
1237 |     safeText(document.getElementById('readerBody'), card.dataset.body || 'Full transcript not available.');
1238 |     document.getElementById('stageReader').classList.add('open');
1239 |     document.body.style.overflow = 'hidden';
1240 |   };
1241 |   window.closeReader = function(){
1242 |     document.getElementById('stageReader').classList.remove('open');
1243 |     document.body.style.overflow = '';
1244 |   };
1245 | 
1246 |   // ── AVATAR PLAYBACK ───────────────────────────────────
1247 |   function setStatus(msg, color){
1248 |     safeText(statusEl, msg);
1249 |     statusEl.style.color = color || 'rgba(255,255,255,.3)';
1250 |     statusEl.className = 'stage-status' + (msg==='Speaking' ? ' speaking' : '');
1251 |     tickerOracle(msg);
1252 |   }
1253 |   function tickerOracle(msg){
1254 |     safeText(document.getElementById('tickerOracle'), msg);
1255 |   }
1256 |   function setBusy(b){
1257 |     busy = b;
1258 |     briefBtn.disabled = b;
1259 |     safeText(badgeEl, b ? '● Rendering…' : '● Avatar Ready');
1260 |     badgeEl.style.color = b ? 'var(--s-gold)' : 'var(--s-green)';
1261 |     badgeEl.style.borderColor = b ? 'rgba(248,193,92,.3)' : 'rgba(46,255,138,.2)';
1262 |     badgeEl.style.background  = b ? 'rgba(248,193,92,.08)' : 'rgba(46,255,138,.08)';
1263 |   }
1264 | 
1265 |   // P1.5: revokeObjectURL in finally block with null check
1266 |   function revokeObjURL() {
1267 |     if (objURL) {
1268 |       try { URL.revokeObjectURL(objURL); } catch(e) {}
1269 |       objURL = null;
1270 |     }
1271 |   }
1272 | 
1273 |   function playAudioOnly(audioUrl) {
1274 |     return new Promise(function(resolve) {
1275 |       var audio;
1276 |       if (window._stageAudioUnlocked) {
1277 |         audio = window._stageAudioUnlocked;
1278 |         window._stageAudioUnlocked = null;
1279 |         // Re-unlock immediately for the NEXT segment
1280 |         var nextUnlock = new Audio();
1281 |         nextUnlock.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1282 |         nextUnlock.volume = 0.001;
1283 |         nextUnlock.play().catch(function(){});
1284 |         window._stageAudioUnlocked = nextUnlock;
1285 |         audio.src = audioUrl;
1286 |         audio.volume = 1.0;
1287 |         audio.muted = false;
1288 |       } else {
1289 |         audio = new Audio(audioUrl);
1290 |         audio.volume = 1.0;
1291 |       }
1292 |       setStatus('Broadcasting…', 'var(--s-green)');
1293 |       audio.onended = function() {
1294 |         URL.revokeObjectURL(audioUrl);
1295 |         setStatus('Ready', 'rgba(255,255,255,.3)');
1296 |         setBusy(false);
1297 |         resolve();
1298 |       };
1299 |       audio.onerror = function() {
1300 |         setBusy(false);
1301 |         resolve();
1302 |       };
1303 |       audio.play().catch(function(e) {
1304 |         console.warn('[Stage mobile] audio.play() rejected:', e.name);
1305 |         setBusy(false);
1306 |         resolve();
1307 |       });
1308 |     });
1309 |   }
1310 | 
1311 |   function playVid(url){
1312 |     return new Promise(function(resolve, reject){
1313 |       revokeObjURL();
1314 |       objURL = url;
1315 |       vid.src = url;
1316 |       vid.muted = true;
1317 |       vid.volume = 1.0;
1318 |       setStatus('Speaking','var(--s-green)');
1319 |       var unmuted = false;
1320 |       function tryUnmute(){ if(unmuted) return; unmuted=true; vid.muted=false; vid.volume=1.0; try { vid.play(); } catch(e) {} }
1321 |       vid.addEventListener('canplay', function oncp(){
1322 |         vid.removeEventListener('canplay',oncp);
1323 |         tryUnmute();
1324 |       },{once:true});
1325 |       vid.onended = function(){
1326 |         vid.src='';
1327 |         setStatus('Ready','rgba(255,255,255,.3)');
1328 |         setBusy(false);
1329 |         revokeObjURL();
1330 |         resolve();
1331 |       };
1332 |       vid.onerror = function(){
1333 |         setBusy(false);
1334 |         revokeObjURL();
1335 |         reject(new Error('Video playback failed'));
1336 |       };
1337 |       var p = vid.play();
1338 |       if(p){
1339 |         p.then(function(){
1340 |           setTimeout(tryUnmute, 50);
1341 |         }).catch(function(err){
1342 |           console.warn('[Stage] vid.play() rejected:', err.name);
1343 |           try{
1344 |             var ac=new(window.AudioContext||window.webkitAudioContext)();
1345 |             var buf=ac.createBuffer(1,1,22050);
1346 |             var src=ac.createBufferSource();
1347 |             src.buffer=buf;src.connect(ac.destination);src.start(0);
1348 |             setTimeout(function(){try{ac.close();}catch(e){}},200);
1349 |           }catch(e){}
1350 |           setTimeout(function(){
1351 |             vid.muted=false;
1352 |             vid.play().catch(function(){
1353 |               setStatus('Tap avatar to play','var(--s-gold)');
1354 |               vid.addEventListener('click',function(){vid.muted=false;vid.play();},{once:true});
1355 |             });
1356 |           },300);
1357 |         });
1358 |       }
1359 |     });
1360 |   }
1361 | 
1362 |   function fetchTO(url, opts, ms){
1363 |     var ctrl = new AbortController();
1364 |     var id = setTimeout(function(){ ctrl.abort(); }, ms||30000);
1365 |     var o = opts||{}; o.signal = ctrl.signal;
1366 |     return fetch(url, o).finally(function(){ clearTimeout(id); });
1367 |   }
1368 | 
1369 |   // ── REQUEST BRIEF (P0.1: routes through rate-limited proxy) ───
1370 |   var _briefCooldown = 0;
1371 |   window.requestBrief = function(){
1372 |     if(busy) return;
1373 |     var now = Date.now();
1374 |     if(now - _briefCooldown < 10000){ setStatus('Please wait…','var(--s-gold)'); return; }
1375 |     _briefCooldown = now;
1376 |     setBusy(true); setStatus('Fetching brief…','var(--s-gold)');
1377 |     fetchTO('/api/oracle/speak',{
1378 |       method:'POST', headers:{'Content-Type':'application/json'},
1379 |       body: JSON.stringify({intent:'DAILY_BRIEF'})
1380 |     }, 60000)
1381 |     .then(function(r){
1382 |       if(handle429(r)) throw new Error('rate-limited');
1383 |       if(!r.ok) throw new Error('HTTP '+r.status);
1384 |       return r.blob().then(function(b){ return URL.createObjectURL(b); });
1385 |     })
1386 |     .then(function(url){ return playVid(url); })
1387 |     .catch(function(e){
1388 |       if(e.message !== 'rate-limited') setStatus('Error — try again','var(--s-red)');
1389 |       console.error(e);
1390 |     })
1391 |     .finally(function(){ setBusy(false); });
1392 |   };
1393 | 
1394 | 
1395 |   // ── BROADCAST SYSTEM ──────────────────────────────────
1396 |   var STAGE_MODE = 'broadcast';
1397 |   var _stageSessionId = 'stage_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
1398 |   var _stageRecognition = null;
1399 |   var _stageIsRec = false;
1400 |   var _currentBroadcastTopic = '';
1401 |   var _preRenderedBlob = null;
1402 |   var _preRenderedItem = null;
1403 |   var _broadcastPaused = false;
1404 |   var _preRenderFirstBlob = null;
1405 |   var _preRenderReady = false;
1406 |   var _preRenderScript = null;
1407 | 
1408 |   async function preRenderFirstSegment() {
1409 |     try {
1410 |       var scriptResp = await fetch('/api/stage/generate-monologue', {
1411 |         method: 'POST',
1412 |         headers: {'Content-Type': 'application/json'}
1413 |       });
1414 |       if (!scriptResp.ok) return;
1415 |       var scriptData = await scriptResp.json();
1416 |       var script = scriptData.script;
1417 |       if (!script) return;
1418 |       _preRenderScript = script;
1419 | 
1420 |       var renderResp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
1421 |         method: 'POST',
1422 |         headers: {'Content-Type': 'application/json'},
1423 |         body: JSON.stringify({text: cleanScript(script), intent: 'BROADCAST_SEGMENT'})
1424 |       }, 120000);
1425 |       if (!renderResp.ok) return;
1426 | 
1427 |       var blob = await renderResp.blob();
1428 |       _preRenderFirstBlob = URL.createObjectURL(blob);
1429 |       _preRenderReady = true;
1430 |       console.log('[Stage] Pre-render complete — ready for tap');
1431 |     } catch(e) {
1432 |       console.warn('[Stage] Pre-render failed:', e);
1433 |     }
1434 |   }
1435 | 
1436 |   // ── BROADCAST QUEUE CONSUMER ──────────────────────────
1437 |   async function startBroadcast() {
1438 |     await runMonologueLoop();
1439 |   }
1440 | 
1441 |   function updateSignalSource(label) {
1442 |     var el = document.getElementById('signalSourceLabel');
1443 |     if (el) el.textContent = label;
1444 |   }
1445 | 
1446 |   function updateTicker(currentItem) {
1447 |     var tickerEl = document.getElementById('tickerContent');
1448 |     if (!tickerEl) return;
1449 |     tickerEl.textContent = currentItem ? ('NOW: ' + currentItem.topic_preview) : 'Loading next segment...';
1450 |   }
1451 | 
1452 |   async function playBroadcastItem(item) {
1453 |     if (_broadcastPaused) return;
1454 |     _currentBroadcastTopic = item.topic_preview || '';
1455 |     updateSignalSource(item.source_label || '📡 BROADCASTING');
1456 |     updateTicker(item);
1457 | 
1458 |     // Update mode badge
1459 |     var badge = document.getElementById('stageModeBadge');
1460 |     if (badge) { badge.textContent = '● ON AIR'; badge.className = 'stage-mode-badge broadcast'; }
1461 | 
1462 |     // Render avatar video via server with script
1463 |     setBusy(true);
1464 |     setStatus('Rendering segment…', 'var(--s-gold)');
1465 | 
1466 |     try {
1467 |       // Generate TTS + avatar via avatar server
1468 |       var resp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
1469 |         method: 'POST',
1470 |         headers: {'Content-Type': 'application/json'},
1471 |         body: JSON.stringify({text: cleanScript(item.script), intent: 'BROADCAST_SEGMENT'})
1472 |       }, 120000);
1473 | 
1474 |       if (!resp.ok) throw new Error('Avatar render failed: HTTP ' + resp.status);
1475 | 
1476 |       var blob = await resp.blob();
1477 |       var url = URL.createObjectURL(blob);
1478 | 
1479 |       // Start pre-rendering next segment while current plays
1480 |       preRenderNext(item.id);
1481 | 
1482 |       await playVid(url);
1483 |       setBusy(false);
1484 | 
1485 |       // After playback: consume and get next
1486 |       if (!_broadcastPaused) {
1487 |         await consumeAndPlay(item.id);
1488 |       }
1489 |     } catch(e) {
1490 |       console.error('playBroadcastItem error:', e);
1491 |       setBusy(false);
1492 |       setStatus('Segment error — retrying…', 'var(--s-red)');
1493 |       setTimeout(function(){ consumeAndPlay(item.id); }, 3000);
1494 |     }
1495 |   }
1496 | 
1497 |   async function consumeAndPlay(consumedId) {
1498 |     if (_broadcastPaused) return;
1499 |     try {
1500 |       var resp = await fetch('/api/stage/consume-broadcast', {
1501 |         method: 'POST',
1502 |         headers: {'Content-Type': 'application/json'},
1503 |         body: JSON.stringify({consumed_id: consumedId})
1504 |       });
1505 |       var data = await resp.json();
1506 | 
1507 |       if (data.next_item) {
1508 |         // If we have a pre-rendered blob for this item, use it
1509 |         if (_preRenderedBlob && _preRenderedItem && _preRenderedItem.id === data.next_item.id) {
1510 |           _currentBroadcastTopic = data.next_item.topic_preview || '';
1511 |           updateSignalSource(data.next_item.source_label || '📡 BROADCASTING');
1512 |           updateTicker(data.next_item);
1513 |           setBusy(true);
1514 |           setStatus('Speaking', 'var(--s-green)');
1515 |           var url = URL.createObjectURL(_preRenderedBlob);
1516 |           _preRenderedBlob = null;
1517 |           _preRenderedItem = null;
1518 |           preRenderNext(data.next_item.id);
1519 |           await playVid(url);
1520 |           setBusy(false);
1521 |           if (!_broadcastPaused) await consumeAndPlay(data.next_item.id);
1522 |         } else {
1523 |           await playBroadcastItem(data.next_item);
1524 |         }
1525 |       } else {
1526 |         updateSignalSource('📡 STANDING BY');
1527 |         setTimeout(startBroadcast, 5000);
1528 |       }
1529 |     } catch(e) {
1530 |       console.error('consumeAndPlay error:', e);
1531 |       setTimeout(startBroadcast, 5000);
1532 |     }
1533 |   }
1534 | 
1535 |   // Pre-render next segment while current plays (reduce dead air)
1536 |   async function preRenderNext(currentId) {
1537 |     try {
1538 |       var resp = await fetch('/api/stage/broadcast-queue');
1539 |       if (!resp.ok) return;
1540 |       var data = await resp.json();
1541 |       // Find next item that isn't current
1542 |       var next = null;
1543 |       for (var i = 0; i < data.items.length; i++) {
1544 |         if (data.items[i].id !== currentId) { next = data.items[i]; break; }
1545 |       }
1546 |       if (!next) return;
1547 | 
1548 |       var renderResp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
1549 |         method: 'POST',
1550 |         headers: {'Content-Type': 'application/json'},
1551 |         body: JSON.stringify({text: cleanScript(next.script), intent: 'BROADCAST_SEGMENT'})
1552 |       }, 120000);
1553 | 
1554 |       if (renderResp.ok) {
1555 |         _preRenderedBlob = await renderResp.blob();
1556 |         _preRenderedItem = next;
1557 |       }
1558 |     } catch(e) {
1559 |       // Pre-render failure is non-fatal
1560 |     }
1561 |   }
1562 | 
1563 |   // ── PUSH TO SPEAK (interrupt flow) ────────────────────
1564 |   var _ptsModalShown = false;
1565 |   var _ptsFirstTime = true;
1566 | 
1567 |   function stageWake() {
1568 |     if (!_preRenderReady && !_preRenderFirstBlob) {
1569 |       // Not ready yet — show feedback but don't proceed
1570 |       var lbl = document.getElementById('stage-tap-label');
1571 |       if (lbl) {
1572 |         lbl.textContent = 'SIGNAL LOADING\u2026';
1573 |         setTimeout(function(){
1574 |           if (!_preRenderReady) lbl.textContent = 'SIGNAL WARMING UP\u2026';
1575 |         }, 1500);
1576 |       }
1577 |       return;
1578 |     }
1579 |     try {
1580 |       var ac=new(window.AudioContext||window.webkitAudioContext)();
1581 |       var buf=ac.createBuffer(1,1,22050);
1582 |       var src=ac.createBufferSource();
1583 |       src.buffer=buf;src.connect(ac.destination);src.start(0);
1584 |       setTimeout(function(){try{ac.close();}catch(e){}},300);
1585 |     } catch(e) {}
1586 |     /* Pre-unlock Audio element for mobile playback */
1587 |     try {
1588 |       window._audioUnlocked = new Audio();
1589 |       window._audioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1590 |       window._audioUnlocked.volume = 0.001;
1591 |       window._audioUnlocked.play().catch(function(){});
1592 |     } catch(e) {}
1593 |     /* Pre-unlock a second Audio element for stage mobile audio-only mode */
1594 |     window._stageAudioUnlocked = new Audio();
1595 |     window._stageAudioUnlocked.src = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAABErAAABAAgAZGF0YQIAAAABAA==';
1596 |     window._stageAudioUnlocked.volume = 0.001;
1597 |     window._stageAudioUnlocked.play().catch(function(){});
1598 |     // Pre-unlock video element for future muted→unmuted autoplay
1599 |     try {
1600 |       var vidEl = document.getElementById('avatarVid');
1601 |       if(vidEl) {
1602 |         vidEl.muted = true;
1603 |         vidEl.src = 'data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28ybXA0MAAAACB3aWRlAAAAAQAAABhtZGF0';
1604 |         vidEl.play().catch(function(){});
1605 |         setTimeout(function(){
1606 |           vidEl.pause();
1607 |           vidEl.src = '';
1608 |           vidEl.load();
1609 |         }, 200);
1610 |       }
1611 |     } catch(e) {}
1612 |     var ov=document.getElementById('stage-wake');
1613 |     if(ov) ov.style.display='none';
1614 | 
1615 |     if (_preRenderReady && _preRenderFirstBlob) {
1616 |       // Pre-rendered segment ready — play immediately within gesture window
1617 |       var url = _preRenderFirstBlob;
1618 |       _preRenderFirstBlob = null;
1619 |       _preRenderReady = false;
1620 |       setBusy(true);
1621 |       setStatus('Broadcasting…', 'var(--s-green)');
1622 |       vid.src = url;
1623 |       vid.muted = false;
1624 |       vid.volume = 1.0;
1625 |       vid.play().then(function() {
1626 |         vid.onended = function() {
1627 |           vid.src = '';
1628 |           URL.revokeObjectURL(url);
1629 |           setBusy(false);
1630 |           setStatus('Ready', 'rgba(255,255,255,.3)');
1631 |           startBroadcast();
1632 |         };
1633 |       }).catch(function(e) {
1634 |         console.warn('[Stage] Pre-rendered play failed:', e.name);
1635 |         URL.revokeObjectURL(url);
1636 |         startBroadcast();
1637 |       });
1638 |     } else {
1639 |       startBroadcast();
1640 |     }
1641 |   }
1642 |   window.stageWake = stageWake;
1643 | 
1644 |   window.toggleStageMic = function() {
1645 |     if (_stageIsRec) { _stopStageMic(); return; }
1646 | 
1647 |     // First-time modal
1648 |     if (_ptsFirstTime) {
1649 |       _ptsFirstTime = false;
1650 |       if (!confirm('The anchor is live. Tap OK to ask a question — the broadcast will pause while you speak.')) {
1651 |         return;
1652 |       }
1653 |     }
1654 | 
1655 |     // Request mic permission
1656 |     if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
1657 |       navigator.mediaDevices.getUserMedia({audio: true, video: false})
1658 |         .then(function(stream) {
1659 |           stream.getTracks().forEach(function(t) { t.stop(); });
1660 |           _startStageMic();
1661 |         })
1662 |         .catch(function(err) {
1663 |           var name = err && err.name ? err.name : '';
1664 |           if (name === 'NotAllowedError') {
1665 |             _appendChatMsg('Microphone blocked. Allow access in browser settings and reload.', 'oracle');
1666 |           } else if (name === 'NotFoundError') {
1667 |             _appendChatMsg('No microphone found. Connect a mic and try again.', 'oracle');
1668 |           } else {
1669 |             _appendChatMsg('Microphone error: ' + name + '. Try Chrome for best results.', 'oracle');
1670 |           }
1671 |         });
1672 |     } else {
1673 |       _startStageMic(); // Fallback: try SpeechRecognition directly
1674 |     }
1675 |   };
1676 | 
1677 |   function _startStageMic() {
1678 |     if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
1679 |       _appendChatMsg('Speech recognition not supported in this browser. Try Chrome.', 'oracle');
1680 |       return;
1681 |     }
1682 | 
1683 |     // Pause broadcast
1684 |     _broadcastPaused = true;
1685 |     if (vid && !vid.paused) {
1686 |       vid.pause();
1687 |     }
1688 |     // Show interrupted state
1689 |     updateSignalSource('🎤 INTERRUPTED — LISTENER SPEAKING');
1690 | 
1691 |     var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
1692 |     _stageRecognition = new SR();
1693 |     _stageRecognition.lang = 'en-US';
1694 |     _stageRecognition.continuous = false;
1695 |     _stageRecognition.interimResults = false;
1696 | 
1697 |     // P1.2: 10-second timeout
1698 |     var micTimeout = setTimeout(function() {
1699 |       _appendChatMsg('No speech detected — try again.', 'oracle');
1700 |       _stopStageMic();
1701 |       _resumeBroadcast();
1702 |     }, 10000);
1703 | 
1704 |     _stageRecognition.onresult = function(e) {
1705 |       clearTimeout(micTimeout);
1706 |       var text = e.results[0][0].transcript;
1707 |       document.getElementById('stageChatInput').value = text;
1708 |       _stopStageMic();
1709 |       _handleInterruptQuestion(text);
1710 |     };
1711 |     _stageRecognition.onerror = function(e) {
1712 |       clearTimeout(micTimeout);
1713 |       // P1.2: User-visible error message
1714 |       var msg = 'Speech error';
1715 |       if (e.error === 'no-speech') msg = 'No speech detected — try again.';
1716 |       else if (e.error === 'audio-capture') msg = 'No microphone available.';
1717 |       else if (e.error === 'not-allowed') msg = 'Microphone access denied.';
1718 |       _appendChatMsg(msg, 'oracle');
1719 |       _stopStageMic();
1720 |       _resumeBroadcast();
1721 |     };
1722 |     _stageRecognition.onend = function() {
1723 |       clearTimeout(micTimeout);
1724 |       _stopStageMic();
1725 |     };
1726 | 
1727 |     _stageRecognition.start();
1728 |     _stageIsRec = true;
1729 |     document.getElementById('stageMicBtn').classList.add('recording');
1730 |     var fmb = document.getElementById('floatingMicBtn');
1731 |     var fmicIcon = document.getElementById('fmicIcon');
1732 |     var fmicStop = document.getElementById('fmicStop');
1733 |     var fmicHint = document.getElementById('fmicHint');
1734 |     if (fmb) {
1735 |       fmb.classList.toggle('fmic-rec', _stageIsRec);
1736 |     }
1737 |     if (fmicIcon) fmicIcon.style.display = _stageIsRec ? 'none' : 'block';
1738 |     if (fmicStop) fmicStop.style.display = _stageIsRec ? 'block' : 'none';
1739 |     if (fmicHint) fmicHint.textContent = _stageIsRec ? 'tap to send' : 'tap to speak';
1740 |     document.getElementById('interactivePanel').classList.add('active');
1741 |   }
1742 | 
1743 |   function _stopStageMic() {
1744 |     _stageIsRec = false;
1745 |     if(_stageRecognition) { try{_stageRecognition.stop();}catch(e){} _stageRecognition = null; }
1746 |     document.getElementById('stageMicBtn').classList.remove('recording');
1747 |     var fmb = document.getElementById('floatingMicBtn');
1748 |     var fmicIcon = document.getElementById('fmicIcon');
1749 |     var fmicStop = document.getElementById('fmicStop');
1750 |     var fmicHint = document.getElementById('fmicHint');
1751 |     if (fmb) {
1752 |       fmb.classList.toggle('fmic-rec', _stageIsRec);
1753 |     }
1754 |     if (fmicIcon) fmicIcon.style.display = _stageIsRec ? 'none' : 'block';
1755 |     if (fmicStop) fmicStop.style.display = _stageIsRec ? 'block' : 'none';
1756 |     if (fmicHint) fmicHint.textContent = _stageIsRec ? 'tap to send' : 'tap to speak';
1757 |   }
1758 | 
1759 |   // ── STAGE CAMERA INTERRUPT ───────────────────────────
1760 |   function handleStageCameraInterrupt() {
1761 |     if (busy) return;
1762 |     var input = document.getElementById('stage-cam-input');
1763 |     if (input) input.click();
1764 |   }
1765 |   window.handleStageCameraInterrupt = handleStageCameraInterrupt;
1766 | 
1767 |   function handleStageCameraUpload(evt) {
1768 |     var file = evt.target.files && evt.target.files[0];
1769 |     if (!file) return;
1770 |     if (busy) {
1771 |       setStatus('Finishing current segment…', 'var(--s-gold)');
1772 |       return;
1773 |     }
1774 | 
1775 |     // Pause broadcast, handle vision interrupt
1776 |     _broadcastPaused = true;
1777 |     if (vid && !vid.paused) vid.pause();
1778 |     setBusy(true);
1779 |     setStatus('Analyzing image…', 'var(--s-gold)');
1780 |     updateSignalSource('📷 VIEWER PHOTO QUESTION');
1781 | 
1782 |     var reader = new FileReader();
1783 |     reader.onload = function(e) {
1784 |       var dataUrl = e.target.result;
1785 |       var b64 = dataUrl.split(',')[1];
1786 |       var mime = file.type || 'image/jpeg';
1787 | 
1788 |       fetchTO('https://avatar.protocolpulse.io/vision/analyze', {
1789 |         method: 'POST',
1790 |         headers: {'Content-Type': 'application/json'},
1791 |         body: JSON.stringify({
1792 |           image_base64: b64,
1793 |           mime_type: mime,
1794 |           session_id: 'stage_' + Date.now(),
1795 |           context: 'Bitcoin hardware question from live broadcast viewer'
1796 |         })
1797 |       }, 45000)
1798 |       .then(function(r) {
1799 |         if (!r.ok) throw new Error('vision ' + r.status);
1800 |         return r.json();
1801 |       })
1802 |       .then(function(d) {
1803 |         var guideText = d.guidance_text || d.text || 'I can see your hardware device.';
1804 | 
1805 |         // Transaction verdict urgency
1806 |         if (d.verdict === 'DO NOT SIGN') {
1807 |           guideText = 'WARNING. DO NOT SIGN THIS TRANSACTION. ' + guideText;
1808 |         } else if (d.verdict === 'REVIEW CAREFULLY') {
1809 |           guideText = 'REVIEW CAREFULLY. ' + guideText;
1810 |         }
1811 | 
1812 |         // Transaction verdict ticker
1813 |         if (d.category === 'transaction' && d.verdict) {
1814 |           var verdictEmoji = d.verdict === 'SAFE TO SIGN' ? '✅'
1815 |             : d.verdict === 'DO NOT SIGN' ? '🚨' : '⚠️';
1816 |           tickerOracle(verdictEmoji + ' TX REVIEW: ' + d.verdict
1817 |             + (d.amount_btc ? ' — ' + d.amount_btc + ' BTC' : ''));
1818 |         }
1819 | 
1820 |         // Cap to 40 words for broadcast pacing
1821 |         var words = guideText.split(/\s+/);
1822 |         var spokenText = words.length > 40 ? words.slice(0,40).join(' ') : guideText;
1823 | 
1824 |         setStatus('SIGNAL answering viewer question…', 'var(--s-green)');
1825 |         tickerOracle('📷 Viewer hardware question: ' + (d.device_name || 'unknown device'));
1826 | 
1827 |         // Get TTS audio
1828 |         return fetchTO('https://avatar.protocolpulse.io/oracle/voice', {
1829 |           method: 'POST',
1830 |           headers: {'Content-Type': 'application/json'},
1831 |           body: JSON.stringify({text: spokenText})
1832 |         }, 35000);
1833 |       })
1834 |       .then(function(ar) {
1835 |         if (!ar.ok) throw new Error('voice failed');
1836 |         return ar.blob();
1837 |       })
1838 |       .then(function(blob) {
1839 |         var audioUrl = URL.createObjectURL(blob);
1840 |         var audio = new Audio(audioUrl);
1841 |         audio.volume = 1.0;
1842 |         audio.onended = function() {
1843 |           URL.revokeObjectURL(audioUrl);
1844 |           setBusy(false);
1845 |           _broadcastPaused = false;
1846 |           setStatus('Resuming broadcast…', 'var(--s-gold)');
1847 |           updateSignalSource('📡 RESUMING');
1848 |           setTimeout(function() {
1849 |             startBroadcast();
1850 |           }, 1500);
1851 |         };
1852 |         audio.onerror = function() {
1853 |           URL.revokeObjectURL(audioUrl);
1854 |           setBusy(false);
1855 |           _broadcastPaused = false;
1856 |           startBroadcast();
1857 |         };
1858 |         audio.play().catch(function() {
1859 |           URL.revokeObjectURL(audioUrl);
1860 |           setBusy(false);
1861 |           _broadcastPaused = false;
1862 |           startBroadcast();
1863 |         });
1864 |       })
1865 |       .catch(function(err) {
1866 |         console.error('[Stage camera] Error:', err);
1867 |         setBusy(false);
1868 |         _broadcastPaused = false;
1869 |         setStatus('Ready', 'rgba(255,255,255,.3)');
1870 |         startBroadcast();
1871 |       });
1872 | 
1873 |       // Clear input for reuse
1874 |       evt.target.value = '';
1875 |     };
1876 |     reader.readAsDataURL(file);
1877 |   }
1878 |   window.handleStageCameraUpload = handleStageCameraUpload;
1879 | 
1880 |   async function _handleInterruptQuestion(text) {
1881 |     setBusy(true);
1882 |     setStatus('Oracle thinking…', 'var(--s-gold)');
1883 |     updateSignalSource('🎤 RESPONDING TO LISTENER');
1884 | 
1885 |     try {
1886 |       var resp = await fetchTO('/api/oracle/chat', {
1887 |         method: 'POST',
1888 |         headers: {'Content-Type': 'application/json'},
1889 |         body: JSON.stringify({
1890 |           text: text,
1891 |           session_id: _stageSessionId,
1892 |           audio_first: true,
1893 |           avatar_source: 'stage_hologram',
1894 |           context: _currentBroadcastTopic
1895 |         })
1896 |       }, 90000);
1897 | 
1898 |       if (handle429(resp)) { setBusy(false); _resumeBroadcast(); return; }
1899 |       if (!resp.ok) throw new Error('HTTP ' + resp.status);
1900 | 
1901 |       var ct = resp.headers.get('content-type') || '';
1902 |       if (ct.indexOf('video') >= 0) {
1903 |         var blob = await resp.blob();
1904 |         var url = URL.createObjectURL(blob);
1905 |         await playVid(url);
1906 |       } else {
1907 |         var j = await resp.json();
1908 |         if (j.job_id) {
1909 |           // Poll for video
1910 |           var polls = 0;
1911 |           await new Promise(function(resolve) {
1912 |             var pollId = setInterval(function() {
1913 |               polls++;
1914 |               if (polls > 45) { clearInterval(pollId); resolve(); return; }
1915 |               fetch(AVATAR_BASE + '/oracle/job/' + j.job_id)
1916 |                 .then(function(vr) { if (vr.ok) return vr.blob(); return null; })
1917 |                 .then(function(vb) {
1918 |                   if (vb) {
1919 |                     clearInterval(pollId);
1920 |                     playVid(URL.createObjectURL(vb)).then(resolve).catch(function(){ resolve(); });
1921 |                   }
1922 |                 }).catch(function(){});
1923 |             }, 1000);
1924 |           });
1925 |         }
1926 |       }
1927 |     } catch(e) {
1928 |       console.error('interrupt error:', e);
1929 |     }
1930 | 
1931 |     setBusy(false);
1932 |     // Resume broadcast after 3s countdown
1933 |     _showResumeCountdown();
1934 |   }
1935 | 
1936 |   function _showResumeCountdown() {
1937 |     var count = 3;
1938 |     setStatus('Returning to broadcast in ' + count + '…', 'var(--s-gold)');
1939 |     var cid = setInterval(function() {
1940 |       count--;
1941 |       if (count <= 0) {
1942 |         clearInterval(cid);
1943 |         _resumeBroadcast();
1944 |       } else {
1945 |         setStatus('Returning to broadcast in ' + count + '…', 'var(--s-gold)');
1946 |       }
1947 |     }, 1000);
1948 |   }
1949 | 
1950 |   function _resumeBroadcast() {
1951 |     _broadcastPaused = false;
1952 |     document.getElementById('interactivePanel').classList.remove('active');
1953 |     updateSignalSource('📡 RESUMING');
1954 |     startBroadcast();
1955 |   }
1956 | 
1957 |   // ── STAGE CHAT (text input) ───────────────────────────
1958 |   window.stageChat = function() {
1959 |     var input = document.getElementById('stageChatInput');
1960 |     var text = (input.value || '').trim();
1961 |     if(!text || busy) return;
1962 |     input.value = '';
1963 |     _handleInterruptQuestion(text);
1964 |   };
1965 | 
1966 |   function _appendChatMsg(text, role) {
1967 |     var hist = document.getElementById('stageChatHistory');
1968 |     var div = document.createElement('div');
1969 |     div.className = 'stage-chat-msg ' + role;
1970 |     div.textContent = text;
1971 |     hist.appendChild(div);
1972 |     hist.scrollTop = hist.scrollHeight;
1973 |   }
1974 | 
1975 |   function pulseStageMic() {
1976 |     var micBtn = document.getElementById('stageMicBtn');
1977 |     if(!micBtn || micBtn.disabled || _stageIsRec) return;
1978 |     micBtn.style.boxShadow = '0 0 0 8px rgba(255,59,95,.2)';
1979 |     setTimeout(function(){ micBtn.style.boxShadow = ''; }, 2000);
1980 |   }
1981 | 
1982 |   // ── BRIEFING COUNTDOWN ──────────────────────────────
1983 |   var _briefCountdownId = null;
1984 |   var _latestBriefUrl = null;
1985 |   var _hasUserInteracted = false;
1986 |   var _countdownRemaining = 0;
1987 | 
1988 |   document.addEventListener('click', function(){ _hasUserInteracted = true; }, {once:true});
1989 | 
1990 |   function loadBriefingSchedule(){
1991 |     fetch('/api/stage/next_briefing')
1992 |     .then(function(r){ return r.json(); })
1993 |     .then(function(d){
1994 |       if(!d.has_brief){
1995 |         safeText(document.getElementById('countdownTimer'), '\u2014');
1996 |         safeText(document.getElementById('countdownSub'), 'First brief coming soon');
1997 |         return;
1998 |       }
1999 |       _latestBriefUrl = d.last_brief.mp4_url;
2000 |       if(d.countdown_seconds <= 0){
2001 |         showBriefReady(d.last_brief);
2002 |       } else {
2003 |         startCountdown(d.countdown_seconds, d.last_brief);
2004 |       }
2005 |     })
2006 |     .catch(function(){
2007 |       safeText(document.getElementById('countdownSub'), 'Schedule unavailable');
2008 |     });
2009 |   }
2010 | 
2011 |   function startCountdown(seconds, lastBrief){
2012 |     if(_briefCountdownId) clearInterval(_briefCountdownId);
2013 |     _countdownRemaining = seconds;
2014 |     var timerEl = document.getElementById('countdownTimer');
2015 |     var subEl = document.getElementById('countdownSub');
2016 |     var dotEl = document.getElementById('briefDot');
2017 |     var playBtn = document.getElementById('briefPlayBtn');
2018 | 
2019 |     dotEl.classList.remove('ready');
2020 |     timerEl.classList.remove('ready');
2021 |     playBtn.style.display = 'none';
2022 |     safeText(subEl, lastBrief.title || 'Last brief loaded');
2023 | 
2024 |     function update(){
2025 |       if(_countdownRemaining <= 0){
2026 |         clearInterval(_briefCountdownId);
2027 |         showBriefReady(lastBrief);
2028 |         return;
2029 |       }
2030 |       var h = Math.floor(_countdownRemaining / 3600);
2031 |       var m = Math.floor((_countdownRemaining % 3600) / 60);
2032 |       var s = _countdownRemaining % 60;
2033 |       safeText(timerEl, pad(h) + ':' + pad(m) + ':' + pad(s));
2034 |       var bb = document.getElementById('betweenCountdown');
2035 |       if(bb) bb.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
2036 |       _countdownRemaining--;
2037 |     }
2038 |     update();
2039 |     _briefCountdownId = setInterval(update, 1000);
2040 |   }
2041 | 
2042 |   function pad(n){ return n < 10 ? '0'+n : ''+n; }
2043 | 
2044 |   function showBriefReady(brief){
2045 |     var timerEl = document.getElementById('countdownTimer');
2046 |     var dotEl = document.getElementById('briefDot');
2047 |     var playBtn = document.getElementById('briefPlayBtn');
2048 | 
2049 |     safeText(timerEl, 'NEW BRIEF');
2050 |     timerEl.classList.add('ready');
2051 |     dotEl.classList.add('ready');
2052 |     safeText(document.getElementById('countdownSub'), brief.title || 'Ready to play');
2053 |     playBtn.style.display = 'block';
2054 |     _latestBriefUrl = brief.mp4_url;
2055 |   }
2056 | 
2057 |   window.playLatestBrief = function(){
2058 |     if(busy) return;
2059 |     // If brief is a pre-rendered MP4 URL, play directly
2060 |     if(_latestBriefUrl && _latestBriefUrl.indexOf('.mp4') >= 0){
2061 |       setBusy(true);
2062 |       setStatus('Playing brief\u2026','var(--s-gold)');
2063 |       playVid(_latestBriefUrl).then(function(){ setBusy(false); }).catch(function(){ setBusy(false); setStatus('Brief unavailable','var(--s-red)'); });
2064 |       return;
2065 |     }
2066 |     // Otherwise fetch brief script and use monologue system
2067 |     fetch('/api/stage/intel').then(function(r){ return r.json(); }).then(function(d){
2068 |       var script = d.brief_script || d.summary || '';
2069 |       if(script && script.length > 30){
2070 |         playMonologue(script);
2071 |       } else {
2072 |         setStatus('No brief available','var(--s-gold)');
2073 |       }
2074 |     }).catch(function(){
2075 |       setStatus('Brief unavailable','var(--s-red)');
2076 |     });
2077 |   };
2078 | 
2079 |   // ── MONOLOGUE PLAYER — zero-gap chunk chaining ────────
2080 |   async function waitAndFetchChunk(jobId, idx) {
2081 |     var url = AVATAR_BASE + '/oracle/monologue/' + jobId + '/chunk/' + idx;
2082 |     for (var attempt = 0; attempt < 120; attempt++) {
2083 |       var r = await fetch(url);
2084 |       if (r.ok) return await r.blob();
2085 |       if (r.status !== 202) throw new Error('Chunk ' + idx + ' failed: ' + r.status);
2086 |       await new Promise(function(res) { setTimeout(res, 250); });
2087 |     }
2088 |     throw new Error('Chunk ' + idx + ' timed out');
2089 |   }
2090 | 
2091 |   async function playMonologue(script) {
2092 |     setBusy(true);
2093 |     setStatus('Preparing broadcast\u2026', 'var(--s-gold)');
2094 |     _broadcastPaused = true;
2095 | 
2096 |     try {
2097 |       var resp = await fetchTO(AVATAR_BASE + '/oracle/monologue', {
2098 |         method: 'POST',
2099 |         headers: {'Content-Type': 'application/json'},
2100 |         body: JSON.stringify({script: script})
2101 |       }, 8000);
2102 |       if (!resp.ok) throw new Error('Monologue submit failed');
2103 |       var job = await resp.json();
2104 |       var jobId = job.job_id;
2105 |       var total = job.total_chunks;
2106 | 
2107 |       var nextBlob = null;
2108 | 
2109 |       for (var i = 0; i < total; i++) {
2110 |         setStatus('Broadcasting ' + (i+1) + ' of ' + total + '\u2026', 'var(--s-green)');
2111 | 
2112 |         var blob;
2113 |         if (nextBlob) {
2114 |           blob = nextBlob;
2115 |           nextBlob = null;
2116 |         } else {
2117 |           blob = await waitAndFetchChunk(jobId, i);
2118 |         }
2119 | 
2120 |         var prefetchPromise = (i + 1 < total) ? waitAndFetchChunk(jobId, i + 1) : Promise.resolve(null);
2121 | 
2122 |         var blobUrl = URL.createObjectURL(blob);
2123 | 
2124 |         var prefetchDone = false;
2125 |         prefetchPromise.then(function(b) { nextBlob = b; prefetchDone = true; });
2126 | 
2127 |         await playVid(blobUrl);
2128 |         URL.revokeObjectURL(blobUrl);
2129 | 
2130 |         if (i + 1 < total && !prefetchDone) {
2131 |           setStatus('Buffering\u2026', 'var(--s-gold)');
2132 |           await new Promise(function(res) {
2133 |             var check = setInterval(function() {
2134 |               if (prefetchDone) { clearInterval(check); res(); }
2135 |             }, 100);
2136 |           });
2137 |         }
2138 |       }
2139 | 
2140 |     } catch(e) {
2141 |       console.error('playMonologue error:', e);
2142 |     } finally {
2143 |       setBusy(false);
2144 |       _broadcastPaused = false;
2145 |       setStatus('Ready', 'rgba(255,255,255,.3)');
2146 |       setTimeout(startBroadcast, 1000);
2147 |     }
2148 |   }
2149 |   window.playMonologue = playMonologue;
2150 | 
2151 |   // ── CONTINUOUS MONOLOGUE LOOP ─────────────────────────
2152 |   var _nextMonologueScript = null;
2153 |   var _nextMonologueJob = null;
2154 |   var _loopRunning = false;
2155 | 
2156 |   async function runMonologueLoop() {
2157 |     if (_loopRunning) return;
2158 |     _loopRunning = true;
2159 | 
2160 |     try {
2161 |       while (!_broadcastPaused) {
2162 |         var script = _nextMonologueScript;
2163 |         var preJob = _nextMonologueJob;
2164 |         _nextMonologueScript = null;
2165 |         _nextMonologueJob = null;
2166 | 
2167 |         if (!script) {
2168 |           setStatus('Generating broadcast\u2026', 'var(--s-gold)');
2169 |           script = await fetchMonologueScript();
2170 |         }
2171 |         if (!script || _broadcastPaused) break;
2172 | 
2173 |         var job;
2174 |         if (preJob) {
2175 |           job = preJob;
2176 |         } else {
2177 |           setStatus('Rendering\u2026', 'var(--s-gold)');
2178 |           try {
2179 |             var resp = await fetchTO(AVATAR_BASE + '/oracle/monologue', {
2180 |               method: 'POST',
2181 |               headers: {'Content-Type': 'application/json'},
2182 |               body: JSON.stringify({script: script})
2183 |             }, 15000);
2184 |             if (!resp.ok) throw new Error('monologue ' + resp.status);
2185 |             job = await resp.json();
2186 |           } catch(mErr) {
2187 |             // Fallback: render via /oracle/speak and play directly
2188 |             try {
2189 |               var speakResp = await fetchTO(AVATAR_BASE + '/oracle/speak', {
2190 |                 method: 'POST',
2191 |                 headers: {'Content-Type': 'application/json'},
2192 |                 body: JSON.stringify({text: script, intent: 'BROADCAST_SEGMENT'})
2193 |               }, 120000);
2194 |               if (!speakResp.ok) { await sleep(3000); continue; }
2195 |               var blob = await speakResp.blob();
2196 |               var url = URL.createObjectURL(blob);
2197 |               await playVid(url);
2198 |               try { URL.revokeObjectURL(url); } catch(e) {}
2199 |               continue;
2200 |             } catch(sErr) {
2201 |               await sleep(3000); continue;
2202 |             }
2203 |           }
2204 |         }
2205 | 
2206 |         prefetchNextMonologue();
2207 | 
2208 |         await playMonologueJob(job);
2209 |       }
2210 |     } finally {
2211 |       _loopRunning = false;
2212 |     }
2213 |   }
2214 | 
2215 |   async function fetchMonologueScript() {
2216 |     try {
2217 |       var r = await fetchTO('/api/stage/generate-monologue', {
2218 |         method: 'POST', headers: {'Content-Type': 'application/json'}
2219 |       }, 25000);
2220 |       if (!r.ok) return null;
2221 |       var d = await r.json();
2222 |       updateTicker({topic_preview: 'Live Oracle Broadcast'});
2223 |       return d.script || null;
2224 |     } catch(e) { return null; }
2225 |   }
2226 | 
2227 |   async function prefetchNextMonologue() {
2228 |     try {
2229 |       var script = await fetchMonologueScript();
2230 |       if (!script) return;
2231 |       _nextMonologueScript = script;
2232 |       var resp = await fetchTO(AVATAR_BASE + '/oracle/monologue', {
2233 |         method: 'POST',
2234 |         headers: {'Content-Type': 'application/json'},
2235 |         body: JSON.stringify({script: script})
2236 |       }, 8000);
2237 |       if (resp.ok) {
2238 |         _nextMonologueJob = await resp.json();
2239 |       }
2240 |     } catch(e) {}
2241 |   }
2242 | 
2243 |   async function playMonologueJob(job) {
2244 |     var jobId = job.job_id;
2245 |     var total = job.total_chunks;
2246 |     var nextBlob = null;
2247 | 
2248 |     for (var i = 0; i < total; i++) {
2249 |       if (_broadcastPaused) break;
2250 |       setStatus('On Air \u00b7 ' + (i+1) + '/' + total, 'var(--s-green)');
2251 |       var badge = document.getElementById('stageModeBadge');
2252 |       if (badge) { badge.textContent = '\u25cf ON AIR'; badge.className = 'stage-mode-badge broadcast'; }
2253 | 
2254 |       var blob = nextBlob || await waitAndFetchChunk(jobId, i);
2255 |       nextBlob = null;
2256 | 
2257 |       var nextIdx = i + 1;
2258 |       if (nextIdx < total) {
2259 |         waitAndFetchChunk(jobId, nextIdx).then(function(b) { nextBlob = b; }).catch(function(){});
2260 |       }
2261 | 
2262 |       var url = URL.createObjectURL(blob);
2263 |       await playVid(url);
2264 |       try { URL.revokeObjectURL(url); } catch(e) {}
2265 |     }
2266 |   }
2267 | 
2268 |   function sleep(ms) { return new Promise(function(r){ setTimeout(r, ms); }); }
2269 | 
2270 |   // ── INIT ──────────────────────────────────────────────
2271 |   loadIntel();
2272 |   loadTranscripts();
2273 |   loadNostr();
2274 |   loadBriefingSchedule();
2275 | 
2276 |   // P1.4: Reduce polling to 30s
2277 |   setInterval(loadIntel, 30000);
2278 |   setInterval(loadNostr, 30000);
2279 |   setInterval(loadBriefingSchedule, 300000);
2280 | 
2281 |   // P0.4: Listen for custom event instead of monkey-patching
2282 |   function initTxDots(){
2283 |     var grid = document.getElementById('transcriptsGrid');
2284 |     var dotsEl = document.getElementById('txDots');
2285 |     if(!grid||!dotsEl) return;
2286 |     var cards = grid.children;
2287 |     if(!cards.length) return;
2288 |     if(window.innerWidth > 640){ dotsEl.style.display='none'; return; }
2289 |     dotsEl.innerHTML = '';
2290 |     var n = Math.min(cards.length, 8);
2291 |     for(var i=0;i<n;i++){
2292 |       var dot = document.createElement('span');
2293 |       if(i===0) dot.className='active';
2294 |       dotsEl.appendChild(dot);
2295 |     }
2296 |     grid.addEventListener('scroll', function(){
2297 |       var idx = Math.round(grid.scrollLeft / (grid.scrollWidth / n));
2298 |       var dots = dotsEl.children;
2299 |       for(var j=0;j<dots.length;j++) dots[j].className = j===idx?'active':'';
2300 |     }, {passive:true});
2301 |   }
2302 |   document.addEventListener('transcriptsRendered', function(){ setTimeout(initTxDots, 100); });
2303 | 
2304 |   // Pre-render first segment silently so it's ready when user taps
2305 |   preRenderFirstSegment();
2306 | 
2307 |   // Animate warming dots + flip label when pre-render is ready (30s timeout)
2308 |   (function(){
2309 |     var dots = document.getElementById('stage-tap-dots');
2310 |     var label = document.getElementById('stage-tap-label');
2311 |     var dotCount = 1;
2312 |     var _warmStart = Date.now();
2313 |     var _WARM_TIMEOUT = 30000;
2314 |     var dotAnim = setInterval(function(){
2315 |       dotCount = (dotCount % 3) + 1;
2316 |       if (dots) dots.textContent = '.'.repeat(dotCount);
2317 |     }, 500);
2318 |     var _stageReadyPoller = setInterval(function(){
2319 |       if (_preRenderReady) {
2320 |         clearInterval(_stageReadyPoller);
2321 |         clearInterval(dotAnim);
2322 |         if (label) {
2323 |           label.textContent = 'TAP TO BEGIN BROADCAST';
2324 |           label.style.opacity = '1';
2325 |         }
2326 |         var ov = document.getElementById('stage-wake');
2327 |         if (ov) ov.classList.add('stage-wake-ready');
2328 |       } else if (Date.now() - _warmStart > _WARM_TIMEOUT) {
2329 |         clearInterval(_stageReadyPoller);
2330 |         clearInterval(dotAnim);
2331 |         if (label) {
2332 |           label.innerHTML = 'SIGNAL UNAVAILABLE &mdash; <span style="text-decoration:underline;cursor:pointer" onclick="location.reload()">TAP TO RETRY</span>';
2333 |           label.style.opacity = '1';
2334 |         }
2335 |         console.warn('[Stage] Pre-render timed out after 30s');
2336 |       }
2337 |     }, 1000);
2338 |   })();
2339 | 
2340 |   // Auto-play greeting on load — mobile gets tap overlay, desktop auto-starts
2341 |   setTimeout(function(){
2342 |     var _isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
2343 |     if(_isMobile) {
2344 |       // Show tap-to-start overlay on mobile — needed for autoplay unlock
2345 |       var ov = document.getElementById('stage-wake');
2346 |       if(ov) ov.style.display = 'flex';
2347 |     } else {
2348 |       startBroadcast();
2349 |     }
2350 |   }, 400);
2351 | 
2352 |   // Prevent iOS pinch-to-zoom
2353 |   document.addEventListener('gesturestart', function(e){ e.preventDefault(); }, {passive:false});
2354 |   document.addEventListener('touchmove', function(e){ if(e.touches.length>1) e.preventDefault(); }, {passive:false});
2355 | 
2356 | })();
2357 | </script>
2358 | {% endblock %}
2359 | 
```

### File: oracle/avatar_server.py (2323 lines)
```
   1 | """
   2 | ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks
   3 | =====================================================================
   4 | GPU-accelerated Wav2Lip lip-sync with:
   5 |   - FP16 inference via ModelRegistry singleton on GPU 1
   6 |   - Kokoro af_heart TTS on cuda:1 (~2-3s latency)
   7 |   - CV2 bilateral sharpen (GFPGAN fully removed 2026-03-12)
   8 |   - MediaPipe eye blinks (gradient overlay, no warpAffine artifacts)
   9 |   - Head movement post-processing
  10 |   - Vision guide endpoints (Gemini 2.5 Flash)
  11 |   - Input audio length guard (30s max, chunked processing)
  12 |   - CRF 23, preset ultrafast, 30fps output
  13 | 
  14 | Deploy: ~/protocol_pulse/oracle/avatar_server.py
  15 | Launch: cd ~/protocol_pulse/oracle && python3 avatar_server.py
  16 | """
  17 | 
  18 | import os
  19 | import sys
  20 | import time
  21 | import math
  22 | import random
  23 | import base64
  24 | import logging
  25 | import subprocess
  26 | import tempfile
  27 | import threading
  28 | import queue
  29 | import uuid
  30 | import numpy as np
  31 | 
  32 | import cv2
  33 | import torch
  34 | torch.backends.cudnn.benchmark = True
  35 | from flask import Flask, request, jsonify, send_file, after_this_request
  36 | 
  37 | from model_registry import ModelRegistry, WAV2LIP_DIR, AVATAR_SOURCE, DEVICE
  38 | 
  39 | import requests as http_requests  # ElevenLabs TTS
  40 | import json as _json
  41 | 
  42 | # ─── Kokoro af_heart TTS (Oracle Avatar) ─────────────────────────────
  43 | # Add oracle/ to path for normalize_pronunciation
  44 | _oracle_dir = os.path.dirname(os.path.abspath(__file__))
  45 | if _oracle_dir not in sys.path:
  46 |     sys.path.insert(0, _oracle_dir)
  47 | _AVATAR_KOKORO_READY = False
  48 | _KOKORO_PIPELINE = None
  49 | 
  50 | # Face enhancement + blink modules
  51 | from face_enhancer import sharpen_mouth_region
  52 | from blink_engine import apply_blink_gradient, generate_blink_schedule
  53 | 
  54 | # ─── Config ───────────────────────────────────────────────────────────
  55 | PORT = 8200
  56 | BATCH_SIZE_DEFAULT = 48  # Proven stable at 134fps — 64 caused VRAM pressure on GPU 1
  57 | BATCH_SIZE_SMALL = 16    # For short audio < 60 mel frames
  58 | BATCH_SIZE = BATCH_SIZE_DEFAULT
  59 | DEFAULT_FPS = 30.0  # Upgraded from 25fps — smoother motion
  60 | 
  61 | # Post-processing config
  62 | BLINK_INTERVAL_MIN = 2.5
  63 | BLINK_INTERVAL_MAX = 5.0
  64 | BLINK_DURATION = 0.22  # ~6-7 frames at 30fps, visible but natural
  65 | HEAD_ROTATION_AMPLITUDE = 2.5   # degrees — visible news-anchor sway
  66 | HEAD_TRANSLATION_X = 4.0        # pixels — visible horizontal drift
  67 | HEAD_TRANSLATION_Y = 2.0        # pixels — visible vertical drift
  68 | HEAD_PERIOD = 5.0               # seconds per full cycle — slow and natural
  69 | 
  70 | # Lock timeout (seconds) — if GPU is busy longer than this, return 503
  71 | LOCK_TIMEOUT = int(os.environ.get("AVATAR_LOCK_TIMEOUT", "120"))  # increased: real-time Q must wait for GPU
  72 | 
  73 | # Max audio duration (seconds) — longer clips get chunked
  74 | MAX_AUDIO_SECONDS = 30
  75 | 
  76 | # ─── Named Avatar Sources ─────────────────────────────────────────────
  77 | AVATAR_SOURCES = {
  78 |     "default":         "/home/ultron/protocol_pulse/static/img/oracle_avatar_static.png",
  79 |     "stage_hologram":  "/home/ultron/protocol_pulse/static/img/stage_bg_hologram.png",
  80 |     "oracle_studio":   "/home/ultron/protocol_pulse/oracle/Proto_P_Avatar_1024.png",
  81 | }
  82 | 
  83 | # Cache for loaded alternate avatar faces: {name: {"face": ndarray, "coords": tuple, "eye_landmarks": ...}}
  84 | _avatar_face_cache = {}
  85 | _avatar_face_cache_lock = threading.Lock()
  86 | 
  87 | 
  88 | def _detect_face_cpu(img, source_name):
  89 |     """Run face detection on CPU — avoids CUDA contention entirely.
  90 |     Returns (coords, eye_lm) or (None, None).
  91 |     """
  92 |     try:
  93 |         if WAV2LIP_DIR not in sys.path:
  94 |             sys.path.insert(0, WAV2LIP_DIR)
  95 |         import face_detection as _fd
  96 |         cpu_detector = _fd.FaceAlignment(_fd.LandmarksType._2D, flip_input=False, device="cpu")
  97 |         results = cpu_detector.get_detections_for_batch(np.array([img]))
  98 |         del cpu_detector
  99 | 
 100 |         coords = None
 101 |         if results[0] is not None:
 102 |             det = results[0]
 103 |             coords = (
 104 |                 max(0, int(det[1])), min(img.shape[0], int(det[3])),
 105 |                 max(0, int(det[0])), min(img.shape[1], int(det[2]))
 106 |             )
 107 |             logger.info(f"[AVATAR_SOURCE] {source_name}: face at {coords} in {img.shape[1]}x{img.shape[0]}")
 108 | 
 109 |         eye_lm = None
 110 |         try:
 111 |             from blink_engine import detect_eye_landmarks
 112 |             eye_lm = detect_eye_landmarks(img)
 113 |         except Exception as e:
 114 |             logger.warning(f"[AVATAR_SOURCE] Eye landmark detection failed for {source_name}: {e}", exc_info=True)
 115 | 
 116 |         return coords, eye_lm
 117 |     except Exception as e:
 118 |         logger.error(f"[AVATAR_SOURCE] CPU face detection failed for {source_name}: {e}")
 119 |         return None, None
 120 | 
 121 | 
 122 | def _load_avatar_face(source_name):
 123 |     """Load and cache an alternate avatar face by source name (lazy, CPU-based detection).
 124 |     Returns (face_img, face_coords, eye_landmarks) or (None, None, None) on failure.
 125 |     Non-default sources are detected lazily on first request using CPU face detection,
 126 |     falling back to default if detection fails.
 127 |     Thread-safe: all work happens inside the lock to prevent thundering herd.
 128 |     """
 129 |     if source_name == "default" or source_name not in AVATAR_SOURCES:
 130 |         reg = ModelRegistry.get()
 131 |         return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks
 132 | 
 133 |     with _avatar_face_cache_lock:
 134 |         # Check cache inside lock — prevents thundering herd
 135 |         if source_name in _avatar_face_cache:
 136 |             c = _avatar_face_cache[source_name]
 137 |             return c["face"], c["coords"], c["eye_landmarks"]
 138 | 
 139 |         # Load and detect inside lock — only one thread does the work
 140 |         img_path = AVATAR_SOURCES[source_name]
 141 |         # Validate path is within expected directory
 142 |         real_path = os.path.realpath(img_path)
 143 |         allowed_base = os.path.realpath("/home/ultron/protocol_pulse")
 144 |         if not real_path.startswith(allowed_base + os.sep):
 145 |             logger.error(f"[AVATAR_SOURCE] Path traversal blocked: {img_path} -> {real_path}")
 146 |             return None, None, None
 147 | 
 148 |         if not os.path.exists(img_path):
 149 |             logger.error(f"[AVATAR_SOURCE] Image not found: {img_path}")
 150 |             return None, None, None
 151 | 
 152 |         img = cv2.imread(img_path)
 153 |         if img is None:
 154 |             logger.error(f"[AVATAR_SOURCE] Failed to read: {img_path}")
 155 |             return None, None, None
 156 | 
 157 |         coords, eye_lm = _detect_face_cpu(img, source_name)
 158 |         if coords is None:
 159 |             logger.error(f"[AVATAR_SOURCE] No face detected in {source_name} — falling back to default")
 160 |             reg = ModelRegistry.get()
 161 |             return reg.avatar_face, reg.avatar_face_coords, reg.eye_landmarks
 162 | 
 163 |         _avatar_face_cache[source_name] = {"face": img.copy(), "coords": coords, "eye_landmarks": eye_lm}
 164 | 
 165 |     return img.copy(), coords, eye_lm
 166 | 
 167 | # ─── Logging ──────────────────────────────────────────────────────────
 168 | logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
 169 | logger = logging.getLogger("avatar_server")
 170 | 
 171 | app = Flask(__name__)
 172 | 
 173 | # ── CORS: allow protocolpulse.io and any origin to call avatar APIs ──────────
 174 | CORS_ORIGINS = [
 175 |     "https://protocolpulse.io",
 176 |     "https://www.protocolpulse.io",
 177 |     "http://localhost:3000",
 178 |     "http://localhost:5000",
 179 |     "http://localhost:8080",
 180 | ]
 181 | 
 182 | @app.after_request
 183 | def add_cors_headers(response):
 184 |     origin = request.headers.get("Origin", "")
 185 |     # Allow configured origins + any localhost
 186 |     if origin in CORS_ORIGINS or origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
 187 |         response.headers["Access-Control-Allow-Origin"] = origin
 188 |     # Default deny: no Access-Control-Allow-Origin header for unknown origins
 189 |     response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
 190 |     response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
 191 |     response.headers["Access-Control-Allow-Credentials"] = "false"
 192 |     response.headers["Access-Control-Max-Age"] = "86400"
 193 |     return response
 194 | 
 195 | @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
 196 | @app.route("/<path:path>", methods=["OPTIONS"])
 197 | def handle_options(path):
 198 |     response = app.make_default_options_response()
 199 |     return response
 200 | 
 201 | # ─── Metrics ──────────────────────────────────────────────────────────
 202 | _lock = threading.Lock()
 203 | _start_time = time.time()
 204 | _request_times = []  # last 100 request times for avg latency
 205 | 
 206 | # ─── Async render job system (Phase 1: audio-first) ──────────────────
 207 | _render_jobs = {}        # job_id -> {"status": "pending"|"done"|"error", "video_bytes": bytes|None, "created": float}
 208 | _render_jobs_lock = threading.Lock()
 209 | _RENDER_JOB_TTL = 120   # seconds — auto-expire stale jobs
 210 | 
 211 | # ─── Concurrency queue (Phase 1: concurrency hardening) ──────────────
 212 | _render_semaphore = threading.Semaphore(2)  # max 2 concurrent Wav2Lip renders
 213 | _render_queue_count = 0
 214 | _render_queue_lock = threading.Lock()
 215 | 
 216 | 
 217 | # ─── SSE event system (Phase 2: push delivery) ───────────────────────
 218 | _job_events = {}          # job_id -> queue.Queue (SSE push events)
 219 | _job_events_lock = threading.Lock()
 220 | 
 221 | _GC_INTERVAL = 60        # seconds between garbage collection sweeps
 222 | _SESSION_TTL = 300       # seconds — evict stream/chunk sessions after 5min of inactivity
 223 | _JOB_TTL_COMPLETED = 300 # seconds — evict completed/failed render jobs after 5min
 224 | _MAX_RENDER_JOBS = 50    # hard cap on concurrent render jobs
 225 | 
 226 | 
 227 | def _gc_worker():
 228 |     """Background daemon: evict stale sessions, jobs, and their temp files."""
 229 |     import shutil
 230 |     while True:
 231 |         time.sleep(_GC_INTERVAL)
 232 |         now = time.time()
 233 |         try:
 234 |             # Clean _stream_sessions
 235 |             with _stream_lock:
 236 |                 expired = [sid for sid, s in _stream_sessions.items()
 237 |                            if now - s.get("created", 0) > _SESSION_TTL]
 238 |                 for sid in expired:
 239 |                     s = _stream_sessions.pop(sid, None)
 240 |                     if s and s.get("dir"):
 241 |                         try:
 242 |                             shutil.rmtree(s["dir"], ignore_errors=True)
 243 |                         except Exception:
 244 |                             pass
 245 |             if expired:
 246 |                 logger.info(f"[GC] Evicted {len(expired)} stream sessions")
 247 | 
 248 |             # Clean _chunk_sessions
 249 |             with _chunk_lock:
 250 |                 expired_chunks = [sid for sid, s in _chunk_sessions.items()
 251 |                                   if now - s.get("created", 0) > _SESSION_TTL]
 252 |                 for sid in expired_chunks:
 253 |                     s = _chunk_sessions.pop(sid, None)
 254 |                     if s and s.get("dir"):
 255 |                         try:
 256 |                             shutil.rmtree(s["dir"], ignore_errors=True)
 257 |                         except Exception:
 258 |                             pass
 259 |             if expired_chunks:
 260 |                 logger.info(f"[GC] Evicted {len(expired_chunks)} chunk sessions")
 261 | 
 262 |             # Clean _render_jobs (completed/failed older than TTL, or pending older than _RENDER_JOB_TTL)
 263 |             with _render_jobs_lock:
 264 |                 expired_jobs = []
 265 |                 for jid, job in _render_jobs.items():
 266 |                     if job["status"] in ("done", "error"):
 267 |                         completed_at = job.get("completed_at", job.get("created", 0))
 268 |                         if now - completed_at > _JOB_TTL_COMPLETED:
 269 |                             expired_jobs.append(jid)
 270 |                     elif now - job.get("created", 0) > _RENDER_JOB_TTL:
 271 |                         expired_jobs.append(jid)
 272 |                 for jid in expired_jobs:
 273 |                     del _render_jobs[jid]
 274 |             if expired_jobs:
 275 |                 logger.info(f"[GC] Evicted {len(expired_jobs)} render jobs")
 276 | 
 277 |             # Clean orphaned SSE queues (job already evicted or completed)
 278 |             with _job_events_lock:
 279 |                 orphaned = [jid for jid in _job_events if jid not in _render_jobs]
 280 |                 for jid in orphaned:
 281 |                     _job_events.pop(jid, None)
 282 |             if orphaned:
 283 |                 logger.info(f"[GC] Evicted {len(orphaned)} orphaned SSE queues")
 284 |         except Exception as e:
 285 |             logger.error(f"[GC] Error during cleanup: {e}", exc_info=True)
 286 | 
 287 | 
 288 | threading.Thread(target=_gc_worker, daemon=True, name="gc_worker").start()
 289 | 
 290 | 
 291 | def _record_latency(seconds):
 292 |     with _lock:
 293 |         _request_times.append(seconds)
 294 |         if len(_request_times) > 100:
 295 |             _request_times.pop(0)
 296 | 
 297 | 
 298 | # ═══════════════════════════════════════════════════════════════════════
 299 | # WAV2LIP INFERENCE (FP16)
 300 | # ═══════════════════════════════════════════════════════════════════════
 301 | 
 302 | FACE_BBOX_CACHE = os.path.join(os.path.dirname(__file__), "cache", "face_bbox.json")
 303 | 
 304 | 
 305 | def wav2lip_generate(audio_path, fps=30.0, avatar_face=None, avatar_face_coords=None):
 306 |     """Run Wav2Lip inference in FP16. Returns list of BGR frames with duration matching.
 307 |     Optional avatar_face/avatar_face_coords override the default ModelRegistry face.
 308 |     """
 309 |     reg = ModelRegistry.get()
 310 |     if reg.wav2lip_model is None:
 311 |         raise RuntimeError("Model not loaded")
 312 | 
 313 |     # Use overrides if provided, else default from registry
 314 |     face_img = avatar_face if avatar_face is not None else reg.avatar_face
 315 |     face_coords = avatar_face_coords if avatar_face_coords is not None else reg.avatar_face_coords
 316 | 
 317 |     if face_img is None or face_coords is None:
 318 |         raise RuntimeError("Avatar face not loaded")
 319 | 
 320 |     if WAV2LIP_DIR not in sys.path:
 321 |         sys.path.insert(0, WAV2LIP_DIR)
 322 |     import audio as wav2lip_audio
 323 | 
 324 |     wav = wav2lip_audio.load_wav(audio_path, 16000)
 325 |     mel = wav2lip_audio.melspectrogram(wav)
 326 |     if mel.shape[1] == 0:
 327 |         raise ValueError("Empty audio")
 328 | 
 329 |     mel_step = 16
 330 |     audio_duration = len(wav) / 16000.0
 331 |     num_frames = int(math.ceil(audio_duration * fps)) + 2  # prevent audio cutoff
 332 |     if num_frames < 1:
 333 |         num_frames = 1
 334 | 
 335 |     # Map each VIDEO frame to its correct MEL position
 336 |     mel_idx_multiplier = 80.0 / fps
 337 | 
 338 |     mel_chunks = []
 339 |     for frame_i in range(num_frames):
 340 |         start_col = int(frame_i * mel_idx_multiplier)
 341 |         end_col = start_col + mel_step
 342 |         if end_col > mel.shape[1]:
 343 |             chunk = mel[:, start_col:]
 344 |             if chunk.shape[1] < mel_step:
 345 |                 chunk = np.pad(chunk, ((0, 0), (0, mel_step - chunk.shape[1])))
 346 |         else:
 347 |             chunk = mel[:, start_col:end_col]
 348 |         mel_chunks.append(chunk)
 349 | 
 350 |     # Adaptive batch size: smaller for short audio
 351 |     batch_size = BATCH_SIZE_SMALL if len(mel_chunks) < 60 else BATCH_SIZE_DEFAULT
 352 | 
 353 |     logger.info(f"Mel: {mel.shape[1]} cols, {num_frames} frames @ {fps}fps, audio {audio_duration:.2f}s, batch={batch_size}")
 354 | 
 355 |     # Face bbox with chin padding (8% lower to eliminate chin seam)
 356 |     y1, y2, x1, x2 = face_coords
 357 |     y2 = min(face_img.shape[0], y2 + int((y2 - y1) * 0.08))
 358 |     face_crop = face_img[y1:y2, x1:x2]
 359 |     face_resized = cv2.resize(face_crop, (96, 96))
 360 |     face_masked = face_resized.copy()
 361 |     face_masked[face_resized.shape[0] // 2:, :] = 0
 362 | 
 363 |     frames = []
 364 |     total_chunks = len(mel_chunks)
 365 | 
 366 |     for batch_start in range(0, total_chunks, batch_size):
 367 |         batch_end = min(batch_start + batch_size, total_chunks)
 368 |         batch_mels = mel_chunks[batch_start:batch_end]
 369 | 
 370 |         img_concat = np.concatenate((face_masked, face_resized), axis=2)
 371 |         img_batch = np.array([img_concat / 255.0] * len(batch_mels), dtype=np.float32)
 372 |         mel_batch = np.array(batch_mels, dtype=np.float32)
 373 | 
 374 |         # FP16 tensors → GPU 1
 375 |         img_batch = torch.HalfTensor(img_batch.transpose(0, 3, 1, 2)).to(DEVICE)
 376 |         mel_batch = torch.HalfTensor(mel_batch[:, np.newaxis, :, :]).to(DEVICE)
 377 | 
 378 |         with torch.no_grad():
 379 |             pred = reg.wav2lip_model(mel_batch, img_batch)
 380 | 
 381 |         pred = pred.float().cpu().numpy().transpose(0, 2, 3, 1) * 255.0
 382 | 
 383 |         for p in pred:
 384 |             p_resized = cv2.resize(p.astype(np.uint8), (x2 - x1, y2 - y1))
 385 |             full_frame = face_img.copy()
 386 |             # Feathered blend to eliminate face paste seam
 387 |             mask = np.ones_like(p_resized, dtype=np.float32)
 388 |             feather = 18
 389 |             h_face, w_face = p_resized.shape[:2]
 390 |             for j in range(min(feather, h_face)):
 391 |                 mask[j, :] = j / feather
 392 |             for j in range(min(feather, h_face)):
 393 |                 mask[-(j+1), :] = j / feather
 394 |             for j in range(min(feather, w_face)):
 395 |                 mask[:, j] *= j / feather
 396 |             for j in range(min(feather, w_face)):
 397 |                 mask[:, -(j+1)] *= j / feather
 398 |             full_frame[y1:y2, x1:x2] = (
 399 |                 p_resized * mask + full_frame[y1:y2, x1:x2] * (1 - mask)
 400 |             ).astype(np.uint8)
 401 |             frames.append(full_frame)
 402 | 
 403 |     logger.info(f"Generated {len(frames)} frames for {audio_duration:.2f}s audio @ {fps}fps")
 404 |     return frames
 405 | 
 406 | 
 407 | # ═══════════════════════════════════════════════════════════════════════
 408 | # POST-PROCESSING: HEAD MOVEMENT
 409 | # ═══════════════════════════════════════════════════════════════════════
 410 | 
 411 | def apply_head_movement(frame, frame_idx, fps):
 412 |     # LAW: NO rotation — warpAffine on portrait avatar looks like body spinning.
 413 |     # Only micro XY translation: subtle alive-breathing feel, not distracting.
 414 |     t = frame_idx / fps
 415 |     # Gentle breathing drift: max ±1.5px horizontal, ±1px vertical
 416 |     # Two overlapping slow sinusoids so it never feels mechanical
 417 |     tx = (
 418 |         1.0 * math.sin(2 * math.pi * t / 6.0 + 0.8) +
 419 |         0.5 * math.sin(2 * math.pi * t / 11.0 + 2.1)
 420 |     )
 421 |     ty = (
 422 |         0.8 * math.sin(2 * math.pi * t / 7.5 + 1.5) +
 423 |         0.2 * math.sin(2 * math.pi * t / 4.2 + 0.6)
 424 |     )
 425 |     # Integer shift only — no warpAffine, no rotation, no interpolation artifacts
 426 |     ix, iy = int(round(tx)), int(round(ty))
 427 |     if ix == 0 and iy == 0:
 428 |         return frame
 429 |     h, w = frame.shape[:2]
 430 |     result = frame.copy()
 431 |     # Clip-and-shift: roll pixels, fill edges with border value
 432 |     if ix > 0:
 433 |         result[:, ix:] = frame[:, :w-ix]
 434 |         result[:, :ix] = frame[:, :1]
 435 |     elif ix < 0:
 436 |         result[:, :w+ix] = frame[:, -ix:]
 437 |         result[:, w+ix:] = frame[:, -1:]
 438 |     tmp = result.copy()
 439 |     if iy > 0:
 440 |         result[iy:, :] = tmp[:h-iy, :]
 441 |         result[:iy, :] = tmp[:1, :]
 442 |     elif iy < 0:
 443 |         result[:h+iy, :] = tmp[-iy:, :]
 444 |         result[h+iy:, :] = tmp[-1:, :]
 445 |     return result
 446 | 
 447 | 
 448 | # ═══════════════════════════════════════════════════════════════════════
 449 | # POST-PROCESSING: COMBINED PIPELINE
 450 | # ═══════════════════════════════════════════════════════════════════════
 451 | 
 452 | def post_process_frames(frames, fps=30.0, enable_blinks=True, enable_head=True):
 453 |     """Apply eye blinks and head movement post-processing."""
 454 |     if len(frames) == 0:
 455 |         return frames
 456 | 
 457 |     reg = ModelRegistry.get()
 458 | 
 459 |     # Generate blink schedule
 460 |     blink_schedule = {}
 461 |     if enable_blinks:
 462 |         blink_schedule = generate_blink_schedule(
 463 |             len(frames), fps,
 464 |             interval_min=BLINK_INTERVAL_MIN,
 465 |             interval_max=BLINK_INTERVAL_MAX,
 466 |             duration=BLINK_DURATION,
 467 |         )
 468 | 
 469 |     processed = []
 470 |     for i, frame in enumerate(frames):
 471 |         result = frame
 472 |         if enable_blinks and i in blink_schedule:
 473 |             try:
 474 |                 result = apply_blink_gradient(
 475 |                     result,
 476 |                     blink_schedule[i],
 477 |                     eye_landmarks=reg.eye_landmarks,
 478 |                     face_coords=reg.avatar_face_coords,
 479 |                 )
 480 |             except Exception as e:
 481 |                 # P0 safety net: blink artifacts → return original frame, but log
 482 |                 logger.error(f"[POST] Blink post-process failed on frame {i}: {e}", exc_info=True)
 483 |                 result = frame
 484 |         if enable_head:
 485 |             result = apply_head_movement(result, i, fps)
 486 |         processed.append(result)
 487 |     return processed
 488 | 
 489 | 
 490 | # ═══════════════════════════════════════════════════════════════════════
 491 | # VIDEO ENCODING
 492 | # ═══════════════════════════════════════════════════════════════════════
 493 | 
 494 | def frames_to_video(frames, fps=30.0, audio_path=None):
 495 |     """Encode frames to MP4, optionally muxing audio (audio as timing master).
 496 |     Returns the path to the output MP4 file (caller must clean up)."""
 497 |     if not frames:
 498 |         return None
 499 |     with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as tmp_avi:
 500 |         avi_path = tmp_avi.name
 501 |     mp4_path = avi_path.replace(".avi", ".mp4")
 502 |     try:
 503 |         h, w = frames[0].shape[:2]
 504 |         fourcc = cv2.VideoWriter_fourcc(*"MJPG")
 505 |         writer = cv2.VideoWriter(avi_path, fourcc, fps, (w, h))
 506 |         for frame in frames:
 507 |             writer.write(frame)
 508 |         writer.release()
 509 | 
 510 |         import subprocess
 511 |         if audio_path and os.path.exists(audio_path):
 512 |             cmd = [
 513 |                 "ffmpeg", "-y", "-loglevel", "error",
 514 |                 "-itsoffset", "0.08", "-i", audio_path, "-i", avi_path,
 515 |             ]
 516 |             if w > 512:
 517 |                 cmd += ["-vf", "scale=512:512"]
 518 |             cmd += [
 519 |                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
 520 |                 "-c:a", "aac", "-b:a", "128k",
 521 |                 "-map", "0:a", "-map", "1:v",
 522 |                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
 523 |                 mp4_path,
 524 |             ]
 525 |             subprocess.run(cmd, check=True, capture_output=True)
 526 |         else:
 527 |             cmd = [
 528 |                 "ffmpeg", "-y", "-loglevel", "error",
 529 |                 "-i", avi_path,
 530 |             ]
 531 |             if w > 512:
 532 |                 cmd += ["-vf", "scale=512:512"]
 533 |             cmd += [
 534 |                 "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
 535 |                 "-pix_fmt", "yuv420p", "-movflags", "+faststart",
 536 |                 mp4_path,
 537 |             ]
 538 |             subprocess.run(cmd, check=True, capture_output=True)
 539 | 
 540 |         if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
 541 |             return mp4_path
 542 |         else:
 543 |             logger.error("ffmpeg failed to produce MP4")
 544 |             return None
 545 |     finally:
 546 |         try:
 547 |             os.unlink(avi_path)
 548 |         except OSError:
 549 |             pass
 550 | 
 551 | 
 552 | # ═══════════════════════════════════════════════════════════════════════
 553 | # KOKORO af_heart FEMALE VOICE (primary) + ELEVENLABS FALLBACK
 554 | # ═══════════════════════════════════════════════════════════════════════
 555 | 
 556 | def _init_avatar_kokoro():
 557 |     """Lazy-init Kokoro af_heart TTS on cuda:1. Call once at startup."""
 558 |     global _AVATAR_KOKORO_READY, _KOKORO_PIPELINE
 559 |     try:
 560 |         from kokoro import KPipeline
 561 |         _KOKORO_PIPELINE = KPipeline(lang_code='a')
 562 |         _KOKORO_PIPELINE.model = _KOKORO_PIPELINE.model.to('cuda:1')
 563 |         _AVATAR_KOKORO_READY = True
 564 |         logger.info("[AVATAR_TTS] Kokoro af_heart loaded on cuda:1")
 565 |     except Exception as e:
 566 |         logger.error(f"[AVATAR_TTS] Kokoro init failed: {e} — ElevenLabs fallback active")
 567 |         _AVATAR_KOKORO_READY = False
 568 | 
 569 | 
 570 | def _preprocess_tts_text(text: str) -> str:
 571 |     """Convert numbers and symbols to spoken form for natural TTS."""
 572 |     import re
 573 |     try:
 574 |         from num2words import num2words
 575 |     except ImportError:
 576 |         return text
 577 | 
 578 |     # Percentages: 0.79% → "point seventy-nine percent"
 579 |     def pct(m):
 580 |         try:
 581 |             val = float(m.group(1))
 582 |             if val == int(val):
 583 |                 return num2words(int(val)) + ' percent'
 584 |             parts = str(val).split('.')
 585 |             return num2words(int(parts[0])) + ' point ' + ' '.join(num2words(int(d)) for d in parts[1]) + ' percent'
 586 |         except: return m.group(0)
 587 |     text = re.sub(r'([\d]+\.?\d*)\s*%', pct, text)
 588 | 
 589 |     # Dollars: $70,586 → "seventy thousand five hundred eighty-six dollars"
 590 |     def dollars(m):
 591 |         try:
 592 |             raw = m.group(1).replace(',', '')
 593 |             val = int(float(raw))
 594 |             return num2words(val) + ' dollars'
 595 |         except: return m.group(0)
 596 |     text = re.sub(r'\$\s*([\d,]+\.?\d*)', dollars, text)
 597 | 
 598 |     # Large numbers with commas: 970,600 → spoken
 599 |     def bignum(m):
 600 |         try: return num2words(int(m.group(0).replace(',', '')))
 601 |         except: return m.group(0)
 602 |     text = re.sub(r'\b\d{1,3}(?:,\d{3})+\b', bignum, text)
 603 | 
 604 |     # Decimals: 970.6 → "nine hundred seventy point six"
 605 |     def decimal(m):
 606 |         try:
 607 |             parts = m.group(0).split('.')
 608 |             return num2words(int(parts[0])) + ' point ' + ' '.join(num2words(int(d)) for d in parts[1])
 609 |         except: return m.group(0)
 610 |     text = re.sub(r'\b(\d+)\.(\d+)\b', decimal, text)
 611 | 
 612 |     # Large plain integers 4+ digits
 613 |     def integer(m):
 614 |         try: return num2words(int(m.group(0)))
 615 |         except: return m.group(0)
 616 |     text = re.sub(r'\b(\d{4,})\b', integer, text)
 617 | 
 618 |     # Proper pronunciations
 619 |     text = re.sub(r'\bNostr\b', 'Nohster', text)
 620 |     text = re.sub(r'\bNOSTR\b', 'Nohster', text)
 621 |     text = re.sub(r'\bnostr\b', 'Nohster', text)
 622 |     text = re.sub(r'\bBTC\b', 'Bitcoin', text)
 623 |     text = re.sub(r'\bETF\b', 'E T F', text)
 624 |     text = re.sub(r'\bFNG\b', 'fear and greed index', text, flags=re.IGNORECASE)
 625 |     text = re.sub(r'\bEH/s\b', 'exahashes per second', text)
 626 |     text = re.sub(r'\bEH\b', 'exahash', text)
 627 |     text = re.sub(r'\bsat/vbyte\b', 'sats per vbyte', text)
 628 | 
 629 |     return text
 630 | 
 631 | 
 632 | def _avatar_tts(text):
 633 |     """Primary TTS: Kokoro af_heart -> 24kHz numpy -> ffmpeg resample 16kHz mono WAV bytes.
 634 |     Falls back to ElevenLabs text_to_speech() if Kokoro fails."""
 635 |     global _AVATAR_KOKORO_READY
 636 | 
 637 |     # Normalize Bitcoin pronunciation (BTC -> "bitcoin", sats, hashrate, etc.)
 638 |     try:
 639 |         from oracle_dialogue_engine import normalize_pronunciation
 640 |         text = normalize_pronunciation(text)
 641 |     except Exception as _np_err:
 642 |         logger.warning(f"[AVATAR_TTS] normalize_pronunciation unavailable: {_np_err}")
 643 | 
 644 |     text = _preprocess_tts_text(text)
 645 | 
 646 |     # Try Kokoro first
 647 |     if _AVATAR_KOKORO_READY and _KOKORO_PIPELINE is not None:
 648 |         t0 = time.time()
 649 |         try:
 650 |             import soundfile as sf
 651 |             # Generate with af_heart voice
 652 |             generator = _KOKORO_PIPELINE(text, voice='af_heart')
 653 |             # Collect all audio chunks
 654 |             audio_chunks = []
 655 |             for _gs, _ps, audio_np in generator:
 656 |                 audio_chunks.append(audio_np)
 657 |             if not audio_chunks:
 658 |                 raise ValueError("Kokoro returned no audio")
 659 |             full_audio = np.concatenate(audio_chunks)
 660 | 
 661 |             # Write 24kHz WAV to temp file
 662 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 663 |                 sf.write(tmp.name, full_audio, 24000)
 664 |                 wav24_path = tmp.name
 665 | 
 666 |             # Resample to 16kHz mono + loudnorm in single ffmpeg call
 667 |             wav16_path = wav24_path + ".16k.wav"
 668 |             r = subprocess.run(
 669 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", wav24_path,
 670 |                  "-af", "aresample=16000,loudnorm=I=-14:TP=-1.5:LRA=11",
 671 |                  "-ac", "1", "-f", "wav", wav16_path],
 672 |                 capture_output=True, text=True, timeout=30,
 673 |             )
 674 |             try:
 675 |                 os.remove(wav24_path)
 676 |             except OSError:
 677 |                 pass
 678 |             if r.returncode == 0 and os.path.exists(wav16_path) and os.path.getsize(wav16_path) > 1000:
 679 |                 with open(wav16_path, "rb") as f:
 680 |                     wav_bytes = f.read()
 681 |                 try:
 682 |                     os.remove(wav16_path)
 683 |                 except OSError:
 684 |                     pass
 685 |                 elapsed = time.time() - t0
 686 |                 logger.info(f"[AVATAR_TTS] Kokoro af_heart OK: {elapsed:.2f}s ({len(wav_bytes)} bytes)")
 687 |                 return wav_bytes
 688 |             else:
 689 |                 logger.warning("[AVATAR_TTS] Kokoro ffmpeg resample failed")
 690 |         except Exception as e:
 691 |             logger.error(f"[AVATAR_TTS] Kokoro FAILED: {e} → ElevenLabs fallback")
 692 |     else:
 693 |         logger.info("[AVATAR_TTS] Kokoro not ready → ElevenLabs fallback")
 694 | 
 695 |     # Fallback: ElevenLabs
 696 |     t0 = time.time()
 697 |     audio_bytes = text_to_speech(text)
 698 |     elapsed = time.time() - t0
 699 |     logger.info(f"[AVATAR_TTS] ElevenLabs fallback: {elapsed:.2f}s ({len(audio_bytes)} bytes)")
 700 |     return audio_bytes
 701 | 
 702 | 
 703 | def text_to_speech(text, voice_id="cgSgspJ2msm6clMCkdW9"):
 704 |     """Call ElevenLabs TTS API. Returns raw audio bytes (mp3)."""
 705 |     api_key = os.environ.get("ELEVENLABS_API_KEY", "")
 706 |     if not api_key:
 707 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
 708 |         if os.path.exists(env_path):
 709 |             for line in open(env_path):
 710 |                 if line.startswith("ELEVENLABS_API_KEY="):
 711 |                     api_key = line.strip().split("=", 1)[1].strip().strip("\"'")
 712 |     if not api_key:
 713 |         raise ValueError("ELEVENLABS_API_KEY not found in environment or .env")
 714 |     resp = http_requests.post(
 715 |         f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
 716 |         headers={"xi-api-key": api_key, "Content-Type": "application/json"},
 717 |         json={
 718 |             "text": text,
 719 |             "model_id": "eleven_turbo_v2_5",
 720 |             # LAW 3: Jessica voice settings — stability=0.45, similarity_boost=0.75, style=0.20
 721 |             "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.20},
 722 |         },
 723 |         timeout=60,
 724 |     )
 725 |     if resp.status_code != 200:
 726 |         raise Exception(f"ElevenLabs error {resp.status_code}: {resp.text[:200]}")
 727 |     return resp.content
 728 | 
 729 | 
 730 | # ═══════════════════════════════════════════════════════════════════════
 731 | # FLASK ROUTES
 732 | # ═══════════════════════════════════════════════════════════════════════
 733 | 
 734 | @app.route("/health")
 735 | def health():
 736 |     """Enhanced health check with VRAM, latency, vision status, enhancer info."""
 737 |     reg = ModelRegistry.get() if ModelRegistry.is_loaded() else None
 738 |     vram = reg.vram_info() if reg else {"available": False}
 739 | 
 740 |     vision_enabled = bool(os.environ.get("GEMINI_API_KEY"))
 741 |     with _lock:
 742 |         avg_latency = round(sum(_request_times) / len(_request_times), 2) if _request_times else None
 743 |         tracked = len(_request_times)
 744 |     uptime = round(time.time() - _start_time, 1)
 745 | 
 746 |     return jsonify({
 747 |         "status": "ok",
 748 |         "engine": "wav2lip-gan-fp16-v2",
 749 |         "enhancements": ["fp16", "cached_face", "cv2_sharpen", "mediapipe_blinks", "head_movement"],
 750 |         "device": DEVICE,
 751 |         "model_loaded": reg is not None and reg.wav2lip_model is not None,
 752 |         "avatar_loaded": reg is not None and reg.avatar_face is not None,
 753 |         "avatar_size": (
 754 |             f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}"
 755 |             if reg and reg.avatar_face is not None else None
 756 |         ),
 757 |         "face_detected": reg is not None and reg.avatar_face_coords is not None,
 758 |         "face_enhancer": "cv2_sharpen_only",
 759 |         "blinks_enabled": True,  # v2 engine: cached landmarks
 760 |         "eye_landmarks_detected": (lambda: __import__("blink_engine")._load_cache() is not None)(),
 761 |         "vram": vram,
 762 |         "vision_enabled": vision_enabled,
 763 |         "uptime_sec": uptime,
 764 |         "avg_latency_sec": avg_latency,
 765 |         "requests_tracked": tracked,
 766 |         "output_fps": DEFAULT_FPS,
 767 |         "batch_size": BATCH_SIZE,
 768 |         "max_audio_seconds": MAX_AUDIO_SECONDS,
 769 |         "encoding": "crf23-ultrafast-512",
 770 |         "blink_config": {
 771 |             "interval": f"{BLINK_INTERVAL_MIN}-{BLINK_INTERVAL_MAX}s",
 772 |             "duration": f"{BLINK_DURATION}s"
 773 |         },
 774 |         "head_movement_config": {
 775 |             "rotation": f"\u00b1{HEAD_ROTATION_AMPLITUDE}\u00b0",
 776 |             "period": f"{HEAD_PERIOD}s"
 777 |         }
 778 |     })
 779 | 
 780 | 
 781 | @app.route("/status")
 782 | def status():
 783 |     """Alias for /health — frontend expects this route."""
 784 |     return health()
 785 | 
 786 | 
 787 | @app.route("/warmup", methods=["POST"])
 788 | def warmup():
 789 |     """Generate a tiny test video to warm up torch.compile and CUDA kernels."""
 790 |     t0 = time.time()
 791 |     reg = ModelRegistry.get()
 792 |     if reg.wav2lip_model is None:
 793 |         return jsonify({"error": "Model not loaded"}), 500
 794 | 
 795 |     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
 796 |         import wave
 797 |         with wave.open(tmp.name, "w") as wf:
 798 |             wf.setnchannels(1)
 799 |             wf.setsampwidth(2)
 800 |             wf.setframerate(16000)
 801 |             wf.writeframes(b"\x00\x00" * 8000)
 802 |         wav_path = tmp.name
 803 | 
 804 |     try:
 805 |         _render_semaphore.acquire()
 806 |         try:
 807 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
 808 |             if frames:
 809 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
 810 |         finally:
 811 |             _render_semaphore.release()
 812 |         elapsed = time.time() - t0
 813 |         logger.info(f"Warmup complete: {len(frames)} frames in {elapsed:.2f}s")
 814 |         return jsonify({
 815 |             "status": "warmed_up",
 816 |             "frames": len(frames),
 817 |             "warmup_time": round(elapsed, 2),
 818 |             "vram": reg.vram_info(),
 819 |         })
 820 |     except Exception as e:
 821 |         logger.error(f"Warmup error: {e}", exc_info=True)
 822 |         return jsonify({"error": str(e)}), 500
 823 |     finally:
 824 |         try:
 825 |             os.unlink(wav_path)
 826 |         except OSError:
 827 |             pass
 828 | 
 829 | 
 830 | @app.route("/generate", methods=["POST"])
 831 | def generate():
 832 |     """Generate lip-synced video with face restoration, blinks, and head movement.
 833 | 
 834 |     Accepts two modes:
 835 |       Mode A: {"text": "..."} -> Kokoro af_heart (or ElevenLabs fallback) -> Wav2Lip -> video
 836 |       Mode B: {"audio_base64": "...", "content_type": "..."} -> Wav2Lip -> video
 837 |     """
 838 |     data = request.get_json()
 839 |     if not data:
 840 |         return jsonify({"error": "JSON body required"}), 400
 841 | 
 842 |     # Input validation
 843 |     MAX_TEXT_LEN = 2000
 844 |     MAX_AUDIO_B64_LEN = 2_000_000  # ~1.5MB decoded
 845 |     if "text" in data:
 846 |         if not isinstance(data["text"], str) or len(data["text"]) > MAX_TEXT_LEN:
 847 |             return jsonify({"error": f"text must be a string under {MAX_TEXT_LEN} chars", "code": "INVALID_INPUT"}), 400
 848 |         if not data["text"].strip():
 849 |             return jsonify({"error": "text cannot be empty", "code": "INVALID_INPUT"}), 400
 850 |     elif "audio_base64" in data:
 851 |         if not isinstance(data["audio_base64"], str) or len(data["audio_base64"]) > MAX_AUDIO_B64_LEN:
 852 |             return jsonify({"error": "audio_base64 too large or invalid", "code": "INVALID_INPUT"}), 400
 853 |         try:
 854 |             base64.b64decode(data["audio_base64"], validate=True)
 855 |         except Exception:
 856 |             return jsonify({"error": "audio_base64 is not valid base64", "code": "INVALID_INPUT"}), 400
 857 |     else:
 858 |         return jsonify({"error": "text or audio_base64 required"}), 400
 859 | 
 860 |     enable_blinks = data.get("enable_blinks", True)  # v2 blink engine enabled
 861 |     enable_head_movement = data.get("enable_head_movement", True)
 862 |     fps = float(data.get("fps", DEFAULT_FPS))
 863 |     avatar_source = data.get("avatar_source", "default")
 864 |     if avatar_source not in AVATAR_SOURCES:
 865 |         avatar_source = "default"
 866 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
 867 | 
 868 |     # Resolve face for this render
 869 |     gen_face, gen_coords, _gen_eyes = _load_avatar_face(avatar_source)
 870 |     if gen_face is None or gen_coords is None:
 871 |         gen_face, gen_coords, _gen_eyes = _load_avatar_face("default")
 872 | 
 873 |     t_start = time.time()
 874 | 
 875 |     # Mode A: text -> Kokoro af_heart (primary) or ElevenLabs (fallback)
 876 |     if "text" in data:
 877 |         try:
 878 |             t_tts = time.time()
 879 |             audio_bytes = _avatar_tts(data["text"])
 880 |             logger.info(f"TTS: {len(audio_bytes)} bytes in {time.time()-t_tts:.2f}s")
 881 |         except Exception as e:
 882 |             logger.error(f"TTS error: {e}")
 883 |             return jsonify({"error": f"TTS failed: {e}"}), 500
 884 |         # Kokoro returns WAV, ElevenLabs returns MP3 — detect from header
 885 |         content_type = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
 886 |     # Mode B: raw audio
 887 |     elif "audio_base64" in data:
 888 |         audio_bytes = base64.b64decode(data["audio_base64"])
 889 |         content_type = data.get("content_type", "audio/mpeg")
 890 |     else:
 891 |         return jsonify({"error": "text or audio_base64 required"}), 400
 892 | 
 893 |     ext = ".mp3" if "mpeg" in content_type else ".wav"
 894 | 
 895 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
 896 |         tmp.write(audio_bytes)
 897 |         audio_path = tmp.name
 898 | 
 899 |     wav_path = audio_path + "_16k.wav"
 900 |     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
 901 | 
 902 |     # Input length guard: check audio duration
 903 |     try:
 904 |         import subprocess as _sp
 905 |         probe = _sp.run(
 906 |             ["ffprobe", "-v", "error", "-show_entries", "format=duration",
 907 |              "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
 908 |             capture_output=True, text=True, timeout=10,
 909 |         )
 910 |         audio_duration_sec = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
 911 |     except Exception as e:
 912 |         logger.error(f"[GENERATE] ffprobe failed: {e}", exc_info=True)
 913 |         audio_duration_sec = 0.0
 914 | 
 915 |     if audio_duration_sec == 0.0:
 916 |         logger.warning("[GENERATE] Audio duration is 0 — possible corrupt file")
 917 |         return jsonify({"error": "Audio validation failed: could not determine duration", "code": "INVALID_AUDIO"}), 400
 918 | 
 919 |     if audio_duration_sec > MAX_AUDIO_SECONDS:
 920 |         logger.warning(f"Audio too long ({audio_duration_sec:.1f}s > {MAX_AUDIO_SECONDS}s) — rejecting")
 921 |         return jsonify({
 922 |             "error": f"Audio too long ({audio_duration_sec:.1f}s). Max {MAX_AUDIO_SECONDS}s.",
 923 |             "code": "AUDIO_TOO_LONG",
 924 |             "max_seconds": MAX_AUDIO_SECONDS,
 925 |         }), 400
 926 | 
 927 |     try:
 928 |         reg = ModelRegistry.get()
 929 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
 930 |         if not acquired:
 931 |             return jsonify({"error": "GPU busy", "code": "GPU_BUSY", "retry_after": 5}), 503
 932 |         try:
 933 |             t0 = time.time()
 934 |             frames = wav2lip_generate(wav_path, fps, avatar_face=gen_face, avatar_face_coords=gen_coords)
 935 |             t_lip = time.time() - t0
 936 |             logger.info(f"Wav2Lip FP16: {len(frames)} frames in {t_lip:.2f}s")
 937 | 
 938 |             # CV2 sharpen only — no GFPGAN
 939 |             t_enhance = 0.0
 940 |             if len(frames) > 0:
 941 |                 try:
 942 |                     t0_enh = time.time()
 943 |                     frames = sharpen_mouth_region(frames, gen_coords)
 944 |                     t_enhance = time.time() - t0_enh
 945 |                     logger.info(f"CV2 sharpen: {t_enhance:.2f}s")
 946 |                 except Exception as e:
 947 |                     logger.warning(f"Sharpen skipped: {e}")
 948 | 
 949 |             t0 = time.time()
 950 |             if enable_blinks or enable_head_movement:
 951 |                 frames = post_process_frames(
 952 |                     frames, fps,
 953 |                     enable_blinks=enable_blinks,
 954 |                     enable_head=enable_head_movement,
 955 |                 )
 956 |             t_post = time.time() - t0
 957 |             logger.info(f"Post-processing: {t_post:.2f}s")
 958 | 
 959 |             t0 = time.time()
 960 |             video_path = frames_to_video(frames, fps, audio_path=wav_path)
 961 |             t_encode = time.time() - t0
 962 |             logger.info(f"Encoding: {t_encode:.2f}s")
 963 |         finally:
 964 |             _render_semaphore.release()
 965 | 
 966 |         if not video_path:
 967 |             return jsonify({"error": "Video encoding failed", "code": "ENCODE_FAILED"}), 500
 968 | 
 969 |         t_total = time.time() - t_start
 970 |         _record_latency(t_total)
 971 |         duration = len(frames) / fps
 972 |         num_frames = len(frames)
 973 | 
 974 |         logger.info(
 975 |             f"Complete: {duration:.1f}s video, {num_frames} frames, "
 976 |             f"lip={t_lip:.1f}s enhance={t_enhance:.1f}s post={t_post:.1f}s enc={t_encode:.1f}s total={t_total:.1f}s"
 977 |         )
 978 | 
 979 |         cleanup_paths = [audio_path, wav_path, video_path]
 980 | 
 981 |         @after_this_request
 982 |         def _cleanup(response):
 983 |             for p in cleanup_paths:
 984 |                 try:
 985 |                     if p and os.path.exists(p):
 986 |                         os.unlink(p)
 987 |                 except OSError:
 988 |                     pass
 989 |             return response
 990 | 
 991 |         response = send_file(
 992 |             video_path,
 993 |             mimetype="video/mp4",
 994 |             as_attachment=True,
 995 |             download_name="oracle.mp4",
 996 |         )
 997 |         response.headers["X-Duration"] = str(round(duration, 2))
 998 |         response.headers["X-Frames"] = str(num_frames)
 999 |         response.headers["X-Processing-Time"] = str(round(t_total, 2))
1000 |         response.headers["X-Timing-Wav2Lip"] = str(round(t_lip, 2))
1001 |         response.headers["X-Timing-FaceEnhance"] = str(round(t_enhance, 2))
1002 |         response.headers["X-Timing-PostProcess"] = str(round(t_post, 2))
1003 |         response.headers["X-Timing-Encoding"] = str(round(t_encode, 2))
1004 |         return response
1005 | 
1006 |     except Exception as e:
1007 |         logger.error(f"Generation error: {e}", exc_info=True)
1008 |         return jsonify({"error": str(e), "code": "GENERATION_ERROR"}), 500
1009 |     finally:
1010 |         for p in [audio_path, wav_path]:
1011 |             try:
1012 |                 if os.path.exists(p):
1013 |                     os.unlink(p)
1014 |             except OSError:
1015 |                 pass
1016 | 
1017 | 
1018 | @app.route("/reload-avatar", methods=["POST"])
1019 | def reload_avatar():
1020 |     """Reload avatar source image via ModelRegistry."""
1021 |     reg = ModelRegistry.get()
1022 |     if reg.reload_avatar():
1023 |         return jsonify({
1024 |             "status": "reloaded",
1025 |             "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
1026 |             "face": reg.avatar_face_coords,
1027 |             "eye_landmarks": reg.eye_landmarks is not None,
1028 |         })
1029 |     else:
1030 |         return jsonify({"error": "No face detected in new image"}), 400
1031 | 
1032 | 
1033 | @app.route("/source-image")
1034 | def source_image():
1035 |     """Serve the current avatar source image."""
1036 |     reg = ModelRegistry.get()
1037 |     if reg.avatar_face is None:
1038 |         return jsonify({"error": "No avatar loaded"}), 404
1039 |     _, buf = cv2.imencode(".png", reg.avatar_face)
1040 |     b64 = base64.b64encode(buf).decode()
1041 |     return jsonify({
1042 |         "image_base64": b64,
1043 |         "size": f"{reg.avatar_face.shape[1]}x{reg.avatar_face.shape[0]}",
1044 |         "face_coords": reg.avatar_face_coords
1045 |     })
1046 | 
1047 | 
1048 | # ═══════════════════════════════════════════════════════════════════════
1049 | # VISION GUIDE ENDPOINTS
1050 | # ═══════════════════════════════════════════════════════════════════════
1051 | 
1052 | @app.route("/vision/analyze", methods=["POST"])
1053 | def vision_analyze():
1054 |     """Analyze a Bitcoin hardware image with Gemini 2.5 Flash."""
1055 |     data = request.get_json()
1056 |     if not data or not data.get("image_base64"):
1057 |         return jsonify({"error": "image_base64 required"}), 400
1058 | 
1059 |     # Strip data URL prefix if present (client may send data:image/...;base64,)
1060 |     image_b64 = data["image_base64"]
1061 |     if image_b64.startswith("data:"):
1062 |         image_b64 = image_b64.split(",", 1)[1]
1063 | 
1064 |     from vision_guide import analyze_image, GuideSession
1065 |     result = analyze_image(
1066 |         image_b64=image_b64,
1067 |         mime_type=data.get("mime_type", "image/jpeg"),
1068 |         context=data.get("context", ""),
1069 |     )
1070 | 
1071 |     if "error" in result:
1072 |         return jsonify(result), 500
1073 | 
1074 |     # Create a GuideSession so follow-up /vision/guide calls have context
1075 |     guide_session = GuideSession.get_or_create(data.get("session_id"))
1076 |     result["session_id"] = guide_session.session_id
1077 | 
1078 |     # Seed the guide session history with this first analysis
1079 |     guide_session.history.append({
1080 |         "role": "user",
1081 |         "parts": [
1082 |             {"text": data.get("context", "Analyze this Bitcoin hardware image.")},
1083 |             {"inlineData": {"mimeType": data.get("mime_type", "image/jpeg"), "data": image_b64}},
1084 |         ],
1085 |     })
1086 |     guidance = result.get("guidance_text", "")
1087 |     if guidance:
1088 |         guide_session.history.append({
1089 |             "role": "model",
1090 |             "parts": [{"text": guidance}],
1091 |         })
1092 |     if result.get("device_name") and result["device_name"] != "unknown":
1093 |         guide_session.device_name = result["device_name"]
1094 | 
1095 |     # Phase 4: Store vision context in dialogue session for carry-forward
1096 |     session_id = data.get("session_id", "anon")
1097 |     try:
1098 |         from oracle_dialogue_engine import _get_session
1099 |         session = _get_session(session_id)
1100 |         vision_history = session.get("vision_history", [])
1101 |         analysis_summary = result.get("summary", "") or str(result.get("device_name", ""))
1102 |         if result.get("current_step"):
1103 |             analysis_summary += f" — {result['current_step']}"
1104 |         vision_history.append({
1105 |             "turn": session.get("turn", 0),
1106 |             "summary": analysis_summary[:200],
1107 |         })
1108 |         session["vision_history"] = vision_history[-3:]  # keep last 3
1109 |     except Exception as e:
1110 |         logger.warning(f"[VISION] Failed to store vision context: {e}")
1111 | 
1112 |     return jsonify(result)
1113 | 
1114 | 
1115 | @app.route("/vision/guide", methods=["POST"])
1116 | def vision_guide():
1117 |     """Multi-turn hardware setup guide session."""
1118 |     data = request.get_json()
1119 |     if not data:
1120 |         return jsonify({"error": "JSON body required"}), 400
1121 | 
1122 |     from vision_guide import GuideSession
1123 |     session = GuideSession.get_or_create(data.get("session_id"))
1124 | 
1125 |     if data.get("image_base64"):
1126 |         # Strip data URL prefix if present
1127 |         img_b64 = data["image_base64"]
1128 |         if img_b64.startswith("data:"):
1129 |             img_b64 = img_b64.split(",", 1)[1]
1130 |         question = data.get("question", "")
1131 |         last_context = data.get("last_context", "")
1132 |         if last_context:
1133 |             question += f"\n\nUser completed these steps: {last_context}\nNow showing the next screen."
1134 |         result = session.send_image(
1135 |             image_b64=img_b64,
1136 |             mime_type=data.get("mime_type", "image/jpeg"),
1137 |             question=question,
1138 |         )
1139 |     elif data.get("question"):
1140 |         result = session.send_text(data["question"])
1141 |     else:
1142 |         return jsonify({"error": "image_base64 or question required"}), 400
1143 | 
1144 |     if "error" in result:
1145 |         return jsonify(result), 500
1146 |     return jsonify(result)
1147 | 
1148 | 
1149 | @app.route("/vision/status")
1150 | def vision_status():
1151 |     """Check if vision features are enabled."""
1152 |     gemini_key = os.environ.get("GEMINI_API_KEY", "")
1153 |     enabled = bool(gemini_key)
1154 |     if enabled:
1155 |         return jsonify({
1156 |             "status": "enabled",
1157 |             "model": "gemini-2.5-flash",
1158 |             "endpoints": ["/vision/analyze", "/vision/guide", "/vision/sessions"],
1159 |         })
1160 |     else:
1161 |         return jsonify({
1162 |             "status": "disabled",
1163 |             "reason": "GEMINI_API_KEY not configured",
1164 |             "setup_url": "https://aistudio.google.com/apikey",
1165 |         })
1166 | 
1167 | 
1168 | @app.route("/vision/sessions")
1169 | def vision_sessions():
1170 |     """List active vision guide sessions."""
1171 |     from vision_guide import GuideSession
1172 |     return jsonify({
1173 |         "active_sessions": GuideSession.active_count(),
1174 |     })
1175 | 
1176 | 
1177 | # ═══════════════════════════════════════════════════════════════════════
1178 | # STREAMING PIPELINE
1179 | # ═══════════════════════════════════════════════════════════════════════
1180 | 
1181 | import re
1182 | import uuid
1183 | import subprocess
1184 | 
1185 | ORACLE_SYSTEM_PROMPT = (
1186 |     "You are the Oracle — Protocol Pulse's personal Bitcoin intelligence guide. "
1187 |     "You are having a private one-on-one conversation with a visitor. "
1188 |     "You are an EDUCATOR (explain Bitcoin at any level), GUIDE (help navigate Protocol Pulse), "
1189 |     "TECHNICAL ASSISTANT (wallets, self-custody, nodes, hardware), and INTELLIGENCE ANALYST "
1190 |     "(market state, price action — conversational, not broadcast). "
1191 |     "TONE: Warm but sharp. Knowledgeable without being condescending. "
1192 |     "Like the smartest person in Bitcoin who actually has time for you. "
1193 |     "Keep responses under 3 sentences. Never say 'As an AI' or offer daily briefs unprompted. "
1194 |     "You are NOT a news anchor or briefing bot — you are a personal guide."
1195 | )
1196 | ORACLE_VOICE_ID = "cgSgspJ2msm6clMCkdW9"  # Jessica
1197 | ORACLE_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
1198 | ORACLE_IDLE_PATH = os.path.join(ORACLE_STATIC_DIR, "oracle_idle.mp4")
1199 | ORACLE_THINKING_PATH = os.path.join(os.path.dirname(__file__), "cache", "thinking_loop.mp4")
1200 | 
1201 | _stream_sessions = {}
1202 | _stream_lock = threading.Lock()
1203 | 
1204 | 
1205 | def _get_anthropic_key():
1206 |     """Get Anthropic API key from env or .env file."""
1207 |     key = os.environ.get("ANTHROPIC_API_KEY", "")
1208 |     if not key:
1209 |         env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
1210 |         if os.path.exists(env_path):
1211 |             for line in open(env_path):
1212 |                 if line.startswith("ANTHROPIC_API_KEY="):
1213 |                     key = line.strip().split("=", 1)[1].strip().strip("\"'")
1214 |     return key
1215 | 
1216 | 
1217 | def _split_sentences(text):
1218 |     """Split text into sentences for chunked processing."""
1219 |     sentences = re.split(r'(?<=[.!?])\s+', text.strip())
1220 |     return [s for s in sentences if s.strip()]
1221 | 
1222 | 
1223 | def _generate_chunk(sentence, chunk_num, session_dir, fps=30.0):
1224 |     """Generate a single video chunk for a sentence: TTS -> Wav2Lip -> MP4."""
1225 |     try:
1226 |         audio_bytes = _avatar_tts(sentence)
1227 |         is_wav = audio_bytes[:4] == b"RIFF"
1228 |         ext = ".wav" if is_wav else ".mp3"
1229 |         audio_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}{ext}")
1230 |         with open(audio_path, "wb") as f:
1231 |             f.write(audio_bytes)
1232 | 
1233 |         wav_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}_16k.wav")
1234 |         if is_wav:
1235 |             # F5 already returned 16kHz mono WAV — just copy
1236 |             import shutil
1237 |             shutil.copy2(audio_path, wav_path)
1238 |         else:
1239 |             subprocess.run(
1240 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
1241 |                 check=True, capture_output=True,
1242 |             )
1243 | 
1244 |         _render_semaphore.acquire()
1245 |         try:
1246 |             frames = wav2lip_generate(wav_path, fps)
1247 |             reg = ModelRegistry.get()
1248 |             try:
1249 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1250 |             except Exception as e:
1251 |                 logger.warning(f"[CHUNK] Sharpening failed on chunk {chunk_num}: {e}", exc_info=True)
1252 |             frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1253 |         finally:
1254 |             _render_semaphore.release()
1255 | 
1256 |         video_path = os.path.join(session_dir, f"chunk_{chunk_num:03d}.mp4")
1257 |         tmp_path = frames_to_video(frames, fps, audio_path=wav_path)
1258 |         if tmp_path:
1259 |             os.rename(tmp_path, video_path)
1260 |             return video_path
1261 |         return None
1262 |     except Exception as e:
1263 |         logger.error(f"Chunk {chunk_num} generation error: {e}", exc_info=True)
1264 |         return None
1265 | 
1266 | 
1267 | def _stream_worker(session_id, text):
1268 |     """Background worker: call Claude -> split sentences -> generate chunks."""
1269 |     session = _stream_sessions.get(session_id)
1270 |     if not session:
1271 |         return
1272 | 
1273 |     try:
1274 |         api_key = _get_anthropic_key()
1275 |         if not api_key:
1276 |             logger.warning("No Anthropic key — using input text as-is")
1277 |             ai_text = text
1278 |         else:
1279 |             resp = http_requests.post(
1280 |                 "https://api.anthropic.com/v1/messages",
1281 |                 headers={
1282 |                     "x-api-key": api_key,
1283 |                     "anthropic-version": "2023-06-01",
1284 |                     "content-type": "application/json",
1285 |                 },
1286 |                 json={
1287 |                     "model": "claude-sonnet-4-20250514",
1288 |                     "max_tokens": 80,  # Short transcript = fewer TTS seconds = fewer Wav2Lip frames
1289 |                     "system": ORACLE_SYSTEM_PROMPT,
1290 |                     "messages": [{"role": "user", "content": text}],
1291 |                 },
1292 |                 timeout=30,
1293 |             )
1294 |             if resp.status_code == 200:
1295 |                 ai_text = resp.json()["content"][0]["text"]
1296 |             else:
1297 |                 logger.error(f"Claude API error {resp.status_code}: {resp.text[:200]}")
1298 |                 ai_text = text
1299 | 
1300 |         session["ai_response"] = ai_text
1301 |         sentences = _split_sentences(ai_text)
1302 |         session["total_chunks"] = len(sentences)
1303 | 
1304 |         session_dir = session["dir"]
1305 |         for i, sentence in enumerate(sentences):
1306 |             chunk_path = _generate_chunk(sentence, i, session_dir)
1307 |             if chunk_path:
1308 |                 session["chunks_ready"].append(chunk_path)
1309 |             else:
1310 |                 session["errors"].append(f"Chunk {i} failed")
1311 | 
1312 |         session["status"] = "complete"
1313 | 
1314 |     except Exception as e:
1315 |         logger.error(f"Stream worker error: {e}", exc_info=True)
1316 |         session["status"] = "error"
1317 |         session["errors"].append(str(e))
1318 | 
1319 | 
1320 | @app.route("/generate_stream", methods=["POST"])
1321 | def generate_stream():
1322 |     """Start streaming generation: text -> Claude -> sentence chunks -> video chunks."""
1323 |     data = request.get_json()
1324 |     if not data or not data.get("text"):
1325 |         return jsonify({"error": "text required"}), 400
1326 | 
1327 |     session_id = str(uuid.uuid4())[:12]
1328 |     session_dir = os.path.join(tempfile.gettempdir(), f"oracle_stream_{session_id}")
1329 |     os.makedirs(session_dir, exist_ok=True)
1330 | 
1331 |     session = {
1332 |         "id": session_id,
1333 |         "status": "processing",
1334 |         "text": data["text"],
1335 |         "ai_response": None,
1336 |         "total_chunks": 0,
1337 |         "chunks_ready": [],
1338 |         "errors": [],
1339 |         "dir": session_dir,
1340 |         "created": time.time(),
1341 |     }
1342 | 
1343 |     with _stream_lock:
1344 |         _stream_sessions[session_id] = session
1345 | 
1346 |     thread = threading.Thread(target=_stream_worker, args=(session_id, data["text"]), daemon=True)
1347 |     thread.start()
1348 | 
1349 |     return jsonify({
1350 |         "session_id": session_id,
1351 |         "status": "processing",
1352 |         "message": "Stream generation started. Poll /stream_status/{session_id} for progress.",
1353 |     })
1354 | 
1355 | 
1356 | @app.route("/stream_status/<session_id>")
1357 | def stream_status(session_id):
1358 |     """Poll for streaming generation progress."""
1359 |     session = _stream_sessions.get(session_id)
1360 |     if not session:
1361 |         return jsonify({"error": "Session not found"}), 404
1362 | 
1363 |     return jsonify({
1364 |         "session_id": session_id,
1365 |         "status": session["status"],
1366 |         "ai_response": session.get("ai_response"),
1367 |         "chunks_ready": len(session["chunks_ready"]),
1368 |         "total_chunks": session["total_chunks"],
1369 |         "total_estimated": max(session["total_chunks"], 3),
1370 |         "errors": session["errors"],
1371 |     })
1372 | 
1373 | 
1374 | @app.route("/stream_chunk/<session_id>/<int:chunk_number>")
1375 | def stream_chunk(session_id, chunk_number):
1376 |     """Fetch a generated video chunk by number."""
1377 |     session = _stream_sessions.get(session_id)
1378 |     if not session:
1379 |         return jsonify({"error": "Session not found"}), 404
1380 | 
1381 |     if chunk_number >= len(session["chunks_ready"]):
1382 |         return jsonify({"error": "Chunk not ready yet"}), 404
1383 | 
1384 |     chunk_path = session["chunks_ready"][chunk_number]
1385 |     if not os.path.exists(chunk_path):
1386 |         return jsonify({"error": "Chunk file missing"}), 500
1387 | 
1388 |     return send_file(chunk_path, mimetype="video/mp4", as_attachment=True,
1389 |                      download_name=f"chunk_{chunk_number:03d}.mp4")
1390 | 
1391 | 
1392 | @app.route("/oracle_idle")
1393 | def oracle_idle():
1394 |     """Serve the pre-rendered idle loop video."""
1395 |     if os.path.exists(ORACLE_IDLE_PATH):
1396 |         return send_file(ORACLE_IDLE_PATH, mimetype="video/mp4")
1397 |     return jsonify({"error": "Idle video not generated yet"}), 404
1398 | 
1399 | 
1400 | @app.route("/oracle/thinking")
1401 | def oracle_thinking():
1402 |     """Serve the pre-rendered thinking loop video (Phase 2: T1.4)."""
1403 |     if os.path.exists(ORACLE_THINKING_PATH):
1404 |         return send_file(ORACLE_THINKING_PATH, mimetype="video/mp4")
1405 |     # Fallback to idle loop if thinking video not yet generated
1406 |     if os.path.exists(ORACLE_IDLE_PATH):
1407 |         return send_file(ORACLE_IDLE_PATH, mimetype="video/mp4")
1408 |     return jsonify({"error": "not ready"}), 404
1409 | 
1410 | 
1411 | def generate_idle_loop():
1412 |     """Generate a 4-second idle loop with blinks + head movement (no audio)."""
1413 |     os.makedirs(ORACLE_STATIC_DIR, exist_ok=True)
1414 |     if os.path.exists(ORACLE_IDLE_PATH):
1415 |         logger.info("Idle loop already exists, skipping generation")
1416 |         return
1417 | 
1418 |     logger.info("Generating idle loop video...")
1419 |     reg = ModelRegistry.get()
1420 |     if reg.avatar_face is None:
1421 |         logger.error("Cannot generate idle loop: no avatar loaded")
1422 |         return
1423 | 
1424 |     fps = DEFAULT_FPS
1425 |     duration = 4.0
1426 |     num_frames = int(duration * fps)
1427 | 
1428 |     base_frame = reg.avatar_face.copy()
1429 |     frames = [base_frame.copy() for _ in range(num_frames)]
1430 | 
1431 |     frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1432 | 
1433 |     video_path = frames_to_video(frames, fps, audio_path=None)
1434 |     if video_path:
1435 |         os.rename(video_path, ORACLE_IDLE_PATH)
1436 |         logger.info(f"Idle loop saved: {ORACLE_IDLE_PATH} ({num_frames} frames)")
1437 |     else:
1438 |         logger.error("Failed to generate idle loop")
1439 | 
1440 | 
1441 | def generate_thinking_loop():
1442 |     """Generate a 4-second thinking loop at cache/thinking_loop.mp4 (Phase 2: T1.4).
1443 |     Re-generate if missing or older than 7 days."""
1444 |     cache_dir = os.path.join(os.path.dirname(__file__), "cache")
1445 |     os.makedirs(cache_dir, exist_ok=True)
1446 | 
1447 |     if os.path.exists(ORACLE_THINKING_PATH):
1448 |         age_days = (time.time() - os.path.getmtime(ORACLE_THINKING_PATH)) / 86400
1449 |         if age_days < 7:
1450 |             logger.info(f"Thinking loop exists ({age_days:.1f}d old), skipping generation")
1451 |             return
1452 |         logger.info(f"Thinking loop is {age_days:.1f}d old, regenerating...")
1453 | 
1454 |     logger.info("Generating thinking loop video...")
1455 |     reg = ModelRegistry.get()
1456 |     if reg.avatar_face is None:
1457 |         logger.error("Cannot generate thinking loop: no avatar loaded")
1458 |         return
1459 | 
1460 |     fps = DEFAULT_FPS
1461 |     duration = 4.0
1462 |     num_frames = int(duration * fps)
1463 | 
1464 |     base_frame = reg.avatar_face.copy()
1465 |     frames = [base_frame.copy() for _ in range(num_frames)]
1466 |     frames = post_process_frames(frames, fps, enable_blinks=True, enable_head=True)
1467 | 
1468 |     video_path = frames_to_video(frames, fps, audio_path=None)
1469 |     if video_path:
1470 |         os.rename(video_path, ORACLE_THINKING_PATH)
1471 |         logger.info(f"Thinking loop saved: {ORACLE_THINKING_PATH} ({num_frames} frames)")
1472 |     else:
1473 |         logger.error("Failed to generate thinking loop")
1474 | 
1475 | 
1476 | # ═══════════════════════════════════════════════════════════════════════
1477 | # ORACLE PRE-CACHE + INTELLIGENCE ENDPOINTS
1478 | # ═══════════════════════════════════════════════════════════════════════
1479 | 
1480 | import oracle_cache_manager
1481 | import oracle_intelligence_feed
1482 | import oracle_dialogue_engine
1483 | 
1484 | # Intent classification — keyword matching
1485 | INTENT_PATTERNS = {
1486 |     "DAILY_BRIEF": r"brief|today|news|happening|what's|latest",
1487 |     "SOVEREIGNTY_INTRO": r"sovereign|score|free",
1488 |     "SOVEREIGNTY_COLD_WALLET": r"cold.?wallet|hardware|ledger|coldcard|custody",
1489 |     "SOVEREIGNTY_NODE": r"node|umbrel|raspberry|verify",
1490 |     "SOVEREIGNTY_BITAXE": r"bitaxe|mine|mining|solo",
1491 |     "SOVEREIGNTY_LIFE_INSURANCE": r"insurance|meanwhile|estate|death",
1492 |     "SOVEREIGNTY_RESIDENCY": r"residency|palau|rns|passport|citizenship",
1493 |     "GOODBYE": r"bye|goodbye|later|thanks",
1494 | }
1495 | 
1496 | 
1497 | def classify_intent(transcript):
1498 |     """Classify user transcript to an intent key. Returns (intent, confidence)."""
1499 |     text = transcript.lower().strip()
1500 |     for intent, pattern in INTENT_PATTERNS.items():
1501 |         if re.search(pattern, text):
1502 |             return intent, 0.85
1503 |     return "UNKNOWN", 0.4
1504 | 
1505 | 
1506 | @app.route("/oracle/cache/status")
1507 | def oracle_cache_status():
1508 |     """Return status of pre-cached responses and daily brief."""
1509 |     cache_status = oracle_cache_manager.get_cache_status()
1510 |     daily_brief = oracle_intelligence_feed.get_daily_brief()
1511 |     return jsonify({
1512 |         "cached_responses": cache_status,
1513 |         "daily_brief_ready": daily_brief is not None,
1514 |         "daily_brief_path": daily_brief,
1515 |         "cache_ttl_s": oracle_cache_manager.CACHE_TTL,
1516 |     })
1517 | 
1518 | 
1519 | @app.route("/oracle/response/<key>")
1520 | def oracle_response(key):
1521 |     """Serve pre-cached mp4 for a response key."""
1522 |     key = key.upper()
1523 |     if key not in oracle_cache_manager.RESPONSE_TREE and key != "DAILY_BRIEF_LIVE":
1524 |         return jsonify({"error": "Unknown response key", "valid_keys": list(oracle_cache_manager.RESPONSE_TREE.keys())}), 404
1525 | 
1526 |     # Daily brief special case
1527 |     if key == "DAILY_BRIEF_LIVE":
1528 |         path = oracle_intelligence_feed.get_daily_brief()
1529 |         if path:
1530 |             return send_file(path, mimetype="video/mp4")
1531 |         return jsonify({"error": "Daily brief not ready yet", "status": "pending"}), 202
1532 | 
1533 |     # Check if rendering
1534 |     if oracle_cache_manager.is_rendering(key):
1535 |         return jsonify({"error": "Response is being rendered", "status": "rendering"}), 202
1536 | 
1537 |     path = oracle_cache_manager.get_cached_response(key)
1538 |     if path:
1539 |         return send_file(path, mimetype="video/mp4")
1540 | 
1541 |     return jsonify({"error": "Response not cached yet", "status": "pending"}), 202
1542 | 
1543 | 
1544 | @app.route("/oracle/speak", methods=["POST"])
1545 | def oracle_speak():
1546 |     """Serve cached response for an intent, or fallback to /generate."""
1547 |     data = request.get_json()
1548 |     if not data or not data.get("intent"):
1549 |         return jsonify({"error": "intent required"}), 400
1550 | 
1551 |     intent = data["intent"].upper()
1552 | 
1553 |     # Try daily brief
1554 |     if intent == "DAILY_BRIEF":
1555 |         brief_path = oracle_intelligence_feed.get_daily_brief()
1556 |         if brief_path:
1557 |             return send_file(brief_path, mimetype="video/mp4")
1558 |         # Fallback to intro
1559 |         intent = "DAILY_BRIEF_INTRO"
1560 | 
1561 |     # If caller provided explicit text, use it directly (broadcast segments, custom scripts)
1562 |     caller_text = (data.get("text") or "").strip()
1563 |     if caller_text:
1564 |         return generate_inline(caller_text)
1565 | 
1566 |     # Try cached response
1567 |     path = oracle_cache_manager.get_cached_response(intent)
1568 |     if path:
1569 |         return send_file(path, mimetype="video/mp4")
1570 | 
1571 |     # Fallback: generate on the fly — but don't block if GPU is busy (cache warming)
1572 |     text = oracle_cache_manager.RESPONSE_TREE.get(intent)
1573 |     if not text:
1574 |         text = oracle_cache_manager.RESPONSE_TREE["UNKNOWN_QUESTION"]
1575 | 
1576 |     # Check GPU availability — thread-safe acquire then release before generate_inline re-acquires
1577 |     acquired = _render_semaphore.acquire(timeout=5)
1578 |     if not acquired:
1579 |         return jsonify({"error": "GPU busy warming cache — try again shortly",
1580 |                         "status": "warming", "retry_after": 30}), 503
1581 |     _render_semaphore.release()  # release immediately, generate_inline re-acquires
1582 | 
1583 |     return generate_inline(text)
1584 | 
1585 | 
1586 | def generate_inline(text):
1587 |     """Internal helper: generate a video from text and return it."""
1588 |     try:
1589 |         audio_bytes = _avatar_tts(text)
1590 |     except Exception as e:
1591 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1592 | 
1593 |     is_wav = audio_bytes[:4] == b"RIFF"
1594 |     ext = ".wav" if is_wav else ".mp3"
1595 |     with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1596 |         tmp.write(audio_bytes)
1597 |         audio_path = tmp.name
1598 | 
1599 |     wav_path = audio_path + "_16k.wav"
1600 |     if is_wav:
1601 |         import shutil
1602 |         shutil.copy2(audio_path, wav_path)
1603 |     else:
1604 |         subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1605 | 
1606 |     try:
1607 |         # Check queue state for concurrency visibility
1608 |         with _render_queue_lock:
1609 |             _queue_pos = _render_queue_count
1610 |         acquired = _render_semaphore.acquire(timeout=LOCK_TIMEOUT)
1611 |         if not acquired:
1612 |             return jsonify({"error": "GPU busy — try again in a moment", "retry_after": 10,
1613 |                             "queue_position": _queue_pos}), 503
1614 |         try:
1615 |             frames = wav2lip_generate(wav_path, DEFAULT_FPS)
1616 |             reg = ModelRegistry.get()
1617 |             try:
1618 |                 frames = sharpen_mouth_region(frames, reg.avatar_face_coords)
1619 |             except Exception as e:
1620 |                 logger.warning(f"[INLINE] Sharpening failed: {e}", exc_info=True)
1621 |             frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1622 |             video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1623 |         finally:
1624 |             _render_semaphore.release()
1625 | 
1626 |         if not video_path:
1627 |             return jsonify({"error": "Video encoding failed"}), 500
1628 | 
1629 |         # Stream video as inline (not attachment) so browser plays it directly.
1630 |         # Generator pattern ensures file stays on disk until fully sent,
1631 |         # then cleans up. Fixes iOS mid-stream cutoff + double-unlink race.
1632 |         def _stream_and_cleanup():
1633 |             try:
1634 |                 with open(video_path, "rb") as vf:
1635 |                     while True:
1636 |                         chunk = vf.read(65536)
1637 |                         if not chunk:
1638 |                             break
1639 |                         yield chunk
1640 |             finally:
1641 |                 for p in [audio_path, wav_path, video_path]:
1642 |                     try:
1643 |                         if p and os.path.exists(p):
1644 |                             os.unlink(p)
1645 |                     except OSError:
1646 |                         pass
1647 | 
1648 |         from flask import Response
1649 |         return Response(
1650 |             _stream_and_cleanup(),
1651 |             mimetype="video/mp4",
1652 |             headers={
1653 |                 "Content-Disposition": "inline",
1654 |                 "X-Accel-Buffering": "no",
1655 |                 "Cache-Control": "no-cache",
1656 |             },
1657 |         )
1658 | 
1659 |     except Exception as e:
1660 |         logger.error(f"generate_inline error: {e}", exc_info=True)
1661 |         for p in [audio_path, wav_path]:
1662 |             try:
1663 |                 if os.path.exists(p): os.unlink(p)
1664 |             except OSError:
1665 |                 pass
1666 |         return jsonify({"error": str(e)}), 500
1667 | 
1668 | 
1669 | 
1670 | 
1671 | 
1672 | 
1673 | @app.route("/oracle/voice", methods=["POST"])
1674 | def oracle_voice():
1675 |     """
1676 |     Voice-only endpoint: text -> ElevenLabs TTS -> audio/mpeg.
1677 |     No Wav2Lip, no GPU. ~400ms vs ~14s for full video.
1678 |     Use for vision guidance, quick confirmations, non-visual responses.
1679 |     Body: {"text": "...", "voice_id": "optional"}
1680 |     """
1681 |     data = request.get_json()
1682 |     if not data or not data.get("text"):
1683 |         return jsonify({"error": "text required"}), 400
1684 | 
1685 |     text = data["text"].strip()
1686 | 
1687 |     try:
1688 |         t0 = time.time()
1689 |         audio_bytes = _avatar_tts(text)
1690 |         logger.info(f"[VOICE] TTS {len(audio_bytes)}B in {time.time()-t0:.2f}s")
1691 |     except Exception as e:
1692 |         return jsonify({"error": f"TTS failed: {e}"}), 500
1693 | 
1694 |     # Loudnorm pass if not already normalized (WAV from Kokoro is already normalized in _avatar_tts,
1695 |     # but ElevenLabs MP3 fallback is not)
1696 |     is_wav = audio_bytes[:4] == b"RIFF"
1697 |     if not is_wav:
1698 |         try:
1699 |             with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as _tmp:
1700 |                 _tmp.write(audio_bytes)
1701 |                 _raw_path = _tmp.name
1702 |             _norm_path = _raw_path + "_norm.wav"
1703 |             _nr = subprocess.run(
1704 |                 ["ffmpeg", "-y", "-loglevel", "error", "-i", _raw_path,
1705 |                  "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
1706 |                  "-ar", "16000", "-ac", "1", _norm_path],
1707 |                 capture_output=True, text=True, timeout=30,
1708 |             )
1709 |             if _nr.returncode == 0 and os.path.exists(_norm_path) and os.path.getsize(_norm_path) > 1000:
1710 |                 with open(_norm_path, "rb") as _nf:
1711 |                     audio_bytes = _nf.read()
1712 |                 is_wav = True
1713 |             for _p in [_raw_path, _norm_path]:
1714 |                 try:
1715 |                     os.remove(_p)
1716 |                 except OSError:
1717 |                     pass
1718 |         except Exception as _ne:
1719 |             logger.warning(f"[VOICE] loudnorm failed (non-fatal): {_ne}")
1720 | 
1721 |     mime = "audio/wav" if is_wav else "audio/mpeg"
1722 | 
1723 |     from flask import Response
1724 |     return Response(
1725 |         audio_bytes,
1726 |         mimetype=mime,
1727 |         headers={
1728 |             "Content-Disposition": "inline",
1729 |             "Content-Length": str(len(audio_bytes)),
1730 |             "Cache-Control": "no-cache",
1731 |         },
1732 |     )
1733 | 
1734 | @app.route("/oracle/job/<job_id>")
1735 | def oracle_job_status(job_id):
1736 |     """Poll for async video render completion."""
1737 |     # Expire stale jobs (pending older than TTL, or completed older than 30s)
1738 |     now = time.time()
1739 |     with _render_jobs_lock:
1740 |         expired = []
1741 |         for k, v in _render_jobs.items():
1742 |             if v.get("completed_at"):
1743 |                 # Completed jobs: keep for 30s after completion
1744 |                 if now - v["completed_at"] > 30:
1745 |                     expired.append(k)
1746 |             elif now - v.get("created", 0) > _RENDER_JOB_TTL:
1747 |                 expired.append(k)
1748 |         for k in expired:
1749 |             del _render_jobs[k]
1750 |         job = _render_jobs.get(job_id)
1751 |     if not job:
1752 |         return jsonify({"status": "not_found"}), 404
1753 |     if job["status"] == "done":
1754 |         # Mark completed_at on first successful poll (keep job for 30s)
1755 |         if not job.get("completed_at"):
1756 |             with _render_jobs_lock:
1757 |                 if job_id in _render_jobs:
1758 |                     _render_jobs[job_id]["completed_at"] = time.time()
1759 |         video_bytes = job["video_bytes"]
1760 |         from flask import Response
1761 |         return Response(video_bytes, mimetype="video/mp4",
1762 |                         headers={"Content-Disposition": "inline", "Cache-Control": "no-cache"})
1763 |     if job["status"] == "error":
1764 |         # Mark completed_at for errors too
1765 |         if not job.get("completed_at"):
1766 |             with _render_jobs_lock:
1767 |                 if job_id in _render_jobs:
1768 |                     _render_jobs[job_id]["completed_at"] = time.time()
1769 |         return jsonify({"status": "error"}), 500
1770 |     return jsonify({"status": "pending"}), 202
1771 | 
1772 | 
1773 | @app.route("/oracle/job/<job_id>/audio")
1774 | def oracle_job_audio(job_id):
1775 |     """Return cached TTS audio from an async render job (avoids duplicate Kokoro call)."""
1776 |     with _render_jobs_lock:
1777 |         job = _render_jobs.get(job_id)
1778 |     if not job:
1779 |         return jsonify({"status": "not_found"}), 404
1780 |     if not job.get("audio_bytes"):
1781 |         # Audio not yet generated — tell client to poll again
1782 |         return jsonify({"status": "pending", "retry_after": 2}), 202
1783 |     audio_bytes = job["audio_bytes"]
1784 |     mime = job.get("audio_mime", "audio/wav")
1785 |     from flask import Response
1786 |     return Response(audio_bytes, mimetype=mime,
1787 |                     headers={"Content-Disposition": "inline",
1788 |                              "Content-Length": str(len(audio_bytes)),
1789 |                              "Cache-Control": "no-cache"})
1790 | 
1791 | 
1792 | @app.route("/oracle/job/<job_id>/stream")
1793 | def oracle_job_stream(job_id):
1794 |     """SSE stream for async render job status (Phase 2: T2.1).
1795 |     Pushes audio_ready, video_ready, or error events as they happen."""
1796 |     def generate():
1797 |         q = queue.Queue()
1798 |         with _job_events_lock:
1799 |             _job_events[job_id] = q
1800 |         try:
1801 |             # Check if job exists and its current state
1802 |             with _render_jobs_lock:
1803 |                 job = _render_jobs.get(job_id)
1804 |             if job is None:
1805 |                 yield f"event: error\ndata: not_found\n\n"
1806 |                 return
1807 |             if job.get("audio_bytes"):
1808 |                 yield f"event: audio_ready\ndata: {job_id}\n\n"
1809 |             if job.get("status") == "done":
1810 |                 yield f"event: video_ready\ndata: {job_id}\n\n"
1811 |                 return
1812 |             if job.get("status") == "error":
1813 |                 yield f"event: error\ndata: render_failed\n\n"
1814 |                 return
1815 | 
1816 |             # Wait for events from render_async (up to 60s)
1817 |             deadline = time.time() + 60
1818 |             while time.time() < deadline:
1819 |                 try:
1820 |                     evt = q.get(timeout=5)
1821 |                     yield f"event: {evt['type']}\ndata: {evt.get('data', job_id)}\n\n"
1822 |                     if evt["type"] in ("video_ready", "error"):
1823 |                         return
1824 |                 except queue.Empty:
1825 |                     # Keep-alive ping (SSE comment — not dispatched as event)
1826 |                     yield ": ping\n\n"
1827 |             yield "event: error\ndata: timeout\n\n"
1828 |         finally:
1829 |             with _job_events_lock:
1830 |                 _job_events.pop(job_id, None)
1831 | 
1832 |     from flask import Response
1833 |     return Response(generate(), mimetype="text/event-stream",
1834 |                     headers={"Cache-Control": "no-cache",
1835 |                              "X-Accel-Buffering": "no"})
1836 | 
1837 | 
1838 | @app.route("/oracle/chat", methods=["POST"])
1839 | def oracle_chat():
1840 |     data = request.get_json()
1841 |     if not data or not data.get("text"):
1842 |         return jsonify({"error": "text required"}), 400
1843 |     text = data["text"].strip()
1844 |     session_id = data.get("session_id", "anon")
1845 |     audio_first = data.get("audio_first", False)
1846 |     avatar_source = data.get("avatar_source", "default")
1847 |     if avatar_source not in AVATAR_SOURCES:
1848 |         avatar_source = "default"
1849 |     logger.info(f"[WAV2LIP] Using avatar source: {avatar_source}")
1850 | 
1851 |     # ── Phase 3: Visitor fingerprint + memory ──────────────────────────
1852 |     from oracle_memory import make_fingerprint, load_visitor
1853 |     visitor_token = data.get("visitor_token", "anon")
1854 |     raw_ip = (request.headers.get("X-Forwarded-For", "") or request.remote_addr or "").split(",")[0].strip()
1855 |     ua = request.headers.get("User-Agent", "")
1856 |     fingerprint = make_fingerprint(raw_ip, ua, visitor_token)
1857 | 
1858 |     session = oracle_dialogue_engine._get_session(session_id)
1859 |     if session["turn"] == 0:
1860 |         memory = load_visitor(fingerprint)
1861 |         if memory:
1862 |             session["visitor_memory"] = memory
1863 |             logger.info(f"[MEMORY] Returning visitor — session #{memory['session_count']}")
1864 |             if memory.get("recent_turns"):
1865 |                 # Pre-warm session with last exchange so Oracle has context immediately
1866 |                 recent = memory["recent_turns"]
1867 |                 if recent:
1868 |                     last = recent[-1]
1869 |                     if last.get("user") and last.get("oracle"):
1870 |                         session["history"] = [
1871 |                             {"role": "user", "content": f"[PRIOR SESSION] {last['user']}"},
1872 |                             {"role": "assistant", "content": f"[PRIOR SESSION] {last['oracle']}"},
1873 |                         ]
1874 |                         logger.info(f"[MEMORY] Pre-warmed session with {len(recent)} prior turns")
1875 |     session["fingerprint"] = fingerprint
1876 | 
1877 |     _sess_turn = oracle_dialogue_engine.get_session_info(session_id).get("turn", 0)
1878 |     if data.get("use_cache_for_intents", True) and _sess_turn == 0:
1879 |         intent, confidence = classify_intent(text)
1880 |         if confidence >= 0.8 and intent != "UNKNOWN":
1881 |             path = oracle_cache_manager.get_cached_response(intent)
1882 |             if path:
1883 |                 logger.info(f"[CHAT] Cache hit {intent}")
1884 |                 return send_file(path, mimetype="video/mp4")
1885 |     elif _sess_turn > 0:
1886 |         logger.info(f"[CHAT] Cache skipped turn={_sess_turn}")
1887 |     live_intel = {}
1888 |     try:
1889 |         live_intel = oracle_dialogue_engine.get_live_intel()
1890 |     except Exception:
1891 |         pass
1892 |     page_context = data.get("page_context", None)
1893 |     result = oracle_dialogue_engine.generate_response(session_id, text, live_intel, page_context)
1894 |     logger.info(f"[CHAT] {session_id} t={result['turn']} p={result['personality']} ctx={page_context.get('type','?') if page_context else 'none'}: {result['text'][:50]}")
1895 | 
1896 |     # ── Background memory save — persist after every turn, not just on unload ──
1897 |     try:
1898 |         _fp = session.get("fingerprint")
1899 |         _hist = session.get("history", [])
1900 |         if _fp and len(_hist) >= 2:
1901 |             import threading as _mem_threading
1902 |             def _bg_save():
1903 |                 try:
1904 |                     from oracle_memory import save_visitor
1905 |                     _flow = session.get("setup_flow", {})
1906 |                     _prev = session.get("visitor_memory", {})
1907 |                     # Store last 3 user+oracle pairs as recent_turns
1908 |                     _turns = []
1909 |                     for i in range(0, min(6, len(_hist)), 2):
1910 |                         if i+1 < len(_hist):
1911 |                             _turns.append({
1912 |                                 "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
1913 |                                 "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
1914 |                             })
1915 |                     save_visitor(_fp, {
1916 |                         "personality": session.get("personality", "AMIABLE"),
1917 |                         "session_summaries": _prev.get("session_summaries", []),
1918 |                         "setup_device": _flow.get("device"),
1919 |                         "setup_step": _flow.get("step", 0),
1920 |                         "topics_seen": list(session.get("topics_discussed", [])),
1921 |                         "products_shown": list(session.get("products_mentioned", [])),
1922 |                         "recent_turns": list(reversed(_turns)),
1923 |                     })
1924 |                 except Exception as _se:
1925 |                     logger.debug(f"[MEMORY] bg save error: {_se}")
1926 |             _mem_threading.Thread(target=_bg_save, daemon=True).start()
1927 |     except Exception:
1928 |         pass
1929 | 
1930 |     if audio_first:
1931 |         # Phase A: return text immediately, fire video render in background
1932 |         job_id = uuid.uuid4().hex[:16]
1933 |         with _render_jobs_lock:
1934 |             _render_jobs[job_id] = {"status": "pending", "video_bytes": None, "created": time.time()}
1935 | 
1936 |         response_text = result["text"]
1937 | 
1938 |         def render_async(txt, jid, src_name="default"):
1939 |             logger.info(f"[RENDER_ASYNC] STARTED job {jid} source={src_name} text={txt[:60]}...")
1940 |             try:
1941 |                 # Resolve avatar source for this render
1942 |                 a_face, a_coords, _a_eyes = _load_avatar_face(src_name)
1943 |                 if a_face is None or a_coords is None:
1944 |                     logger.warning(f"[ASYNC RENDER] Avatar source '{src_name}' failed, falling back to default")
1945 |                     a_face, a_coords, _a_eyes = _load_avatar_face("default")
1946 | 
1947 |                 def _sse_push(event_type, data=None):
1948 |                     """Push an event to any SSE listener for this job."""
1949 |                     with _job_events_lock:
1950 |                         q = _job_events.get(jid)
1951 |                     if q:
1952 |                         try:
1953 |                             q.put_nowait({"type": event_type, "data": data or jid})
1954 |                         except queue.Full:
1955 |                             pass
1956 | 
1957 |                 audio_bytes = _avatar_tts(txt)
1958 |                 # Cache audio in job dict so frontend can fetch it without calling Kokoro again
1959 |                 with _render_jobs_lock:
1960 |                     if jid in _render_jobs:
1961 |                         _render_jobs[jid]["audio_bytes"] = audio_bytes
1962 |                         _render_jobs[jid]["audio_mime"] = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"
1963 |                 _sse_push("audio_ready")
1964 |                 is_wav = audio_bytes[:4] == b"RIFF"
1965 |                 ext = ".wav" if is_wav else ".mp3"
1966 |                 with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
1967 |                     tmp.write(audio_bytes)
1968 |                     audio_path = tmp.name
1969 |                 wav_path = audio_path + "_16k.wav"
1970 |                 if is_wav:
1971 |                     import shutil
1972 |                     shutil.copy2(audio_path, wav_path)
1973 |                 else:
1974 |                     subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path], check=True, capture_output=True, timeout=30)
1975 |                 try:
1976 |                     acquired = _render_semaphore.acquire(timeout=60)
1977 |                     if not acquired:
1978 |                         logger.warning(f"[ASYNC RENDER] GPU busy for job {jid}")
1979 |                         with _render_jobs_lock:
1980 |                             if jid in _render_jobs:
1981 |                                 _render_jobs[jid] = {"status": "error", "video_bytes": None,
1982 |                                                      "created": time.time(), "code": "GPU_BUSY"}
1983 |                         _sse_push("error", "GPU_BUSY")
1984 |                         return
1985 |                     try:
1986 |                         frames = wav2lip_generate(wav_path, DEFAULT_FPS, avatar_face=a_face, avatar_face_coords=a_coords)
1987 |                         try:
1988 |                             frames = sharpen_mouth_region(frames, a_coords)
1989 |                         except Exception as e:
1990 |                             logger.warning(f"[ASYNC RENDER] Sharpening failed for job {jid}: {e}", exc_info=True)
1991 |                         frames = post_process_frames(frames, DEFAULT_FPS, enable_blinks=True, enable_head=True)
1992 |                         video_path = frames_to_video(frames, DEFAULT_FPS, audio_path=wav_path)
1993 |                     finally:
1994 |                         _render_semaphore.release()
1995 | 
1996 |                     if video_path and os.path.exists(video_path):
1997 |                         with open(video_path, "rb") as vf:
1998 |                             vbytes = vf.read()
1999 |                         os.unlink(video_path)
2000 |                         with _render_jobs_lock:
2001 |                             if jid in _render_jobs:
2002 |                                 _render_jobs[jid] = {"status": "done", "video_bytes": vbytes, "created": time.time()}
2003 |                         _sse_push("video_ready")
2004 |                     else:
2005 |                         with _render_jobs_lock:
2006 |                             if jid in _render_jobs:
2007 |                                 _render_jobs[jid]["status"] = "error"
2008 |                         _sse_push("error", "render_failed")
2009 |                 finally:
2010 |                     for p in [audio_path, wav_path]:
2011 |                         try:
2012 |                             if os.path.exists(p):
2013 |                                 os.unlink(p)
2014 |                         except OSError:
2015 |                             pass
2016 |             except Exception as e:
2017 |                 logger.error(f"[ASYNC RENDER] {e}")
2018 |                 with _render_jobs_lock:
2019 |                     if jid in _render_jobs:
2020 |                         _render_jobs[jid]["status"] = "error"
2021 |                 _sse_push("error", "render_failed")
2022 | 
2023 |         t = threading.Thread(target=render_async, args=(response_text, job_id, avatar_source), daemon=True)
2024 |         t.start()
2025 | 
2026 |         resp_data = {
2027 |             "text": response_text,
2028 |             "session_id": session_id,
2029 |             "job_id": job_id,
2030 |             "video_pending": True,
2031 |         }
2032 |         # Detect action card from user input (zero LLM cost)
2033 |         try:
2034 |             card = oracle_dialogue_engine.detect_action_card(text)
2035 |             if card:
2036 |                 resp_data["action_card"] = card
2037 |                 logger.info(f"[CHAT] Action card triggered: {card['id']}")
2038 |         except Exception as _card_err:
2039 |             logger.warning(f"[CHAT] Action card detection error: {_card_err}")
2040 |         return jsonify(resp_data)
2041 | 
2042 |     # Existing: return video directly
2043 |     return generate_inline(result["text"])
2044 | 
2045 | 
2046 | @app.route("/oracle/session", methods=["GET"])
2047 | def oracle_session_info():
2048 |     return jsonify(oracle_dialogue_engine.get_session_info(request.args.get("session_id","anon")))
2049 | 
2050 | 
2051 | @app.route("/oracle/session/reset", methods=["POST"])
2052 | def oracle_session_reset():
2053 |     data = request.get_json() or {}
2054 |     sid = data.get("session_id", "anon")
2055 | 
2056 |     # ── Phase 3: Save visitor memory before clearing session ───────────
2057 |     session = oracle_dialogue_engine._sessions.get(sid, {})
2058 |     fingerprint = session.get("fingerprint")
2059 |     if fingerprint and session.get("history"):
2060 |         try:
2061 |             from oracle_memory import save_visitor, generate_session_summary
2062 |             api_key = _get_anthropic_key()
2063 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
2064 |             flow = session.get("setup_flow", {})
2065 |             prev_memory = session.get("visitor_memory", {})
2066 |             # Build recent_turns from session history
2067 |             _hist = session.get("history", [])
2068 |             _turns = []
2069 |             for i in range(0, min(6, len(_hist)), 2):
2070 |                 if i+1 < len(_hist):
2071 |                     _turns.append({
2072 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
2073 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
2074 |                     })
2075 |             save_visitor(fingerprint, {
2076 |                 "personality": session.get("personality", "AMIABLE"),
2077 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
2078 |                 "setup_device": flow.get("device"),
2079 |                 "setup_step": flow.get("step", 0),
2080 |                 "topics_seen": session.get("topics_discussed", []),
2081 |                 "products_shown": session.get("products_mentioned", []),
2082 |                 "recent_turns": list(reversed(_turns)),
2083 |             })
2084 |             logger.info(f"[MEMORY] Saved visitor memory for session {sid}")
2085 |         except Exception as e:
2086 |             logger.warning(f"[MEMORY] Save failed on reset: {e}")
2087 | 
2088 |     oracle_dialogue_engine.reset_session(sid)
2089 |     return jsonify({"status": "reset"})
2090 | 
2091 | 
2092 | @app.route("/oracle/session/save", methods=["POST"])
2093 | def oracle_session_save():
2094 |     """Save session memory on page unload without clearing the session."""
2095 |     data = request.get_json() or {}
2096 |     sid = data.get("session_id", "anon")
2097 |     session = oracle_dialogue_engine._sessions.get(sid, {})
2098 |     fingerprint = session.get("fingerprint")
2099 |     if fingerprint and session.get("history"):
2100 |         try:
2101 |             from oracle_memory import save_visitor, generate_session_summary
2102 |             api_key = _get_anthropic_key()
2103 |             summary = generate_session_summary(session["history"], api_key) if api_key else ""
2104 |             flow = session.get("setup_flow", {})
2105 |             prev_memory = session.get("visitor_memory", {})
2106 |             topics = list(session.get("topics_discussed", []))
2107 |             # Build recent_turns from session history
2108 |             _hist = session.get("history", [])
2109 |             _turns = []
2110 |             for i in range(0, min(6, len(_hist)), 2):
2111 |                 if i+1 < len(_hist):
2112 |                     _turns.append({
2113 |                         "user": _hist[-(i+2)]["content"][:120] if len(_hist) > i+1 else "",
2114 |                         "oracle": _hist[-(i+1)]["content"][:200] if len(_hist) > i else ""
2115 |                     })
2116 |             save_visitor(fingerprint, {
2117 |                 "personality": session.get("personality", "AMIABLE"),
2118 |                 "session_summaries": prev_memory.get("session_summaries", []) + ([summary] if summary else []),
2119 |                 "setup_device": flow.get("device"),
2120 |                 "setup_step": flow.get("step", 0),
2121 |                 "topics_seen": topics,
2122 |                 "products_shown": session.get("products_mentioned", []),
2123 |                 "recent_turns": list(reversed(_turns)),
2124 |             })
2125 |             logger.info(f"[MEMORY] Saved session {sid} on unload — {len(topics)} topics, summary len={len(summary)}")
2126 |         except Exception as e:
2127 |             logger.warning(f"[MEMORY] Save on unload failed: {e}")
2128 |     return jsonify({"status": "saved"})
2129 | 
2130 | 
2131 | @app.route("/oracle/intent", methods=["POST"])
2132 | def oracle_intent():
2133 |     """Classify user transcript to an intent."""
2134 |     data = request.get_json()
2135 |     if not data or not data.get("transcript"):
2136 |         return jsonify({"error": "transcript required"}), 400
2137 | 
2138 |     intent, confidence = classify_intent(data["transcript"])
2139 | 
2140 |     # If low confidence, try Claude Haiku for better classification
2141 |     if confidence < 0.6:
2142 |         try:
2143 |             api_key = _get_anthropic_key()
2144 |             if api_key:
2145 |                 resp = http_requests.post(
2146 |                     "https://api.anthropic.com/v1/messages",
2147 |                     headers={
2148 |                         "x-api-key": api_key,
2149 |                         "anthropic-version": "2023-06-01",
2150 |                         "content-type": "application/json",
2151 |                     },
2152 |                     json={
2153 |                         "model": "claude-haiku-4-5-20251001",
2154 |                         "max_tokens": 30,
2155 |                         "messages": [{
2156 |                             "role": "user",
2157 |                             "content": (
2158 |                                 f"Classify this user message into ONE intent from this list: "
2159 |                                 f"{', '.join(INTENT_PATTERNS.keys())}, GREETING, UNKNOWN. "
2160 |                                 f"Reply with ONLY the intent name.\n\nMessage: {data['transcript']}"
2161 |                             ),
2162 |                         }],
2163 |                     },
2164 |                     timeout=10,
2165 |                 )
2166 |                 if resp.status_code == 200:
2167 |                     ai_intent = resp.json()["content"][0]["text"].strip().upper()
2168 |                     valid = set(INTENT_PATTERNS.keys()) | {"GREETING", "UNKNOWN", "SOVEREIGNTY_ASSESSMENT"}
2169 |                     if ai_intent in valid:
2170 |                         intent = ai_intent
2171 |                         confidence = 0.75
2172 |         except Exception as e:
2173 |             logger.warning(f"Intent AI fallback failed: {e}")
2174 | 
2175 |     return jsonify({
2176 |         "intent": intent,
2177 |         "confidence": round(confidence, 2),
2178 |         "cached": oracle_cache_manager.get_cached_response(intent) is not None,
2179 |     })
2180 | 
2181 | 
2182 | # ═══════════════════════════════════════════════════════════════════════
2183 | # SENTENCE CHUNKING FOR LONG TEXT
2184 | # ═══════════════════════════════════════════════════════════════════════
2185 | 
2186 | _chunk_sessions = {}
2187 | _chunk_lock = threading.Lock()
2188 | 
2189 | 
2190 | @app.route("/oracle/chunks/<session_id>")
2191 | def oracle_chunks(session_id):
2192 |     """Poll for additional chunks from a long-text generation."""
2193 |     session = _chunk_sessions.get(session_id)
2194 |     if not session:
2195 |         return jsonify({"error": "Session not found"}), 404
2196 | 
2197 |     return jsonify({
2198 |         "session_id": session_id,
2199 |         "chunks_ready": len(session["paths"]),
2200 |         "total_chunks": session["total"],
2201 |         "complete": session["complete"],
2202 |         "paths": [f"/oracle/chunks/{session_id}/{i}" for i in range(len(session["paths"]))],
2203 |     })
2204 | 
2205 | 
2206 | @app.route("/oracle/chunks/<session_id>/<int:idx>")
2207 | def oracle_chunk_file(session_id, idx):
2208 |     """Serve a specific chunk file."""
2209 |     session = _chunk_sessions.get(session_id)
2210 |     if not session or idx >= len(session["paths"]):
2211 |         return jsonify({"error": "Chunk not ready"}), 404
2212 |     return send_file(session["paths"][idx], mimetype="video/mp4")
2213 | 
2214 | 
2215 | # ═══════════════════════════════════════════════════════════════════════
2216 | # TTS PROVIDER STATUS
2217 | # ═══════════════════════════════════════════════════════════════════════
2218 | 
2219 | @app.route("/avatar/tts-provider", methods=["GET"])
2220 | def avatar_tts_provider():
2221 |     """Report which TTS provider is active."""
2222 |     if _AVATAR_KOKORO_READY:
2223 |         return jsonify({
2224 |             "provider": "kokoro",
2225 |             "voice": "af_heart",
2226 |             "backend": "cuda:1",
2227 |             "sample_rate": 24000,
2228 |             "ready": True,
2229 |         })
2230 |     return jsonify({
2231 |         "provider": "elevenlabs_fallback",
2232 |         "reason": "Kokoro not loaded or init failed",
2233 |         "ready": False,
2234 |     })
2235 | 
2236 | 
2237 | # ═══════════════════════════════════════════════════════════════════════
2238 | # MAIN
2239 | # ═══════════════════════════════════════════════════════════════════════
2240 | 
2241 | if __name__ == "__main__":
2242 |     print(f"\n{'='*60}")
2243 |     print("  ORACLE AVATAR SERVER v3 — Kokoro af_heart TTS + CV2 Sharpen + Blinks")
2244 |     print(f"  Port: {PORT}")
2245 |     print(f"  Device: {DEVICE}")
2246 |     print(f"  Avatar: {AVATAR_SOURCE}")
2247 |     print(f"  FPS: {DEFAULT_FPS}")
2248 |     print(f"  Encoding: CRF 23, preset ultrafast, 512px output")
2249 |     print(f"  Features: FP16, cv2_sharpen, mediapipe_blinks, head_movement")
2250 |     print(f"  Vision: {'enabled' if os.environ.get('GEMINI_API_KEY') else 'disabled'}")
2251 |     print(f"  Max audio: {MAX_AUDIO_SECONDS}s | Lock timeout: {LOCK_TIMEOUT}s")
2252 |     print(f"{'='*60}\n")
2253 | 
2254 |     # Load all models via registry (FP16 on GPU 1)
2255 |     logger.info("Initializing ModelRegistry...")
2256 |     reg = ModelRegistry.get()
2257 | 
2258 |     if reg.wav2lip_model is None:
2259 |         logger.error("Failed to load Wav2Lip model. Exiting.")
2260 |         sys.exit(1)
2261 | 
2262 |     if reg.avatar_face_coords is None:
2263 |         logger.error("No face detected in avatar. Exiting.")
2264 |         sys.exit(1)
2265 | 
2266 |     logger.info("Face enhancer: CV2 sharpen-only (no GFPGAN)")
2267 | 
2268 |     # Load Kokoro af_heart TTS on cuda:1 (~2-3s per utterance)
2269 |     logger.info("[STARTUP] Initializing Kokoro af_heart TTS on cuda:1...")
2270 |     _init_avatar_kokoro()
2271 | 
2272 |     # Auto-warmup (non-blocking — runs in background thread so Flask can start immediately)
2273 |     def _warmup_background():
2274 |         logger.info("[WARMUP] Running pipeline warmup in background...")
2275 |         warmup_start = time.time()
2276 |         try:
2277 |             import wave
2278 |             with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
2279 |                 with wave.open(tmp.name, "w") as wf:
2280 |                     wf.setnchannels(1)
2281 |                     wf.setsampwidth(2)
2282 |                     wf.setframerate(16000)
2283 |                     wf.writeframes(b"\x00\x00" * 8000)
2284 |                 warmup_wav = tmp.name
2285 |             frames = wav2lip_generate(warmup_wav, DEFAULT_FPS)
2286 |             if frames:
2287 |                 frames = post_process_frames(frames[:5], DEFAULT_FPS, enable_blinks=False, enable_head=True)
2288 |             os.unlink(warmup_wav)
2289 |             logger.info(
2290 |                 f"[WARMUP] Pipeline ready in {time.time()-warmup_start:.1f}s "
2291 |                 f"({len(frames)} frames)"
2292 |             )
2293 |         except Exception as e:
2294 |             logger.warning(f"[WARMUP] Failed (non-fatal): {e}")
2295 |     threading.Thread(target=_warmup_background, daemon=True).start()
2296 | 
2297 |     dev_idx = int(DEVICE.split(':')[1]) if ':' in DEVICE else 0
2298 |     logger.info(
2299 |         f"[WARMUP] GPU {dev_idx} VRAM: {torch.cuda.memory_allocated(dev_idx)/1024**3:.1f}GB used"
2300 |     )
2301 | 
2302 |     # Generate idle loop if not already present
2303 |     generate_idle_loop()
2304 | 
2305 |     # Phase 2 T1.4: Generate thinking loop if missing or stale
2306 |     generate_thinking_loop()
2307 | 
2308 |     # Phase 2: Start cache warming in background (delayed 60s to allow incoming requests)
2309 |     logger.info("[STARTUP] Oracle cache warmer will start in 60s...")
2310 |     def _delayed_warmup():
2311 |         time.sleep(60)
2312 |         logger.info("[STARTUP] Cache warmup starting now (60s delay complete)")
2313 |         oracle_cache_manager.warm_cache()
2314 |     threading.Thread(target=_delayed_warmup, daemon=True).start()
2315 |     oracle_cache_manager.start_background_warmer()
2316 | 
2317 |     # Phase 3: Start intelligence feed
2318 |     logger.info("[STARTUP] Starting intelligence feed...")
2319 |     oracle_intelligence_feed.start_intelligence_feed()
2320 | 
2321 |     logger.info(f"Avatar server v2 ready on port {PORT}")
2322 |     app.run(host="0.0.0.0", port=PORT, threaded=True)
2323 | 
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

