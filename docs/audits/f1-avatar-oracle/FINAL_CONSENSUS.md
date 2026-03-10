# CONSENSUS REPORT — F1-AVATAR-ORACLE — CYCLE 2
Generated: 2026-03-09 02:43
Models: grok, gemini, gpt4o

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 2/10 | 2/10 | 2/10 | **2/10** |
| Law Compliance | 1/10 | 1/10 | 1/10 | **1/10** |
| Security | 3/10 | 3/10 | 3/10 | **3/10** |
| Frontend Quality | 3/10 | 2/10 | 3/10 | **2.5/10** |
| Backend Quality | 3/10 | 3/10 | 4/10 | **3/10** |
| **Overall** | **2.4/10** | **2.2/10** | **2.6/10** | **2.4/10** |

> **Note:** Grok's Cycle 2 output was anomalous — it opened by claiming it had no Cycle 1 output, then produced analysis nearly identical in structure to the consensus, suggesting it was partially synthesizing other models rather than reviewing independently. Its scores are included but weighted slightly lower in tiebreaker situations. Gemini and GPT-4o are treated as the primary independent sources.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Critical Omission: Core Feature Files Are Absent
- **What:** `oracle/avatar_server.py`, `oracle_routes.py`, and `oracle/templates/oracle.html` — the three files that constitute the actual `f1-avatar-oracle` feature — were not submitted for audit. `app.py:282-283` registers `oracle_bp`, confirming the files exist somewhere but were excluded.
- **Impact:** The entire purpose of this audit (evaluating the Oracle avatar, lip-sync, and Sanctuary UI) cannot be performed. All law compliance verdicts are UNVERIFIABLE as a direct result. This is a submission failure, not a code failure — but it blocks the audit entirely.
- **File/Line:** `app.py:282-283` (registration exists; files missing)
- **Action:** Re-submit with `oracle/avatar_server.py`, `oracle_routes.py`, and `oracle/templates/oracle.html` included.

### U2 — Hardcoded Fallback Secret Key
- **What:** `SECRET_KEY` falls back to a hardcoded literal string when `SESSION_SECRET` env var is not set.
- **Impact:** Any attacker who knows the fallback value (it is in source control) can forge Flask session cookies, impersonate any user, and bypass all authentication. Severity: CRITICAL.
- **File/Line:** `app.py:45-46`
- **Action:**
```python
import secrets, sys
secret = os.environ.get("SESSION_SECRET")
if not secret:
    if os.environ.get("FLASK_ENV") == "production":
        print("FATAL: SESSION_SECRET not set in production.", file=sys.stderr)
        sys.exit(1)
    secret = secrets.token_hex(32)  # ephemeral, dev-only
app.config["SECRET_KEY"] = secret
```

### U3 — Signal Gauge Permanently Broken (Wrong Element IDs)
- **What:** `updateSignalStrength()` writes computed values to `#signal-fill` and `#telem-signal`. The audit spec and HTML define the gauge elements as `#sig-composite`, `#sig-sentiment`, and `#sig-spaces`. The correct elements are never updated; the gauge displays its initial state forever.
- **File/Line:** `media_unified.js:916-941` (specifically `932-940`)
- **Action:** Replace all references to `#signal-fill` and `#telem-signal` inside `updateSignalStrength()` with the correct IDs: `#sig-composite`, `#sig-sentiment`, `#sig-spaces`. Verify against the HTML template after change.

### U4 — N+1 Query in `inject_ads()` Template Filter
- **What:** `models.Advertisement.query.filter_by(is_active=True).all()` executes inside a Jinja2 template filter. Every invocation of this filter on a page render fires a full DB round-trip. If the filter is used N times on one page, N queries execute.
- **File/Line:** `app.py:167-190` (specifically `171`)
- **Action:** Fetch active ads once per request in a `before_request` hook and store on Flask's `g` object:
```python
@app.before_request
def load_active_ads():
    from flask import g
    g.active_ads = models.Advertisement.query.filter_by(is_active=True).all()
```
Then reference `g.active_ads` inside the filter instead of querying.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — `db.create_all()` Running at Production Startup
- **Models:** Gemini + GPT-4o (Grok agreed implicitly)
- **What:** `db.create_all()` is called unconditionally at app startup. Flask-Migrate is already present. In production, `create_all()` can silently diverge from the migration history, miss destructive changes, or create columns that migrations would later try to add — causing crashes.
- **File/Line:** `app.py:241-247`
- **Action:** Guard behind an environment check:
```python
if app.config.get("FLASK_ENV") != "production":
    with app.app_context():
        db.create_all()
```
In production, rely exclusively on `flask db upgrade`.

