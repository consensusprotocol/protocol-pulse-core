# CONSENSUS REPORT — F1-AVATAR-ORACLE — CYCLE 2
Generated: 2026-03-18 05:09
Models: Grok (+2 failed: Gemini 403 API key leaked, GPT-4o 429 quota exceeded)

---

> ⚠️ **Audit Integrity Notice:** This Cycle 2 consensus is based on a single model (Grok). The two additional models failed due to infrastructure errors (leaked API key, quota exhaustion). Confidence in findings is **reduced** — unanimous/majority thresholds are meaningless with N=1. All findings should be treated as **single-model assessments** requiring human engineering judgment before acting. A Cycle 3 re-run with functioning models is strongly recommended before merge.

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Correctness     | —      | —      | 4/10 | **4/10** ⚠️ single model |
| Law Compliance  | —      | —      | 5/10 | **5/10** ⚠️ single model |
| Security        | —      | —      | 5/10 | **5/10** ⚠️ single model |
| Frontend Quality| —      | —      | N/A  | **N/A** — no frontend code in scope |
| Backend Quality | —      | —      | 4/10 | **4/10** ⚠️ single model |
| **Overall**     | —      | —      | **4/10** | **4/10** ⚠️ LOW CONFIDENCE |

*Scores derived from Grok Cycle 2 only. Gemini and GPT-4o scores unavailable due to API failures. Do not treat these as consensus scores in the traditional sense.*

---

## UNANIMOUS FINDINGS (all available models agree — implement with high confidence given N=1 constraint)

With only one functioning model, "unanimous" means confirmed by Grok in both its Cycle 1 context (via the Grok C1 excerpt provided) and Cycle 2 output — i.e., findings that survived two passes of the same model.

---

### U-1 — Silent Blueprint Registration Failure
- **What it is:** The try/except block in `app.py` (lines 370–374) catches import failures for the Oracle Avatar blueprint and logs a critical error, but does **not** halt the application or signal degraded state. The app continues running as if the feature exists, serving 404s or broken behavior to users.
- **File/Line:** `app.py`, lines 370–374
- **What to change:** In production mode (`not app.debug`), re-raise the exception after logging, or set a module-level flag that a `/health` or `/ready` endpoint can expose. Silent degradation is unacceptable for a paid/subscribed feature. Minimum fix:
  ```python
  except ImportError as e:
      app.logger.critical(f"Oracle Avatar blueprint failed to load: {e}")
      if not app.debug:
          raise RuntimeError("Critical feature blueprint failed — aborting startup") from e
  ```

---

### U-2 — Missing Endpoint-Specific Rate Limiting on High-Cost API Calls
- **What it is:** Global rate limiting at 200 req/day/IP (`app.py`, lines 107–109) does not protect individual high-cost endpoints. ElevenLabs TTS and Oracle AI calls can exhaust third-party API quotas or incur significant cost from a single abusive client staying under the global ceiling.
- **File/Line:** `app.py`, lines 107–109 (global limiter definition); Oracle/ElevenLabs route handlers (exact lines unknown — core files missing)
- **What to change:** Apply `@limiter.limit("10 per minute; 50 per day")` (or equivalent conservative limits) as a decorator on each Oracle Avatar and ElevenLabs TTS endpoint individually. Do not rely solely on global limits for any endpoint with per-call monetary cost.

---

### U-3 — Missing Startup Validation for Oracle Avatar Environment Variables
- **What it is:** No explicit startup check exists for environment variables required by the Oracle Avatar feature (e.g., `ELEVENLABS_API_KEY`, any Oracle/AI backend key referenced in `PIPELINE_STATE_SNAPSHOT.md`). Missing keys cause silent runtime failures rather than a clear startup error.
- **File/Line:** `app.py` (startup/config block; compare pattern at lines 47–53 for `SESSION_SECRET`)
- **What to change:** Add a dedicated config validation block at startup, patterned after the existing `SESSION_SECRET` check:
  ```python
  _REQUIRED_ORACLE_VARS = ["ELEVENLABS_API_KEY"]  # extend as needed
  for _var in _REQUIRED_ORACLE_VARS:
      if not os.environ.get(_var):
          if not app.debug:
              raise RuntimeError(f"Missing required env var: {_var}")
          app.logger.warning(f"Oracle Avatar: {_var} not set — feature will degrade")
  ```

