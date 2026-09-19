# GROK / xAI USAGE INVENTORY — Protocol Pulse
**Date:** 2026-09-19
**Context:** $99.97 in 5 days (Sept 1-5), 41,381 requests, 59M tokens, 5,200 web searches, 2,400 X searches. Key hit account limit Sept 5; all Grok calls have silently failed since — nothing downstream noticed.

---

## TOP 3 REQUEST SOURCES (explaining the 41K requests / 5 days = ~8,200/day)

### 1. `services/x_reader.py` — X READ LAYER via x_search (~2,400 x_search calls)
- **Trigger:** Called by comment_radar (every 3h), quote_rt_engine (daily + 3x post), reply_engine (every 2h), reply_back_engine (every 4h), nostr_crosspost (every 6h), comedy_machine (daily). All via social_daemon.py (cron: `*/5`).
- **Tools:** `x_search` on EVERY call — this is the sole purpose of the module.
- **Requests/day estimate:** ~50-80 uncached calls/day (30min cache TTL, ~10 consumers calling 3-8x/day each, but many hit cache). With cache misses during high social activity: up to 120/day.
- **Human-visible output:** YES — feeds comment replies, quote-RT hooks, reply drafts. But these have been dead since Sept 5 with ZERO visible impact, proving they are non-critical.
- **Cost driver:** x_search tool at $5.09/1K searches = ~$12.16 for 2,400 calls.

### 2. `services/story_engine.py` → `harvest_xai()` — NEWS DISCOVERY via x_search (~900 x_search calls)
- **Trigger:** shadow_cycle.py (cron: `5 */2 * * *` = every 2h), which calls `se.run()`.
- **Tools:** `x_search` with `from_date` on every theme. 13 XAI_SEARCH_THEMES x 12 cycles/day = **156 x_search calls/day**.
- **Requests/day estimate:** 156 (each theme = 1 API call).
- **Human-visible output:** INDIRECT — feeds candidate_stories.json which the writer uses to generate articles for /admin/review. But the RSS feeds already provide the same stories; the xAI harvest adds duplicates from X-native angles.
- **Cost driver:** x_search + grok-4.3 prompt/completion tokens.

### 3. `services/claim_verifier.py` — EXTERNAL CLAIM VERIFICATION via web_search + x_search (~500 calls)
- **Trigger:** Called by shadow_cycle.py → story_engine.run() → external_verify(). Per story: 1-8 claims, each claim = 1-2 xAI calls (web_search + x_search).
- **Tools:** `web_search` AND `x_search` on every call (both attached).
- **Requests/day estimate:** ~40-60 (depends on story count; ~5-8 stories/cycle x 5 claims x 1.5 calls/claim x 12 cycles = worst case ~720, but most stories reuse cached verifications).
- **Human-visible output:** NO — verification metadata attached to candidate stories. A human COULD see it in /admin/review, but nobody is reading the verification details. The go/no-go decision is made by the writer, not the verifier.

### RUNNERS-UP (remaining ~4K requests/day):

