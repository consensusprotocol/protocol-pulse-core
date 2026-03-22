# CONSENSUS REPORT — F2-BRIEFING-ROOM — CYCLE 1
Generated: 2026-03-09 02:33
Models: grok, gemini, gpt4o

---

## SCORES

Scores are synthesized from each model's implicit severity ratings, coverage, and confidence signals across all sections.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 6.5/10 | 6.0/10 | 6.5/10 | **6.3/10** |
| Law Compliance | 7.0/10 | 5.5/10 | 7.5/10 | **6.7/10** |
| Security | 8.5/10 | 7.0/10 | 7.5/10 | **7.7/10** |
| Frontend Quality | 6.0/10 | 5.5/10 | 7.0/10 | **6.2/10** |
| Backend Quality | 8.5/10 | 7.0/10 | 8.0/10 | **7.8/10** |
| **Overall** | **7.3/10** | **6.2/10** | **7.3/10** | **6.9/10** |

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

These findings carry maximum confidence. Every model independently identified them.

---

### U1 — Video swap does not update associated metadata
**File:** `core/templates/market_briefing.html` ~line 786–838
**What:** When a user clicks a previous briefing card, the `loadBriefing()` JS function swaps the `<video>` source and the main title, but leaves all associated metadata stale: timestamp, duration, BTC-at-generation price, and the script panel content remain anchored to the most-recent briefing.
**Fix:** Extend `loadBriefing()` to accept and render all card data attributes. Add `data-timestamp`, `data-duration`, `data-btc-price`, `data-script` on each card element (the template already sets `data-script` but JS never reads it). On card click, update all displayed metadata fields and the script panel alongside the video source.

---

### U2 — Timezone-string-to-Date anti-pattern in countdown timer
**File:** `core/templates/market_briefing.html` ~line 714–718
**What:** `toETDate()` calls `toLocaleString('en-US', { timeZone: 'America/New_York' })` and then passes the resulting locale-formatted string directly into `new Date()`. This is a widely-documented anti-pattern; behavior is browser, OS, and locale-dependent and will produce wrong countdowns for a material portion of users.
**Fix:** Use the `Intl` API correctly, or compute ET offset arithmetic explicitly using a fixed UTC offset (`-5` / `-4` depending on DST) without re-parsing a locale string. Alternatively, serve the next-slot timestamp as a UTC epoch from the backend and let the frontend compute the diff.

---

### U3 — LAW 4 (/stage → 302 → /briefing) is unverifiable — route file missing
**File:** Routes file (not provided — likely `core/routes.py` or `app.py`)
**What:** All three models flagged that the redirect from `/stage` to `/briefing` (permanent 302) cannot be verified because no route definitions were supplied. The template exists but the wiring is absent from reviewed code.
**Fix:** Provide and review the route file. Confirm `redirect(url_for('briefing'), code=302)` is present on the `/stage` route. Add an automated smoke test that asserts the 302 response code.

---

### U4 — Cost guard race condition allows duplicate generation
**File:** `core/services/briefing_service.py` ~line 243–266, 294–315
**What:** `_check_cost_guard()` performs a COUNT query, then the caller separately creates a new `MarketBriefing` row. These two operations are not atomic. Two concurrent workers (e.g., scheduler restart, duplicate cron fire) can both pass the guard before either inserts its row, resulting in duplicate briefings for the same slot and budget overruns.
**Fix:** Wrap the guard check and the row insert in a single serialized transaction, or add a DB-level unique constraint on `(date, slot_type)` (e.g., `UNIQUE(briefing_date, slot)`) so the second insert fails gracefully, then catch the `IntegrityError` and abort cleanly.

---

### U5 — UTC timestamps displayed as ET in template without conversion
**File:** `core/templates/market_briefing.html` ~line 600, 683; `core/services/briefing_service.py` ~line 296
**What:** `generated_at` is stored as naive UTC (`datetime.utcnow()`), but the template formats it with an "ET" label (e.g., `strftime('%-I:%M %p ET · %b %-d, %Y')`). This displays the wrong time for all users — UTC timestamps labelled as Eastern Time are off by 4–5 hours.
**Fix:** Either (a) store `generated_at` as timezone-aware UTC and convert to ET in the template/route before rendering, or (b) store as ET-aware datetime at write time using `datetime.now(pytz.timezone('America/New_York'))`. Option (a) is preferred for correctness.

