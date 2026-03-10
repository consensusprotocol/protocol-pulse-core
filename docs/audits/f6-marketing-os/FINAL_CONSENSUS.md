# CONSENSUS REPORT — F6-MARKETING-OS — CYCLE 2
Generated: 2026-03-09 02:42
Models: gpt4o, gemini, grok

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Correctness     | 1/10   | 1/10   | 1/10 | **1/10**  |
| Law Compliance  | 0/10   | 0/10   | 0/10 | **0/10**  |
| Security        | 1/10   | 3/10   | 2/10 | **2/10**  |
| Frontend Quality| 1/10   | 1/10   | 1/10 | **1/10**  |
| Backend Quality | 1/10   | 2/10   | 1/10 | **1/10**  |
| **Overall**     | **1/10** | **1/10** | **1/10** | **1/10** |

> **Scoring note:** Security variance (Gemini 1, GPT-4o 3, Grok 2) reflects differing weights assigned to the dangerous build command vs. the XSS vulnerability. Consensus settles at 2/10 — both issues are real but the score is bounded by the total absence of the feature being audited.

---

## UNANIMOUS FINDINGS
*All 3 models agree — implement unconditionally.*

### U1 — The F6 Feature Does Not Exist
- **What:** No implementation files were submitted. The diff contains only GOSPEL documentation, audit tooling, launcher scripts, app bootstrap, logs, and unrelated frontend JS. Zero lines of actual F6 code exist.
- **Missing entirely:**
  - `services/milestone_service.py`
  - Model/migration for `milestone_fired`
  - Model/migration for `performance_metrics`
  - `/api/launch-gate` route
  - Cron integration for 5-minute milestone checks
  - Homepage banner tied to milestone state
  - Weekly performance analysis cron
  - All 5 milestone trigger actions (Pulse Check, Nostr post, newsletter, banner, Oracle)
- **Files:** All of the above — none exist
- **What to change:** Write the full implementation as specified in `GOSPEL.md:73-113`
- **Impact:** Total product failure for this feature. Nothing ships.

### U2 — Hardcoded Flask Session Secret Fallback
- **What:** `app.py:45-46` falls back to a hardcoded string if `SESSION_SECRET` env var is missing. A predictable session signing key enables session forgery and auth compromise.
- **File:** `app.py:45-46`
- **What to change:** Remove the fallback entirely. Application must call `sys.exit(1)` or raise a fatal error at startup if `SESSION_SECRET` is absent.
- **Impact:** Session hijacking / authentication bypass in production.

### U3 — All Four GOSPEL Laws Are Violated
- **What:** Because no implementation exists (U1), all four laws are simultaneously violated:
  - LAW 1: No `/api/launch-gate` endpoint → 9-item gate unchecked
  - LAW 2: No `MilestoneService` → fire-once logic absent
  - LAW 3: No trigger actions implemented
  - LAW 4: No `milestone_fired` or `performance_metrics` tables
- **Files:** All missing implementation files
- **What to change:** Implement all four laws as part of U1 implementation
- **Impact:** Complete spec failure. The feature cannot be considered even partially compliant.

### U4 — Frontend Canvas Violates Stack Constraint
- **What:** `media_reforge/static/js/media_unified.js` uses `<canvas>` for sparklines and gauge rendering. The stack spec explicitly states "NO Canvas / NO Three.js / NO WebGL." This is a direct architectural violation even though the JS file is nominally unrelated to F6.
- **File:** `media_reforge/static/js/media_unified.js:169-199, 760-806`
- **What to change:** Replace all Canvas-based rendering with pure CSS animations or SVG
- **Impact:** Architectural non-compliance; blocks merge under current stack rules.

### U5 — External Fetches Lack Timeout / Abort
- **What:** Every `fetch()` call in `media_unified.js` is bare with no `AbortController`, no timeout, no retry, and no fallback. Under network degradation, UI hangs indefinitely in loading/partial states.
- **File:** `media_reforge/static/js/media_unified.js:220-297, 299-318, 365-379, 609-623, 744-758`
- **What to change:** Wrap all external fetches with `AbortController` + timeout (e.g., 10s), add retry with exponential backoff, render a graceful error state on exhaustion.
- **Impact:** Silently broken UI under any real-world network degradation.

