# CONSENSUS REPORT — F1-AVATAR-ORACLE — CYCLE 1
Generated: 2026-03-18 05:06
Models: grok (+2 failed)

> **⚠ AUDIT INTEGRITY WARNING**: Only 1 of 3 models successfully completed review. Gemini 2.5 Pro failed with a leaked API key (403 PERMISSION_DENIED). GPT-4o failed with quota exhaustion (429 insufficient_quota). All consensus conclusions below are drawn from Grok-3 alone. Confidence thresholds are reduced accordingly — treat every "unanimous" finding as single-model confidence, and elevate skepticism on any assessment marked "all models agree." A Cycle 2 re-audit with all three models operational is strongly recommended before merge.

---

## SCORES

| Subsystem        | Gemini   | GPT-4o   | Grok | Consensus         |
|------------------|----------|----------|------|-------------------|
| Correctness      | ❌ FAILED | ❌ FAILED | 5/10 | 5/10 (low conf.)  |
| Law Compliance   | ❌ FAILED | ❌ FAILED | 6/10 | 6/10 (low conf.)  |
| Security         | ❌ FAILED | ❌ FAILED | 6/10 | 6/10 (low conf.)  |
| Frontend Quality | ❌ FAILED | ❌ FAILED | N/A  | UNSCORED          |
| Backend Quality  | ❌ FAILED | ❌ FAILED | 5/10 | 5/10 (incomplete) |
| **Overall**      | ❌ FAILED | ❌ FAILED | 5/10 | **5/10 — PROVISIONAL** |

> Scores are provisional. No cross-model validation was possible. Do not treat this as a passed quality gate.

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

> With only one model, "unanimous" means Grok identified these with high internal confidence. They should still be treated as single-model findings requiring human verification.

---

### FINDING U-1: Silent Blueprint Registration Failure
**File**: `app.py` | **Lines**: 370–374
**What it is**: The Oracle Avatar blueprint import is wrapped in a try/except that logs a CRITICAL error but allows the application to continue running without the feature loaded. Users will silently receive broken behavior (missing routes, 404s) with no visible degradation signal.
**What to change**: After logging the critical error, either raise the exception to halt startup in production (`raise` after the log statement), or implement a health-check endpoint that returns a degraded-state flag so monitoring systems can catch it. Do not allow the app to boot into a state where Oracle routes are missing without an explicit circuit-breaker.

```python
# BEFORE (silent swallow)
except Exception as e:
    app.logger.critical(f"Oracle blueprint failed: {e}")

# AFTER (halt on production, degrade gracefully on dev)
except Exception as e:
    app.logger.critical(f"Oracle blueprint failed: {e}")
    if not app.config.get("DEBUG"):
        raise RuntimeError("Oracle Avatar blueprint is required — aborting startup.") from e
```

---

### FINDING U-2: Missing Rate Limiting on Oracle/ElevenLabs API Endpoints
**File**: `app.py` | **Lines**: 107–109 (Flask-Limiter config)
**What it is**: Global rate limit is 200 req/day per IP. The Oracle Avatar feature makes ElevenLabs TTS calls and potentially Wav2Lip inference calls per user interaction. There is no per-user or per-endpoint cap on Oracle-specific routes. A single user or a small bot cluster could exhaust the ElevenLabs API quota for the entire application.
**What to change**: Add a dedicated, tighter rate limit decorator to Oracle Avatar inference endpoints (both the TTS trigger and any video-generation route). Suggested cap: 10 requests/hour per authenticated user for TTS, 3 requests/hour for full video generation.

```python
@oracle_bp.route("/ask", methods=["POST"])
@login_required
@limiter.limit("10 per hour", key_func=lambda: current_user.id)
def oracle_ask():
    ...
```

---

### FINDING U-3: `apply_blink()` Compliance Unverifiable — LAW 2 at Risk
**File**: `avatar_server.py` (NOT PROVIDED)
**What it is**: `PIPELINE_STATE_SNAPSHOT.md` line 175 documents that `apply_blink()` caused black oval artifacts and was scheduled to be replaced with a no-op `return frame`. The actual `avatar_server.py` was not included in the audit package, so it is impossible to confirm this fix was applied.
**What to change**: `avatar_server.py` MUST be included in every future audit package. Before merge, a human reviewer must open `avatar_server.py` and verify:
1. `apply_blink()` exists as a function
2. Its body is exactly `return frame` (or equivalent no-op)
3. No other call site in the codebase calls any blink function with active logic