### M2 — XSS Risk: Unescaped Ad Content in Template Filter
- **Models:** GPT-4o + Grok
- **What:** `ad.image_url` and `ad.name` are interpolated directly into an HTML string in `inject_ads()` without escaping. If ad records are ever compromised (insider threat, DB injection, third-party ad network), arbitrary HTML/JS executes in users' browsers.
- **File/Line:** `app.py:175-183`
- **Action:** Use `markupsafe.escape()` on all dynamic fields and return `markupsafe.Markup()`:
```python
from markupsafe import escape, Markup
return Markup(f'<img src="{escape(ad.image_url)}" alt="{escape(ad.name)}">')
```

### M3 — `sys.modules["app"] = sys.modules["__main__"]` Architectural Hack
- **Models:** Gemini + GPT-4o
- **What:** This statement patches the module registry to work around circular import dependencies. It is brittle, makes import behavior unpredictable, breaks certain testing frameworks, and masks a real structural problem.
- **File/Line:** `app.py:234-236`
- **Action:** Resolve the underlying circular dependency. Common fix: move shared objects (db, login_manager, limiter) into a `extensions.py` module that both `app.py` and `routes.py` import from, breaking the cycle cleanly.

### M4 — Overly Broad Public API Cache Header
- **Models:** Gemini + GPT-4o
- **What:** `after_request` handler applies `Cache-Control: public, max-age=60` to all `/api/` responses by default. Any user-specific or authenticated API endpoint cached with this header will serve one user's data to another.
- **File/Line:** `app.py:153-157`
- **Action:** Flip the default to private/no-store and require routes to opt into caching explicitly:
```python
if request.path.startswith("/api/"):
    response.headers["Cache-Control"] = "private, no-store"
```

### M5 — Per-Relay Status Bar Not Implemented
- **Models:** Gemini + GPT-4o
- **What:** The audit spec explicitly requires per-relay UI elements (`#relay-status-bar`, `.mu-relay-item`, `.mu-relay-status`, `.mu-relay-count`). The JavaScript never writes to any of these IDs. The relay status bar is entirely non-functional.
- **File/Line:** `media_unified.js:395-429`
- **Action:** Implement per-relay state tracking in `NostrFeed`. On open/close/error for each relay, update the corresponding `.mu-relay-item` and `.mu-relay-status` elements. Track counts per relay and update `.mu-relay-count`.

### M6 — Nostr Health Optimistic and Misleading
- **Models:** GPT-4o + Grok
- **What:** `setHealth('health-nostr-col', 'connected')` is called when *any* relay opens (`media_unified.js:397-398`). On error/close, only `health-nostr` is updated. One connected relay out of five marks the feed as fully healthy. Operators cannot diagnose partial outages.
- **File/Line:** `media_unified.js:397-433`
- **Action:** Track open relay count. Only mark `health-nostr-col` as connected when ≥1 relay is open; mark degraded when <50% are open; mark error when all are closed.

### M7 — Dangerous Development Script Flag
- **Models:** Gemini + GPT-4o
- **What:** `launch_all_features.sh:81` calls `claude --dangerously-skip-permissions`. This flag bypasses permission checks in the Claude CLI. While not a runtime product risk, it is a serious SDLC risk: a developer running this script could inadvertently grant an AI agent unrestricted filesystem/execution access.
- **File/Line:** `launch_all_features.sh:81`
- **Action:** Remove the flag. If the underlying permission prompt blocks legitimate workflow, resolve that specifically rather than bypassing all checks.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — `load_user()` Can 500 on Malformed Session IDs
- **Source:** GPT-4o only
- **What:** `int(user_id)` in the Flask-Login user loader raises `ValueError` if the session is corrupted or tampered. The loader should return `None` on failure, not raise.
- **File/Line:** `app.py:222-225`
- **Assessment:** **Implement.** This is a correct and well-scoped finding. A tampered session cookie can currently cause a 500 error rather than a graceful logout.
```python
@login_manager.user_loader
def load_user(user_id):
    try:
        return models.User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None
```

