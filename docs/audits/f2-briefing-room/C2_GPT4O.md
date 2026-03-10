## CYCLE 2 FINAL REVIEW — f2-briefing-room

## 1) What the other models caught that I missed

A few important things:

- **Featured-player swap bug is worse than just title/video drift**  
  I had noted UX confusion generally, but **Gemini/GPT-4o were right to call out the exact stale fields**: timestamp, duration, BTC-at-generation, script panel, and poster are not updated when selecting a previous briefing.

- **Countdown ET conversion is fragile**  
  I did not explicitly call out the `toLocaleString(...timeZone...) -> new Date(...)` anti-pattern. That is a real browser/locale correctness bug.

- **No idempotency / duplicate-slot protection**  
  GPT-4o correctly highlighted that `generate_briefing()` can create duplicate briefings for the same slot/day if cron fires twice or multiple scheduler processes exist.

- **UTC labeled as ET in template**  
  GPT-4o’s point is strong: the template formats `generated_at` with literal `ET` but no visible timezone conversion. If `generated_at` is UTC-naive or UTC-backed, the UI is factually wrong.

- **HeyGen success-code assumption may be too strict**  
  GPT-4o noted `_heygen_generate()` only accepts HTTP 200. For async APIs, 201/202 are common. That is a plausible integration bug.

- **`asia_data` is dead / unfinished prompt wiring**  
  Gemini and GPT-4o both caught that `asia_data` is passed into `.format(...)` but unused by the prompt templates.

- **Cost guard excludes failed attempts**  
  Gemini’s point is valid: if failures happen after paid upstream work, excluding `failed` rows undercounts spend pressure.

## 2) Where I agree or disagree

### Grok findings
- **Persistent failure notification missing** — **Agree**
  Logging alone is not enough for a scheduled production feature.
- **BTC fallback to `0.0` is misleading** — **Agree**
  Better to use `None` and render “unavailable” explicitly.
- **No fallback when Claude/HeyGen fails** — **Partially agree**
  Reliability concern, yes. But not necessarily a law violation. Text-only fallback would improve resilience.
- **Cost guard race condition** — **Agree**
  This is one of the biggest backend risks.
- **Frontend generating-state confusion** — **Partially agree**
  The empty state exists, but the UX is still weak during long generation windows.

### Gemini findings
- **Playback metadata/script not updated** — **Strongly agree**
  Definite bug.
- **Countdown timer unreliable** — **Strongly agree**
  Definite bug.
- **Cost guard should include failed** — **Agree**
  Not perfect accounting, but better than current logic.
- **Hardcoded placeholder `asia_data`** — **Agree**
  It signals incomplete implementation.
- **LAW 3 only partial because route query not shown** — **Agree**
  Template alone does not prove compliance.

### GPT-4o findings
- **Manual trigger wording conflicts with law** — **Partially agree**
  The docstring is loose, but not itself a shipping blocker unless a manual route exists.
- **No dedupe/idempotency** — **Strongly agree**
  P0/P1 depending on deployment topology.
- **LAW 5 missing mempool/network data inputs** — **Agree**
  If the gospel/spec explicitly requires those inputs, current implementation is incomplete.
- **Script sanitization incomplete** — **Agree**
  Prompt asks for constraints, but code does not verify them.
- **HeyGen 200-only success handling** — **Agree**
  Needs confirmation against API docs, but current code is brittle.
- **Mixed v2 generate + v1 status endpoint** — **Partially agree**
  Could be valid if HeyGen documents it. Risky, but not provably wrong from code alone.
- **`%-d` portability issue** — **Agree**
  Real portability issue.
- **UTC timestamps labeled ET** — **Strongly agree**
  Likely correctness bug.
- **`db.create_all()` at startup is dangerous** — **Agree**
  App-level concern, not specific to F2, but still valid.

## 3) New findings from this review

Here are issues I do **not** think were clearly surfaced in Cycle 1:

### N1 — Previous-briefing cards can break HTML/JS due to unescaped attribute payloads
**File:** `core/templates/market_briefing.html:659-663`

The template injects raw values into HTML attributes:

```html
data-title="{{ b.title }}"
data-script="{{ b.script_text | truncate(300) }}"
```

If `title` or `script_text` contains quotes, angle brackets, or line breaks, attribute parsing can break. Jinja autoescaping helps for HTML, but embedding long freeform script text into attributes is still brittle and can produce malformed DOM behavior. Better:
- use `|e`
- or store data in a `<script type="application/json">`
- or fetch full briefing payload by ID on click.

### N2 — Truncated script in `data-script` guarantees wrong script display even after JS fix
**File:** `core/templates/market_briefing.html:662`

Even if `loadBriefing()` is fixed to use `data-script`, the template currently stores only:
```html
data-script="{{ b.script_text | truncate(300) }}"
```
So the script panel would still show a shortened script, not the real one. If the requirement is to show the actual script, this is still wrong.

### N3 — `loadBriefing()` appends a new video element without clearing stale state in empty-player path
**File:** `core/templates/market_briefing.html:817-832`

If the page initially has no `featuredVideo`, clicking a previous card appends one. That works, but:
- no poster is set
- no metadata/script controls are synchronized
- repeated edge transitions between empty/latest states are not normalized

This is more of a state-management flaw than a separate bug, but it reinforces that the featured area should be rendered from a single source-of-truth object.

### N4 — Cost guard uses `generated_at` for in-flight limiting, which may be semantically wrong
**File:** `core/services/briefing_service.py:249-256`

The guard filters on `generated_at >= cutoff` and statuses `generating/completed`. If `generated_at` means row creation time, okay-ish. If it means actual completion/publication time, then in-flight rows may be miscounted or not counted as intended. The naming suggests ambiguity. A dedicated `created_at` / `started_at` would be safer for spend throttling.

