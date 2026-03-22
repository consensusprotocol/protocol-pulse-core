# CONSENSUS REPORT — F2-BRIEFING-ROOM — CYCLE 2
Generated: 2026-03-09 02:36
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok | Consensus |
|------------------|--------|--------|------|-----------|
| Correctness      | 4.0/10 | 5.5/10 | 6.0/10 | **5.2/10** |
| Law Compliance   | 7.0/10 | 6.5/10 | 6.5/10 | **6.7/10** |
| Security         | 8.0/10 | 7.2/10 | 8.0/10 | **7.7/10** |
| Frontend Quality | 5.0/10 | 5.8/10 | 6.0/10 | **5.6/10** |
| Backend Quality  | 5.5/10 | 6.8/10 | 7.5/10 | **6.6/10** |
| **Overall**      | **5.9/10** | **6.1/10** | **6.8/10** | **6.3/10** |

> **Consensus note:** Gemini's Correctness score of 4.0 reflects the most pessimistic read — anchored by idempotency failure and multi-commit transaction management. GPT-4o and Grok were less severe on those same issues. The consensus lands at 5.2 to reflect that these are real, ship-blocking flaws without overweighting the worst-case framing.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Video swap does not update associated metadata or script panel
- **What it is:** `loadBriefing()` in the JS player swaps the `<video>` source and the main title when a user clicks a previous briefing card, but leaves all other UI state stale: timestamp, BTC-at-generation, duration, poster image, and the script panel continue to show data from the most recent briefing. A user watching a 9:30 AM briefing sees the 4:30 PM script and price.
- **File/line:** `core/templates/market_briefing.html:786–838`
- **Fix:** Extend `loadBriefing()` to accept the full briefing data object (or fetch it by ID) and update every bound UI element: `#featuredTimestamp`, `#featuredBTCPrice`, `#featuredDuration`, `#scriptPanelText`, poster attribute, and any other metadata fields. Prefer fetching by ID to avoid embedding large payloads in data attributes.

### U2 — Countdown timer uses `toLocaleString → new Date()` anti-pattern
- **What it is:** The "Next Briefing In" countdown converts UTC to ET using `nowUTC.toLocaleString('en-US', { timeZone: 'America/New_York' })` and feeds the resulting locale string into `new Date()`. This is undefined behavior: the Date constructor does not accept locale-formatted strings, and parsing behavior varies across V8, Firefox, Safari, and non-US OS locales. Countdown will be wrong or `NaN` for a meaningful fraction of users.
- **File/line:** `core/templates/market_briefing.html:714–718`
- **Fix:** Send the next scheduled briefing's UTC epoch timestamp from the backend (e.g., as a `data-next-briefing-utc` attribute on the countdown element). In JS, compute the delta directly from `Date.now()` vs that UTC epoch — no locale string conversion needed.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — No idempotency check before generating a new briefing (GPT-4o + Gemini)
- **What it is:** `generate_briefing()` creates a new `MarketBriefing` DB row unconditionally. If the APScheduler fires twice for the same slot (container restart, delayed job, multi-process deployment), two Claude calls, two HeyGen renders, and two DB rows are created. Cost is doubled; UI shows duplicates.
- **File/line:** `core/services/briefing_service.py:294–315`
- **Fix:** Before inserting, query for an existing non-failed briefing with the same `briefing_type` and ET calendar date. If found, log and return early. Pair this with a unique database constraint on `(briefing_type, date)` to enforce at the storage layer.

### M2 — Cost guard excludes `failed` status, allowing budget overruns (Gemini + GPT-4o)
- **What it is:** `_check_cost_guard()` queries for recent briefings with status `generating` or `completed`. A briefing that fails *after* the Claude API call has already been billed is not counted. In a persistent failure loop, the guard never trips and costs accumulate unbounded.
- **File/line:** `core/services/briefing_service.py:254`
- **Fix:** Add `'failed'` to the status filter in the cost guard query. Optionally, track a dedicated `api_cost_incurred` boolean flag set the moment any paid API call completes, regardless of subsequent pipeline status.

### M3 — UTC timestamps displayed with hardcoded "ET" label (GPT-4o + Grok)
- **What it is:** The template formats `generated_at` — which is stored as a naive UTC datetime — using strftime with a literal `ET` suffix appended. The time shown to users is UTC, but it reads as Eastern Time, which is factually wrong by 4–5 hours depending on DST.
- **File/line:** `core/templates/market_briefing.html:600`, `683`
- **Fix:** Either (a) store `generated_at` as a timezone-aware datetime in ET (use `pytz.timezone('America/New_York')` at write time), or (b) convert naive UTC to ET at template render time using a Jinja filter. Option (a) is cleaner for this use case.