---

## MAJORITY FINDINGS (2 of 1 models agree)

*Not applicable in the mathematically strict sense with N=1. However, the following findings were raised independently in both the Cycle 1 context summary (attributed to Grok C1) and the Grok C2 output, giving them cross-pass corroboration:*

### M-1 — Missing Core Implementation Files (`avatar_server.py`, `oracle.html`)
- **What it is:** The audit package does not include the primary implementation files for the Oracle Avatar feature. Every law compliance check, correctness check, and security check for the feature's actual logic is therefore **unverifiable**.
- **Corroboration:** Flagged in C1 context and C2 output.
- **Recommendation:** Block merge until `avatar_server.py` and associated frontend files are included in audit scope. A code audit without the principal artifact is a process failure, not a technical finding — it means the audit has not actually happened for the core feature.

---

## UNIQUE INSIGHTS (only flagged once — evaluate carefully)

### I-1 — Path Traversal Protection in Static File Serving May Be Insufficient
- **Raised by:** Grok C2
- **What it is:** Custom static routes (`/a/<path:fn>`, `/v3/<path:fn>` in `app.py`, lines 420–452) include a `startswith` path traversal check, but no file type allowlist or response size cap. A valid in-tree path to a large binary or sensitive non-web file could be served.
- **Assessment: Investigate further.** The `startswith` check prevents directory traversal. The risk of large-file serving or MIME-type abuse is real but depends on what files exist under `_STATIC_ROOT`. Before dismissing: confirm no credentials, SQLite databases, `.env` files, or large assets are stored within the static root tree. If yes — add an extension allowlist (`{'.js', '.css', '.png', '.woff2', ...}`). If the static root is tightly controlled, risk is low.
- **Provisional recommendation:** Add an explicit extension allowlist as a low-cost hardening measure. It costs ~5 lines and eliminates the risk entirely.

### I-2 — N+1 Query Risk in Ad Injection Filter
- **Raised by:** Grok C1 context (noted but not escalated in C2)
- **What it is:** `app.py`'s ad injection filter (lines 179–206) queries for active ads using `g._active_ads` as a per-request cache. This is correct for a single request but provides no cross-request caching. Under load, every request hitting an ad-bearing page fires a DB query.
- **Assessment: Investigate further — low urgency for this feature specifically, but worth a ticket.** This is an existing infrastructure issue, not introduced by `f1-avatar-oracle`. Do not block this feature on it, but file a separate maintenance issue. A short TTL in-memory cache (e.g., 30 seconds, `cachetools.TTLCache`) would resolve it cleanly.

### I-3 — Race Condition Risk on CSRF Session Token
- **Raised by:** Grok C1 context
- **What it is:** Session-based CSRF token handling (`app.py`, lines 129–133) could theoretically have concurrent-request race conditions if Flask's session is not locked.
- **Assessment: Skip / low confidence.** Flask sessions are cookie-based and per-client by default. Concurrent requests from the same client on the same session are an edge case Flask does not natively serialize, but CSRF tokens are read-heavy and typically set once. This is a theoretical concern without a demonstrated exploit path. Monitor but do not block merge.

---

## CONFLICTS (models disagree — tiebreaker)

*With N=1, no inter-model conflicts exist. The sole recorded conflict is intra-report: Grok C1 context (attributed to "GPT-4o" in the C1 header but presenting as Grok analysis) marks some findings as acceptable, while Grok C2 escalates them to P0. Grok C2 is more recent and more conservative — defer to C2 escalation on all shared findings.*

*If Gemini and GPT-4o had been available, conflict resolution would have been the primary value of this section. Their absence is the primary reason to demand a Cycle 3 re-run.*

---

## VALIDATED STRENGTHS (confirmed excellent — do NOT alter in second pass)

Based on what was reviewable in the provided files:

