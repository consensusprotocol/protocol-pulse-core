# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: x-spaces-pipeline
# Branch: main
# Generated: 2026-03-18 18:11 UTC
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

### File: x_spaces_scraper/scraper.py (484 lines)
```
   1 | """
   2 | scraper.py — Find recent X Spaces from key Bitcoin accounts (last 7 days).
   3 | 
   4 | Detection order:
   5 |   1. Twitter API v2 (if TWITTER_BEARER_TOKEN set)
   6 |   2. Guest Token + GraphQL (no auth needed)
   7 |   3. yt-dlp metadata extraction (per-account fallback)
   8 | 
   9 | Unlike the live spaces_scraper, this targets *ended* Spaces with replays.
  10 | """
  11 | 
  12 | import json
  13 | import logging
  14 | import os
  15 | import re
  16 | import time
  17 | from dataclasses import asdict, dataclass, field
  18 | from datetime import datetime, timedelta, timezone
  19 | from pathlib import Path
  20 | from typing import Optional
  21 | 
  22 | import requests
  23 | 
  24 | logger = logging.getLogger(__name__)
  25 | 
  26 | # X public bearer (same as spaces_scraper)
  27 | X_PUBLIC_BEARER = (
  28 |     "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
  29 |     "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
  30 | )
  31 | 
  32 | TARGET_ACCOUNTS = [
  33 |     "saylor",
  34 |     "nvk",
  35 |     "giacomozucco",
  36 |     "dergigi",
  37 |     "natbrunell",
  38 |     "saifedean",
  39 |     "aantonop",
  40 |     "stacker_news",
  41 |     "BitcoinMagazine",
  42 |     # extras from the live scraper
  43 |     "thebitcoinlayer",
  44 |     "WhatBitcoinDid",
  45 |     "MartyBent",
  46 |     "gladstein",
  47 |     "LynAldenContact",
  48 | ]
  49 | 
  50 | SPACE_KEYWORDS = ["bitcoin", "btc", "lightning", "sats", "nostr"]
  51 | 
  52 | 
  53 | @dataclass
  54 | class SpaceInfo:
  55 |     """Metadata for a discovered X Space."""
  56 |     space_id: str
  57 |     title: str
  58 |     host: str
  59 |     date: str               # ISO format
  60 |     participant_count: int
  61 |     state: str               # "ended", "live", "scheduled"
  62 |     url: str
  63 |     replay_available: bool = False
  64 |     detected_via: str = "unknown"
  65 |     detected_at: float = field(default_factory=time.time)
  66 | 
  67 |     def to_dict(self):
  68 |         return asdict(self)
  69 | 
  70 | 
  71 | # ─── Twitter API v2 ─────────────────────────────────────────────────────────
  72 | 
  73 | class TwitterAPIv2Scraper:
  74 |     """Uses X API v2 to search for recent Spaces (requires elevated access)."""
  75 | 
  76 |     def __init__(self, bearer_token: str):
  77 |         self.bearer = bearer_token
  78 |         self.base = "https://api.twitter.com/2"
  79 |         self.session = requests.Session()
  80 |         self.session.headers["Authorization"] = f"Bearer {self.bearer}"
  81 | 
  82 |     def search_spaces(self, query: str = "bitcoin", state: str = "all") -> list[SpaceInfo]:
  83 |         try:
  84 |             r = self.session.get(
  85 |                 f"{self.base}/spaces/search",
  86 |                 params={
  87 |                     "query": query,
  88 |                     "state": state,
  89 |                     "space.fields": "id,title,host_ids,participant_count,started_at,state,ended_at",
  90 |                     "expansions": "host_ids",
  91 |                     "user.fields": "username",
  92 |                 },
  93 |                 timeout=15,
  94 |             )
  95 |             if r.status_code == 403:
  96 |                 logger.warning("Twitter API v2: 403 — token lacks Spaces access")
  97 |                 return []
  98 |             r.raise_for_status()
  99 |             data = r.json()
 100 | 
 101 |             spaces = data.get("data", [])
 102 |             users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}
 103 | 
 104 |             cutoff = datetime.now(timezone.utc) - timedelta(days=7)
 105 |             results = []
 106 |             for s in spaces:
 107 |                 started = s.get("started_at", "")
 108 |                 if started:
 109 |                     try:
 110 |                         dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
 111 |                         if dt < cutoff:
 112 |                             continue
 113 |                     except ValueError:
 114 |                         pass
 115 | 
 116 |                 host_id = (s.get("host_ids") or [""])[0]
 117 |                 results.append(SpaceInfo(
 118 |                     space_id=s["id"],
 119 |                     title=s.get("title", ""),
 120 |                     host=users.get(host_id, "unknown"),
 121 |                     date=started,
 122 |                     participant_count=s.get("participant_count", 0),
 123 |                     state=s.get("state", "ended").lower(),
 124 |                     url=f"https://twitter.com/i/spaces/{s['id']}",
 125 |                     replay_available=s.get("state", "").lower() == "ended",
 126 |                     detected_via="twitter_api_v2",
 127 |                 ))
 128 |             return results
 129 |         except Exception as e:
 130 |             logger.error(f"TwitterAPIv2 search error: {e}")
 131 |             return []
 132 | 
 133 |     def get_spaces_by_user(self, user_id: str) -> list[SpaceInfo]:
 134 |         """Get spaces created by a specific user."""
 135 |         try:
 136 |             r = self.session.get(
 137 |                 f"{self.base}/spaces/by/creator_ids",
 138 |                 params={
 139 |                     "user_ids": user_id,
 140 |                     "space.fields": "id,title,host_ids,participant_count,started_at,state,ended_at",
 141 |                     "expansions": "host_ids",
 142 |                     "user.fields": "username",
 143 |                 },
 144 |                 timeout=15,
 145 |             )
 146 |             if r.status_code != 200:
 147 |                 return []
 148 |             data = r.json()
 149 |             spaces = data.get("data", [])
 150 |             users = {u["id"]: u["username"] for u in data.get("includes", {}).get("users", [])}
 151 | 
 152 |             results = []
 153 |             for s in spaces:
 154 |                 host_id = (s.get("host_ids") or [""])[0]
 155 |                 results.append(SpaceInfo(
 156 |                     space_id=s["id"],
 157 |                     title=s.get("title", ""),
 158 |                     host=users.get(host_id, "unknown"),
 159 |                     date=s.get("started_at", ""),
 160 |                     participant_count=s.get("participant_count", 0),
 161 |                     state=s.get("state", "ended").lower(),
 162 |                     url=f"https://twitter.com/i/spaces/{s['id']}",
 163 |                     replay_available=s.get("state", "").lower() == "ended",
 164 |                     detected_via="twitter_api_v2",
 165 |                 ))
 166 |             return results
 167 |         except Exception as e:
 168 |             logger.debug(f"get_spaces_by_user error: {e}")
 169 |             return []
 170 | 
 171 | 
 172 | # ─── Guest Token + GraphQL ──────────────────────────────────────────────────
 173 | 
 174 | class GuestTokenScraper:
 175 |     """Uses guest authentication to find Spaces via GraphQL."""
 176 | 
 177 |     GRAPHQL_HEADERS = {
 178 |         "Authorization": f"Bearer {X_PUBLIC_BEARER}",
 179 |         "Content-Type": "application/json",
 180 |         "User-Agent": (
 181 |             "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
 182 |             "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
 183 |         ),
 184 |         "X-Twitter-Active-User": "yes",
 185 |         "X-Twitter-Client-Language": "en",
 186 |     }
 187 | 
 188 |     def __init__(self):
 189 |         self.session = requests.Session()
 190 |         self.session.headers.update(self.GRAPHQL_HEADERS)
 191 |         self.guest_token: Optional[str] = None
 192 |         self.token_time: float = 0
 193 | 
 194 |     def _refresh_token(self) -> bool:
 195 |         try:
 196 |             r = self.session.post(
 197 |                 "https://api.twitter.com/1.1/guest/activate.json",
 198 |                 timeout=10,
 199 |             )
 200 |             r.raise_for_status()
 201 |             self.guest_token = r.json()["guest_token"]
 202 |             self.token_time = time.time()
 203 |             self.session.headers["X-Guest-Token"] = self.guest_token
 204 |             logger.info(f"Guest token refreshed: {self.guest_token[:8]}...")
 205 |             return True
 206 |         except Exception as e:
 207 |             logger.error(f"Guest token refresh failed: {e}")
 208 |             return False
 209 | 
 210 |     def _ensure_token(self):
 211 |         if not self.guest_token or (time.time() - self.token_time) > 780:
 212 |             self._refresh_token()
 213 | 
 214 |     def search_spaces(self, keywords: list[str]) -> list[SpaceInfo]:
 215 |         """Search for Spaces (both live and ended) matching keywords."""
 216 |         self._ensure_token()
 217 |         results = []
 218 |         seen_ids = set()
 219 | 
 220 |         for keyword in keywords[:3]:
 221 |             try:
 222 |                 variables = json.dumps({
 223 |                     "query": f"{keyword} space",
 224 |                     "count": 20,
 225 |                     "product": "Top",
 226 |                 })
 227 |                 features = json.dumps({
 228 |                     "responsive_web_graphql_exclude_directive_enabled": True,
 229 |                     "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
 230 |                     "responsive_web_graphql_timeline_navigation_enabled": True,
 231 |                     "spaces_2022_h2_spaces_communities_enabled": True,
 232 |                     "spaces_2022_h2_clipping_enabled": True,
 233 |                 })
 234 |                 r = self.session.get(
 235 |                     "https://twitter.com/i/api/graphql/nK1dw4oV3k4w5TdtcAdSww/SearchTimeline",
 236 |                     params={"variables": variables, "features": features},
 237 |                     timeout=15,
 238 |                 )
 239 |                 if r.status_code != 200:
 240 |                     logger.debug(f"SearchTimeline {keyword}: HTTP {r.status_code}")
 241 |                     continue
 242 | 
 243 |                 data = r.json()
 244 |                 instructions = (
 245 |                     data.get("data", {})
 246 |                     .get("search_by_raw_query", {})
 247 |                     .get("search_timeline", {})
 248 |                     .get("timeline", {})
 249 |                     .get("instructions", [])
 250 |                 )
 251 |                 for instruction in instructions:
 252 |                     for entry in instruction.get("entries", []):
 253 |                         content = entry.get("content", {})
 254 |                         item_content = content.get("itemContent", {})
 255 | 
 256 |                         # Check for AudioSpace cards
 257 |                         space_result = item_content.get("audioSpace", {})
 258 |                         if not space_result:
 259 |                             # Also check tweet card bindings for Space links
 260 |                             tweet_result = item_content.get("tweet_results", {}).get("result", {})
 261 |                             card = tweet_result.get("card", {}).get("legacy", {})
 262 |                             binding_values = card.get("binding_values", [])
 263 |                             for bv in binding_values:
 264 |                                 if bv.get("key") == "card_url":
 265 |                                     url_val = bv.get("value", {}).get("string_value", "")
 266 |                                     space_match = re.search(r"/i/spaces/(\w+)", url_val)
 267 |                                     if space_match:
 268 |                                         sid = space_match.group(1)
 269 |                                         if sid not in seen_ids:
 270 |                                             seen_ids.add(sid)
 271 |                                             results.append(SpaceInfo(
 272 |                                                 space_id=sid,
 273 |                                                 title="(from tweet card)",
 274 |                                                 host="unknown",
 275 |                                                 date="",
 276 |                                                 participant_count=0,
 277 |                                                 state="unknown",
 278 |                                                 url=f"https://twitter.com/i/spaces/{sid}",
 279 |                                                 detected_via="guest_token_card",
 280 |                                             ))
 281 |                             continue
 282 | 
 283 |                         meta = space_result.get("metadata", {})
 284 |                         sid = meta.get("rest_id", "")
 285 |                         if not sid or sid in seen_ids:
 286 |                             continue
 287 |                         seen_ids.add(sid)
 288 | 
 289 |                         creator = (
 290 |                             meta.get("creator_results", {})
 291 |                             .get("result", {})
 292 |                             .get("legacy", {})
 293 |                             .get("screen_name", "unknown")
 294 |                         )
 295 |                         state = meta.get("state", "").lower()
 296 |                         results.append(SpaceInfo(
 297 |                             space_id=sid,
 298 |                             title=meta.get("title", ""),
 299 |                             host=creator,
 300 |                             date=meta.get("started_at", ""),
 301 |                             participant_count=meta.get("total_live_listeners", 0),
 302 |                             state="ended" if state in ("ended", "timedout") else state,
 303 |                             url=f"https://twitter.com/i/spaces/{sid}",
 304 |                             replay_available=state in ("ended", "timedout"),
 305 |                             detected_via="guest_token",
 306 |                         ))
 307 |             except Exception as e:
 308 |                 logger.debug(f"search_spaces({keyword}): {e}")
 309 | 
 310 |         return results
 311 | 
 312 |     def get_space_details(self, space_id: str) -> Optional[dict]:
 313 |         """Get detailed metadata for a specific Space."""
 314 |         self._ensure_token()
 315 |         try:
 316 |             variables = json.dumps({
 317 |                 "id": space_id,
 318 |                 "isMetatagsQuery": False,
 319 |                 "withReplays": True,
 320 |                 "withListeners": True,
 321 |             })
 322 |             r = self.session.get(
 323 |                 "https://twitter.com/i/api/graphql/xVEgTJ5D2lCMBDerNuMSIg/AudioSpaceById",
 324 |                 params={"variables": variables},
 325 |                 timeout=15,
 326 |             )
 327 |             if r.status_code != 200:
 328 |                 return None
 329 |             return r.json().get("data", {}).get("audioSpace", {})
 330 |         except Exception as e:
 331 |             logger.debug(f"get_space_details({space_id}): {e}")
 332 |             return None
 333 | 
 334 | 
 335 | # ─── yt-dlp metadata fallback ───────────────────────────────────────────────
 336 | 
 337 | def ytdlp_find_spaces(account: str) -> list[SpaceInfo]:
 338 |     """Use yt-dlp to check an account's Spaces (works for some ended Spaces)."""
 339 |     import subprocess
 340 |     results = []
 341 |     try:
 342 |         # yt-dlp can extract Space info from Twitter URLs
 343 |         proc = subprocess.run(
 344 |             [
 345 |                 "yt-dlp", "--flat-playlist", "--dump-json",
 346 |                 f"https://twitter.com/{account}/spaces",
 347 |             ],
 348 |             capture_output=True, text=True, timeout=30,
 349 |         )
 350 |         if proc.returncode != 0:
 351 |             return []
 352 |         for line in proc.stdout.strip().split("\n"):
 353 |             if not line:
 354 |                 continue
 355 |             try:
 356 |                 info = json.loads(line)
 357 |                 sid = info.get("id", "")
 358 |                 # Parse upload_date — yt-dlp returns YYYYMMDD format
 359 |                 raw = info.get("upload_date", "")
 360 |                 if raw:
 361 |                     if len(raw) == 8 and raw.isdigit():
 362 |                         dt = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
 363 |                         date_str = dt.isoformat()
 364 |                     else:
 365 |                         date_str = raw
 366 |                 else:
 367 |                     date_str = ""
 368 |                 results.append(SpaceInfo(
 369 |                     space_id=sid,
 370 |                     title=info.get("title", ""),
 371 |                     host=account,
 372 |                     date=date_str,
 373 |                     participant_count=0,
 374 |                     state="ended",
 375 |                     url=info.get("url", f"https://twitter.com/i/spaces/{sid}"),
 376 |                     replay_available=True,
 377 |                     detected_via="yt-dlp",
 378 |                 ))
 379 |             except json.JSONDecodeError:
 380 |                 continue
 381 |     except Exception as e:
 382 |         logger.debug(f"ytdlp_find_spaces({account}): {e}")
 383 |     return results
 384 | 
 385 | 
 386 | # ─── Unified scraper ────────────────────────────────────────────────────────
 387 | 
 388 | class XSpacesScraper:
 389 |     """
 390 |     Finds recent Bitcoin X Spaces from target accounts.
 391 |     Runs all sources (API v2, Guest Token, yt-dlp) and unions results.
 392 |     Processed-ID tracking backed by SpaceStateDB (injected_at column).
 393 |     """
 394 | 
 395 |     def __init__(self):
 396 |         from x_spaces_scraper.spaces_state import SpaceStateDB
 397 |         bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
 398 |         self.api_scraper = TwitterAPIv2Scraper(bearer) if bearer else None
 399 |         self.guest_scraper = GuestTokenScraper()
 400 |         self.cache_dir = Path(__file__).parent / "cache"
 401 |         self.cache_dir.mkdir(exist_ok=True)
 402 |         self.db = SpaceStateDB()
 403 | 
 404 |     def _load_processed(self) -> set[str]:
 405 |         """Load set of already-processed Space IDs from DB."""
 406 |         return self.db.get_injected_ids()
 407 | 
 408 |     def mark_processed(self, space_id: str):
 409 |         """Mark a space as injected/processed in the DB."""
 410 |         self.db.mark(space_id, "injected")
 411 | 
 412 |     def find_spaces(self, skip_processed: bool = True) -> list[SpaceInfo]:
 413 |         """
 414 |         Find recent Bitcoin X Spaces. Returns list of SpaceInfo,
 415 |         filtering out already-processed ones if skip_processed=True.
 416 |         Always runs all three sources and unions results (deduplicated by space_id).
 417 |         """
 418 |         processed = self._load_processed() if skip_processed else set()
 419 |         all_spaces: dict[str, SpaceInfo] = {}  # keyed by space_id for dedup
 420 | 
 421 |         # Source 1: Twitter API v2 (always run if available)
 422 |         if self.api_scraper:
 423 |             logger.info("Searching via Twitter API v2...")
 424 |             for kw in SPACE_KEYWORDS[:2]:
 425 |                 for space in self.api_scraper.search_spaces(kw, state="all"):
 426 |                     if space.space_id not in processed and space.space_id not in all_spaces:
 427 |                         all_spaces[space.space_id] = space
 428 | 
 429 |         # Source 2: Guest Token GraphQL (always run, even if API found results)
 430 |         logger.info("Searching via Guest Token GraphQL...")
 431 |         for space in self.guest_scraper.search_spaces(SPACE_KEYWORDS):
 432 |             if space.space_id not in processed and space.space_id not in all_spaces:
 433 |                 all_spaces[space.space_id] = space
 434 | 
 435 |         # Source 3: yt-dlp (always run for target accounts)
 436 |         logger.info("Trying yt-dlp metadata for target accounts...")
 437 |         for account in TARGET_ACCOUNTS:
 438 |             for space in ytdlp_find_spaces(account):
 439 |                 if space.space_id not in processed and space.space_id not in all_spaces:
 440 |                     all_spaces[space.space_id] = space
 441 | 
 442 |         # Filter to last 7 days — handle both ISO and YYYYMMDD formats
 443 |         cutoff = datetime.now(timezone.utc) - timedelta(days=7)
 444 |         recent = []
 445 |         for s in all_spaces.values():
 446 |             if s.date:
 447 |                 try:
 448 |                     raw = s.date
 449 |                     if len(raw) == 8 and raw.isdigit():
 450 |                         dt = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
 451 |                     else:
 452 |                         dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
 453 |                     if dt < cutoff:
 454 |                         continue
 455 |                 except (ValueError, TypeError) as e:
 456 |                     logger.warning(f"Cannot parse date for {s.space_id}: {s.date!r} — excluding")
 457 |                     continue  # EXCLUDE undatable spaces, never silently include them
 458 |             recent.append(s)
 459 | 
 460 |         logger.info(f"Found {len(recent)} spaces ({len(processed)} previously processed)")
 461 |         return recent
 462 | 
 463 | 
 464 | # ─── CLI ────────────────────────────────────────────────────────────────────
 465 | 
 466 | if __name__ == "__main__":
 467 |     from dotenv import load_dotenv
 468 |     load_dotenv(Path(__file__).parent.parent / ".env")
 469 | 
 470 |     logging.basicConfig(
 471 |         level=logging.INFO,
 472 |         format="%(asctime)s %(levelname)s %(name)s: %(message)s",
 473 |     )
 474 |     scraper = XSpacesScraper()
 475 |     spaces = scraper.find_spaces(skip_processed=False)
 476 |     if spaces:
 477 |         print(f"\nFound {len(spaces)} space(s):")
 478 |         for s in spaces:
 479 |             print(f"  [{s.detected_via}] @{s.host}: {s.title or '(no title)'}")
 480 |             print(f"    ID: {s.space_id} | State: {s.state} | Date: {s.date}")
 481 |             print(f"    URL: {s.url}")
 482 |     else:
 483 |         print("\nNo Bitcoin X Spaces found.")
 484 | 
```