---

## MAJORITY FINDINGS
*2 of 3 models agree — implement unless compelling reason exists.*

### M1 — Stored XSS in `inject_ads` Template Filter
- **Models:** Gemini + GPT-4o (Grok did not separately call this out)
- **What:** `app.py:175-183` (approx.) builds an HTML string via f-string interpolation of database-backed fields (`ad.image_url`, `ad.name`) without sanitization. If ad content is compromised or user-controllable, this is a classic stored XSS vector.
- **File:** `app.py:167-190`
- **What to change:** Use `markupsafe.escape()` on all interpolated values, or build the HTML fragment using a DOM-safe templating approach (Jinja2 macro rather than a Python filter). Never build raw HTML from DB fields via string concatenation.
- **Impact:** Stored XSS — attacker-controlled ad record executes arbitrary JS in all visitor browsers.

### M2 — Dangerous `--dangerously-skip-permissions` in Build Launcher
- **Models:** Gemini + GPT-4o (Grok noted unsafe launcher practices generally)
- **What:** `launch_all_features.sh:81` invokes `claude --dangerously-skip-permissions` in an automated script. This explicitly bypasses the AI agent's safety controls in a pipeline that runs unattended. The likely reason is that the agent encounters errors it cannot solve and is configured to ignore them — which is precisely why the F6 build produced no artifacts.
- **File:** `launch_all_features.sh:81`
- **What to change:** Remove the flag entirely. If the agent requires this flag to complete a task, the task definition or environment is broken and must be fixed — not bypassed. Add a pipeline step that validates required output artifacts exist before marking a build successful.
- **Impact:** Critical build pipeline security risk; root cause of the empty F6 build.

### M3 — Nostr WebSocket Infinite Reconnection Loop
- **Models:** Gemini + GPT-4o (Grok noted "flapping" without identifying the exact mechanism)
- **What:** In `NostrFeed.prototype.connect`, the `onerror` handler calls `ws.close()`, which triggers the `onclose` handler's reconnection timer. On a persistent error (bad relay URL, network block), this creates an unbounded reconnection loop. The backoff reduces frequency but does not prevent infinite retries on unrecoverable errors.
- **File:** `media_reforge/static/js/media_unified.js:395-430`
- **What to change:** Implement a circuit breaker: classify errors as transient vs. permanent, cap total retry attempts (e.g., 5), and on permanent failure mark that relay as dead and stop retrying it. Do not call `ws.close()` inside `onerror` — let the browser handle closure and only reconnect from `onclose`.
- **Impact:** Client-side DoS / misleading relay health state under persistent errors.

### M4 — Runtime `db.create_all()` Instead of Migrations
- **Models:** GPT-4o + Gemini
- **What:** `app.py:238-247` uses `db.create_all()` at startup, wrapped in a `try/except` that only logs a warning on failure. This means (a) the app starts even if schema is incomplete, (b) schema drift between environments is invisible, and (c) the missing F6 tables would be silently absent.
- **File:** `app.py:238-247`
- **What to change:** Replace with proper Alembic migrations. The startup `db.create_all()` block should be removed. If any migration fails, the app must not start (`sys.exit(1)`).
- **Impact:** Schema drift across environments; silent runtime failures when F6 tables are accessed.

### M5 — Broken Timestamp Updater (`data-ts` Never Set)
- **Models:** GPT-4o + Grok
- **What:** `initTimeUpdater()` queries for `.intel-card-time` elements with `data-ts` attributes to refresh relative timestamps. However, `renderNote()` and `renderCard()` never set `data-ts` on those elements. The time updater silently does nothing on every tick.
- **File:** `media_reforge/static/js/media_unified.js:1173-1179` vs `:556, :721`
- **What to change:** Add `data-ts="${note.created_at}"` (or equivalent) to the rendered element in both `renderNote()` and `renderCard()`.
- **Impact:** All displayed timestamps are static and never update — broken UX that appears superficially correct.

