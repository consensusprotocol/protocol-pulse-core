# Newsletter Send Path — Protocol Pulse

**Authored:** 2026-11-09 by Claude Code session (newsletter-tracking branch)
**Purpose:** End-to-end trace of the daily newsletter dispatch, module inventory, and known gaps.

---

## 1. Scheduler Entry Point

The daily newsletter is **not a cron job**. It is an APScheduler `BackgroundScheduler` running inside the Waitress process.

- **File:** `core/app.py:445-451`
- **Job ID:** `newsletter_daily`
- **Trigger:** `CronTrigger(hour=12, minute=0, timezone="UTC")`
- **Comment says:** "8:00 AM ET = 12:00 UTC"
- **Actual behavior:** 12:00 UTC = **07:00 EST** / **08:00 EDT**. The comment is wrong during Standard Time (Nov-Mar). During EST the send fires at 7:00 AM, not 8:00 AM.

## 2. Dispatch Function

**File:** `core/app.py:380-439` — `_newsletter_daily_dispatch()`

### Flow:

1. **Queue lookup** (line 384-397): Globs `data/newsletter_queue/*_hook.json`, sorted alphabetically. Takes the **last** (newest by filename timestamp). If no files, logs and returns.
2. **Engine import** (line 407-412): Loads `services/newsletter_engine.py` **fresh from disk** via `importlib.util.spec_from_file_location()` on every run. This means code changes to `newsletter_engine.py` go live on the next dispatch without a Waitress restart.
3. **Inside `app.app_context()`** (line 414-434):
   - `engine.get_subscribers()` — returns filtered email list
   - `engine.get_todays_articles(5)` — top 5 diverse articles from DB
   - `hook_data.get("hook", "")` or `engine.generate_ai_summary(articles)` — uses hook text as summary, falls back to Grok-3 AI summary
   - `engine.get_btc_price()` — CoinGecko -> CoinCap -> price_service fallback
   - `engine.generate_html(articles, summary, btc_data)` — renders 6-section Bloomberg/cypherpunk HTML
   - `engine.send_newsletter(subscribers, html=html)` — sends via Resend batch API
4. **Queue move** (line 429): Moves **only the single hook file** to `data/newsletter_queue/sent/`. Older hooks accumulate.
5. **Logging** (line 431-434): Writes to `logs/newsletter_dispatch.log` and Python logger.

