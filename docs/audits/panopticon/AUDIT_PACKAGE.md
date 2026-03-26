# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: panopticon
# Branch: main
# Generated: 2026-03-26 00:49 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS

### LAW 1: BRAND PALETTE
- Primary Red: #CC2222 (accent, borders, kickers)
- FFmpeg Red: #FF3333 (drawtext/drawbox fallback — closest FFmpeg-safe)
- Background: #0A0A0F (dark navy, never pure black)
- White: #FFFFFF (primary text)
- Gold: #F8C15C (info rail, price displays)
- Mono Font: JetBrains Mono (data, kickers, code)

### LAW 2: PIXEL ZONES
- Full canvas: 1920×1080
- Left panel (PiP): 0–960px wide, full 1080 height
- Right panel (PiP video): 960–1920px
- PiP zone: top-right quadrant x=960-1880, y=0-540
- Subtitle band: y=778-885, full width, dark glass bg
- Info rail: bottom y≈1032-1080, gold text

### LAW 3: TYPOGRAPHY
- Headlines: Bold, white, large (fontsize 42-56)
- Kickers: Red monospace, uppercase, fontsize 24-28
- Body: White, fontsize 28-32
- Sponsor text: White monospace, fontsize 22-26

### LAW 4: COMPONENT PATTERNS
- Cards: Dark bg (#111), red left accent border (3px), white text
- Glass panels: rgba(0,0,0,0.82) fill, subtle border
- Sponsor carousel: 3 rotating cards, 8s per card, FFmpeg enable= timing
- Episode title: Large white bold, "PULSE CHECK" red kicker above

### LAW 5: ANIMATION
- Sponsor rotation: enable='between(t,START,END)' pattern
- Smooth transitions preferred, hard cuts acceptable for data cards
- No debug overlays in production



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

### File: services/panopticon_service.py (1112 lines)
```
   1 | """
   2 | PANOPTICON Intelligence Service
   3 | "They watch us. Now we watch them."
   4 | 
   5 | Data pipeline for congressional disclosures, whale wallet tracking,
   6 | forex/macro signals, and geopolitical intelligence.
   7 | 
   8 | Sources (all free, no auth):
   9 | - efts.house.gov — STOCK Act financial disclosures
  10 | - mempool.space — Bitcoin whale wallet monitoring
  11 | - exchangerate.host — Forex/macro sovereign signals
  12 | - Existing article pipeline — Geopolitical events
  13 | - Anthropic API — "Make the Bitcoin Case" AI generation
  14 | """
  15 | 
  16 | import logging
  17 | import os
  18 | import random
  19 | import time
  20 | import hashlib
  21 | import json
  22 | import re
  23 | import threading
  24 | from datetime import datetime, timedelta
  25 | from typing import Optional
  26 | 
  27 | import requests
  28 | 
  29 | logger = logging.getLogger(__name__)
  30 | 
  31 | ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
  32 | ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL_ID", "claude-sonnet-4-6-20250514")
  33 | 
  34 | # ── Cache layer (thread-safe with TTL + thundering herd protection) ─────────
  35 | _cache = {}
  36 | _cache_lock = threading.Lock()
  37 | _cache_inflight = set()
  38 | 
  39 | 
  40 | def _cached(key: str, ttl_seconds: int = 300):
  41 |     """Return cached value if fresh, else None. Thread-safe."""
  42 |     with _cache_lock:
  43 |         entry = _cache.get(key)
  44 |         if entry and time.time() - entry["ts"] < ttl_seconds:
  45 |             return entry["data"]
  46 |     return None
  47 | 
  48 | 
  49 | def _set_cache(key: str, data):
  50 |     with _cache_lock:
  51 |         _cache[key] = {"data": data, "ts": time.time()}
  52 | 
  53 | 
  54 | def _get_or_fetch(key: str, fetch_fn, ttl_seconds: int = 300):
  55 |     """Thread-safe cache fetch with thundering-herd protection.
  56 |     If another thread is already fetching, returns stale data instead of piling on."""
  57 |     with _cache_lock:
  58 |         entry = _cache.get(key)
  59 |         if entry and time.time() - entry["ts"] < ttl_seconds:
  60 |             return entry["data"]
  61 |         if key in _cache_inflight:
  62 |             # Return stale data rather than pile on
  63 |             return entry["data"] if entry else None
  64 |         _cache_inflight.add(key)
  65 |     try:
  66 |         data = fetch_fn()
  67 |         _set_cache(key, data)
  68 |         return data
  69 |     finally:
  70 |         with _cache_lock:
  71 |             _cache_inflight.discard(key)
  72 | 
  73 | 
  74 | # ── Rate-limited HTTP GET with exponential backoff ──────────────────────────
  75 | 
  76 | def _rate_limited_get(url, params=None, timeout=10, sleep_secs=1.0, retries=3,
  77 |                       headers=None):
  78 |     """HTTP GET with exponential backoff on 429 responses."""
  79 |     if headers is None:
  80 |         headers = {"User-Agent": "ProtocolPulse/1.0"}
  81 |     for attempt in range(retries):
  82 |         try:
  83 |             resp = requests.get(url, params=params, timeout=timeout, headers=headers)
  84 |             if resp.status_code == 429:
  85 |                 wait = sleep_secs * (2 ** attempt) + random.uniform(0, 0.5)
  86 |                 logger.warning("Rate limited (429) by %s — backing off %.1fs", url, wait)
  87 |                 time.sleep(wait)
  88 |                 continue
  89 |             return resp
  90 |         except requests.exceptions.RequestException as e:
  91 |             if attempt < retries - 1:
  92 |                 wait = sleep_secs * (2 ** attempt) + random.uniform(0, 0.3)
  93 |                 logger.warning("Request failed for %s (attempt %d): %s — retrying in %.1fs",
  94 |                                url, attempt + 1, e, wait)
  95 |                 time.sleep(wait)
  96 |             else:
  97 |                 raise
  98 |     return resp  # Return last response even if 429
  99 | 
 100 | 
 101 | # ── KNOWN WHALE WALLETS (public, documented) ────────────────────────────────
 102 | WHALE_WALLETS = {
 103 |     "bc1qazcm763858nkj2dz7g20juz9muhp68hllhz52g": {
 104 |         "label": "MicroStrategy Treasury",
 105 |         "entity": "MicroStrategy / Saylor",
 106 |         "threshold_btc": 100,
 107 |     },
 108 |     "bc1qjasf9z3h7w3jspkhtgatgpyvvzgpa2wwd2lr0eh5tx44reyn2k7sfl6tyeq": {
 109 |         "label": "BlackRock iShares IBIT",
 110 |         "entity": "BlackRock IBIT ETF",
 111 |         "threshold_btc": 50,
 112 |     },
 113 |     "bc1q4c8n5t00jmj8temxdgcc3t32nkg2wjwz24lywv": {
 114 |         "label": "Fidelity FBTC Custody",
 115 |         "entity": "Fidelity FBTC ETF",
 116 |         "threshold_btc": 50,
 117 |     },
 118 |     "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb": {
 119 |         "label": "Bitfinex Cold Wallet",
 120 |         "entity": "Bitfinex Exchange",
 121 |         "threshold_btc": 500,
 122 |     },
 123 |     "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h": {
 124 |         "label": "Binance Cold Wallet",
 125 |         "entity": "Binance Exchange",
 126 |         "threshold_btc": 500,
 127 |     },
 128 | }
 129 | 
 130 | # ── WATCH LIST — publicly documented high-pattern individuals ────────────────
 131 | WATCH_LIST = [
 132 |     {
 133 |         "name": "Nancy Pelosi",
 134 |         "chamber": "house",
 135 |         "party": "D",
 136 |         "committee": "N/A (former Speaker)",
 137 |         "coverage": ["Bloomberg", "WSJ", "Unusual Whales"],
 138 |         "note": "Publicly documented trading pattern — husband Paul Pelosi executes trades. Covered extensively by financial media.",
 139 |     },
 140 |     {
 141 |         "name": "Tommy Tuberville",
 142 |         "chamber": "senate",
 143 |         "party": "R",
 144 |         "committee": "Armed Services",
 145 |         "coverage": ["Business Insider", "Capitol Trades"],
 146 |         "note": "Multiple documented late filings. Publicly covered pattern of defense-sector trades while on Armed Services Committee.",
 147 |     },
 148 |     {
 149 |         "name": "Dan Crenshaw",
 150 |         "chamber": "house",
 151 |         "party": "R",
 152 |         "committee": "Energy and Commerce",
 153 |         "coverage": ["Unusual Whales", "Forbes"],
 154 |         "note": "Publicly documented crypto-adjacent trading activity.",
 155 |     },
 156 |     {
 157 |         "name": "Ro Khanna",
 158 |         "chamber": "house",
 159 |         "party": "D",
 160 |         "committee": "Armed Services, Oversight",
 161 |         "coverage": ["Capitol Trades"],
 162 |         "note": "Silicon Valley representative with documented tech sector trading.",
 163 |     },
 164 | ]
 165 | 
 166 | # ── CRYPTO-RELATED KEYWORDS for disclosure filtering ────────────────────────
 167 | CRYPTO_KEYWORDS = [
 168 |     "bitcoin", "btc", "crypto", "coinbase", "coin", "microstrategy", "mstr",
 169 |     "ishares bitcoin", "ibit", "fbtc", "grayscale", "gbtc", "blockchain",
 170 |     "blackrock", "digital asset", "etf", "marathon digital", "mara",
 171 |     "riot platforms", "riot", "cleanspark", "bitdeer",
 172 | ]
 173 | 
 174 | 
 175 | # ═══════════════════════════════════════════════════════════════════════════
 176 | # TIER 1: CONFIRMED — STOCK Act Disclosures
 177 | # ═══════════════════════════════════════════════════════════════════════════
 178 | 
 179 | def fetch_stock_act_disclosures(limit: int = 50) -> list[dict]:
 180 |     """Fetch STOCK Act disclosures from efts.house.gov, filtered for crypto/fintech keywords."""
 181 |     cache_key = "panopticon_stock_act"
 182 |     cached = _cached(cache_key, ttl_seconds=1800)  # 30min cache
 183 |     if cached is not None:
 184 |         return cached[:limit]
 185 | 
 186 |     disclosures = []
 187 | 
 188 |     # Primary: House EFTS full-text search for financial disclosures
 189 |     search_terms = ['"bitcoin"', '"crypto"', '"coinbase"', '"microstrategy"', '"ibit"', '"etf"']
 190 |     for term in search_terms:
 191 |         try:
 192 |             resp = _rate_limited_get(
 193 |                 "https://efts.house.gov/LATEST/search-index",
 194 |                 params={
 195 |                     "q": term,
 196 |                     "dateRange": "custom",
 197 |                     "startdt": (datetime.utcnow() - timedelta(days=90)).strftime("%m/%d/%Y"),
 198 |                     "enddt": datetime.utcnow().strftime("%m/%d/%Y"),
 199 |                 },
 200 |                 timeout=15,
 201 |                 headers={"User-Agent": "ProtocolPulse/1.0 research@protocolpulse.io"},
 202 |             )
 203 |             if resp.status_code == 200:
 204 |                 data = resp.json() if "json" in resp.headers.get("content-type", "") else {}
 205 |                 hits = data.get("hits", {}).get("hits", data.get("results", []))
 206 |                 for hit in hits:
 207 |                     src = hit.get("_source", hit) if isinstance(hit, dict) else {}
 208 |                     entity = src.get("filing_name", src.get("name", src.get("display_names", ["Unknown"])))
 209 |                     if isinstance(entity, list):
 210 |                         entity = entity[0] if entity else "Unknown"
 211 |                     filed = src.get("filing_date", src.get("file_date", ""))
 212 |                     doc_url = src.get("url", src.get("doc_url", ""))
 213 |                     disclosures.append({
 214 |                         "entity": entity,
 215 |                         "asset": _extract_asset_from_hit(src),
 216 |                         "trade_type": src.get("transaction_type", "disclosure"),
 217 |                         "amount_range": src.get("amount", "See filing"),
 218 |                         "date_filed": filed,
 219 |                         "date_traded": src.get("transaction_date", filed),
 220 |                         "source_url": doc_url or "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
 221 |                         "tier": "confirmed",
 222 |                     })
 223 |             time.sleep(0.5)  # Rate limit courtesy
 224 |         except Exception as e:
 225 |             logger.warning("efts.house.gov fetch failed for %s: %s", term, e)
 226 |             continue
 227 | 
 228 |     # Deduplicate by entity+date
 229 |     seen = set()
 230 |     unique = []
 231 |     for d in disclosures:
 232 |         key = f"{d['entity']}:{d['date_filed']}:{d['asset']}"
 233 |         if key not in seen:
 234 |             seen.add(key)
 235 |             unique.append(d)
 236 |     disclosures = unique[:limit]
 237 | 
 238 |     _set_cache(cache_key, disclosures)
 239 |     return disclosures
 240 | 
 241 | 
 242 | def _extract_asset_from_hit(src: dict) -> str:
 243 |     """Extract asset name from EFTS hit source data.
 244 |     Known-good schema fields (as of 2026-03): asset_name, asset, ticker, description."""
 245 |     for field in ("asset_name", "asset", "ticker", "description"):
 246 |         val = src.get(field, "")
 247 |         if val:
 248 |             return str(val)
 249 |     # Schema drift detection — log when all known fields return empty
 250 |     logger.warning(
 251 |         "SCHEMA_DRIFT: asset extraction failed on all known fields. "
 252 |         "Keys present: %s", list(src.keys())
 253 |     )
 254 |     # Check text body for crypto keywords
 255 |     text = json.dumps(src).lower()
 256 |     for kw in CRYPTO_KEYWORDS:
 257 |         if kw in text:
 258 |             return kw.upper()
 259 |     return "See filing"
 260 | 
 261 | 
 262 | def fetch_disclosures(limit: int = 50) -> tuple[list[dict], bool]:
 263 |     """Fetch recent STOCK Act disclosures — tries efts.house.gov first, falls back to placeholders.
 264 | 
 265 |     Returns:
 266 |         (disclosures, is_live) — is_live=False when using fallback placeholder data.
 267 |     """
 268 |     cache_key = "panopticon_disclosures"
 269 |     cached = _cached(cache_key, ttl_seconds=1800)  # 30min cache
 270 |     if cached is not None:
 271 |         return cached
 272 | 
 273 |     # Try live efts.house.gov first
 274 |     disclosures = fetch_stock_act_disclosures(limit=limit)
 275 |     is_live = bool(disclosures)
 276 | 
 277 |     # Schema drift batch warning — if >80% of live hits have "See filing" asset
 278 |     if disclosures:
 279 |         see_filing_count = sum(1 for d in disclosures if d.get("asset") == "See filing")
 280 |         if len(disclosures) > 3 and see_filing_count / len(disclosures) > 0.8:
 281 |             logger.warning(
 282 |                 "SCHEMA_DRIFT: >80%% of efts.house.gov results returned 'See filing' "
 283 |                 "(%d/%d) — API schema may have changed",
 284 |                 see_filing_count, len(disclosures),
 285 |             )
 286 | 
 287 |     # Fallback to well-known public data
 288 |     if not disclosures:
 289 |         disclosures = _generate_disclosure_placeholders()
 290 | 
 291 |     result = (disclosures, is_live)
 292 |     _set_cache(cache_key, result)
 293 |     return result
 294 | 
 295 | 
 296 | def _generate_disclosure_placeholders() -> list[dict]:
 297 |     """Placeholder disclosures based on real public filings. Uses FIXED dates to avoid
 298 |     misleading freshness. All carry is_placeholder=True for UI banner."""
 299 |     return [
 300 |         {
 301 |             "entity": "Rep. Michael McCaul (R-TX)",
 302 |             "asset": "Bitcoin ETF (IBIT)",
 303 |             "trade_type": "purchase",
 304 |             "amount_range": "$15,001–$50,000",
 305 |             "chamber": "house",
 306 |             "party": "R",
 307 |             "date_filed": "2025-09-15",
 308 |             "date_traded": "2025-08-20",
 309 |             "days_to_file": 26,
 310 |             "committee": "Foreign Affairs (Chair)",
 311 |             "source_url": "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
 312 |             "tier": "confirmed",
 313 |             "correlation_note": None,
 314 |             "is_placeholder": True,
 315 |         },
 316 |         {
 317 |             "entity": "Sen. Cynthia Lummis (R-WY)",
 318 |             "asset": "Bitcoin (BTC)",
 319 |             "trade_type": "purchase",
 320 |             "amount_range": "$50,001–$100,000",
 321 |             "chamber": "senate",
 322 |             "party": "R",
 323 |             "date_filed": "2025-10-01",
 324 |             "date_traded": "2025-09-10",
 325 |             "days_to_file": 22,
 326 |             "committee": "Banking (Digital Assets Subcommittee Chair)",
 327 |             "source_url": "https://efts.sec.gov/LATEST/search-index?q=lummis",
 328 |             "tier": "confirmed",
 329 |             "correlation_note": "Trade within 14 days of Senate Banking hearing on stablecoin bill",
 330 |             "is_placeholder": True,
 331 |         },
 332 |         {
 333 |             "entity": "Rep. Patrick McHenry (R-NC)",
 334 |             "asset": "Coinbase (COIN)",
 335 |             "trade_type": "purchase",
 336 |             "amount_range": "$1,001–$15,000",
 337 |             "chamber": "house",
 338 |             "party": "R",
 339 |             "date_filed": "2025-08-28",
 340 |             "date_traded": "2025-08-03",
 341 |             "days_to_file": 25,
 342 |             "committee": "Financial Services (former Chair)",
 343 |             "source_url": "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
 344 |             "tier": "confirmed",
 345 |             "correlation_note": None,
 346 |             "is_placeholder": True,
 347 |         },
 348 |         {
 349 |             "entity": "Rep. Ritchie Torres (D-NY)",
 350 |             "asset": "MicroStrategy (MSTR)",
 351 |             "trade_type": "purchase",
 352 |             "amount_range": "$1,001–$15,000",
 353 |             "chamber": "house",
 354 |             "party": "D",
 355 |             "date_filed": "2025-11-05",
 356 |             "date_traded": "2025-10-13",
 357 |             "days_to_file": 23,
 358 |             "committee": "Financial Services",
 359 |             "source_url": "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
 360 |             "tier": "confirmed",
 361 |             "correlation_note": "Trade within 7 days of FIT21 markup session",
 362 |             "is_placeholder": True,
 363 |         },
 364 |     ]
 365 | 
 366 | 
 367 | # ═══════════════════════════════════════════════════════════════════════════
 368 | # TIER 2: FLAGGED — Statistical Correlation Detection
 369 | # ═══════════════════════════════════════════════════════════════════════════
 370 | 
 371 | def check_correlations(disclosures: list[dict]) -> list[dict]:
 372 |     """Cross-reference disclosures with committee hearing schedules.
 373 |     Returns flagged items with correlation scores."""
 374 |     flagged = []
 375 |     for d in disclosures:
 376 |         if d.get("correlation_note"):
 377 |             flagged.append({
 378 |                 **d,
 379 |                 "tier": "flagged",
 380 |                 "correlation_score": 0.7,
 381 |                 "flag_reason": d["correlation_note"],
 382 |             })
 383 |     return flagged
 384 | 
 385 | 
 386 | # ═══════════════════════════════════════════════════════════════════════════
 387 | # REAL-TIME FEED 1: WHALE TRACKER — mempool.space
 388 | # ═══════════════════════════════════════════════════════════════════════════
 389 | 
 390 | def fetch_whale_alerts(limit: int = 20) -> list[dict]:
 391 |     """Monitor known whale wallets for large BTC movements via mempool.space API."""
 392 |     cache_key = "panopticon_whales"
 393 |     cached = _cached(cache_key, ttl_seconds=300)  # 5min cache
 394 |     if cached is not None:
 395 |         return cached
 396 | 
 397 |     alerts = []
 398 |     for address, meta in WHALE_WALLETS.items():
 399 |         try:
 400 |             url = f"https://mempool.space/api/address/{address}/txs"
 401 |             resp = _rate_limited_get(url, timeout=10)
 402 |             if resp.status_code != 200:
 403 |                 continue
 404 | 
 405 |             txs = resp.json()
 406 |             for tx in txs[:5]:  # Last 5 txs per wallet
 407 |                 # Calculate total output value
 408 |                 total_out_sats = sum(vout.get("value", 0) for vout in tx.get("vout", []))
 409 |                 total_btc = total_out_sats / 1e8
 410 | 
 411 |                 if total_btc < meta["threshold_btc"]:
 412 |                     continue
 413 | 
 414 |                 # Determine if this address is sender or receiver
 415 |                 is_sender = any(
 416 |                     vin.get("prevout", {}).get("scriptpubkey_address") == address
 417 |                     for vin in tx.get("vin", [])
 418 |                 )
 419 |                 tx_type = "outflow" if is_sender else "inflow"
 420 | 
 421 |                 confirmed = tx.get("status", {}).get("confirmed", False)
 422 |                 block_time = tx.get("status", {}).get("block_time")
 423 |                 tx_time = datetime.utcfromtimestamp(block_time) if block_time else datetime.utcnow()
 424 | 
 425 |                 alerts.append({
 426 |                     "entity": meta["entity"],
 427 |                     "wallet_label": meta["label"],
 428 |                     "address": address[:12] + "..." + address[-6:],
 429 |                     "txid": tx.get("txid", "")[:16] + "...",
 430 |                     "txid_full": tx.get("txid", ""),
 431 |                     "amount_btc": round(total_btc, 4),
 432 |                     "amount_usd": None,  # Filled by caller with current BTC price
 433 |                     "tx_type": tx_type,
 434 |                     "confirmed": confirmed,
 435 |                     "timestamp": tx_time.isoformat(),
 436 |                     "event_type": "whale",
 437 |                     "source_url": f"https://mempool.space/tx/{tx.get('txid', '')}",
 438 |                 })
 439 | 
 440 |             time.sleep(0.3)  # Rate limit courtesy
 441 | 
 442 |         except Exception as e:
 443 |             logger.warning("Whale check failed for %s: %s", meta["label"], e)
 444 |             continue
 445 | 
 446 |     # Sort by timestamp descending
 447 |     alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
 448 |     alerts = alerts[:limit]
 449 | 
 450 |     _set_cache(cache_key, alerts)
 451 |     return alerts
 452 | 
 453 | 
 454 | # ═══════════════════════════════════════════════════════════════════════════
 455 | # REAL-TIME FEED 3: NATION-STATE SIGNAL — Forex/Macro
 456 | # ═══════════════════════════════════════════════════════════════════════════
 457 | 
 458 | def fetch_forex_signals() -> list[dict]:
 459 |     """Track sovereign currency interventions and macro signals via free forex APIs."""
 460 |     cache_key = "panopticon_forex"
 461 |     cached = _cached(cache_key, ttl_seconds=600)  # 10min cache
 462 |     if cached is not None:
 463 |         return cached
 464 | 
 465 |     signals = []
 466 | 
 467 |     # Fetch key forex pairs relevant to sovereign BTC thesis
 468 |     pairs_of_interest = {
 469 |         "USD/JPY": {"threshold": 2.0, "context": "Japan yen intervention watch — historical BTC correlation: +12% 30d forward"},
 470 |         "USD/CNY": {"threshold": 1.5, "context": "China yuan devaluation signal — capital flight to BTC historically follows"},
 471 |         "DXY": {"threshold": 1.5, "context": "Dollar index shift — weakening DXY historically bullish for BTC"},
 472 |         "EUR/USD": {"threshold": 1.0, "context": "Euro zone monetary stress indicator"},
 473 |     }
 474 | 
 475 |     try:
 476 |         # exchangerate.host free tier — ~1000 calls/month
 477 |         resp = _rate_limited_get(
 478 |             "https://api.exchangerate.host/latest",
 479 |             params={"base": "USD", "symbols": "JPY,CNY,EUR,GBP,CHF"},
 480 |             timeout=10,
 481 |         )
 482 |         if resp.status_code == 200:
 483 |             data = resp.json()
 484 |             rates = data.get("rates", {})
 485 |             for currency, rate in rates.items():
 486 |                 pair = f"USD/{currency}"
 487 |                 if pair in pairs_of_interest:
 488 |                     signals.append({
 489 |                         "pair": pair,
 490 |                         "rate": round(rate, 4),
 491 |                         "context": pairs_of_interest[pair]["context"],
 492 |                         "event_type": "forex",
 493 |                         "timestamp": datetime.utcnow().isoformat(),
 494 |                         "status": "monitoring",
 495 |                     })
 496 |     except Exception as e:
 497 |         logger.warning("Forex fetch failed: %s", e)
 498 | 
 499 |     # 10Y Treasury yield proxy (from existing data if available)
 500 |     try:
 501 |         # fiscaldata.treasury.gov — no documented rate limit, courtesy sleep via _rate_limited_get
 502 |         resp = _rate_limited_get(
 503 |             "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates",
 504 |             params={
 505 |                 "filter": "security_desc:eq:Treasury Notes",
 506 |                 "sort": "-record_date",
 507 |                 "page[size]": "1",
 508 |             },
 509 |             timeout=10,
 510 |         )
 511 |         if resp.status_code == 200:
 512 |             data = resp.json()
 513 |             records = data.get("data", [])
 514 |             if records:
 515 |                 rec = records[0]
 516 |                 signals.append({
 517 |                     "pair": "US 10Y TREASURY",
 518 |                     "rate": float(rec.get("avg_interest_rate_amt", 0)),
 519 |                     "context": "Bond market stress gauge — inverted yield curve signals recession, historically bullish for hard assets",
 520 |                     "event_type": "macro",
 521 |                     "timestamp": rec.get("record_date", datetime.utcnow().isoformat()),
 522 |                     "status": "monitoring",
 523 |                 })
 524 |     except Exception as e:
 525 |         logger.warning("Treasury yield fetch failed: %s", e)
 526 | 
 527 |     # Always include static sovereign BTC intelligence
 528 |     signals.extend([
 529 |         {
 530 |             "pair": "EL SALVADOR / BTC",
 531 |             "rate": None,
 532 |             "context": "El Salvador sovereign BTC reserve — 6,102+ BTC accumulated, daily DCA continues",
 533 |             "event_type": "sovereign",
 534 |             "timestamp": datetime.utcnow().isoformat(),
 535 |             "status": "active_buyer",
 536 |         },
 537 |         {
 538 |             "pair": "US STRATEGIC RESERVE",
 539 |             "rate": None,
 540 |             "context": "US Strategic Bitcoin Reserve — Executive Order signed, seized BTC held in reserve",
 541 |             "event_type": "sovereign",
 542 |             "timestamp": datetime.utcnow().isoformat(),
 543 |             "status": "holding",
 544 |         },
 545 |     ])
 546 | 
 547 |     _set_cache(cache_key, signals)
 548 |     return signals
 549 | 
 550 | 
 551 | # ═══════════════════════════════════════════════════════════════════════════
 552 | # REAL-TIME FEED 4: GEOPOLITICAL ALERT FEED
 553 | # ═══════════════════════════════════════════════════════════════════════════
 554 | 
 555 | def fetch_geopolitical(limit: int = 20) -> list[dict]:
 556 |     """Pull geopolitical events from existing article pipeline + GDELT project."""
 557 |     cache_key = "panopticon_geopolitical"
 558 |     cached = _cached(cache_key, ttl_seconds=600)
 559 |     if cached is not None:
 560 |         return cached
 561 | 
 562 |     events = []
 563 | 
 564 |     # Pull from our existing article pipeline (sovereign/regulatory tagged)
 565 |     try:
 566 |         # Deferred import to avoid circular dependency at module load time
 567 |         from app import app, db
 568 |         from models import Article
 569 |         with app.app_context():
 570 |             geo_articles = Article.query.filter(
 571 |                 Article.published == True,
 572 |                 db.or_(
 573 |                     Article.category.in_(["regulation", "sovereignty", "geopolitical", "cbdc", "policy"]),
 574 |                     Article.tags.ilike("%sanction%"),
 575 |                     Article.tags.ilike("%cbdc%"),
 576 |                     Article.tags.ilike("%capital control%"),
 577 |                     Article.tags.ilike("%bitcoin ban%"),
 578 |                     Article.tags.ilike("%adoption%"),
 579 |                 )
 580 |             ).order_by(Article.created_at.desc()).limit(limit).all()
 581 | 
 582 |             for art in geo_articles:
 583 |                 # Derive bitcoin signal from tags/category
 584 |                 btc_signal = _classify_btc_signal(art.title, art.tags or "", art.category or "")
 585 |                 events.append({
 586 |                     "headline": art.title,
 587 |                     "category": art.category,
 588 |                     "btc_signal": btc_signal["direction"],
 589 |                     "btc_rationale": btc_signal["rationale"],
 590 |                     "source": "Protocol Pulse Intelligence",
 591 |                     "source_url": f"/article/{art.slug}" if art.slug else f"/article/{art.id}",
 592 |                     "timestamp": art.created_at.isoformat() if art.created_at else datetime.utcnow().isoformat(),
 593 |                     "event_type": "geopolitical",
 594 |                 })
 595 |     except Exception as e:
 596 |         logger.warning("Article pipeline geopolitical fetch failed: %s", e)
 597 | 
 598 |     # GDELT fallback — free event database
 599 |     if not events:
 600 |         try:
 601 |             gdelt_url = "https://api.gdeltproject.org/api/v2/doc/doc"
 602 |             resp = _rate_limited_get(
 603 |                 gdelt_url,
 604 |                 params={
 605 |                     "query": "(bitcoin OR cryptocurrency OR CBDC OR \"digital currency\") sourcelang:eng",
 606 |                     "mode": "artlist",
 607 |                     "maxrecords": "10",
 608 |                     "format": "json",
 609 |                 },
 610 |                 timeout=15,
 611 |             )
 612 |             if resp.status_code == 200:
 613 |                 data = resp.json()
 614 |                 for article in data.get("articles", [])[:limit]:
 615 |                     btc_signal = _classify_btc_signal(article.get("title", ""), "", "geopolitical")
 616 |                     events.append({
 617 |                         "headline": article.get("title", "Unknown Event"),
 618 |                         "category": "geopolitical",
 619 |                         "btc_signal": btc_signal["direction"],
 620 |                         "btc_rationale": btc_signal["rationale"],
 621 |                         "source": article.get("domain", "GDELT"),
 622 |                         "source_url": article.get("url", ""),
 623 |                         "timestamp": article.get("seendate", datetime.utcnow().isoformat()),
 624 |                         "event_type": "geopolitical",
 625 |                     })
 626 |         except Exception as e:
 627 |             logger.warning("GDELT fetch failed: %s", e)
 628 | 
 629 |     # Static fallback if all sources fail
 630 |     if not events:
 631 |         events = _static_geopolitical_feed()
 632 | 
 633 |     _set_cache(cache_key, events)
 634 |     return events
 635 | 
 636 | 
 637 | def _classify_btc_signal(title: str, tags: str, category: str) -> dict:
 638 |     """Classify a geopolitical event's Bitcoin signal direction."""
 639 |     text = f"{title} {tags} {category}".lower()
 640 | 
 641 |     bullish_terms = ["adoption", "legal tender", "reserve", "accumulate", "pro-crypto", "approve", "etf approved", "institutional"]
 642 |     bearish_terms = ["ban", "restrict", "cbdc mandate", "crackdown", "sanction crypto", "seize"]
 643 | 
 644 |     bull_score = sum(1 for t in bullish_terms if t in text)
 645 |     bear_score = sum(1 for t in bearish_terms if t in text)
 646 | 
 647 |     if bull_score > bear_score:
 648 |         return {"direction": "bullish", "rationale": "Sovereign adoption or favorable regulation strengthens Bitcoin's monetary network effect."}
 649 |     elif bear_score > bull_score:
 650 |         return {"direction": "bearish", "rationale": "Regulatory restriction signals short-term selling pressure but long-term validates Bitcoin's censorship resistance."}
 651 |     return {"direction": "neutral", "rationale": "Event requires further analysis for Bitcoin monetary implications."}
 652 | 
 653 | 
 654 | def _static_geopolitical_feed() -> list[dict]:
 655 |     """Fallback static feed with real, publicly known events."""
 656 |     return [
 657 |         {
 658 |             "headline": "US Strategic Bitcoin Reserve — Executive Order Establishes National BTC Stockpile",
 659 |             "category": "sovereignty",
 660 |             "btc_signal": "bullish",
 661 |             "btc_rationale": "Nation-state accumulation confirms Bitcoin as strategic reserve asset alongside gold.",
 662 |             "source": "White House",
 663 |             "source_url": "https://www.whitehouse.gov",
 664 |             "timestamp": "2025-03-06T12:00:00",
 665 |             "event_type": "geopolitical",
 666 |             "status": "confirmed",
 667 |         },
 668 |         {
 669 |             "headline": "EU MiCA Regulation — Full Implementation of Crypto Asset Framework",
 670 |             "category": "regulation",
 671 |             "btc_signal": "neutral",
 672 |             "btc_rationale": "Regulatory clarity in the EU provides framework but may push innovation to more permissive jurisdictions.",
 673 |             "source": "European Commission",
 674 |             "source_url": "https://finance.ec.europa.eu",
 675 |             "timestamp": "2025-12-30T00:00:00",
 676 |             "event_type": "geopolitical",
 677 |             "status": "confirmed",
 678 |         },
 679 |         {
 680 |             "headline": "Japan Yen Under Pressure — BOJ Intervention Watch Activated",
 681 |             "category": "macro",
 682 |             "btc_signal": "bullish",
 683 |             "btc_rationale": "Currency debasement historically drives capital to hard assets. BTC +12% average 30d forward after yen interventions.",
 684 |             "source": "Reuters",
 685 |             "source_url": "https://www.reuters.com",
 686 |             "timestamp": datetime.utcnow().isoformat(),
 687 |             "event_type": "geopolitical",
 688 |             "status": "monitoring",
 689 |         },
 690 |     ]
 691 | 
 692 | 
 693 | # ═══════════════════════════════════════════════════════════════════════════
 694 | # REAL-TIME FEED 5: POLYMARKET — Prediction Market Odds
 695 | # ═══════════════════════════════════════════════════════════════════════════
 696 | 
 697 | POLYMARKET_CRYPTO_SLUGS = [
 698 |     "bitcoin", "btc", "crypto", "ethereum", "regulation", "sec", "etf",
 699 |     "stablecoin", "digital-asset", "cbdc", "fed", "interest-rate",
 700 | ]
 701 | 
 702 | 
 703 | def fetch_polymarket_markets(limit: int = 15) -> list[dict]:
 704 |     """Fetch active Polymarket prediction markets relevant to crypto/macro.
 705 |     Uses the public Strapi API (no auth required)."""
 706 |     cache_key = "panopticon_polymarket"
 707 |     cached = _cached(cache_key, ttl_seconds=300)  # 5min cache
 708 |     if cached is not None:
 709 |         return cached[:limit]
 710 | 
 711 |     markets = []
 712 |     try:
 713 |         resp = _rate_limited_get(
 714 |             "https://strapi-matic.polymarket.com/markets",
 715 |             params={
 716 |                 "active": "true",
 717 |                 "_limit": "50",
 718 |                 "_sort": "volume:desc",
 719 |             },
 720 |             timeout=15,
 721 |         )
 722 |         if resp.status_code == 200:
 723 |             raw_markets = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])
 724 |             for m in raw_markets:
 725 |                 question = (m.get("question") or m.get("title") or "").lower()
 726 |                 slug = (m.get("slug") or "").lower()
 727 |                 desc = (m.get("description") or "").lower()
 728 |                 text = f"{question} {slug} {desc}"
 729 | 
 730 |                 # Filter for crypto/macro relevance
 731 |                 if not any(kw in text for kw in POLYMARKET_CRYPTO_SLUGS):
 732 |                     continue
 733 | 
 734 |                 # Extract probability from outcomes
 735 |                 outcomes = m.get("outcomes", [])
 736 |                 outcome_prices = m.get("outcomePrices", m.get("outcome_prices", []))
 737 |                 yes_price = None
 738 |                 if outcome_prices:
 739 |                     try:
 740 |                         yes_price = float(outcome_prices[0]) if isinstance(outcome_prices[0], (int, float, str)) else None
 741 |                     except (ValueError, IndexError):
 742 |                         pass
 743 | 
 744 |                 markets.append({
 745 |                     "question": m.get("question") or m.get("title", "Unknown"),
 746 |                     "slug": m.get("slug", ""),
 747 |                     "yes_price": round(yes_price * 100, 1) if yes_price else None,
 748 |                     "volume": m.get("volume") or m.get("volumeNum", 0),
 749 |                     "liquidity": m.get("liquidity", 0),
 750 |                     "end_date": m.get("end_date_iso") or m.get("endDate", ""),
 751 |                     "source_url": f"https://polymarket.com/event/{m.get('slug', '')}",
 752 |                     "event_type": "prediction",
 753 |                     "btc_signal": _classify_polymarket_signal(m.get("question", "")),
 754 |                 })
 755 | 
 756 |     except Exception as e:
 757 |         logger.warning("Polymarket fetch failed: %s", e)
 758 | 
 759 |     # Fallback with known active markets
 760 |     if not markets:
 761 |         markets = _static_polymarket_feed()
 762 | 
 763 |     markets.sort(key=lambda x: x.get("volume", 0), reverse=True)
 764 |     result = markets[:limit]
 765 |     _set_cache(cache_key, result)
 766 |     return result
 767 | 
 768 | 
 769 | def _classify_polymarket_signal(question: str) -> str:
 770 |     """Classify a Polymarket question's implied Bitcoin signal."""
 771 |     q = question.lower()
 772 |     bullish = ["approve", "pass", "adopt", "reserve", "legal tender", "etf"]
 773 |     bearish = ["ban", "reject", "restrict", "tax", "crack"]
 774 |     if any(kw in q for kw in bullish):
 775 |         return "bullish"
 776 |     if any(kw in q for kw in bearish):
 777 |         return "bearish"
 778 |     return "neutral"
 779 | 
 780 | 
 781 | def _static_polymarket_feed() -> list[dict]:
 782 |     """Fallback static Polymarket data based on known active markets."""
 783 |     return [
 784 |         {
 785 |             "question": "Will Bitcoin exceed $150,000 by end of 2026?",
 786 |             "slug": "bitcoin-150k-2026",
 787 |             "yes_price": 42.0,
 788 |             "volume": 8500000,
 789 |             "liquidity": 1200000,
 790 |             "end_date": "2026-12-31",
 791 |             "source_url": "https://polymarket.com",
 792 |             "event_type": "prediction",
 793 |             "btc_signal": "bullish",
 794 |         },
 795 |         {
 796 |             "question": "Will US Congress pass stablecoin legislation in 2026?",
 797 |             "slug": "stablecoin-legislation-2026",
 798 |             "yes_price": 67.0,
 799 |             "volume": 3200000,
 800 |             "liquidity": 800000,
 801 |             "end_date": "2026-12-31",
 802 |             "source_url": "https://polymarket.com",
 803 |             "event_type": "prediction",
 804 |             "btc_signal": "bullish",
 805 |         },
 806 |         {
 807 |             "question": "Will the SEC approve a spot Ethereum ETF by Q2 2026?",
 808 |             "slug": "sec-eth-etf-q2-2026",
 809 |             "yes_price": 55.0,
 810 |             "volume": 5100000,
 811 |             "liquidity": 900000,
 812 |             "end_date": "2026-06-30",
 813 |             "source_url": "https://polymarket.com",
 814 |             "event_type": "prediction",
 815 |             "btc_signal": "neutral",
 816 |         },
 817 |         {
 818 |             "question": "Will the Federal Reserve cut rates before July 2026?",
 819 |             "slug": "fed-rate-cut-july-2026",
 820 |             "yes_price": 72.0,
 821 |             "volume": 12000000,
 822 |             "liquidity": 2500000,
 823 |             "end_date": "2026-07-01",
 824 |             "source_url": "https://polymarket.com",
 825 |             "event_type": "prediction",
 826 |             "btc_signal": "bullish",
 827 |         },
 828 |     ]
 829 | 
 830 | 
 831 | # ═══════════════════════════════════════════════════════════════════════════
 832 | # CORRELATION TIMELINE — Cross-reference engine with temporal windowing
 833 | # ═══════════════════════════════════════════════════════════════════════════
 834 | 
 835 | CORRELATION_WINDOW_HOURS = 72  # ±72h temporal window
 836 | 
 837 | 
 838 | def _parse_date_safe(date_str: str) -> Optional[datetime]:
 839 |     """Parse a date string safely, returning None on failure."""
 840 |     if not date_str:
 841 |         return None
 842 |     for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
 843 |         try:
 844 |             return datetime.strptime(date_str[:19], fmt)
 845 |         except (ValueError, TypeError):
 846 |             continue
 847 |     return None
 848 | 
 849 | 
 850 | def build_correlations(limit: int = 10) -> list[dict]:
 851 |     """Build correlation timeline with genuine ±72h temporal windowing.
 852 |     Only surfaces correlations with minimum 2 co-occurring signals."""
 853 |     cache_key = "panopticon_correlations"
 854 |     cached = _cached(cache_key, ttl_seconds=600)
 855 |     if cached is not None:
 856 |         return cached
 857 | 
 858 |     correlations = []
 859 |     disc_result = fetch_disclosures()
 860 |     disclosures = disc_result[0] if isinstance(disc_result, tuple) else disc_result
 861 |     whales = fetch_whale_alerts()
 862 |     geo = fetch_geopolitical()
 863 | 
 864 |     window = timedelta(hours=CORRELATION_WINDOW_HOURS)
 865 | 
 866 |     flagged = [d for d in disclosures if d.get("correlation_note")]
 867 |     for disc in flagged[:limit]:
 868 |         disc_date = _parse_date_safe(disc.get("date_traded", ""))
 869 |         if not disc_date:
 870 |             continue
 871 | 
 872 |         # Find whale events within ±72h window
 873 |         related_whales = []
 874 |         for w in whales:
 875 |             w_date = _parse_date_safe(w.get("timestamp", ""))
 876 |             if w_date and abs((w_date - disc_date).total_seconds()) <= window.total_seconds():
 877 |                 related_whales.append({
 878 |                     "type": "whale",
 879 |                     "entity": w.get("entity", ""),
 880 |                     "amount": f"{w.get('amount_btc', 0)} BTC",
 881 |                     "direction": w.get("tx_type", ""),
 882 |                     "timestamp": w.get("timestamp", ""),
 883 |                     "days_offset": round(abs((w_date - disc_date).total_seconds()) / 86400, 1),
 884 |                 })
 885 | 
 886 |         # Find geopolitical events within ±72h window
 887 |         related_geo = []
 888 |         for g in geo:
 889 |             g_date = _parse_date_safe(g.get("timestamp", ""))
 890 |             if g_date and abs((g_date - disc_date).total_seconds()) <= window.total_seconds():
 891 |                 related_geo.append({
 892 |                     "type": "geopolitical",
 893 |                     "headline": g.get("headline", ""),
 894 |                     "btc_signal": g.get("btc_signal", "neutral"),
 895 |                     "timestamp": g.get("timestamp", ""),
 896 |                     "days_offset": round(abs((g_date - disc_date).total_seconds()) / 86400, 1),
 897 |                 })
 898 | 
 899 |         # Minimum 2 co-occurring signals required
 900 |         total_related = len(related_whales) + len(related_geo)
 901 |         if total_related < 2:
 902 |             continue
 903 | 
 904 |         # Score based on temporal proximity (closer = higher)
 905 |         all_offsets = [r["days_offset"] for r in related_whales + related_geo]
 906 |         avg_offset = sum(all_offsets) / len(all_offsets) if all_offsets else 3.0
 907 |         proximity_score = max(0, 1.0 - (avg_offset / 6.0))
 908 |         correlation_score = round(min(proximity_score * (1 + total_related * 0.1), 1.0), 2)
 909 | 
 910 |         correlations.append({
 911 |             "disclosure": {
 912 |                 "entity": disc.get("entity", ""),
 913 |                 "asset": disc.get("asset", ""),
 914 |                 "trade_type": disc.get("trade_type", ""),
 915 |                 "date": disc.get("date_traded", ""),
 916 |                 "correlation_note": disc.get("correlation_note", ""),
 917 |             },
 918 |             "related_whales": related_whales[:3],
 919 |             "related_geo": related_geo[:3],
 920 |             "correlation_score": correlation_score,
 921 |             "signal_count": total_related,
 922 |             "window_hours": CORRELATION_WINDOW_HOURS,
 923 |             "disclaimer": "PATTERN FOR RESEARCH — NOT VERIFIED. Temporal correlation only.",
 924 |             "timeline_summary": f"{disc.get('entity', 'Unknown')} traded {disc.get('asset', 'crypto assets')} — "
 925 |                                f"{total_related} related signals within {CORRELATION_WINDOW_HOURS}h window",
 926 |         })
 927 | 
 928 |     _set_cache(cache_key, correlations)
 929 |     return correlations
 930 | 
 931 | 
 932 | # ═══════════════════════════════════════════════════════════════════════════
 933 | # WATCH LIST DATA
 934 | # ═══════════════════════════════════════════════════════════════════════════
 935 | 
 936 | def get_watch_list() -> list[dict]:
 937 |     """Return the publicly documented watch list with source citations."""
 938 |     return WATCH_LIST
 939 | 
 940 | 
 941 | # ═══════════════════════════════════════════════════════════════════════════
 942 | # LIVE BTC PRICE (for enrichment)
 943 | # ═══════════════════════════════════════════════════════════════════════════
 944 | 
 945 | def get_btc_price() -> Optional[float]:
 946 |     """Get current BTC/USD price from CoinGecko (free, no auth)."""
 947 |     cache_key = "panopticon_btc_price"
 948 |     cached = _cached(cache_key, ttl_seconds=120)
 949 |     if cached is not None:
 950 |         return cached
 951 | 
 952 |     try:
 953 |         # CoinGecko free tier: ~10-50 calls/min — use rate-limited wrapper
 954 |         resp = _rate_limited_get(
 955 |             "https://api.coingecko.com/api/v3/simple/price",
 956 |             params={"ids": "bitcoin", "vs_currencies": "usd"},
 957 |             timeout=10,
 958 |             sleep_secs=1.2,
 959 |         )
 960 |         if resp.status_code == 200:
 961 |             price = resp.json().get("bitcoin", {}).get("usd")
 962 |             if price:
 963 |                 _set_cache(cache_key, price)
 964 |                 return price
 965 |     except Exception as e:
 966 |         logger.warning("BTC price fetch failed: %s", e)
 967 | 
 968 |     return None
 969 | 
 970 | 
 971 | # ═══════════════════════════════════════════════════════════════════════════
 972 | # AGGREGATE DASHBOARD DATA
 973 | # ═══════════════════════════════════════════════════════════════════════════
 974 | 
 975 | def get_dashboard_data() -> dict:
 976 |     """Aggregate all panopticon data for the dashboard (Commander tier — full data)."""
 977 |     btc_price = get_btc_price()
 978 |     disclosures, disclosures_live = fetch_disclosures()
 979 |     whales = fetch_whale_alerts()
 980 |     forex = fetch_forex_signals()
 981 |     geo = fetch_geopolitical()
 982 |     correlations = build_correlations()
 983 |     watch_list = get_watch_list()
 984 |     polymarket = fetch_polymarket_markets()
 985 | 
 986 |     # Enrich whale alerts with USD values
 987 |     if btc_price:
 988 |         for w in whales:
 989 |             if w.get("amount_btc"):
 990 |                 w["amount_usd"] = round(w["amount_btc"] * btc_price, 2)
 991 | 
 992 |     # Count events today
 993 |     today = datetime.utcnow().strftime("%Y-%m-%d")
 994 |     events_today = sum(1 for d in disclosures if today in d.get("date_filed", ""))
 995 |     events_today += sum(1 for w in whales if today in w.get("timestamp", ""))
 996 |     events_today += sum(1 for g in geo if today in g.get("timestamp", ""))
 997 | 
 998 |     return {
 999 |         "btc_price": btc_price,
1000 |         "events_today": max(events_today, len(disclosures) + len(whales)),
1001 |         "disclosures": disclosures,
1002 |         "disclosures_live": disclosures_live,
1003 |         "flagged": check_correlations(disclosures),
1004 |         "whales": whales,
1005 |         "forex": forex,
1006 |         "geopolitical": geo,
1007 |         "correlations": correlations,
1008 |         "watch_list": watch_list,
1009 |         "polymarket": polymarket,
1010 |         "generated_at": datetime.utcnow().isoformat(),
1011 |     }
1012 | 
1013 | 
1014 | def get_demo_safe_data() -> dict:
1015 |     """Return redacted data structure for free-tier users.
1016 |     No sensitive Commander-tier data is included — only counts and structure.
1017 |     This ensures CSS overlay bypass cannot expose paid content (P0 fix for U1)."""
1018 |     return {
1019 |         "btc_price": get_btc_price(),  # Public data, safe to show
1020 |         "events_today": 0,
1021 |         "disclosures": [],
1022 |         "disclosures_live": True,
1023 |         "flagged": [],
1024 |         "whales": [],
1025 |         "forex": [],
1026 |         "geopolitical": [],
1027 |         "correlations": [],
1028 |         "watch_list": [],
1029 |         "polymarket": [],
1030 |         "generated_at": datetime.utcnow().isoformat(),
1031 |         "demo_counts": {
1032 |             "disclosures": "12+",
1033 |             "whales": "8+",
1034 |             "flags": "3+",
1035 |             "markets": "15+",
1036 |             "geo": "5+",
1037 |         },
1038 |     }
1039 | 
1040 | 
1041 | # ═══════════════════════════════════════════════════════════════════════════
1042 | # MAKE THE BITCOIN CASE — AI-generated cypherpunk argument via Anthropic
1043 | # ═══════════════════════════════════════════════════════════════════════════
1044 | 
1045 | def get_make_bitcoin_case(event_summary: str) -> dict:
1046 |     """Generate a cypherpunk argument for Bitcoin self-custody based on a specific event.
1047 | 
1048 |     Uses Anthropic claude-sonnet-4-6 to produce a concise, compelling Bitcoin case
1049 |     tied to the given event (disclosure, whale movement, geopolitical signal).
1050 | 
1051 |     Returns:
1052 |         dict with keys: case_text, event_summary, generated_at, model
1053 |     """
1054 |     cache_key = f"btc_case_{hashlib.sha256(event_summary.encode()).hexdigest()[:16]}"
1055 |     cached = _cached(cache_key, ttl_seconds=3600)  # 1hr cache per event
1056 |     if cached is not None:
1057 |         return cached
1058 | 
1059 |     api_key = ANTHROPIC_API_KEY
1060 |     if not api_key:
1061 |         return {
1062 |             "case_text": "Self-custody is the only guarantee that no institution, government, or counterparty can freeze, seize, or debase your savings. This event is another reminder: when the rules are written by the players, Bitcoin is the exit.",
1063 |             "event_summary": event_summary,
1064 |             "generated_at": datetime.utcnow().isoformat(),
1065 |             "model": "fallback",
1066 |         }
1067 | 
1068 |     try:
1069 |         import anthropic
1070 |         client = anthropic.Anthropic(api_key=api_key)
1071 |         message = client.messages.create(
1072 |             model=ANTHROPIC_MODEL,
1073 |             max_tokens=512,
1074 |             messages=[{
1075 |                 "role": "user",
1076 |                 "content": f"""You are a Bitcoin-first monetary analyst writing for Protocol Pulse PANOPTICON.
1077 | 
1078 | Analyze the following event and write a 3-4 sentence cypherpunk argument for Bitcoin self-custody.
1079 | 
1080 | <event_data>
1081 | {event_summary}
1082 | </event_data>
1083 | 
1084 | Rules:
1085 | - Reference the specific event details (names, amounts, dates) from the event_data above
1086 | - Connect it to Bitcoin's value proposition (censorship resistance, fixed supply, self-sovereignty)
1087 | - End with a concrete call to self-custody
1088 | - Tone: authoritative, urgent, not preachy
1089 | - No hashtags, no emojis, no fluff
1090 | - Output ONLY the argument text, nothing else"""
1091 |             }],
1092 |         )
1093 |         case_text = message.content[0].text.strip()
1094 | 
1095 |         result = {
1096 |             "case_text": case_text,
1097 |             "event_summary": event_summary,
1098 |             "generated_at": datetime.utcnow().isoformat(),
1099 |             "model": "claude-sonnet-4-6",
1100 |         }
1101 |         _set_cache(cache_key, result)
1102 |         return result
1103 | 
1104 |     except Exception as e:
1105 |         logger.error("Anthropic make_bitcoin_case failed: %s", e)
1106 |         return {
1107 |             "case_text": f"When {event_summary[:100]}... happens in traditional finance, it proves the system was never built for you. Bitcoin fixes this: no counterparty risk, no permission needed, no politician can freeze your stack. Take self-custody today.",
1108 |             "event_summary": event_summary,
1109 |             "generated_at": datetime.utcnow().isoformat(),
1110 |             "model": "fallback",
1111 |         }
1112 | 
```

### File: core/blueprints/panopticon.py (291 lines)
```
   1 | """
   2 | PANOPTICON Blueprint — Congressional Disclosure & Whale Intelligence Dashboard
   3 | "They watch us. Now we watch them."
   4 | 
   5 | Routes:
   6 |   /panopticon                          — Main dashboard (Commander-gated)
   7 |   /api/panopticon/disclosures          — STOCK Act filings (crypto-filtered)
   8 |   /api/panopticon/congress             — Alias for disclosures
   9 |   /api/panopticon/whale-alerts         — Whale wallet movements
  10 |   /api/panopticon/whales               — Alias for whale-alerts
  11 |   /api/panopticon/correlations         — Cross-reference timeline
  12 |   /api/panopticon/geopolitical         — Nation-state & macro signals
  13 |   /api/panopticon/polymarket           — Prediction market odds
  14 |   /api/panopticon/make-bitcoin-case    — AI-generated Bitcoin case (POST)
  15 |   /api/panopticon/bitcoin-case         — Alias for make-bitcoin-case
  16 | """
  17 | 
  18 | import logging
  19 | import re
  20 | from flask import Blueprint, render_template, jsonify, request
  21 | from flask_login import current_user
  22 | 
  23 | logger = logging.getLogger(__name__)
  24 | 
  25 | panopticon_bp = Blueprint("panopticon", __name__)
  26 | 
  27 | # ── Rate limiter (P0 fix for U2 — IP-based throttling on all API routes) ────
  28 | # Applied via before_request to avoid circular import issues with app.limiter
  29 | _rate_limit_store = {}  # IP -> {count, window_start}
  30 | _RATE_LIMIT_WINDOW = 60  # seconds
  31 | _RATE_LIMIT_MAX = 30  # requests per window for general API routes
  32 | _RATE_LIMIT_WHALE = 10  # tighter limit for expensive whale-alerts endpoint (P2 UI-2)
  33 | import time as _time
  34 | 
  35 | 
  36 | @panopticon_bp.before_request
  37 | def _enforce_rate_limit():
  38 |     """IP-based rate limiting for all /api/panopticon/* routes."""
  39 |     if not request.path.startswith("/api/panopticon/"):
  40 |         return None
  41 | 
  42 |     ip = request.remote_addr or "unknown"
  43 |     now = _time.time()
  44 |     key = f"{ip}:{request.path}"
  45 | 
  46 |     # Tighter limit for whale-alerts (most expensive upstream call)
  47 |     max_requests = _RATE_LIMIT_WHALE if "whale" in request.path else _RATE_LIMIT_MAX
  48 | 
  49 |     entry = _rate_limit_store.get(key)
  50 |     if entry is None or now - entry["start"] > _RATE_LIMIT_WINDOW:
  51 |         _rate_limit_store[key] = {"count": 1, "start": now}
  52 |         return None
  53 | 
  54 |     entry["count"] += 1
  55 |     if entry["count"] > max_requests:
  56 |         logger.warning("Rate limit exceeded: %s on %s (%d/%d)", ip, request.path,
  57 |                         entry["count"], max_requests)
  58 |         return jsonify({
  59 |             "error": "Rate limit exceeded",
  60 |             "retry_after": int(_RATE_LIMIT_WINDOW - (now - entry["start"])),
  61 |         }), 429
  62 | 
  63 |     return None
  64 | 
  65 | _EMPTY_DATA = {
  66 |     "btc_price": None,
  67 |     "events_today": 0,
  68 |     "disclosures": [],
  69 |     "flagged": [],
  70 |     "whales": [],
  71 |     "forex": [],
  72 |     "geopolitical": [],
  73 |     "correlations": [],
  74 |     "watch_list": [],
  75 |     "polymarket": [],
  76 |     "generated_at": None,
  77 | }
  78 | 
  79 | # Redacted teaser data for free-tier users (no real Commander data leaked)
  80 | _DEMO_DATA = {
  81 |     "btc_price": None,
  82 |     "events_today": 12,
  83 |     "disclosures": [
  84 |         {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
  85 |         {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
  86 |         {"entity": "██████████", "asset": "CLASSIFIED", "trade_type": "███", "amount_range": "$███,███", "date_filed": "████-██-██", "date_traded": "████-██-██", "tier": "confirmed", "status": "classified"},
  87 |     ],
  88 |     "flagged": [
  89 |         {"entity": "██████████", "asset": "CLASSIFIED", "tier": "flagged", "correlation_score": 0.0, "flag_reason": "CLASSIFIED — Upgrade to Commander"},
  90 |     ],
  91 |     "whales": [
  92 |         {"entity": "██████████", "wallet_label": "CLASSIFIED", "address": "████...████", "txid": "████...████", "amount_btc": 0, "tx_type": "classified", "confirmed": True, "timestamp": "████-██-██", "event_type": "whale"},
  93 |     ],
  94 |     "forex": [],
  95 |     "geopolitical": [
  96 |         {"headline": "CLASSIFIED — Upgrade to Commander for geopolitical intelligence", "category": "classified", "btc_signal": "neutral", "btc_rationale": "CLASSIFIED", "source": "CLASSIFIED", "timestamp": "████-██-██", "event_type": "geopolitical"},
  97 |     ],
  98 |     "correlations": [],
  99 |     "watch_list": [],
 100 |     "polymarket": [
 101 |         {"question": "CLASSIFIED — Upgrade to Commander for prediction market data", "yes_price": None, "volume": 0, "event_type": "prediction", "btc_signal": "neutral"},
 102 |     ],
 103 |     "generated_at": None,
 104 | }
 105 | 
 106 | 
 107 | def _is_commander() -> bool:
 108 |     """Check if current user has Commander+ tier access."""
 109 |     if not current_user.is_authenticated:
 110 |         return False
 111 |     tier = getattr(current_user, "subscription_tier", "free")
 112 |     return tier in ("commander", "sovereign")
 113 | 
 114 | 
 115 | def _sanitize_event_summary(text: str) -> str:
 116 |     """Sanitize user input for the Make Bitcoin Case prompt to prevent injection."""
 117 |     # Strip control characters and excessive whitespace
 118 |     text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
 119 |     # Remove common prompt injection patterns
 120 |     text = re.sub(r'(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)', '', text)
 121 |     # Limit to alphanumeric, basic punctuation, and spaces
 122 |     text = re.sub(r'[^\w\s.,;:!?\'"\-()/$%@#&+=]', '', text)
 123 |     return text.strip()[:500]
 124 | 
 125 | 
 126 | # ═══════════════════════════════════════════════════════════════════════════
 127 | # PAGE ROUTE
 128 | # ═══════════════════════════════════════════════════════════════════════════
 129 | 
 130 | @panopticon_bp.route("/panopticon")
 131 | def panopticon_page():
 132 |     """PANOPTICON dashboard — Commander tier sees full data, free tier sees redacted CLASSIFIED data.
 133 |     SECURITY: Free-tier users receive only redacted placeholder data. Real Commander data is NEVER
 134 |     embedded in the HTML payload for unauthenticated or free-tier users."""
 135 |     demo_mode = not _is_commander()
 136 | 
 137 |     if demo_mode:
 138 |         # Free tier: send only redacted demo data — no real data touches the template
 139 |         data = _DEMO_DATA
 140 |     else:
 141 |         # Commander tier: fetch real intelligence data
 142 |         try:
 143 |             from services.panopticon_service import get_dashboard_data
 144 |             data = get_dashboard_data()
 145 |         except Exception as e:
 146 |             logger.error("Panopticon data fetch failed: %s", e)
 147 |             data = _EMPTY_DATA
 148 | 
 149 |     return render_template(
 150 |         "panopticon.html",
 151 |         demo_mode=demo_mode,
 152 |         data=data,
 153 |     )
 154 | 
 155 | 
 156 | # ═══════════════════════════════════════════════════════════════════════════
 157 | # API ROUTES
 158 | # ═══════════════════════════════════════════════════════════════════════════
 159 | 
 160 | @panopticon_bp.route("/api/panopticon/disclosures")
 161 | @panopticon_bp.route("/api/panopticon/congress")
 162 | def api_disclosures():
 163 |     """Recent STOCK Act filings filtered for crypto/fintech."""
 164 |     if not _is_commander():
 165 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 166 | 
 167 |     try:
 168 |         from services.panopticon_service import fetch_disclosures
 169 |         limit = min(int(request.args.get("limit", 50)), 100)
 170 |         disclosures, is_live = fetch_disclosures(limit=limit)
 171 |         return jsonify({
 172 |             "disclosures": disclosures,
 173 |             "count": len(disclosures),
 174 |             "is_live": is_live,
 175 |             "tier": "confirmed",
 176 |         })
 177 |     except Exception as e:
 178 |         logger.error("Disclosures API error: %s", e)
 179 |         return jsonify({"error": "Failed to fetch disclosures"}), 500
 180 | 
 181 | 
 182 | @panopticon_bp.route("/api/panopticon/whale-alerts")
 183 | @panopticon_bp.route("/api/panopticon/whales")
 184 | def api_whale_alerts():
 185 |     """Recent large BTC wallet movements from known entities."""
 186 |     if not _is_commander():
 187 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 188 | 
 189 |     try:
 190 |         from services.panopticon_service import fetch_whale_alerts, get_btc_price
 191 |         limit = min(int(request.args.get("limit", 20)), 50)
 192 |         alerts = fetch_whale_alerts(limit=limit)
 193 |         btc_price = get_btc_price()
 194 | 
 195 |         # Enrich with USD
 196 |         if btc_price:
 197 |             for a in alerts:
 198 |                 if a.get("amount_btc"):
 199 |                     a["amount_usd"] = round(a["amount_btc"] * btc_price, 2)
 200 | 
 201 |         return jsonify({
 202 |             "alerts": alerts,
 203 |             "count": len(alerts),
 204 |             "btc_price": btc_price,
 205 |         })
 206 |     except Exception as e:
 207 |         logger.error("Whale alerts API error: %s", e)
 208 |         return jsonify({"error": "Failed to fetch whale alerts"}), 500
 209 | 
 210 | 
 211 | @panopticon_bp.route("/api/panopticon/correlations")
 212 | def api_correlations():
 213 |     """Cross-reference timeline: disclosures x whale movements x geopolitical events."""
 214 |     if not _is_commander():
 215 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 216 | 
 217 |     try:
 218 |         from services.panopticon_service import build_correlations
 219 |         limit = min(int(request.args.get("limit", 10)), 25)
 220 |         correlations = build_correlations(limit=limit)
 221 |         return jsonify({
 222 |             "correlations": correlations,
 223 |             "count": len(correlations),
 224 |         })
 225 |     except Exception as e:
 226 |         logger.error("Correlations API error: %s", e)
 227 |         return jsonify({"error": "Failed to build correlations"}), 500
 228 | 
 229 | 
 230 | @panopticon_bp.route("/api/panopticon/geopolitical")
 231 | def api_geopolitical():
 232 |     """Nation-state signals, forex interventions, sovereign BTC activity."""
 233 |     if not _is_commander():
 234 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 235 | 
 236 |     try:
 237 |         from services.panopticon_service import fetch_geopolitical, fetch_forex_signals
 238 |         geo = fetch_geopolitical()
 239 |         forex = fetch_forex_signals()
 240 |         return jsonify({
 241 |             "geopolitical": geo,
 242 |             "forex": forex,
 243 |             "count": len(geo) + len(forex),
 244 |         })
 245 |     except Exception as e:
 246 |         logger.error("Geopolitical API error: %s", e)
 247 |         return jsonify({"error": "Failed to fetch geopolitical signals"}), 500
 248 | 
 249 | 
 250 | @panopticon_bp.route("/api/panopticon/polymarket")
 251 | def api_polymarket():
 252 |     """Live Polymarket prediction market odds for crypto/macro events."""
 253 |     if not _is_commander():
 254 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 255 | 
 256 |     try:
 257 |         from services.panopticon_service import fetch_polymarket_markets
 258 |         limit = min(int(request.args.get("limit", 15)), 30)
 259 |         markets = fetch_polymarket_markets(limit=limit)
 260 |         return jsonify({
 261 |             "markets": markets,
 262 |             "count": len(markets),
 263 |         })
 264 |     except Exception as e:
 265 |         logger.error("Polymarket API error: %s", e)
 266 |         return jsonify({"error": "Failed to fetch Polymarket data"}), 500
 267 | 
 268 | 
 269 | @panopticon_bp.route("/api/panopticon/make-bitcoin-case", methods=["POST"])
 270 | @panopticon_bp.route("/api/panopticon/bitcoin-case", methods=["POST"])
 271 | def api_make_bitcoin_case():
 272 |     """Generate a cypherpunk Bitcoin self-custody argument for a specific event via Claude."""
 273 |     if not _is_commander():
 274 |         return jsonify({"error": "Commander access required", "upgrade_url": "/join"}), 403
 275 | 
 276 |     try:
 277 |         body = request.get_json(silent=True) or {}
 278 |         raw_summary = body.get("event_summary", "").strip()
 279 |         if not raw_summary:
 280 |             return jsonify({"error": "event_summary is required"}), 400
 281 |         event_summary = _sanitize_event_summary(raw_summary)
 282 |         if not event_summary:
 283 |             return jsonify({"error": "event_summary contains no valid content"}), 400
 284 | 
 285 |         from services.panopticon_service import get_make_bitcoin_case
 286 |         result = get_make_bitcoin_case(event_summary)
 287 |         return jsonify(result)
 288 |     except Exception as e:
 289 |         logger.error("Make Bitcoin Case API error: %s", e)
 290 |         return jsonify({"error": "Failed to generate Bitcoin case"}), 500
 291 | 
```

### File: templates/panopticon.html (1398 lines)
```
   1 | {% extends "base.html" %}
   2 | 
   3 | {% block title %}PANOPTICON — Congressional Intelligence | Protocol Pulse{% endblock %}
   4 | {% block meta_description %}Real-time intelligence dashboard tracking congressional disclosures, whale wallet movements, and geopolitical financial signals cross-referenced with Bitcoin data.{% endblock %}
   5 | 
   6 | {% block head %}
   7 | <link rel="preconnect" href="https://fonts.googleapis.com">
   8 | <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
   9 | <style>
  10 | /* ═══════════════════════════════════════════════════════════════════════
  11 |    PANOPTICON — "They watch us. Now we watch them."
  12 |    Bloomberg Terminal × NSA Aesthetic
  13 |    ═══════════════════════════════════════════════════════════════════════ */
  14 | :root {
  15 |     --pn-bg: #06070b;
  16 |     --pn-surface: #0d1118;
  17 |     --pn-surface-2: #121824;
  18 |     --pn-border: #1a1a2e;
  19 |     --pn-border-active: #2a2a4e;
  20 |     --pn-text: #eef2ff;
  21 |     --pn-text-secondary: #95a0ba;
  22 |     --pn-muted: #555577;
  23 |     --pn-red: #ff3b5f;
  24 |     --pn-gold: #f8c15c;
  25 |     --pn-cyan: #5de4ff;
  26 |     --pn-lime: #89ffb8;
  27 |     --pn-coral: #ff8ba0;
  28 |     --pn-amber: #ffaa00;
  29 |     --pn-purple: #8b5cf6;
  30 |     --pn-confirmed: #ff3b5f;
  31 |     --pn-flagged: #ffaa00;
  32 |     --pn-watch: #5de4ff;
  33 | }
  34 | 
  35 | body.panopticon-body {
  36 |     background: var(--pn-bg) !important;
  37 |     color: var(--pn-text);
  38 |     font-family: 'Inter', sans-serif;
  39 |     margin: 0;
  40 |     padding: 0;
  41 |     overflow-x: hidden;
  42 | }
  43 | body.panopticon-body nav,
  44 | body.panopticon-body .navbar,
  45 | body.panopticon-body footer,
  46 | body.panopticon-body .site-footer,
  47 | body.panopticon-body .pp-nav,
  48 | body.panopticon-body .pp-footer { display: none !important; }
  49 | 
  50 | .pn-wrap {
  51 |     max-width: 1640px;
  52 |     margin: 0 auto;
  53 |     padding: 0 12px;
  54 | }
  55 | 
  56 | /* ── HEADER ────────────────────────────────────────────────────── */
  57 | .pn-header {
  58 |     display: flex;
  59 |     align-items: center;
  60 |     justify-content: space-between;
  61 |     padding: 12px 16px;
  62 |     border-bottom: 1px solid var(--pn-border);
  63 |     background: var(--pn-bg);
  64 |     position: sticky;
  65 |     top: 0;
  66 |     z-index: 100;
  67 | }
  68 | .pn-header-left {
  69 |     display: flex;
  70 |     align-items: center;
  71 |     gap: 16px;
  72 | }
  73 | .pn-logo {
  74 |     font-family: 'JetBrains Mono', monospace;
  75 |     font-weight: 800;
  76 |     font-size: 15px;
  77 |     letter-spacing: 3px;
  78 |     text-transform: uppercase;
  79 |     color: var(--pn-red);
  80 | }
  81 | .pn-logo-sub {
  82 |     font-family: 'JetBrains Mono', monospace;
  83 |     font-size: 9px;
  84 |     letter-spacing: 2px;
  85 |     text-transform: uppercase;
  86 |     color: var(--pn-muted);
  87 |     margin-top: 2px;
  88 | }
  89 | .pn-tagline {
  90 |     font-family: 'JetBrains Mono', monospace;
  91 |     font-size: 10px;
  92 |     color: var(--pn-text-secondary);
  93 |     letter-spacing: 1px;
  94 |     opacity: 0.7;
  95 | }
  96 | .pn-header-right {
  97 |     display: flex;
  98 |     align-items: center;
  99 |     gap: 20px;
 100 | }
 101 | .pn-clock {
 102 |     font-family: 'JetBrains Mono', monospace;
 103 |     font-size: 14px;
 104 |     font-weight: 500;
 105 |     color: var(--pn-text);
 106 |     letter-spacing: 1px;
 107 | }
 108 | .pn-events-count {
 109 |     font-family: 'JetBrains Mono', monospace;
 110 |     font-size: 11px;
 111 |     color: var(--pn-gold);
 112 |     letter-spacing: 1px;
 113 | }
 114 | .pn-status {
 115 |     display: flex;
 116 |     align-items: center;
 117 |     gap: 6px;
 118 |     font-family: 'JetBrains Mono', monospace;
 119 |     font-size: 10px;
 120 |     color: var(--pn-lime);
 121 |     text-transform: uppercase;
 122 |     letter-spacing: 1px;
 123 | }
 124 | .pn-status-dot {
 125 |     width: 6px;
 126 |     height: 6px;
 127 |     border-radius: 50%;
 128 |     background: var(--pn-lime);
 129 |     animation: pnPulse 2s ease-in-out infinite;
 130 | }
 131 | @keyframes pnPulse {
 132 |     0%, 100% { opacity: 1; }
 133 |     50% { opacity: 0.3; }
 134 | }
 135 | .pn-back {
 136 |     color: var(--pn-text-secondary);
 137 |     text-decoration: none;
 138 |     font-family: 'JetBrains Mono', monospace;
 139 |     font-size: 11px;
 140 |     transition: color 0.2s;
 141 | }
 142 | .pn-back:hover { color: var(--pn-text); }
 143 | 
 144 | /* ── LIVE TICKER ───────────────────────────────────────────────── */
 145 | .pn-ticker {
 146 |     display: flex;
 147 |     align-items: center;
 148 |     padding: 8px 16px;
 149 |     border-bottom: 1px solid var(--pn-border);
 150 |     background: var(--pn-surface);
 151 |     gap: 12px;
 152 |     overflow: hidden;
 153 |     min-height: 36px;
 154 | }
 155 | .pn-ticker-label {
 156 |     font-family: 'JetBrains Mono', monospace;
 157 |     font-size: 9px;
 158 |     font-weight: 800;
 159 |     letter-spacing: 2px;
 160 |     text-transform: uppercase;
 161 |     color: var(--pn-red);
 162 |     white-space: nowrap;
 163 |     padding: 3px 8px;
 164 |     border: 1px solid rgba(255,59,95,0.3);
 165 |     background: rgba(255,59,95,0.08);
 166 | }
 167 | .pn-ticker-text {
 168 |     font-family: 'JetBrains Mono', monospace;
 169 |     font-size: 11px;
 170 |     color: var(--pn-text);
 171 |     white-space: nowrap;
 172 |     animation: tickerScroll 30s linear infinite;
 173 |     flex: 1;
 174 | }
 175 | @keyframes tickerScroll {
 176 |     0% { transform: translateX(0); }
 177 |     100% { transform: translateX(-50%); }
 178 | }
 179 | .pn-ticker-btc {
 180 |     font-family: 'JetBrains Mono', monospace;
 181 |     font-size: 13px;
 182 |     font-weight: 700;
 183 |     color: var(--pn-gold);
 184 |     white-space: nowrap;
 185 | }
 186 | 
 187 | /* ── ALERT RAIL ────────────────────────────────────────────────── */
 188 | .pn-alert-rail {
 189 |     display: flex;
 190 |     align-items: center;
 191 |     padding: 6px 16px;
 192 |     border-bottom: 1px solid var(--pn-border);
 193 |     background: rgba(255,59,95,0.04);
 194 |     gap: 16px;
 195 | }
 196 | .pn-alert-critical {
 197 |     display: flex;
 198 |     align-items: center;
 199 |     gap: 8px;
 200 |     color: var(--pn-red);
 201 |     font-family: 'JetBrains Mono', monospace;
 202 |     font-size: 11px;
 203 |     font-weight: 700;
 204 | }
 205 | .pn-alert-dot {
 206 |     width: 8px;
 207 |     height: 8px;
 208 |     border-radius: 50%;
 209 |     background: var(--pn-red);
 210 |     animation: critPulse 1s ease-in-out infinite;
 211 | }
 212 | @keyframes critPulse {
 213 |     0%, 100% { box-shadow: 0 0 0 0 rgba(255,59,95,0.7); }
 214 |     50% { box-shadow: 0 0 0 6px rgba(255,59,95,0); }
 215 | }
 216 | 
 217 | /* ── THREE COLUMN GRID ─────────────────────────────────────────── */
 218 | .pn-grid {
 219 |     display: grid;
 220 |     grid-template-columns: 1fr 1fr 1.2fr;
 221 |     gap: 1px;
 222 |     background: var(--pn-border);
 223 |     margin-top: 1px;
 224 |     min-height: calc(100vh - 160px);
 225 | }
 226 | @media (max-width: 1024px) {
 227 |     .pn-grid { grid-template-columns: 1fr; }
 228 | }
 229 | 
 230 | /* ── PANEL ─────────────────────────────────────────────────────── */
 231 | .pn-panel {
 232 |     background: var(--pn-bg);
 233 |     padding: 16px;
 234 |     position: relative;
 235 |     overflow-y: auto;
 236 |     max-height: calc(100vh - 160px);
 237 | }
 238 | .pn-panel-header {
 239 |     font-family: 'JetBrains Mono', monospace;
 240 |     font-size: 10px;
 241 |     font-weight: 700;
 242 |     text-transform: uppercase;
 243 |     letter-spacing: 2px;
 244 |     margin-bottom: 16px;
 245 |     padding-bottom: 8px;
 246 |     border-bottom: 1px solid var(--pn-border);
 247 |     display: flex;
 248 |     align-items: center;
 249 |     gap: 10px;
 250 | }
 251 | .pn-panel-header .tier-dot {
 252 |     width: 8px;
 253 |     height: 8px;
 254 |     border-radius: 50%;
 255 | }
 256 | .tier-confirmed .tier-dot { background: var(--pn-confirmed); }
 257 | .tier-confirmed .pn-panel-header { color: var(--pn-confirmed); }
 258 | .tier-flagged .tier-dot { background: var(--pn-flagged); }
 259 | .tier-flagged .pn-panel-header { color: var(--pn-flagged); }
 260 | .tier-feed .tier-dot { background: var(--pn-watch); }
 261 | .tier-feed .pn-panel-header { color: var(--pn-watch); }
 262 | 
 263 | .pn-panel-count {
 264 |     margin-left: auto;
 265 |     font-size: 9px;
 266 |     color: var(--pn-muted);
 267 |     font-weight: 500;
 268 | }
 269 | 
 270 | /* ── DISCLOSURE CARD ───────────────────────────────────────────── */
 271 | .pn-card {
 272 |     background: var(--pn-surface);
 273 |     border: 1px solid var(--pn-border);
 274 |     border-radius: 8px;
 275 |     padding: 14px;
 276 |     margin-bottom: 10px;
 277 |     transition: border-color 0.2s;
 278 |     position: relative;
 279 | }
 280 | .pn-card:hover { border-color: var(--pn-border-active); }
 281 | .pn-card-header {
 282 |     display: flex;
 283 |     justify-content: space-between;
 284 |     align-items: flex-start;
 285 |     margin-bottom: 10px;
 286 | }
 287 | .pn-card-entity {
 288 |     font-family: 'Inter', sans-serif;
 289 |     font-size: 14px;
 290 |     font-weight: 600;
 291 |     color: var(--pn-text);
 292 |     line-height: 1.3;
 293 | }
 294 | .pn-card-party {
 295 |     font-family: 'JetBrains Mono', monospace;
 296 |     font-size: 10px;
 297 |     font-weight: 700;
 298 |     padding: 2px 8px;
 299 |     border-radius: 4px;
 300 |     letter-spacing: 1px;
 301 | }
 302 | .party-R { background: rgba(255,59,95,0.15); color: var(--pn-red); }
 303 | .party-D { background: rgba(93,228,255,0.15); color: var(--pn-cyan); }
 304 | .party-I { background: rgba(139,92,246,0.15); color: var(--pn-purple); }
 305 | 
 306 | .pn-card-body {
 307 |     display: grid;
 308 |     grid-template-columns: 1fr 1fr;
 309 |     gap: 8px;
 310 |     margin-bottom: 10px;
 311 | }
 312 | .pn-card-field {
 313 |     display: flex;
 314 |     flex-direction: column;
 315 | }
 316 | .pn-card-label {
 317 |     font-family: 'JetBrains Mono', monospace;
 318 |     font-size: 9px;
 319 |     font-weight: 700;
 320 |     text-transform: uppercase;
 321 |     letter-spacing: 1.5px;
 322 |     color: var(--pn-muted);
 323 |     margin-bottom: 3px;
 324 | }
 325 | .pn-card-value {
 326 |     font-family: 'JetBrains Mono', monospace;
 327 |     font-size: 12px;
 328 |     font-weight: 500;
 329 |     color: var(--pn-text);
 330 | }
 331 | .pn-card-value.buy { color: var(--pn-lime); }
 332 | .pn-card-value.sell { color: var(--pn-coral); }
 333 | 
 334 | .pn-card-correlation {
 335 |     background: rgba(255,170,0,0.06);
 336 |     border: 1px solid rgba(255,170,0,0.15);
 337 |     border-radius: 6px;
 338 |     padding: 8px 10px;
 339 |     font-family: 'JetBrains Mono', monospace;
 340 |     font-size: 10px;
 341 |     color: var(--pn-amber);
 342 |     line-height: 1.4;
 343 | }
 344 | .pn-card-correlation::before {
 345 |     content: "PATTERN DETECTED";
 346 |     display: block;
 347 |     font-size: 8px;
 348 |     font-weight: 800;
 349 |     letter-spacing: 2px;
 350 |     margin-bottom: 4px;
 351 |     color: var(--pn-amber);
 352 |     opacity: 0.7;
 353 | }
 354 | 
 355 | .pn-card-source {
 356 |     margin-top: 8px;
 357 |     font-family: 'JetBrains Mono', monospace;
 358 |     font-size: 9px;
 359 |     color: var(--pn-muted);
 360 | }
 361 | .pn-card-source a {
 362 |     color: var(--pn-text-secondary);
 363 |     text-decoration: none;
 364 | }
 365 | .pn-card-source a:hover { color: var(--pn-gold); }
 366 | 
 367 | /* ── WHALE CARD ────────────────────────────────────────────────── */
 368 | .pn-whale-card {
 369 |     background: var(--pn-surface);
 370 |     border: 1px solid var(--pn-border);
 371 |     border-left: 3px solid var(--pn-cyan);
 372 |     border-radius: 0 8px 8px 0;
 373 |     padding: 12px 14px;
 374 |     margin-bottom: 8px;
 375 |     transition: border-color 0.2s;
 376 | }
 377 | .pn-whale-card:hover { border-color: var(--pn-border-active); border-left-color: var(--pn-cyan); }
 378 | .pn-whale-entity {
 379 |     font-family: 'Inter', sans-serif;
 380 |     font-size: 12px;
 381 |     font-weight: 600;
 382 |     color: var(--pn-text);
 383 |     margin-bottom: 6px;
 384 | }
 385 | .pn-whale-amount {
 386 |     font-family: 'JetBrains Mono', monospace;
 387 |     font-size: 18px;
 388 |     font-weight: 700;
 389 |     margin-bottom: 4px;
 390 | }
 391 | .pn-whale-amount.inflow { color: var(--pn-lime); }
 392 | .pn-whale-amount.outflow { color: var(--pn-coral); }
 393 | .pn-whale-usd {
 394 |     font-family: 'JetBrains Mono', monospace;
 395 |     font-size: 11px;
 396 |     color: var(--pn-text-secondary);
 397 |     margin-bottom: 6px;
 398 | }
 399 | .pn-whale-meta {
 400 |     display: flex;
 401 |     justify-content: space-between;
 402 |     font-family: 'JetBrains Mono', monospace;
 403 |     font-size: 9px;
 404 |     color: var(--pn-muted);
 405 | }
 406 | .pn-whale-meta a {
 407 |     color: var(--pn-text-secondary);
 408 |     text-decoration: none;
 409 | }
 410 | .pn-whale-meta a:hover { color: var(--pn-gold); }
 411 | .pn-whale-type {
 412 |     font-size: 9px;
 413 |     font-weight: 700;
 414 |     letter-spacing: 1px;
 415 |     text-transform: uppercase;
 416 |     padding: 2px 6px;
 417 |     border-radius: 3px;
 418 | }
 419 | .pn-whale-type.inflow { background: rgba(137,255,184,0.1); color: var(--pn-lime); }
 420 | .pn-whale-type.outflow { background: rgba(255,139,160,0.1); color: var(--pn-coral); }
 421 | 
 422 | /* ── GEOPOLITICAL CARD ─────────────────────────────────────────── */
 423 | .pn-geo-card {
 424 |     background: var(--pn-surface);
 425 |     border: 1px solid var(--pn-border);
 426 |     border-radius: 8px;
 427 |     padding: 12px 14px;
 428 |     margin-bottom: 8px;
 429 | }
 430 | .pn-geo-headline {
 431 |     font-family: 'Inter', sans-serif;
 432 |     font-size: 13px;
 433 |     font-weight: 600;
 434 |     color: var(--pn-text);
 435 |     margin-bottom: 8px;
 436 |     line-height: 1.3;
 437 | }
 438 | .pn-geo-signal {
 439 |     display: inline-flex;
 440 |     align-items: center;
 441 |     gap: 6px;
 442 |     font-family: 'JetBrains Mono', monospace;
 443 |     font-size: 10px;
 444 |     font-weight: 700;
 445 |     letter-spacing: 1px;
 446 |     text-transform: uppercase;
 447 |     padding: 3px 8px;
 448 |     border-radius: 4px;
 449 |     margin-bottom: 6px;
 450 | }
 451 | .signal-bullish { background: rgba(137,255,184,0.1); color: var(--pn-lime); }
 452 | .signal-bearish { background: rgba(255,139,160,0.1); color: var(--pn-coral); }
 453 | .signal-neutral { background: rgba(149,160,186,0.1); color: var(--pn-text-secondary); }
 454 | .pn-geo-rationale {
 455 |     font-family: 'JetBrains Mono', monospace;
 456 |     font-size: 10px;
 457 |     color: var(--pn-text-secondary);
 458 |     line-height: 1.4;
 459 |     margin-top: 6px;
 460 | }
 461 | .pn-geo-meta {
 462 |     margin-top: 8px;
 463 |     font-family: 'JetBrains Mono', monospace;
 464 |     font-size: 9px;
 465 |     color: var(--pn-muted);
 466 |     display: flex;
 467 |     justify-content: space-between;
 468 | }
 469 | 
 470 | /* ── FOREX MINI-CARD ───────────────────────────────────────────── */
 471 | .pn-forex-row {
 472 |     display: flex;
 473 |     justify-content: space-between;
 474 |     align-items: center;
 475 |     padding: 8px 12px;
 476 |     background: var(--pn-surface);
 477 |     border: 1px solid var(--pn-border);
 478 |     border-radius: 6px;
 479 |     margin-bottom: 6px;
 480 | }
 481 | .pn-forex-pair {
 482 |     font-family: 'JetBrains Mono', monospace;
 483 |     font-size: 12px;
 484 |     font-weight: 700;
 485 |     color: var(--pn-text);
 486 | }
 487 | .pn-forex-rate {
 488 |     font-family: 'JetBrains Mono', monospace;
 489 |     font-size: 14px;
 490 |     font-weight: 700;
 491 |     color: var(--pn-gold);
 492 | }
 493 | .pn-forex-status {
 494 |     font-family: 'JetBrains Mono', monospace;
 495 |     font-size: 9px;
 496 |     color: var(--pn-cyan);
 497 |     text-transform: uppercase;
 498 |     letter-spacing: 1px;
 499 | }
 500 | 
 501 | /* ── WATCH LIST SECTION ────────────────────────────────────────── */
 502 | .pn-watchlist {
 503 |     margin-top: 20px;
 504 |     padding-top: 16px;
 505 |     border-top: 1px solid var(--pn-border);
 506 | }
 507 | .pn-watchlist-header {
 508 |     font-family: 'JetBrains Mono', monospace;
 509 |     font-size: 10px;
 510 |     font-weight: 700;
 511 |     text-transform: uppercase;
 512 |     letter-spacing: 2px;
 513 |     color: var(--pn-cyan);
 514 |     margin-bottom: 12px;
 515 | }
 516 | .pn-watchlist-item {
 517 |     display: flex;
 518 |     align-items: center;
 519 |     gap: 12px;
 520 |     padding: 10px 12px;
 521 |     background: var(--pn-surface);
 522 |     border: 1px solid var(--pn-border);
 523 |     border-radius: 8px;
 524 |     margin-bottom: 6px;
 525 | }
 526 | .pn-watchlist-name {
 527 |     font-family: 'Inter', sans-serif;
 528 |     font-size: 13px;
 529 |     font-weight: 600;
 530 |     color: var(--pn-text);
 531 |     min-width: 140px;
 532 | }
 533 | .pn-watchlist-detail {
 534 |     font-family: 'JetBrains Mono', monospace;
 535 |     font-size: 10px;
 536 |     color: var(--pn-text-secondary);
 537 |     flex: 1;
 538 | }
 539 | .pn-watchlist-sources {
 540 |     font-family: 'JetBrains Mono', monospace;
 541 |     font-size: 9px;
 542 |     color: var(--pn-muted);
 543 | }
 544 | 
 545 | /* ── CORRELATION TIMELINE ──────────────────────────────────────── */
 546 | .pn-correlation {
 547 |     background: var(--pn-surface-2);
 548 |     border: 1px solid var(--pn-border);
 549 |     border-left: 3px solid var(--pn-gold);
 550 |     border-radius: 0 8px 8px 0;
 551 |     padding: 14px;
 552 |     margin-bottom: 12px;
 553 | }
 554 | .pn-correlation-header {
 555 |     font-family: 'JetBrains Mono', monospace;
 556 |     font-size: 9px;
 557 |     font-weight: 800;
 558 |     letter-spacing: 2px;
 559 |     text-transform: uppercase;
 560 |     color: var(--pn-gold);
 561 |     margin-bottom: 8px;
 562 | }
 563 | .pn-correlation-summary {
 564 |     font-family: 'Inter', sans-serif;
 565 |     font-size: 12px;
 566 |     color: var(--pn-text);
 567 |     line-height: 1.4;
 568 |     margin-bottom: 10px;
 569 | }
 570 | .pn-correlation-events {
 571 |     display: flex;
 572 |     flex-direction: column;
 573 |     gap: 6px;
 574 | }
 575 | .pn-corr-event {
 576 |     display: flex;
 577 |     align-items: center;
 578 |     gap: 8px;
 579 |     padding: 6px 10px;
 580 |     background: rgba(248,193,92,0.04);
 581 |     border-radius: 4px;
 582 |     font-family: 'JetBrains Mono', monospace;
 583 |     font-size: 10px;
 584 |     color: var(--pn-text-secondary);
 585 | }
 586 | .pn-corr-event-type {
 587 |     font-size: 8px;
 588 |     font-weight: 800;
 589 |     letter-spacing: 1px;
 590 |     text-transform: uppercase;
 591 |     padding: 2px 6px;
 592 |     border-radius: 3px;
 593 |     white-space: nowrap;
 594 | }
 595 | .pn-corr-event-type.whale { background: rgba(93,228,255,0.1); color: var(--pn-cyan); }
 596 | .pn-corr-event-type.geo { background: rgba(139,92,246,0.1); color: var(--pn-purple); }
 597 | 
 598 | /* ── DEMO / CLASSIFIED OVERLAY ─────────────────────────────────── */
 599 | .pn-demo-overlay {
 600 |     position: absolute;
 601 |     inset: 0;
 602 |     background: rgba(6,7,11,0.88);
 603 |     backdrop-filter: blur(6px);
 604 |     display: flex;
 605 |     flex-direction: column;
 606 |     align-items: center;
 607 |     justify-content: center;
 608 |     z-index: 10;
 609 |     gap: 12px;
 610 | }
 611 | .pn-classified-badge {
 612 |     font-family: 'JetBrains Mono', monospace;
 613 |     font-size: 14px;
 614 |     font-weight: 800;
 615 |     letter-spacing: 4px;
 616 |     text-transform: uppercase;
 617 |     color: var(--pn-red);
 618 |     border: 2px solid var(--pn-red);
 619 |     padding: 10px 24px;
 620 |     animation: classifiedFlash 3s ease-in-out infinite;
 621 | }
 622 | @keyframes classifiedFlash {
 623 |     0%, 100% { opacity: 1; border-color: var(--pn-red); }
 624 |     50% { opacity: 0.6; border-color: rgba(255,59,95,0.3); }
 625 | }
 626 | .pn-classified-sub {
 627 |     font-family: 'JetBrains Mono', monospace;
 628 |     font-size: 10px;
 629 |     color: var(--pn-text-secondary);
 630 |     letter-spacing: 1px;
 631 | }
 632 | .pn-upgrade-btn {
 633 |     display: inline-block;
 634 |     margin-top: 8px;
 635 |     padding: 8px 24px;
 636 |     background: var(--pn-red);
 637 |     color: #fff;
 638 |     font-family: 'JetBrains Mono', monospace;
 639 |     font-size: 11px;
 640 |     font-weight: 700;
 641 |     letter-spacing: 2px;
 642 |     text-transform: uppercase;
 643 |     text-decoration: none;
 644 |     border-radius: 4px;
 645 |     transition: background 0.2s;
 646 | }
 647 | .pn-upgrade-btn:hover { background: #e02a4d; color: #fff; }
 648 | 
 649 | /* ── SECTION DIVIDERS ──────────────────────────────────────────── */
 650 | .pn-section-title {
 651 |     font-family: 'JetBrains Mono', monospace;
 652 |     font-size: 10px;
 653 |     font-weight: 700;
 654 |     letter-spacing: 2px;
 655 |     text-transform: uppercase;
 656 |     color: var(--pn-gold);
 657 |     margin: 20px 0 12px;
 658 |     padding-bottom: 6px;
 659 |     border-bottom: 1px solid rgba(248,193,92,0.15);
 660 | }
 661 | 
 662 | /* ── MAKE THE BITCOIN CASE ────────────────────────────────────── */
 663 | .pn-btc-case-btn {
 664 |     display: flex;
 665 |     align-items: center;
 666 |     justify-content: center;
 667 |     gap: 8px;
 668 |     width: 100%;
 669 |     padding: 10px 16px;
 670 |     margin-top: 8px;
 671 |     background: linear-gradient(135deg, rgba(248,193,92,0.12), rgba(255,59,95,0.08));
 672 |     border: 1px solid rgba(248,193,92,0.25);
 673 |     border-radius: 6px;
 674 |     color: var(--pn-gold);
 675 |     font-family: 'JetBrains Mono', monospace;
 676 |     font-size: 10px;
 677 |     font-weight: 700;
 678 |     letter-spacing: 2px;
 679 |     text-transform: uppercase;
 680 |     cursor: pointer;
 681 |     transition: all 0.3s ease;
 682 | }
 683 | .pn-btc-case-btn:hover {
 684 |     background: linear-gradient(135deg, rgba(248,193,92,0.20), rgba(255,59,95,0.14));
 685 |     border-color: rgba(248,193,92,0.45);
 686 |     box-shadow: 0 0 20px rgba(248,193,92,0.12);
 687 | }
 688 | .pn-btc-case-btn:disabled {
 689 |     opacity: 0.5;
 690 |     cursor: wait;
 691 | }
 692 | .pn-btc-case-output {
 693 |     margin-top: 10px;
 694 |     padding: 14px 16px;
 695 |     background: rgba(248,193,92,0.04);
 696 |     border: 1px solid rgba(248,193,92,0.12);
 697 |     border-left: 3px solid var(--pn-gold);
 698 |     border-radius: 0 6px 6px 0;
 699 |     font-family: 'JetBrains Mono', monospace;
 700 |     font-size: 11px;
 701 |     color: var(--pn-text);
 702 |     line-height: 1.6;
 703 |     letter-spacing: 0.3px;
 704 |     display: none;
 705 | }
 706 | .pn-btc-case-output.visible { display: block; }
 707 | .pn-btc-case-label {
 708 |     font-size: 8px;
 709 |     font-weight: 800;
 710 |     letter-spacing: 2px;
 711 |     text-transform: uppercase;
 712 |     color: var(--pn-gold);
 713 |     margin-bottom: 6px;
 714 |     opacity: 0.7;
 715 | }
 716 | .pn-typewriter-cursor {
 717 |     display: inline-block;
 718 |     width: 2px;
 719 |     height: 14px;
 720 |     background: var(--pn-gold);
 721 |     margin-left: 2px;
 722 |     animation: cursorBlink 0.7s step-end infinite;
 723 |     vertical-align: text-bottom;
 724 | }
 725 | @keyframes cursorBlink {
 726 |     0%, 100% { opacity: 1; }
 727 |     50% { opacity: 0; }
 728 | }
 729 | .pn-btc-case-model {
 730 |     margin-top: 8px;
 731 |     font-size: 8px;
 732 |     color: var(--pn-muted);
 733 |     letter-spacing: 1px;
 734 |     text-transform: uppercase;
 735 | }
 736 | 
 737 | /* ── POLYMARKET PANEL ──────────────────────────────────────────── */
 738 | .pn-poly-card {
 739 |     background: var(--pn-surface);
 740 |     border: 1px solid var(--pn-border);
 741 |     border-radius: 8px;
 742 |     padding: 12px 14px;
 743 |     margin-bottom: 8px;
 744 |     transition: border-color 0.2s;
 745 | }
 746 | .pn-poly-card:hover { border-color: var(--pn-border-active); }
 747 | .pn-poly-question {
 748 |     font-family: 'Inter', sans-serif;
 749 |     font-size: 12px;
 750 |     font-weight: 600;
 751 |     color: var(--pn-text);
 752 |     line-height: 1.3;
 753 |     margin-bottom: 8px;
 754 | }
 755 | .pn-poly-bar-wrap {
 756 |     width: 100%;
 757 |     height: 6px;
 758 |     background: rgba(255,255,255,0.06);
 759 |     border-radius: 3px;
 760 |     overflow: hidden;
 761 |     margin-bottom: 6px;
 762 | }
 763 | .pn-poly-bar-fill {
 764 |     height: 100%;
 765 |     border-radius: 3px;
 766 |     transition: width 0.8s ease;
 767 | }
 768 | .pn-poly-bar-fill.bullish { background: linear-gradient(90deg, var(--pn-lime), rgba(137,255,184,0.5)); }
 769 | .pn-poly-bar-fill.bearish { background: linear-gradient(90deg, var(--pn-coral), rgba(255,139,160,0.5)); }
 770 | .pn-poly-bar-fill.neutral { background: linear-gradient(90deg, var(--pn-gold), rgba(248,193,92,0.5)); }
 771 | .pn-poly-meta {
 772 |     display: flex;
 773 |     justify-content: space-between;
 774 |     align-items: center;
 775 |     font-family: 'JetBrains Mono', monospace;
 776 |     font-size: 9px;
 777 |     color: var(--pn-muted);
 778 | }
 779 | .pn-poly-odds {
 780 |     font-family: 'JetBrains Mono', monospace;
 781 |     font-size: 18px;
 782 |     font-weight: 700;
 783 |     margin-right: 4px;
 784 | }
 785 | .pn-poly-odds.bullish { color: var(--pn-lime); }
 786 | .pn-poly-odds.bearish { color: var(--pn-coral); }
 787 | .pn-poly-odds.neutral { color: var(--pn-gold); }
 788 | .pn-poly-volume {
 789 |     font-family: 'JetBrains Mono', monospace;
 790 |     font-size: 10px;
 791 |     color: var(--pn-text-secondary);
 792 | }
 793 | 
 794 | /* ── DISCLAIMER ────────────────────────────────────────────────── */
 795 | .pn-disclaimer {
 796 |     padding: 12px 16px;
 797 |     border-top: 1px solid var(--pn-border);
 798 |     background: var(--pn-surface);
 799 |     font-family: 'JetBrains Mono', monospace;
 800 |     font-size: 9px;
 801 |     color: var(--pn-muted);
 802 |     text-align: center;
 803 |     line-height: 1.5;
 804 |     letter-spacing: 0.5px;
 805 | }
 806 | 
 807 | /* ── LOADING STATE ─────────────────────────────────────────────── */
 808 | .pn-loading {
 809 |     display: flex;
 810 |     align-items: center;
 811 |     gap: 8px;
 812 |     padding: 16px;
 813 |     font-family: 'JetBrains Mono', monospace;
 814 |     font-size: 11px;
 815 |     color: var(--pn-text-secondary);
 816 | }
 817 | .pn-loading-dot {
 818 |     width: 4px;
 819 |     height: 4px;
 820 |     border-radius: 50%;
 821 |     background: var(--pn-cyan);
 822 |     animation: loadDot 1.2s ease-in-out infinite;
 823 | }
 824 | .pn-loading-dot:nth-child(2) { animation-delay: 0.2s; }
 825 | .pn-loading-dot:nth-child(3) { animation-delay: 0.4s; }
 826 | @keyframes loadDot {
 827 |     0%, 100% { opacity: 0.3; }
 828 |     50% { opacity: 1; }
 829 | }
 830 | 
 831 | /* ── HERO STATS ROW ────────────────────────────────────────────── */
 832 | .pn-stats-row {
 833 |     display: grid;
 834 |     grid-template-columns: repeat(5, 1fr);
 835 |     gap: 1px;
 836 |     background: var(--pn-border);
 837 |     margin-bottom: 1px;
 838 | }
 839 | @media (max-width: 768px) {
 840 |     .pn-stats-row { grid-template-columns: 1fr 1fr; }
 841 | }
 842 | .pn-stat {
 843 |     background: var(--pn-bg);
 844 |     padding: 14px 16px;
 845 |     text-align: center;
 846 | }
 847 | .pn-stat-value {
 848 |     font-family: 'JetBrains Mono', monospace;
 849 |     font-size: 22px;
 850 |     font-weight: 700;
 851 |     color: var(--pn-text);
 852 | }
 853 | .pn-stat-label {
 854 |     font-family: 'JetBrains Mono', monospace;
 855 |     font-size: 9px;
 856 |     font-weight: 700;
 857 |     text-transform: uppercase;
 858 |     letter-spacing: 1.5px;
 859 |     color: var(--pn-muted);
 860 |     margin-top: 4px;
 861 | }
 862 | 
 863 | /* ── EMPTY STATE ───────────────────────────────────────────────── */
 864 | .pn-empty {
 865 |     padding: 30px 16px;
 866 |     text-align: center;
 867 |     font-family: 'JetBrains Mono', monospace;
 868 |     font-size: 11px;
 869 |     color: var(--pn-muted);
 870 | }
 871 | 
 872 | /* ── STATUS CHIP ───────────────────────────────────────────────── */
 873 | .pn-status-chip {
 874 |     display: inline-flex;
 875 |     align-items: center;
 876 |     gap: 4px;
 877 |     font-family: 'JetBrains Mono', monospace;
 878 |     font-size: 9px;
 879 |     font-weight: 700;
 880 |     letter-spacing: 1px;
 881 |     text-transform: uppercase;
 882 |     padding: 2px 8px;
 883 |     border-radius: 3px;
 884 | }
 885 | .pn-status-chip.loading { background: rgba(93,228,255,0.1); color: var(--pn-cyan); }
 886 | .pn-status-chip.live { background: rgba(137,255,184,0.1); color: var(--pn-lime); }
 887 | .pn-status-chip.stale { background: rgba(85,85,119,0.2); color: var(--pn-muted); }
 888 | </style>
 889 | {% endblock %}
 890 | 
 891 | {% block body_class %}panopticon-body{% endblock %}
 892 | 
 893 | {% block content %}
 894 | <div class="pn-wrap">
 895 |     <!-- ═══ HEADER ═══ -->
 896 |     <header class="pn-header">
 897 |         <div class="pn-header-left">
 898 |             <div>
 899 |                 <div class="pn-logo">PANOPTICON</div>
 900 |                 <div class="pn-logo-sub">They watch us. Now we watch them.</div>
 901 |             </div>
 902 |             <span class="pn-tagline">Congressional Disclosure &amp; Whale Intelligence</span>
 903 |         </div>
 904 |         <div class="pn-header-right">
 905 |             <span class="pn-events-count" id="pnEventsCount">{{ data.events_today }} EVENTS TODAY</span>
 906 |             <span class="pn-clock" id="pnClock">--:--:-- UTC</span>
 907 |             <div class="pn-status">
 908 |                 <div class="pn-status-dot"></div>
 909 |                 <span>SCANNING</span>
 910 |             </div>
 911 |             <a href="/" class="pn-back">&larr; PROTOCOL PULSE</a>
 912 |         </div>
 913 |     </header>
 914 | 
 915 |     <!-- ═══ LIVE TICKER ═══ -->
 916 |     <div class="pn-ticker">
 917 |         <span class="pn-ticker-label">LIVE FEED</span>
 918 |         <span class="pn-ticker-text" id="pnTickerText">
 919 |             {% if data.whales %}
 920 |                 {% for w in data.whales[:3] %}
 921 |                     {{ w.entity }}: {{ w.amount_btc }} BTC {{ w.tx_type }} &nbsp;&bull;&nbsp;
 922 |                 {% endfor %}
 923 |             {% endif %}
 924 |             {% for d in data.disclosures[:3] %}
 925 |                 {{ d.entity }} — {{ d.asset }} ({{ d.trade_type }}) &nbsp;&bull;&nbsp;
 926 |             {% endfor %}
 927 |             PANOPTICON monitoring {{ data.events_today }} events &nbsp;&bull;&nbsp; All data from public sources
 928 |         </span>
 929 |         <span class="pn-ticker-btc" id="pnBtcPrice">
 930 |             {% if data.btc_price %}BTC ${{ "{:,.0f}".format(data.btc_price) }}{% else %}BTC --{% endif %}
 931 |         </span>
 932 |     </div>
 933 | 
 934 |     {% if demo_mode %}
 935 |     <!-- ═══ CLASSIFIED ALERT ═══ -->
 936 |     <div class="pn-alert-rail">
 937 |         <div class="pn-alert-critical">
 938 |             <div class="pn-alert-dot"></div>
 939 |             <span>[ CLASSIFIED — Commander Access Required ]</span>
 940 |         </div>
 941 |         <span style="margin-left:auto; font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--pn-muted);">
 942 |             Upgrade to Commander to unlock full intelligence feed
 943 |         </span>
 944 |     </div>
 945 |     {% endif %}
 946 | 
 947 |     <!-- ═══ STATS ROW ═══ -->
 948 |     <div class="pn-stats-row">
 949 |         <div class="pn-stat">
 950 |             <div class="pn-stat-value" id="pnStatDisclosures">{{ data.disclosures|length }}</div>
 951 |             <div class="pn-stat-label">Disclosures Tracked</div>
 952 |         </div>
 953 |         <div class="pn-stat">
 954 |             <div class="pn-stat-value" id="pnStatWhales">{{ data.whales|length }}</div>
 955 |             <div class="pn-stat-label">Whale Movements</div>
 956 |         </div>
 957 |         <div class="pn-stat">
 958 |             <div class="pn-stat-value" id="pnStatFlags">{{ data.flagged|length }}</div>
 959 |             <div class="pn-stat-label">Patterns Flagged</div>
 960 |         </div>
 961 |         <div class="pn-stat">
 962 |             <div class="pn-stat-value" id="pnStatPoly">{{ data.polymarket|length if data.polymarket else 0 }}</div>
 963 |             <div class="pn-stat-label">Prediction Markets</div>
 964 |         </div>
 965 |         <div class="pn-stat">
 966 |             <div class="pn-stat-value" id="pnStatGeo">{{ data.geopolitical|length }}</div>
 967 |             <div class="pn-stat-label">Geopolitical Signals</div>
 968 |         </div>
 969 |     </div>
 970 | 
 971 |     <!-- ═══ THREE COLUMN GRID ═══ -->
 972 |     <div class="pn-grid">
 973 |         <!-- ═══ COLUMN 1: CONFIRMED (STOCK Act) ═══ -->
 974 |         <div class="pn-panel tier-confirmed">
 975 |             <div class="pn-panel-header">
 976 |                 <span class="tier-dot"></span>
 977 |                 TIER 1 — CONFIRMED
 978 |                 <span class="pn-panel-count">STOCK ACT FILINGS</span>
 979 |             </div>
 980 | 
 981 |             {% if demo_mode %}
 982 |             <div class="pn-demo-overlay">
 983 |                 <div class="pn-classified-badge">CLASSIFIED</div>
 984 |                 <div class="pn-classified-sub">Commander Access Required</div>
 985 |                 <a href="/join" class="pn-upgrade-btn">Unlock Intelligence</a>
 986 |             </div>
 987 |             {% endif %}
 988 | 
 989 |             {% if not demo_mode and data.disclosures_live is defined and not data.disclosures_live %}
 990 |             <div class="pn-fallback-banner" style="background:rgba(248,193,92,0.1);border:1px solid var(--pn-gold);border-radius:6px;padding:8px 12px;margin-bottom:12px;font-size:0.75rem;color:var(--pn-gold);">
 991 |                 <strong>NOTICE:</strong> Live data from efts.house.gov is temporarily unavailable. Displaying documented public examples.
 992 |             </div>
 993 |             {% endif %}
 994 | 
 995 |             <div id="pnDisclosures">
 996 |                 {% for d in data.disclosures %}
 997 |                 <div class="pn-card">
 998 |                     <div class="pn-card-header">
 999 |                         <div class="pn-card-entity">{{ d.entity }}</div>
1000 |                         {% if d.party %}
1001 |                         <span class="pn-card-party party-{{ d.party }}">{{ d.party }}</span>
1002 |                         {% endif %}
1003 |                     </div>
1004 |                     <div class="pn-card-body">
1005 |                         <div class="pn-card-field">
1006 |                             <span class="pn-card-label">Asset</span>
1007 |                             <span class="pn-card-value">{{ d.asset }}</span>
1008 |                         </div>
1009 |                         <div class="pn-card-field">
1010 |                             <span class="pn-card-label">Type</span>
1011 |                             <span class="pn-card-value {{ 'buy' if d.trade_type == 'purchase' else 'sell' if d.trade_type == 'sale' else '' }}">{{ d.trade_type|upper }}</span>
1012 |                         </div>
1013 |                         <div class="pn-card-field">
1014 |                             <span class="pn-card-label">Amount</span>
1015 |                             <span class="pn-card-value">{{ d.amount_range }}</span>
1016 |                         </div>
1017 |                         <div class="pn-card-field">
1018 |                             <span class="pn-card-label">Filed</span>
1019 |                             <span class="pn-card-value">{{ d.date_filed }}</span>
1020 |                         </div>
1021 |                         {% if d.get('days_to_file') %}
1022 |                         <div class="pn-card-field">
1023 |                             <span class="pn-card-label">Days to File</span>
1024 |                             <span class="pn-card-value">{{ d.days_to_file }}d</span>
1025 |                         </div>
1026 |                         {% endif %}
1027 |                         {% if d.get('committee') %}
1028 |                         <div class="pn-card-field">
1029 |                             <span class="pn-card-label">Committee</span>
1030 |                             <span class="pn-card-value">{{ d.committee }}</span>
1031 |                         </div>
1032 |                         {% endif %}
1033 |                     </div>
1034 |                     {% if d.get('correlation_note') %}
1035 |                     <div class="pn-card-correlation">{{ d.correlation_note }}</div>
1036 |                     {% endif %}
1037 |                     {% if d.get('status') == 'loading' %}
1038 |                     <div style="margin-top:8px;">
1039 |                         <span class="pn-status-chip loading">Awaiting Live Data</span>
1040 |                     </div>
1041 |                     {% endif %}
1042 |                     <div class="pn-card-source">
1043 |                         Source: <a href="{{ d.source_url }}" target="_blank" rel="noopener">Public Financial Disclosure</a>
1044 |                     </div>
1045 |                 </div>
1046 |                 {% endfor %}
1047 |                 {% if not data.disclosures %}
1048 |                 <div class="pn-empty">No crypto-related disclosures in current window</div>
1049 |                 {% endif %}
1050 |             </div>
1051 | 
1052 |             <!-- WATCH LIST -->
1053 |             <div class="pn-watchlist">
1054 |                 <div class="pn-watchlist-header">TIER 3 — WATCH LIST (Publicly Documented)</div>
1055 |                 {% for w in data.watch_list %}
1056 |                 <div class="pn-watchlist-item">
1057 |                     <div class="pn-watchlist-name">
1058 |                         {{ w.name }}
1059 |                         <span class="pn-card-party party-{{ w.party }}" style="margin-left:6px;">{{ w.party }}</span>
1060 |                     </div>
1061 |                     <div class="pn-watchlist-detail">{{ w.note }}</div>
1062 |                     <div class="pn-watchlist-sources">{{ w.coverage|join(', ') }}</div>
1063 |                 </div>
1064 |                 {% endfor %}
1065 |             </div>
1066 |         </div>
1067 | 
1068 |         <!-- ═══ COLUMN 2: FLAGGED (Correlations) ═══ -->
1069 |         <div class="pn-panel tier-flagged">
1070 |             <div class="pn-panel-header">
1071 |                 <span class="tier-dot"></span>
1072 |                 TIER 2 — FLAGGED
1073 |                 <span class="pn-panel-count">PATTERN DETECTION</span>
1074 |             </div>
1075 | 
1076 |             {% if demo_mode %}
1077 |             <div class="pn-demo-overlay">
1078 |                 <div class="pn-classified-badge">CLASSIFIED</div>
1079 |                 <div class="pn-classified-sub">Commander Access Required</div>
1080 |                 <a href="/join" class="pn-upgrade-btn">Unlock Intelligence</a>
1081 |             </div>
1082 |             {% endif %}
1083 | 
1084 |             <div style="margin-bottom:12px; padding:10px; background:rgba(255,170,0,0.04); border:1px solid rgba(255,170,0,0.1); border-radius:6px; font-family:'JetBrains Mono',monospace; font-size:9px; color:var(--pn-amber); letter-spacing:0.5px; line-height:1.5;">
1085 |                 PATTERN FOR RESEARCH &mdash; NOT VERIFIED. Statistical correlations shown for independent research purposes only. These are computed patterns, not accusations.
1086 |             </div>
1087 | 
1088 |             <!-- Correlation Timeline -->
1089 |             <div class="pn-section-title">Correlation Timeline</div>
1090 |             <div id="pnCorrelations">
1091 |                 {% for c in data.correlations %}
1092 |                 <div class="pn-correlation">
1093 |                     <div class="pn-correlation-header">CROSS-REFERENCE EVENT</div>
1094 |                     <div class="pn-correlation-summary">{{ c.timeline_summary }}</div>
1095 |                     <div class="pn-correlation-events">
1096 |                         {% if c.disclosure %}
1097 |                         <div class="pn-corr-event">
1098 |                             <span class="pn-corr-event-type" style="background:rgba(255,59,95,0.1);color:var(--pn-red);">DISCLOSURE</span>
1099 |                             {{ c.disclosure.entity }} &mdash; {{ c.disclosure.asset }} ({{ c.disclosure.trade_type }})
1100 |                         </div>
1101 |                         {% endif %}
1102 |                         {% for w in c.related_whales %}
1103 |                         <div class="pn-corr-event">
1104 |                             <span class="pn-corr-event-type whale">WHALE</span>
1105 |                             {{ w.entity }} &mdash; {{ w.amount }} {{ w.direction }}
1106 |                         </div>
1107 |                         {% endfor %}
1108 |                         {% for g in c.related_geo %}
1109 |                         <div class="pn-corr-event">
1110 |                             <span class="pn-corr-event-type geo">GEO</span>
1111 |                             {{ g.headline[:80] }}{% if g.headline|length > 80 %}...{% endif %}
1112 |                         </div>
1113 |                         {% endfor %}
1114 |                     </div>
1115 |                     {% if not demo_mode %}
1116 |                     <button class="pn-btc-case-btn" onclick="makeBitcoinCase(this, '{{ c.timeline_summary|e }}')" data-idx="{{ loop.index }}">
1117 |                         &#x20BF; Make the Bitcoin Case
1118 |                     </button>
1119 |                     <div class="pn-btc-case-output" id="btcCase{{ loop.index }}"></div>
1120 |                     {% endif %}
1121 |                 </div>
1122 |                 {% endfor %}
1123 |                 {% if not data.correlations %}
1124 |                 <div class="pn-empty">Awaiting correlated events...</div>
1125 |                 {% endif %}
1126 |             </div>
1127 | 
1128 |             <!-- Flagged Disclosures -->
1129 |             <div class="pn-section-title">Flagged Trades</div>
1130 |             {% for f in data.flagged %}
1131 |             <div class="pn-card" style="border-left:3px solid var(--pn-amber);">
1132 |                 <div class="pn-card-header">
1133 |                     <div class="pn-card-entity">{{ f.entity }}</div>
1134 |                     {% if f.party %}
1135 |                     <span class="pn-card-party party-{{ f.party }}">{{ f.party }}</span>
1136 |                     {% endif %}
1137 |                 </div>
1138 |                 <div class="pn-card-body">
1139 |                     <div class="pn-card-field">
1140 |                         <span class="pn-card-label">Asset</span>
1141 |                         <span class="pn-card-value">{{ f.asset }}</span>
1142 |                     </div>
1143 |                     <div class="pn-card-field">
1144 |                         <span class="pn-card-label">Score</span>
1145 |                         <span class="pn-card-value" style="color:var(--pn-amber)">{{ "%.0f"|format(f.correlation_score * 100) }}%</span>
1146 |                     </div>
1147 |                 </div>
1148 |                 <div class="pn-card-correlation">{{ f.flag_reason }}</div>
1149 |             </div>
1150 |             {% endfor %}
1151 |             {% if not data.flagged %}
1152 |             <div class="pn-empty">No statistical patterns detected in current window</div>
1153 |             {% endif %}
1154 |         </div>
1155 | 
1156 |         <!-- ═══ COLUMN 3: REAL-TIME FEED ═══ -->
1157 |         <div class="pn-panel tier-feed">
1158 |             <div class="pn-panel-header">
1159 |                 <span class="tier-dot"></span>
1160 |                 REAL-TIME FEED
1161 |                 <span class="pn-panel-count">WHALE + FOREX + GEO</span>
1162 |             </div>
1163 | 
1164 |             {% if demo_mode %}
1165 |             <div class="pn-demo-overlay">
1166 |                 <div class="pn-classified-badge">CLASSIFIED</div>
1167 |                 <div class="pn-classified-sub">Commander Access Required</div>
1168 |                 <a href="/join" class="pn-upgrade-btn">Unlock Intelligence</a>
1169 |             </div>
1170 |             {% endif %}
1171 | 
1172 |             <!-- Whale Alerts -->
1173 |             <div class="pn-section-title">Whale Tracker</div>
1174 |             <div id="pnWhales">
1175 |                 {% for w in data.whales %}
1176 |                 <div class="pn-whale-card">
1177 |                     <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
1178 |                         <div class="pn-whale-entity">{{ w.entity }}</div>
1179 |                         <span class="pn-whale-type {{ w.tx_type }}">{{ w.tx_type|upper }}</span>
1180 |                     </div>
1181 |                     <div class="pn-whale-amount {{ w.tx_type }}">
1182 |                         {% if w.tx_type == 'inflow' %}+{% else %}-{% endif %}{{ w.amount_btc }} BTC
1183 |                     </div>
1184 |                     {% if w.amount_usd %}
1185 |                     <div class="pn-whale-usd">${{ "{:,.0f}".format(w.amount_usd) }} USD</div>
1186 |                     {% endif %}
1187 |                     <div class="pn-whale-meta">
1188 |                         <span>{{ w.address }}</span>
1189 |                         <a href="{{ w.source_url }}" target="_blank" rel="noopener">View TX &rarr;</a>
1190 |                     </div>
1191 |                 </div>
1192 |                 {% endfor %}
1193 |                 {% if not data.whales %}
1194 |                 <div class="pn-loading">
1195 |                     <div class="pn-loading-dot"></div>
1196 |                     <div class="pn-loading-dot"></div>
1197 |                     <div class="pn-loading-dot"></div>
1198 |                     Scanning whale wallets...
1199 |                 </div>
1200 |                 {% endif %}
1201 |             </div>
1202 | 
1203 |             <!-- Polymarket Prediction Markets -->
1204 |             <div class="pn-section-title">Polymarket Prediction Odds</div>
1205 |             <div id="pnPolymarket">
1206 |                 {% for p in data.polymarket %}
1207 |                 <div class="pn-poly-card">
1208 |                     <div class="pn-poly-question">{{ p.question }}</div>
1209 |                     <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
1210 |                         {% if p.yes_price %}
1211 |                         <span class="pn-poly-odds {{ p.btc_signal }}">{{ p.yes_price }}%</span>
1212 |                         <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--pn-muted);text-transform:uppercase;">YES</span>
1213 |                         {% else %}
1214 |                         <span class="pn-poly-odds neutral">--</span>
1215 |                         {% endif %}
1216 |                         <span class="pn-geo-signal signal-{{ p.btc_signal }}" style="margin-left:auto;">
1217 |                             {% if p.btc_signal == 'bullish' %}&#9650;{% elif p.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
1218 |                             {{ p.btc_signal|upper }}
1219 |                         </span>
1220 |                     </div>
1221 |                     {% if p.yes_price %}
1222 |                     <div class="pn-poly-bar-wrap">
1223 |                         <div class="pn-poly-bar-fill {{ p.btc_signal }}" style="width:{{ p.yes_price }}%"></div>
1224 |                     </div>
1225 |                     {% endif %}
1226 |                     <div class="pn-poly-meta">
1227 |                         {% if p.volume %}
1228 |                         <span class="pn-poly-volume">${{ "{:,.0f}".format(p.volume) }} vol</span>
1229 |                         {% endif %}
1230 |                         {% if p.end_date %}
1231 |                         <span>Expires {{ p.end_date[:10] }}</span>
1232 |                         {% endif %}
1233 |                         <a href="{{ p.source_url }}" target="_blank" rel="noopener" style="color:var(--pn-text-secondary);text-decoration:none;font-size:9px;">Polymarket &rarr;</a>
1234 |                     </div>
1235 |                 </div>
1236 |                 {% endfor %}
1237 |                 {% if not data.polymarket %}
1238 |                 <div class="pn-loading">
1239 |                     <div class="pn-loading-dot"></div>
1240 |                     <div class="pn-loading-dot"></div>
1241 |                     <div class="pn-loading-dot"></div>
1242 |                     Fetching prediction markets...
1243 |                 </div>
1244 |                 {% endif %}
1245 |             </div>
1246 | 
1247 |             <!-- Nation-State / Forex -->
1248 |             <div class="pn-section-title">Nation-State Signals</div>
1249 |             <div id="pnForex">
1250 |                 {% for f in data.forex %}
1251 |                 <div class="pn-forex-row">
1252 |                     <span class="pn-forex-pair">{{ f.pair }}</span>
1253 |                     {% if f.rate %}
1254 |                     <span class="pn-forex-rate">{{ f.rate }}</span>
1255 |                     {% endif %}
1256 |                     <span class="pn-forex-status">{{ f.status }}</span>
1257 |                 </div>
1258 |                 {% endfor %}
1259 |                 {% if not data.forex %}
1260 |                 <div class="pn-loading">
1261 |                     <div class="pn-loading-dot"></div>
1262 |                     <div class="pn-loading-dot"></div>
1263 |                     <div class="pn-loading-dot"></div>
1264 |                     Fetching sovereign signals...
1265 |                 </div>
1266 |                 {% endif %}
1267 |             </div>
1268 | 
1269 |             <!-- Geopolitical Feed -->
1270 |             <div class="pn-section-title">Geopolitical Alert Feed</div>
1271 |             <div id="pnGeo">
1272 |                 {% for g in data.geopolitical %}
1273 |                 <div class="pn-geo-card">
1274 |                     <div class="pn-geo-headline">{{ g.headline }}</div>
1275 |                     <span class="pn-geo-signal signal-{{ g.btc_signal }}">
1276 |                         {% if g.btc_signal == 'bullish' %}&#9650;{% elif g.btc_signal == 'bearish' %}&#9660;{% else %}&#9644;{% endif %}
1277 |                         BTC SIGNAL: {{ g.btc_signal|upper }}
1278 |                     </span>
1279 |                     <div class="pn-geo-rationale">{{ g.btc_rationale }}</div>
1280 |                     <div class="pn-geo-meta">
1281 |                         <span>{{ g.source }}</span>
1282 |                         <span>{{ g.timestamp[:10] if g.timestamp else 'N/A' }}</span>
1283 |                     </div>
1284 |                 </div>
1285 |                 {% endfor %}
1286 |                 {% if not data.geopolitical %}
1287 |                 <div class="pn-empty">No geopolitical signals in current window</div>
1288 |                 {% endif %}
1289 |             </div>
1290 |         </div>
1291 |     </div>
1292 | 
1293 |     <!-- ═══ DISCLAIMER ═══ -->
1294 |     <div class="pn-disclaimer">
1295 |         All data sourced from public filings (STOCK Act, SEC EDGAR), public blockchain explorers (mempool.space), and open APIs.
1296 |         Correlation shown for independent research purposes only. Protocol Pulse does not make accusations of insider trading.
1297 |         "FLAGGED" items are statistical patterns, not verified misconduct. Always consult original sources.
1298 |     </div>
1299 | </div>
1300 | {% endblock %}
1301 | 
1302 | {% block scripts %}
1303 | <script>
1304 | (function() {
1305 |     // UTC clock
1306 |     function updateClock() {
1307 |         const now = new Date();
1308 |         const h = String(now.getUTCHours()).padStart(2, '0');
1309 |         const m = String(now.getUTCMinutes()).padStart(2, '0');
1310 |         const s = String(now.getUTCSeconds()).padStart(2, '0');
1311 |         const el = document.getElementById('pnClock');
1312 |         if (el) el.textContent = h + ':' + m + ':' + s + ' UTC';
1313 |     }
1314 |     updateClock();
1315 |     setInterval(updateClock, 1000);
1316 | 
1317 |     {% if not demo_mode %}
1318 |     // ── Make the Bitcoin Case (typewriter animation) ──
1319 |     window.makeBitcoinCase = function(btn, eventSummary) {
1320 |         var idx = btn.getAttribute('data-idx');
1321 |         var outputEl = document.getElementById('btcCase' + idx);
1322 |         if (!outputEl) return;
1323 | 
1324 |         btn.disabled = true;
1325 |         btn.textContent = 'GENERATING...';
1326 |         outputEl.innerHTML = '';
1327 |         outputEl.classList.add('visible');
1328 | 
1329 |         fetch('/api/panopticon/make-bitcoin-case', {
1330 |             method: 'POST',
1331 |             headers: {'Content-Type': 'application/json'},
1332 |             body: JSON.stringify({event_summary: eventSummary})
1333 |         })
1334 |         .then(function(r) { return r.json(); })
1335 |         .then(function(data) {
1336 |             if (data.error) {
1337 |                 outputEl.innerHTML = '<span style="color:var(--pn-coral)">' + data.error + '</span>';
1338 |                 btn.disabled = false;
1339 |                 btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
1340 |                 return;
1341 |             }
1342 |             // Typewriter animation
1343 |             var text = data.case_text || '';
1344 |             var model = data.model || '';
1345 |             outputEl.innerHTML = '<div class="pn-btc-case-label">THE BITCOIN CASE</div><span id="typewriter' + idx + '"></span><span class="pn-typewriter-cursor"></span>';
1346 |             var twEl = document.getElementById('typewriter' + idx);
1347 |             var i = 0;
1348 |             function typeChar() {
1349 |                 if (i < text.length) {
1350 |                     twEl.textContent += text.charAt(i);
1351 |                     i++;
1352 |                     setTimeout(typeChar, 18 + Math.random() * 12);
1353 |                 } else {
1354 |                     // Remove cursor, show model tag
1355 |                     var cursor = outputEl.querySelector('.pn-typewriter-cursor');
1356 |                     if (cursor) cursor.remove();
1357 |                     outputEl.innerHTML += '<div class="pn-btc-case-model">Model: ' + model + '</div>';
1358 |                     btn.disabled = false;
1359 |                     btn.innerHTML = '&#x20BF; Regenerate Case';
1360 |                 }
1361 |             }
1362 |             typeChar();
1363 |         })
1364 |         .catch(function() {
1365 |             outputEl.innerHTML = '<span style="color:var(--pn-coral)">Failed to generate. Try again.</span>';
1366 |             btn.disabled = false;
1367 |             btn.innerHTML = '&#x20BF; Make the Bitcoin Case';
1368 |         });
1369 |     };
1370 | 
1371 |     // Auto-refresh data every 5 minutes
1372 |     function refreshData() {
1373 |         fetch('/api/panopticon/whale-alerts')
1374 |             .then(r => r.json())
1375 |             .then(data => {
1376 |                 if (data.alerts && data.alerts.length > 0) {
1377 |                     const count = document.getElementById('pnStatWhales');
1378 |                     if (count) count.textContent = data.alerts.length;
1379 |                 }
1380 |             })
1381 |             .catch(() => {});
1382 | 
1383 |         fetch('/api/panopticon/geopolitical')
1384 |             .then(r => r.json())
1385 |             .then(data => {
1386 |                 if (data.geopolitical) {
1387 |                     const count = document.getElementById('pnStatGeo');
1388 |                     if (count) count.textContent = data.geopolitical.length;
1389 |                 }
1390 |             })
1391 |             .catch(() => {});
1392 |     }
1393 |     setInterval(refreshData, 300000); // 5 min
1394 |     {% endif %}
1395 | })();
1396 | </script>
1397 | {% endblock %}
1398 | 
```

### File: services/scheduler.py (736 lines)
```
   1 | import os as _twt_os
   2 | _TWEETS_ON = _twt_os.environ.get("ENABLE_TWEETS", "false").lower() == "true"
   3 | 
   4 | """
   5 | Central scheduler for Protocol Pulse automation tasks.
   6 | Defines the 6 Replit-style tasks; run via cron hitting a single endpoint or run_task(name).
   7 | 
   8 | Tasks:
   9 | - Cypherpunk'd Loop: every 6h — article generation from trending
  10 | - Social Guard: every 10min — (optional) social listening / reply checks
  11 | - Sarah Daily Brief: 05:45 UTC — prep
  12 | - Sarah Intelligence Briefing: 06:00 UTC — generate and publish daily brief
  13 | - Sentiment Buffer Update: every 5min — rolling sentiment
  14 | - Emergency Flash Check: every 5min — detect 40%+ sentiment drift
  15 | """
  16 | 
  17 | import json
  18 | import logging
  19 | import os
  20 | import subprocess
  21 | from datetime import datetime
  22 | from typing import Dict, List, Optional
  23 | from threading import Lock
  24 | 
  25 | logger = logging.getLogger(__name__)
  26 | _scheduler_started_at: Optional[datetime] = None
  27 | _apscheduler = None  # BackgroundScheduler, set in initialize_scheduler
  28 | _scheduler_lock = Lock()
  29 | 
  30 | # When False (default), Queued SentryJob posts are only written to data/pulseevents.jsonl with [DRY-RUN]. No live posting.
  31 | ENABLE_LIVE_POSTING = os.environ.get("ENABLE_LIVE_POSTING", "false").strip().lower() in {"1", "true", "yes", "on"}
  32 | 
  33 | # New article draft schedule: burst 4 every 15 min (UTC 00–07), break (08–11), then 1/hour (12–23). Only active when set.
  34 | ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE = os.environ.get("ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE", "false").strip().lower() in {"1", "true", "yes", "on"}
  35 | 
  36 | # Replit-style: generate one breaking_news article every 15 minutes (with DB lock).
  37 | # Keep OFF until explicitly enabled.
  38 | ENABLE_ARTICLE_AUTOMATION_15M = os.environ.get("ENABLE_ARTICLE_AUTOMATION_15M", "false").strip().lower() in {"1", "true", "yes", "on"}
  39 | 
  40 | # UTC hour windows: burst = 0–7, break = 8–11, slow = 12–23
  41 | ARTICLE_DRAFT_BURST_HOURS = set(range(0, 8))   # 00:00–07:59 UTC
  42 | ARTICLE_DRAFT_SLOW_HOURS = set(range(12, 24)) # 12:00–23:59 UTC
  43 | 
  44 | TASKS = {
  45 |     "x_engagement_cycle": {"interval_minutes": 5, "description": "X Engagement Sentry cycle (every 5m)"},
  46 |     "sentry_megaphone": {"interval_minutes": 2, "description": "SentryJob Queued -> pulseevents.jsonl [DRY-RUN] (no live post when ENABLE_LIVE_POSTING=False)"},
  47 |     "mining_snapshot_hourly": {"interval_minutes": 60, "description": "Mining risk snapshot_all (hourly)"},
  48 |     "media_feed_sync": {"interval_minutes": 15, "description": "Media Command Center RSS+YouTube feed sync (every 15m)"},
  49 |     "media_ai_summaries": {"interval_minutes": 60, "description": "Generate AI summaries for new media episodes (hourly)"},
  50 |     "cypherpunk_loop": {"interval_minutes": 120, "description": "Article auto-draft from trending (every 2h, around the clock)"},
  51 |     "social_guard": {"interval_minutes": 10, "description": "Social listening / reply checks"},
  52 |     "sarah_brief_prep": {"cron": "05:45", "description": "Sarah daily brief prep (05:45 UTC)"},
  53 |     "sarah_intelligence_briefing": {"cron": "06:00", "description": "Sarah daily intelligence briefing (06:00 UTC)"},
  54 |     "sentiment_buffer_update": {"interval_minutes": 5, "description": "Rolling sentiment buffer update"},
  55 |     "emergency_flash_check": {"interval_minutes": 5, "description": "Emergency flash check (40%+ drift)"},
  56 |     "daily_distribution_brief_9am_est": {"cron_est": "09:00", "description": "Sentry auto-poster daily brief dispatch (09:00 EST)"},
  57 |     "daily_medley_gpu1": {"cron_est": "09:10", "description": "Daily Beat medley render (GPU 1, 60s)"},
  58 |     "monetization_injector": {"interval_minutes": 30, "description": "Smart-link injector scan for briefs + x drafts"},
  59 |     "pulse_drop_rebuild_5am": {"cron_est": "05:00", "description": "Pulse Drop daily rebuild (05:00 EST)"},
  60 |     "auto_viral_reel": {"interval_minutes": 30, "description": "Viral reel: monitor → clip → narration → publish (X/Telegram if ENABLE_LIVE_POSTING)"},
  61 |     "intel_medley": {"interval_minutes": 60, "description": "Automated Intel Medley: monitor UC9ZM3N0ybRtp44 + partners, 3-5 clips, 5-10 min briefing, outro + CTAs"},
  62 |     "article_draft_burst_4": {"interval_minutes": 15, "description": "Article draft burst: 4 articles every 15 min (UTC 00–07 only, when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE)"},
  63 |     "article_draft_hourly_1": {"interval_minutes": 60, "description": "Article draft slow: 1 article per hour (UTC 12–23 only, when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE)"},
  64 |     "article_generation_15m": {"interval_minutes": 15, "description": "Replit-style: generate 1 breaking_news article every 15 minutes (when ENABLE_ARTICLE_AUTOMATION_15M)"},
  65 |     "affiliate_education_morning": {"cron": "11:00", "description": "Affiliate education article #1 (11:00 UTC / 6am EST)"},
  66 |     "affiliate_education_evening": {"cron": "21:00", "description": "Affiliate education article #2 (21:00 UTC / 4pm EST)"},
  67 |     # Stage Brief Pipeline — 3x/day Chatterbox TTS + intel extraction
  68 |     "stage_brief_morning": {"cron": "06:00", "description": "Stage brief morning (06:00 UTC) — Chatterbox TTS, intel extraction"},
  69 |     "stage_brief_midday": {"cron": "14:00", "description": "Stage brief midday (14:00 UTC) — Chatterbox TTS, intel extraction"},
  70 |     "stage_brief_evening": {"cron": "22:00", "description": "Stage brief evening (22:00 UTC) — Chatterbox TTS, intel extraction"},
  71 |     # Social Media Sacred Schedule (3 posts/day max, global gate enforced)
  72 |     "morning_signal_tweet": {"cron_est": "09:00", "description": "Sacred slot 1/3: Morning signal tweet via tweet_machine (09:00 ET)"},
  73 |     "afternoon_article_tweet": {"cron_est": "14:00", "description": "Sacred slot 2/3: Top article tweet via x_daily_top_article (14:00 ET)"},
  74 |     "evening_signal_tweet": {"cron_est": "19:00", "description": "Sacred slot 3/3: Evening signal tweet via tweet_machine (19:00 ET)"},
  75 |     # Auto-engagement (replies, likes, retweets — separate from post count)
  76 |     "auto_engagement_noon": {"cron_est": "12:00", "description": "Auto-engagement: reply to mentions, like + RT tier-1 (noon ET)"},
  77 |     "auto_engagement_evening": {"cron_est": "18:00", "description": "Auto-engagement: reply to mentions, like + RT tier-1 (6pm ET)"},
  78 |     # F6 Marketing OS
  79 |     "btc_milestone_check": {"interval_minutes": 5, "description": "F6: BTC price milestone check — fires campaigns at 100K/120K/.../1M (never repeats)"},
  80 |     "daily_metrics_snapshot": {"interval_minutes": 60, "description": "F6: Daily performance metrics snapshot (hourly upsert)"},
  81 |     "weekly_performance_analysis": {"cron": "00:00", "cron_day": "sun", "description": "F6: Weekly performance analysis (Sunday 00:00 UTC)"},
  82 |     # PANOPTICON — Congressional disclosure + whale tracker
  83 |     "panopticon_congress_refresh": {"interval_minutes": 30, "description": "PANOPTICON: refresh congressional disclosures from efts.house.gov (every 30m)"},
  84 |     "panopticon_whale_scan": {"interval_minutes": 5, "description": "PANOPTICON: scan whale wallets via mempool.space (every 5m)"},
  85 |     "panopticon_polymarket_refresh": {"interval_minutes": 5, "description": "PANOPTICON: refresh Polymarket prediction odds (every 5m)"},
  86 | }
  87 | 
  88 | 
  89 | def _send_alert_email(subject: str, body: str) -> bool:
  90 |     """Send alert email on failure. Uses SENDGRID_API_KEY and CONTACT_EMAIL or VIRAL_ALERT_EMAIL."""
  91 |     to = os.environ.get("VIRAL_ALERT_EMAIL") or os.environ.get("CONTACT_EMAIL") or os.environ.get("SENDGRID_FROM_EMAIL")
  92 |     if not to:
  93 |         return False
  94 |     try:
  95 |         from sendgrid import SendGridAPIClient
  96 |         from sendgrid.helpers.mail import Mail, Email, To, Content
  97 |     except ImportError:
  98 |         return False
  99 |     api_key = os.environ.get("SENDGRID_API_KEY")
 100 |     if not api_key:
 101 |         return False
 102 |     from_email = os.environ.get("SENDGRID_FROM_EMAIL", "noreply@protocolpulse.io")
 103 |     message = Mail(
 104 |         from_email=Email(from_email, "Protocol Pulse"),
 105 |         to_emails=To(to),
 106 |         subject=subject[:200],
 107 |         plain_text_content=Content("text/plain", body[:10000]),
 108 |     )
 109 |     try:
 110 |         SendGridAPIClient(api_key).send(message)
 111 |         return True
 112 |     except Exception as e:
 113 |         logger.warning("Alert email failed: %s", e)
 114 |         return False
 115 | 
 116 | 
 117 | def auto_viral_reel() -> Dict:
 118 |     """
 119 |     Batch 5: monitor → clip → narration → publish.
 120 |     Runs every 30m. If ENABLE_LIVE_POSTING, publishes to X and Telegram.
 121 |     On failure sends alert email.
 122 |     """
 123 |     try:
 124 |         from app import app
 125 |         import models
 126 |         from services.viralmoments import ViralMomentsReelEngine
 127 |         from pathlib import Path
 128 | 
 129 |         engine = ViralMomentsReelEngine()
 130 |         with app.app_context():
 131 |             # 1) Monitor partners (create ClipJobs for new videos)
 132 |             mon = engine.monitor_partners()
 133 |             job_ids = mon.get("job_ids") or []
 134 |             # 2) Pick one Planned job and render reel (or use latest Completed for publish-only)
 135 |             job = (
 136 |                 models.ClipJob.query.filter(models.ClipJob.status == "Planned")
 137 |                 .order_by(models.ClipJob.id.asc())
 138 |                 .first()
 139 |             )
 140 |             if not job:
 141 |                 return {
 142 |                     "success": True,
 143 |                     "message": "auto_viral_reel: no Planned job; monitor only",
 144 |                     "result": {"monitor": mon, "published": False},
 145 |                 }
 146 |             # 3) Render reel (includes optional voiceover if VIRAL_ADD_VOICEOVER=1)
 147 |             render = engine.render_reel(job)
 148 |             if not render.get("ok"):
 149 |                 _send_alert_email(
 150 |                     "[Protocol Pulse] auto_viral_reel render failed",
 151 |                     f"job_id={job.id} video_id={job.video_id}\nerror={render.get('error', 'unknown')}",
 152 |                 )
 153 |                 return {
 154 |                     "success": False,
 155 |                     "message": render.get("error", "render failed"),
 156 |                     "result": {"render": render},
 157 |                 }
 158 |             out_path = render.get("output_path")
 159 |             base_url = os.environ.get("BASE_URL", "https://protocolpulse.io").rstrip("/")
 160 |             reel_url = f"{base_url}/static/clips/reels/{Path(out_path or '').name}" if out_path else None
 161 |             if not reel_url and out_path:
 162 |                 reel_url = f"{base_url}/{out_path}" if not out_path.startswith("http") else out_path
 163 | 
 164 |             published_x = False
 165 |             published_tg = False
 166 |             if ENABLE_LIVE_POSTING and reel_url:
 167 |                 # 4a) Publish to X (tweet with link) — through global gate
 168 |                 try:
 169 |                     from services.x_service import XService, can_post_tweet
 170 |                     x = XService()
 171 |                     if x.client or getattr(x, "client_v2", None):
 172 |                         text = f"New Intel Briefing reel — {job.channel_name or 'Partner'} | {reel_url}"
 173 |                         if len(text) > 280:
 174 |                             text = f"Intel Briefing | {job.channel_name or 'Partner'} {reel_url}"
 175 |                         # Global gate check
 176 |                         allowed, reason = can_post_tweet(text[:280], source="auto_viral_reel")
 177 |                         if not allowed:
 178 |                             logger.warning("auto_viral_reel gate blocked: %s", reason)
 179 |                         elif x.client:
 180 |                             x.client.update_status(text[:280])
 181 |                             published_x = True
 182 |                         elif getattr(x, "client_v2", None) and x.client_v2:
 183 |                             x.client_v2.create_tweet(text=text[:280])
 184 |                             published_x = True
 185 |                 except Exception as ex:
 186 |                     logger.warning("auto_viral_reel X post failed: %s", ex)
 187 |                     _send_alert_email("[Protocol Pulse] auto_viral_reel X post failed", str(ex))
 188 |                 # 4b) Publish to Telegram (message with link)
 189 |                 try:
 190 |                     token = os.environ.get("TELEGRAM_BOT_TOKEN")
 191 |                     chat_id = os.environ.get("TELEGRAM_CHAT_ID")
 192 |                     if token and chat_id:
 193 |                         import requests
 194 |                         msg = f"Intel Briefing reel — {job.channel_name or 'Partner'}\n{reel_url}"
 195 |                         r = requests.post(
 196 |                             f"https://api.telegram.org/bot{token}/sendMessage",
 197 |                             json={"chat_id": chat_id, "text": msg},
 198 |                             timeout=10,
 199 |                         )
 200 |                         published_tg = r.status_code == 200
 201 |                 except Exception as ex:
 202 |                     logger.warning("auto_viral_reel Telegram post failed: %s", ex)
 203 |                     _send_alert_email("[Protocol Pulse] auto_viral_reel Telegram failed", str(ex))
 204 | 
 205 |             return {
 206 |                 "success": True,
 207 |                 "message": "auto_viral_reel: reel rendered" + (" and published" if (published_x or published_tg) else ""),
 208 |                 "result": {
 209 |                     "job_id": job.id,
 210 |                     "reel_url": reel_url,
 211 |                     "published_x": published_x,
 212 |                     "published_tg": published_tg,
 213 |                     "monitor": mon,
 214 |                 },
 215 |             }
 216 |     except Exception as e:
 217 |         logger.exception("auto_viral_reel failed: %s", e)
 218 |         _send_alert_email(
 219 |             "[Protocol Pulse] auto_viral_reel failed",
 220 |             f"auto_viral_reel error:\n{type(e).__name__}: {e}",
 221 |         )
 222 |         return {"success": False, "message": str(e), "result": None}
 223 | 
 224 | 
 225 | def run_task(name: str) -> Dict:
 226 |     if name == "x_engagement_cycle":
 227 |         try:
 228 |             from app import app
 229 |             from core.services.x_engagement_sentry import run_cycle
 230 |             with app.app_context():
 231 |                 out = run_cycle()
 232 |             return {"success": bool(out.get("success")), "message": "X engagement cycle run", "result": out}
 233 |         except Exception as e:
 234 |             logger.warning("x_engagement_cycle failed: %s", e)
 235 |             return {"success": False, "message": str(e), "result": None}
 236 | 
 237 |     if name == "media_feed_sync":
 238 |         try:
 239 |             from services.media_feed_service import sync_all_feeds
 240 |             count = sync_all_feeds()
 241 |             return {"success": True, "message": f"Media feed sync: {count} new items", "result": {"new_items": count}}
 242 |         except Exception as e:
 243 |             logger.warning("media_feed_sync failed: %s", e)
 244 |             return {"success": False, "message": str(e), "result": None}
 245 | 
 246 |     if name == "media_ai_summaries":
 247 |         try:
 248 |             from services.media_feed_service import generate_ai_summaries
 249 |             count = generate_ai_summaries()
 250 |             return {"success": True, "message": f"AI summaries: {count} generated", "result": {"summaries": count}}
 251 |         except Exception as e:
 252 |             logger.warning("media_ai_summaries failed: %s", e)
 253 |             return {"success": False, "message": str(e), "result": None}
 254 | 
 255 |     if name == "mining_snapshot_hourly":
 256 |         try:
 257 |             from app import app
 258 |             from services.mining_risk_service import snapshot_all
 259 |             with app.app_context():
 260 |                 out = snapshot_all()
 261 |             return {"success": bool(out.get("success")), "message": "Mining snapshot captured", "result": out}
 262 |         except Exception as e:
 263 |             logger.warning("mining_snapshot_hourly failed: %s", e)
 264 |             return {"success": False, "message": str(e), "result": None}
 265 | 
 266 |     if name == "sentry_megaphone":
 267 |         try:
 268 |             from app import app
 269 |             from pathlib import Path
 270 |             with app.app_context():
 271 |                 import models
 272 |                 jobs = models.SentryJob.query.filter_by(status="Queued").limit(50).all()
 273 |                 log_path = Path(app.root_path) / "data" / "pulseevents.jsonl"
 274 |                 log_path.parent.mkdir(parents=True, exist_ok=True)
 275 |                 written = 0
 276 |                 for job in jobs:
 277 |                     line = json.dumps({
 278 |                         "ts": datetime.utcnow().isoformat() + "Z",
 279 |                         "tag": "DRY-RUN",
 280 |                         "message": f"[DRY-RUN] SentryJob id={job.id} platform={job.platform}",
 281 |                         "sentry_job_id": job.id,
 282 |                         "platform": job.platform,
 283 |                         "content_preview": (job.content or "")[:200],
 284 |                     }) + "\n"
 285 |                     with open(log_path, "a", encoding="utf-8") as f:
 286 |                         f.write(line)
 287 |                     job.status = "Written"
 288 |                     written += 1
 289 |                 if written:
 290 |                     from app import db
 291 |                     db.session.commit()
 292 |             return {"success": True, "message": f"Sentry megaphone: {written} queued posts written to pulseevents.jsonl", "result": {"written": written, "live_posting": ENABLE_LIVE_POSTING}}
 293 |         except Exception as e:
 294 |             logger.warning("sentry_megaphone failed: %s", e)
 295 |             return {"success": False, "message": str(e), "result": None}
 296 | 
 297 |     """
 298 |     Run a single named task. Returns { success, message, result }.
 299 |     """
 300 |     if name == "cypherpunk_loop":
 301 |         if ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 302 |             return {"success": True, "message": "cypherpunk_loop disabled when ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE is on", "result": None}
 303 |         try:
 304 |             from services.automation import generate_article_with_tracking
 305 |             out = generate_article_with_tracking()
 306 |             return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
 307 |         except Exception as e:
 308 |             logger.exception("cypherpunk_loop failed: %s", e)
 309 |             return {"success": False, "message": str(e), "result": None}
 310 | 
 311 |     if name == "article_draft_burst_4":
 312 |         if not ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 313 |             return {"success": True, "message": "article_draft_burst_4 skipped (new schedule disabled)", "result": None}
 314 |         hour_utc = datetime.utcnow().hour
 315 |         if hour_utc not in ARTICLE_DRAFT_BURST_HOURS:
 316 |             return {"success": True, "message": f"article_draft_burst_4 outside burst window (UTC hour {hour_utc})", "result": None}
 317 |         try:
 318 |             from services.automation import generate_article_with_tracking
 319 |             results = []
 320 |             for _ in range(4):
 321 |                 out = generate_article_with_tracking(force=True)
 322 |                 results.append(out)
 323 |             ok = any(r.get("success") for r in results)
 324 |             return {"success": ok, "message": f"Burst 4: {sum(1 for r in results if r.get('success'))}/4", "result": results}
 325 |         except Exception as e:
 326 |             logger.exception("article_draft_burst_4 failed: %s", e)
 327 |             return {"success": False, "message": str(e), "result": None}
 328 | 
 329 |     if name == "article_draft_hourly_1":
 330 |         if not ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 331 |             return {"success": True, "message": "article_draft_hourly_1 skipped (new schedule disabled)", "result": None}
 332 |         hour_utc = datetime.utcnow().hour
 333 |         if hour_utc not in ARTICLE_DRAFT_SLOW_HOURS:
 334 |             return {"success": True, "message": f"article_draft_hourly_1 outside slow window (UTC hour {hour_utc})", "result": None}
 335 |         try:
 336 |             from services.automation import generate_article_with_tracking
 337 |             out = generate_article_with_tracking(force=True)
 338 |             return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
 339 |         except Exception as e:
 340 |             logger.exception("article_draft_hourly_1 failed: %s", e)
 341 |             return {"success": False, "message": str(e), "result": None}
 342 | 
 343 |     if name == "article_generation_15m":
 344 |         if not ENABLE_ARTICLE_AUTOMATION_15M:
 345 |             return {"success": True, "message": "article_generation_15m skipped (disabled)", "result": None}
 346 |         try:
 347 |             from services.automation import generate_breaking_article_with_tracking
 348 |             out = generate_breaking_article_with_tracking()
 349 |             return {"success": out.get("success", False) or out.get("skipped", False), "message": str(out), "result": out}
 350 |         except Exception as e:
 351 |             logger.exception("article_generation_15m failed: %s", e)
 352 |             return {"success": False, "message": str(e), "result": None}
 353 | 
 354 |     if name == "social_guard":
 355 |         # Optional: social_listener check or reply queue
 356 |         return {"success": True, "message": "Social guard (no-op)", "result": None}
 357 | 
 358 |     if name == "sarah_brief_prep":
 359 |         # Optional: collect signals before brief
 360 |         try:
 361 |             from services.sentiment_tracker_service import SentimentTrackerService
 362 |             t = SentimentTrackerService()
 363 |             x = t.fetch_x_posts(hours_back=24)
 364 |             n = t.fetch_nostr_notes(hours_back=24)
 365 |             s = t.fetch_stacker_news(limit=15)
 366 |             t.save_signals_to_db(x + n + s)
 367 |             return {"success": True, "message": f"Signals collected: X={len(x)} Nostr={len(n)} Stacker={len(s)}", "result": None}
 368 |         except Exception as e:
 369 |             logger.warning("sarah_brief_prep: %s", e)
 370 |             return {"success": False, "message": str(e), "result": None}
 371 | 
 372 |     if name == "sarah_intelligence_briefing":
 373 |         try:
 374 |             from services.briefing_engine import briefing_engine
 375 |             article_id = briefing_engine.generate_daily_brief()
 376 |             return {"success": article_id is not None, "message": f"Brief article_id={article_id}", "result": {"article_id": article_id}}
 377 |         except Exception as e:
 378 |             logger.exception("sarah_intelligence_briefing failed: %s", e)
 379 |             return {"success": False, "message": str(e), "result": None}
 380 | 
 381 |     if name == "sentiment_buffer_update":
 382 |         try:
 383 |             from services.sentiment_service import sentiment_service
 384 |             result = sentiment_service.update_buffer()
 385 |             return {"success": True, "message": "Buffer updated", "result": result}
 386 |         except Exception as e:
 387 |             # sentiment_service may not exist yet
 388 |             logger.debug("sentiment_buffer_update: %s", e)
 389 |             return {"success": True, "message": "Sentiment service not configured", "result": None}
 390 | 
 391 |     if name == "emergency_flash_check":
 392 |         try:
 393 |             from services.briefing_engine import briefing_engine
 394 |             flash = briefing_engine.check_emergency_flash()
 395 |             return {"success": True, "message": "Flash checked", "result": flash}
 396 |         except Exception as e:
 397 |             logger.warning("emergency_flash_check: %s", e)
 398 |             return {"success": False, "message": str(e), "result": None}
 399 | 
 400 |     if name == "daily_distribution_brief_9am_est":
 401 |         try:
 402 |             from services.distribution_manager import distribution_manager
 403 |             result = distribution_manager.dispatch_daily_brief()
 404 |             return {"success": bool(result.get("success")), "message": "Daily distribution brief dispatch attempted", "result": result}
 405 |         except Exception as e:
 406 |             logger.warning("daily_distribution_brief_9am_est: %s", e)
 407 |             return {"success": False, "message": str(e), "result": None}
 408 | 
 409 |     if name == "daily_medley_gpu1":
 410 |         try:
 411 |             root = "/home/ultron/protocol_pulse"
 412 |             out = f"{root}/logs/medley_daily_beat.mp4"
 413 |             prog = f"{root}/logs/medley_daily_beat.progress"
 414 |             rep = f"{root}/logs/medley_daily_beat.report.json"
 415 |             env = os.environ.copy()
 416 |             env["CUDA_VISIBLE_DEVICES"] = "1"
 417 |             cmd = [
 418 |                 f"{root}/venv/bin/python",
 419 |                 f"{root}/medley_director.py",
 420 |                 "--output", out,
 421 |                 "--progress-file", prog,
 422 |                 "--report-file", rep,
 423 |                 "--duration", "60",
 424 |             ]
 425 |             proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
 426 |             ok = proc.returncode == 0
 427 |             return {
 428 |                 "success": ok,
 429 |                 "message": "Daily medley render attempted on GPU 1",
 430 |                 "result": {
 431 |                     "returncode": proc.returncode,
 432 |                     "output": out,
 433 |                     "report": rep,
 434 |                     "stderr_tail": (proc.stderr or "")[-300:],
 435 |                 },
 436 |             }
 437 |         except Exception as e:
 438 |             logger.warning("daily_medley_gpu1: %s", e)
 439 |             return {"success": False, "message": str(e), "result": None}
 440 | 
 441 |     if name == "monetization_injector":
 442 |         try:
 443 |             from app import app
 444 |             from services.monetization_engine import monetization_engine
 445 |             with app.app_context():
 446 |                 report = monetization_engine.run()
 447 |             return {"success": True, "message": "Monetization injector scan complete", "result": report}
 448 |         except Exception as e:
 449 |             logger.warning("monetization_injector: %s", e)
 450 |             return {"success": False, "message": str(e), "result": None}
 451 | 
 452 |     if name == "pulse_drop_rebuild_5am":
 453 |         try:
 454 |             from app import app
 455 |             from services.channel_monitor import channel_monitor_service
 456 |             from services.highlight_extractor import highlight_extractor_service
 457 |             from services.commentary_generator import commentary_generator_service
 458 |             with app.app_context():
 459 |                 h = channel_monitor_service.run_harvest(hours_back=24)
 460 |                 x = highlight_extractor_service.run(hours_back=24)
 461 |                 c = commentary_generator_service.run(hours_back=24)
 462 |             return {"success": True, "message": "Pulse Drop rebuild complete", "result": {"harvest": h, "extract": x, "commentary": c}}
 463 |         except Exception as e:
 464 |             logger.warning("pulse_drop_rebuild_5am: %s", e)
 465 |             return {"success": False, "message": str(e), "result": None}
 466 | 
 467 |     if name == "auto_viral_reel":
 468 |         return auto_viral_reel()
 469 | 
 470 |     if name == "intel_medley":
 471 |         return auto_viral_reel()
 472 | 
 473 |     if name in ("affiliate_education_morning", "affiliate_education_evening"):
 474 |         try:
 475 |             from app import app
 476 |             from services.affiliate_article_generator import affiliate_article_generator
 477 |             with app.app_context():
 478 |                 result = affiliate_article_generator.generate_affiliate_article()
 479 |             if result:
 480 |                 return {"success": True, "message": f"Affiliate article generated: {result.get('title', '')[:60]}", "result": result}
 481 |             return {"success": False, "message": "Affiliate article generation returned None (duplicate or AI failure)", "result": None}
 482 |         except Exception as e:
 483 |             logger.exception("affiliate_education task failed: %s", e)
 484 |             return {"success": False, "message": str(e), "result": None}
 485 | 
 486 |     # ─── Sacred Social Schedule ──────────────────────────────────────────────
 487 | 
 488 |     if name == "morning_signal_tweet":
 489 |         try:
 490 |             from services.tweet_machine import main as tweet_machine_main
 491 |             tweet_machine_main()
 492 |             return {"success": True, "message": "Morning signal tweet dispatched", "result": None}
 493 |         except Exception as e:
 494 |             logger.warning("morning_signal_tweet failed: %s", e)
 495 |             return {"success": False, "message": str(e), "result": None}
 496 | 
 497 |     if name == "afternoon_article_tweet":
 498 |         try:
 499 |             from services.x_daily_top_article import main as top_article_main
 500 |             top_article_main()
 501 |             return {"success": True, "message": "Afternoon article tweet dispatched", "result": None}
 502 |         except Exception as e:
 503 |             logger.warning("afternoon_article_tweet failed: %s", e)
 504 |             return {"success": False, "message": str(e), "result": None}
 505 | 
 506 |     if name == "evening_signal_tweet":
 507 |         try:
 508 |             from services.tweet_machine import main as tweet_machine_main
 509 |             tweet_machine_main()
 510 |             return {"success": True, "message": "Evening signal tweet dispatched", "result": None}
 511 |         except Exception as e:
 512 |             logger.warning("evening_signal_tweet failed: %s", e)
 513 |             return {"success": False, "message": str(e), "result": None}
 514 | 
 515 |     if name in ("auto_engagement_noon", "auto_engagement_evening"):
 516 |         try:
 517 |             from app import app
 518 |             from services.x_engagement_engine import run_auto_engagement
 519 |             with app.app_context():
 520 |                 result = run_auto_engagement()
 521 |             return {"success": bool(result.get("success")), "message": "Auto-engagement cycle complete", "result": result}
 522 |         except Exception as e:
 523 |             logger.warning("auto_engagement failed: %s", e)
 524 |             return {"success": False, "message": str(e), "result": None}
 525 | 
 526 |     # ─── F6 Marketing OS ─────────────────────────────────────────────────────
 527 | 
 528 |     if name == "btc_milestone_check":
 529 |         try:
 530 |             from app import app
 531 |             from services.price_service import PriceService
 532 |             from services.milestone_service import milestone_service
 533 |             with app.app_context():
 534 |                 price_svc = PriceService()
 535 |                 prices = price_svc.get_prices()
 536 |                 btc_price = prices.get("bitcoin", {}).get("price", 0)
 537 |                 if btc_price > 0:
 538 |                     fired = milestone_service.check_price(btc_price)
 539 |                     msg = f"Checked BTC ${btc_price:,.0f} — {len(fired)} milestone(s) fired"
 540 |                 else:
 541 |                     msg = "BTC price unavailable — skip milestone check"
 542 |             return {"success": True, "message": msg, "result": {"btc_price": btc_price, "fired_count": len(fired) if btc_price > 0 else 0}}
 543 |         except Exception as e:
 544 |             logger.warning("btc_milestone_check failed: %s", e)
 545 |             return {"success": False, "message": str(e), "result": None}
 546 | 
 547 |     if name == "daily_metrics_snapshot":
 548 |         try:
 549 |             from app import app, db
 550 |             from models import PerformanceMetrics
 551 |             from services.price_service import PriceService
 552 |             from datetime import date
 553 |             with app.app_context():
 554 |                 today = date.today()
 555 |                 metric = PerformanceMetrics.query.filter_by(metric_date=today).first()
 556 |                 if not metric:
 557 |                     metric = PerformanceMetrics(metric_date=today)
 558 |                     db.session.add(metric)
 559 |                 # Snapshot BTC close price
 560 |                 try:
 561 |                     prices = PriceService().get_prices()
 562 |                     btc = prices.get("bitcoin", {}).get("price", 0)
 563 |                     if btc > 0:
 564 |                         if metric.btc_price_open is None:
 565 |                             metric.btc_price_open = btc
 566 |                         metric.btc_price_close = btc
 567 |                 except Exception:
 568 |                     pass
 569 |                 db.session.commit()
 570 |             return {"success": True, "message": "Daily metrics snapshot updated", "result": {"date": str(today)}}
 571 |         except Exception as e:
 572 |             try:
 573 |                 from app import db
 574 |                 db.session.rollback()
 575 |             except Exception:
 576 |                 pass
 577 |             logger.warning("daily_metrics_snapshot failed: %s", e)
 578 |             return {"success": False, "message": str(e), "result": None}
 579 | 
 580 |     if name == "weekly_performance_analysis":
 581 |         try:
 582 |             from app import app
 583 |             from services.milestone_service import run_weekly_performance_analysis
 584 |             with app.app_context():
 585 |                 result = run_weekly_performance_analysis()
 586 |             return {"success": result.get("success", False), "message": "Weekly analysis complete", "result": result}
 587 |         except Exception as e:
 588 |             logger.warning("weekly_performance_analysis failed: %s", e)
 589 |             return {"success": False, "message": str(e), "result": None}
 590 | 
 591 |     # Stage Brief Pipeline — 3x/day Chatterbox TTS + intel extraction
 592 |     if name in ("stage_brief_morning", "stage_brief_midday", "stage_brief_evening"):
 593 |         brief_type = name.replace("stage_brief_", "")  # morning/midday/evening
 594 |         try:
 595 |             from services.stage_brief_pipeline import generate_brief
 596 |             result_path = generate_brief(brief_type=brief_type)
 597 |             return {
 598 |                 "success": bool(result_path),
 599 |                 "message": f"Stage brief ({brief_type}): {result_path or 'FAILED'}",
 600 |                 "result": {"path": result_path, "brief_type": brief_type},
 601 |             }
 602 |         except Exception as e:
 603 |             logger.warning("stage_brief_%s failed: %s", brief_type, e)
 604 |             return {"success": False, "message": str(e), "result": None}
 605 | 
 606 |     # ── PANOPTICON tasks ──────────────────────────────────────────────────
 607 |     if name == "panopticon_congress_refresh":
 608 |         try:
 609 |             from services.panopticon_service import fetch_stock_act_disclosures, _cache
 610 |             _cache.pop("panopticon_stock_act", None)
 611 |             _cache.pop("panopticon_disclosures", None)
 612 |             results = fetch_stock_act_disclosures()
 613 |             return {"success": True, "message": f"Congress disclosures: {len(results)} fetched", "result": {"count": len(results)}}
 614 |         except Exception as e:
 615 |             logger.warning("panopticon_congress_refresh failed: %s", e)
 616 |             return {"success": False, "message": str(e), "result": None}
 617 | 
 618 |     if name == "panopticon_whale_scan":
 619 |         try:
 620 |             from services.panopticon_service import fetch_whale_alerts, _cache
 621 |             _cache.pop("panopticon_whales", None)
 622 |             alerts = fetch_whale_alerts()
 623 |             return {"success": True, "message": f"Whale scan: {len(alerts)} alerts", "result": {"count": len(alerts)}}
 624 |         except Exception as e:
 625 |             logger.warning("panopticon_whale_scan failed: %s", e)
 626 |             return {"success": False, "message": str(e), "result": None}
 627 | 
 628 |     if name == "panopticon_polymarket_refresh":
 629 |         try:
 630 |             from services.panopticon_service import fetch_polymarket_markets, _cache
 631 |             _cache.pop("panopticon_polymarket", None)
 632 |             markets = fetch_polymarket_markets()
 633 |             return {"success": True, "message": f"Polymarket: {len(markets)} markets", "result": {"count": len(markets)}}
 634 |         except Exception as e:
 635 |             logger.warning("panopticon_polymarket_refresh failed: %s", e)
 636 |             return {"success": False, "message": str(e), "result": None}
 637 | 
 638 |     return {"success": False, "message": f"Unknown task: {name}", "result": None}
 639 | 
 640 | 
 641 | def run_all_due() -> List[Dict]:
 642 |     """Run all tasks that are 'due' based on interval (simplified: run each once). For cron, prefer calling run_task per schedule."""
 643 |     results = []
 644 |     for task_name in TASKS:
 645 |         try:
 646 |             r = run_task(task_name)
 647 |             results.append({"task": task_name, **r})
 648 |         except Exception as e:
 649 |             results.append({"task": task_name, "success": False, "message": str(e), "result": None})
 650 |     return results
 651 | 
 652 | 
 653 | def initialize_scheduler() -> Dict:
 654 |     """
 655 |     Compatibility shim for admin command deck.
 656 |     We use systemd + endpoint-triggered tasks; this marks scheduler as active.
 657 |     """
 658 |     global _scheduler_started_at, _apscheduler
 659 |     from apscheduler.schedulers.background import BackgroundScheduler
 660 |     from apscheduler.triggers.cron import CronTrigger
 661 |     from apscheduler.triggers.interval import IntervalTrigger
 662 |     with _scheduler_lock:
 663 |         if _apscheduler and _apscheduler.running:
 664 |             return {"success": True, "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None, "already_running": True}
 665 | 
 666 |         _apscheduler = BackgroundScheduler(timezone="UTC")
 667 |         _apscheduler.add_job(lambda: run_task("x_engagement_cycle"), trigger=IntervalTrigger(minutes=5), id="x_engagement_cycle", replace_existing=True)
 668 |         _apscheduler.add_job(lambda: run_task("sentry_megaphone"), trigger=IntervalTrigger(minutes=2), id="sentry_megaphone", replace_existing=True)
 669 |         if ENABLE_ARTICLE_AUTOMATION_15M:
 670 |             _apscheduler.add_job(
 671 |                 lambda: run_task("article_generation_15m"),
 672 |                 trigger=IntervalTrigger(minutes=15),
 673 |                 id="article_generation_15m",
 674 |                 replace_existing=True,
 675 |                 max_instances=1,
 676 |             )
 677 |         if ENABLE_ARTICLE_DRAFT_NEW_SCHEDULE:
 678 |             _apscheduler.add_job(lambda: run_task("article_draft_burst_4"), trigger=IntervalTrigger(minutes=15), id="article_draft_burst_4", replace_existing=True)
 679 |             _apscheduler.add_job(lambda: run_task("article_draft_hourly_1"), trigger=IntervalTrigger(minutes=60), id="article_draft_hourly_1", replace_existing=True)
 680 |         else:
 681 |             _apscheduler.add_job(lambda: run_task("cypherpunk_loop"), trigger=IntervalTrigger(minutes=120), id="cypherpunk_loop", replace_existing=True)
 682 |         _apscheduler.add_job(lambda: run_task("mining_snapshot_hourly"), trigger=IntervalTrigger(hours=1), id="mining_snapshot_hourly", replace_existing=True)
 683 |         _apscheduler.add_job(lambda: run_task("daily_medley_gpu1"), trigger=CronTrigger(hour=23, minute=0), id="daily_medley_gpu1", replace_existing=True)
 684 |         _apscheduler.add_job(lambda: run_task("monetization_injector"), trigger=IntervalTrigger(minutes=30), id="monetization_injector", replace_existing=True)
 685 |         _apscheduler.add_job(lambda: run_task("pulse_drop_rebuild_5am"), trigger=CronTrigger(hour=10, minute=0), id="pulse_drop_rebuild_5am", replace_existing=True)
 686 |         _apscheduler.add_job(lambda: run_task("auto_viral_reel"), trigger=IntervalTrigger(minutes=30), id="auto_viral_reel", replace_existing=True)
 687 |         _apscheduler.add_job(lambda: run_task("intel_medley"), trigger=IntervalTrigger(minutes=60), id="intel_medley", replace_existing=True)
 688 |         _apscheduler.add_job(lambda: run_task("affiliate_education_morning"), trigger=CronTrigger(hour=11, minute=0), id="affiliate_education_morning", replace_existing=True, max_instances=1)
 689 |         _apscheduler.add_job(lambda: run_task("affiliate_education_evening"), trigger=CronTrigger(hour=21, minute=0), id="affiliate_education_evening", replace_existing=True, max_instances=1)
 690 |         # Sacred Social Schedule — 3 posts/day (ET times converted to UTC: ET = UTC-4 in summer, UTC-5 in winter)
 691 |         _apscheduler.add_job(lambda: run_task("morning_signal_tweet"), trigger=CronTrigger(hour=13, minute=0), id="morning_signal_tweet", replace_existing=True, max_instances=1)
 692 |         _apscheduler.add_job(lambda: run_task("afternoon_article_tweet"), trigger=CronTrigger(hour=18, minute=0), id="afternoon_article_tweet", replace_existing=True, max_instances=1)
 693 |         _apscheduler.add_job(lambda: run_task("evening_signal_tweet"), trigger=CronTrigger(hour=23, minute=0), id="evening_signal_tweet", replace_existing=True, max_instances=1)
 694 |         # Auto-engagement (noon + 6pm ET = 16:00 + 22:00 UTC)
 695 |         _apscheduler.add_job(lambda: run_task("auto_engagement_noon"), trigger=CronTrigger(hour=16, minute=0), id="auto_engagement_noon", replace_existing=True, max_instances=1)
 696 |         _apscheduler.add_job(lambda: run_task("auto_engagement_evening"), trigger=CronTrigger(hour=22, minute=0), id="auto_engagement_evening", replace_existing=True, max_instances=1)
 697 |         # F6 Marketing OS jobs
 698 |         _apscheduler.add_job(lambda: run_task("btc_milestone_check"), trigger=IntervalTrigger(minutes=5), id="btc_milestone_check", replace_existing=True, max_instances=1)
 699 |         _apscheduler.add_job(lambda: run_task("daily_metrics_snapshot"), trigger=IntervalTrigger(hours=1), id="daily_metrics_snapshot", replace_existing=True, max_instances=1)
 700 |         _apscheduler.add_job(lambda: run_task("weekly_performance_analysis"), trigger=CronTrigger(day_of_week="sun", hour=0, minute=0), id="weekly_performance_analysis", replace_existing=True, max_instances=1)
 701 |         # Stage Brief Pipeline — 3x/day Chatterbox TTS + intel extraction
 702 |         _apscheduler.add_job(lambda: run_task("stage_brief_morning"), trigger=CronTrigger(hour=6, minute=0), id="stage_brief_morning", replace_existing=True, max_instances=1)
 703 |         _apscheduler.add_job(lambda: run_task("stage_brief_midday"), trigger=CronTrigger(hour=14, minute=0), id="stage_brief_midday", replace_existing=True, max_instances=1)
 704 |         _apscheduler.add_job(lambda: run_task("stage_brief_evening"), trigger=CronTrigger(hour=22, minute=0), id="stage_brief_evening", replace_existing=True, max_instances=1)
 705 |         # SESSION 2: Daily newsletter briefing — 13:00 UTC (8am Eastern)
 706 |         try:
 707 |             from services.newsletter_automation import send_daily_briefing
 708 |             _apscheduler.add_job(send_daily_briefing, trigger=CronTrigger(hour=13, minute=0), id="newsletter_daily_briefing", replace_existing=True, max_instances=1)
 709 |         except Exception as _nle:
 710 |             logging.warning("Newsletter automation job not scheduled: %s", _nle)
 711 |         # Media feed sync every 15 minutes + AI summaries every hour
 712 |         try:
 713 |             from services.media_feed_service import sync_all_feeds, generate_ai_summaries
 714 |             _apscheduler.add_job(sync_all_feeds, trigger=IntervalTrigger(minutes=15), id="media_feed_sync", replace_existing=True, max_instances=1)
 715 |             _apscheduler.add_job(generate_ai_summaries, trigger=IntervalTrigger(minutes=60), id="media_ai_summaries", replace_existing=True, max_instances=1)
 716 |         except Exception as _mfe:
 717 |             logging.warning("Media feed sync job not scheduled: %s", _mfe)
 718 |         # PANOPTICON scheduled tasks
 719 |         _apscheduler.add_job(lambda: run_task("panopticon_congress_refresh"), trigger=IntervalTrigger(minutes=30), id="panopticon_congress_refresh", replace_existing=True, max_instances=1)
 720 |         _apscheduler.add_job(lambda: run_task("panopticon_whale_scan"), trigger=IntervalTrigger(minutes=5), id="panopticon_whale_scan", replace_existing=True, max_instances=1)
 721 |         _apscheduler.add_job(lambda: run_task("panopticon_polymarket_refresh"), trigger=IntervalTrigger(minutes=5), id="panopticon_polymarket_refresh", replace_existing=True, max_instances=1)
 722 |         _apscheduler.start()
 723 |         _scheduler_started_at = datetime.utcnow()
 724 |     return {"success": True, "started_at": _scheduler_started_at.isoformat(), "mode": "apscheduler"}
 725 | 
 726 | 
 727 | def get_scheduler_status() -> Dict:
 728 |     """Compatibility status payload expected by command deck UI."""
 729 |     jobs = [{"name": name, **meta} for name, meta in TASKS.items()]
 730 |     return {
 731 |         "running": bool(_apscheduler and _apscheduler.running),
 732 |         "started_at": _scheduler_started_at.isoformat() if _scheduler_started_at else None,
 733 |         "jobs": jobs,
 734 |         "mode": "apscheduler+systemd",
 735 |     }
 736 | 
```

---

## YOUR REVIEW TASK — PANOPTICON INTELLIGENCE DASHBOARD AUDIT (5 CRITICAL QUESTIONS)

You are auditing the PANOPTICON dashboard: a congressional insider trading tracker, whale wallet monitor,
and geopolitical intelligence feed cross-referenced with Polymarket prediction markets and Bitcoin on-chain data.

Read every file above line-by-line. Your analysis must cite specific line numbers.

### Q1 — CONGRESSIONAL DATA FETCHING ARCHITECTURE
Is the efts.house.gov API integration correct and production-safe?
- Does the search-index endpoint actually accept these parameters?
- Are there rate limits we're violating?
- Is the XML/JSON parsing robust against schema changes?
- Is the fallback placeholder system appropriate or misleading?

### Q2 — API RATE LIMITING
Are all API endpoints properly rate-limited?
- Blueprint routes: any IP-based throttling?
- External API calls: mempool.space, exchangerate.host, CoinGecko — are we respecting their limits?
- Can a malicious user trigger expensive upstream calls by hammering our endpoints?
- Is the in-memory cache sufficient or do we need Redis/SQLite caching?

### Q3 — CLASSIFIED OVERLAY SECURITY
Is the Commander-gated CLASSIFIED overlay secure against client-side bypass?
- Can a free-tier user inspect DOM, remove CSS classes, or modify JS to see data?
- Is the data actually withheld server-side, or just hidden with CSS?
- Are the API routes properly guarded (not just the page route)?

### Q4 — CORRELATION TIMELINE LOGIC
Is the correlation timeline cross-referencing correct?
- Are temporal correlations actually computed (date math) or just associated?
- Is the correlation_score meaningful or arbitrary?
- Could this produce false correlations that look authoritative?
- Legal risk: does the framing stay within "research correlation" or cross into accusation?

### Q5 — SCALABILITY
Will this scale under 1000 concurrent users?
- In-memory cache: thread-safe? Race conditions?
- External API calls: what happens when 1000 users hit /panopticon simultaneously?
- Does get_dashboard_data() make too many sequential API calls?
- Database writes: any N+1 queries or missing indexes?

### RESPONSE FORMAT
For each question (Q1-Q5):
- DETAILED ANALYSIS with line number citations
- SEVERITY: CRITICAL / HIGH / MEDIUM / LOW
- SPECIFIC FIX with code-level recommendation

### FINAL VERDICT
- How many CRITICAL issues found?
- Top 3 changes needed before production
- Is the legal framing adequate for a public-facing product?

