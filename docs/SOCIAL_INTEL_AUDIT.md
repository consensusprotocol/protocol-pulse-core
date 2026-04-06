# Social Intelligence Layer — Audit Report
## Generated: 2026-04-06 00:15 UTC

---

### Executive Summary

The social intelligence layer is **partially operational with critical failures**. The Nitter scraper runs successfully (84% handle success rate, 46 tweets/cycle), the Twilio voice call system works daily, and the social daemon is alive. However, the **tweet machine is completely down** (Anthropic API 400 on all runs today), the **morning brief is producing empty fallbacks** (both Qwen and Haiku failing), the **narrative context is 16 days stale**, and **Nostr publishing is feature-flagged off**. Two systems (sentiment brief service, quote-RT amplification) were never built. The XAI_API_KEY env var is missing from the daemon environment, breaking 2 of 4 daemon tasks.

---

### Detailed Findings

## SECTION 1: DATA COLLECTION

### 1a. Nitter RSS Scraper — LIVE (degraded)

| Check | Evidence |
|-------|---------|
| Cron active | YES — `0 */6 * * *` (two entries: one from `core/`, one from `services/`) |
| Last successful run | 2026-04-06 00:04:06 UTC — 37/44 handles OK, 46 new tweets collected |
| Handles monitored | **44 handles** configured |
| Failed handles (7) | ODELL, matt_odell, SimplyBitcoinTV, nic__carter, pierre_rochard, WClementeIII, woonomic — XML parse errors or Nitter instance failures |
| raw_tweets.json | **5,061 entries**, date range 2007-09-08 to 2026-04-06. File healthy. |
| pending_tweets.json | 62,469 bytes, last modified 2026-04-05 02:21 ET |
| Known bug | `nitter_cron.log` showed JSONDecodeError crashes on 2026-03-23 (file corruption). Rebuilt since. Two duplicate cron entries (core/ vs services/) — one is stale. |

**Recommendation**: Remove duplicate cron entry. Fix or drop the 7 failing handles. Monitor for Nitter instance rotation.

### 1b. Nostr Signal Scraping — BROKEN

| Check | Evidence |
|-------|---------|
| DB file | `data/nostr_signal.db` exists |
| Service files | `services/nostr_service.py`, `services/nostr_signal_service.py`, `services/nostr_feed_worker.py`, `services/nostr_broadcaster.py`, `services/nostr_crosspost.py`, `cron/nostr_cron.py` |
| Cron active | YES — `0 * * * *` hourly via `cron/nostr_cron.py` |
| Import errors | **CRITICAL**: `cannot import name 'ApiKey' from 'models'`; `cannot import name 'get_stats' from 'services.nostr_service'` |
| signals.json | **Zero nostr entries** — 22 keys, all market data, no nostr signal data |
| npubs monitored | No hardcoded watchlist. Protocol Pulse own npub: `npub1a38uwcec9u4pqd4dutezcfg3ujfapfm90vzzjtkq9cs2u5tws50stujyhm`. Relay event consumption model, not polling. |

**Recommendation**: Fix import errors (`ApiKey`, `get_stats`). Verify relay connections. Add npub watchlist for top Bitcoin KOLs.

### 1c. X Spaces Scraper — BROKEN (stale 9+ days)

| Check | Evidence |
|-------|---------|
| Cron active | YES — `*/30 12-23,0-3 * * *` (runs every 30min during active hours) |
| Scraper file | `x_spaces_scraper/run_scraper.py` exists |
| Cache | 166 directories in `x_spaces_scraper/cache/`, last activity **2026-03-27** |
| Cron log | `/tmp/xspaces_cron.log` — empty or missing (no output) |
| Legacy scraper | `spaces_scraper/` also exists (untouched since Mar 2) |

**Recommendation**: Check if run_scraper.py is crashing silently (no stderr redirect). Verify X guest token is refreshing. Test manually.

---