### M4 — Cost guard race condition: check and insert are non-atomic (Grok + GPT-4o)
- **What it is:** `_check_cost_guard()` reads the DB, then the caller proceeds to insert a new row. In concurrent execution (two simultaneous cron fires, two web requests), both processes can pass the guard before either has committed its new row. This negates the guard entirely under concurrency.
- **File/line:** `core/services/briefing_service.py:243–266`, `273–289`
- **Fix:** Wrap the guard check and the initial row insert in a single database transaction using `SELECT ... FOR UPDATE` or a DB-level unique constraint (see M1) that causes a duplicate to raise an integrity error. The idempotency fix in M1 partially addresses this when combined with a unique constraint.

### M5 — Hardcoded `asia_data` placeholder undermines pre-market briefing value (Gemini + GPT-4o)
- **What it is:** `briefing_service.py:155` sets `asia_data = "Asian markets closed mixed; see latest data."` — a static string. This is passed into the Claude prompt for the 7:00 AM pre-market briefing, which is supposed to synthesize overnight Asian market action. Every pre-market briefing says the same thing about Asia regardless of what actually happened.
- **File/line:** `core/services/briefing_service.py:155`
- **Fix:** Integrate a real Asian market data source (e.g., a market data API or scraped index data) for the pre-market slot. If no real data source is available at launch, remove the placeholder from the prompt rather than passing false specificity.

### M6 — Multiple intermediate `db.session.commit()` calls break transaction atomicity (Gemini + GPT-4o implied)
- **What it is:** `generate_briefing()` commits to the database at each pipeline stage (after script generation, after HeyGen submission, after polling). A failure mid-pipeline leaves an orphan row permanently stuck in `generating` status with no recovery path. The feature has no cleanup job for stuck rows.
- **File/line:** `core/services/briefing_service.py:294–403`
- **Fix:** Restructure so the DB row is written once at the start as `pending`, updated in-memory throughout the pipeline, and committed as a single final write on success. On any exception, rollback and mark the row `failed` in a single commit inside the `except` block.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### Unique-1 — `data-script` attribute embeds raw freeform text, risking broken HTML/JS (GPT-4o)
- **What it is:** The template writes `data-script="{{ b.script_text | truncate(300) }}"` into an HTML attribute. Script text containing quotes, angle brackets, newlines, or Jinja-escaped characters can break attribute parsing, produce malformed DOM, or cause `loadBriefing()` to receive corrupted data.
- **Assessment:** **Implement.** The risk is real. The fix is to store briefing data as a `<script type="application/json">` block or fetch it from an API endpoint on click. Additionally, truncating to 300 characters means `loadBriefing()` can never show the full script regardless — which compounds U1.

### Unique-2 — Truncated `data-script` means full script never reachable even after U1 fix (GPT-4o)
- **What it is:** Even if `loadBriefing()` is fixed to read `data-script`, the template only stores the first 300 characters. The script panel for historical briefings will always be cut off.
- **Assessment:** **Implement fix alongside U1.** Either embed the full script in a JSON block or fetch the full record by briefing ID via an API call in `loadBriefing()`. Fetching by ID is the cleaner solution and resolves Unique-1 at the same time.

### Unique-3 — APScheduler jobs missing `max_instances=1` and `coalesce=True` (GPT-4o)
- **What it is:** Without `max_instances=1`, APScheduler can queue multiple instances of the same job if a previous run is still executing at the next fire time. Without `coalesce=True`, missed fires are all executed in rapid succession on recovery. Both settings are trivial to add and provide a first line of defense before application-level deduplication.
- **Assessment:** **Implement.** Low-effort, high-value scheduler hardening. Complements M1 but does not replace it.

### Unique-4 — HeyGen video URLs may expire, breaking archived briefings (Grok)
- **What it is:** The `video_url` and `thumbnail_url` returned by HeyGen are stored in the DB permanently but may be time-limited CDN URLs. Older briefings could return 403/404, silently breaking playback for any briefing older than the URL TTL.
- **Assessment:** **Investigate before shipping.** Check HeyGen documentation for URL expiry. If URLs are ephemeral, implement a background job to download and re-host videos on owned storage (S3, R2, etc.) after generation completes.