### File: x_spaces_scraper/transcript_fetcher.py (366 lines)
```
   1 | """
   2 | transcript_fetcher.py — Transcript truth model for X Spaces.
   3 | 
   4 | Source truth labels enforced:
   5 |   AUDIO_REPLAY  = "audio_replay"    — yt-dlp download + Whisper
   6 |   LIVE_CAPTURE  = "live_capture"    — twspace-dl + rolling Whisper
   7 |   CONTEXT_ONLY  = "context_only"    — tweets/title only — NOT a real transcript
   8 | 
   9 | Quality gate: word_count >= 150, language_prob >= 0.70, repetition check.
  10 | Map-reduce summarization for transcripts > 2000 words.
  11 | """
  12 | 
  13 | import json
  14 | import logging
  15 | import os
  16 | import signal
  17 | import subprocess
  18 | import time
  19 | from pathlib import Path
  20 | 
  21 | from x_spaces_scraper.whisper_worker import WhisperWorker
  22 | from x_spaces_scraper.diarizer import diarize
  23 | from x_spaces_scraper.spaces_state import SpaceStateDB
  24 | 
  25 | logger = logging.getLogger(__name__)
  26 | 
  27 | CACHE_DIR = Path(__file__).parent / "cache"
  28 | CACHE_DIR.mkdir(exist_ok=True)
  29 | 
  30 | # Source truth constants
  31 | AUDIO_REPLAY = "audio_replay"
  32 | LIVE_CAPTURE = "live_capture"
  33 | CONTEXT_ONLY = "context_only"
  34 | 
  35 | # Quality thresholds
  36 | MIN_WORDS_FOR_AUDIO = 150
  37 | MIN_LANGUAGE_PROB = 0.70
  38 | MAX_REPETITION_RATE = 0.40
  39 | 
  40 | 
  41 | def _cache_path(space_id):
  42 |     return CACHE_DIR / f"transcript_{space_id}.json"
  43 | 
  44 | 
  45 | class TranscriptFetcher:
  46 |     def fetch(self, space_id, space_url, title="", db=None):
  47 |         """
  48 |         Returns:
  49 |         {
  50 |           "space_id": str,
  51 |           "transcript": str,
  52 |           "source": AUDIO_REPLAY | LIVE_CAPTURE | CONTEXT_ONLY,
  53 |           "word_count": int,
  54 |           "quality_score": float,  # 0.0-1.0
  55 |           "language_probability": float,
  56 |           "segments": list,        # diarized segments
  57 |           "speakers": list,        # unique speaker labels
  58 |           "usable": bool,          # True if meets quality threshold for narration
  59 |         }
  60 |         """
  61 |         # Check cache first
  62 |         cached = self._check_cache(space_id)
  63 |         if cached:
  64 |             return cached
  65 | 
  66 |         # Method 1: yt-dlp audio download + Whisper transcription
  67 |         result = self._try_audio_replay(space_id, space_url)
  68 |         if result.get("usable"):
  69 |             if db:
  70 |                 db.mark(space_id, "transcribed")
  71 |             self._save_cache(space_id, result)
  72 |             return result
  73 | 
  74 |         # Method 2: Twitter API tweets as context (NOT narration-grade)
  75 |         context = self._try_api_context(space_id)
  76 |         if context:
  77 |             result = {
  78 |                 "space_id": space_id,
  79 |                 "transcript": context,
  80 |                 "source": CONTEXT_ONLY,
  81 |                 "word_count": len(context.split()),
  82 |                 "quality_score": 0.3,
  83 |                 "language_probability": 1.0,
  84 |                 "segments": [],
  85 |                 "speakers": [],
  86 |                 "usable": False,
  87 |             }
  88 |             self._save_cache(space_id, result)
  89 |             return result
  90 | 
  91 |         # Final fallback: metadata only — cache as negative result to prevent re-attempts
  92 |         fallback_result = {
  93 |             "space_id": space_id,
  94 |             "transcript": f"X Space: {title}" if title else "",
  95 |             "source": CONTEXT_ONLY,
  96 |             "word_count": 0,
  97 |             "quality_score": 0.0,
  98 |             "language_probability": 0.0,
  99 |             "segments": [],
 100 |             "speakers": [],
 101 |             "usable": False,
 102 |             "cached_at": time.time(),
 103 |             "negative_cache": True,
 104 |         }
 105 |         self._save_cache(space_id, fallback_result)
 106 |         return fallback_result
 107 | 
 108 |     def _check_cache(self, space_id):
 109 |         path = _cache_path(space_id)
 110 |         if path.exists():
 111 |             try:
 112 |                 data = json.loads(path.read_text())
 113 |                 # Respect negative cache TTL (24h)
 114 |                 if data.get("negative_cache"):
 115 |                     age = time.time() - data.get("cached_at", 0)
 116 |                     if age < 86400:
 117 |                         logger.debug(f"Negative cache hit for {space_id} ({age/3600:.1f}h old)")
 118 |                         return data
 119 |                     else:
 120 |                         return None  # expired — retry
 121 |                 if data.get("transcript") or data.get("text"):
 122 |                     # Normalize old cache format
 123 |                     if "text" in data and "transcript" not in data:
 124 |                         data["transcript"] = data.pop("text")
 125 |                     if "usable" not in data:
 126 |                         data["usable"] = data.get("source") != CONTEXT_ONLY
 127 |                     logger.info(f"Cache hit for transcript {space_id}")
 128 |                     return data
 129 |             except (json.JSONDecodeError, OSError):
 130 |                 pass
 131 |         return None
 132 | 
 133 |     def _save_cache(self, space_id, result):
 134 |         try:
 135 |             _cache_path(space_id).write_text(json.dumps(result, indent=2))
 136 |         except OSError as e:
 137 |             logger.debug(f"Cache write failed: {e}")
 138 | 
 139 |     def _try_audio_replay(self, space_id, space_url):
 140 |         """Download audio + Whisper transcribe. Full pipeline."""
 141 |         import tempfile
 142 |         fd, audio_path = tempfile.mkstemp(prefix=f"space_{space_id}_", suffix=".m4a")
 143 |         os.close(fd)
 144 |         try:
 145 |             proc = subprocess.Popen(
 146 |                 ["yt-dlp", "-f", "bestaudio", "-o", audio_path,
 147 |                  space_url, "--no-warnings", "--quiet"],
 148 |                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
 149 |                 preexec_fn=os.setsid,
 150 |             )
 151 |             try:
 152 |                 proc.wait(timeout=120)
 153 |             except subprocess.TimeoutExpired:
 154 |                 try:
 155 |                     os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
 156 |                 except ProcessLookupError:
 157 |                     pass
 158 |                 return {"usable": False, "error": "yt-dlp timeout"}
 159 |             finally:
 160 |                 try:
 161 |                     if proc.poll() is None:  # only kill if still running
 162 |                         os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
 163 |                 except ProcessLookupError:
 164 |                     pass
 165 |             if proc.returncode != 0 or not os.path.exists(audio_path):
 166 |                 return {"usable": False}
 167 | 
 168 |             worker = WhisperWorker.get()
 169 |             result = worker.transcribe(audio_path)
 170 | 
 171 |             if not self._passes_quality_gate(result):
 172 |                 return {"usable": False}
 173 | 
 174 |             # Diarize segments
 175 |             result["segments"] = diarize(audio_path, result["segments"])
 176 |             result["speakers"] = list(set(s["speaker"] for s in result["segments"]))
 177 |             result["space_id"] = space_id
 178 |             result["usable"] = True
 179 |             result["quality_score"] = self._compute_quality_score(result)
 180 |             result["transcript"] = result.pop("text", "")
 181 | 
 182 |             # Map-reduce summarization for long transcripts
 183 |             if result["word_count"] > 2000:
 184 |                 result["full_transcript"] = result["transcript"]
 185 |                 result["transcript"] = self._map_reduce_summarize(
 186 |                     result["transcript"], result["segments"]
 187 |                 )
 188 | 
 189 |             return result
 190 |         except Exception as e:
 191 |             logger.error(f"_try_audio_replay({space_id}): {e}")
 192 |             return {"usable": False, "error": str(e)}
 193 |         finally:
 194 |             if os.path.exists(audio_path):
 195 |                 try:
 196 |                     os.remove(audio_path)
 197 |                 except OSError:
 198 |                     pass
 199 | 
 200 |     def _passes_quality_gate(self, result):
 201 |         """True if transcript meets all quality thresholds."""
 202 |         if result.get("word_count", 0) < MIN_WORDS_FOR_AUDIO:
 203 |             return False
 204 |         if result.get("language_probability", 0) < MIN_LANGUAGE_PROB:
 205 |             return False
 206 |         # Repetition check — bigram dedup rate
 207 |         text = result.get("text", "")
 208 |         words = text.lower().split()
 209 |         if len(words) > 50:
 210 |             bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
 211 |             unique_rate = len(set(bigrams)) / len(bigrams)
 212 |             if unique_rate < (1 - MAX_REPETITION_RATE):
 213 |                 return False
 214 |         return True
 215 | 
 216 |     def _compute_quality_score(self, result):
 217 |         """Compute 0.0-1.0 quality score from transcript metrics."""
 218 |         score = 0.0
 219 |         wc = result.get("word_count", 0)
 220 |         if wc >= 500:
 221 |             score += 0.4
 222 |         elif wc >= 150:
 223 |             score += 0.2
 224 |         lp = result.get("language_probability", 0)
 225 |         score += min(lp * 0.4, 0.4)
 226 |         if result.get("speakers") and len(result["speakers"]) > 1:
 227 |             score += 0.2
 228 |         return round(min(score, 1.0), 2)
 229 | 
 230 |     def _map_reduce_summarize(self, transcript, segments):
 231 |         """
 232 |         For transcripts > 2000 words: chunk -> Haiku summarize -> Sonnet synthesize.
 233 |         Preserves speaker attribution.
 234 |         """
 235 |         try:
 236 |             import anthropic
 237 |         except ImportError:
 238 |             logger.warning("anthropic not installed — skipping map-reduce")
 239 |             return transcript[:2000]
 240 | 
 241 |         api_key = os.environ.get("ANTHROPIC_API_KEY", "")
 242 |         if not api_key:
 243 |             logger.warning("ANTHROPIC_API_KEY not set — skipping map-reduce")
 244 |             return transcript[:2000]
 245 | 
 246 |         client = anthropic.Anthropic(api_key=api_key)
 247 | 
 248 |         # Split into ~600-word chunks
 249 |         words = transcript.split()
 250 |         chunk_size = 600
 251 |         chunks = []
 252 |         for i in range(0, len(words), chunk_size):
 253 |             chunks.append(" ".join(words[i:i + chunk_size]))
 254 | 
 255 |         # Map phase: Haiku summarizes each chunk
 256 |         chunk_summaries = []
 257 |         for i, chunk in enumerate(chunks):
 258 |             try:
 259 |                 resp = client.messages.create(
 260 |                     model="claude-haiku-4-5-20251001",
 261 |                     max_tokens=300,
 262 |                     messages=[{
 263 |                         "role": "user",
 264 |                         "content": (
 265 |                             f"Summarize this Bitcoin/crypto X Space segment in 2-3 sentences. "
 266 |                             f"Keep specific numbers, names, predictions, and strong opinions. "
 267 |                             f"Segment {i + 1}/{len(chunks)}:\n\n{chunk}"
 268 |                         ),
 269 |                     }],
 270 |                 )
 271 |                 chunk_summaries.append(resp.content[0].text)
 272 |             except Exception:
 273 |                 chunk_summaries.append(chunk[:200])
 274 | 
 275 |         # Reduce phase: Sonnet synthesizes chunk summaries
 276 |         try:
 277 |             all_summaries = "\n\n".join(
 278 |                 f"[Segment {i + 1}]: {s}" for i, s in enumerate(chunk_summaries)
 279 |             )
 280 |             resp = client.messages.create(
 281 |                 model="claude-sonnet-4-6",
 282 |                 max_tokens=600,
 283 |                 messages=[{
 284 |                     "role": "user",
 285 |                     "content": (
 286 |                         f"You are a Protocol Pulse Bitcoin intelligence editor. "
 287 |                         f"Synthesize these X Space segment summaries into a 3-4 sentence "
 288 |                         f"broadcast-ready intelligence briefing. "
 289 |                         f"Lead with the most impactful statement. "
 290 |                         f"Include specific claims, predictions, and speaker names.\n\n"
 291 |                         f"{all_summaries}"
 292 |                     ),
 293 |                 }],
 294 |             )
 295 |             return resp.content[0].text
 296 |         except Exception:
 297 |             return " ".join(chunk_summaries[:3])
 298 | 
 299 |     def _try_api_context(self, space_id):
 300 |         """Twitter API v2 — returns tweet text as CONTEXT ONLY. Never transcript."""
 301 |         import requests
 302 |         bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
 303 |         if not bearer:
 304 |             return ""
 305 |         try:
 306 |             r = requests.get(
 307 |                 f"https://api.twitter.com/2/spaces/{space_id}/tweets",
 308 |                 headers={"Authorization": f"Bearer {bearer}"},
 309 |                 params={"tweet.fields": "text,author_id,created_at"},
 310 |                 timeout=15,
 311 |             )
 312 |             if r.status_code == 200:
 313 |                 tweets = r.json().get("data", [])
 314 |                 return " ".join(t["text"] for t in tweets[:20])
 315 |         except Exception:
 316 |             pass
 317 |         return ""
 318 | 
 319 | 
 320 | # Backward-compatible function API (used by run_scraper.py)
 321 | _fetcher = None
 322 | 
 323 | 
 324 | def fetch_transcript(space_id, space_url, title="", db=None):
 325 |     """Backward-compatible wrapper around TranscriptFetcher."""
 326 |     global _fetcher
 327 |     if _fetcher is None:
 328 |         _fetcher = TranscriptFetcher()
 329 |     result = _fetcher.fetch(space_id, space_url, title=title, db=db)
 330 |     # Normalize for backward compat: ensure "text" key exists
 331 |     if "transcript" in result and "text" not in result:
 332 |         result["text"] = result["transcript"]
 333 |     return result
 334 | 
 335 | 
 336 | # CLI
 337 | if __name__ == "__main__":
 338 |     import re
 339 |     import sys
 340 |     logging.basicConfig(
 341 |         level=logging.INFO,
 342 |         format="%(asctime)s %(levelname)s %(name)s: %(message)s",
 343 |     )
 344 | 
 345 |     if len(sys.argv) < 2:
 346 |         print("Usage: python transcript_fetcher.py <space_url_or_id>")
 347 |         sys.exit(1)
 348 | 
 349 |     target = sys.argv[1]
 350 |     if target.startswith("http"):
 351 |         m = re.search(r"/spaces/(\w+)", target)
 352 |         sid = m.group(1) if m else target
 353 |         url = target
 354 |     else:
 355 |         sid = target
 356 |         url = f"https://twitter.com/i/spaces/{target}"
 357 | 
 358 |     result = fetch_transcript(sid, url)
 359 |     if result:
 360 |         text = result.get("transcript", result.get("text", ""))
 361 |         print(f"\nTranscript ({result.get('word_count', 0)} words, source={result.get('source', '?')}):")
 362 |         print(f"Usable: {result.get('usable', '?')}")
 363 |         print(text[:2000])
 364 |     else:
 365 |         print("Failed to fetch transcript.")
 366 | 
```