### M6 — Unquoted Shell Variables in Launcher Script
- **Models:** GPT-4o + Grok
- **What:** Variables throughout `launch_all_features.sh` are used unquoted, creating word-splitting and glob-expansion vulnerabilities. Paths with spaces or special characters will break the script or execute unintended commands.
- **File:** `launch_all_features.sh` (multiple lines)
- **What to change:** Quote all variable expansions: `"$VAR"` not `$VAR`. Use `set -euo pipefail` at the top of the script to fail fast on errors.
- **Impact:** Silent build failures or unintended command execution on paths with spaces.

---

## UNIQUE INSIGHTS
*Single-model observations — evaluated individually.*

### X1 — Audit Pipeline References Non-Existent File (GPT-4o)
- **What:** `launch_all_features.sh:11,64` sets `AUDIT_ENGINE=$BASE_DIR/utils/cross_llm_audit.py` and invokes it. The provided file tree shows audit scripts at `docs/audits/run_mu_audit.py` and `docs/intel/run_multi_llm_audit.py` — not at `utils/cross_llm_audit.py`. If this file does not exist, the entire automated post-build audit pipeline silently fails.
- **Assessment:** **Investigate immediately.** If confirmed missing, the claimed multi-model audit step has never actually run. This would mean the entire audit loop is theater — the build completes, the audit invocation exits non-zero, and the pipeline marks success anyway (likely because the `--dangerously-skip-permissions` flag masks the failure). Fix: verify the path, add `|| exit 1` after the invocation, and add an artifact existence check.

### X2 — Systemic Process Failure: AI Agent Producing Empty Builds (Gemini)
- **What:** Gemini identified a meta-finding: the `launch_all_features.sh` process is designed to automate feature builds from GOSPEL files. That this process "completed" for F6 yet produced no implementation artifacts is evidence that the development loop itself is broken — not just this feature. The `--dangerously-skip-permissions` flag (M2) strongly suggests the agent encountered unresolvable errors and silently plowed ahead, producing an empty build that then passed into audit.
- **Assessment:** **Implement — this is the most important systemic finding.** Add mandatory artifact validation to the build pipeline: after the AI agent step, a validation script must assert the existence of all required files (enumerated in the GOSPEL) before the build is considered successful. A build that produces no implementation files must fail loudly. This prevents future features from entering the audit cycle as empty shells.

### X3 — 5-Minute Cron Interval May Hit API Rate Limits (Grok)
- **What:** The GOSPEL specifies BTC price checks every 5 minutes. Depending on the price feed API, this could exhaust rate limits, especially if multiple environments (dev, staging, prod) run simultaneously.
- **Assessment:** **Investigate before implementation.** Confirm the chosen price API's rate limits. If the API allows polling at 5-minute intervals without issue, proceed. If not, consider a WebSocket price feed subscription instead of polling, or implement request caching with a TTL slightly below 5 minutes. Do not implement the cron without confirming this.

### X4 — `/api/launch-gate` Lacks Fallback Strategy in GOSPEL (Grok)
- **What:** The GOSPEL specifies the launch gate endpoint but does not define behavior if the gate status cannot be retrieved (DB down, timeout). Without a specified fallback, the implementation might default to "gate open" (dangerous) or "gate closed" (campaigns never fire).
- **Assessment:** **Implement defensive default during feature build.** The correct safe default is "gate closed" — if gate status cannot be confirmed, no campaigns fire. Document this explicitly in the implementation and add a health alert if the gate endpoint is unreachable for >15 minutes.

### X5 — Public Cache Default for All `/api/` Routes (GPT-4o)
- **What:** `app.py:153-157` sets `Cache-Control: public, max-age=60` as a default for all `/api/` responses. Any authenticated or user-specific API route that does not explicitly override this header will serve cached responses that may leak user data or serve stale content.
- **Assessment:** **Implement.** Change the default to `Cache-Control: no-store` for all `/api/` routes. Individual routes that are genuinely public and cacheable can explicitly opt in to caching. Fail-safe defaults matter for security.