### Unique-5 — `%-d` strftime format is not portable across all Linux/Mac configurations (GPT-4o)
- **What it is:** `datetime.utcnow().strftime("%b %-d, %Y")` uses a platform-specific GNU extension. It works on Ubuntu but fails on some BSD-derived systems and certain container base images.
- **Assessment:** **Implement.** Simple fix: use `strftime("%b {d}, %Y").format(d=dt.day)` or `lstrip('0')` on `%d`. Low risk to change, real portability benefit.

### Unique-6 — Countdown timer ignores DST transitions at boundary (Grok)
- **What it is:** Beyond the `toLocaleString` anti-pattern (U2), even a corrected implementation would need to account for DST transitions affecting Eastern Time schedule offsets. A briefing scheduled for 7:00 AM ET crosses the UTC offset change from -5 to -4 twice a year.
- **Assessment:** **Addressed by U2 fix.** If the backend sends the exact UTC epoch of the next scheduled briefing, the client-side countdown is automatically DST-correct. No additional fix needed beyond U2.

### Unique-7 — Script length (180-word cap) enforced only in prompt, not validated post-generation (Grok)
- **What it is:** The Claude prompt requests ≤180 words, but the code does not count or truncate the response. Claude can and occasionally does exceed prompt constraints. An overlong script produces a video longer than the intended ~90 seconds.
- **Assessment:** **Implement.** Add a word count assertion after Claude returns. If exceeded, either re-prompt with stricter instruction or truncate at the last complete sentence before the limit. Log a warning either way.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1 — HeyGen HTTP 200-only success check (GPT-4o flagged; Grok partially agreed; Gemini did not flag)
- **GPT-4o position:** The code treats only HTTP 200 as success for the HeyGen generate call. For async APIs, 201/202 are common, and false failures could result.
- **Grok position:** Partially agree — depends on HeyGen docs.
- **Gemini position:** Did not surface this concern.
- **Tiebreaker:** GPT-4o is correct to flag this as a risk, but the resolution depends on HeyGen's actual API contract. **Verdict: Investigate.** Check HeyGen v2 API documentation for the exact success response codes on `POST /v2/video/generate`. If 201/202 are returned, fix the check. Treat as P1 pending documentation review.

### Conflict 2 — Severity of manual trigger docstring vs. law (GPT-4o flagged as concern; Grok/Gemini did not)
- **GPT-4o position:** The docstring says "Called by cron or manual trigger" which conflicts with the law specifying cron-only scheduling.
- **Other models:** Did not flag this as a violation.
- **Tiebreaker:** A docstring alone is not a law violation if no actual manual trigger route exists in the exposed API surface. **Verdict: Minor — update the docstring to remove "or manual trigger" for clarity, but this is not a blocking issue.**

### Conflict 3 — Whether the UI handles the `generating` state adequately (Grok flagged confusion; Gemini disagreed)
- **Grok position:** UI doesn't clarify if a briefing is generating.
- **Gemini position:** Explicitly disagreed — `market_briefing.html:571–572` checks for `generating` status and displays an appropriate message.
- **Tiebreaker:** **Gemini is correct.** The template does handle the generating state display. However, the 30-second hard reload (`market_briefing.html:841–845`) is a separate UX concern worth addressing. Grok's concern about the generating state UX is resolved by existing code; the hard reload behavior is the actual issue.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **Sarah avatar configuration** — `briefing_service.py:25`, `briefing_service.py:195`: Correct `SARAH_AVATAR_ID` used exclusively. Resolution hardcoded to 1280×720. No Wav2Lip or other avatar bleed. Law 1 is fully satisfied at the service layer. Do not touch.

2. **APScheduler cron schedule** — `cron/briefing_cron.py:66–93`: All three briefing times (07:00, 09:30, 16:30 ET) are correctly registered with Eastern timezone. Law 2 schedule is correctly implemented. Do not touch the schedule definition itself.

3. **HeyGen retry logic** — `briefing_service.py:334–343`: Max 2 retries enforced as required by Law 2. Loop logic is correct. Do not change retry count.

4. **Error isolation in cron runner** — `cron/briefing_cron.py:40–60`: try/except wrapping prevents cron crashes from propagating and killing the scheduler. Pattern is sound.

5. **Script sanitization (em-dash, en-dash, ellipsis removal)** — `briefing_service.py:166–168`: Post-generation cleanup of forbidden characters is correctly applied. Do not remove this step.