1. **`SESSION_SECRET` Handling (`app.py`, lines 47–53):** Correctly generates an ephemeral key in debug mode and raises a hard error in production if unset. This is the exact pattern the Oracle Avatar env var validation should replicate.
2. **Path Traversal Check in Static Serving (`app.py`, lines 420–452):** The `startswith(_STATIC_ROOT)` guard is correctly implemented and present. Do not remove it while adding extension allowlisting.
3. **Global Rate Limiting Infrastructure (`app.py`, lines 107–109):** The limiter is correctly instantiated and applied globally. The gap is granularity, not the existence of the system — do not replace it, augment it.
4. **Critical-level Logging on Blueprint Failure:** The log call itself is correct. The fix is additive (raise after log), not a replacement of the log.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Basis |
|-----|--------|-------|
| LAW 5 — Port 8200, GPU cache warming, ModelRegistry pattern | ❌ **UNVERIFIABLE** | `avatar_server.py` absent from audit package. Cannot confirm compliance. |
| General blueprint registration pattern | ⚠️ **PARTIAL** | Blueprint structure present in `app.py` but silent failure mode violates operational law of production robustness. |
| Environment variable management law | ⚠️ **PARTIAL** | Pattern exists for `SESSION_SECRET` but not extended to Oracle-specific vars. |
| Rate limiting law (if defined) | ⚠️ **PARTIAL** | Global limit present; endpoint-specific limits absent for high-cost routes. |

**Final Determination:** Law compliance **cannot be certified** until `avatar_server.py` is reviewed. Treat as non-compliant pending that review. Do not merge.

---

## SECURITY CONSENSUS

Priority order (single-model, treat as provisional):

| Priority | Issue | Severity |
|----------|-------|----------|
| 1 | Missing endpoint-specific rate limits on ElevenLabs/Oracle API calls | **HIGH** — direct financial and quota abuse vector |
| 2 | Missing startup validation for API keys | **MEDIUM** — keys absent = feature broken or insecure degradation |
| 3 | Static file serving lacks extension allowlist | **LOW-MEDIUM** — contingent on static root contents |
| 4 | CSRF session race condition | **LOW** — theoretical, no demonstrated path |

No SQL injection, XSS, or authentication bypass findings were raised — but this assessment is limited by the absence of `avatar_server.py` and frontend templates. The true security surface of this feature is **not yet audited**.

---

## WORLD-CLASS GAP CONSENSUS

*Only items mentioned by 2+ models qualify. With N=1, this section reports the single model's observations, flagged explicitly as unconfirmed by independent review.*

> ⚠️ The following items were raised by Grok across Cycle 1 and Cycle 2 (two-pass corroboration from same model — not independent):

1. **Missing core implementation files in audit scope.** A world-class AI product audit must include the actual AI feature implementation. The absence of `avatar_server.py` means the avatar model integration, response handling, error states, and latency characteristics have never been reviewed. This is the single largest gap between this audit and a world-class audit.

2. **No resilience design for third-party AI/TTS service outages.** Stripe setup docs and the feature design show no documented fallback for ElevenLabs unavailability (circuit breaker, degraded text-only mode, queue-and-retry). A world-class live AI avatar product degrades gracefully when upstream APIs fail — it does not return a 500 or hang.

*Items that would have required 2 independent models to confirm but only appeared once: health-check endpoint design, GPU cache warming verification, streaming response backpressure handling.*

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Re-raise blueprint import exception in production; do not silently continue | `app.py:370-374` | Grok (C1+C2) | Feature is invisible-dead without this; users get broken experience with no operator alert |
| **P0 CRITICAL** | Add endpoint-specific rate limits to Oracle/ElevenLabs routes | `app.py:107-109` + Oracle route handlers | Grok (C1+C2) | Direct financial abuse vector; global limit insufficient for per-call cost endpoints |
| **P0 CRITICAL** | Add startup env var validation for `ELEVENLABS_API_KEY` and all Oracle dependencies | `app.py` config block | Grok (C2) | Silent runtime failure on missing keys is a correctness and security failure |
| **P0 CRITICAL** | Obtain and include `avatar_server.py` in audit scope; re-run audit | `avatar_server.py` (missing) | Grok (C1+C2) | Core feature logic has never been audited; LAW 5 compliance unverifiable; merge is premature |
| **P1 HIGH** | Add file extension allowlist to custom static file serving routes | `app.py:420-452` | Grok (C2) | Low-cost hardening; eliminates file-type abuse risk entirely |
| **P1 HIGH** | Document and implement ElevenLabs/Oracle API outage fallback (degraded text mode or circuit breaker) | Oracle feature handler (missing file) | Grok (C1+C2) | World-class live AI product requirement; currently no resilience design documented |
| **P2 MEDIUM** | Add structured logging around Oracle Avatar blueprint init and first-request lifecycle | `app.py` + `avatar_server.py` | Grok (C2) | Improves debuggability and monitoring in production |
| **P2 MEDIUM** | Investigate and optionally add TTL cache for ad injection DB query | `app.py:179-206` | Grok (C1) | N+1 query risk under load; not Oracle-specific but worth a maintenance ticket |

