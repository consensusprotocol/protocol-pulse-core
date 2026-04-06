# Social Intelligence Layer — Audit Report
## Generated: 2026-04-06 05:30 UTC

---

### Executive Summary

The social intelligence stack is **critically degraded**. Only 2 of 14 subsystems are fully operational: the Nitter RSS scraper (84% handle success rate, 5,061 tweets collected) and the Twilio voice+SMS pipeline (daily brief delivered to PBX on April 5). The tweet machine's primary LLM (Anthropic Haiku) is returning HTTP 400 due to **depleted credits**, and the Gemini fallback produces malformed JSON that fails parsing — meaning **zero tweets have been generated since April 5 06:21 UTC** (24+ hours of silence). Nostr publishing has 3 broken implementations and 1 functional one. X Spaces scraping is dead (API 403 since March 27). The reply engine, comment radar, and reply-back engine are all broken due to missing env vars (`XAI_API_KEY`, `PP_X_USER_ID`). The narrative intelligence feeding the video pipeline is **17 days stale**. Two systems (sentiment brief service, tweet recycling) were never built.

---

### Detailed Findings

---

## SECTION 1: DATA COLLECTION

### 1a. Nitter RSS Scraper — LIVE

| Item | Evidence |
|------|----------|
| Cron | `0 */6 * * *` — every 6 hours — ACTIVE |
| Script | `services/nitter_scraper.py` (401 lines, last modified 2026-03-31) |
| Handles | 44 configured in `config/social_targets.json` |
| Success rate | 37/44 handles per run (84%) |
| Last run | 2026-04-06 00:04 UTC — 46 new tweets |
| Output | `data/tweet_study/raw_tweets.json` — 5,061 tweets, 4.8 MB |
| Date span | Latest tweets from 2026-04-06 (12 tweets today) |
| Errors | 0 ERROR/CRITICAL. 7 handles consistently fail (all Nitter instances return errors) |
| Top handles | PeterMcCormack (267), LynAldenContact (232), adam3us (224), saylor (220), ErikVoorhees (204) |

**Failing handles (7):** ODELL, matt_odell, SimplyBitcoinTV, nic__carter, pierre_rochard, WClementeIII, woonomic (XML parse error)

**Recommendation:** Remove or replace the 7 dead handles. Otherwise healthy — no action needed.

---

### 1b. Nostr Signal Scraping — BROKEN (zero data since inception)

| Item | Evidence |
|------|----------|
| Cron | `0 * * * *` — hourly — ACTIVE (crashes every run) |
| Script | `cron/nostr_cron.py` (142 lines) |
| DB | `data/nostr_signal.db` — 28,672 bytes — **0 rows** in all tables |
| Flask DB | `nostr_monitor_events` — **0 rows**; `nostr_tracked_pubkeys` — 10 rows (seeded) |
| Log | `logs/nostr_cron.log` — 1.7 MB of repeated errors |
| Error since | 2026-03-27 14:00 — every hourly run |

**Root cause (dual bug):**

1. **Import conflict** — Two `nostr_service.py` files exist:
   - `core/services/nostr_service.py` — HAS `seed_tracked_pubkeys()` and `get_stats()`
   - `services/nostr_service.py` — does NOT have these functions
   - The cron's `sys.path` resolves the wrong one:
   ```
   ERROR Seed pubkeys error: cannot import name 'seed_tracked_pubkeys' from 'services.nostr_service'
   ```

2. **No relay fetcher** — Even if imports were fixed, `nostr_cron.py` only seeds pubkeys and prunes old events. It **never connects to relays** or fetches new events. No active ingestion code exists.

**Collateral damage:** Each hourly run boots the entire Flask app, triggering 5+ unrelated import errors (ApiKey, oracle_avatar, PRAW, selenium, Substack).

**Recommendation:** Fix import path, build actual relay event ingestion, or disable the cron to stop wasting compute (168 failed runs/week).

---

### 1c. X Spaces Scraper — BROKEN (dead since March 27)

| Item | Evidence |
|------|----------|
| Cron | `*/30 0-3,12-23 * * *` — ~32 runs/day — ACTIVE (produces nothing) |
| Script | `x_spaces_scraper/run_scraper.py` (265 lines) — imports cleanly |
| Last success | 2026-03-27 (last `live_spaces_*.json` cache file) |
| Current error | **HTTP 403** on all 14 X API v2 Spaces search queries |
| Cache | `last_run.json`: spaces_found=0, elapsed=0.7s |
| Log | `logs/x_spaces_scraper.log` — 17.5 MB |