### File: x_spaces_scraper/whisper_worker.py (117 lines)
```
   1 | """
   2 | whisper_worker.py — Singleton GPU Whisper worker.
   3 | 
   4 | Loads model ONCE, keeps alive across calls. Never instantiate inside fetch functions.
   5 | Call WhisperWorker.get() always.
   6 | """
   7 | 
   8 | import logging
   9 | import threading
  10 | 
  11 | logger = logging.getLogger(__name__)
  12 | 
  13 | _init_lock = threading.Lock()
  14 | 
  15 | 
  16 | class WhisperWorker:
  17 |     _instance = None
  18 | 
  19 |     @classmethod
  20 |     def get(cls):
  21 |         if cls._instance is None:
  22 |             with _init_lock:
  23 |                 if cls._instance is None:  # double-checked locking
  24 |                     cls._instance = cls()
  25 |         return cls._instance
  26 | 
  27 |     def __init__(self):
  28 |         self.model = None
  29 |         self.model_name = None
  30 |         self._load_model()
  31 | 
  32 |     def _load_model(self):
  33 |         try:
  34 |             from faster_whisper import WhisperModel
  35 | 
  36 |             for model_name in ["distil-large-v3", "small.en", "base.en", "base"]:
  37 |                 try:
  38 |                     self.model = WhisperModel(
  39 |                         model_name,
  40 |                         device="cuda",
  41 |                         compute_type="float16",
  42 |                         num_workers=1,
  43 |                         cpu_threads=4,
  44 |                     )
  45 |                     self.model_name = model_name
  46 |                     logger.info(f"WhisperWorker loaded model: {model_name}")
  47 |                     break
  48 |                 except Exception as e:
  49 |                     logger.debug(f"WhisperWorker: {model_name} unavailable: {e}")
  50 |                     continue
  51 |         except ImportError:
  52 |             logger.warning("faster_whisper not installed — WhisperWorker unavailable")
  53 |             self.model = None
  54 |             self.model_name = None
  55 | 
  56 |     def transcribe(self, audio_path, language="en"):
  57 |         """
  58 |         Transcribe audio file. Returns:
  59 |         {
  60 |           "text": str,
  61 |           "segments": [{"start": float, "end": float, "text": str, "speaker": str}],
  62 |           "language": str,
  63 |           "language_probability": float,
  64 |           "word_count": int,
  65 |           "source": "audio_replay"
  66 |         }
  67 |         """
  68 |         if not self.model:
  69 |             return {
  70 |                 "text": "", "segments": [], "language": "en",
  71 |                 "language_probability": 0.0, "word_count": 0, "source": "unavailable",
  72 |             }
  73 | 
  74 |         try:
  75 |             segments_iter, info = self.model.transcribe(
  76 |                 audio_path,
  77 |                 beam_size=5,
  78 |                 language=language,
  79 |                 vad_filter=True,
  80 |                 vad_parameters={"min_silence_duration_ms": 500},
  81 |                 word_timestamps=False,
  82 |             )
  83 |             segments = []
  84 |             full_text_parts = []
  85 |             for seg in segments_iter:
  86 |                 segments.append({
  87 |                     "start": round(seg.start, 2),
  88 |                     "end": round(seg.end, 2),
  89 |                     "text": seg.text.strip(),
  90 |                     "speaker": "unknown",
  91 |                 })
  92 |                 full_text_parts.append(seg.text.strip())
  93 | 
  94 |             full_text = " ".join(full_text_parts)
  95 |             return {
  96 |                 "text": full_text,
  97 |                 "segments": segments,
  98 |                 "language": info.language,
  99 |                 "language_probability": round(info.language_probability, 3),
 100 |                 "word_count": len(full_text.split()),
 101 |                 "source": "audio_replay",
 102 |             }
 103 |         except Exception as e:
 104 |             logger.error(f"WhisperWorker.transcribe error: {e}")
 105 |             return {
 106 |                 "text": "", "segments": [], "language": "en",
 107 |                 "language_probability": 0.0, "word_count": 0,
 108 |                 "source": "error", "error": str(e),
 109 |             }
 110 | 
 111 |     def transcribe_live_chunk(self, audio_chunk_path, chunk_index, overlap_seconds=2.0):
 112 |         """30-second rolling window transcription for live Spaces."""
 113 |         result = self.transcribe(audio_chunk_path)
 114 |         result["source"] = "live_capture"
 115 |         result["chunk_index"] = chunk_index
 116 |         return result
 117 | 
```

### File: x_spaces_scraper/diarizer.py (90 lines)
```
   1 | """
   2 | diarizer.py — Speaker diarization for X Spaces transcripts.
   3 | 
   4 | Waterfall:
   5 |   1. pyannote-audio (if installed + HF token available)
   6 |   2. Energy-based heuristic (silence gaps = speaker change)
   7 |   3. All segments labeled "HOST" (graceful fallback)
   8 | """
   9 | 
  10 | import logging
  11 | 
  12 | logger = logging.getLogger(__name__)
  13 | 
  14 | 
  15 | def diarize(audio_path, segments, num_speakers=4):
  16 |     """
  17 |     Assign speaker labels to Whisper segments.
  18 |     Returns segments with "speaker" field updated:
  19 |       "HOST" for the primary speaker (most speaking time)
  20 |       "GUEST_1", "GUEST_2" etc for others
  21 |       "UNKNOWN" if diarization fails
  22 |     """
  23 |     if not segments:
  24 |         return segments
  25 | 
  26 |     # Method 1: pyannote
  27 |     try:
  28 |         import os
  29 |         hf_token = os.environ.get("HF_TOKEN", "")
  30 |         if hf_token:
  31 |             from pyannote.audio import Pipeline
  32 |             pipeline = Pipeline.from_pretrained(
  33 |                 "pyannote/speaker-diarization-3.1",
  34 |                 use_auth_token=hf_token,
  35 |             )
  36 |             diarization = pipeline(audio_path, num_speakers=num_speakers)
  37 |             for seg in segments:
  38 |                 mid = (seg["start"] + seg["end"]) / 2
  39 |                 for turn, _, label in diarization.itertracks(yield_label=True):
  40 |                     if turn.start <= mid <= turn.end:
  41 |                         seg["speaker"] = _normalize_label(label)
  42 |                         break
  43 |             logger.info("Diarization: pyannote success")
  44 |             return segments
  45 |     except Exception as e:
  46 |         logger.debug(f"pyannote diarization failed: {e}")
  47 | 
  48 |     # Method 2: Energy-based heuristic
  49 |     try:
  50 |         speaker_idx = 0
  51 |         prev_end = 0.0
  52 |         label_map = {}
  53 |         for seg in segments:
  54 |             if seg["start"] - prev_end > 1.5:
  55 |                 speaker_idx = (speaker_idx + 1) % num_speakers
  56 |             label = f"SPEAKER_{speaker_idx}"
  57 |             seg["speaker"] = label
  58 |             label_map[label] = label_map.get(label, 0) + len(seg["text"].split())
  59 |             prev_end = seg["end"]
  60 | 
  61 |         # Rename most-speaking speaker to HOST
  62 |         if label_map:
  63 |             host_label = max(label_map, key=label_map.get)
  64 |             for seg in segments:
  65 |                 if seg["speaker"] == host_label:
  66 |                     seg["speaker"] = "HOST"
  67 |                 elif seg["speaker"].startswith("SPEAKER_"):
  68 |                     n = seg["speaker"].split("_")[1]
  69 |                     seg["speaker"] = f"GUEST_{n}"
  70 |         logger.info("Diarization: energy-based heuristic applied")
  71 |         return segments
  72 |     except Exception as e:
  73 |         logger.debug(f"Energy-based diarization failed: {e}")
  74 | 
  75 |     # Fallback: all HOST
  76 |     for seg in segments:
  77 |         seg["speaker"] = "HOST"
  78 |     logger.info("Diarization: fallback — all segments labeled HOST")
  79 |     return segments
  80 | 
  81 | 
  82 | def _normalize_label(raw_label):
  83 |     mapping = {
  84 |         "SPEAKER_00": "HOST",
  85 |         "SPEAKER_01": "GUEST_1",
  86 |         "SPEAKER_02": "GUEST_2",
  87 |         "SPEAKER_03": "GUEST_3",
  88 |     }
  89 |     return mapping.get(raw_label, raw_label)
  90 | 
```

### File: x_spaces_scraper/spaces_state.py (142 lines)
```
   1 | """
   2 | spaces_state.py — SQLite-backed idempotent state machine for X Spaces.
   3 | 
   4 | States: discovered -> downloading -> transcribed -> summarized -> injected -> published
   5 | Each state is a timestamp column. NULL = not yet reached.
   6 | Prevents cron races. Atomic upsert via INSERT ... ON CONFLICT.
   7 | """
   8 | 
   9 | import os
  10 | import sqlite3
  11 | import threading
  12 | from datetime import datetime, timezone
  13 | 
  14 | STATE_ORDER = ["discovered", "downloaded", "transcribed", "summarized", "injected", "published"]
  15 | 
  16 | _ALL_COLUMNS = [
  17 |     "space_id", "title", "host", "url", "started_at", "ended_at",
  18 |     "transcript_source", "transcript_word_count", "transcript_quality_score",
  19 |     "impact_score", "discovered_at", "downloaded_at", "transcribed_at",
  20 |     "summarized_at", "injected_at", "published_at", "error",
  21 | ]
  22 | 
  23 | _SCHEMA = """
  24 | CREATE TABLE IF NOT EXISTS spaces (
  25 |     space_id TEXT PRIMARY KEY,
  26 |     title TEXT,
  27 |     host TEXT,
  28 |     url TEXT,
  29 |     started_at TEXT,
  30 |     ended_at TEXT,
  31 |     transcript_source TEXT,
  32 |     transcript_word_count INTEGER DEFAULT 0,
  33 |     transcript_quality_score REAL DEFAULT 0.0,
  34 |     impact_score INTEGER DEFAULT 0,
  35 |     discovered_at TEXT,
  36 |     downloaded_at TEXT,
  37 |     transcribed_at TEXT,
  38 |     summarized_at TEXT,
  39 |     injected_at TEXT,
  40 |     published_at TEXT,
  41 |     error TEXT,
  42 |     UNIQUE(space_id)
  43 | );
  44 | CREATE INDEX IF NOT EXISTS idx_spaces_discovered ON spaces(discovered_at);
  45 | CREATE INDEX IF NOT EXISTS idx_spaces_downloaded ON spaces(downloaded_at);
  46 | CREATE INDEX IF NOT EXISTS idx_spaces_transcribed ON spaces(transcribed_at);
  47 | CREATE INDEX IF NOT EXISTS idx_spaces_injected ON spaces(injected_at);
  48 | CREATE INDEX IF NOT EXISTS idx_spaces_error ON spaces(error);
  49 | """
  50 | 
  51 | from pathlib import Path as _Path
  52 | 
  53 | _BASE_DIR = _Path(os.environ.get("PP_BASE_DIR", _Path(__file__).parent.parent))
  54 | DEFAULT_DB_PATH = str(_BASE_DIR / "data" / "spaces_state.db")
  55 | 
  56 | 
  57 | class SpaceStateDB:
  58 |     def __init__(self, db_path=None):
  59 |         self.db_path = db_path or DEFAULT_DB_PATH
  60 |         os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
  61 |         self._lock = threading.Lock()
  62 |         self.conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
  63 |         self.conn.row_factory = sqlite3.Row
  64 |         self.conn.execute("PRAGMA journal_mode=WAL")
  65 |         self.conn.executescript(_SCHEMA)
  66 |         self.conn.commit()
  67 | 
  68 |     def upsert(self, space_id, **kwargs):
  69 |         """Atomic insert-or-update. COALESCE preserves existing non-null values."""
  70 |         kwargs["space_id"] = space_id
  71 |         values = [kwargs.get(col) for col in _ALL_COLUMNS]
  72 |         update_cols = _ALL_COLUMNS[1:]
  73 |         update_clause = ", ".join(
  74 |             f"{col} = COALESCE(excluded.{col}, spaces.{col})"
  75 |             for col in update_cols
  76 |         )
  77 |         placeholders = ", ".join("?" for _ in _ALL_COLUMNS)
  78 |         col_names = ", ".join(_ALL_COLUMNS)
  79 |         with self._lock:
  80 |             self.conn.execute(
  81 |                 f"INSERT INTO spaces ({col_names}) VALUES ({placeholders}) "
  82 |                 f"ON CONFLICT(space_id) DO UPDATE SET {update_clause}",
  83 |                 values,
  84 |             )
  85 |             self.conn.commit()
  86 | 
  87 |     def get(self, space_id):
  88 |         """Get a space record by ID. Returns dict or None."""
  89 |         row = self.conn.execute(
  90 |             "SELECT * FROM spaces WHERE space_id = ?", (space_id,)
  91 |         ).fetchone()
  92 |         if row is None:
  93 |             return None
  94 |         return dict(row)
  95 | 
  96 |     def get_pending(self, state):
  97 |         """Return spaces where {state}_at IS NULL and previous state IS NOT NULL.
  98 | 
  99 |         e.g. get_pending("transcribed") = downloaded but not yet transcribed.
 100 |         """
 101 |         state_col = f"{state}_at"
 102 |         idx = STATE_ORDER.index(state) if state in STATE_ORDER else -1
 103 |         if idx <= 0:
 104 |             # For "discovered" or unknown: return where discovered_at is set but state is not
 105 |             return self._query_pending(state_col, "discovered_at")
 106 | 
 107 |         prev_state = STATE_ORDER[idx - 1]
 108 |         prev_col = f"{prev_state}_at"
 109 |         return self._query_pending(state_col, prev_col)
 110 | 
 111 |     def _query_pending(self, state_col, prev_col):
 112 |         rows = self.conn.execute(
 113 |             f"SELECT * FROM spaces WHERE {state_col} IS NULL AND {prev_col} IS NOT NULL"
 114 |         ).fetchall()
 115 |         return [dict(r) for r in rows]
 116 | 
 117 |     def mark(self, space_id, state):
 118 |         """Set {state}_at = now() for the given space. Creates row if missing via upsert."""
 119 |         col = f"{state}_at"
 120 |         allowed = {"discovered", "downloaded", "transcribed", "summarized", "injected", "published"}
 121 |         if state not in allowed:
 122 |             raise ValueError(f"Unknown state: {state}")
 123 |         self.upsert(space_id, **{col: datetime.now(timezone.utc).isoformat()})
 124 | 
 125 |     def needs_processing(self, space_id, state):
 126 |         """Return True if space exists but hasn't reached this state yet."""
 127 |         record = self.get(space_id)
 128 |         if record is None:
 129 |             return False
 130 |         col = f"{state}_at"
 131 |         return record.get(col) is None
 132 | 
 133 |     def get_injected_ids(self):
 134 |         """Return set of space_ids where injected_at IS NOT NULL."""
 135 |         rows = self.conn.execute(
 136 |             "SELECT space_id FROM spaces WHERE injected_at IS NOT NULL"
 137 |         ).fetchall()
 138 |         return {r[0] for r in rows}
 139 | 
 140 |     def close(self):
 141 |         self.conn.close()
 142 | 
```