### UI2 — Timestamp Updater Never Fires (Missing `data-ts` Attribute)
- **Source:** GPT-4o only
- **What:** `initTimeUpdater()` queries elements with `[data-ts]` to show relative timestamps ("2 minutes ago"). `renderCard()` generates card HTML but never sets a `data-ts` attribute. The updater finds no elements and is permanently inert.
- **File/Line:** `media_unified.js:721` (renderCard) vs `1173-1178` (initTimeUpdater)
- **Assessment:** **Implement.** This is a concrete, verifiable contract mismatch between two functions in the same file. Fix is trivial: add `data-ts="${timestamp}"` to the card's outermost element in `renderCard()`.

### UI3 — Audit Runner Reads Wrong JS Filename
- **Source:** GPT-4o only
- **What:** `docs/audits/run_mu_audit.py:9` reads `static/js/media_unified_v4.js` but the actual audited file is `media_reforge/static/js/media_unified.js`. The automated audit may be running against a stale or nonexistent file.
- **File/Line:** `docs/audits/run_mu_audit.py:9`
- **Assessment:** **Implement immediately.** If the audit runner is validating the wrong file, every automated check is meaningless. Update the path to match the real file location.

### UI4 — No Cleanup of Intervals and WebSockets on Page Lifecycle
- **Source:** GPT-4o only
- **What:** Multiple `setInterval()` calls and WebSocket connections are created with no corresponding teardown. In SPA-style navigation or script re-execution, these accumulate and duplicate polling/connections.
- **File/Line:** `media_unified.js:216-217, 604, 739, 1206`
- **Assessment:** **Implement.** Export cleanup functions or use `AbortController`/`clearInterval()` references stored at module scope. This is a real resource leak.

### UI5 — `linkify()` Fragile Against Edge Cases After HTML Escaping
- **Source:** GPT-4o only
- **What:** The pattern `linkify(escapeHtml(text))` is better than naive linkification, but the regex still injects matched text directly into `href` and link body, which is fragile for encoded entities and trailing punctuation.
- **File/Line:** `media_unified.js:134-137`
- **Assessment:** **Investigate further.** The current approach is safer than raw linkification, but a more robust solution (e.g., a battle-tested library, or strictly validating matched URLs against `URL` constructor) is worth adding to the backlog. Not a P0.

### UI6 — Telemetry Health Marked Connected After Partial Failure
- **Source:** GPT-4o only
- **What:** `setHealth('health-telemetry', 'connected')` is called after `Promise.allSettled()` regardless of how many individual telemetry fetches failed. The health indicator lies about system state.
- **File/Line:** `media_unified.js:293`
- **Assessment:** **Implement.** Check the settled results and compute health from the ratio of fulfilled vs. rejected promises before setting the indicator.

### UI7 — Audit Tooling Labels `gpt-5.4` Output as `gpt4o`
- **Source:** GPT-4o only
- **What:** `docs/intel/run_multi_llm_audit.py:64-75` misattributes model provenance in reports.
- **File/Line:** `docs/intel/run_multi_llm_audit.py:64-75`
- **Assessment:** **Skip for now / low priority.** This is a tooling label bug, not a product bug. Fix during a tooling cleanup sprint.

### UI8 — Frontend Race Condition on Shared `state` Object
- **Source:** Grok only (Gemini acknowledged but was less specific)
- **What:** Multiple async callbacks (`updateSignalStrength`, `NostrFeed.handleEvent`, telemetry fetches) all write to a single shared `state` object with no coordination. In the browser single-threaded event loop this won't cause data corruption, but it can produce inconsistent intermediate UI states.
- **File/Line:** `media_unified.js:113-121`
- **Assessment:** **Investigate further.** This is real but somewhat overstated as a "race condition" in a single-threaded runtime. The practical consequence is stale renders, not corrupted data. Consider a simple reducer pattern or batched update queue if UI flicker is observed.

### UI9 — Unbounded Nostr Reconnection Attempts
- **Source:** Grok only
- **What:** Exponential backoff exists but there is no maximum retry count or maximum delay cap. A permanently dead relay will be retried indefinitely.
- **File/Line:** `media_unified.js:419-425`
- **Assessment:** **Implement.** Add `MAX_RETRIES = 10` and cap backoff at 5 minutes. After max retries, mark relay as permanently failed and stop attempting.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Canvas Usage: Law Violation or Not?
- **Conflict:** GPT-4o (Cycle 1) flagged Canvas use in `media_unified.js:169-199, 760-806` as a violation of project law (LAW 4). Gemini (Cycle 2) explicitly retracted this, stating LAW 4 bans "Three.js, VR, DAO, WebGL shaders" — not Canvas.
- **Tiebreaker: Gemini is correct.** The laws as provided in this audit packet do not prohibit Canvas. LAW 4 specifically bans Three.js, VR, DAO, and WebGL shaders. Canvas 2D API is a distinct technology not mentioned. GPT-4o's Cycle 1 finding on this point was an error that GPT-4o itself partially walked back in Cycle 2. **Do not implement any Canvas-removal work based on law compliance grounds.**
- **Caveat:** If a project-specific design document (outside this audit packet) prohibits Canvas for UI animations, that would override this verdict. Verify against the gospel document.