**Root cause:** X API v2 bearer token revoked or access tier downgraded. All search queries (bitcoin, btc, sound money, market crash, etc.) across both `live` and `ended` states return 403 Forbidden.

**Timeline:**
- 2026-03-13: Last successful Space detection (27-28 spaces found)
- 2026-03-19: Last run with any results (38 detected, transcripts unusable)
- 2026-03-27: Last cache file created
- 2026-03-28 → now: Zero spaces detected

**Recommendation:** Regenerate bearer token or acquire new API access tier. Disable cron until fixed (~32 wasted runs/day).

---

## SECTION 2: INTELLIGENCE SYNTHESIS

### 2a. Morning Brief (morning_brief.py) — PARTIAL

| Item | Evidence |
|------|----------|
| Cron | `0 11 * * *` and `0 16 * * *` — twice daily — ACTIVE |
| Latest brief | `data/intelligence/morning_intelligence_brief.json` — 2026-04-06 01:42 ET, 1,833 bytes |
| Content quality | Has BTC price ($69,196), sentiment (bearish), 155 tweets analyzed, KOL quotes present |
| Primary LLM | Local Qwen3-coder:30b via Ollama (port 11435, 60s timeout) |
| Fallback chain | Qwen3 → Claude Haiku → Gemini 2.5 Flash → error stub |
| Nostr signals | Always 0 (database empty) |

**Failure pattern (April 5):**
```
11:00 — Qwen3 timed out (60s), Haiku HTTP 400 (credits depleted) → empty fallback
16:00 — Same double failure → empty fallback
```

**April 6 01:42 — SUCCESS** (Qwen3 generated in ~58s, just under timeout)

**Issues:**
1. Qwen3 timeout ~40% of runs (60s too short for 30b model)
2. Haiku fallback permanently dead (HTTP 400, credit balance depleted)
3. Gemini fallback exists in code but may not be reliably reached
4. `morning_brief_cron.sh` (06:45 UTC) runs `satomi_brief_generator`, NOT `morning_brief.py` — misleading name
5. `transcript_intelligence.py` (every 4h, feeds KOL data to brief) also BROKEN due to same Anthropic 400

**KOL data sources:**
- `kol_transcript_digest.json` — Last generated 2026-04-05, BTC Sessions + Pompliano analysis
- 51 historical analyses in `kol_transcript_intel.json` — no new ones since credits depleted

**Recommendation:** P0: Top up Anthropic credits. Increase Qwen3 timeout to 120s. Verify Gemini fallback path fires.

---

### 2b. KOL Sentiment Brief Service — NEVER_BUILT

| Item | Evidence |
|------|----------|
| File | `services/sentiment_brief_service.py` — **DOES NOT EXIST** |
| Import | `ModuleNotFoundError` |
| Route | `/api/sentiment-brief` — **NOT REGISTERED** |
| Grep | Zero matches across entire codebase |

The closest analog is `transcript_intelligence.py` → `kol_transcript_digest.json` → `morning_brief.py`, but this is a batch pipeline, not a standalone service with an API endpoint.

**Recommendation:** Either build this service or formally designate the transcript_intelligence pipeline as the replacement.

---

### 2c. Narrative Context for Video Pipeline — BROKEN (17 days stale)

| Item | Evidence |
|------|----------|
| File | `video_pipeline_v3/data/intelligence/narrative_context.json` — EXISTS |
| Last modified | **2026-03-20 13:38** (17 days stale) |
| Content | Fallback quality: "12 of 0 Priority-1 thought leaders" (logic error in template) |
| Cron | `30 9 * * *` runs `utils.narrative_intelligence` — ACTIVE |
| Log | `logs/narrative_intel.log` — **FILE DOES NOT EXIST** |

**All intelligence files stale:**

| File | Age |
|------|-----|
| `narrative_context.json` | 17 days |
| `daily_signals.json` | 17 days |
| `narrative_history.json` | 17 days |
| `sentiment.json` | 29 days |
| `live_signals.json` | 21 days |
| `entity_mentions.json` | 28 days |

**Root cause:** `NarrativeIntelligenceEngine` uses X API v2 `search_recent_tweets` which returns **403 Forbidden** (public bearer token, not project-level token). Falls back to `_fallback_narratives()` which recycles stale data.

**Pipeline impact:**
- `script_writer.py` enforces a 4-hour freshness window → receives `{}` (empty dict)
- `clip_selector.py` falls back to recency/engagement ranking only (no narrative relevance)
- `render_social.py` references 17-day-old narrative themes for tweet cards