### File: x_spaces_scraper/run_scraper.py (245 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | run_scraper.py — X Spaces Scraper orchestrator for Protocol Pulse.
   4 | 
   5 | Pipeline: Find Spaces → Fetch Transcripts → Generate Articles → Publish
   6 | 
   7 | Usage:
   8 |     python3 run_scraper.py              # Full pipeline (publishes as drafts)
   9 |     python3 run_scraper.py --dry-run    # No publish, just log what it would do
  10 |     python3 run_scraper.py --publish    # Auto-publish (set published=True)
  11 | """
  12 | 
  13 | import argparse
  14 | import json
  15 | import logging
  16 | import sys
  17 | import time
  18 | from datetime import datetime
  19 | from pathlib import Path
  20 | 
  21 | # Add project root to path
  22 | PROJECT_ROOT = Path(__file__).parent.parent
  23 | sys.path.insert(0, str(PROJECT_ROOT))
  24 | 
  25 | from dotenv import load_dotenv
  26 | load_dotenv(PROJECT_ROOT / ".env")
  27 | 
  28 | from x_spaces_scraper.scraper import XSpacesScraper, SpaceInfo
  29 | from x_spaces_scraper.spaces_state import SpaceStateDB
  30 | from x_spaces_scraper.transcript_fetcher import fetch_transcript
  31 | from x_spaces_scraper.article_generator import generate_article
  32 | from x_spaces_scraper.pp_publisher import publish_article
  33 | 
  34 | # ─── Logging setup ──────────────────────────────────────────────────────────
  35 | 
  36 | LOG_DIR = PROJECT_ROOT / "logs"
  37 | LOG_DIR.mkdir(exist_ok=True)
  38 | LOG_FILE = LOG_DIR / "x_spaces_scraper.log"
  39 | 
  40 | 
  41 | def setup_logging(verbose: bool = False):
  42 |     level = logging.DEBUG if verbose else logging.INFO
  43 |     fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
  44 | 
  45 |     # File handler
  46 |     fh = logging.FileHandler(LOG_FILE, mode="a")
  47 |     fh.setLevel(logging.DEBUG)
  48 |     fh.setFormatter(logging.Formatter(fmt))
  49 | 
  50 |     # Console handler
  51 |     ch = logging.StreamHandler()
  52 |     ch.setLevel(level)
  53 |     ch.setFormatter(logging.Formatter(fmt))
  54 | 
  55 |     root = logging.getLogger()
  56 |     root.setLevel(logging.DEBUG)
  57 |     if not root.handlers:
  58 |         root.addHandler(fh)
  59 |         root.addHandler(ch)
  60 | 
  61 | 
  62 | logger = logging.getLogger("x_spaces_scraper")
  63 | 
  64 | 
  65 | # ─── Pipeline ───────────────────────────────────────────────────────────────
  66 | 
  67 | def run_pipeline(dry_run: bool = False, auto_publish: bool = False, max_spaces: int = 10):
  68 |     """Run the full X Spaces → articles pipeline."""
  69 |     start = time.time()
  70 |     logger.info("=" * 60)
  71 |     logger.info(f"X Spaces Scraper starting | dry_run={dry_run} | auto_publish={auto_publish}")
  72 |     logger.info("=" * 60)
  73 | 
  74 |     stats = {
  75 |         "spaces_found": 0,
  76 |         "transcripts_attempted": 0,
  77 |         "transcripts_fetched": 0,
  78 |         "articles_generated": 0,
  79 |         "articles_published": 0,
  80 |         "errors": [],
  81 |     }
  82 | 
  83 |     # ── Step 1: Find Spaces ──────────────────────────────────────────────
  84 |     logger.info("Step 1/4: Searching for Bitcoin X Spaces...")
  85 |     db = SpaceStateDB()
  86 |     scraper = XSpacesScraper()
  87 |     scraper.db = db  # share the same DB instance
  88 |     spaces = scraper.find_spaces(skip_processed=True)
  89 |     stats["spaces_found"] = len(spaces)
  90 | 
  91 |     if not spaces:
  92 |         logger.info("No new Spaces found. Pipeline complete.")
  93 |         _log_summary(stats, time.time() - start)
  94 |         return stats
  95 | 
  96 |     logger.info(f"Found {len(spaces)} new space(s)")
  97 |     for s in spaces:
  98 |         logger.info(f"  [{s.detected_via}] @{s.host}: {s.title or '(no title)'} ({s.state})")
  99 |         # Upsert discovered spaces into DB immediately
 100 |         db.upsert(s.space_id, title=s.title, host=s.host,
 101 |                   url=s.url, started_at=s.date,
 102 |                   discovered_at=datetime.utcnow().isoformat())
 103 | 
 104 |     # Limit to max_spaces
 105 |     spaces = spaces[:max_spaces]
 106 | 
 107 |     # ── Step 2: Fetch Transcripts ────────────────────────────────────────
 108 |     logger.info(f"\nStep 2/4: Fetching transcripts for {len(spaces)} space(s)...")
 109 |     transcripts = {}
 110 |     for space in spaces:
 111 |         if dry_run:
 112 |             logger.info(f"  [DRY RUN] Would fetch transcript for {space.space_id} (@{space.host})")
 113 |             continue
 114 | 
 115 |         stats["transcripts_attempted"] += 1
 116 |         transcript = fetch_transcript(space.space_id, space.url, db=db)
 117 |         if transcript:
 118 |             transcripts[space.space_id] = transcript
 119 |             if transcript.get("usable"):
 120 |                 stats["transcripts_fetched"] += 1
 121 |             logger.info(
 122 |                 f"  Transcript {'OK' if transcript.get('usable') else 'NOT USABLE'}: {space.space_id} — "
 123 |                 f"{transcript.get('word_count', 0)} words, "
 124 |                 f"{transcript.get('duration_s', 0)}s"
 125 |             )
 126 |         else:
 127 |             err = f"Transcript fetch failed for {space.space_id}"
 128 |             stats["errors"].append(err)
 129 |             logger.warning(f"  {err}")
 130 | 
 131 |     if dry_run:
 132 |         logger.info(f"[DRY RUN] Would attempt transcription for {len(spaces)} spaces")
 133 |         _log_summary(stats, time.time() - start)
 134 |         return stats
 135 | 
 136 |     if not transcripts:
 137 |         logger.warning("No transcripts fetched. Pipeline stopping.")
 138 |         _log_summary(stats, time.time() - start)
 139 |         return stats
 140 | 
 141 |     # ── Step 3: Generate Articles ────────────────────────────────────────
 142 |     logger.info(f"\nStep 3/4: Generating articles from {len(transcripts)} transcript(s)...")
 143 |     articles = {}
 144 |     for space in spaces:
 145 |         if space.space_id not in transcripts:
 146 |             continue
 147 | 
 148 |         transcript = transcripts[space.space_id]
 149 |         if not transcript.get("usable", False):
 150 |             source = transcript.get("source", "unknown")
 151 |             logger.warning(f"Skipping {space.space_id}: transcript not usable (source={source})")
 152 |             stats["errors"].append(f"Unusable transcript for {space.space_id} (source={source})")
 153 |             continue
 154 |         if transcript.get("word_count", 0) < 100:
 155 |             logger.warning(f"  Skipping {space.space_id}: transcript too short ({transcript.get('word_count', 0)} words)")
 156 |             continue
 157 | 
 158 |         meta = space.to_dict()
 159 |         article = generate_article(transcript, meta)
 160 |         if article:
 161 |             articles[space.space_id] = article
 162 |             stats["articles_generated"] += 1
 163 |             logger.info(f"  Article OK: \"{article.get('title', '?')}\"")
 164 |         else:
 165 |             err = f"Article generation failed for {space.space_id}"
 166 |             stats["errors"].append(err)
 167 |             logger.warning(f"  {err}")
 168 | 
 169 |     if not articles:
 170 |         logger.warning("No articles generated. Pipeline stopping.")
 171 |         _log_summary(stats, time.time() - start)
 172 |         return stats
 173 | 
 174 |     # ── Step 4: Publish ──────────────────────────────────────────────────
 175 |     logger.info(f"\nStep 4/4: Publishing {len(articles)} article(s)...")
 176 |     for space_id, article in articles.items():
 177 |         try:
 178 |             article_id = publish_article(article, auto_publish=auto_publish)
 179 |             if article_id:
 180 |                 stats["articles_published"] += 1
 181 |                 logger.info(f"  Published #{article_id}: \"{article.get('title', '?')}\"")
 182 |                 scraper.mark_processed(space_id)  # mark AFTER successful publish
 183 |             else:
 184 |                 err = f"Publish failed for {space_id}"
 185 |                 stats["errors"].append(err)
 186 |                 logger.warning(f"  {err}")
 187 |         except Exception as e:
 188 |             logger.error(f"Publish failed for {space_id}: {e}")
 189 |             stats["errors"].append(f"Publish exception for {space_id}: {e}")
 190 | 
 191 |     _log_summary(stats, time.time() - start)
 192 |     return stats
 193 | 
 194 | 
 195 | def _log_summary(stats: dict, elapsed: float):
 196 |     """Log final pipeline summary."""
 197 |     logger.info("\n" + "=" * 60)
 198 |     logger.info("PIPELINE SUMMARY")
 199 |     logger.info(f"  Spaces found:       {stats['spaces_found']}")
 200 |     logger.info(f"  Transcripts attempted: {stats.get('transcripts_attempted', 0)}")
 201 |     logger.info(f"  Transcripts usable: {stats['transcripts_fetched']}")
 202 |     logger.info(f"  Articles generated: {stats['articles_generated']}")
 203 |     logger.info(f"  Articles published: {stats['articles_published']}")
 204 |     logger.info(f"  Errors:             {len(stats['errors'])}")
 205 |     if stats["errors"]:
 206 |         for e in stats["errors"]:
 207 |             logger.info(f"    - {e}")
 208 |     logger.info(f"  Elapsed:            {elapsed:.1f}s")
 209 |     logger.info("=" * 60)
 210 | 
 211 |     # Write summary to JSON for monitoring
 212 |     summary_path = Path(__file__).parent / "cache" / "last_run.json"
 213 |     summary_path.parent.mkdir(parents=True, exist_ok=True)
 214 |     summary_path.write_text(json.dumps({
 215 |         **stats,
 216 |         "timestamp": datetime.utcnow().isoformat(),
 217 |         "elapsed_s": round(elapsed, 1),
 218 |     }, indent=2))
 219 | 
 220 | 
 221 | # ─── CLI ────────────────────────────────────────────────────────────────────
 222 | 
 223 | def main():
 224 |     parser = argparse.ArgumentParser(description="X Spaces Scraper for Protocol Pulse")
 225 |     parser.add_argument("--dry-run", action="store_true", help="Log what would happen without executing")
 226 |     parser.add_argument("--publish", action="store_true", help="Auto-publish articles (default: save as drafts)")
 227 |     parser.add_argument("--max-spaces", type=int, default=10, help="Max spaces to process per run")
 228 |     parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
 229 |     args = parser.parse_args()
 230 | 
 231 |     setup_logging(verbose=args.verbose)
 232 | 
 233 |     stats = run_pipeline(
 234 |         dry_run=args.dry_run,
 235 |         auto_publish=args.publish,
 236 |         max_spaces=args.max_spaces,
 237 |     )
 238 | 
 239 |     # Exit code: 0 if no errors, 1 if errors
 240 |     sys.exit(0 if not stats.get("errors") else 1)
 241 | 
 242 | 
 243 | if __name__ == "__main__":
 244 |     main()
 245 | 
```

### File: x_spaces_scraper/article_generator.py (182 lines)
```
   1 | """
   2 | article_generator.py — Generate Protocol Pulse articles from X Space transcripts.
   3 | 
   4 | Uses Claude API to produce 600-800 word Bitcoin-focused articles
   5 | with title, summary, key quotes, analysis, and tags.
   6 | """
   7 | 
   8 | import json
   9 | import logging
  10 | import os
  11 | from datetime import datetime
  12 | from pathlib import Path
  13 | from typing import Optional
  14 | 
  15 | import anthropic
  16 | 
  17 | logger = logging.getLogger(__name__)
  18 | 
  19 | ARTICLES_DIR = Path(__file__).parent / "articles"
  20 | ARTICLES_DIR.mkdir(exist_ok=True)
  21 | 
  22 | SYSTEM_PROMPT = """\
  23 | You are a senior journalist at Protocol Pulse, a Bitcoin-first media platform.
  24 | Your writing style is:
  25 | - Direct, informed, no-fluff — like a seasoned financial journalist
  26 | - Bitcoin-maximalist lens: evaluate everything through sound money principles
  27 | - Use "When" not "If" framing for Bitcoin adoption narratives
  28 | - Data-driven where possible, cite specific numbers from the transcript
  29 | - Never use clickbait or sensationalism — let the signal speak
  30 | - Professional tone, no emojis
  31 | 
  32 | Output format: JSON with these exact keys:
  33 | {
  34 |   "title": "Headline (max 100 chars, compelling but factual)",
  35 |   "summary": "2-3 sentence TL;DR for the article card",
  36 |   "content": "Full HTML article body, 600-800 words. Use <h2>, <p>, <blockquote> tags. Include 3-5 direct quotes from speakers wrapped in <blockquote>. End with analysis section.",
  37 |   "tags": ["tag1", "tag2", ...],
  38 |   "key_quotes": ["quote1 — Speaker", "quote2 — Speaker", ...],
  39 |   "seo_title": "SEO-optimized title (max 60 chars)",
  40 |   "seo_description": "Meta description (max 155 chars)"
  41 | }
  42 | 
  43 | Rules:
  44 | - Title should reference the Space topic, not generic "Bitcoin discussion"
  45 | - Include speaker attribution for all quotes
  46 | - Tags: always include "bitcoin" and "x-spaces", plus 2-3 topic-specific tags
  47 | - Content must be valid HTML (no markdown)
  48 | - Analysis section should connect the discussion to broader Bitcoin narratives
  49 | - If transcript is mostly noise/short, still produce a concise article but note limited content
  50 | """
  51 | 
  52 | 
  53 | def generate_article(
  54 |     transcript: dict,
  55 |     space_meta: dict,
  56 |     model: str = "claude-sonnet-4-6",
  57 | ) -> Optional[dict]:
  58 |     """
  59 |     Generate a PP-style article from a Space transcript.
  60 | 
  61 |     Args:
  62 |         transcript: dict with "text", "word_count", "duration_s", etc.
  63 |         space_meta: dict with "space_id", "title", "host", "date", "participant_count"
  64 |         model: Claude model to use
  65 | 
  66 |     Returns:
  67 |         Article dict ready for publishing, or None on failure.
  68 |     """
  69 |     api_key = os.environ.get("ANTHROPIC_API_KEY")
  70 |     if not api_key:
  71 |         logger.error("ANTHROPIC_API_KEY not set")
  72 |         return None
  73 | 
  74 |     client = anthropic.Anthropic(api_key=api_key)
  75 | 
  76 |     # Truncate very long transcripts to stay within context
  77 |     text = transcript.get("transcript") or transcript.get("text", "")
  78 |     if len(text) > 50000:
  79 |         text = text[:50000] + "\n\n[... transcript truncated for length]"
  80 | 
  81 |     user_prompt = f"""Generate a Protocol Pulse article from this X Space transcript.
  82 | 
  83 | SPACE METADATA:
  84 | - Title: {space_meta.get('title', 'Untitled Space')}
  85 | - Host: @{space_meta.get('host', 'unknown')}
  86 | - Date: {space_meta.get('date', 'unknown')}
  87 | - Participants: {space_meta.get('participant_count', 'unknown')}
  88 | - Duration: {transcript.get('duration_s', 'unknown')} seconds
  89 | - Word count: {transcript.get('word_count', 0)} words
  90 | 
  91 | TRANSCRIPT:
  92 | {text}
  93 | 
  94 | Generate the article as JSON. Remember: 600-800 words, Bitcoin-first angle, 3-5 direct quotes."""
  95 | 
  96 |     try:
  97 |         logger.info(f"Generating article for Space '{space_meta.get('title', space_meta.get('space_id'))}'...")
  98 |         response = client.messages.create(
  99 |             model=model,
 100 |             max_tokens=4096,
 101 |             system=SYSTEM_PROMPT,
 102 |             messages=[{"role": "user", "content": user_prompt}],
 103 |         )
 104 | 
 105 |         raw = response.content[0].text.strip()
 106 | 
 107 |         # Extract JSON from response (handle markdown code blocks)
 108 |         if raw.startswith("```"):
 109 |             raw = raw.split("\n", 1)[1]
 110 |             if raw.endswith("```"):
 111 |                 raw = raw[:-3]
 112 | 
 113 |         article = json.loads(raw)
 114 | 
 115 |         # Enrich with metadata
 116 |         article["space_id"] = space_meta.get("space_id", "")
 117 |         article["space_url"] = space_meta.get("url", f"https://twitter.com/i/spaces/{space_meta.get('space_id', '')}")
 118 |         article["space_host"] = space_meta.get("host", "unknown")
 119 |         article["space_date"] = space_meta.get("date", "")
 120 |         article["space_participants"] = space_meta.get("participant_count", 0)
 121 |         article["generated_at"] = datetime.utcnow().isoformat()
 122 |         article["source_type"] = "x_spaces"
 123 |         article["transcript_words"] = transcript.get("word_count", 0)
 124 | 
 125 |         # Save to articles dir
 126 |         filename = f"article_{space_meta.get('space_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
 127 |         out_path = ARTICLES_DIR / filename
 128 |         out_path.write_text(json.dumps(article, indent=2))
 129 |         logger.info(f"Article saved: {out_path}")
 130 | 
 131 |         return article
 132 | 
 133 |     except json.JSONDecodeError as e:
 134 |         logger.error(f"Claude returned invalid JSON: {e}")
 135 |         logger.debug(f"Raw response: {raw[:500]}")
 136 |         return None
 137 |     except anthropic.APIError as e:
 138 |         logger.error(f"Claude API error: {e}")
 139 |         return None
 140 |     except Exception as e:
 141 |         logger.error(f"generate_article error: {e}")
 142 |         return None
 143 | 
 144 | 
 145 | # ─── CLI ────────────────────────────────────────────────────────────────────
 146 | 
 147 | if __name__ == "__main__":
 148 |     import sys
 149 |     from dotenv import load_dotenv
 150 |     load_dotenv(Path(__file__).parent.parent / ".env")
 151 | 
 152 |     logging.basicConfig(
 153 |         level=logging.INFO,
 154 |         format="%(asctime)s %(levelname)s %(name)s: %(message)s",
 155 |     )
 156 | 
 157 |     if len(sys.argv) < 2:
 158 |         print("Usage: python article_generator.py <transcript_cache_file.json>")
 159 |         sys.exit(1)
 160 | 
 161 |     transcript_file = Path(sys.argv[1])
 162 |     if not transcript_file.exists():
 163 |         print(f"File not found: {transcript_file}")
 164 |         sys.exit(1)
 165 | 
 166 |     transcript = json.loads(transcript_file.read_text())
 167 |     meta = {
 168 |         "space_id": transcript.get("space_id", "test"),
 169 |         "title": "Test Space",
 170 |         "host": "test_user",
 171 |         "date": datetime.utcnow().isoformat(),
 172 |         "participant_count": 100,
 173 |         "url": f"https://twitter.com/i/spaces/{transcript.get('space_id', 'test')}",
 174 |     }
 175 |     article = generate_article(transcript, meta)
 176 |     if article:
 177 |         print(f"\nGenerated: {article['title']}")
 178 |         print(f"Tags: {article.get('tags', [])}")
 179 |         print(f"Summary: {article.get('summary', '')}")
 180 |     else:
 181 |         print("Article generation failed.")
 182 | 
```

### File: x_spaces_pipeline/monitor.py (90 lines)
```
   1 | """
   2 | TOMBSTONED 2026-03-18
   3 | This file is part of the deprecated x_spaces_pipeline/ live-capture system.
   4 | It has been superseded by x_spaces_scraper/run_scraper.py which is the
   5 | single authoritative pipeline. SpaceStateDB is the authoritative state store.
   6 | DO NOT USE — DO NOT IMPORT — DO NOT EXECUTE
   7 | Live capture capability will be reintegrated as a clean stage in run_scraper.py.
   8 | """
   9 | #!/usr/bin/env python3
  10 | """x_spaces_pipeline/monitor.py"""
  11 | import os, re, subprocess, sys, time, logging
  12 | from datetime import datetime, timezone
  13 | from pathlib import Path
  14 | sys.path.insert(0, "/home/ultron/protocol_pulse")
  15 | from x_spaces_scraper.spaces_state import SpaceStateDB
  16 | logger = logging.getLogger("spaces.monitor")
  17 | LOCK_DIR = Path("/tmp/pp_spaces_locks")
  18 | RAW_DIR  = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
  19 | COOKIE   = "/home/ultron/protocol_pulse/video_pipeline_v3/data/yt_cookies.txt"
  20 | PIPELINE = Path("/home/ultron/protocol_pulse/x_spaces_pipeline")
  21 | STALE_LOCK_AGE = 18000
  22 | MONITORED_HANDLES = [
  23 |     "saylor","LynAldenContact","PrestonPysh","Breedlove22","ODELL",
  24 |     "MartyBent","natbrunell","PeterMcCormack","lopp","saifedean",
  25 |     "JeffBooth","CaitlinLong_","coryklippsten","Dennis_Porter_",
  26 |     "americanhodl8","woonomic","jack","adam3us","nvk","giacomozucco",
  27 |     "dergigi","pierre_rochard","jimmysong","Excellion","nic__carter",
  28 |     "100trillionUSD","aantonop","APompliano","knutsvanholm","TheGuySwann",
  29 | ]
  30 | def acquire_lock(handle):
  31 |     LOCK_DIR.mkdir(exist_ok=True)
  32 |     lp = LOCK_DIR / f"{handle}.lock"
  33 |     if lp.exists():
  34 |         if time.time() - lp.stat().st_mtime > STALE_LOCK_AGE:
  35 |             lp.unlink(missing_ok=True)
  36 |         else:
  37 |             return None
  38 |     try:
  39 |         fd = os.open(str(lp), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
  40 |         os.write(fd, str(os.getpid()).encode())
  41 |         return fd
  42 |     except FileExistsError:
  43 |         return None
  44 | def release_lock(handle, fd):
  45 |     try: os.close(fd)
  46 |     except OSError: pass
  47 |     (LOCK_DIR / f"{handle}.lock").unlink(missing_ok=True)
  48 | def _extract_space_id(url, handle, prefix="live"):
  49 |     """Extract canonical space ID from m3u8 URL or fall back to timestamped ID."""
  50 |     space_id_match = re.search(r'/([A-Za-z0-9]{13,})/', url)
  51 |     if space_id_match:
  52 |         return f"{prefix}_{space_id_match.group(1)}"
  53 |     return f"{prefix}_{handle}_{int(time.time())}"
  54 | 
  55 | def is_space_live(handle):
  56 |     try:
  57 |         res = subprocess.run(["twspace_dl","-i",f"https://twitter.com/{handle}","--cookies",COOKIE,"--metadata"],capture_output=True,text=True,timeout=30)
  58 |         if res.returncode == 0:
  59 |             for line in res.stdout.splitlines():
  60 |                 if "m3u8" in line:
  61 |                     url = line.strip()
  62 |                     return {"handle":handle,"url":url,"space_id":_extract_space_id(url, handle, "live"),"detected_at":time.time()}
  63 |     except subprocess.TimeoutExpired: logger.warning(f"twspace_dl timeout @{handle}")
  64 |     except Exception as e: logger.debug(f"@{handle}: {e}")
  65 |     try:
  66 |         res = subprocess.run(["yt-dlp","--cookies",COOKIE,"--get-url","--no-playlist",f"https://twitter.com/{handle}"],capture_output=True,text=True,timeout=30)
  67 |         if res.returncode==0 and "m3u8" in res.stdout:
  68 |             url = res.stdout.strip().splitlines()[0]
  69 |             return {"handle":handle,"url":url,"space_id":_extract_space_id(url, handle, "replay"),"detected_at":time.time()}
  70 |     except Exception: pass
  71 |     return None
  72 | def run_monitor():
  73 |     db = SpaceStateDB()
  74 |     RAW_DIR.mkdir(parents=True, exist_ok=True)
  75 |     for handle in MONITORED_HANDLES:
  76 |         fd = acquire_lock(handle)
  77 |         if fd is None: continue
  78 |         space = is_space_live(handle)
  79 |         if space:
  80 |             if db.get(space["space_id"]):
  81 |                 release_lock(handle, fd); continue
  82 |             db.upsert(space["space_id"],title=f"Space @{handle}",host=handle,url=space["url"],discovered_at=datetime.now(timezone.utc).isoformat())
  83 |             subprocess.Popen(["python3",str(PIPELINE/"recorder.py"),"--handle",handle,"--url",space["url"],"--space-id",space["space_id"],"--lock-fd",str(fd)],start_new_session=True,close_fds=False,pass_fds=(fd,))
  84 |             logger.info(f"Spawned recorder @{handle}")
  85 |         else:
  86 |             release_lock(handle, fd)
  87 | if __name__ == "__main__":
  88 |     logging.basicConfig(level=logging.INFO)
  89 |     run_monitor()
  90 | 
```

### File: x_spaces_pipeline/recorder.py (65 lines)
```
   1 | """
   2 | TOMBSTONED 2026-03-18
   3 | This file is part of the deprecated x_spaces_pipeline/ live-capture system.
   4 | It has been superseded by x_spaces_scraper/run_scraper.py which is the
   5 | single authoritative pipeline. SpaceStateDB is the authoritative state store.
   6 | DO NOT USE — DO NOT IMPORT — DO NOT EXECUTE
   7 | Live capture capability will be reintegrated as a clean stage in run_scraper.py.
   8 | """
   9 | #!/usr/bin/env python3
  10 | """x_spaces_pipeline/recorder.py"""
  11 | import argparse, json, logging, os, signal, subprocess, sys
  12 | from datetime import datetime
  13 | from pathlib import Path
  14 | sys.path.insert(0, "/home/ultron/protocol_pulse")
  15 | from x_spaces_scraper.spaces_state import SpaceStateDB
  16 | logger = logging.getLogger("spaces.recorder")
  17 | RAW_DIR  = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
  18 | LOCK_DIR = Path("/tmp/pp_spaces_locks")
  19 | TIMEOUT  = 14400
  20 | def release_lock(handle, lock_fd):
  21 |     try: os.close(lock_fd)
  22 |     except OSError: pass
  23 |     (LOCK_DIR / f"{handle}.lock").unlink(missing_ok=True)
  24 | def record(handle, url, space_id, lock_fd):
  25 |     RAW_DIR.mkdir(parents=True, exist_ok=True)
  26 |     date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
  27 |     output = RAW_DIR / f"{date_str}_{space_id}.m4a"
  28 |     meta_path = RAW_DIR / f"{date_str}_{space_id}.meta.json"
  29 |     meta_path.write_text(json.dumps({"handle":handle,"space_id":space_id,"url":url,"date_str":date_str},indent=2))
  30 |     db = SpaceStateDB()
  31 |     cmd = ["ffmpeg","-y","-allowed_extensions","ALL","-protocol_whitelist","file,crypto,data,tls,tcp,http,https,m3u8,hls","-i",url,"-c","copy","-t",str(TIMEOUT),str(output)]
  32 |     proc = None
  33 |     try:
  34 |         proc = subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,preexec_fn=os.setsid)
  35 |         logger.info(f"Recording @{handle} pid={proc.pid}")
  36 |         proc.wait(timeout=TIMEOUT+60)
  37 |         if output.exists() and output.stat().st_size > 102400:
  38 |             db.upsert(space_id, downloaded_at=datetime.now().isoformat(), transcript_source="audio_replay")
  39 |             return str(output)
  40 |         db.upsert(space_id, error="output_too_small_or_missing")
  41 |         return None
  42 |     except subprocess.TimeoutExpired:
  43 |         db.upsert(space_id, error="timeout")
  44 |         if proc:
  45 |             try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
  46 |             except ProcessLookupError: pass
  47 |         return None
  48 |     except Exception as e:
  49 |         db.upsert(space_id, error=str(e)[:200])
  50 |         if proc:
  51 |             try: os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
  52 |             except ProcessLookupError: pass
  53 |         return None
  54 |     finally:
  55 |         release_lock(handle, lock_fd)
  56 | if __name__ == "__main__":
  57 |     logging.basicConfig(level=logging.INFO)
  58 |     ap = argparse.ArgumentParser()
  59 |     ap.add_argument("--handle", required=True)
  60 |     ap.add_argument("--url", required=True)
  61 |     ap.add_argument("--space-id", required=True)
  62 |     ap.add_argument("--lock-fd", type=int, required=True)
  63 |     args = ap.parse_args()
  64 |     record(args.handle, args.url, args.space_id, args.lock_fd)
  65 | 
```

### File: x_spaces_pipeline/transcriber.py (54 lines)
```
   1 | """
   2 | TOMBSTONED 2026-03-18
   3 | This file is part of the deprecated x_spaces_pipeline/ live-capture system.
   4 | It has been superseded by x_spaces_scraper/run_scraper.py which is the
   5 | single authoritative pipeline. SpaceStateDB is the authoritative state store.
   6 | DO NOT USE — DO NOT IMPORT — DO NOT EXECUTE
   7 | Live capture capability will be reintegrated as a clean stage in run_scraper.py.
   8 | """
   9 | #!/usr/bin/env python3
  10 | """x_spaces_pipeline/transcriber.py"""
  11 | import json, logging, sys, time
  12 | from pathlib import Path
  13 | from datetime import datetime
  14 | sys.path.insert(0, "/home/ultron/protocol_pulse")
  15 | from x_spaces_scraper.whisper_worker import WhisperWorker
  16 | from x_spaces_scraper.spaces_state import SpaceStateDB
  17 | logger = logging.getLogger("spaces.transcriber")
  18 | RAW_DIR = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
  19 | MAX_AGE = 86400
  20 | def transcribe_pending():
  21 |     db = SpaceStateDB()
  22 |     worker = WhisperWorker.get()
  23 |     if not worker.model:
  24 |         logger.error("WhisperWorker unavailable")
  25 |         return
  26 |     for meta_file in sorted(RAW_DIR.glob("*.meta.json"), key=lambda f: f.stat().st_mtime, reverse=True):
  27 |         if time.time() - meta_file.stat().st_mtime > MAX_AGE:
  28 |             continue
  29 |         try: meta = json.loads(meta_file.read_text())
  30 |         except Exception: continue
  31 |         stem = meta_file.name.replace(".meta.json", "")
  32 |         audio_file = RAW_DIR / f"{stem}.m4a"
  33 |         transcript_file = RAW_DIR / f"{stem}.json"
  34 |         if transcript_file.exists(): continue
  35 |         if not audio_file.exists(): continue
  36 |         handle   = meta.get("handle", "unknown")
  37 |         space_id = meta.get("space_id", "unknown")
  38 |         result = worker.transcribe(str(audio_file))
  39 |         word_count = result.get("word_count", 0)
  40 |         if word_count < 50:
  41 |             db.upsert(space_id, error=f"too_short_{word_count}")
  42 |             continue
  43 |         result["handle"]   = handle
  44 |         result["space_id"] = space_id
  45 |         result["meta"]     = meta
  46 |         tmp = transcript_file.with_suffix(".tmp.json")
  47 |         tmp.write_text(json.dumps(result, indent=2))
  48 |         tmp.rename(transcript_file)
  49 |         db.upsert(space_id, transcribed_at=datetime.now().isoformat(), transcript_word_count=word_count)
  50 |         logger.info(f"Transcribed @{handle}: {word_count} words")
  51 | if __name__ == "__main__":
  52 |     logging.basicConfig(level=logging.INFO)
  53 |     transcribe_pending()
  54 | 
```

### File: x_spaces_pipeline/curator.py (80 lines)
```
   1 | """
   2 | TOMBSTONED 2026-03-18
   3 | This file is part of the deprecated x_spaces_pipeline/ live-capture system.
   4 | It has been superseded by x_spaces_scraper/run_scraper.py which is the
   5 | single authoritative pipeline. SpaceStateDB is the authoritative state store.
   6 | DO NOT USE — DO NOT IMPORT — DO NOT EXECUTE
   7 | Live capture capability will be reintegrated as a clean stage in run_scraper.py.
   8 | """
   9 | #!/usr/bin/env python3
  10 | """x_spaces_pipeline/curator.py"""
  11 | import json, logging, os, sys, time
  12 | from pathlib import Path
  13 | from datetime import datetime
  14 | sys.path.insert(0, "/home/ultron/protocol_pulse")
  15 | from dotenv import load_dotenv
  16 | load_dotenv(Path("/home/ultron/protocol_pulse/.env"))
  17 | from x_spaces_scraper.spaces_state import SpaceStateDB
  18 | import anthropic
  19 | logger = logging.getLogger("spaces.curator")
  20 | RAW_DIR    = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/raw")
  21 | MOMENT_DIR = Path("/home/ultron/protocol_pulse/video_pipeline_v3/data/spaces/moments")
  22 | MAX_AGE    = 21600
  23 | MAX_WORDS  = 6000
  24 | CALL_LOG   = Path("/home/ultron/protocol_pulse/data/curator_calls.json")
  25 | CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
  26 | MAX_DAILY  = 10
  27 | def get_daily_calls():
  28 |     today = datetime.now().strftime("%Y%m%d")
  29 |     try:
  30 |         d = json.loads(CALL_LOG.read_text())
  31 |         return d.get("count", 0) if d.get("date") == today else 0
  32 |     except Exception: return 0
  33 | def inc_calls():
  34 |     today = datetime.now().strftime("%Y%m%d")
  35 |     CALL_LOG.write_text(json.dumps({"date": today, "count": get_daily_calls()+1}))
  36 | def curate_pending():
  37 |     MOMENT_DIR.mkdir(parents=True, exist_ok=True)
  38 |     db = SpaceStateDB()
  39 |     if get_daily_calls() >= MAX_DAILY:
  40 |         logger.warning("Daily cap reached")
  41 |         return
  42 |     api_key = os.environ.get("ANTHROPIC_API_KEY", "")
  43 |     if not api_key:
  44 |         logger.error("ANTHROPIC_API_KEY not set")
  45 |         return
  46 |     client = anthropic.Anthropic(api_key=api_key)
  47 |     prompt = 'Bitcoin editor. Extract top 3 moments. Return ONLY JSON no markdown: {"moments":[{"rank":1,"start_sec":0.0,"end_sec":0.0,"quote":"words","speaker":"unknown","signal_type":"macro","quality_score":80}]}'
  48 |     for tf in sorted(RAW_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
  49 |         if time.time() - tf.stat().st_mtime > MAX_AGE: continue
  50 |         if tf.name.endswith(".meta.json"): continue
  51 |         try: transcript = json.loads(tf.read_text())
  52 |         except Exception: continue
  53 |         handle = transcript.get("handle", "unknown")
  54 |         space_id = transcript.get("space_id", "unknown")
  55 |         stem = tf.stem
  56 |         mf = MOMENT_DIR / f"{stem}_moments.json"
  57 |         if mf.exists(): continue
  58 |         text = transcript.get("text", "")
  59 |         if len(text.split()) < 100: continue
  60 |         if get_daily_calls() >= MAX_DAILY: break
  61 |         truncated = " ".join(text.split()[:MAX_WORDS])
  62 |         try:
  63 |             resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role":"user","content": prompt + "\n\n" + truncated}])
  64 |             inc_calls()
  65 |             data = json.loads(resp.content[0].text.strip())
  66 |             data["handle"] = handle
  67 |             data["space_id"] = space_id
  68 |             data["stem"] = stem
  69 |             data["transcript_file"] = str(tf)
  70 |             tmp = mf.with_suffix(".tmp.json")
  71 |             tmp.write_text(json.dumps(data, indent=2))
  72 |             tmp.rename(mf)
  73 |             db.upsert(space_id, summarized_at=datetime.now().isoformat())
  74 |             logger.info(f"@{handle}: {len(data.get('moments',[]))} moments")
  75 |         except Exception as e:
  76 |             logger.error(f"@{handle}: {e}")
  77 |             db.upsert(space_id, error=str(e)[:200])
  78 | if __name__ == "__main__":
  79 |     logging.basicConfig(level=logging.INFO)
  80 |     curate_pending()
```

### File: video_pipeline_v3/utils/spaces_pipeline.py (160 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | spaces_pipeline.py — Bridge between x_spaces_scraper and assembler_v2.
   4 | 
   5 | Reads transcript cache from x_spaces_scraper/cache/ and returns
   6 | formatted segment data for video injection.
   7 | 
   8 | V3: Strict transcript truth — only audio_replay/live_capture sources.
   9 | context_only rejected entirely at this bridge level.
  10 | """
  11 | import json
  12 | import logging
  13 | import os
  14 | import re
  15 | import time
  16 | from pathlib import Path
  17 | 
  18 | logger = logging.getLogger(__name__)
  19 | 
  20 | CACHE_DIR = Path(__file__).parent.parent.parent / "x_spaces_scraper" / "cache"
  21 | 
  22 | 
  23 | def score_transcript(transcript: dict) -> int:
  24 |     """
  25 |     Score 0-100 for video injection priority.
  26 |     - Controversy/named entity keywords: +25
  27 |     - Data/metrics (numbers, %): +20
  28 |     - Named entity + prediction language: +20
  29 |     - Breaking/urgent reference: +10
  30 |     - Length bonus: 150-300w +5, 300-600w +10, 600w+ +15
  31 |     Max: 100
  32 |     """
  33 |     text = transcript.get("transcript", transcript.get("text", "")).lower()
  34 |     score = 0
  35 | 
  36 |     # Controversy / named entity keywords
  37 |     controversy_kws = [
  38 |         "saylor", "blackrock", "sec", "gensler", "etf", "ban", "regulation",
  39 |         "institutional", "congress", "fed", "powell", "inflation", "hack",
  40 |         "exploit", "lawsuit", "fraud", "arrest",
  41 |     ]
  42 |     if any(kw in text for kw in controversy_kws):
  43 |         score += 25
  44 | 
  45 |     # Data / metrics (numbers, %)
  46 |     if re.search(r'\d+\.?\d*\s*%', text) or re.search(r'\$\d+', text) or re.search(r'\d{4,}', text):
  47 |         score += 20
  48 | 
  49 |     # Named entity + prediction language
  50 |     prediction_kws = ["predict", "forecast", "expect", "will reach", "target", "by 20"]
  51 |     entity_kws = ["bitcoin", "btc", "lightning", "mining", "hashrate"]
  52 |     has_prediction = any(kw in text for kw in prediction_kws)
  53 |     has_entity = any(kw in text for kw in entity_kws)
  54 |     if has_prediction and has_entity:
  55 |         score += 20
  56 | 
  57 |     # Breaking / urgent
  58 |     if "breaking" in text or "urgent" in text or "just announced" in text:
  59 |         score += 10
  60 | 
  61 |     # Length bonus
  62 |     wc = len(text.split())
  63 |     if wc >= 600:
  64 |         score += 15
  65 |     elif wc >= 300:
  66 |         score += 10
  67 |     elif wc >= 150:
  68 |         score += 5
  69 | 
  70 |     return min(score, 100)
  71 | 
  72 | 
  73 | def get_latest_spaces_segment(max_age_hours: float = 4.0):
  74 |     """
  75 |     Scan x_spaces_scraper/cache/ for the highest-quality usable transcript
  76 |     written within the last max_age_hours.
  77 | 
  78 |     Returns a dict compatible with assembler_v2 SegmentSpec, or None if nothing fresh.
  79 | 
  80 |     Rules:
  81 |     - Only return transcripts with usable=True AND source in (audio_replay, live_capture)
  82 |     - Reject context_only entirely (usable=False always in this bridge)
  83 |     - Reject transcripts older than max_age_hours
  84 |     - Return highest impact_score among candidates
  85 |     - If max_age_hours=0, always return None (used in tests)
  86 |     """
  87 |     if max_age_hours <= 0:
  88 |         return None
  89 | 
  90 |     if not CACHE_DIR.exists():
  91 |         return None
  92 | 
  93 |     best = None
  94 |     best_impact = -1
  95 |     now = time.time()
  96 |     max_age_s = max_age_hours * 3600
  97 | 
  98 |     for item in CACHE_DIR.glob("transcript_*.json"):
  99 |         try:
 100 |             mtime = item.stat().st_mtime
 101 |             age = now - mtime
 102 |             if age > max_age_s:
 103 |                 continue
 104 | 
 105 |             data = json.loads(item.read_text())
 106 | 
 107 |             # Normalize old cache format
 108 |             if "text" in data and "transcript" not in data:
 109 |                 data["transcript"] = data["text"]
 110 | 
 111 |             # Strict source truth: only audio_replay / live_capture
 112 |             source = data.get("source", "")
 113 |             if source not in ("audio_replay", "live_capture"):
 114 |                 continue
 115 | 
 116 |             # Must be marked usable
 117 |             if not data.get("usable", False):
 118 |                 continue
 119 | 
 120 |             impact = score_transcript(data)
 121 |             if impact > best_impact:
 122 |                 best_impact = impact
 123 |                 best = data
 124 |                 best["_mtime"] = mtime
 125 |                 best["_impact"] = impact
 126 |         except (json.JSONDecodeError, OSError):
 127 |             continue
 128 | 
 129 |     if best is None:
 130 |         return None
 131 | 
 132 |     # Build TTS text: first 500 words, cleaned
 133 |     transcript_text = best.get("transcript", best.get("text", ""))
 134 |     words = transcript_text.split()[:500]
 135 |     tts_text = " ".join(words)
 136 |     # Strip HTML tags and special chars
 137 |     tts_text = re.sub(r'<[^>]+>', '', tts_text)
 138 |     tts_text = re.sub(r'[^\w\s.,!?\'-]', '', tts_text)
 139 | 
 140 |     return {
 141 |         "segment_type": "x_spaces",
 142 |         "space_id": best.get("space_id", ""),
 143 |         "host": best.get("host", best.get("speaker", "unknown")),
 144 |         "title": best.get("title", best.get("space_title", "X Space")),
 145 |         "transcript": transcript_text[:2000],
 146 |         "source": best.get("source", "unknown"),
 147 |         "word_count": len(transcript_text.split()),
 148 |         "quality_score": best.get("quality_score", 0.0),
 149 |         "impact_score": best["_impact"],
 150 |         "speakers": best.get("speakers", []),
 151 |         "tts_text": tts_text,
 152 |         "eyebrow": "LIVE X SPACES SIGNAL",
 153 |         "cached_at": best["_mtime"],
 154 |     }
 155 | 
 156 | 
 157 | if __name__ == "__main__":
 158 |     seg = get_latest_spaces_segment()
 159 |     print("SPACES SEGMENT:", json.dumps(seg, indent=2) if seg else "None")
 160 | 