### C2 — Severity of Frontend "Race Condition"
- **Conflict:** Grok and Gemini characterized the shared `state` mutations as race conditions requiring a locking mechanism. GPT-4o (Cycle 2) correctly noted JavaScript's single-threaded event loop means true data races cannot occur, but acknowledged intermediate UI states are a real concern.
- **Tiebreaker: GPT-4o is more precisely correct.** This is not a race condition in the multi-threaded sense. It is a stale-closure / uncoordinated-update problem. The fix is a batched UI update pattern or simple state reducer, not a mutex. Categorize as a frontend quality issue (P2), not a correctness or security issue.

### C3 — Backend Quality Score (3 vs. 4)
- **Conflict:** Grok scored backend at 4/10; Gemini and GPT-4o scored 3/10.
- **Tiebreaker: 3/10.** Grok's higher score is inconsistent with the `sys.modules` hack (which Grok did not independently identify), the startup `create_all()` risk, and the `load_user()` 500 risk. The two-model majority of 3/10 is better supported by evidence.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> **Honest assessment:** No area of the submitted code received unanimous praise across all three models. The models were consistent in finding problems everywhere they could audit. The following patterns were noted as *acceptable* or *not broken*, which is the closest to a validated strength this submission offers:

- **Relay URL Keying:** Nostr relay URLs are consistently keyed with full `wss://` URLs rather than display names, which prevents a class of connection-duplication bugs.
- **Note Deduplication:** The `seen` Set in `NostrFeed` correctly deduplicates incoming Nostr events.
- **`after_request` Security Headers:** The global addition of security/cache headers is structurally sound, even though the specific cache values for API routes need correction.
- **Author Filter Uses `pubkey` (Hex), Not `npub`:** The Nostr filter correctly uses `pubkey` in hex format, avoiding the "npub is not valid hex" bug that affects many Nostr implementations.

**Do NOT change these patterns in the second pass.**

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|---|---|---|
| LAW 1: Wav2Lip is the ONLY approved lip-sync engine | **UNVERIFIABLE** | `avatar_server.py` not submitted |
| LAW 2: `apply_blink()` is permanently disabled | **UNVERIFIABLE** | `avatar_server.py` not submitted |
| LAW 3: [Assumed audio/voice law] | **UNVERIFIABLE** | Core feature files absent |
| LAW 4: No Three.js, no VR, no DAO, no WebGL shaders | **LIKELY COMPLIANT** | No evidence of these in submitted files; Canvas use is not prohibited |
| LAW 5: `avatar_server.py` is the authoritative file | **SUBMISSION VIOLATION** | File was not included in the audit package; compliance with its internal requirements cannot be assessed |

**Final Determination:** Zero laws can be certified as compliant or violated for the core feature. The audit submission structurally failed LAW 5 compliance review by excluding the authoritative file. This is a **process blocker**, not a code verdict.

---

## SECURITY CONSENSUS

Priority-ordered security issues with multi-model agreement:

| Priority | Issue | File:Line | Models |
|---|---|---|---|
| **CRITICAL** | Hardcoded fallback secret key enables session forgery | `app.py:45-46` | All 3 |
| **HIGH** | Unescaped ad content allows XSS via compromised ad records | `app.py:175-183` | GPT-4o + Grok |
| **HIGH** | Overly broad public API caching can leak user-specific data | `app.py:153-157` | Gemini + GPT-4o |
| **HIGH** | `--dangerously-skip-permissions` in dev launcher | `launch_all_features.sh:81` | Gemini + GPT-4o |
| **MEDIUM** | `load_user()` raises 500 on malformed session (should return None) | `app.py:222-225` | GPT-4o only |
| **MEDIUM** | `inject_ads()` performs DB query per invocation (DoS amplification) | `app.py:167-190` | All 3 |

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class product:

1. **No feature code, no feature audit.** (All 3 models) A world-class engineering process does not submit an audit for a feature while omitting the feature's primary implementation files. The audit pipeline itself needs a pre-flight check that validates required files are present before triggering review.