6. **Recent briefings loop in template** — `market_briefing.html:656–695`: The template correctly loops through recent briefings and handles the empty state. The display structure is solid; only the `loadBriefing()` JS function needs fixing, not the card rendering.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|-----|--------|---------|
| **LAW 1** — HeyGen Sarah is the ONLY avatar | ✅ **COMPLIANT** | Correct avatar ID and resolution enforced at service level. No other avatar used. |
| **LAW 2** — Three briefings per day, fixed schedule, max 2 retries | ✅ **COMPLIANT** | Cron schedule correct. Retry cap at 2 enforced. |
| **LAW 3** — Always show last 3 briefings | ⚠️ **PARTIAL** | Template structure is correct, but backend query for `recent` briefings was not provided for full verification. Cannot confirm compliance without seeing the route/query. |
| **LAW 4** — (Not shown; inferred) | ⚠️ **UNVERIFIED** | Backend query not in scope of provided code. |
| **LAW 5** — Script inputs: live BTC price, latest articles, mempool stats, network data | ❌ **VIOLATED** | Only BTC price and article headlines are fetched. Mempool stats and network data are absent from `_generate_script()`. `asia_data` is a hardcoded placeholder. |

**LAW 5 is the only confirmed law violation.** Mempool and network data inputs must be implemented or the gospel must be updated to reflect what data is actually sourced.

---

## SECURITY CONSENSUS

All models rated security in the 7.2–8.0 range. No critical vulnerabilities were identified. Issues in priority order:

1. **Freeform script text in HTML data attributes** (GPT-4o, Unique-1): Embedding Claude-generated text in HTML attributes without strict escaping is an XSS vector if autoescaping is ever disabled or bypassed. Priority: Medium. Fix by moving to JSON blocks or API fetch.

2. **Cost guard race condition** (Grok + GPT-4o): While not a security vulnerability per se, a race condition that bypasses spend limits is a financial security risk. Priority: High (see M4).

3. **No rate limiting on any manual invocation path**: If a manual trigger route is ever exposed (even internally), no rate limiting exists. Priority: Low — monitor if manual routes are added.

4. **API keys/secrets management**: Not visible in provided code. Assumed to be handled via environment variables. No action required based on available evidence.

---

## WORLD-CLASS GAP CONSENSUS

Issues 2+ models identified as missing from a truly world-class product:

1. **Real-time generation status via WebSocket or SSE instead of 30-second hard reload** (Gemini P2.3, GPT-4o implied, Grok implied via UX concern): A polling page reload is a poor substitute for push-based status updates. A world-class briefing room would use WebSocket or Server-Sent Events to stream generation progress and push the completed video to the client without a jarring full-page reload.

2. **Text-only fallback when video generation fails** (Grok + Gemini): If HeyGen fails after script generation succeeds, users get nothing. A world-class product surfaces the script text as a fallback briefing, ensuring users always receive value from the scheduled slot even if the video pipeline degrades.

3. **Real data pipeline for all script inputs** (GPT-4o + Grok + Gemini on `asia_data`): Hardcoded placeholders signal an incomplete implementation. A world-class intelligence briefing requires live, structured data for every input the prompt claims to use — Asian market data, mempool stats, network congestion metrics — not static strings.