## SECTION 2: INTELLIGENCE SYNTHESIS

### 2a. Morning Brief — BROKEN (fallback-only output)

| Check | Evidence |
|-------|---------|
| Cron active | YES — `45 6 * * *` via `morning_brief_cron.sh`, plus `0 11 * * *` and `0 16 * * *` via direct `morning_brief.py` |
| Brief file | Exists, 175 bytes, last modified 2026-04-05 16:01 ET |
| Content quality | **DEGRADED** — contains only `"error": "All LLM calls failed"`, `"generated_by": "fallback"`. No KOL quotes, no sentiment, no narratives. |
| Model chain | Primary: `qwen3-coder:30b` via Ollama (localhost:11435). Fallback: `claude-haiku-4-5-20251001` |
| Failure pattern | Qwen3 times out every run (60s timeout, port 11435 unresponsive). Haiku returns HTTP 400 (credit balance depleted). Apr 4 was last successful brief via Haiku. |
| Tweet ingestion | Loads 126-164 tweets/day. Nostr signals: consistently 0. |

**Recommendation**: Fix Ollama availability (port 11435 unreachable). Anthropic credits need recharge. Add Gemini fallback (same pattern as oracle_dialogue_engine.py fix).

### 2b. KOL Sentiment Brief Service — NEVER_BUILT

| Check | Evidence |
|-------|---------|
| File exists | **NO** — `services/sentiment_brief_service.py` does not exist |
| Route registered | **NO** — zero matches for `sentiment-brief` or `sentiment.brief` in any route file |
| API endpoint | **NO** — `/api/sentiment-brief` not registered |

**Recommendation**: Build this service. Design docs reference it but implementation was never started.

### 2c. Narrative Context for Video Pipeline — PARTIAL (16 days stale)

| Check | Evidence |
|-------|---------|
| File exists | YES — `video_pipeline_v3/data/intelligence/narrative_context.json`, 861 bytes |
| Last updated | **2026-03-20 13:38 ET — 16 days stale** |
| Content | Has `dominant_narrative: "price"`, `clip_selection_priority`, `narrative_bridge_lines`. But `thought_leaders_mentioned: []` (empty). |
| Pipeline reads it | **YES, deeply** — consumed by `render_social.py`, `clip_selector.py`, `script_writer.py`, `utils/clip_scorer.py` |
| Auto-refresh | **NONE** — `utils/narrative_intelligence.py` exists but has no cron trigger and is not called by daily_producer.py |
| KOL in scripts | Recent test renders have incidental tweet quotes but no structured KOL synthesis |

**Recommendation**: Add narrative_intelligence.py call to daily_producer.py Step 1 (pre-render). Wire morning brief KOL data into narrative context. Add cron fallback.

---

## SECTION 3: OUTPUT — TWEET MACHINE

### 3a. Tweet Machine — BROKEN (Anthropic API 400)

| Check | Evidence |
|-------|---------|
| Cron active | YES — `0 */3 * * *` (every 3 hours) |
| File / import | `services/tweet_machine.py` exists, imports cleanly |
| Voice laws | Embedded in Claude prompt context via `TWEET_FORMATS` dict (per-format instructions). No standalone `TWEET_VOICE_LAWS` constant. |
| Last tweets posted | `posted_tweets.json` has 15 entries (ID strings only, no timestamps — audit trail weak) |
| Today's status | **ALL 5 RUNS FAILED** — `HTTP Error 400: Bad Request` from Anthropic API during tweet generation (12:00, 15:00, 18:00, 21:00, 00:00 UTC). Zero tweets today. |
| X auth | X write credentials load successfully — the 400 is from Anthropic, not X |

**Recommendation**: Same root cause as morning brief — Anthropic credits depleted. Add Gemini/Grok fallback for tweet generation. Add timestamps to posted_tweets.json.

### 3b. Reply Engine — PARTIAL (draft-only, never auto-posts)