2. **No production-safety guardrails at the framework level.** (Gemini + GPT-4o) Secret key validation, `db.create_all()` suppression, and import structure all need environment-aware guards. World-class apps fail loudly and immediately when misconfigured for production rather than silently degrading.

3. **No observable system health.** (GPT-4o + Grok) The signal gauge is broken, per-relay status is unimplemented, telemetry health is misleading, and timestamp relative display is inert. A world-class real-time dashboard provides accurate, live health signals operators can act on. Currently this dashboard lies about its own state.

4. **No error surfaces for users or operators.** (Gemini + GPT-4o) Silent `catch` blocks throughout the frontend mean failures are invisible. World-class products log errors to an observability backend and surface degraded states in the UI so users understand what is happening.

5. **No automated audit coverage of the actual deployed asset.** (GPT-4o) The audit runner reads a different file than the one being audited. World-class CI pipelines audit exactly what gets deployed, validated by hash or path matching.

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Submit missing core feature files (`oracle/avatar_server.py`, `oracle_routes.py`, `oracle/templates/oracle.html`) for audit | Missing from submission | All 3 | Entire feature is unauditable without them; all law compliance is UNVERIFIABLE |
| P0-2 | Replace hardcoded fallback secret key with fail-loud production guard or ephemeral dev key | `app.py:45-46` | All 3 | Session forgery possible with known key in source control |
| P0-3 | Fix signal gauge element ID mismatch in `updateSignalStrength()` | `media_unified.js:932-940` | All 3 | Gauge permanently displays initial state; core UI feature is broken |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Move active ads query to `before_request` hook on `g`; remove DB call from template filter | `app.py:167-190` | All 3 | N+1 DB query per page render; degrades under any real load |
| P1-2 | Escape all dynamic ad fields with `markupsafe.escape()`; return `Markup` | `app.py:175-183`

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles. In Cycle 1, it was the only model to independently identify the signal gauge root cause with precise file/line citations (`media_unified.js:916-941`), name the specific wrong HTML IDs versus the correct ones, flag the `sys.modules` hack as an architectural smell, and surface the `launch_all_features.sh` process-level security risk — all findings that were validated and absorbed into the Cycle 2 consensus. Its Cycle 2 self-correction was also the most intellectually honest, explicitly retracting its Canvas violation finding when it re-read the law rather than quietly dropping it.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: **severity × verifiability × blast radius**

---

## P0 — BLOCKS AUDIT ENTIRELY (fix before anything else)

### P0-1 — Resubmit Missing Core Feature Files
- **Files:** `oracle/avatar_server.py`, `oracle_routes.py`, `oracle/templates/oracle.html`
- **Why P0:** Every law compliance verdict, every correctness check, and the entire stated purpose of the `f1-avatar-oracle` audit is unverifiable without these. All other findings below are on *peripheral* files only.
- **Action:** Add all three files to the audit package. Confirm `oracle_bp` registered at `app.py:282-283` resolves correctly after inclusion.

---

## P1 — CRITICAL SECURITY (exploitable or session-breaking in production)

### P1-1 — Hardcoded Fallback Secret Key
- **File:** `app.py:45-46`
- **Risk:** Session forgery, CSRF token prediction, cross-environment session bleedover if `SESSION_SECRET` is unset in any deploy.
- **Action:** Remove the hardcoded fallback entirely. Raise a hard startup exception if `SESSION_SECRET` is absent. Add to CI environment validation checklist.

### P1-2 — XSS via Unescaped Ad Content in Template Filter
- **File:** `app.py:175-183`
- **Risk:** `ad.image_url` and `ad.name` interpolated directly into HTML string without escaping. If ad content is ever compromised or admin credentials are weak, this is a stored XSS vector.
- **Action:** Pass values through `markupsafe.escape()` before interpolation, or refactor to use Jinja2 template rendering instead of manual string concatenation.

### P1-3 — Public Cache Header Applied to All `/api/` Routes
- **File:** `app.py:153-157`
- **Risk:** User-specific or authenticated API responses cached publicly for 60 seconds. Any `/api/` route returning user data is silently broken.
- **Action:** Restrict the public cache header to explicitly whitelisted, verified-public endpoints. Default all `/api/` responses to `Cache-Control: no-store` unless opted in.

---

## P2 — CORRECTNESS (broken features, confirmed bugs)