**Recommendation:** Fix X API bearer token (needs project-level token). Interim: pipe `morning_intelligence_brief.json` into the video pipeline as a bridge.

---

## SECTION 3: OUTPUT — TWEET MACHINE

### 3a. Tweet Machine — BROKEN (silent since April 5 06:21 UTC)

| Item | Evidence |
|------|----------|
| Cron | `0 */3 * * *` — every 3 hours (8x/day) — ACTIVE |
| Script | `services/tweet_machine.py` (1,048 lines, v4) |
| Last tweet | 2026-04-05 06:21 UTC: "828.9 EH/s hashrate at extreme fear..." |
| Voice laws | YES — 7 laws at lines 192-240 + cypherpunk guardrails + 5 banned angles |
| Formats | 8 rotating formats (on_chain_signal, historical_parallel, fiat_failure, socratic_question, etc.) |
| Posting | 1 tweet per run, gated by `x_service.can_post_tweet()` |

**LLM fallback chain:**

| LLM | Status | Error |
|-----|--------|-------|
| Anthropic Haiku | **DEAD** | HTTP 400: credit balance depleted |
| Gemini 2.5 Flash | **BROKEN** | Returns content but JSON extraction fails (unescaped apostrophes in `Bitcoin's`) |
| Grok 3 Mini Fast | **WORKS** | Successful in dry run — but only reached when Gemini returns a clean error, not when it returns malformed content |

**Every run since April 5 06:21 has failed.** The Gemini path returns content (triggering "success") but the JSON is malformed, so no tweet text is extracted. The Grok fallback is only reached on hard errors, not on content that fails parsing.

**Social daemon (`social_daemon.py`):** Running (PID 224330, started April 3). All 4 subtasks broken:

| Task | Interval | Error |
|------|----------|-------|
| reply_engine | 2h | `PP_X_USER_ID` not set → 0 mentions |
| comment_radar | 3h | `XAI_API_KEY` not set → ValueError |
| reply_back | 4h | `XAI_API_KEY` not set → ValueError |
| nostr_crosspost | 6h | Depends on CommentRadar → broken |

**Posting gate (`x_service.py`):** Constants `_MAX_POSTS_PER_24H=8`, `_MIN_GAP_HOURS=2` (docstring says 3/4h — mismatch). `ENABLE_TWEETS` not set (defaults false) but `can_post_tweet()` doesn't check it.

**Recommendation:** P0: Top up Anthropic credits. P0: Fix Gemini JSON extraction (handle apostrophes). P1: Set `XAI_API_KEY` and `PP_X_USER_ID`.

---

### 3b. Reply Engine — BROKEN (infrastructure exists, nothing works)

| Item | Evidence |
|------|----------|
| Files | `services/reply_engine.py` (214 lines) — draft-only, no auto-posting |
| | `services/reply_back_engine.py` (268 lines) — replies to replies on PP tweets |
| | `core/services/x_reply_writer.py` — core services layer |
| Admin UI | `templates/admin_reply_squad.html` exists for draft review |
| Status | reply_engine: `PP_X_USER_ID` not set. reply_back: `XAI_API_KEY` not set. Neither produces output. |
| Last reply | **NEVER** — zero replies posted or drafted |

**Recommendation:** Set `PP_X_USER_ID` and `XAI_API_KEY`. Low priority since replies are draft-only (require manual approval).

---

### 3c. Quote Retweet / Amplification — BROKEN (code exists, env blocks it)

| Item | Evidence |
|------|----------|
| Comment Radar | `services/comment_radar.py` (804 lines) — monitors 63 Bitcoin KOL accounts |
| | Can quote-tweet up to 3/day, reply up to 18/day |
| Engagement Engine | `services/x_engagement_engine.py` (821 lines) — viral tweet + quote tweet cycles |
| x_service.py | `quote_tweet()` exists (line 604) but uses text+URL, not native X API `quote_tweet_id` |
| Status | **ALL BROKEN** — require `XAI_API_KEY` which is not set |
| Self-amplification | **NEVER_BUILT** — no system to re-post or recycle top-performing original tweets |

**Recommendation:** Set `XAI_API_KEY` to activate. The code is well-built (63 monitored accounts, engagement scoring, persona-aware drafting) but completely gated behind one missing env var.

---

## SECTION 4: DISTRIBUTION

### 4a. Nostr Publishing — PARTIALLY BROKEN

**Four separate implementations exist (fragmentation concern):**