---

### FINDING U-4: `avatar_server.py` Entirely Absent — LAW 5 Cannot Be Verified
**File**: `avatar_server.py` (NOT PROVIDED)
**What it is**: LAW 5 designates `avatar_server.py` as the authoritative file for the Oracle Avatar feature. It must run on port 8200, implement GPU cache warming, and preserve ModelRegistry pattern. None of this can be verified from the provided audit package.
**What to change**: Block merge until `avatar_server.py` is reviewed. Add a pre-merge checklist item that requires the authoritative file to be present in any audit submission. PIPELINE_STATE_SNAPSHOT.md referencing port 8200 is not a substitute for code review.

---

### FINDING U-5: Missing Environment Variable Fallback/Validation for Critical Config
**File**: `app.py` | **Lines**: 69–72 (DATABASE_URL area)
**What it is**: `SESSION_SECRET` correctly raises on missing value in production. `DATABASE_URL` and other critical variables (ElevenLabs key, Wav2Lip model path) appear to have no equivalent guard. A missing `DATABASE_URL` will produce an obscure SQLAlchemy error at first DB call rather than a clear startup failure.
**What to change**: Add an explicit startup validation block that checks all required environment variables and raises a descriptive `EnvironmentError` before any application logic runs.

```python
REQUIRED_ENV = ["DATABASE_URL", "ELEVENLABS_API_KEY", "WAV2LIP_MODEL_PATH", "SESSION_SECRET"]
missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
if missing:
    raise EnvironmentError(f"Missing required environment variables: {missing}")
```

---

## MAJORITY FINDINGS (2 of 3 models agree)

> **Not applicable.** Only 1 model produced output. No majority threshold can be met. The section is preserved for structural integrity and to signal clearly that no cross-model corroboration exists.

*All findings in this report are single-model. None have been corroborated by a second or third model.*

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

Since all findings originate from a single model, the following are observations with lower confidence that warrant human judgment before acting on them.

---

### INSIGHT G-1: Ad Injection Filter Bypasses Request-Scope Caching Benefit
**File**: `app.py` | **Lines**: 179–206
**Observation**: The `g._active_ads` pattern stores active ads in Flask's `g` context, scoped to a single request. This is correct within a request, but if the template or filter is called multiple times per request, subsequent calls re-use `g._active_ads` correctly. However, there is no cross-request cache (e.g., Redis TTL cache), meaning every new request issues a database query for active ads.
**Assessment**: **INVESTIGATE FURTHER**. If ad changes are infrequent (likely), a short Redis/memcached TTL cache (30–60 seconds) would eliminate hundreds of DB round-trips per day. Not a blocker for merge, but a meaningful performance issue at scale. Flag for P2 backlog.

---

### INSIGHT G-2: CSRF Token Session Validation Not Confirmed in Routes
**File**: `app.py` | **Lines**: 129–133
**Observation**: CSRF tokens are generated and stored in session, but there is no evidence in the provided files that any route decorator or middleware validates the CSRF token on POST requests. If validation exists only in unshared route files, this is fine. If it is missing, every POST endpoint (including Oracle Avatar interactions) is vulnerable to CSRF.
**Assessment**: **INVESTIGATE FURTHER**. Before merge, confirm that Flask-WTF or equivalent CSRF protection is enforced on all POST routes in the Oracle blueprint. If using Flask-WTF, verify `CSRFProtect(app)` is initialized and that Oracle routes are not decorated with `@csrf.exempt` unless there is a documented justification.

---

### INSIGHT G-3: Stripe Webhook/Downtime Handling Absent from Documentation
**Files**: `STRIPE_SETUP.md`, `STRIPE_TERMINAL_SETUP.md`
**Observation**: Neither Stripe documentation file describes handling for API downtime or webhook delivery failure. If a subscription webhook fails (Stripe retries for 3 days), the system may grant or deny access incorrectly during the retry window.
**Assessment**: **IMPLEMENT** (P2). Add idempotent webhook handling with a `stripe_event_id` deduplication check against the database. Implement a pending-state model for subscriptions awaiting webhook confirmation. This is standard Stripe integration hygiene.

---

