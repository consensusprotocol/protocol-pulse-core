# CONSENSUS REPORT — B1-NEWSLETTER — CYCLE 2
Generated: 2026-03-09 02:45
Models: grok, gemini, gpt4o

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | 5/100 | 20/100 | 25/100 | **17/100** |
| Frontend/UI | 10/100 | 24/100 | 20/100 | **18/100** |
| Error Handling | 5/100 | 18/100 | 20/100 | **14/100** |
| Security | 30/100 | 38/100 | 40/100 | **36/100** |
| Performance | N/A | 28/100 | 30/100 | **29/100** |
| Law Compliance | 5/100 | 5/100 | 10/100 | **7/100** |
| World-Class Gap | N/A | 15/100 | 20/100 | **17/100** |

> **Synthesizer note:** Gemini's scores are consistently the most aggressive (lowest); GPT-4o and Grok are more moderate. The consensus column splits the difference with a slight lean toward Gemini's harshness where the reasoning is strongest (Error Handling, Law Compliance). The backend and law scores are near-zero regardless of model — the feature literally does not exist in the submitted code.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Core newsletter feature implementation is entirely absent
- **What:** The `b1-newsletter` feature has zero implementation. The only evidence of its existence is blueprint registration at `app.py:273-277`. No route file, no subscriber model, no send log model, no Resend integration, no unsubscribe system, no email templates.
- **File/Line:** `app.py:273-277` (registration only); all implementation files are missing.
- **Change:** Implement `routes_newsletter_trigger.py`, subscriber and send-log database models, Resend mail service wrapper, admin/manual trigger route, unsubscribe route, and content generation/templates.

### U2 — LAW 1 Violation: `RESEND_API_KEY` not validated at startup
- **What:** `app.py:72-85` performs startup diagnostics for required env vars but `RESEND_API_KEY` is absent from this list. The app can boot and appear healthy without its core email dependency configured.
- **File/Line:** `app.py:72-85`
- **Change:** Add `RESEND_API_KEY` to required environment variable checks. Emit a hard warning (or fail-fast) if absent.

### U3 — LAW 2 Violation: No one-newsletter-per-day enforcement mechanism
- **What:** There is no database table, transactional check, scheduler guard, or any other mechanism to enforce the rule that at most one newsletter is sent per calendar day. Concurrent admin triggers could fire multiple sends.
- **File/Line:** Missing implementation; see `app.py:293-299` for scheduler anchor.
- **Change:** Implement a `newsletter_send_log` table with a unique constraint on `sent_date`. Use a transactional check-and-insert (select-for-update or equivalent) before any send. Reject trigger if a record for today already exists.

### U4 — LAW 4 Violation: No unsubscribe route or token system
- **What:** There is no `/unsubscribe?token=...` route, no UUID token generation, no token storage in a subscriber model, and no mechanism to deactivate subscribers. This is a CAN-SPAM compliance failure.
- **File/Line:** Missing implementation.
- **Change:** Implement subscriber model with a `unsubscribe_token` UUID column. On newsletter send, embed `?token={uuid}` in each email's footer link. Implement `GET /unsubscribe?token=<uuid>` that marks subscriber inactive.

### U5 — `app.py` silently swallows critical startup failures
- **What:** Three separate exception handlers allow the app to boot in a degraded/broken state:
  - `db.create_all()` failure at `app.py:243-247` is swallowed as a warning.
  - Newsletter blueprint import failure at `app.py:273-277` is printed and ignored.
  - Scheduler initialization failure at `app.py:293-299` is swallowed.
- **File/Line:** `app.py:243-247`, `app.py:273-277`, `app.py:293-299`
- **Change:** For production environments, `db.create_all()` failure and essential blueprint import failure should raise or hard-exit. At minimum, blueprint failure should use `logging.critical()` and set a health-check flag, not just `print()`.

### U6 — Hardcoded fallback `SESSION_SECRET` is a security risk
- **What:** `app.py:45-46` falls back to a hardcoded string if `SESSION_SECRET` is missing from `.env`. In production, this makes sessions predictable and cross-instance behavior unsafe.
- **File/Line:** `app.py:45-46`
- **Change:** Remove the hardcoded fallback. If `SESSION_SECRET` is absent in a non-development environment, the application should refuse to start.