| Implementation | Status | Issue |
|---------------|--------|-------|
| `nostr/nostr_publisher.py` | **BROKEN** | Expects hex private key; env has nsec1 (bech32). `len(priv_hex) != 64` always fails |
| `services/nostr_crosspost.py` | **BROKEN** | Sends **unsigned events** — relays reject per NIP-01 |
| `services/distribution_manager.py` | **FUNCTIONAL** | Only path with proper nsec1 decode + Schnorr signing (coincurve) |
| `core/social_publisher.py` | **BROKEN** | Delegates to broken nostr_publisher.py |

**Key:** `NOSTR_PRIVATE_KEY` is set (63 chars, nsec1-encoded). Only `distribution_manager.py` decodes it correctly.

**Relay status (2026-03-23, 14 days stale):** damus: connected, nos.lol: disconnected, nostr.band: disconnected, primal.net: connected.

**Feature flag:** `ENABLE_NOSTR_POSTING=true` — enables distribution_manager path.

**Recommendation:** Fix `nostr_publisher.py` key handling (copy nsec1 decode from distribution_manager). Fix `nostr_crosspost.py` to sign events. Consider consolidating all 4 implementations into one.

---

### 4b. SMS (Twilio / GoHighLevel) — PARTIAL

| System | Status | Evidence |
|--------|--------|----------|
| **Twilio voice + SMS** | **LIVE** | Last delivery: 2026-04-05 16:00 UTC. Call + SMS to PBX + 1 subscriber. HTTP 201. |
| **Satomi Brief Generator** | **LIVE** | Runs daily at 12:00 UTC. Pipeline: intel → Claude script → Kokoro TTS → Twilio call |
| **GoHighLevel SMS** | **DEAD** | `GHL_API_KEY` and `GHL_LOCATION_ID` **NOT SET** |