### INSIGHT G-4: No Core Frontend Files Provided — Oracle UI Entirely Unaudited
**Files**: `oracle.html`, any Oracle-specific CSS/JS (NOT PROVIDED)
**Observation**: The entire frontend layer — layout, mobile viewport behavior, loading states, error states, JS errors, and world-class visual target — could not be evaluated because no frontend files were included in the audit package.
**Assessment**: **BLOCK MERGE on frontend audit**. A feature built around a live AI avatar has its quality gate primarily on the frontend. Auditing only backend scaffolding and documentation is insufficient. Require `oracle.html`, Oracle-specific JS, and any associated CSS/SCSS to be included in Cycle 2.

---

## CONFLICTS (models disagree — your tiebreaker)

> **Not applicable.** Only one model produced output. No conflicts exist between models. If Gemini and GPT-4o had reviewed the code, conflicts would be resolved here. Re-run with all three models to surface any genuine disagreements.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> Given only one model reviewed successfully, these are areas Grok identified as implemented correctly. They carry single-model confidence only. Do not treat as fully validated.

---

### STRENGTH 1: Secrets Management
**File**: `app.py` (env var loading), `.env.example`
All secrets are loaded from environment variables. `.env.example` contains no real values. No hardcoded API keys detected in any provided file. This is correct and should not be changed.

### STRENGTH 2: Database Access via ORM
**File**: `app.py` | **Lines**: 39–40
SQLAlchemy ORM is used for database operations, eliminating direct SQL injection vectors from the ORM layer. Maintain this pattern — do not introduce raw `db.engine.execute()` or `text()` calls without parameterization.

### STRENGTH 3: SESSION_SECRET Production Guard
**File**: `app.py` | **Lines**: 47–53
The ephemeral-key-in-debug / raise-in-production pattern for `SESSION_SECRET` is correctly implemented. This is the right behavior and should be replicated for other critical environment variables (see U-5).

### STRENGTH 4: Flask-Login Integration
**File**: `app.py` | **Lines**: 103–105, 238–245
Flask-Login is initialized and a user loader is registered. The foundation for authentication is correct. Do not refactor this in the second pass.

### STRENGTH 5: Law 1 Compliance (Wav2Lip Only)
No evidence in any provided file of alternative lip-sync engines (MuseTalk, SadTalker, HeyGen) being imported, configured, or referenced for the Oracle Avatar feature.

### STRENGTH 6: Law 3 Compliance (Jessica Voice Only)
Voice ID `cgSgspJ2msm6clMCkdW9` (Jessica) is documented as the Oracle voice. No conflicting voice assignment found in Oracle-related files. The separate voice assignment in `VIDEO_PIPELINE_FIX_GOSPEL.md` is for a different feature and does not constitute a violation.

### STRENGTH 7: Law 4 Compliance (No Three.js/VR/WebGL)
No Three.js, WebXR, WebGL shader code, or DAO patterns found in any provided file. `AUDIT_PROTOCOL.md` explicitly bans WebXR, confirming architectural alignment.

### STRENGTH 8: Law 6 Compliance (Proto-P Avatar Asset)
No evidence of deviation from `oracle/assets/Proto_P_Avatar_512.png` as the current approved avatar face asset.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Confidence | Blocking? |
|-----|--------|------------|-----------|
| LAW 1: Wav2Lip only | ✅ COMPLIANT | Medium (no core code reviewed) | No |
| LAW 2: apply_blink() disabled | ⚠️ UNVERIFIABLE | None — file missing | **YES — BLOCK MERGE** |
| LAW 3: Voice = Jessica only | ✅ COMPLIANT | Medium | No |
| LAW 4: No Three.js/VR/WebGL/DAO | ✅ COMPLIANT | Medium | No |
| LAW 5: avatar_server.py authoritative | ⚠️ UNVERIFIABLE | None — file missing | **YES — BLOCK MERGE** |
| LAW 6: Proto-P avatar asset | ✅ COMPLIANT | Medium | No |

**Final Determination**: **MERGE BLOCKED on LAW 2 and LAW 5**. Both violations are due to the absence of `avatar_server.py` from the audit package, not confirmed violations. But absence of verification is not compliance — it is an open risk. The authoritative file must be reviewed before these laws can be signed off. All other laws show no evidence of violation.

---

## SECURITY CONSENSUS