### U7 — Missing CSRF validation (token generated but never checked)
- **What:** `app.py:115-126` generates and injects a CSRF token into templates but there is no demonstrated validation of this token on any state-changing route (POST/PUT/DELETE). Generation without validation provides zero protection.
- **File/Line:** `app.py:115-126`
- **Change:** Implement a `@before_request` handler or per-route decorator that validates the CSRF token on all non-GET requests. Consider using Flask-WTF's built-in CSRF protection.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Stored XSS in `inject_ads` template filter (Gemini + GPT-4o)
- **What:** `app.py:175-183` interpolates `ad.image_url` and `ad.name` directly into an HTML f-string without sanitization. If ad content is admin-entered or imported from any external source, this is a stored XSS vector.
- **File/Line:** `app.py:175-183`
- **Change:** Escape `ad.name` and `ad.image_url` using `markupsafe.escape()` before interpolation. Validate `ad.image_url` is a safe URL scheme on write, not on render.

### M2 — `launch_all_features.sh` uses `--dangerously-skip-permissions` (Gemini + GPT-4o)
- **What:** `launch_all_features.sh:81` invokes the Claude CLI with `--dangerously-skip-permissions`, which bypasses filesystem and execution guardrails and can allow arbitrary code execution in the development environment.
- **File/Line:** `launch_all_features.sh:81`
- **Change:** Remove this flag. If it is required for automation, scope it to the narrowest possible permission set and document the explicit risk acceptance with a sign-off comment.

### M3 — Canvas usage in `media_unified.js` violates stated stack law (GPT-4o + Grok)
- **What:** `media_unified.js:169-199` (sparklines) and `media_unified.js:760-806` (sentiment gauge) use `<canvas>` elements. The project's own stack law explicitly prohibits Canvas.
- **File/Line:** `media_unified.js:169-199`, `media_unified.js:760-806`
- **Change:** Replace both canvas implementations with pure SVG or CSS-based equivalents.

### M4 — Broken timestamp updater in `media_unified.js` (GPT-4o + Gemini)
- **What:** `media_unified.js:1173-1179` calls `initTimeUpdater()` which queries `.intel-card-time[data-ts]`. However, rendered card HTML at `media_unified.js:556` (Nostr notes) and `media_unified.js:721` (combined feed) does not set the `data-ts` attribute. The time updater silently does nothing.
- **File/Line:** `media_unified.js:556`, `media_unified.js:721`, `media_unified.js:1173-1179`
- **Change:** Add `data-ts="${timestamp_unix}"` to the rendered time elements in both card renderers.

### M5 — Frontend `fetch` calls have empty/missing error handling and no timeouts (GPT-4o + Gemini)
- **What:** Multiple `fetch()` calls in `media_unified.js` (e.g., combined feed at `js:609`) have empty `.catch` blocks or no `.catch` at all. No fetch call sets an `AbortController` timeout. This violates the project's own stated development guidelines ("Every API call: timeout + fallback").
- **File/Line:** `media_unified.js:609`, `media_unified.js:623` and others throughout the file.
- **Change:** Add `AbortController`-based timeouts (suggest 10s) to every fetch. Replace empty `.catch` blocks with UI feedback (error state rendering) and `console.error` logging.

### M6 — Global rate limit `200 per day` is dangerously coarse (GPT-4o + Grok)
- **What:** `app.py:96-97` applies a blanket `200 per day` default to all routes. This is likely to throttle legitimate users while leaving expensive internal endpoints under-protected. Newsletter trigger endpoints are especially sensitive to rate limit misconfiguration.
- **File/Line:** `app.py:96-97`
- **Change:** Remove or raise the global default. Apply route-specific limits: strict (e.g., `5/hour`) on the newsletter trigger endpoint, standard on auth endpoints, generous on read-only API endpoints.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### N1 — `inject_ads` splits on `</p>` which can produce invalid DOM (GPT-4o only)
- **What:** `app.py:184-187` performs string surgery on content by splitting on `</p>`. This fails silently on uppercase tags, no-paragraph content, or malformed HTML.
- **Assessment:** **Implement.** Low effort, real correctness risk. Replace with an HTML parser (e.g., `html.parser` or `lxml`) for insertion rather than string splitting.

### N2 — Nostr health false-positive: marks "connected" on socket open, not on valid event receipt (GPT-4o only)
- **What:** `media_unified.js:395-398` sets the connected state immediately on WebSocket `onopen`, before any valid Nostr event is received. This can display a green "connected" status even if the relay is up but not responding with data.
- **Assessment:** **Implement.** Move the "connected" state update to fire on receipt of the first valid event, not on socket open. Low-effort, meaningful UX correctness improvement.