---

## MAJORITY FINDINGS (2 of 3 models agree)

These issues were independently confirmed by two models and should be implemented.

---

### M1 — Incomplete cost guard: failed briefings not counted
**Models:** Gemini + GPT-4o
**File:** `core/services/briefing_service.py` ~line 254
**What:** `_check_cost_guard()` filters for `status IN ('generating', 'completed')`. A briefing can fail *after* the Claude API call (the expensive step) has already executed and been billed. Not counting `'failed'` records means the guard will allow new attempts that exceed the actual budget already consumed.
**Fix:** Add `'failed'` to the status list in the cost guard query: `status IN ('generating', 'completed', 'failed')`.

---

### M2 — `asia_data` variable passed to prompt but no matching `{asia_data}` placeholder used
**Models:** Gemini + GPT-4o
**File:** `core/services/briefing_service.py` ~line 152–156
**What:** `asia_data` is formatted into `prompt.format(...)` but the prompt template string does not contain a `{asia_data}` placeholder (or if it does, the data is a static hardcoded string: `"Asian markets closed mixed; see latest data."`). Either the variable is silently dropped or the prompt contains stale placeholder logic.
**Fix:** Either (a) implement a real Asian market data fetch and wire it into the prompt with a proper `{asia_data}` placeholder, or (b) remove the variable entirely and remove the dead format argument to avoid silent confusion.

---

### M3 — Claude API call has no explicit timeout
**Models:** Gemini + Grok
**File:** `core/services/briefing_service.py` ~line 158–165
**What:** All external API calls in this codebase have explicit timeouts (HeyGen: `203`, BTC price: `107`, `117`), but the Claude API call does not. A slow or hung Claude response will block the cron worker indefinitely, stalling the entire briefing pipeline.
**Fix:** Add `timeout=60` (or appropriate value) to the Claude API call, and catch `anthropic.APITimeoutError` explicitly to log and fail gracefully.

---

### M4 — `pollLatest()` silently swallows errors, no user feedback
**Models:** Gemini + GPT-4o + Grok (all three mentioned, framing varies — escalated from majority to near-unanimous)
**File:** `core/templates/market_briefing.html` ~line 847–865
**What:** The fetch polling loop that calls `/api/briefing/latest` every 2 minutes catches errors but shows no UI feedback when the endpoint fails. Users remain unaware that status polling has broken.
**Fix:** On fetch error or non-200 response, update a visible status indicator (e.g., the "Next Briefing In" region or a subtle banner) to reflect connectivity issues rather than silently continuing.

---

### M5 — `%-d` strftime directive is platform-specific / non-portable
**Models:** GPT-4o + Grok (implicitly)
**File:** `core/services/briefing_service.py` ~line 296
**What:** `datetime.utcnow().strftime("%b %-d, %Y")` uses `%-d` (no zero-pad), which works on Linux/glibc but fails on Windows and some BSD-derived systems with a `ValueError`.
**Fix:** Replace with `strftime("%b {d}, %Y").format(d=dt.day)` or `f"{dt.strftime('%b')} {dt.day}, {dt.year}"` for full portability.

---

### M6 — Briefing schedule hardcoded in both cron and template (maintenance liability)
**Models:** Gemini + GPT-4o
**File:** `core/templates/market_briefing.html` ~line 642–644, 708–712; `cron/briefing_cron.py` ~line 65–93
**What:** The three briefing times (07:00, 09:30, 16:30 ET) are defined in the cron file and duplicated in the frontend JS countdown. A schedule change requires editing two separate files; one being missed breaks the countdown display.
**Fix:** Expose the schedule as a shared config constant (e.g., `config.py: BRIEFING_SLOTS = [(7,0), (9,30), (16,30)]`), import it into the cron, and inject it into the template context from the route so the JS reads from a single source of truth.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