> Single-model assessment. Priority order based on Grok's findings.

| Priority | Issue | Severity |
|----------|-------|----------|
| 1 | CSRF validation not confirmed on Oracle POST endpoints | HIGH |
| 2 | No per-user rate limiting on ElevenLabs/Wav2Lip inference routes | HIGH |
| 3 | Missing env var startup validation (DATABASE_URL, ELEVENLABS_API_KEY) | MEDIUM |
| 4 | Blueprint silent failure could mask broken auth enforcement | MEDIUM |
| 5 | Stripe webhook deduplication absent | LOW-MEDIUM |

No hardcoded secrets, no SQL injection vectors detected in reviewed files. Authentication foundation is present. Core security risks center on rate limiting, CSRF validation confirmation, and the unreviewed Oracle endpoint code.

---

## WORLD-CLASS GAP CONSENSUS

> Single-model assessment. Items included represent Grok's highest-confidence gaps. Normally this section requires 2+ models — treat all items here with that caveat clearly in mind.

**1. The Entire Frontend Is Unreviewed**
The Oracle Avatar is a *visual-first* feature. Its world-class claim rests on the anime-realism cyberpunk Bloomberg aesthetic, the radial glow, the animated SVG elements, and the live avatar rendering. None of that was audited. A product cannot be declared world-class when its primary experiential layer was not reviewed. This is the single largest gap in this audit cycle.

**2. No Observability Layer for AI Pipeline**
For a live AI pipeline (TTS → Wav2Lip → video stream), there is no evidence of latency tracking, inference failure alerting, or degraded-mode UX (e.g., what does the user see if Wav2Lip fails mid-session?). World-class AI products have observable pipelines with sub-second alerting on inference degradation.

**3. No Error/Loading/Empty State Specification**
The feature description mentions a live AI avatar delivering Bitcoin intelligence. What does the user see while the avatar is generating? What happens on ElevenLabs timeout? What happens if the Wav2Lip model is cold? These states were not addressed in any provided file.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Include `avatar_server.py` in audit and verify `apply_blink()` is a no-op | `avatar_server.py`:unknown | grok (unique) | LAW 2 and LAW 5 cannot be signed off without this file. Merge is blocked. |
| **P0 CRITICAL** | Include `oracle.html` and Oracle JS/CSS in audit package | `oracle.html`:all | grok (unique) | Primary feature layer entirely unreviewed. World-class claim is unverifiable. |
| **P0 CRITICAL** | Raise on blueprint registration failure in production | `app.py`:370–374 | grok (unique) | Silent failure leaves app in undefined state with no user-visible signal |
| **P1 HIGH** | Add per-user rate limiting to Oracle inference endpoints (10/hr TTS, 3/hr video) | `oracle_blueprint.py` or equivalent | grok (unique) | Single user can exhaust ElevenLabs quota for entire app |
| **P1 HIGH** | Confirm CSRF validation is enforced on all Oracle POST endpoints | Oracle blueprint routes | grok (unique) | CSRF tokens are generated but validation not confirmed — all Oracle POSTs at risk |
| **P1 HIGH** | Add startup validation block for all required environment variables | `app.py`:69–72 | grok (unique) | Missing DATABASE_URL or ELEVENLABS_API_KEY produces obscure late-stage errors |
| **P2 MEDIUM** | Implement Stripe webhook idempotency with `stripe_event_id` dedup | Stripe webhook handler | grok (unique) | Webhook retries can grant/deny access incorrectly during 3-day retry window |
| **P2 MEDIUM** | Add Redis/TTL cache for active ads query (30–60s TTL) | `app.py`:179–206 | grok (unique) | Every request issues a DB query for ads; infrequent data doesn't justify it |
| **P2 MEDIUM** | Define and implement loading/error/empty states for Oracle Avatar UI | `oracle.html` / Oracle JS | grok (unique) | World-class product requires explicit degraded-state UX for AI pipeline failures |

---

## CYCLE 1 VERDICT

**NOT READY FOR SECOND BUILD PASS IN CURRENT STATE.**

Two hard blockers prevent this:

1. **Audit package is incomplete.** `avatar_server.py` (the LAW 5 authoritative file) and all frontend files (`oracle.html`, Oracle JS/CSS) were absent. Two laws cannot be verified. The entire frontend quality gate was skipped. This is not a nitpick — for a live AI avatar feature, the avatar server and the UI are the product.