Twilio env vars all present: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE`, `PBX_PHONE_NUMBER`. Working flawlessly.

GoHighLevel was intended for bulk SMS (whale alerts, Satoshi Hour, difficulty adjustments). Credentials never configured.

**Recommendation:** Twilio path is healthy. Set GHL credentials if bulk SMS is desired.

---

### 4c. X Articles / Long-Form — PARTIAL

| Item | Evidence |
|------|----------|
| File | `services/x_daily_top_article.py` (315 lines) |
| Cron | `0 14 * * *` (14:00 UTC / 10:00 AM ET daily) — ACTIVE |
| Last success | 2026-04-04 18:00 UTC — article #523 posted |
| Image gen | Uses Grok image API — **BROKEN** (`XAI_API_KEY` not set) → text-only tweets |
| Copy gen | Uses GPT-4o (OpenAI) — WORKING (`OPENAI_API_KEY` is set) |
| Success rate | ~42% (5/12 attempts) |
| Dedup | Working (correctly skipped already-posted article on 2026-04-05) |
| X threads | **NEVER_BUILT** — no thread-posting or X Articles code |
| `ENABLE_X_POSTING` | **NOT SET** — disables distribution_manager X path (daily brief dual-post only goes to Nostr) |

**Recommendation:** Set `XAI_API_KEY` for image generation. Set `ENABLE_X_POSTING=true` for dual-posting. Investigate 58% failure rate.

---

## SECTION 5: CRON HEALTH SUMMARY

| Schedule (UTC) | Command | Exists | Imports | Status |
|----------------|---------|--------|---------|--------|
| `0 */6 * * *` | `services/nitter_scraper.py` | YES | YES | **LIVE** (84% handles) |
| `0 * * * *` | `cron/nostr_cron.py` | YES | PARTIAL | **BROKEN** (import conflict) |
| `*/30 0-3,12-23 * * *` | `x_spaces_scraper/run_scraper.py` | YES | YES | **BROKEN** (API 403) |
| `0 */3 * * *` | `services/tweet_machine.py` | YES | YES | **BROKEN** (LLM 400/JSON) |
| `45 6 * * *` | `scripts/morning_brief_cron.sh` | YES | YES | **LIVE** (runs satomi_brief, not morning_brief) |
| `0 11 * * *` | `services/morning_brief.py` | YES | YES | **PARTIAL** (Qwen3 intermittent, Haiku dead) |
| `0 16 * * *` | `services/morning_brief.py` | YES | YES | **PARTIAL** (same) |
| `0 12 * * *` | `satomi_brief_generator` (Twilio) | YES | YES | **LIVE** |
| `*/5 * * * *` | `services/social_daemon.py` (keepalive) | YES | YES | **RUNNING** (all 4 subtasks broken) |
| `30 9 * * *` | `video_pipeline_v3/utils/narrative_intelligence` | YES | YES | **BROKEN** (X API 403, no log) |
| `0 */4 * * *` | `services/transcript_intelligence.py` | YES | YES | **BROKEN** (Anthropic 400) |
| `*/30 * * * *` | `video_pipeline_v3/fetch_intelligence_data.py` | YES | YES | **LIVE** |
| `*/5 * * * *` | `services/sovereign_context_engine.py` | YES | YES | **LIVE** |
| `0 14 * * *` | `services/x_daily_top_article.py` | YES | YES | **PARTIAL** (no images, 42% success) |

---

### Priority Fix List

| Priority | Component | Status | Effort | Impact |
|----------|-----------|--------|--------|--------|
| **P0** | Anthropic API credits | DEPLETED | 5 min (billing) | Unblocks tweet_machine Haiku, transcript_intelligence, morning_brief fallback, reply_engine drafts |
| **P0** | Gemini JSON extraction in tweet_machine | BROKEN | 30 min (code) | Secondary fallback produces content that fails parsing — zero tweets for 24h+ |
| **P1** | `XAI_API_KEY` in .env | NOT SET | 5 min (env) | Unblocks comment_radar (63 accounts), reply_back_engine, nostr_crosspost, X article images |
| **P1** | `PP_X_USER_ID` in .env | NOT SET | 5 min (env) | Unblocks reply_engine mention fetching |
| **P1** | X API bearer token (project-level) | WRONG TYPE | 30 min (dev portal) | Unblocks narrative_intelligence (17 days stale) + X Spaces scraper |
| **P2** | Nostr publisher key handling | FORMAT MISMATCH | 1 hour (code) | nsec1→hex decode needed in `nostr_publisher.py` + signing in `nostr_crosspost.py` |
| **P2** | Nostr cron import conflict | WRONG MODULE | 30 min (code) | `services/nostr_service.py` vs `core/services/nostr_service.py` |
| **P2** | GoHighLevel SMS credentials | NOT SET | 10 min (env) | Enables whale alerts, Satoshi Hour, difficulty adjustment SMS |
| **P2** | Qwen3 timeout for morning_brief | 60s TOO SHORT | 5 min (code) | Increase to 120s for 30b model reliability |
| **P3** | `ENABLE_X_POSTING` / `ENABLE_TWEETS` | NOT SET | 5 min (env) | Enables distribution_manager X posting path |
| **P3** | Nitter dead handles (7) | STALE CONFIG | 15 min (config) | Replace dead handles with current Bitcoin KOL accounts |
| **P3** | x_service.py gate constants vs docstring | MISMATCH | 10 min (code) | Code says 8 max / 2h gap, docstring says 3 / 4h |
| **P4** | X Spaces scraper cron | WASTING COMPUTE | 2 min (cron) | Disable ~32 daily runs that produce nothing until API access restored |

---

### Architecture Gaps

1. **Sentiment Brief Service** — Referenced in audit spec but never built. No `sentiment_brief_service.py`, no `/api/sentiment-brief` route. The transcript_intelligence + morning_brief pipeline is the closest analog but lacks a standalone API.

2. **Tweet recycling / best-of amplification** — No system exists to re-post or quote-retweet top-performing original tweets. The engagement engine can quote-tweet OTHER accounts' posts but has no self-amplification.

3. **X threads / X Articles** — No thread-posting code exists. `x_daily_top_article.py` posts single tweets with article links, not threads.

4. **Nostr event ingestion** — Infrastructure exists to PUBLISH to Nostr (4 implementations) but nothing actively READS from Nostr relays. The 10 tracked pubkeys are seeded in the DB but no relay subscription fetches their posts. `nostr_signal.db` has been empty since creation.

5. **Narrative intelligence → video pipeline bridge** — The morning_brief produces fresh intelligence (when Qwen3 succeeds) but the video pipeline's `narrative_context.json` is 17 days stale. These two systems produce compatible data but don't talk to each other.

6. **LLM cost tracking / billing alerts** — No unified cost dashboard for Anthropic + Gemini + Grok + OpenAI API calls. The Anthropic credit depletion was not detected until it caused cascading failures across 4+ subsystems.

7. **Unified social status dashboard** — Multiple overlapping systems (tweet_machine, social_daemon, x_engagement_engine, comment_radar, reply_engine) with no single status page. Each has its own log file, scheduling mechanism, and error handling.

8. **Nostr publisher consolidation** — Four separate Nostr publishing implementations with different relay lists, different key handling, and different signing approaches. Only one actually works.

---

*Audit performed by Claude Code (Opus 4.6) on 2026-04-06. No fixes applied — diagnostic only.*