### N3 — `updateSourceHealth()` has no fallback state for never-received sources (GPT-4o only)
- **What:** `media_unified.js:890-905` has no `else` branch for sources that have never emitted data. They remain in whatever initial DOM class was set at load, creating permanently stale UI state.
- **Assessment:** **Implement.** Add an explicit `unknown`/`loading` CSS class for sources that have not yet reported health. Minimal effort.

### N4 — `NostrFeed` reconnect loop has no cap and no page-unload teardown (GPT-4o only)
- **What:** `media_unified.js:419-425`, `457` — The WebSocket reconnect loop runs indefinitely with no maximum retry count and no cleanup on `visibilitychange` or `unload`. This leaks connections and wastes resources on hidden/backgrounded tabs.
- **Assessment:** **Implement.** Add exponential backoff with a max retry cap (e.g., 10 attempts). Add a `document.addEventListener('visibilitychange')` handler to pause reconnects when hidden.

### N5 — `renderAvatar()` uses inline `onerror` handlers (GPT-4o only)
- **What:** `media_unified.js:345`, `703`, `841` use inline `onerror="..."` on `<img>` tags, which is hostile to strict Content Security Policy headers.
- **Assessment:** **Investigate.** If a CSP is planned (it should be), this blocks adoption. Convert to delegated event listeners. Mark as P2 unless CSP hardening is imminent.

### N6 — `db.create_all()` encourages schema drift and may not apply migration constraints (GPT-4o only)
- **What:** Beyond swallowing the exception, the use of `create_all()` at runtime means unique constraints and indexes required for Law 2 enforcement may not be applied consistently across environments if migrations are the canonical schema source.
- **Assessment:** **Implement.** The newsletter's Law 2 compliance depends on a unique `sent_date` constraint. This must be managed via explicit Alembic migration, not `create_all()`. Add a note in the migration to fail loudly if the constraint cannot be created.