2. **Audit lost two-thirds of its models.** Gemini failed due to a leaked API key that must be rotated immediately. GPT-4o failed due to quota exhaustion. A single-model review is not sufficient confidence for a pre-merge quality gate on a complex AI pipeline feature.

**Recommended next step**: Fix the audit infrastructure (rotate Gemini key, restore GPT-4o quota), add `avatar_server.py` and all frontend files to the audit package, and re-run as **Cycle 1 Retry** with all three models. Only after a complete three-model review of the complete file set should a second build pass be commissioned.

If there is a hard deadline requiring a second pass now, the P0 items must be resolved first by a human reviewer before the second build pass begins.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/F1_AVATAR_ORACLE_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/f1-avatar-oracle_CONSENSUS_C1.md.

This is the SECOND PASS for f1-avatar-oracle.
The first build was reviewed by 1 independent AI model across 1 cycle
(2 of 3 models failed due to infrastructure issues — see CONSENSUS report).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

⚠️ CRITICAL PREREQUISITE: Before implementing anything, verify that
avatar_server.py is present in the repo and that apply_blink() is a
no-op (body: `return frame`). If it is not, halt and report — do not
proceed with the second pass until LAW 2 and LAW 5 are manually verified.

PRIORITY ACTION PLAN:

P0 CRITICAL | Verify apply_blink() is no-op in avatar_server.py | avatar_server.py | grok | LAW 2 + LAW 5 compliance — merge blocked without this
P0 CRITICAL | Add oracle.html and Oracle JS/CSS to review scope | oracle.html | grok | Primary feature layer entirely unreviewed
P0 CRITICAL | Raise RuntimeError on Oracle blueprint failure in production | app.py:370-374 | grok | Silent failure leaves app in broken state with no signal
P1 HIGH     | Add per-user rate limiting on Oracle inference endpoints | oracle blueprint routes | grok | Single user can exhaust ElevenLabs API quota
P1 HIGH     | Confirm and enforce CSRF validation on all Oracle POST routes | oracle blueprint routes | grok | CSRF tokens generated but validation not confirmed
P1 HIGH     | Add startup env var validation block for all critical variables | app.py:69-72 | grok | Missing vars produce obscure late-stage failures
P2 MEDIUM   | Implement Stripe webhook idempotency (stripe_event_id dedup) | stripe webhook handler | grok | Retry storms can corrupt subscription state
P2 MEDIUM   | Add Redis TTL cache (30-60s) for active ads query | app.py:179-206 | grok | Per-request DB query for infrequently changing data
P2 MEDIUM   | Implement loading/error/empty states for Oracle Avatar UI | oracle.html + Oracle JS | grok | World-class AI product requires explicit degraded-state UX

VALIDATED — do NOT touch (confirmed correct by audit):
- Secrets management: all secrets loaded from env vars, no hardcoded values
- SQLAlchemy ORM: do not introduce raw SQL or db.engine.execute() calls
- SESSION_SECRET production guard: ephemeral-in-debug / raise-in-production pattern is correct
- Flask-Login integration: initialization and user_loader are correct, do not refactor
- Law 1 (Wav2Lip only): no alternative lip-sync engine detected — maintain this
- Law 3 (Jessica voice only, ID: cgSgspJ2msm6clMCkdW9): confirmed, do not change
- Law 4 (No Three.js/VR/WebGL/DAO): confirmed clean, do not introduce any of these
- Law 6 (Proto-P avatar asset): oracle/assets/Proto_P_Avatar_512.png confirmed, do not swap

LAWS IN FORCE (from F1_AVATAR_ORACLE_GOSPEL.md):
- LAW 1: Wav2Lip is the ONLY approved lip-sync engine
- LAW 2: apply_blink() is permanently disabled — body must be `return frame`
- LAW 3: Voice = Jessica (ID: cgSgspJ2msm6clMCkdW9) only
- LAW 4: No Three.js, no VR, no DAO, no WebGL shaders
- LAW 5: avatar_server.py is the authoritative file (port 8200, GPU cache warming, ModelRegistry)
- LAW 6: Proto-P avatar asset = oracle/assets/Proto_P_Avatar_512.png until new asset approved

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(f1-avatar-oracle): post-audit pass — consensus improvements"