### Queue accumulation problem:
As of 2026-11-09: **84 unsent** hook files in queue, **147 in sent/**. Only the newest is picked; the rest are orphaned. The `stage_brief_pipeline.py` writes 3 hooks/day (06:00, 14:00, 22:00 UTC), but only one is consumed per day.

## 3. Duplicate Route

**File:** `core/routes_api.py:1327-1376` — `api_newsletter_dispatch()`

`POST /api/newsletter/dispatch` does the **exact same thing** as the APScheduler job:
- Auth: localhost = no auth, external = `X-Admin-Secret` header
- Same engine import via `importlib.util`
- Same flow: `get_subscribers()` -> `get_todays_articles(5)` -> hook/summary -> BTC price -> HTML -> send
- Extra fallback: also checks `NewsletterSubscriber` table directly if engine returns 0

This is a manual trigger duplicate. Both paths call `engine.send_newsletter()` with identical semantics.

## 4. Subscriber Selection and the 9 vs 5 Answer

**File:** `services/newsletter_engine.py:759-787` — `get_subscribers()`

1. Queries `NewsletterSubscriber` table where `subscribed=True` — returns 9 rows.
2. Filters out `TEST_ADDRS` set (line 770-775):
   - `test@example.com`
   - `test_diagnostic@protocolpulse.io`
   - `pbx_test_live@protocolpulse.io`
   - `test_audit@protocolpulse.io`
3. 4 test addresses match rows 2-5 (created Mar 26-31 via API). **5 real subscribers remain**.
4. Fallback if `real` is empty: returns all emails including test (safety net). Currently `real` has 5 entries (3x @consensusprotocol.org internal, 2x gmail).

## 5. What "Sent" Means

**File:** `services/newsletter_engine.py:678-757` — `send_newsletter()`

- Posts to `https://api.resend.com/emails/batch` via `_resend_post()` (line 730-735)
- `_resend_post()` (line 44-61): retries once after 5s on non-200/201
- Checks `response.status_code in (200, 201)` and counts `sent += len(batch)`
- **Response body is discarded**. Resend returns `{"data":[{"id":"..."},...]}`  with per-email message IDs — these are never captured.
- `"Sent 5/5"` means **Resend accepted 5 emails for delivery**, not that they were delivered or opened.
- **Nothing is written to `newsletter_sends`** (0 rows as of tonight). No `newsletter_campaigns` rows either.

## 6. Content Pipeline

### Queue Producer
**File:** `services/stage_brief_pipeline.py:530-537` — `extract_intel()`
- Runs 3x/day: 06:00, 14:00, 22:00 UTC (cron entries)
- Generates brief script via LLM cascade (Anthropic -> Gemini -> Grok -> Qwen)
- Extracts intel: tweets, newsletter hook, sentiment, article seeds, oracle context
- Writes `data/newsletter_queue/{timestamp}_hook.json` with `{"generated_at", "brief_type", "hook"}`

### Template
**File:** `services/newsletter_engine.py:397-676` — `generate_html()`
- 6-section design: Masthead, The Number (BTC price), Signal Intelligence, Article Cards (top 3), The Signal, Satomi Is Watching, Footer
- All inline CSS, mobile-first, dark mode
- `generate_subject()` (line 261-318): Dynamic subject from BTC price + Fear & Greed + summary

### Content Sources
| Source | Function | File:Line |
|--------|----------|-----------|
| Articles | `get_todays_articles(5)` | `newsletter_engine.py:75-151` |
| AI Summary | `generate_ai_summary()` | `newsletter_engine.py:153-226` |
| BTC Price | `get_btc_price()` | `newsletter_engine.py:228-259` |
| Satomi Bullets | `generate_satomi_watching()` | `newsletter_engine.py:320-395` |
| Subject Line | `generate_subject()` | `newsletter_engine.py:261-318` |
| Hook Text | `stage_brief_pipeline.py:extract_intel()` | `stage_brief_pipeline.py:489-572` |

## 7. Database Tables

### `newsletter_sends` (0 rows)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| subject | TEXT | |
| resend_batch_id | VARCHAR(100) | |
| resend_message_id | VARCHAR(255) | Added via ALTER TABLE, not in root models.py |
| recipient_count | INTEGER | |
| open_count | INTEGER | |
| click_count | INTEGER | |
| sent_at | DATETIME | |
| article_ids | TEXT | Added via ALTER TABLE, not in root models.py |

ORM defined in:
- `core/models.py:1253-1269` — has `resend_message_id` + `article_ids`
- `models.py:1402-1416` (root) — missing `resend_message_id` + `article_ids`

The engine imports `from models import ...` (root `models.py`), running from project root inside app context.

### `newsletter_campaigns` (0 rows — models.py:1419-1432)
Tracks digest campaign sends. Never written to.

### `daily_brief` (1 row — core/models.py:664-673)
| Column | Type |
|--------|------|
| id | INTEGER PK |
| headline | VARCHAR(500) |
| body | TEXT |
| signals_json | TEXT |
| status | VARCHAR(20) |
| published_at | DATETIME |
| created_at | DATETIME |

## 8. Brief Writers (morning_intelligence_brief.json)

Multiple code paths write or read `data/intelligence/morning_intelligence_brief.json`:

### Writers:
| Writer | Schedule | Trigger |
|--------|----------|---------|
| `services/morning_brief.py:main()` | 11:00 UTC cron + 16:00 UTC cron | `crontab: 0 11 * * * ... services/morning_brief.py` + `0 16 * * *` |
| `scripts/morning_brief_cron.sh` -> `services.satomi_brief_generator` | 06:45 UTC cron | `crontab: 45 6 * * *` |
| `services/stage_brief_pipeline.py` | 06:00, 14:00, 22:00 UTC cron | Writes to `video_pipeline_v3/data/stage_briefs/` not `data/intelligence/` — but writes **newsletter hooks** to `data/newsletter_queue/` |

**`morning_brief.py`** is the primary writer of `morning_intelligence_brief.json`. It uses LLM cascade: Qwen3(local) -> Haiku -> Gemini -> Grok -> NVIDIA NIM. Output at line 534-538: atomic write via `.tmp` then `rename()`.

### Readers (not exhaustive):
- `services/tweet_machine.py` — for tweet generation
- `services/newsletter_service.py:399` — for oracle signal
- `core/routes_auth.py:722` — dashboard display
- `core/routes_api.py:7406` — API endpoint
- `video_pipeline_v3/daily_run.py:85` — video pipeline
- `video_pipeline_v3/utils/narrative_intelligence.py:313` — narrative context
- `services/image_of_the_day.py:14` — image generation context

---

## 9. Newsletter Module Inventory

| Module | Path | Imported By | Called By (cron/scheduler/route) | Verdict |
|--------|------|-------------|----------------------------------|---------|
| `newsletter_engine.py` | `services/newsletter_engine.py` | APScheduler (`core/app.py:409`), `routes_api.py:1354` via importlib | APScheduler daily 12:00 UTC, POST `/api/newsletter/dispatch` | **IN USE** — primary send engine |
| `newsletter_service.py` | `services/newsletter_service.py` | `newsletter_automation.py:49`, `cron/newsletter_cron.py:49` | Has `send_daily_newsletter()` called by automation/cron paths | **IN USE** — B1 alternate send path |
| `newsletter_automation.py` | `services/newsletter_automation.py` | `services/scheduler.py` (if APScheduler alternate) | Was intended as APScheduler entry at 13:00 UTC | **UNCLEAR** — may be superseded by app.py dispatcher |
| `newsletter_digest.py` | `services/newsletter_digest.py` | None found in current codebase active paths | No scheduler/cron/route references | **UNUSED** — "Sovereign Signal" 4-pass pipeline, uses OpenAI GPT-4o |
| `newsletter_alpha_integration.py` | `services/newsletter_alpha_integration.py` | No active callers found | No scheduler/cron/route | **UNUSED** — premium/free tier HTML section generator |
| `resend_newsletter.py` | `services/resend_newsletter.py` | No active callers found | No scheduler/cron/route | **UNUSED** — early Resend service class, `from_email` still uses old domain |
| `newsletter.py` (services/) | `services/newsletter.py` | `models.py` import at top level | No active route or scheduler | **UNUSED** — SendGrid-based, superseded by Resend |
| `newsletter.py` (core/services/) | `core/services/newsletter.py` | Blueprint routes in `core/` context | Has `send()` method, used by B1 cron path | **IN USE** — B1 Gospel engine (uses `resend` package directly) |
| `newsletter.py` (core/blueprints/) | `core/blueprints/newsletter.py` | Flask app blueprint registration | Routes: GET `/newsletter`, POST `/newsletter/subscribe`, GET `/newsletter/unsubscribe` | **IN USE** — subscriber management UI |
| `email_templates.py` | `services/email_templates.py` | Double opt-in flow, welcome emails | Subscribe routes | **IN USE** — dark-themed email templates |
| `newsletter_cron.py` | `cron/newsletter_cron.py` | Standalone script | System cron (alternate to APScheduler) | **UNCLEAR** — may run if APScheduler fails |
| `routes_newsletter_trigger.py` | `routes_newsletter_trigger.py` | Flask blueprint | POST `/api/newsletter/send` — single recipient (pbx@) | **IN USE** — minimal daily digest trigger |
| `routes_newsletter_b1.py` | `routes_newsletter_b1.py` | Flask blueprint | POST `/api/newsletter/subscribe`, GET `/unsubscribe`, POST `/api/newsletter/send` | **IN USE** — B1 subscribe/unsubscribe/admin-send |
| `mining_intel/newsletter_monitor.py` | `mining_intel/newsletter_monitor.py` | Mining intel pipeline | Monitors newsletter health | **IN USE** — monitoring only |

---

## 10. Known Gaps (pre-tracking)

1. **No send records**: `newsletter_sends` has 0 rows. Response body (message IDs) discarded.
2. **No open/click tracking**: `open_count` and `click_count` always 0. No Resend event polling.
3. **No brief archival**: `daily_brief` has 1 row from March. `morning_intelligence_brief.json` is overwritten each run with no DB persistence.
4. **Queue accumulation**: 84 orphan hook files. Only newest consumed per day.
5. **EST/EDT mismatch**: Comment says 8 AM ET but 12:00 UTC = 7:00 AM EST.
6. **Duplicate dispatch logic**: `core/app.py` scheduler and `core/routes_api.py` POST route have identical copy-pasted logic.
7. **Root vs core models.py divergence**: Root `models.py` `NewsletterSend` is missing `resend_message_id` and `article_ids` columns that exist in `core/models.py` and in the actual DB schema.

---

## Session log 2026-11-09

### Commits
| # | Hash | Description |
|---|------|-------------|
| 1 | `2d5a6c98` | docs: NEWSLETTER_SEND_PATH.md — full send path trace + module inventory |
| 2 | `0a0945df` | feat: record every newsletter send to newsletter_sends DB |
| 3 | `22b3534f` | feat: newsletter_stats_poller.py — poll Resend for opens/clicks |
| 4 | `98f63387` | feat: archive morning briefs to daily_brief DB table |

All merged to origin/main via fast-forward push.

### Test outputs

**newsletter_sends row (Step 2):**
```
subject       = Test Subject $99,999
resend_batch_id = 80c702a8-adcc-4376-b8bb-91de7ee2e6e9
resend_message_id = ["test-msg-0", "test-msg-1", "test-msg-2"]
recipient_count = 3
open_count = 0, click_count = 0
sent_at = 2026-11-09 23:30:17
article_ids = [101, 202, 303]
```

**daily_brief row (Step 4):**
```
id        = 2
headline  = Institutional accumulation deepens
body      = (full brief JSON, 528 chars)
signals   = {"key_stats_today": ..., "sentiment": "bullish", "generated_by": "test"}
status    = generated
created_at = 2026-11-09 23:32:53
```

**Poller dry-run (Step 3):**
```
Found 1 sends to poll
Send 1 (Test Subject $99,999...): polling 3 message IDs
[dry-run] Would GET https://api.resend.com/emails/test-msg-0
[dry-run] Would GET https://api.resend.com/emails/test-msg-1
[dry-run] Would GET https://api.resend.com/emails/test-msg-2
[dry-run] Send 1: 3 messages, no updates
```

### Resend domain tracking status
```
protocolpulse.io:  open_tracking=OFF, click_tracking=ON,  status=verified
yespbx.com:        open_tracking=OFF, click_tracking=OFF, status=verified
thebtcboomers.com: open_tracking=OFF, click_tracking=OFF, status=failed
```
**Action required:** Enable open_tracking on protocolpulse.io in Resend dashboard for open counts to work.

### What remains for deploy

1. **Production checkout** `/home/ultron/protocol_pulse` is on branch `combo-letterbox-quoteonly-v2`, not `main`. Deploy = cherry-pick these 4 commits (or `git pull origin main`) into that checkout once the `pipeline_pp_vert` tmux session is closed.
2. **newsletter_engine.py changes go live** on the next 07:00 EST dispatch with no Waitress restart (importlib re-imports from disk each run).
3. **morning_brief.py changes** require no restart — it runs from cron each time.
4. **newsletter_stats_poller.py** needs its cron line installed after deploy.

### Proposed cron line for poller (do NOT install yet)
```
0 * * * * flock -n /tmp/nl_stats_poller.lock python3 /home/ultron/protocol_pulse/services/newsletter_stats_poller.py >> /home/ultron/protocol_pulse/logs/newsletter_stats.log 2>&1
```

### Regression
- `py_compile` PASS on all 3 changed Python files
- Test scripts: 4/4 assertions PASS (2 send tests, 2 brief tests)
- No existing files modified except `services/newsletter_engine.py` and `services/morning_brief.py`
- `regression_test.sh` not run (paths hardcoded to `~/protocol_pulse`, cannot run from worktree)

### Audit round 2026-11-09

**Round 1:** `/home/ultron/audits/newsletter_tracking_20261109/audit.md`
Panel: deepseek, qwen27b, glm. 4 consensus findings:
1. [medium] Stale article IDs leak when html provided without article_ids
2. [medium] NULL subject crash in poller `subject[:40]`
3. [low] morning_brief _archive_brief_to_db: connection not closed on exception
4. [low] poller poll(): connection not closed on exception

Non-consensus (noted, not implemented):
- deepseek F1: _record_send exceptions could escape before inner try, flipping result to success=False. Mitigated by _record_send's own try/except wrapping all logic including imports; the outer try would only catch truly unexpected failures.
- qwen partial-batch: `sent += len(batch)` counts full batch on HTTP 200, but Resend may later reject individuals. The count reflects API acceptance, not delivery — matches existing semantics. True delivery count comes from the poller.

**Round 2:** `/home/ultron/audits/newsletter_tracking_20261109_r2/audit.md`
Panel: deepseek, qwen27b, glm. 1 consensus finding:
1. [low] Dead variable `remembered_ids` — removed.

No other findings. All 4 original findings confirmed fixed.