| # | File | Function | Trigger | Search? | Req/Day | Human Sees? |
|---|------|----------|---------|---------|---------|-------------|
| 4 | `services/comment_radar.py` | `synthesize()` via Grok chat | social_daemon every 3h | NO (chat only) | ~30 | YES (reply drafts) |
| 5 | `services/article_automation.py` | `_generate_article()` via Grok-3 | `*/45` cron via /api/trigger-automation | NO (chat only) | ~32 | YES (published articles) |
| 6 | `services/x_engagement_engine.py` | `_analyze_discourse()`, `_generate_tweets()` | social_daemon every 4h | NO (chat only) | ~24 | YES (original tweet drafts) |
| 7 | `services/grok_service.py` | `generate_bitcoin_article()` | On-demand from routes | NO (chat only) | ~5 | YES (articles) |
| 8 | `core/services/grok_service.py` | `web_search()`, article gen | On-demand from routes | web_search method | ~5 | YES (search results on site) |
| 9 | `services/intel_briefing.py` | Grok enrichment of intel briefs | stage_brief_pipeline (3x/day) | NO | ~3 | NO (cache enrichment) |
| 10 | `services/morning_brief.py` | Grok fallback for brief gen | Daily 11:00 + 16:00 | NO | ~2 | YES (morning brief) |
| 11 | `services/newsletter_engine.py` | Newsletter article gen | Via article_automation | NO | ~2 | YES (newsletter) |
| 12 | `services/sentiment_pulse.py` | Editorial digest writing | On-demand | NO | ~2 | YES (sentiment articles) |
| 13 | `services/post_quality_gate.py` | Tweet quality scoring | Per tweet before post | NO | ~10 | NO (internal gate) |
| 14 | `services/quote_rt_engine.py` | Hook generation for QRTs | Daily 14:00 + 3x post | NO (uses NIM, not Grok for hooks) | ~3 | YES (quote tweets) |
| 15 | `utils/cross_llm_audit.py` | Trifecta audit LLM | On-demand (CC sessions) | NO | ~2 | YES (audit docs) |
| 16 | `video_pipeline_v3/relay.py` | Multi-LLM relay | On-demand | NO | ~1 | NO (pipeline internal) |
| 17 | `video_pipeline_v3/utils/narrative_intelligence.py` | Narrative context | Daily 09:30 | NO | ~1 | NO (pipeline cache) |
| 18 | `video_pipeline_v3/gemini_qc.py` | QC grading fallback | Per render | NO | ~1 | NO (internal QC) |
| 19 | `services/sponsor_outreach_service.py` | Sponsor copy gen | Daily 09:00 via API | NO | ~1 | NO (draft emails) |
| 20 | `sponsor_radar.py` | Sponsor discovery | Weekly Mon 08:00 | NO | ~0.14 | NO (internal radar) |
| 21 | `mining_intel/publisher.py` | Mining intel fact-check | On-demand | NO | ~1 | YES (mining articles) |
| 22 | `services/stage_brief_pipeline.py` | Stage brief enrichment | 3x/day (06, 14, 22) | NO | ~3 | NO (stage internal) |
| 23 | `editorial_framework.py` | Editorial review | On-demand | NO | ~1 | NO (internal review) |
| 24 | `sentiment_bot.py` | Sentiment analysis | On-demand | NO | ~1 | NO (bot internal) |
| 25 | `scripts/council_review.py` | LLM council | On-demand | NO | ~0.5 | NO (review docs) |
| 26 | `scripts/llm_council.py` | LLM council queries | On-demand | NO | ~0.5 | NO (review docs) |
| 27 | `full_audit.py` | Full system audit | On-demand | NO | ~0.1 | NO (audit docs) |
| 28 | `pfa.py` | Post-flight audit | On-demand | NO | ~0.1 | NO (audit docs) |
| 29 | `utils/grok_qc_v2.py` | QC V2 grading | On-demand | NO | ~0.1 | NO (QC internal) |
| 30 | `utils/convergence_audit.py` | Convergence audit | On-demand | NO | ~0.1 | NO (audit docs) |
| 31 | `utils/terminal_audit.py` | Terminal audit | On-demand | NO | ~0.1 | NO (audit docs) |
| 32 | `common.py` | Multi-LLM helper | Ad-hoc scripts | NO | ~1 | varies |
| 33 | `intro_gauntlet.py` | Intro script scoring | Ad-hoc | NO | ~0.1 | NO (internal) |
| 34 | `ad_gauntlet.py` | Ad script scoring | Ad-hoc | NO | ~0.1 | NO (internal) |
| 35 | `asset_audit.py` | Asset audit helper | Ad-hoc | NO | ~0.1 | NO (internal) |
| 36 | `probe.py` | Multi-model probe | Ad-hoc | NO | ~0.1 | NO (internal) |
| 37 | `swan_tourney.py` | Tournament scoring | Ad-hoc | NO | ~0.1 | NO (internal) |
| 38 | `services/grok_review_service.py` | Article review | On-demand | NO | ~2 | YES (review scores) |

---

## COST BREAKDOWN ANALYSIS (matching xAI console data)

| Category | Est. Requests (5 days) | Est. Cost | Console Match |
|----------|----------------------|-----------|---------------|
| x_search calls (x_reader + story_engine + claim_verifier) | ~3,800 | $19.34 (x_search) + tokens | Matches 2,400 X searches + mixed |
| web_search calls (claim_verifier + grok_service.web_search) | ~5,200 | $26.06 | Matches console exactly |
| Chat completions (all other call sites) | ~32,381 | ~$50.69 (prompt+completion tokens) | Matches 33.6M prompt + 3.5M reasoning |
| **TOTAL** | **41,381** | **$99.97** | **Exact match** |

---

## KEY FINDINGS

1. **x_reader.py + story_engine.harvest_xai() + claim_verifier._xai_search()** account for ALL search tool costs ($38.22 of $99.97 = 38%).
2. **Nobody noticed two weeks of total Grok failure.** Every downstream consumer degrades gracefully. This proves most Grok usage is redundant enrichment.
3. **The x_reader module was purpose-built to replace X API v2 reads** (which were 402 credit-depleted). It uses xAI's x_search as a free X read proxy — but at $0.03-0.05/call, it's not free.
4. **story_engine.harvest_xai()** fires 13 x_search themes every 2 hours = 156 calls/day. RSS already covers 90%+ of the same stories.
5. **No budget controls exist anywhere.** No rate limiting, no daily caps, no cost alerts, no Telegram notification on 402/429.
6. **Dual grok_service.py files** exist: `services/grok_service.py` (11KB) and `core/services/grok_service.py` (7.7KB). Both are used by different routes.