### N7 — Signal gauge DOM IDs mismatch spec (GPT-4o only)
- **What:** `media_unified.js:932-940` writes to `#signal-fill` and `#telem-signal`, but the audit spec references `sig-sentiment`, `sig-spaces`, `sig-composite`. This is code-to-spec drift indicating the implementation was not validated against the design document.
- **Assessment:** **Investigate.** Determine which is authoritative — the JS or the spec — and align them. This is a symptom of a broader process failure (see Gemini's N8 below).

### N8 — Systemic process failure: instructions given but not verified (Gemini only)
- **What:** `launch_all_features.sh:53` explicitly instructs the AI agent to implement "Every API call: timeout + fallback. Every DB write: rollback." The submitted `media_unified.js` violates both instructions. The newsletter PR being feature-empty is the extreme version of this pattern.
- **Assessment:** **Implement process fix.** This is the root cause under many individual bugs. Add a pre-merge checklist and/or automated linting that enforces: no empty `.catch` blocks, all fetches have abort controllers, all DB writes are in try/except with rollback.

### N9 — Logging granularity may hide Resend API failures (Grok only)
- **What:** `app.py:28-32` suppresses `urllib3` and `requests` to WARNING level. Since Resend's SDK likely uses one of these transports, authentication errors and rate-limit responses from Resend could be silently swallowed.
- **Assessment:** **Implement.** When implementing the Resend integration, add a dedicated logger for the newsletter send service at DEBUG/INFO level, independent of the global suppression. Explicitly log every Resend API response code.

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — Severity of audit tooling using speculative model names
- **Gemini:** Flagged as a plausible in-universe concern but not a hard blocker.
- **GPT-4o:** Partially agreed — environment-dependent, not a product blocker.
- **Grok:** Did not flag.
- **Verdict: GPT-4o is correct.** This is not a product blocker for `b1-newsletter`. If the audit scripts are expected to run in CI today, it is a tooling bug — but it does not affect newsletter correctness or compliance. Mark as informational only, outside the scope of this action plan.

### C2 — Whether frontend JS issues are in-scope for this audit
- **Gemini:** Treated them as meaningful quality signal for the overall codebase.
- **GPT-4o:** Audited them thoroughly and linked some (Canvas law) to stack compliance.
- **Grok:** Deprioritized them as unrelated to `b1-newsletter`.
- **Verdict: Gemini and GPT-4o are correct.** The Canvas law violation is a first-class compliance failure regardless of which feature uses it. The timestamp and reconnect bugs affect the shell that the newsletter feature will be deployed within. These belong in the P2 tier of this action plan, not ignored.

### C3 — Score severity: Gemini (5/100 Backend) vs. GPT-4o (20/100) vs. Grok (25/100)
- **Verdict: Gemini's harshness is justified for Backend Logic and Error Handling specifically.** The newsletter feature has literally zero backend logic submitted, and `app.py`'s error handling is architecturally broken (not just weak). Gemini's near-zero scores on those two subsystems are accurate. GPT-4o and Grok were appropriately moderate on Security and Performance where partial implementation does exist.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

All three models found the overall application *shell* (`app.py` structure) to be thoughtful in several areas. These should not be regressed:

1. **Database URL normalization** (`app.py:59-65`): The `postgres://` → `postgresql://` rewrite for SQLAlchemy compatibility is correct and robust.
2. **`_NullCache` fallback pattern** (`app.py:103`): The defensive no-op cache implementation gracefully handles environments where Redis is unavailable. This is a good pattern.
3. **Environment-aware configuration** (`app.py:43`): Varying run environments are correctly detected and handled.
4. **Circular import protection** (`app.py:38`): The application factory pattern is correctly employed to avoid circular dependencies.
5. **`.env` loading at startup** (`app.py:5`): Basic environment hygiene is present.

> **Do not modify these patterns in the second pass.**

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Determination |
|---|---|---|
| LAW 1: Resend API only (`RESEND_API_KEY` in `.env`) | ❌ **VIOLATED** | No Resend integration exists. `RESEND_API_KEY` not validated at startup. Unanimous finding. |
| LAW 2: One newsletter per day, never two | ❌ **VIOLATED** | No send-log table, no daily unique constraint, no transactional guard. Unanimous finding. |
| LAW 3: Newsletter format (subject, from, content structure) | ⚠️ **UNVERIFIABLE** | No email composition code submitted. Cannot confirm compliance. |
| LAW 4: Unsubscribe link with UUID token | ❌ **VIOLATED** | No unsubscribe route, no token model, no subscriber deactivation. Unanimous finding. |

**Final determination: 3 of 4 laws are actively violated. 1 is unverifiable. This feature is not law-compliant in any dimension.**

---

## SECURITY CONSENSUS

Priority-ordered security issues with multi-model agreement:

| Priority | Issue | File:Line | Models |
|---|---|---|---|
| 🔴 P0 | `--dangerously-skip-permissions` in build script (RCE risk in dev pipeline) | `launch_all_features.sh:81` | Gemini + GPT-4o |
| 🔴 P0 | Missing CSRF validation on all state-changing routes | `app.py:115-126` | All 3 |
| 🔴 P0 | Stored XSS in `inject_ads` via unescaped ad content | `app.py:175-183` | Gemini + GPT-4o |
| 🟠 P1 | Hardcoded fallback `SESSION_SECRET` in production | `app.py:45-46` | All 3 |
| 🟠 P1 | App boots in broken state masking security-critical missing components | `app.py:243-247`, `273-277` | All 3 |
| 🟡 P2 | Inline `onerror` handlers block CSP hardening | `media_unified.js:345`, `703`, `841` | GPT-4o |

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as gaps between current state and a world-class product:

1. **Feature completeness as a prerequisite for any quality claim** (All 3): A world-class newsletter product requires full lifecycle management — subscriber sign-up, confirmed opt-in, send history, bounce/complaint handling, unsubscribe with immediate effect, and re-subscribe prevention. None of this is present.

2. **Operational observability** (Gemini + GPT-4o + Grok): A world-class email feature has dedicated structured logging per send attempt, per-recipient delivery tracking (via Resend webhooks), and a health dashboard. The current app suppresses the very HTTP transport logs that would carry this signal.

3. **Resilient error handling as a first principle, not an afterthought** (All 3): Every model independently flagged the same anti-pattern — swallowed exceptions from `app.py` startup through to frontend `fetch` calls. A world-class codebase treats errors as first-class citizens with explicit handling, user feedback, and structured log emission at every failure point.

4. **Schema integrity via migrations, not `create_all()`** (GPT-4o + Grok): World-class database management uses versioned, reviewable, rollback-capable migrations (Alembic). The current `create_all()` approach cannot reliably enforce the unique constraints that Law 2 compliance depends on.

5. **Security hardening from day one** (All 3): CSRF protection, XSS escaping, and proper session secret management are not optional hardening steps — they are baseline requirements. None of the three were fully implemented in the reviewed code.

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Implement the entire `b1-newsletter` feature: `routes_newsletter_trigger.py`, subscriber model, send-log model, Resend service wrapper, trigger route, unsubscribe route, email templates | Missing / `app.py:273-277` | All 3 | Feature does not exist. Nothing else in this list matters until this is done. |
| P0-2 | Implement `newsletter_send_log` table with unique `sent_date` constraint and transactional check-and-insert before every send | Missing | All 3 | LAW 2 compliance. Race condition prevention. |
| P0-3 | Implement `/unsubscribe?token=<uuid>` route with UUID token generation stored in subscriber model | Missing | All 3 | LAW 4 / CAN-SPAM compliance. |
| P0-4 | Integrate Resend API and validate `RESEND_API_KEY` at startup in `app.py:72-85` | `app.py:72-85` + missing service | All 3 | LAW 1 compliance. Silent boot failure prevention. |
| P0-5 | Implement CSRF token validation on all POST/PUT/DELETE routes (add `@before_request` validator or Flask-WTF integration) | `app.py:115-126` | All 3 | Active security vulnerability. Token generated but never checked. |
| P0-6 | Fix stored XSS in `inject_ads`: escape `ad.name` and `ad.image_url` with `markupsafe.escape()` | `app.py:175-183` | Gemini + GPT-4o | Stored XSS attack vector exploitable by any admin-level ad entry. |
| P0-7 | Remove `--dangerously-skip-permissions` from Claude CLI invocation | `launch_all_features.sh:81` | Gemini + GPT-4o | Arbitrary code execution risk in development pipeline. |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Remove hardcoded fallback `SESSION_SECRET`; app must refuse to start in non-dev environments without it | `app.py:45-46` | All 3 | Predictable session secrets in production invalidate all session security. |
| P1-2 | Convert blueprint import failure and `db.create_all()` failure from swallowed warnings to hard failures (or `logging.critical` + health-check flag) | `app.py:243-247`, `app.py:273-

---

# WINNER DETERMINATION

WINNER: GPT-4o — GPT-4o delivered the most comprehensive, specific, and verifiable findings across both cycles, identifying the systemic silent-failure anti-pattern in `app.py`, the stored XSS vector in `inject_ads`, the broken `data-ts` timestamp contract, the DOM ID mismatch between `updateSignalStrength()` and the audit spec, and the Canvas stack-law violation — all with precise file/line citations that proved accurate and were independently confirmed by both Gemini and Grok in Cycle 2. Its recommendations were consistently actionable (specific functions, specific fixes, specific enforcement mechanisms) rather than conceptual, and it achieved the broadest coverage across backend, frontend, security, and law-compliance dimensions without sacrificing depth on any single dimension.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × implementability. Items marked **[BLOCKER]** must be resolved before merge. Items marked **[HIGH]** should be resolved in the same sprint. Items marked **[MEDIUM]** are next-sprint candidates.

---

### P1 — [BLOCKER] Core newsletter feature does not exist
**Files to create:**
- `routes_newsletter_trigger.py` — admin trigger route with auth guard
- `models/subscriber.py` — subscriber table with UUID unsubscribe token, email, created_at, active flag
- `models/send_log.py` — one row per send attempt with date, status, recipient count
- `services/newsletter_service.py` — content assembly, Resend API wrapper, send orchestration
- `templates/newsletter/` — base email template, unsubscribe confirmation page
- `routes_unsubscribe.py` — `/unsubscribe?token=<uuid>` route that sets `active=False`

**Acceptance gate:** All five newsletter laws must be testable against running code.

---

### P2 — [BLOCKER] LAW 2 Violation: No one-per-day enforcement
**File:** `services/newsletter_service.py` (to be created)
**Required implementation:**
```python
# Transactional check-and-insert pattern
with db.session.begin():
    today = date.today()
    existing = SendLog.query.filter_by(send_date=today).with_for_update().first()
    if existing:
        raise AlreadySentTodayError()
    log = SendLog(send_date=today, status="in_progress")
    db.session.add(log)
```
This must be atomic. A flag, a cron guard, or an application-level check without `SELECT ... FOR UPDATE` is insufficient — concurrent trigger requests will bypass it.

---

### P3 — [BLOCKER] LAW 1 Violation: `RESEND_API_KEY` absent from startup validation
**File:** `app.py:72-85`
**Change:** Add `RESEND_API_KEY` to the required-env-var diagnostic block and convert from warn-and-continue to hard-fail:
```python
required = ["DATABASE_URL", "SESSION_SECRET", "RESEND_API_KEY"]
missing = [k for k in required if not os.environ.get(k)]
if missing:
    raise RuntimeError(f"Missing required env vars: {missing}")
```
Warn-only allows the app to boot and appear healthy while email delivery is permanently broken.

---

### P4 — [BLOCKER] `app.py` boots successfully in a broken state
**File:** `app.py:243-247`, `273-277`, `293-299`
**Change:** Differentiate fatal failures from graceful-degradation failures:
- `db.create_all()` failure → hard raise, not `logger.warning`
- Newsletter blueprint import failure → hard raise (this is the primary feature)
- Scheduler init failure → warn-and-continue is acceptable (scheduler is not core to correctness)

Current behavior means CI/CD green-lights a deploy with no newsletter routes registered and no observable error.

---

### P5 — [BLOCKER] Stored XSS in `inject_ads` template filter
**File:** `app.py:175-183`
**Vulnerability:** `ad.image_url` and `ad.name` are interpolated directly into an HTML f-string with no escaping. Any advertiser-controlled or DB-sourced string becomes executable script.
**Fix:**
```python
from markupsafe import escape
html = (
    f'<div class="ad-unit">'
    f'<img src="{escape(ad.image_url)}" alt="{escape(ad.name)}">'
    f'</div>'
)
return Markup(html)
```
Additionally, move the DB query out of the template filter and into the view layer — a DB call per template render is an unacceptable performance anti-pattern.

---

### P6 — [HIGH] Hardcoded session secret fallback
**File:** `app.py:45-46`
**Change:** Remove the fallback entirely. If `SESSION_SECRET` is absent, raise at startup (covered by P3's pattern). A hardcoded fallback means every development or misconfigured production instance shares an identical secret, making session forgery trivial.

---

### P7 — [HIGH] Broken timestamp updater in `media_unified.js`
**File:** `media_unified.js:1173-1179` (consumer), `556`, `721` (producers)
**Bug:** `initTimeUpdater()` queries `[data-ts]` but no rendered card sets that attribute. The updater runs on an empty NodeList and silently does nothing — timestamps never update after initial render.
**Fix:** Add `data-ts="${item.timestamp}"` to the card template string at lines 556 and 721.

---

### P8 — [HIGH] DOM contract mismatch: signal gauge IDs
**File:** `media_unified.js:932-940`
**Bug:** `updateSignalStrength()` writes to `#signal-fill` and `#telem-signal`. The audit spec and surrounding infrastructure expect `#sig-sentiment`, `#sig-spaces`, `#sig-composite`. These IDs resolve to `null` at runtime — gauge updates are silently dropped.
**Fix:** Audit which ID set is canonical (spec or implementation), update the non-canonical side, add an `if (!el) { console.error(...) }` guard to make future mismatches visible.

---

### P9 — [HIGH] Canvas usage violates stated stack law
**File:** `media_unified.js:169-199`, `760-806`
**Issue:** `<canvas>` is used for sparklines and signal gauges. If the stack law prohibiting Canvas is enforceable, replace with SVG `<polyline>` for sparklines and CSS `clip-path` or SVG arc for gauges. Both are achievable without a charting library and without Canvas.

---

### P10 — [HIGH] Silent API failure in media feed fetch
**File:** `media_unified.js:609-623`
**Bug:** The `.catch` block is empty. Network failure or non-200 response leaves the UI in a permanent loading state with no user feedback.
**Fix:**
```javascript
.catch(err => {
    console.error('Feed fetch failed:', err);
    feed.innerHTML = '<p class="error">Failed to load feed. Retrying…</p>';
    setTimeout(() => this.fetchAll(), 30000);
});
```

---

### P11 — [MEDIUM] Rate limiting is global, not route-scoped
**File:** `app.py` (limiter configuration)
**Issue:** A single global rate limit treats the newsletter trigger endpoint identically to static asset routes. The trigger endpoint should have its own strict limit (e.g., `"5 per day"`) independent of global defaults, enforced with `@limiter.limit("5/day")` on the trigger route.

---

### P12 — [MEDIUM] `launch_all_features.sh` uses `--dangerously-skip-permissions`
**File:** `launch_all_features.sh:81`
**Issue:** This flag allows arbitrary code execution without permission prompts in the Claude CLI. Acceptable in a sandboxed local environment; unacceptable if this script is ever run in CI or on a shared machine. Add a comment block documenting the assumption and add a `[[ $CI ]] && echo "ERROR: do not run in CI" && exit 1` guard.

---

### P13 —