---

### X1 — `db.create_all()` at app startup masks migration drift
**Model:** GPT-4o only
**File:** `app.py` ~line 241–247
**Assessment:** **IMPLEMENT.** This is a well-known and serious anti-pattern in production Flask apps using Alembic. `create_all()` will silently create missing tables rather than surfacing the fact that migrations are out of date, making schema drift invisible until it causes data corruption. **Remove `db.create_all()` from startup and rely exclusively on Alembic migrations.**

---

### X2 — HeyGen may return 201/202 for async job acceptance, code only accepts 200
**Model:** GPT-4o only
**File:** `core/services/briefing_service.py` ~line 205–211
**Assessment:** **INVESTIGATE FURTHER.** If HeyGen's v2 `/video/generate` endpoint returns 201 or 202 (accepted but not yet started), the current check `if response.status_code == 200` will incorrectly treat a valid submission as a failure. Confirm against HeyGen API documentation what success codes are possible. Fix to `if response.status_code in (200, 201, 202)` if confirmed.

---

### X3 — Mixed HeyGen API versions (v2 generate, v1 status poll)
**Model:** GPT-4o only
**File:** `core/services/briefing_service.py` ~line 199–203, 219–223
**Assessment:** **INVESTIGATE FURTHER.** Using `/v2/video/generate` for submission and `/v1/video_status.get` for polling is unusual. This may be correct per HeyGen's current API design (they retained v1 for status endpoints), but it should be explicitly verified against their documentation. A breaking change in v1 deprecation would silently break all polling without touching the generation code.

---