---

## CYCLE 2 VERDICT

**❌ NOT PRODUCTION READY.**

**Confidence in this verdict: MODERATE** (limited by N=1 model due to infrastructure failures).

### Absolute Final Blockers:

1. **`avatar_server.py` has never been audited.** The core feature implementation is outside the scope of both cycles. This alone is sufficient to block merge — you cannot ship code that no reviewer has read.

2. **Silent blueprint registration failure** creates a class of production incidents that are invisible to operators and broken for users simultaneously. This is a P0 defect.

3. **No endpoint-specific rate limiting** on AI/TTS API calls exposes the operator to unbounded third-party API costs from a single abusive session.

### Recommended Path to Merge:
1. Fix P0 items (U-1, U-2, U-3 above)
2. Submit `avatar_server.py` and any frontend templates to audit scope
3. Trigger **Cycle 3** with all three models functional (resolve Gemini key leak, resolve GPT-4o quota)
4. Only after Cycle 3 returns ≥ 7/10 overall with no P0 findings: proceed to merge

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/F1_AVATAR_ORACLE_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/f1-avatar-oracle_CONSENSUS_C2.md.

This is the FINAL PASS for f1-avatar-oracle.
The first build was reviewed by 1 independent AI model across 2 cycles
(2 additional models failed due to API infrastructure errors — Gemini
key leaked, GPT-4o quota exceeded). Implement every P0 and P1 item from
the consensus. Use judgment on P2.

⚠️  AUDIT INTEGRITY NOTE: avatar_server.py was NOT present in the audit
package. Do not modify it blindly — surface it for human review first.
All fixes below are scoped to app.py and supporting infrastructure unless
otherwise noted.

PRIORITY ACTION PLAN:

P0 CRITICAL | Re-raise blueprint import exception in production | app.py:370-374
  - Wrap existing log with: if not app.debug: raise RuntimeError(...) from e
  - Do NOT remove the log call — add the raise after it

P0 CRITICAL | Add endpoint-specific rate limits to Oracle/ElevenLabs routes | app.py:107-109 + Oracle route handlers
  - Apply @limiter.limit("10 per minute; 50 per day") to each Oracle Avatar
    and ElevenLabs TTS endpoint individually
  - Do not remove the global limit — this is additive

P0 CRITICAL | Add startup env var validation for Oracle dependencies | app.py config block
  - Pattern after existing SESSION_SECRET check (lines 47-53)
  - Required vars at minimum: ELEVENLABS_API_KEY
  - In production: raise RuntimeError if missing
  - In debug: log warning and continue

P0 CRITICAL | Surface avatar_server.py for human review | avatar_server.py (missing from audit)
  - Do not auto-modify this file
  - Add a TODO comment in app.py blueprint registration block noting
    that avatar_server.py requires independent audit before production deploy

P1 HIGH | Add file extension allowlist to static file serving routes | app.py:420-452
  - Define: ALLOWED_STATIC_EXTENSIONS = {'.js', '.css', '.png', '.jpg',
    '.svg', '.woff', '.woff2', '.ico', '.map', '.webp'}
  - After path traversal check, add:
    if pathlib.Path(safe_p).suffix.lower() not in ALLOWED_STATIC_EXTENSIONS:
        abort(403)

P1 HIGH | Document ElevenLabs/Oracle outage fallback | Oracle feature handler
  - Add a try/except around ElevenLabs API calls
  - On failure: return degraded text-only response with HTTP 200 +
    header X-Oracle-Mode: degraded
  - Log the failure with error level including status code from upstream

P2 MEDIUM | Add structured logging for Oracle Avatar blueprint lifecycle | app.py + avatar_server.py
  - Log blueprint registration success with INFO level
  - Log first successful Oracle request with INFO level
  - Log any ElevenLabs API errors with ERROR level including upstream response