### N5 — Cron jobs do not set `max_instances=1` or coalescing
**File:** `cron/briefing_cron.py:66-93`

Even before app-level dedupe, APScheduler can help reduce overlap:
- `max_instances=1`
- `coalesce=True`

Without these, delayed or overlapping runs can stack more easily.

## 4) Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---:|---:|---|
| Correctness | 6.5/10 | 5.5/10 | More concrete correctness bugs confirmed: stale featured metadata, timezone bug, duplicate generation risk, ET labeling issue, brittle HeyGen response handling. |
| Law Compliance | 7.5/10 | 6.5/10 | LAW 3 and LAW 4 remain unproven; LAW 5 may be incomplete if mempool/network inputs are required by spec. |
| Security | 7.5/10 | 7.2/10 | Still decent overall, but attribute embedding of freeform script text and possible trigger abuse/race conditions lower confidence slightly. |
| Frontend Quality | 7.0/10 | 5.8/10 | Visual quality is strong, but interactive correctness is materially broken. |
| Backend Quality | 8.0/10 | 6.8/10 | Scheduler/service structure is decent, but idempotency, cost-guard race, timezone handling, and API brittleness are significant. |
| Overall | 7.3/10 | 6.1/10 | The combined review shows this is less production-ready than it first appeared. |

## 5) Final priority list

### P0 CRITICAL

1. **Add idempotency / duplicate-slot protection for briefing generation**
   - **File:** `core/services/briefing_service.py:294-315`
   - Problem: duplicate rows/videos can be created for same slot/day under double cron fire, multi-process schedulers, or retries.
   - Fix: enforce unique slot key per ET date + briefing_type, or transactional lock before insert.

2. **Fix cost-guard race condition**
   - **File:** `core/services/briefing_service.py:243-266`, `273-289`
   - Problem: `_check_cost_guard()` and row creation are separate, non-atomic operations.
   - Fix: move guard + insert into one transaction/lock; ideally use DB-backed quota enforcement.

3. **Fix featured-player state sync when loading previous briefings**
   - **File:** `core/templates/market_briefing.html:659-663`, `786-838`
   - Problem: video swaps but metadata/script/poster stay stale.
   - Fix: pass full payload and update title, timestamp, duration, BTC price, script, poster, and active state together.

4. **Stop labeling UTC timestamps as ET unless actually converted**
   - **File:** `core/templates/market_briefing.html:600`, `683`
   - Problem: likely false timestamps in UI.
   - Fix: convert server-side to America/New_York before formatting, or render timezone-aware ISO and format client-side correctly.

### P1 HIGH

5. **Replace countdown timezone hack**
   - **File:** `core/templates/market_briefing.html:714-718`
   - Fix with backend-provided next-slot UTC timestamp or proper `Intl.DateTimeFormat(...).formatToParts()` logic.

6. **Harden HeyGen response handling**
   - **File:** `core/services/briefing_service.py:199-211`
   - Accept documented async success codes, validate payload shape, and log parsed error bodies.

7. **Count failed attempts in spend protection, or track spend stages explicitly**
   - **File:** `core/services/briefing_service.py:253-255`
   - Current logic underestimates cost pressure during persistent failures.

8. **Remove brittle `%-d` formatting**
   - **File:** `core/services/briefing_service.py:296`, template `600`, `683`
   - Use portable formatting or helper functions.

9. **Escape/remove freeform script text from HTML attributes**
   - **File:** `core/templates/market_briefing.html:661-663`
   - Use IDs + JSON payload/API fetch instead of embedding script text in attributes.

10. **Ensure LAW 3 in backend query, not just template**
    - **File:** route file not provided
    - Need explicit latest + previous 3 query semantics, excluding latest from recent.

11. **Verify and implement LAW 4 redirect**
    - **File:** route file not provided
    - `/stage` must 302 to `/briefing`, with test coverage.

12. **Add scheduler overlap protections**
    - **File:** `cron/briefing_cron.py:66-93`
    - Add `max_instances=1`, `coalesce=True`.

### P2 MEDIUM

13. **Enforce script output constraints post-generation**
    - **File:** `core/services/briefing_service.py:147-168`
    - Validate word count, strip markdown, normalize punctuation, maybe retry once within policy if invalid.

14. **Replace `0.0` BTC fallback with explicit unavailable state**
    - **File:** `core/services/briefing_service.py:123`, `151`
    - Avoid ambiguous “0” semantics.

15. **Remove dead `asia_data` plumbing or implement real market context**
    - **File:** `core/services/briefing_service.py:152-156`
    - Dead placeholder indicates incomplete prompt design.

16. **Add operational alerting for repeated cron failures**
    - **File:** `cron/briefing_cron.py:40-60`
    - Logging alone is weak for scheduled production media generation.

17. **Reconsider runtime `db.create_all()`**
    - **File:** `app.py:241-247`
    - Not an F2 blocker by itself, but risky in managed migration environments.

## 6) The single highest-leverage change

**Make briefing generation idempotent and transactionally guarded, so one scheduled slot can never create duplicate or over-budget runs.**

## 7) Production ready?

**No.**

### Conditions before I would call it production-ready:
1. **Implement DB-backed idempotency for each ET slot/day + briefing type.**
2. **Make cost guard atomic with creation/start of generation.**
3. **Fix the featured-player swap so all metadata/script/poster update correctly.**
4. **Correct timezone handling in both displayed timestamps and countdown logic.**
5. **Verify route compliance for LAW 3 and LAW 4 with actual route code and tests.**
6. **Harden HeyGen integration against non-200 async success responses and polling edge cases.**

Once those are done, this becomes a solid candidate for release. Right now it looks polished, but it still has too many correctness traps for a scheduled production feature.