### X4 — Missing mempool stats and network data from script generation inputs
**Model:** GPT-4o only (Gemini noted the hardcoded `asia_data` but didn't flag missing mempool/network data)
**File:** `core/services/briefing_service.py` ~line 147–171
**Assessment:** **IMPLEMENT if gospel requires it.** If the F2 Gospel specifies that mempool stats and Bitcoin network data are required inputs to the script prompt, their absence is a LAW 5 compliance gap, not just a quality gap. Review the gospel and either add the data fetching or formally de-scope it.

---

### X5 — WebSocket push available but polling used instead
**Model:** Gemini only
**File:** `core/templates/market_briefing.html` ~line 847–865; `app.py`
**Assessment:** **INVESTIGATE / P2.** Flask-SocketIO is in the stack. Real-time push for briefing-ready events would eliminate the 2-minute polling lag and the page-reload churn when `status == 'generating'`. This is a genuine world-class gap, but it's a feature enhancement rather than a bug. Flag for Cycle 2 or backlog.

---

### X6 — Repeated page reloads while status is 'generating' causes UX churn
**Model:** GPT-4o only
**File:** `core/templates/market_briefing.html` ~line 840–845
**Assessment:** **IMPLEMENT.** If a briefing is stuck in `'generating'` for an extended period (HeyGen slow, retries happening), the page reloads every 30 seconds indefinitely. This creates a disorienting loop. **Cap reload attempts** (e.g., max 10 reloads = 5 minutes) and then display a "Briefing delayed — check back soon" message rather than infinite churn.

---

## CONFLICTS (models disagree — tiebreaker)

---

### C1 — LAW 3 compliance: COMPLIANT vs. PARTIAL
**Grok:** COMPLIANT — template renders last 3 briefings.
**Gemini + GPT-4o:** PARTIAL — depends on un-reviewed route query; cannot confirm the latest is excluded from the `recent` set or that exactly 3 are always returned.

**Tiebreaker: Gemini + GPT-4o are correct.** Template compliance alone is insufficient. The law requires the *backend route* to always inject exactly 3 *previous* (non-latest) briefings into the template context. Without verifying the route query (`offset(1).limit(3)` or equivalent), this is unproven. **Verdict: PARTIAL.**

---

### C2 — Authentication: gap vs. not applicable
**Grok:** Flags missing authentication as a potential security gap on briefing routes.
**Gemini:** Explicitly states "not applicable — the briefing page is public."

**Tiebreaker: Gemini is correct** for the public display page. However, Grok's concern has merit *if any manual trigger endpoint exists*. The generation service should never be callable from a public HTTP endpoint. Since the cron is the only confirmed trigger and the service doesn't expose an HTTP endpoint in reviewed code, this is not a current vulnerability — but should be explicitly documented and guarded if manual triggers are ever added.

---

### C3 — Security posture: "strong" vs. "gaps in rate limiting"
**Gemini:** Security posture is strong; cost guard is domain-specific and sufficient.
**Grok + GPT-4o:** Rate limiting gaps on briefing routes are a concern.

**Tiebreaker: Gemini is correct for the current architecture.** The expensive generation path is cron-only and never user-triggered, making IP-based rate limiting moot for the generation cost. The cost guard is adequate. The display page is read-only. Security rating should be "good" not "gapped" for the current design.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

These areas are production-grade. Leave them alone.

1. **SQLAlchemy ORM usage throughout** — No raw SQL, no injection risk. All three models confirmed.
2. **DB write integrity** — Every write path in `briefing_service.py` has `try/except` with `db.session.rollback()`. Confirmed excellent by all models.
3. **HeyGen retry logic** — Max 2 retries enforced correctly, failure logged gracefully. Confirmed LAW 2 compliant.
4. **BTC price fetch** — Has timeout, two API sources with fallback, graceful degradation. All models approved.
5. **Secrets management** — No hardcoded credentials. All API keys from environment variables. Confirmed by all models.
6. **Cron isolation** — `except Exception` wrapper in `briefing_cron.py` prevents one failed job from crashing the scheduler. Confirmed excellent.
7. **LAW 1 avatar** — Sarah avatar ID and 1280x720 resolution are correctly hardcoded as constants. All models confirmed compliant.
8. **CSS/UI aesthetic** — Professional "broadcast" aesthetic confirmed world-class by all models. Do not redesign.
9. **Video empty/error states** — `generating`, `failed`, `unavailable` states handled gracefully in the player. All models approved.
10. **HeyGen polling fault tolerance** — Polling loop is timeout-bounded and fails cleanly. All models confirmed.

---

## LAW COMPLIANCE CONSENSUS

| Law | Verdict | Confidence | Blocker? |
|---|---|---|---|
| LAW 1: HeyGen Sarah only | ✅ COMPLIANT | High | No |
| LAW 2: 3 briefings/day, fixed schedule | ⚠️ PARTIAL | High | Yes (duplicate risk) |
| LAW 3: Always show last 3 briefings | ⚠️ PARTIAL | High | Yes (route unverified) |
| LAW 4: /stage → 302 → /briefing | ❌ UNVERIFIED | High | Yes (code not provided) |
| LAW 5: Claude-generated scripts | ⚠️ PARTIAL | High | Soft (missing data inputs) |

**LAW 2 gap:** No uniqueness guard prevents duplicate briefings per slot/day.
**LAW 3 gap:** Route query not reviewed; cannot confirm exactly-3 previous (non-latest) briefings always returned.
**LAW 4 gap:** Route file entirely absent from review. This is the most critical compliance blocker — the redirect either exists or doesn't and there is zero evidence either way.
**LAW 5 gap:** `asia_data` is hardcoded/broken. Mempool/network data potentially missing per gospel. No hard word-count enforcement.

---

## SECURITY CONSENSUS

All three models assessed security as generally sound. No critical vulnerabilities were found. Issues in priority order:

1. **(Medium) Cost guard race condition** — Two workers can bypass the guard simultaneously. Mitigated by DB unique constraint (see U4). Not an external attack vector but a real operational risk.
2. **(Low) No explicit Claude timeout** — Not a security issue per se, but a DoS-adjacent reliability gap that could exhaust cron worker threads.
3. **(Info) Rate limiting on display routes** — Agreed non-issue given public read-only nature. No action needed.
4. **(Info) Manual trigger surface** — No public endpoint confirmed. If one is added in future, it must be authenticated + rate-limited.

---

## WORLD-CLASS GAP CONSENSUS

Items confirmed by 2+ models as missing from a truly world-class product:

1. **[2/3 — Gemini + GPT-4o] Full context update on briefing selection** — Clicking a previous briefing should update ALL associated context (metadata, script panel, BTC price, timestamp), not just the video. Bloomberg/Blockworks-class terminals treat the selected item as the new focal point. This is the single highest-impact UX improvement.

2. **[2/3 — Gemini + Grok] Real-time delivery vs. polling** — A world-class financial briefing product pushes the "briefing ready" event to connected clients instantly (WebSocket), rather than making users wait up to 2 minutes for polling to catch up. The infrastructure (Flask-SocketIO) is already in the stack.

3. **[2/3 — Gemini + GPT-4o] Missing transcript/closed captions** — No synchronized transcript or closed captions for the video briefing. A professional financial product must be accessible to hearing-impaired users and support silent viewing in trading-floor environments. This is both a product quality and accessibility gap.

4. **[2/3 — GPT-4o + Grok] No shareable briefing links / deep links** — Individual briefings cannot be directly linked. A world-class product should generate a permanent, shareable URL for each briefing (e.g., `/briefing/2026-03-09/premarket`) to enable sharing in trading communities, Discord, or newsletters.

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Add DB unique constraint on `(briefing_date, slot)` and catch `IntegrityError` in service to prevent duplicate briefings | `briefing_service.py:294-315` + migration | all 3 | Race condition allows budget overrun and data corruption; LAW 2 violation |
| P0-2 | Provide and review route file; confirm `/stage` → 302 → `/briefing` redirect exists | `routes.py` or `app.py` (missing) | all 3 | LAW 4 cannot be verified without this file; may be a complete compliance failure |
| P0-3 | Fix UTC→ET timestamp bug: convert `generated_at` to ET before rendering in template | `market_briefing.html:600,683` + `briefing_service.py:296` | all 3 | Timestamps labelled "ET" are 4–5 hours wrong for all users |
| P0-4 | Fix video swap: update all metadata (timestamp, duration, BTC price, script panel) when a previous briefing card is clicked | `market_briefing.html:786-838` | all 3 | Watching old video with latest metadata is factually incorrect and damages trust |
| P0-5 | Add `'failed'` to cost guard status filter | `briefing_service.py:254` | gemini + gpt4o | Budget already consumed on failed attempts is not counted, enabling overruns |
| P0-6 | Fix or remove broken `asia_data` variable; implement real fetch or remove dead code | `briefing_service.py:152-156` | gemini + gpt4o | Silent broken prompt logic; LAW 5 compliance gap |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Fix timezone countdown anti-pattern: use UTC epoch from backend or correct Intl offset arithmetic | `market_briefing.html:714-718` | all 3 | Countdown shows wrong time for material % of users |
| P1-2 | Add explicit timeout to Claude API call; catch `APITimeoutError` | `briefing_service.py:158-165` | gemini + grok | Only external call without timeout; can block cron worker indefinitely |
| P1-3 | Remove `db.create_all()` from app startup; rely exclusively on Alembic migrations | `app.py:241-247` | gpt4o | Masks migration drift; dangerous in production |
| P1-4 | Fix/extract schedule config to single source of truth; inject into template from route | `market_briefing.html:642-644,708-712` + `briefing_cron.py:65-93` + `config.py` | gemini + gpt4o | Duplication creates maintenance hazard; schedule change requires two-file sync |
| P1-5 | Cap page-reload attempts when `status == 'generating'` (max 10 × 30s = 5 min), then show "briefing delayed" message | `market_briefing.html:840-845` | gpt4o | Infinite reload loop is disorienting and wastes resources |
| P1-6 | Add error UI feedback to `pollLatest()` on fetch failure | `market_briefing.html:847-865` | all 3 | Silent failure leaves users with no indication polling has broken |
| P1-7 | Verify route query always returns exactly 3 *previous* (non-latest) briefings; implement `offset(1).limit(3)` if missing | `routes.py` (missing) | gemini + gpt4o | LAW 3 compliance