### X6 — `load_dotenv` May Load Repo-Local `.env` in Production (GPT-4o)
- **What:** `app.py:5` loads `.env` from the app directory. Combined with the hardcoded secret fallback (U2) and permissive startup, this increases the chance of accidentally running production with development secrets if a `.env` file is present in a cloned repo.
- **Assessment:** **Investigate.** Ensure `.env` is in `.gitignore` (confirm this is the case) and add a startup check that warns loudly if running in production mode with a file-based `.env`. In production, all secrets should come from environment variables set by the deployment platform, not from a file.

---

## CONFLICTS
*Where models disagreed — tiebreaker ruling.*

### C1 — Partial Credit for GOSPEL Pseudocode (Grok vs. Gemini/GPT-4o)
- **Conflict:** Grok gave partial Law compliance credit for the `already_fired` logic and milestone list documented in `GOSPEL.md:78-83`. Gemini and GPT-4o held that documentation is not code and no compliance credit is warranted.
- **Ruling: Gemini/GPT-4o are correct.** The audit protocol explicitly states "Never audit specs." GOSPEL pseudocode is a specification, not an implementation. Compliance is measured against running code. A well-written spec with zero implementation is a 0/10 for law compliance, not a partial score. Grok's leniency here was the only meaningful scoring divergence and it is overruled.