| Check | Evidence |
|-------|---------|
| Files | `services/reply_engine.py`, `services/reply_back_engine.py`, `core/services/x_reply_writer.py` |
| Mode | **Draft-only** — queues replies to `x_reply_draft` DB table. NO auto-posting. |
| Running | Yes, via `social_daemon.py` every 2 hours |
| Logs | `logs/reply_engine.log` exists but empty. Output goes to `social_daemon.log`. |

**Recommendation**: Decide if auto-posting is desired or if manual review is intentional. If intentional, build admin UI for draft review.

### 3c. Quote Retweet / Amplification — NEVER_BUILT

| Check | Evidence |
|-------|---------|
| Code exists | **NO** — no quote-tweet, amplification, or retweet recycling code anywhere |
| Thread engine | `services/thread_engine.py` exists (5-7 tweet threads) but this is creation, not amplification |

**Recommendation**: Low priority unless engagement growth is a goal.

---

## SECTION 4: DISTRIBUTION

### 4a. Nostr Publishing — BROKEN (feature-flagged off + API key missing)

| Check | Evidence |
|-------|---------|
| Code exists | YES — `services/nostr_crosspost.py`, `services/nostr_broadcaster.py`, `services/distribution_manager.py` |
| Feature flag | `ENABLE_NOSTR_POSTING` defaults to `False` in `services/feature_flags.py:16`. Not overridden in `.env`. |
| Daemon task | social_daemon runs nostr_crosspost every 6h but errors with `XAI_API_KEY not set` |
| Content | Would crosspost same content as X (with Nostr formatting) |

**Recommendation**: Set `XAI_API_KEY` in daemon env. Then set `ENABLE_NOSTR_POSTING=true` in `.env` to activate.

### 4b. SMS / Twilio — LIVE

| Check | Evidence |
|-------|---------|
| Env vars | `TWILIO_ACCOUNT_SID`: YES. `TWILIO_AUTH_TOKEN`: YES. `TWILIO_FROM_NUMBER`: not set as env var (likely hardcoded). |
| sms_service.py | Exists, warns "missing GHL credentials" (GoHighLevel integration, separate from Twilio core) |
| satomi_brief_generator.py | **EXISTS and WORKING** — generates 90-second voice script from live intel, delivers via Twilio voice call + SMS summary |
| Cron | `0 12 * * *` (06:45 ET daily) |
| Last delivery | **2026-04-05 12:00:23 UTC** — SMS sent, status 201. Fully operational. |
| 2-tier system | Not built — single subscriber only |

**Recommendation**: Working as-is. 2-tier free/premium system not yet needed.

### 4c. X Articles / Long-Form — NEVER_BUILT

| Check | Evidence |
|-------|---------|
| Thread engine | `services/thread_engine.py` — generates 5-7 tweet threads (closest to long-form) |
| X Articles | **NO** dedicated X Articles (blog-style post) code |
| Distribution manager | `services/distribution_manager.py` auto-threads long posts into up to 3 parts |

**Recommendation**: Not critical. Thread engine covers the use case adequately.

---

## SECTION 5: CRON HEALTH SUMMARY

| Schedule (UTC) | Command | Target Exists | Status |
|----------------|---------|---------------|--------|
| `0 */6 * * *` | `services/nitter_scraper.py` | YES | RUNNING (84% success) |
| `0 */6 * * *` | `core/services/nitter_scraper.py` | NO (stale path) | DUPLICATE — remove |
| `0 * * * *` | `cron/nostr_cron.py` | YES | BROKEN (import errors) |
| `0 */3 * * *` | `services/tweet_machine.py` | YES | BROKEN (Anthropic 400) |
| `45 6 * * *` | `scripts/morning_brief_cron.sh` | YES | BROKEN (LLM fallback only) |
| `0 11 * * *` | `services/morning_brief.py` | YES | BROKEN (same as above) |
| `0 16 * * *` | `services/morning_brief.py` | YES | BROKEN (same as above) |
| `*/30 0-3,12-23 * * *` | `x_spaces_scraper/run_scraper.py` | YES | STALE (9 days silent) |
| `*/5 * * * *` | `services/social_daemon.py` (watchdog) | YES | RUNNING (2/4 tasks broken) |
| `@reboot` | `services/social_daemon.py` | YES | RUNNING |
| `0 12 * * *` | `satomi_brief_generator` (Twilio) | YES | LIVE |
| `0 6/14/22 * * *` | `services/stage_brief_pipeline.py` | YES | UNKNOWN (not audited) |
| `15 9 * * *` | `services/blockware_intel_scraper.py` | YES | UNKNOWN (not audited) |