4. **Idempotent, observable generation pipeline** (GPT-4o + Gemini): A world-class scheduled system has audit logs per run, deduplication guarantees, and an operations dashboard showing the status of every scheduled slot. The current system has no visibility into which slots succeeded, failed, or were skipped.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0** | Add idempotency check: query for existing non-failed briefing by `(briefing_type, ET_date)` before inserting; add unique DB constraint | `briefing_service.py:294–315` | GPT-4o + Gemini | Prevents duplicate renders, wasted API spend, and DB clutter under any double-fire condition |
| **P0** | Fix video swap: update timestamp, BTC price, duration, poster, script panel in `loadBriefing()` — prefer fetch-by-ID over data attributes | `market_briefing.html:786–838` | All 3 | Core feature is functionally broken for historical playback |
| **P0** | Fix cost guard to include `'failed'` in status filter | `briefing_service.py:254` | GPT-4o + Gemini | Failed attempts that consumed paid API calls are not counted; budget overruns possible |
| **P0** | Eliminate multi-commit pipeline: single final commit on success, rollback on any exception | `briefing_service.py:294–403` | GPT-4o + Gemini | Mid-pipeline failures create orphan rows permanently stuck in `generating` |
| **P0** | Atomize cost guard + insert: use DB unique constraint or `SELECT FOR UPDATE` to prevent race condition | `briefing_service.py:243–289` | Grok + GPT-4o | Two concurrent processes can both pass the guard before either commits |
| **P1** | Fix countdown timer: backend provides UTC epoch of next briefing; JS computes delta from `Date.now()` | `market_briefing.html:714–718` | All 3 | `toLocaleString → new Date()` is broken across browsers and locales |
| **P1** | Fix UTC→ET timezone: store or convert `generated_at` to ET-aware datetime; remove hardcoded "ET" label on UTC value | `market_briefing.html:600, 683` + `briefing_service.py` | GPT-4o + Grok | Timestamps shown are factually wrong by 4–5 hours |
| **P1** | Move `data-script` out of HTML attribute: use `<script type="application/json">` or fetch by ID on click; remove truncation | `market_briefing.html:659–663` | GPT-4o (+ confirmed by U1 fix scope) | Freeform text in attributes breaks HTML; truncation means full script never shown |
| **P1** | Add `max_instances=1, coalesce=True` to all three APScheduler job registrations | `cron/briefing_cron.py:66–93` | GPT-4o | Trivial hardening that prevents scheduler-level job stacking |
| **P1** | Add post-generation word count check on Claude response; warn and truncate if >180 words | `briefing_service.py:166–172` | Grok | Prompt constraint is not enforced; overlength scripts cause overlong videos |
| **P1** | Investigate HeyGen `POST /v2/video/generate` success codes; accept 200/201/202 if documented | `briefing_service.py:205–211` | GPT-4o | False failure if HeyGen returns 201/202 for accepted async jobs |
| **P1** | Unify HeyGen API version: use `/v2/` for status polling or confirm cross-version pairing is documented | `briefing_service.py:200, 220` | GPT-4o + Gemini | Mixed v1/v2 API usage is fragile under third-party API evolution |
| **P2** | Replace hardcoded `asia_data` placeholder with real data feed or remove from prompt | `briefing_service.py:155` | Gemini + GPT-4o | Pre-market briefing claims to cover Asian markets but always says the same static string |
| **P

---

# WINNER DETERMINATION

WINNER: **GPT-4o** — Across both cycles, GPT-4o consistently identified the most technically precise and actionable backend issues (idempotency failure, HeyGen 201/202 status code assumption, UTC-labeled-as-ET display bug, unused `asia_data` prompt wiring) with exact file/line citations and clear implementation paths, and its Cycle 2 self-correction was honest and structured rather than defensive. While Gemini caught overlapping issues and added the database multi-commit transaction flaw, GPT-4o's findings proved most broadly verified by the consensus and scored highest on correctness and backend quality where it mattered most for ship-blocking decisions.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × blast radius. Implement in this sequence.

---

### P0 — SHIP BLOCKERS (must fix before merge)

**P0-1 — No idempotency check in `generate_briefing()`**
- **File:** `core/services/briefing_service.py:294–315`
- **Risk:** Duplicate briefings created per slot if cron misfires, container restarts, or manual trigger races the scheduler. Wastes real API credits (Claude + HeyGen) and corrupts the "last 3 briefings" display.
- **Fix:** Before inserting a new row, query for an existing briefing with `(slot, date, status IN ['generating','completed'])`. If found, return early with a log entry. Use a DB-level unique constraint on `(slot_name, scheduled_date)` as a hard backstop.

**P0-2 — Multi-step `db.session.commit()` leaves DB in inconsistent state on failure**
- **File:** `core/services/briefing_service.py` (multiple intermediate commits)
- **Risk:** If HeyGen polling fails after the Claude step commits, the row is partially written with no rollback path. Briefing appears in UI with corrupted state.
- **Fix:** Remove all intermediate commits. Accumulate all state changes on the ORM object in memory. Issue exactly one `db.session.commit()` on full success. Wrap the entire function body in a `try/except` with `db.session.rollback()` on any exception.

**P0-3 — Cost guard does not count `failed` status rows**
- **File:** `core/services/briefing_service.py:254`
- **Risk:** Expensive upstream calls (Claude token spend) occur before a downstream step fails. Those failed rows are invisible to the guard. Under persistent failure conditions, budget overruns silently.
- **Fix:** Add `'failed'` to the status filter in `_check_cost_guard`. Consider also tracking estimated spend per attempt rather than attempt count alone.

**P0-4 — HeyGen generation only accepts HTTP 200; async APIs return 201/202**
- **File:** `core/services/briefing_service.py:205–211`
- **Risk:** HeyGen returning 201 (Accepted) causes the code to mark generation as failed immediately, burning the API call with no video produced.
- **Fix:** Change the success condition to `response.status_code in (200, 201, 202)`. Log the actual status code at DEBUG level for future traceability.