P2 MEDIUM | File maintenance ticket for ad injection N+1 query | app.py:179-206
  - Do NOT fix this in this pass — it is not Oracle-specific
  - Add a # TODO(maintenance): add TTL cache for _active_ads query comment

VALIDATED (do NOT touch — all available models confirmed excellent):
  - SESSION_SECRET handling (app.py:47-53) — correct pattern, do not alter
  - Path traversal startswith() guard in static serving (app.py:420-452) — keep it, add to it
  - Global rate limiter instantiation (app.py:107-109) — keep it, augment with endpoint limits
  - Critical-level log on blueprint failure (app.py:370-374) — keep log, add raise after it

After implementing all P0 and P1 items:
  1. Run: bash regression_test.sh
     Expected: zero FAILs
  2. Manually verify: curl -X GET /health returns 200 with oracle_avatar: ok
     (or equivalent health signal — implement if missing)
  3. Manually verify: app fails fast on startup if ELEVENLABS_API_KEY is unset in prod mode
  4. git add -A && git commit -m "feat(f1-avatar-oracle): post-audit pass — consensus improvements C2"
  5. git push origin feature/f1-avatar-oracle

NOTE: A Cycle 3 audit is REQUIRED before merge. Gemini and GPT-4o must be
functional for that run. This pass addresses known P0/P1 items but does not
substitute for independent multi-model review of avatar_server.py.
```

---

# WINNER DETERMINATION

# WINNER: **Grok** — Grok demonstrated the highest-quality analysis across both cycles by correctly identifying the silent blueprint registration failure (U-1) that survived cross-cycle validation, providing specific line-number-anchored findings with concrete remediation steps, and maintaining internal consistency between its Cycle 1 flags and Cycle 2 confirmations. While the audit was severely compromised by N=1 conditions (Gemini API key leak, GPT-4o quota exhaustion), Grok's work was the only output substantive enough to evaluate against all four criteria, and its findings proved durable enough to anchor the consensus report's unanimous findings section.

---

# FINAL SECOND-PASS PRIORITY LIST
*Definitive ordered implementation queue based on cross-cycle survival, severity, and confidence. All items are single-model validated — apply engineering judgment before merge. Cycle 3 re-run strongly recommended.*

---

## 🔴 P0 — MERGE BLOCKERS (fix before any merge attempt)

### P0-1 — Silent Blueprint Registration Failure
- **File:** `app.py`, lines 370–374
- **Finding:** Try/except swallows import failures for the Oracle Avatar blueprint. App boots successfully while the feature is entirely absent, producing silent 404s with no user-facing or ops-facing signal.
- **Implement:** In production environments, replace silent log with a hard raise. Add a `/health` or `/readiness` endpoint that explicitly asserts blueprint registration state. If the blueprint is absent, the health check must return non-200 so load balancers and orchestrators can gate traffic.

```python
# BEFORE (dangerous)
try:
    from oracle_avatar import bp as oracle_bp
    app.register_blueprint(oracle_bp)
except Exception as e:
    app.logger.critical(f"Oracle blueprint failed: {e}")

# AFTER (safe)
try:
    from oracle_avatar import bp as oracle_bp
    app.register_blueprint(oracle_bp)
except Exception as e:
    app.logger.critical(f"Oracle blueprint failed: {e}")
    if not app.config.get("TESTING"):
        raise RuntimeError(f"Critical blueprint load failure: {e}") from e
```

---

### P0-2 — Leaked API Key in Gemini Infrastructure
- **Finding:** Gemini's Cycle 2 participation failed with a 403 attributed to a leaked API key. This is not an audit artifact — a credentials leak occurred in the audit pipeline itself, which shares infrastructure with the feature branch environment.
- **Implement:** Immediately rotate all API keys in the affected environment. Audit git history, CI logs, and environment variable dumps for key exposure. Add pre-commit hooks and CI secret scanning (e.g., `truffleHog`, `gitleaks`) before this branch touches main. This is a security incident, not just a configuration error.

---

## 🟠 P1 — HIGH SEVERITY (implement before production traffic)

### P1-1 — Insufficient Rate Limiting on High-Cost API Endpoints
- **File:** `app.py`, lines 107–109
- **Finding:** Global rate limit of 200 requests/day/IP applies uniformly. Oracle Avatar endpoints that proxy to ElevenLabs or similar paid APIs have no endpoint-specific throttling. A single motivated user can exhaust API quota or generate significant cost before the global limit triggers.
- **Implement:** Apply per-endpoint rate limits using Flask-Limiter's `@limiter.limit()` decorator on all Oracle/ElevenLabs proxy routes. Set limits based on per-call cost, not global traffic assumptions. Add spend-based circuit breakers if the API provider exposes usage webhooks.

```python
@bp.route("/oracle/speak", methods=["POST"])
@limiter.limit("10 per hour; 50 per day")
def oracle_speak():
    ...