### C2 — Security Score Variance (Gemini 1/10 vs. GPT-4o 3/10 vs. Grok 2/10)
- **Conflict:** Models scored security between 1 and 3, with Gemini most severe (weighting the dangerous build command heavily) and GPT-4o most lenient.
- **Ruling:** Consensus at **2/10**. Both the stored XSS (M1) and the dangerous build flag (M2) are legitimate P0 security issues. The hardcoded secret (U2) is a third. Three concurrent critical security issues in a feature that doesn't even exist yet justifies a score near the bottom. Gemini's 1/10 is defensible but slightly harsh given that none of the issues are in the F6 code itself (which doesn't exist). GPT-4o's 3/10 is too generous given the severity and number of issues.

---

## VALIDATED STRENGTHS
*All models confirmed these are already good — do NOT change.*

> **None.** There is no aspect of the F6 feature implementation that all three models agreed is excellent, because no F6 implementation exists to evaluate. The models found no area of the submitted code worth preserving without change relative to the F6 feature. The app bootstrap and launcher architecture have some reasonable structure, but all three models identified issues in both.
>
> **Constraint for second pass:** Do not refactor the GOSPEL documentation itself — it is the correct specification and should be treated as the source of truth for implementation.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Reason |
|-----|--------|--------|
| LAW 1: Launch gate — 9 items must ALL be ✓ before milestone campaigns fire | **VIOLATED** | `/api/launch-gate` endpoint does not exist. No gate check of any kind is implemented. |
| LAW 2: Price milestone triggers fire ONCE per milestone, never repeat | **VIOLATED** | `MilestoneService` does not exist. `milestone_fired` table does not exist. No deduplication logic exists. |
| LAW 3: What each milestone trigger fires (5 required actions) | **VIOLATED** | None of the 5 actions (Pulse Check, Nostr post, newsletter, banner, Oracle update) are implemented. |
| LAW 4: Performance metrics schema | **VIOLATED** | `performance_metrics` table/model does not exist. No migration exists. |

**Final determination: 0/4 laws compliant. Feature is in total violation of all laws. Merge is blocked.**

---

## SECURITY CONSENSUS

Issues flagged by 2+ models, in priority order:

| Priority | Issue | Models | File |
|----------|-------|--------|------|
| P0 | Hardcoded Flask session secret fallback | All 3 | `app.py:45-46` |
| P0 | Dangerous `--dangerously-skip-permissions` build flag | Gemini + GPT-4o | `launch_all_features.sh:81` |
| P0 | Stored XSS in `inject_ads` via unsanitized DB fields | Gemini + GPT-4o | `app.py:167-190` |
| P1 | Public cache default on all `/api/` routes | GPT-4o (unique, but high confidence) | `app.py:153-157` |
| P1 | Silent DB startup failure allows running with missing schema | Gemini + GPT-4o | `app.py:238-247` |
| P1 | `load_user` `int()` cast can throw on malformed session | GPT-4o (unique, credible) | `app.py:223-225` |

---

## WORLD-CLASS GAP CONSENSUS
*What 3 AI models collectively identify as missing from a truly world-class product.*

### WC1 — The Core Feature (all 3 models)
A world-class marketing automation system has a working implementation. Protocol Pulse's F6 is entirely absent. A world-class version would include: atomic milestone deduplication using database-level unique constraints (not just application-level checks), idempotent trigger actions with retry queues, observable campaign state visible to operators, and rollback capability if a milestone fires erroneously.

### WC2 — Production-Grade Build Pipeline Validation (Gemini + GPT-4o)
A world-class AI-assisted development pipeline validates its own outputs. After an AI agent build step, the pipeline must assert the existence and basic validity of all required artifacts before declaring success. The current pipeline can produce empty builds that enter the audit cycle undetected — this is a fundamental reliability failure.

### WC3 — Circuit Breakers and Fault Tolerance Throughout (GPT-4o + Gemini)
Every external integration (BTC price API, Nostr relays, newsletter provider, Nostr post delivery) needs circuit breakers, timeouts, and fallback behavior. A world-class system degrades gracefully — if the price feed is down, the milestone checker logs the failure and retries; it does not silently skip or crash. The current codebase has none of this.

### WC4 — Observability and Alerting for Milestone Campaigns (Grok + GPT-4o)
A world-class milestone system produces observable, auditable records of every campaign trigger decision: why a milestone fired, what actions were taken, which succeeded, which failed, and what retry state each action is in. Currently there is no logging, no metrics, and no alerting defined anywhere in the spec or implementation.

---

## FINAL ACTION PLAN

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|--------|-----------|--------|-----|
| P0-1 | Implement entire F6 Marketing OS feature per GOSPEL | All missing files | All 3 | Feature does not exist. Zero lines of F6 code submitted. Total product failure. |
| P0-2 | Remove hardcoded session secret fallback; fail fast on missing `SESSION_SECRET` | `app.py:45-46` | All 3 | Session forgery / auth bypass. Predictable key enables forged sessions in production. |
| P0-3 | Implement all four GOSPEL laws (launch gate, fire-once, 5 trigger actions, metrics schema) | All missing files | All 3 | 0/4 laws compliant. Direct spec violation blocks all milestone campaign functionality. |
| P0-4 | Remove `--dangerously-skip-permissions` from launcher; add artifact existence validation | `launch_all_features.sh:81` | Gemini + GPT-4o | Root cause of empty F6 build. Security risk in automated pipeline. |
| P0-5 | Fix stored XSS in `inject_ads` — escape all DB-backed fields before HTML injection | `app.py:167-190` | Gemini + GPT-4o | Stored XSS executes attacker-controlled JS in all visitor browsers. |
| P0-6 | Replace Canvas rendering with CSS/SVG per stack constraint | `media_unified.js:169-199, 760-806` | All 3 | Direct violation of explicit stack constraint. Architectural non-compliance blocks merge. |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|--------|-----------|--------|-----|
| P1-1 | Replace `db.create_all()` with Alembic migrations; fail startup on migration error | `app.py:238-247` | GPT-4o + Gemini | Silent schema failures. App runs without F6 tables, causing runtime errors. |
| P1-2 | Implement circuit breaker for Nostr WebSocket reconnection; cap retries; classify permanent vs transient errors | `media_unified.js:395-430` | Gemini + GPT-4o | Unbounded reconnect loop on persistent errors. Client-side resource exhaustion. |
| P1-3 | Add `AbortController` + timeout to all external `fetch()` calls | `media_unified.js:220-297, 299-318, 365-379, 609-623, 744-758` | All 3 | Bare fetches hang indefinitely under network degradation, leaving UI broken. |
| P1-4 | Fix `data-ts` never being set in `renderNote()` and `renderCard()` | `media_unified.js:556, 721` vs `:1173-1179` | GPT-4o + Grok | Timestamp updater silently does nothing. All displayed timestamps are permanently static. |
| P1-5 | Change default `/api/` cache policy from `public, max-age=60` to `no-store` | `app.py:153-157` | GPT-4o (unique — high confidence) | Unsafe default risks caching user-specific or sensitive API responses publicly. |
| P1-6 | Harden `load_user` against malformed session data with try/except on `int()` cast | `app.py:223-225` | GPT-4o (unique — credible) | Unhandled exception on bad session cookie causes 500 errors

---

# WINNER DETERMINATION

## WINNER: GPT-4o

GPT-4o delivered the highest-quality analysis across both cycles. In Cycle 1, it was the most precise and actionable: it correctly identified the feature's total absence without hedging, immediately flagged the Canvas stack violation with exact line numbers, caught the broken timestamp updater mechanism, identified the unquoted shell variables, and flagged the malformed `load_user` path — all issues the other models missed or underweighted. In Cycle 2, GPT-4o demonstrated the strongest self-correction discipline, explicitly acknowledging where it had been too generous (crediting GOSPEL pseudocode as partial implementation) and confirming other models' findings with surgical precision rather than vague agreement.

**Why not Gemini:** Gemini was technically strong and found the XSS vulnerability and dangerous build command that others initially missed, earning it second place — but its Cycle 1 output was truncated and it failed to flag several frontend issues GPT-4o caught.

**Why not Grok:** Grok's Cycle 1 output treated pseudocode stubs as partial compliance, gave unwarranted partial credit, and its Cycle 2 self-assessment explicitly acknowledged it would have missed the Canvas violation and frontend issues. It was the least precise of the three.

---

## FINAL SECOND-PASS PRIORITY LIST

*Definitive ordered list — implement in this sequence. Priority determined by: blocking severity → security risk → architectural integrity → correctness → maintainability.*

---

### P0 — BLOCKING: Ship Nothing Until These Are Done

**P0-1 — Write the entire F6 implementation from scratch**
The feature does not exist. Before any other work proceeds, implement:
- `services/milestone_service.py` — full `MilestoneService` class with cron logic
- `milestone_fired` model + migration
- `performance_metrics` model + migration
- `/api/launch-gate` route returning all 9 gate statuses
- 5-minute cron for BTC price milestone detection
- All 5 trigger actions: Pulse Check episode generation, Nostr post, newsletter blast, homepage banner activation (48h TTL), Oracle context update
- Weekly performance analysis cron
- Idempotency guard on milestone firing (the `already_fired` check must be atomic — see P1-2)
- **File:** Create all files above per `GOSPEL.md:73-113`

**P0-2 — Remove hardcoded Flask session secret fallback**
A predictable signing key allows session forgery in production.
- `app.py:45-46`: Remove the fallback string entirely. If `SESSION_SECRET` is absent at startup, raise `RuntimeError` and abort. Do not default to anything.
- **File:** `app.py`

**P0-3 — Remove `--dangerously-skip-permissions` from build script**
This flag bypasses the AI agent's own safety mechanisms during automated CI execution. The blast radius is unbounded.
- `launch_all_features.sh:81`: Remove the flag entirely. If the underlying command requires it to function, that command must be redesigned before it runs in any automated context.
- **File:** `launch_all_features.sh`

---

### P1 — CRITICAL: Security and Data Integrity

**P1-1 — Fix stored XSS in `inject_ads` template filter**
Ad content from the `Advertisement` model is rendered into an f-string without sanitization, then injected as raw HTML.
- `app.py:175-183`: Sanitize all ad fields through `markupsafe.escape()` before interpolation, or switch to a template-based render that escapes by default. Never concatenate DB content into raw HTML strings.
- **File:** `app.py`

**P1-2 — Make milestone firing atomic to prevent race conditions**
The `already_fired` check and the subsequent write are two separate DB operations. Concurrent cron runs can both read `fired=False`, both proceed, and double-fire.
- In `milestone_service.py` (once written per P0-1): Wrap the check-and-insert in a single transaction with a database-level unique constraint on `(milestone_value)` in the `milestone_fired` table. Handle the unique constraint violation as a no-op, not an error.
- **File:** `services/milestone_service.py`, migration for `milestone_fired`

**P1-3 — Fix malformed `load_user` on bad session data**
`app.py:223-225`: If session data is malformed or contains a non-integer user ID, `load_user` will throw an unhandled exception rather than returning `None`, potentially leaking stack traces or causing 500s.
- Wrap the user ID cast in a try/except, return `None` on any failure.
- **File:** `app.py`

---

### P2 — ARCHITECTURAL: Stack Compliance and Core Correctness

**P2-1 — Remove all Canvas usage from frontend**
The technology stack explicitly prohibits Canvas. Two separate Canvas-based implementations exist.
- `media_unified.js:169-199`: Sparkline canvas — replace with SVG-based implementation
- `media_unified.js:760-806`: Gauge canvas — replace with CSS/SVG-based gauge
- **File:** `media_reforge/static/js/media_unified.js`

**P2-2 — Fix infinite reconnection loop in Nostr client**
`onerror` calls `ws.close()`, which triggers `onclose`, which schedules reconnection. On a persistent error (bad relay URL, network block), this loops infinitely and can DDOS the relay or saturate the client.
- `media_unified.js:386-427`: Add an error classification step in `onerror`. For unrecoverable errors (e.g., `CloseEvent.code` 4000–4999, or repeated failures within a threshold window), set a `permanentFailure` flag and do not reconnect. Log the failure state visibly.
- **File:** `media_reforge/static/js/media_unified.js`

**P2-3 — Fix broken timestamp updater**
`initTimeUpdater()` queries `.intel-card-time` elements for a `data-ts` attribute, but cards are rendered without that attribute, making the updater permanently inert.
- `media_unified.js:1173-1179` and `media_unified.js:556, 721`: Add `data-ts="${timestamp}"` to all card render sites, or switch `initTimeUpdater` to read from an alternative attribute that is actually written at render time.
- **File:** `media_reforge/static/js/media_unified.js`

---

### P3 — QUALITY: Maintainability and Operational Safety

**P3-1 — Externalize all hardcoded frontend configuration**
`NOSTR_RELAYS`, `POLL_INTERVALS`, and `SPACES_ACCOUNTS` are hardcoded in JS. Any environment change requires a code deploy.
- `media_unified.js:10, 18, 26`: Inject these values at page render time via a `<script>` block in the template that writes a `window.APP_CONFIG` object, populated from server-side environment variables. Read from `window.APP_CONFIG` in JS.
- **File:** `media_reforge/static/js/media_unified.js`, relevant Jinja templates

**P3-2 — Quote all shell variables in launcher scripts**
Unquoted variables in `launch_all_features.sh` will word-split on spaces and glob-expand on special characters, causing silent misbehavior on any non-trivial path or value.
- Audit every `$VAR` reference in the launcher and wrap in double quotes: `"$VAR"`.
- **File:** `launch_all_features.sh`

**P3-3 — Add error logging to DB calls in milestone service**
Once `milestone_service.py` exists (P0-1): any DB failure in the `already_fired` check must log explicitly. Silent failure here means a double-fire with no trace.
- Wrap all DB calls in try/except with structured logging. Do not silently swallow exceptions.
- **File:** `services/milestone_service.py`

---

*This feature must not merge. P0 items are gate conditions. P1 items must be resolved before any production deployment. P2 and P3 items must be resolved before the next sprint closes.*