**P0-5 — HeyGen API version mismatch (`/v2/` generate, `/v1/` status poll)**
- **File:** `core/services/briefing_service.py:219–223`
- **Risk:** Cross-version polling relies on undocumented compatibility. A HeyGen API update could silently break status resolution with no error surface.
- **Fix:** Align both endpoints to the same API version. Confirm against current HeyGen documentation and pin the version string to a single constant at the top of the file.

---

### P1 — HIGH PRIORITY (fix in same sprint)

**P1-1 — Video swap does not update metadata or script panel (Unanimous U1)**
- **File:** `core/templates/market_briefing.html:786–838`
- **Fix:** Extend `loadBriefing()` to fetch the full briefing object by ID via a lightweight JSON endpoint (`/api/briefing/<id>`). Update `#featuredTimestamp`, `#featuredBTCPrice`, `#featuredDuration`, `#scriptPanelText`, poster attribute, and any other bound fields atomically after fetch resolves.

**P1-2 — Countdown timer uses `toLocaleString → new Date()` anti-pattern (Unanimous U2)**
- **File:** `core/templates/market_briefing.html:714–718`
- **Fix:** Replace with a library that correctly handles IANA timezone arithmetic (e.g., `Intl.DateTimeFormat` with explicit UTC offset calculation, or Luxon/Day.js with timezone plugin). Compute next slot time in UTC server-side and pass it as a UTC ISO-8601 timestamp to the template; client-side timer counts down from that fixed point.

**P1-3 — `generated_at` displayed with hardcoded `ET` label but no timezone conversion**
- **File:** `core/templates/market_briefing.html` (timestamp display block)
- **Risk:** If `generated_at` is stored as UTC-naive, the UI is factually wrong for all users outside ET and misleading for ET users during DST transitions.
- **Fix:** Store timezone-aware datetimes (UTC) in the DB. Convert to ET explicitly in the template using `pytz` or `zoneinfo` before rendering, or pass an ISO-8601 string to JS and format client-side with correct IANA zone.

**P1-4 — LAW 5 data inputs incomplete — mempool stats and network data missing**
- **File:** `core/services/briefing_service.py:147–171`
- **Risk:** The feature's stated intelligence value depends on live network data. Shipping without it makes the briefing materially weaker than the law requires.
- **Fix:** Add fetch calls for mempool stats (e.g., mempool.space API) and relevant network metrics before the Claude prompt is assembled. Pass them as named variables in the prompt template alongside BTC price and headlines.

**P1-5 — `asia_data` passed to `.format()` but no prompt template placeholder consumes it**
- **File:** `core/services/briefing_service.py:152–156`
- **Risk:** Dead variable signals unfinished prompt work. The pre-market briefing silently omits Asian market context.
- **Fix:** Either add `{asia_data}` to the prompt template in the correct position, or remove the variable and fetch/inject real Asian market data as part of P1-4 above. Do not leave dead `.format()` arguments in production code.

---

### P2 — MEDIUM PRIORITY (fix within 2 sprints)

**P2-1 — BTC price fallback to `0.0` is semantically misleading**
- **File:** `core/services/briefing_service.py:102–123`
- **Fix:** Change fallback to `None`. In the prompt template, render `None` as the string `"unavailable"`. Add a warning-level log entry when both price APIs fail so ops is alerted.

**P2-2 — No cross-run persistent failure alerting for cron jobs**
- **File:** `cron/briefing_cron.py:43–59`
- **Fix:** Add a failure counter (Redis key or DB column) incremented on each failed run. If the counter exceeds 2 consecutive failures for the same slot, emit a structured alert (Slack webhook, PagerDuty, or email). Reset counter on success.

**P2-3 — No fallback output when Claude or HeyGen fails**
- **File:** `core/services/briefing_service.py:171, 240`
- **Fix:** On Claude failure, consider storing the raw data fetch as a text-only fallback briefing record. On HeyGen timeout, mark status `text_only` and surface the script in the UI rather than showing nothing. This is a UX resilience improvement, not a correctness fix.

**P2-4 — Concurrent cost guard bypass under race conditions**
- **File:** `core/services/briefing_service.py:243–266`
- **Fix:** Wrap the cost guard check and new-row insert in a `SELECT FOR UPDATE` or use a DB-level advisory lock to prevent two concurrent callers from both passing the guard before