---

### Priority Fix List

| Priority | Component | Status | Effort | Impact |
|----------|-----------|--------|--------|--------|
| **P1** | Anthropic API credits | DEPLETED | 5 min (billing) | Unblocks tweet machine, morning brief, reply engine |
| **P1** | XAI_API_KEY in daemon env | MISSING | 2 min (env var) | Unblocks comment_radar + nostr_crosspost in social_daemon |
| **P2** | Morning brief LLM fallback | NO GEMINI FALLBACK | 30 min (code) | Brief produces real content when Anthropic is down |
| **P2** | Tweet machine LLM fallback | NO GEMINI FALLBACK | 30 min (code) | Tweets post when Anthropic is down |
| **P2** | Nostr cron import errors | `ApiKey` + `get_stats` missing | 20 min (code) | Nostr signal data starts flowing |
| **P3** | Narrative context auto-refresh | NO CRON/TRIGGER | 30 min (code) | Pipeline gets fresh intelligence instead of 16-day-old data |
| **P3** | X Spaces scraper | STALE 9 DAYS | 1 hr (debug) | Spaces intelligence resumes |
| **P3** | ENABLE_NOSTR_POSTING flag | OFF | 2 min (env) | Nostr distribution activates |
| **P4** | Nitter duplicate cron + failed handles | DEGRADED | 15 min (config) | Cleaner scraping, fewer errors |
| **P4** | posted_tweets.json timestamps | MISSING | 15 min (code) | Audit trail for tweet posting |
| **P5** | Sentiment brief service | NEVER_BUILT | 4 hr (new service) | Structured KOL sentiment endpoint |
| **P5** | Quote-RT amplification | NEVER_BUILT | 4 hr (new service) | Engagement growth feature |

---

### Architecture Gaps

1. **No LLM fallback chain in tweet_machine.py or morning_brief.py** — Both depend solely on Anthropic. When credits hit $0, the entire social output layer goes dark. The oracle dialogue engine now has Gemini fallback (fixed today) but tweet/brief do not.

2. **No narrative intelligence refresh trigger** — `utils/narrative_intelligence.py` exists and is deeply integrated into the video pipeline, but nothing calls it on a schedule. The pipeline reads stale 16-day-old context.

3. **No structured sentiment endpoint** — `sentiment_brief_service.py` referenced in design docs but never built. The sentiment_analyzer.py exists for article-level sentiment but there's no aggregated KOL sentiment API.

4. **Nostr is fully built but fully off** — Broadcaster, crosspost, and feed worker all exist. Feature flag is False, API key is missing from daemon env. Two config changes away from activation.

5. **Reply engine is draft-only with no review UI** — Replies are generated and stored in DB but never posted. No admin interface exists to review/approve drafts. The system generates work that nobody sees.

6. **Social daemon env isolation** — The daemon runs via cron watchdog but inherits a limited env. `XAI_API_KEY` is set in `.env` but not exported to the daemon's process environment, breaking 2 of 4 tasks.

7. **No deduplication between tweet_machine.py and social_daemon.py** — Both systems can theoretically generate tweets. No coordination mechanism prevents duplicate posts if both fire.