```

---

### P1-2 — Quota Exhaustion Risk in Audit Pipeline (GPT-4o 429)
- **Finding:** GPT-4o failed with 429 during Cycle 2. If the same OpenAI credentials are used in the feature's production Oracle path, quota exhaustion is a live production risk, not just an audit infrastructure problem.
- **Implement:** Confirm whether feature production calls share credentials with CI/audit tooling. If yes, separate them immediately. Implement exponential backoff with jitter on all OpenAI API calls. Add fallback behavior (graceful degradation message, cached response, or alternative model) when 429s occur.

---

## 🟡 P2 — MEDIUM SEVERITY (implement before GA, acceptable for initial merge with tracking ticket)

### P2-1 — CSRF Session Race Condition Risk
- **File:** `app.py`, lines 129–133
- **Finding:** CSRF token handling via Flask session lacks explicit locking. Under concurrent requests (realistic for a real-time avatar feature), simultaneous session reads/writes could produce token mismatch errors or, in degenerate cases, token collision.
- **Implement:** Audit whether Flask's session backend is thread-safe for your deployment configuration (server-side sessions vs. signed cookies). If using server-side sessions with a shared store (Redis, DB), confirm atomic read-modify-write on token generation. Add integration tests simulating concurrent session access.

---

### P2-2 — Audit Integrity: Single-Model Consensus
- **Finding:** This entire audit's consensus is N=1. Findings that would normally require unanimous agreement from three models are backed by a single model's two passes — which is self-reinforcing, not independently validated.
- **Implement:** Schedule and complete Cycle 3 with all three models operational before treating any finding above P1 as definitively scoped. P0 items are severe enough to act on regardless, but P1 and P2 scoping and severity ratings must be re-validated with a full three-model consensus run.

---

## 🔵 P3 — LOW SEVERITY / HOUSEKEEPING (backlog acceptable)

### P3-1 — `_KEY_CACHE` NameError Status Unverified
- **File:** Referenced in `PIPELINE_STATE_SNAPSHOT.md`, line 278
- **Finding:** Grok flagged a previously reported `NameError` for `_KEY_CACHE` as "fixed" but the fix was not present in audited code artifacts. Cannot confirm resolution without the implementation file.
- **Implement:** Add `_KEY_CACHE` initialization to the explicit pre-merge checklist. Require the implementing engineer to confirm the fix is present in the branch and add a regression test that would catch re-introduction.

---

### P3-2 — Ad Injection Filter Query Pattern (`app.py`, lines 179–206)
- **Finding:** Grok identified a potential N+1 query pattern in the ad injection filter. Full analysis was truncated in the Cycle 1 output — scope is unconfirmed.
- **Implement:** Engineering to review the ad injection filter loop for ORM query calls inside iteration. If confirmed N+1, batch the query before the loop. Flag for Cycle 3 full review.

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Owner | Gate |
|----------|------|-------|------|
| P0-1 | Silent blueprint failure fix + health endpoint | Backend | Before any merge |
| P0-2 | Rotate leaked keys + add secret scanning | SecOps | Immediate, parallel |
| P1-1 | Per-endpoint rate limiting on Oracle routes | Backend | Before prod traffic |
| P1-2 | Separate prod/CI credentials + add 429 fallback | Backend + Infra | Before prod traffic |
| P2-1 | CSRF session concurrency audit | Backend | Before GA |
| P2-2 | Cycle 3 re-run with all 3 models | Audit | Before GA |
| P3-1 | Confirm `_KEY_CACHE` fix + regression test | Backend | Backlog |
| P3-2 | Ad injection N+1 review | Backend | Backlog / Cycle 3 |

---

*Confidence: LOW-MEDIUM. All findings require human engineering review. Do not treat this as a passing audit. Cycle 3 is mandatory before merge.*