### P2-1 — Signal Gauge Never Updates (Wrong DOM IDs)
- **File:** `media_reforge/static/js/media_unified.js:916-941`
- **Bug:** `updateSignalStrength()` writes to `#signal-fill` and `#telem-signal`. The gauge HTML uses `#sig-composite`, `#sig-sentiment`, `#sig-spaces`. The gauge is permanently frozen at its initial state.
- **Action:** Update all DOM write targets in `updateSignalStrength()` to match the actual HTML spec IDs. Verify with a live render test after fix.

### P2-2 — Relay Status Bar Not Implemented
- **File:** `media_unified.js` (relay connection handlers)
- **Bug:** The audit spec explicitly requires updates to `#relay-status-bar`, `.mu-relay-item`, `.mu-relay-status`, `.mu-relay-count`. None of these selectors are written to anywhere in the JS.
- **Action:** Implement relay status update calls inside the WebSocket `onopen`, `onclose`, and `onerror` handlers for each relay connection.

### P2-3 — Feed Timestamps Never Refresh
- **File:** `media_unified.js:721` vs `1173-1178`
- **Bug:** `initTimeUpdater()` polls for `data-ts` attributes on cards. `renderCard()` never sets `data-ts`. All timestamps are static from render time.
- **Action:** Add `data-ts="${timestamp}"` to the card element in `renderCard()`. Confirm `initTimeUpdater()` then picks them up correctly.

### P2-4 — Telemetry Reports `connected` on Partial/Total Failure
- **File:** `media_unified.js:293`
- **Bug:** `setHealth('health-telemetry', 'connected')` is called unconditionally after `Promise.allSettled()`, regardless of how many promises rejected.
- **Action:** Inspect the `allSettled` results array. Set health to `degraded` if any rejected, `error` if all rejected, `connected` only if all fulfilled.

---

## P3 — PERFORMANCE (degrades under load)

### P3-1 — N+1 DB Query in Template Filter
- **File:** `app.py:167-190`
- **Bug:** `inject_ads()` runs a live `SELECT * FROM advertisements WHERE is_active=1` on every invocation. If used N times per page render, runs N queries.
- **Action:** Fetch active ads once per request in a `before_request` hook, store on `flask.g`, and read from `g` inside the filter. Alternatively, add aggressive short-TTL caching (e.g., 30s) with cache invalidation on ad update.

### P3-2 — Unbounded Nostr Reconnect Attempts
- **File:** `media_unified.js:386-430`
- **Bug:** Exponential backoff on relay reconnection has no maximum retry cap. Long-running sessions accumulate unbounded reconnect loops.
- **Action:** Add `MAX_RECONNECT_ATTEMPTS = 10` (or similar). After cap is reached, mark relay as permanently failed, update the relay status bar (see P2-2), and stop retrying until explicit user action.

---

## P4 — ARCHITECTURE / MAINTAINABILITY

### P4-1 — `sys.modules` Hack Signals Circular Dependency
- **File:** `app.py:234-236`
- **Issue:** `sys.modules["app"] = sys.modules["__main__"]` is a workaround for a structural import problem, not a solution. It will break silently when the module graph changes.
- **Action:** Identify which modules import from `app` directly and refactor to use an application factory pattern (`create_app()`). This resolves both the circular dependency and makes the app properly testable.

### P4-2 — `db.create_all()` at Startup Masks Migration Drift
- **File:** `app.py:241-247`
- **Issue:** Running `create_all()` in production silently creates tables that Alembic doesn't know about, causing schema divergence that only manifests as data loss or integrity errors later.
- **Action:** Remove `create_all()` from the startup path entirely. Add a CI check that runs `alembic check` to confirm migration state matches model definitions before any deploy.

### P4-3 — `launch_all_features.sh` Uses `--dangerously-skip-permissions`
- **File:** `launch_all_features.sh:81`
- **Issue:** This is not a runtime risk but is a serious SDLC risk — automated scripts running with skipped permission checks in a shared dev environment can cause irreversible side effects.
- **Action:** Remove the flag. If the underlying permission issue is real, fix it explicitly in configuration rather than bypassing it.

### P4-4 — Shared Mutable `state` Object with No Coordination
- **File:** `media_unified.js:113-121`
- **Issue:** Multiple async event handlers (WebSocket events, API responses, timers) mutate the same `state` object with no queuing or locking. This is a race condition waiting to manifest under normal relay traffic.
- **Action:** Refactor to a reducer pattern: all state mutations go through a single `dispatch(action)` function that applies changes sequentially