```

### File: video_pipeline_v3/utils/spaces_monitor.py (642 lines)
```
   1 | #!/usr/bin/env python3
   2 | """
   3 | TOMBSTONED 2026-03-18 — This module is superseded by x_spaces_scraper/ pipeline.
   4 | SpaceStateDB (x_spaces_scraper/spaces_state.py) is the authoritative state store.
   5 | The check_cookie_validity() and get_live_signal_age() utility functions below
   6 | remain active and are used by tests. All monitoring/discovery logic in this file
   7 | is DEPRECATED and must NOT be called. Use x_spaces_scraper/run_scraper.py instead.
   8 | 
   9 | --- Original docstring ---
  10 | spaces_monitor.py — X Spaces Discovery Engine V2
  11 | 
  12 | STRATEGY (in priority order):
  13 | 1. Batch API poll: GET /2/spaces/by/creator_ids for ALL monitored handles (one call, 100 user IDs)
  14 | 2. Participant cross-check: any Space with a legendary handle as host/speaker qualifies regardless of title
  15 | 3. Tweet link intercept: scan recent tweets of monitored handles for /i/spaces/ links (catches announced spaces)
  16 | 4. Keyword search fallback: Guest Token GraphQL search for bitcoin/btc/lightning spaces
  17 | 5. Replay harvest: yt-dlp sweep for ended spaces with replays (daily job)
  18 | 
  19 | Runs every 5 minutes via cron.
  20 | Per PIPELINE_LAWS.md — no keyword title dependency. Handle-first detection.
  21 | """
  22 | 
  23 | import json, logging, os, re, statistics, subprocess, sys, time
  24 | from datetime import datetime, timezone, timedelta
  25 | from pathlib import Path
  26 | 
  27 | BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  28 | sys.path.insert(0, BASE)
  29 | 
  30 | from utils.spaces_pulse import process_spaces_chunk
  31 | 
  32 | logger = logging.getLogger("SpacesMonitor")
  33 | if not logger.handlers:
  34 |     h = logging.StreamHandler()
  35 |     h.setFormatter(logging.Formatter("%(asctime)s [spaces] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
  36 |     logger.addHandler(h)
  37 |     logger.setLevel(logging.INFO)
  38 | 
  39 | LIVE_SIGNALS = os.path.join(BASE, "data", "intelligence", "live_signals.json")
  40 | SPACES_CACHE_DIR = os.path.join(BASE, "cache", "spaces")
  41 | COOKIE_FILE = os.path.join(BASE, "cache", "x_cookies.txt")
  42 | 
  43 | # ─────────────────────────────────────────────────────────────────────────────
  44 | # MASTER HANDLE LIST — unified, deduplicated, corrected
  45 | # Any Space hosted or participated in by these handles is captured.
  46 | # ─────────────────────────────────────────────────────────────────────────────
  47 | MONITORED_HANDLES = [
  48 |     # Core Bitcoin thought leaders
  49 |     "saylor",           # Michael Saylor
  50 |     "jack",             # Jack Dorsey
  51 |     "lopp",             # Jameson Lopp
  52 |     "ODELL",            # Matt Odell
  53 |     "matt_odell",       # Matt Odell alt
  54 |     "MartyBent",        # Marty Bent
  55 |     "PrestonPysh",      # Preston Pysh
  56 |     "stephanlivera",    # Stephan Livera
  57 |     "natbrunell",       # Natalie Brunell
  58 |     "LynAldenContact",  # Lyn Alden
  59 |     "gladstein",        # Alex Gladstein
  60 |     "saifedean",        # Saifedean Ammous
  61 |     "adam3us",          # Adam Back
  62 |     "nvk",              # NVK
  63 |     "giacomozucco",     # Giacomo Zucco
  64 |     "dergigi",          # Gigi
  65 |     "pierre_rochard",   # Pierre Rochard — alias BitcoinPierre
  66 |     "BitcoinPierre",    # Pierre Rochard
  67 |     "coryklippsten",    # Cory Klippsten
  68 |     "Breedlove22",      # Robert Breedlove
  69 |     "JeffBooth",        # Jeff Booth
  70 |     "jimmysong",        # Jimmy Song
  71 |     "ToneVays",         # Tone Vays
  72 |     "Excellion",        # Samson Mow
  73 |     "nic__carter",      # Nic Carter
  74 |     "woonomic",         # Willy Woo
  75 |     "100trillionUSD",   # PlanB
  76 |     "aantonop",         # Andreas Antonopoulos
  77 |     "PeterMcCormack",   # Peter McCormack
  78 |     "APompliano",       # Anthony Pompliano
  79 |     "maxkeiser",        # Max Keiser
  80 |     "real_vijay",       # Vijay Boyapati
  81 |     "knutsvanholm",     # Knut Svanholm
  82 |     "TheGuySwann",      # Guy Swann
  83 |     "pete_rizzo_",      # Pete Rizzo
  84 |     "TuurDemeester",    # Tuur Demeester
  85 |     "MustStopMurad",    # Murad Mahmudov
  86 |     "bitstein",         # Michael Goldstein
  87 |     "pwuille",          # Pieter Wuille
  88 |     "TheBlueMatt",      # Matt Corallo
  89 |     "FossGregf",        # Greg Foss
  90 |     "parman_the",       # BTC Sessions / Par Man
  91 |     "level39",          # Level39
  92 |     "bitkite",          # Bitkite
  93 |     "BTCization",       # BTCization
  94 | 
  95 |     # Media / shows
  96 |     "DocumentingBTC",   # Documenting Bitcoin
  97 |     "BitcoinMagazine",  # Bitcoin Magazine
  98 |     "WhatBitcoinDid",   # Peter McCormack show
  99 |     "SimplyBitcoinTV",  # Simply Bitcoin
 100 |     "TheBitcoinConf",   # Bitcoin Conference
 101 |     "thebitcoinlayer",  # The Bitcoin Layer
 102 |     "stacker_news",     # Stacker News
 103 | 
 104 |     # Political / macro / institutional
 105 |     "nayibbukele",      # President Bukele
 106 |     "GaryCardone",      # Gary Cardone
 107 |     "LukeDashjr",       # Luke Dashjr
 108 | 
 109 |     # Community / traders / analysts
 110 |     "dotkrueger",       # Derek Ross
 111 |     "TonySeverinoCMT",  # Tony Severino
 112 |     "RealCryptoCrank",  # Crypto Crank
 113 |     "LadyTraderRa",     # Lady Trader Ra
 114 |     "ts_hodl",          # TS Hodl
 115 |     "isaiahdaustin",    # Isaiah D Austin
 116 |     "BritishHodl",      # British Hodl
 117 |     "LorenHodl",        # Loren Hodl
 118 |     "Rlad1776",         # Rlad1776
 119 |     "TheBTCTherapist",  # BTC Therapist
 120 |     "MMCrypto",         # MMCrypto
 121 | ]
 122 | 
 123 | # Subset used for priority weighting in sentiment (top tier)
 124 | LEGENDARY_HANDLES = {h.lower() for h in [
 125 |     "saylor", "jack", "lopp", "ODELL", "MartyBent", "PrestonPysh",
 126 |     "stephanlivera", "natbrunell", "LynAldenContact", "gladstein",
 127 |     "saifedean", "adam3us", "nvk", "giacomozucco", "dergigi",
 128 |     "pierre_rochard", "BitcoinPierre", "coryklippsten", "Breedlove22",
 129 |     "JeffBooth", "jimmysong", "Excellion", "nic__carter", "woonomic",
 130 |     "100trillionUSD", "aantonop", "PeterMcCormack", "APompliano",
 131 |     "real_vijay", "knutsvanholm", "TuurDemeester", "MustStopMurad",
 132 |     "LukeDashjr", "nayibbukele", "GaryCardone", "maxkeiser",
 133 |     "ToneVays", "TheGuySwann", "pete_rizzo_", "FossGregf",
 134 | ]}
 135 | 
 136 | # ─────────────────────────────────────────────────────────────────────────────
 137 | # Loop detection (unchanged)
 138 | # ─────────────────────────────────────────────────────────────────────────────
 139 | LOOP_KEYWORDS = ['24/7','live price','live chart','radio','ambient','lofi','non-stop','continuous','price ticker']
 140 | REAL_STREAM_KEYWORDS = ['discussion','debate','interview','ama','recap','reaction','breaking','analysis','panel','live with']
 141 | 
 142 | def is_looped_stream(stream_info: dict) -> bool:
 143 |     red, green = 0, 0
 144 |     title_lower = stream_info.get('title','').lower()
 145 |     if stream_info.get('duration_seconds',0) > 21600: red += 1
 146 |     if any(kw in title_lower for kw in LOOP_KEYWORDS): red += 1
 147 |     words = stream_info.get('transcript_sample','').lower().split()
 148 |     if len(words) > 100:
 149 |         blocks = [' '.join(words[i:i+50]) for i in range(0,len(words)-50,25)]
 150 |         if blocks and len(set(blocks))/len(blocks) < 0.5: red += 1
 151 |     if stream_info.get('consecutive_live_days',0) >= 2: red += 1
 152 |     samples = stream_info.get('viewer_count_samples',[])
 153 |     if len(samples) >= 3 and statistics.mean(samples) > 0:
 154 |         if (statistics.stdev(samples)/statistics.mean(samples)) < 0.05: red += 1
 155 |     if any(kw in title_lower for kw in REAL_STREAM_KEYWORDS): green += 1
 156 |     if 1800 <= stream_info.get('duration_seconds',0) <= 18000: green += 1
 157 |     is_loop = (red >= 2) and (green == 0)
 158 |     if is_loop: logger.warning(f"[LOOP_DETECT] Discarding: {stream_info.get('title')}")
 159 |     return is_loop
 160 | 
 161 | # ─────────────────────────────────────────────────────────────────────────────
 162 | # Topic / sentiment classification (unchanged)
 163 | # ─────────────────────────────────────────────────────────────────────────────
 164 | TOPIC_KEYWORDS = {
 165 |     "mining": ["mining","hashrate","hash rate","difficulty","miner","asic","exahash"],
 166 |     "ETF": ["etf","blackrock","fidelity","grayscale","inflows","outflows","ibit","fbtc"],
 167 |     "price": ["price","rally","dump","bull","bear","ath","all-time high","crash","pump"],
 168 |     "regulation": ["regulation","sec","congress","ban","legislation","gensler","warren"],
 169 |     "self-custody": ["custody","keys","wallet","cold storage","not your keys","self custody"],
 170 |     "lightning": ["lightning","layer 2","l2","payments","nostr","zap"],
 171 |     "macro": ["fed","inflation","interest rate","dollar","treasury","powell","monetary"],
 172 |     "institutional": ["saylor","microstrategy","corporate","treasury","institutional"],
 173 |     "privacy": ["privacy","coinjoin","mixer","surveillance","kyc"],
 174 |     "sovereignty": ["sovereignty","self-sovereign","cypherpunk","decentralize","censorship"],
 175 | }
 176 | BULLISH_WORDS = ["bullish","moon","pump","rally","accumulate","buy","stack","up","surge","breakout","green","higher","ath"]
 177 | BEARISH_WORDS = ["bearish","crash","dump","sell","fear","down","collapse","red","lower","capitulation","panic"]
 178 | 
 179 | def classify_text(text):
 180 |     text_lower = text.lower()
 181 |     topics = [t for t,kws in TOPIC_KEYWORDS.items() if any(kw in text_lower for kw in kws)]
 182 |     bull = sum(1 for w in BULLISH_WORDS if w in text_lower)
 183 |     bear = sum(1 for w in BEARISH_WORDS if w in text_lower)
 184 |     if bull > bear: sentiment = min(90, 50 + bull * 10)
 185 |     elif bear > bull: sentiment = max(10, 50 - bear * 10)
 186 |     else: sentiment = 50
 187 |     return topics, sentiment
 188 | 
 189 | # ─────────────────────────────────────────────────────────────────────────────
 190 | # Twitter API v2 — STRATEGY 1: Batch handle poll (primary, handle-first)
 191 | # ─────────────────────────────────────────────────────────────────────────────
 192 | import requests as _requests
 193 | 
 194 | X_PUBLIC_BEARER = (
 195 |     "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
 196 |     "=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
 197 | )
 198 | 
 199 | def _get_bearer():
 200 |     """Use project bearer token if available, else public."""
 201 |     return os.environ.get("TWITTER_BEARER_TOKEN", X_PUBLIC_BEARER)
 202 | 
 203 | def _api_headers():
 204 |     return {"Authorization": f"Bearer {_get_bearer()}", "User-Agent": "ProtocolPulse/2.0"}
 205 | 
 206 | def _resolve_user_ids(handles: list) -> dict:
 207 |     """
 208 |     Batch resolve handles → user IDs via GET /2/users/by.
 209 |     Returns {handle_lower: user_id}.
 210 |     Max 100 per call — we chunk automatically.
 211 |     """
 212 |     handle_to_id = {}
 213 |     for chunk_start in range(0, len(handles), 100):
 214 |         chunk = handles[chunk_start:chunk_start+100]
 215 |         try:
 216 |             r = _requests.get(
 217 |                 "https://api.twitter.com/2/users/by",
 218 |                 params={"usernames": ",".join(chunk), "user.fields": "id,username"},
 219 |                 headers=_api_headers(), timeout=15,
 220 |             )
 221 |             if r.status_code == 200:
 222 |                 for u in r.json().get("data", []):
 223 |                     handle_to_id[u["username"].lower()] = u["id"]
 224 |             else:
 225 |                 logger.warning(f"[API] users/by HTTP {r.status_code}: {r.text[:200]}")
 226 |         except Exception as e:
 227 |             logger.warning(f"[API] _resolve_user_ids failed: {e}")
 228 |     return handle_to_id
 229 | 
 230 | def batch_poll_spaces(handles: list) -> list:
 231 |     """
 232 |     STRATEGY 1: GET /2/spaces/by/creator_ids — one call per 100 user IDs.
 233 |     Returns all live/scheduled Spaces for our handle list.
 234 |     No title filtering — handle presence alone qualifies.
 235 |     """
 236 |     handle_to_id = _resolve_user_ids(handles)
 237 |     if not handle_to_id:
 238 |         logger.warning("[API] Could not resolve any user IDs — bearer token may be invalid")
 239 |         return []
 240 | 
 241 |     user_ids = list(handle_to_id.values())
 242 |     spaces = []
 243 |     id_to_handle = {v: k for k,v in handle_to_id.items()}
 244 | 
 245 |     for chunk_start in range(0, len(user_ids), 100):
 246 |         chunk = user_ids[chunk_start:chunk_start+100]
 247 |         try:
 248 |             r = _requests.get(
 249 |                 "https://api.twitter.com/2/spaces/by/creator_ids",
 250 |                 params={
 251 |                     "user_ids": ",".join(chunk),
 252 |                     "space.fields": "id,title,host_ids,speaker_ids,participant_count,started_at,state,ended_at,is_ticketed",
 253 |                     "expansions": "host_ids,speaker_ids",
 254 |                     "user.fields": "username",
 255 |                 },
 256 |                 headers=_api_headers(), timeout=20,
 257 |             )
 258 |             if r.status_code == 200:
 259 |                 data = r.json()
 260 |                 users = {u["id"]: u["username"] for u in data.get("includes",{}).get("users",[])}
 261 |                 for s in data.get("data", []):
 262 |                     host_id = (s.get("host_ids") or [""])[0]
 263 |                     host_handle = users.get(host_id, id_to_handle.get(host_id, "unknown"))
 264 |                     spaces.append({
 265 |                         "video_id": s["id"],
 266 |                         "title": s.get("title","") or f"Space by @{host_handle}",
 267 |                         "channel": f"@{host_handle}",
 268 |                         "source": "x_spaces",
 269 |                         "url": f"https://twitter.com/i/spaces/{s['id']}",
 270 |                         "detected_at": datetime.now(timezone.utc).isoformat(),
 271 |                         "state": s.get("state","live"),
 272 |                         "participant_count": s.get("participant_count",0),
 273 |                         "detected_via": "batch_api_v2",
 274 |                     })
 275 |                     logger.info(f"[BATCH] LIVE SPACE: @{host_handle} — {s.get('title','(no title)')}")
 276 |             elif r.status_code == 403:
 277 |                 logger.warning("[API] 403 on spaces/by/creator_ids — token may not have Spaces access")
 278 |             else:
 279 |                 logger.debug(f"[API] spaces/by/creator_ids HTTP {r.status_code}")
 280 |         except Exception as e:
 281 |             logger.warning(f"[API] batch_poll_spaces error: {e}")
 282 | 
 283 |     return spaces
 284 | 
 285 | # ─────────────────────────────────────────────────────────────────────────────
 286 | # STRATEGY 2: Participant cross-check
 287 | # For any Space found, verify if legendary handles are participants/speakers
 288 | # ─────────────────────────────────────────────────────────────────────────────
 289 | def participant_cross_check(space_id: str) -> list:
 290 |     """
 291 |     GET /2/spaces/{id} with speaker/listener expansions.
 292 |     Returns list of legendary handles found as participants.
 293 |     """
 294 |     try:
 295 |         r = _requests.get(
 296 |             f"https://api.twitter.com/2/spaces/{space_id}",
 297 |             params={
 298 |                 "space.fields": "host_ids,speaker_ids,participant_count",
 299 |                 "expansions": "host_ids,speaker_ids",
 300 |                 "user.fields": "username",
 301 |             },
 302 |             headers=_api_headers(), timeout=15,
 303 |         )
 304 |         if r.status_code != 200:
 305 |             return []
 306 |         data = r.json()
 307 |         users = {u["id"]: u["username"].lower() for u in data.get("includes",{}).get("users",[])}
 308 |         return [uname for uname in users.values() if uname in LEGENDARY_HANDLES]
 309 |     except Exception:
 310 |         return []
 311 | 
 312 | # ─────────────────────────────────────────────────────────────────────────────
 313 | # STRATEGY 3: Tweet link intercept — scan recent tweets for /i/spaces/ links
 314 | # ─────────────────────────────────────────────────────────────────────────────
 315 | def tweet_link_intercept(handles: list, handle_to_id: dict) -> list:
 316 |     """
 317 |     Scan last 30 mins of tweets from monitored handles for Space URLs.
 318 |     Catches spaces announced via tweet before showing up in Spaces API.
 319 |     """
 320 |     since = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
 321 |     spaces_found = []
 322 |     seen_ids = set()
 323 | 
 324 |     # Sample up to 20 high-priority handles to keep API calls reasonable
 325 |     priority = [h for h in handles if h.lower() in LEGENDARY_HANDLES][:20]
 326 | 
 327 |     for handle in priority:
 328 |         uid = handle_to_id.get(handle.lower())
 329 |         if not uid:
 330 |             continue
 331 |         try:
 332 |             r = _requests.get(
 333 |                 f"https://api.twitter.com/2/users/{uid}/tweets",
 334 |                 params={
 335 |                     "start_time": since,
 336 |                     "max_results": 10,
 337 |                     "tweet.fields": "text,created_at",
 338 |                     "expansions": "attachments.media_keys",
 339 |                 },
 340 |                 headers=_api_headers(), timeout=10,
 341 |             )
 342 |             if r.status_code != 200:
 343 |                 continue
 344 |             for tweet in r.json().get("data", []):
 345 |                 text = tweet.get("text","")
 346 |                 for match in re.finditer(r'twitter\.com/i/spaces/(\w+)|x\.com/i/spaces/(\w+)', text):
 347 |                     sid = match.group(1) or match.group(2)
 348 |                     if sid and sid not in seen_ids:
 349 |                         seen_ids.add(sid)
 350 |                         spaces_found.append({
 351 |                             "video_id": sid,
 352 |                             "title": f"Space announced by @{handle}",
 353 |                             "channel": f"@{handle}",
 354 |                             "source": "x_spaces",
 355 |                             "url": f"https://twitter.com/i/spaces/{sid}",
 356 |                             "detected_at": datetime.now(timezone.utc).isoformat(),
 357 |                             "state": "live",
 358 |                             "detected_via": "tweet_link_intercept",
 359 |                         })
 360 |                         logger.info(f"[TWEET_INTERCEPT] @{handle} tweeted Space link: {sid}")
 361 |         except Exception as e:
 362 |             logger.debug(f"[TWEET_INTERCEPT] {handle}: {e}")
 363 | 
 364 |     return spaces_found
 365 | 
 366 | # ─────────────────────────────────────────────────────────────────────────────
 367 | # STRATEGY 4: Guest Token keyword search fallback
 368 | # ─────────────────────────────────────────────────────────────────────────────
 369 | def guest_token_search() -> list:
 370 |     """Fallback keyword search via Guest Token GraphQL when API returns nothing."""
 371 |     try:
 372 |         r = _requests.post("https://api.twitter.com/1.1/guest/activate.json",
 373 |                            headers={"Authorization": f"Bearer {X_PUBLIC_BEARER}"}, timeout=10)
 374 |         r.raise_for_status()
 375 |         guest_token = r.json()["guest_token"]
 376 |     except Exception as e:
 377 |         logger.debug(f"[GUEST] Token refresh failed: {e}")
 378 |         return []
 379 | 
 380 |     headers = {
 381 |         "Authorization": f"Bearer {X_PUBLIC_BEARER}",
 382 |         "X-Guest-Token": guest_token,
 383 |         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/122.0.0.0 Safari/537.36",
 384 |         "X-Twitter-Active-User": "yes",
 385 |         "X-Twitter-Client-Language": "en",
 386 |     }
 387 | 
 388 |     spaces, seen = [], set()
 389 |     for kw in ["bitcoin", "btc", "lightning"]:
 390 |         try:
 391 |             variables = json.dumps({"query": f"{kw} space", "count": 20, "product": "Top"})
 392 |             features = json.dumps({
 393 |                 "responsive_web_graphql_exclude_directive_enabled": True,
 394 |                 "spaces_2022_h2_spaces_communities_enabled": True,
 395 |                 "spaces_2022_h2_clipping_enabled": True,
 396 |             })
 397 |             r = _requests.get(
 398 |                 "https://twitter.com/i/api/graphql/nK1dw4oV3k4w5TdtcAdSww/SearchTimeline",
 399 |                 params={"variables": variables, "features": features},
 400 |                 headers=headers, timeout=15,
 401 |             )
 402 |             if r.status_code != 200:
 403 |                 continue
 404 |             data = r.json()
 405 |             instructions = (data.get("data",{}).get("search_by_raw_query",{})
 406 |                               .get("search_timeline",{}).get("timeline",{}).get("instructions",[]))
 407 |             for inst in instructions:
 408 |                 for entry in inst.get("entries",[]):
 409 |                     space_result = entry.get("content",{}).get("itemContent",{}).get("audioSpace",{})
 410 |                     if not space_result:
 411 |                         continue
 412 |                     meta = space_result.get("metadata",{})
 413 |                     sid = meta.get("rest_id","")
 414 |                     if not sid or sid in seen:
 415 |                         continue
 416 |                     seen.add(sid)
 417 |                     creator = (meta.get("creator_results",{}).get("result",{})
 418 |                                   .get("legacy",{}).get("screen_name","unknown"))
 419 |                     # Only include if creator is in our monitored list
 420 |                     if creator.lower() not in {h.lower() for h in MONITORED_HANDLES}:
 421 |                         continue
 422 |                     state = meta.get("state","").lower()
 423 |                     spaces.append({
 424 |                         "video_id": sid,
 425 |                         "title": meta.get("title","") or f"Space by @{creator}",
 426 |                         "channel": f"@{creator}",
 427 |                         "source": "x_spaces",
 428 |                         "url": f"https://twitter.com/i/spaces/{sid}",
 429 |                         "detected_at": datetime.now(timezone.utc).isoformat(),
 430 |                         "state": "ended" if state in ("ended","timedout") else state,
 431 |                         "detected_via": "guest_token_keyword",
 432 |                     })
 433 |         except Exception as e:
 434 |             logger.debug(f"[GUEST] search {kw}: {e}")
 435 | 
 436 |     return spaces
 437 | 
 438 | # ─────────────────────────────────────────────────────────────────────────────
 439 | # STRATEGY 5: twspace-dl / yt-dlp per-handle (last resort)
 440 | # ─────────────────────────────────────────────────────────────────────────────
 441 | def _find_twspace_dl():
 442 |     for name in ["twspace_dl","twspace-dl"]:
 443 |         for p in [os.path.expanduser(f"~/.local/bin/{name}"), f"/usr/local/bin/{name}"]:
 444 |             if os.path.exists(p): return p
 445 |     return None
 446 | 
 447 | TWSPACE_BIN = _find_twspace_dl()
 448 | 
 449 | def twspace_handle_check(handles: list) -> list:
 450 |     """Last-resort: poll individual handles via twspace-dl. Slow — limit to top 20."""
 451 |     if not TWSPACE_BIN:
 452 |         return []
 453 |     os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)
 454 |     if not os.path.exists(COOKIE_FILE):
 455 |         open(COOKIE_FILE,"w").write("# Netscape HTTP Cookie File\n")
 456 | 
 457 |     spaces = []
 458 |     priority = [h for h in handles if h.lower() in LEGENDARY_HANDLES][:20]
 459 |     for handle in priority:
 460 |         try:
 461 |             res = subprocess.run(
 462 |                 [TWSPACE_BIN, "-U", f"https://twitter.com/{handle}", "-c", COOKIE_FILE, "-p"],
 463 |                 capture_output=True, text=True, timeout=15,
 464 |             )
 465 |             out = res.stdout.strip() + res.stderr.strip()
 466 |             if res.returncode == 0 and out and "no live" not in out.lower() and "error" not in out.lower():
 467 |                 sid_match = re.search(r'spaces?/([a-zA-Z0-9]+)', out)
 468 |                 sid = sid_match.group(1) if sid_match else f"twspace_{handle}_{int(time.time())}"
 469 |                 title_match = re.search(r'title[\"\s:]+(.+?)[\n\"]', out, re.IGNORECASE)
 470 |                 title = title_match.group(1).strip() if title_match else f"Live Space by @{handle}"
 471 |                 spaces.append({
 472 |                     "video_id": sid, "title": title, "channel": f"@{handle}",
 473 |                     "source": "x_spaces", "url": f"https://twitter.com/i/spaces/{sid}",
 474 |                     "detected_at": datetime.now(timezone.utc).isoformat(),
 475 |                     "state": "live", "detected_via": "twspace_dl",
 476 |                 })
 477 |                 logger.info(f"[TWSPACE] LIVE: @{handle} — {title}")
 478 |         except subprocess.TimeoutExpired:
 479 |             logger.debug(f"[TWSPACE] Timeout: @{handle}")
 480 |         except Exception as e:
 481 |             logger.debug(f"[TWSPACE] {handle}: {e}")
 482 |     return spaces
 483 | 
 484 | # ─────────────────────────────────────────────────────────────────────────────
 485 | # Cookie validity check
 486 | # ─────────────────────────────────────────────────────────────────────────────
 487 | def check_cookie_validity(path):
 488 |     if not os.path.exists(path):
 489 |         logger.warning(f"[COOKIE] Missing: {path}")
 490 |         return False
 491 |     if os.path.getsize(path) < 50:
 492 |         logger.info("[COOKIE] Empty placeholder — unauthenticated mode")
 493 |         return True
 494 |     age = (time.time() - os.path.getmtime(path)) / 86400
 495 |     if age > 6:
 496 |         logger.warning(f"[COOKIE] {age:.1f} days old — may be stale. Refresh via browser export.")
 497 |     return True
 498 | 
 499 | 
 500 | def get_live_signal_age(cache_path=None):
 501 |     """Return age in seconds of active_signal.json cache. Returns float('inf') if missing."""
 502 |     if cache_path is None:
 503 |         cache_path = os.path.join(BASE, "cache", "active_signal.json")
 504 |     try:
 505 |         data = json.loads(open(cache_path).read())
 506 |         fetched = data.get("fetched_at", 0)
 507 |         return time.time() - fetched
 508 |     except Exception:
 509 |         return float('inf')
 510 | 
 511 | # ─────────────────────────────────────────────────────────────────────────────
 512 | # Live Signals JSON
 513 | # ─────────────────────────────────────────────────────────────────────────────
 514 | def load_live_signals():
 515 |     if os.path.exists(LIVE_SIGNALS):
 516 |         try:
 517 |             with open(LIVE_SIGNALS) as f: return json.load(f)
 518 |         except (json.JSONDecodeError, OSError): pass
 519 |     return {"live_streams":[],"updated_at":None,"monitoring":True,"channels_watched":0}
 520 | 
 521 | def save_live_signals(signals):
 522 |     os.makedirs(os.path.dirname(LIVE_SIGNALS), exist_ok=True)
 523 |     signals["updated_at"] = datetime.now(timezone.utc).isoformat()
 524 |     tmp = LIVE_SIGNALS + ".tmp"
 525 |     with open(tmp,"w") as f: json.dump(signals, f, indent=2)
 526 |     os.replace(tmp, LIVE_SIGNALS)
 527 | 
 528 | def update_live_signals(space_info, topics, sentiment, transcript_chunk=""):
 529 |     signals = load_live_signals()
 530 |     stream_entry = next((s for s in signals.get("live_streams",[])
 531 |                         if s.get("video_id") == space_info.get("video_id")), None)
 532 |     if stream_entry is None:
 533 |         stream_entry = {
 534 |             "video_id": space_info["video_id"],
 535 |             "title": space_info["title"],
 536 |             "channel": space_info["channel"],
 537 |             "source": "x_spaces",
 538 |             "url": space_info.get("url",""),
 539 |             "started_at": space_info.get("detected_at", datetime.now(timezone.utc).isoformat()),
 540 |             "topics":[], "current_sentiment":50, "sentiment_history":[],
 541 |             "transcript_chunks":[], "status":"live",
 542 |             "detected_via": space_info.get("detected_via","unknown"),
 543 |             "participant_count": space_info.get("participant_count",0),
 544 |         }
 545 |         signals.setdefault("live_streams",[]).append(stream_entry)
 546 | 
 547 |     stream_entry["topics"] = list(set(stream_entry.get("topics",[]) + topics))
 548 |     if sentiment != 50 or not stream_entry["sentiment_history"]:
 549 |         stream_entry["sentiment_history"].append(
 550 |             {"time": datetime.now(timezone.utc).isoformat(), "score": sentiment})
 551 |         stream_entry["sentiment_history"] = stream_entry["sentiment_history"][-100:]
 552 |     recent = stream_entry["sentiment_history"][-5:]
 553 |     stream_entry["current_sentiment"] = round(sum(r["score"] for r in recent) / len(recent))
 554 |     if transcript_chunk:
 555 |         stream_entry["transcript_chunks"].append(transcript_chunk[:200])
 556 |         stream_entry["transcript_chunks"] = stream_entry["transcript_chunks"][-50:]
 557 |     stream_entry["last_updated"] = datetime.now(timezone.utc).isoformat()
 558 |     save_live_signals(signals)
 559 |     return stream_entry
 560 | 
 561 | # ─────────────────────────────────────────────────────────────────────────────
 562 | # Main — unified discovery with strategy cascade
 563 | # ─────────────────────────────────────────────────────────────────────────────
 564 | def detect_all_spaces() -> list:
 565 |     """
 566 |     Run all detection strategies in priority order.
 567 |     Deduplicate by video_id. Legendary-handle spaces always win.
 568 |     """
 569 |     check_cookie_validity(COOKIE_FILE)
 570 |     all_spaces = []
 571 |     seen_ids = set()
 572 | 
 573 |     def add_spaces(new_spaces, label):
 574 |         added = 0
 575 |         for s in new_spaces:
 576 |             if s["video_id"] not in seen_ids:
 577 |                 seen_ids.add(s["video_id"])
 578 |                 all_spaces.append(s)
 579 |                 added += 1
 580 |         if added: logger.info(f"[{label}] +{added} space(s)")
 581 | 
 582 |     # Strategy 1: Batch API (best — no title dependency)
 583 |     handle_to_id = {}
 584 |     batch_spaces = batch_poll_spaces(MONITORED_HANDLES)
 585 |     add_spaces(batch_spaces, "BATCH_API")
 586 | 
 587 |     # Resolve IDs for strategy 3 (tweet intercept) — reuse if already done
 588 |     if not handle_to_id:
 589 |         handle_to_id = _resolve_user_ids(MONITORED_HANDLES)
 590 | 
 591 |     # Strategy 2: Participant cross-check for any spaces found
 592 |     for s in list(all_spaces):
 593 |         legendary = participant_cross_check(s["video_id"])
 594 |         if legendary:
 595 |             s["legendary_participants"] = legendary
 596 |             logger.info(f"[PARTICIPANT] {s['video_id']}: legendary participants — {legendary}")
 597 | 
 598 |     # Strategy 3: Tweet link intercept (catches pre-live announcements)
 599 |     tweet_spaces = tweet_link_intercept(MONITORED_HANDLES, handle_to_id)
 600 |     add_spaces(tweet_spaces, "TWEET_INTERCEPT")
 601 | 
 602 |     # Strategy 4: Keyword fallback (only if strategies 1+3 found nothing)
 603 |     if not all_spaces:
 604 |         guest_spaces = guest_token_search()
 605 |         add_spaces(guest_spaces, "GUEST_TOKEN")
 606 | 
 607 |     # Strategy 5: twspace-dl last resort
 608 |     if not all_spaces:
 609 |         twspace_spaces = twspace_handle_check(MONITORED_HANDLES)
 610 |         add_spaces(twspace_spaces, "TWSPACE_DL")
 611 | 
 612 |     return all_spaces
 613 | 
 614 | def run_daemon():
 615 |     logger.info(f"[V2] Scanning {len(MONITORED_HANDLES)} handles via 5-strategy cascade...")
 616 |     spaces = detect_all_spaces()
 617 | 
 618 |     if not spaces:
 619 |         logger.info("No active X Spaces detected across all strategies")
 620 |     else:
 621 |         for space in spaces:
 622 |             if is_looped_stream(space):
 623 |                 continue
 624 |             logger.info(f"SPACE: {space['channel']} [{space.get('detected_via','?')}] — {space['title']}")
 625 |             topics, sentiment = classify_text(space["title"])
 626 |             update_live_signals(space, topics, sentiment, f"X Space detected: {space['title']}")
 627 |             process_spaces_chunk(
 628 |                 space_id=space["video_id"],
 629 |                 chunk_text=space["title"],
 630 |                 speaker_handle=space["channel"].lstrip("@"),
 631 |                 space_url=space.get("url",""),
 632 |                 chunk_index=0,
 633 |             )
 634 | 
 635 |     signals = load_live_signals()
 636 |     space_count = sum(1 for s in signals.get("live_streams",[])
 637 |                      if s.get("source") == "x_spaces" and s.get("status") == "live")
 638 |     logger.info(f"[V2] Summary: {space_count} X Spaces in live_signals.json")
 639 | 
 640 | if __name__ == "__main__":
 641 |     run_daemon()
 642 | 
```

### File: video_pipeline_v3/assembler_v2/segments/x_spaces_segment.py (159 lines)
```
   1 | from __future__ import annotations
   2 | import os
   3 | import logging
   4 | from pathlib import Path
   5 | from .base import Segment
   6 | from ..manifest import SegmentSpec, RenderedSegment
   7 | from ..state import EpisodeContext
   8 | from ..helpers import run_ffmpeg, ffprobe_duration, ffprobe_contract, atomic_rename, safe_text
   9 | from ..constants import (
  10 |     VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_PIX_FMT, VIDEO_CODEC, VIDEO_CRF,
  11 |     AUDIO_CODEC, AUDIO_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_CHANNELS,
  12 |     AUDIO_LIMITER, AUDIO_TARGET_LUFS, AUDIO_MAX_TRUE_PEAK, AUDIO_LRA,
  13 |     COLOR_BG, FONT_BOLD, FONT_MONO,
  14 |     FFMPEG_TIMEOUT_FILTER,
  15 | )
  16 | 
  17 | logger = logging.getLogger(__name__)
  18 | 
  19 | BRAND_RED = "0xE8272B"
  20 | CARD_BG = "0x141419"
  21 | META_GRAY = "0x888888"
  22 | 
  23 | 
  24 | class XSpacesSegment(Segment):
  25 |     """X Spaces intelligence segment — branded visual with TTS narration."""
  26 |     criticality = 'optional'
  27 | 
  28 |     def render(self, spec: SegmentSpec, ctx: EpisodeContext,
  29 |                output_path: Path, idx: int) -> RenderedSegment:
  30 |         try:
  31 |             return self._render(spec, ctx, output_path, idx)
  32 |         except Exception as e:
  33 |             logger.exception(f'[x_spaces] exception: {e}')
  34 |             return self.filler_result(spec, ctx, output_path, str(e))
  35 | 
  36 |     def _render(self, spec: SegmentSpec, ctx: EpisodeContext,
  37 |                 output_path: Path, idx: int = 0) -> RenderedSegment:
  38 |         # Law 1: no content → filler
  39 |         if not spec.body:
  40 |             return self.filler_result(spec, ctx, output_path, 'no_x_spaces_content')
  41 | 
  42 |         # Get TTS audio
  43 |         tts = self._get_tts(spec, ctx, idx)
  44 |         if not tts or not tts.exists() or tts.stat().st_size < 1000:
  45 |             return self.filler_result(spec, ctx, output_path, 'no_tts_for_x_spaces')
  46 | 
  47 |         dur = ffprobe_duration(tts)
  48 |         if dur < 0.5:
  49 |             dur = 10.0
  50 | 
  51 |         tmp = output_path.with_suffix('.tmp.mp4')
  52 |         fg = self._build_filter_graph(spec)
  53 | 
  54 |         ok = run_ffmpeg([
  55 |             '-f', 'lavfi', '-i', f'color=c={COLOR_BG}:s={VIDEO_W}x{VIDEO_H}:r={VIDEO_FPS}',
  56 |             '-i', str(tts),
  57 |             '-filter_complex', fg,
  58 |             '-map', '[v_out]', '-map', '[a_out]',
  59 |             '-c:v', VIDEO_CODEC, '-crf', str(VIDEO_CRF), '-preset', 'medium',
  60 |             '-r', str(VIDEO_FPS), '-pix_fmt', VIDEO_PIX_FMT,
  61 |             '-c:a', AUDIO_CODEC, '-ar', str(AUDIO_SAMPLE_RATE),
  62 |             '-b:a', AUDIO_BITRATE, '-ac', str(AUDIO_CHANNELS),
  63 |             '-t', str(round(dur, 3)), '-movflags', '+faststart', str(tmp),
  64 |         ], 'x_spaces', FFMPEG_TIMEOUT_FILTER)
  65 | 
  66 |         if not ok or not tmp.exists() or tmp.stat().st_size < 1000:
  67 |             return self.filler_result(spec, ctx, output_path, 'x_spaces encode failed')
  68 | 
  69 |         passed, summary = ffprobe_contract(tmp)
  70 |         if not passed:
  71 |             tmp.unlink(missing_ok=True)
  72 |             return self.filler_result(spec, ctx, output_path, 'contract_failed')
  73 | 
  74 |         rename_ok = atomic_rename(tmp, output_path)
  75 |         if not rename_ok:
  76 |             tmp.unlink(missing_ok=True)
  77 |             return self.filler_result(spec, ctx, output_path, 'atomic_rename failed')
  78 |         actual = summary.get('duration', dur)
  79 |         logger.info(f'[x_spaces] OK ({actual:.1f}s)')
  80 |         return RenderedSegment(
  81 |             spec=spec, path=str(output_path), duration=actual,
  82 |             contract_passed=True, degraded=False, ffprobe_summary=summary,
  83 |         )
  84 | 
  85 |     def _get_tts(self, spec: SegmentSpec, ctx: EpisodeContext, idx: int = 0):
  86 |         """Get TTS audio: spec.tts_path first, then inline ElevenLabs."""
  87 |         tts = spec.tts()
  88 |         if tts and tts.exists() and tts.stat().st_size >= 1000:
  89 |             return tts
  90 | 
  91 |         # Inline ElevenLabs — follow cold_open.py pattern
  92 |         try:
  93 |             from ..network import http_post
  94 |             key = os.environ.get('ELEVENLABS_API_KEY', '')
  95 |             if not key:
  96 |                 return None
  97 |             voice_id = '1SM7GgM6IMuvQlz2BwM3'
  98 |             text = spec.body[:500]
  99 |             out_path = ctx.segment_dir() / f'xspaces_{idx}_tts.mp3'
 100 |             resp = http_post(
 101 |                 f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
 102 |                 headers={'xi-api-key': key, 'Content-Type': 'application/json'},
 103 |                 json_body={
 104 |                     'text': text,
 105 |                     'model_id': 'eleven_turbo_v2_5',
 106 |                     'voice_settings': {'stability': 0.5, 'similarity_boost': 0.5},
 107 |                 },
 108 |                 timeout=30,
 109 |             )
 110 |             if resp is None or len(resp.content) < 1000:
 111 |                 return None
 112 |             out_path.write_bytes(resp.content)
 113 |             return out_path
 114 |         except Exception as e:
 115 |             logger.warning(f'[x_spaces] inline TTS failed: {e}')
 116 |             return None
 117 | 
 118 |     def _build_filter_graph(self, spec: SegmentSpec) -> str:
 119 |         """Build branded X Spaces visual filter graph."""
 120 |         parts = [f'[0:v]scale={VIDEO_W}:{VIDEO_H},format={VIDEO_PIX_FMT}[bg]']
 121 | 
 122 |         # Top red eyebrow strip
 123 |         eyebrow = safe_text(spec.headline or 'X SPACES', 40)
 124 |         parts.append(
 125 |             f'[bg]drawbox=x=0:y=0:w={VIDEO_W}:h=80:color={BRAND_RED}:t=fill[bar]'
 126 |         )
 127 |         parts.append(
 128 |             f"[bar]drawtext=fontfile={FONT_BOLD}:text='{eyebrow}':"
 129 |             f"fontcolor=white:fontsize=32:x=40:y=24[top]"
 130 |         )
 131 | 
 132 |         # Main content: transcript excerpt
 133 |         body_text = safe_text(spec.body or '', 200)
 134 |         parts.append(
 135 |             f"[top]drawtext=fontfile={FONT_MONO}:text='{body_text}':"
 136 |             f"fontcolor=white:fontsize=22:x=60:y=140:line_spacing=8[mid]"
 137 |         )
 138 | 
 139 |         # Bottom attribution strip
 140 |         btc_str = safe_text(f'BTC {spec.btc_price}', 30) if spec.btc_price and spec.btc_price != 'N/A' else ''
 141 |         source_attr = safe_text('via X Spaces // Protocol Pulse', 60)
 142 |         parts.append(
 143 |             f"[mid]drawbox=x=0:y={VIDEO_H - 80}:w={VIDEO_W}:h=80:"
 144 |             f"color={CARD_BG}:t=fill[bot]"
 145 |         )
 146 |         parts.append(
 147 |             f"[bot]drawtext=fontfile={FONT_MONO}:text='{source_attr}':"
 148 |             f"fontcolor={META_GRAY}:fontsize=18:x=40:y={VIDEO_H - 52}[v_out]"
 149 |         )
 150 | 
 151 |         # Audio processing
 152 |         parts.append(
 153 |             f'[1:a]aformat=channel_layouts=stereo:sample_rates={AUDIO_SAMPLE_RATE},'
 154 |             f'loudnorm=I={AUDIO_TARGET_LUFS}:TP={AUDIO_MAX_TRUE_PEAK}:LRA={AUDIO_LRA}:linear=true,'
 155 |             f'alimiter=limit={AUDIO_LIMITER}:attack=5:release=50[a_out]'
 156 |         )
 157 | 
 158 |         return ';'.join(parts)
 159 | 
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
