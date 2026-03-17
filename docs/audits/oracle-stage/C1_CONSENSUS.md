# CONSENSUS REPORT — ORACLE-STAGE — CYCLE 1
Generated: 2026-03-17 01:57
Models: grok (+2 failed — Gemini 403 PERMISSION_DENIED leaked key; GPT-4o 429 quota exhausted)

---

## SCORES

> **Note:** Only Grok-3 produced output. Gemini and GPT-4o failed at the API level before generating reviews. Scores are derived solely from Grok's assessment. Consensus column reflects single-model confidence, not triangulated agreement. All findings below carry **reduced confidence** and should be treated as a single expert review, not a true multi-model consensus. Cycle 2 should retry with repaired API credentials before treating any "Unanimous" findings as fully validated.

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | — | — | 5.5 / 10 | 5.5 / 10 ⚠️ |
| Law Compliance | — | — | 6.0 / 10 | 6.0 / 10 ⚠️ |
| Security | — | — | 4.5 / 10 | 4.5 / 10 ⚠️ |
| Frontend Quality | — | — | 6.0 / 10 | 6.0 / 10 ⚠️ |
| Backend Quality | — | — | 5.5 / 10 | 5.5 / 10 ⚠️ |
| **Overall** | — | — | **5.5 / 10** | **5.5 / 10** |

*Scores inferred from Grok's severity language ("HIGH RISK", "MODERATE", "PARTIAL", "COMPLIANT") mapped to numeric values. ⚠️ = single-model only.*

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

With only one model available, "unanimous" means Grok flagged these with HIGH RISK or as structural violations. They represent the highest-confidence issues from the available review and should be treated as mandatory.

---

**U1 — No Authentication on API Routes**
- **What:** `/api/stage/transcripts`, `/api/oracle/recent`, and related endpoints have zero authentication checks. Any unauthenticated actor can query them.
- **File/Line:** `routes.py` lines ~10803, ~9801
- **Change:** Add `@login_required` decorator (or equivalent session/token check) to every route that returns oracle, transcript, or session data. If public access is intentional, document it explicitly in the gospel and add read-only rate limiting regardless.

---

**U2 — No Rate Limiting on Any Endpoint or Client Action**
- **What:** `requestBrief()` and `requestGreet()` on the frontend, plus all backend API routes, have no rate limiting. A single client can spam external `avatar.protocolpulse.io` calls, exhausting paid API quotas and potentially DOSing the service.
- **File/Line:** `stage.html` line ~915 (client); `routes.py` lines ~10803, ~9801 (server)
- **Change:** Implement Flask-Limiter on all `/api/oracle/*` and `/api/stage/*` routes (e.g., `@limiter.limit("10/minute")`). On the client, enforce a cooldown lock on avatar request buttons — `setBusy()` exists but is insufficient alone.

---

**U3 — Silent Failures / No Error State UI**
- **What:** When `/api/oracle/ask` fails and the `/health` fallback also fails, users see "Loading…" indefinitely. Error states are logged to console but never surfaced in the UI.
- **File/Line:** `stage.html` lines ~690 (primary fetch), ~732 (fallback), ~474 (loading text), ~929 (error log)
- **Change:** Implement a visible error state: replace skeleton loaders with a message (e.g., "Oracle unavailable — retrying…") after a defined timeout (suggest 10s). The `fetchTO()` catch block must update DOM, not just `console.error`.

---

**U4 — Missing DB Index on `created_at` Sort Column**
- **What:** `OracleSession.query.order_by(created_at)` at line ~9807 has no confirmed index. At scale (1000 concurrent users, per spec), this is a full table scan on every call.
- **File/Line:** `routes.py` line ~9807; migration/model file (not shown)
- **Change:** Add `Index('ix_oracle_session_created_at', OracleSession.created_at)` to the SQLAlchemy model definition or Alembic migration. Verify all other sort/filter columns are indexed per the compliance requirement.

---

**U5 — Unvalidated/Unsanitized Transcript Content Rendered in Modal**
- **What:** Transcript data read from files is rendered in the reader modal with only basic escaping. Script tags or malicious HTML in attributes could survive the escape and execute.
- **File/Line:** `routes.py` line ~10821 (file read); `stage.html` lines ~803, ~808, ~850 (render)
- **Change:** Use a strict allowlist sanitizer (e.g., `bleach` on the backend before serving, or `DOMPurify` on the frontend before innerHTML assignment). Do not rely on manual escaping alone.

---

## MAJORITY FINDINGS (2 of 1 models agree)

*This section is structurally void — majority requires 2+ models and only 1 produced output. The findings below are elevated from Grok's MODERATE RISK category and would likely have been confirmed by additional models. Treat as high-probability real issues.*

---

**M1 — `objURL` Memory Leak on Rapid Avatar Requests**
- **What:** `URL.revokeObjectURL()` is called at line ~881 but `objURL` is not nulled/guarded if a second request fires before the first video completes. The old blob URL is orphaned.
- **File/Line:** `stage.html` lines ~869, ~881
- **Likely fix:** Guard with `if (objURL) { URL.revokeObjectURL(objURL); objURL = null; }` before any new blob assignment. Cancel in-flight fetch if `busy` is already true rather than relying on the soft busy flag.

**M2 — N+1 File Read Pattern in Transcript Endpoint**
- **What:** `/api/stage/transcripts` reads each channel directory and file sequentially in a loop. With many channels, this is an O(n) blocking I/O chain inside a synchronous Flask route.
- **File/Line:** `routes.py` lines ~10829–10844
- **Likely fix:** Use `concurrent.futures.ThreadPoolExecutor` for parallel file reads, or cache results in SQLite/memory with a TTL (since transcript files don't change per-request).

**M3 — No Pagination on Transcript/Oracle Response**
- **What:** `results` list in the transcript endpoint grows unbounded. No `limit`/`offset` parameter exists.
- **File/Line:** `routes.py` line ~10845
- **Likely fix:** Add `?limit=N&offset=M` query params; default limit 20, max 100. Return total count for frontend pagination UI.

---

## UNIQUE INSIGHTS (only Grok caught this — evaluate carefully)

Since all findings come from a single model, "unique" here means observations that are more nuanced or less obvious. These warrant careful evaluation rather than automatic implementation.

---

**UI1 — Ticker Animation Breaks on Empty/Malformed API Response**
- **Grok's observation:** The ticker duplication logic for seamless scrolling (lines ~494–512) assumes content is present. Empty responses break the animation.
- **Assessment: IMPLEMENT** — This is a real defensive programming gap. Add a guard: if the ticker container has no meaningful content after the API call, show a static fallback string rather than running an empty animation loop. Low effort, prevents visual glitch.

**UI2 — DOM Element Existence Not Checked Before Use**
- **Grok's observation:** Line ~673 assumes `avatarVid` exists in the DOM. If template structure changes, the script fails silently.
- **Assessment: IMPLEMENT** — Add `if (!avatarVid) { console.warn('avatarVid not found'); return; }` guards before DOM-dependent operations. This is defensive hygiene that prevents entire script blocks from throwing.

**UI3 — Hardcoded `AVATAR_BASE` URL Should Be Environment-Driven**
- **Grok's observation:** `AVATAR_BASE` at line ~670 is hardcoded. While not a secret, it's a config value that complicates environment switching (dev/staging/prod).
- **Assessment: IMPLEMENT** — Move to a Flask config variable injected into the template via Jinja2 (`{{ config.AVATAR_BASE }}`), sourced from environment variable. Standard twelve-factor app practice.

**UI4 — `setBusy()` Race Condition on Concurrent Button Clicks**
- **Grok's observation:** The busy flag isn't atomic. Two simultaneous clicks could both read `busy=false` before either sets `busy=true`.
- **Assessment: INVESTIGATE FURTHER** — In a browser single-threaded JS environment, true simultaneous execution of two click handlers is impossible (event loop serializes). However, rapid sequential clicks within a single event loop tick could slip through if `setBusy()` is async. Audit whether `setBusy()` awaits anything before setting the flag. If it's synchronous, this is a false positive. If async, add a synchronous pre-check.

**UI5 — Missing ARIA Labels / Accessibility**
- **Grok's observation:** No hover tooltips or ARIA labels mentioned. Premium products have accessibility features.
- **Assessment: IMPLEMENT (P2)** — Add `aria-label` to icon buttons, `role="status"` to loading regions, `aria-live="polite"` to dynamic content areas. Not blocking but required for world-class classification.

**UI6 — Responsive Layout Risk on Dense Grids**
- **Grok's observation:** Grid layouts (line ~296) and long text (line ~394) may overflow on small screens.
- **Assessment: INVESTIGATE FURTHER** — Cannot confirm without visual testing. Add to QA checklist for manual review at 375px, 390px (iPhone SE/14) and 768px (tablet). If issues found, add `min-width` constraints and text truncation with `text-overflow: ellipsis`.

---

## CONFLICTS (models disagree — your tiebreaker)

*No conflicts exist — only one model produced output. This section is structurally inapplicable for Cycle 1.*

**Meta-conflict to resolve before Cycle 2:** Gemini and GPT-4o must be operational. The leaked Gemini key must be rotated immediately (U.S. security practice: treat a leaked API key as a compromised credential — rotate, audit usage logs, check for unauthorized charges). The GPT-4o quota issue must be resolved via billing. Re-run all three models on the same code before treating the Cycle 2 consensus as fully validated.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

*With one model, "validated" means Grok assessed as COMPLIANT or explicitly positive. Do NOT change these in the second pass.*

**VS1 — ORM Usage (No Raw SQL)**
Grok confirmed: SQLAlchemy ORM is used throughout (line ~9806). No raw SQL string construction observed. SQL injection surface is correctly minimized. **Do not replace with raw queries.**

**VS2 — CSS-Only Animations (No Three.js / WebGL / Canvas)**
Grok confirmed: All animations are CSS-based (lines ~61–64, ~78–80). Spec compliance is met. **Do not introduce canvas or WebGL.**

**VS3 — Technology Stack Compliance**
Python 3.12, Flask 3.x, SQLite via SQLAlchemy — all confirmed compliant. **Do not deviate from the stack.**

**VS4 — `fetchTO()` Timeout Wrapper Exists**
A timeout mechanism exists on fetch calls (line ~908). The pattern is correct, even if the error handling downstream needs improvement. **Keep `fetchTO()` — only improve its catch branches.**

**VS5 — Loading States with Shimmer Effects**
Skeleton loaders and shimmer effects are present (line ~451). The visual loading pattern is correctly implemented. **Do not remove — only extend with error and empty states.**

**VS6 — Responsive Design Fundamentals Present**
Media queries exist (lines ~133–136, ~152–154). The foundation is correct. **Do not remove breakpoints — only audit and supplement.**

---

## LAW COMPLIANCE CONSENSUS

*(Based solely on Grok. Treat as provisional until confirmed by 3-model cycle.)*

| Requirement | Status | Determination |
|---|---|---|
| Python 3.12 / Flask 3.x / SQLAlchemy | ✅ COMPLIANT | Confirmed by code usage |
| CSS/SVG only animations (no Three.js/WebGL/Canvas) | ✅ COMPLIANT | Confirmed |
| ~1000 concurrent users / every route must handle load | ❌ **VIOLATED** | No rate limiting, no caching, blocking file I/O in routes |
| Every sort/filter column must have a DB index | ⚠️ **UNCONFIRMED** | `created_at` sort exists, index not evidenced in provided code |
| Authentication on data-exposing routes | ❌ **VIOLATED** | No auth checks on oracle/transcript endpoints |
| No hardcoded secrets | ⚠️ **PARTIAL** | No keys visible, but `AVATAR_BASE` is hardcoded config |

**Final Determination:** 2 clear violations, 2 unconfirmed/partial. Code is **not law-compliant** in its current state for production deployment.

---

## SECURITY CONSENSUS

*(Single model — elevated risk items listed in priority order)*

| Priority | Issue | Severity |
|---|---|---|
| 🔴 P0 | No authentication on data API routes | CRITICAL |
| 🔴 P0 | No rate limiting — external API quota exhaustion possible | CRITICAL |
| 🟠 P1 | Unsanitized transcript content in modal render | HIGH |
| 🟠 P1 | `AVATAR_BASE` hardcoded — should be env-driven | MEDIUM-HIGH |
| 🟡 P2 | `objURL` blob not cleaned up on overlapping requests | MEDIUM |
| 🟡 P2 | No input validation on transcript length/format | MEDIUM |

**Security posture: UNACCEPTABLE for production.** The authentication gap alone is a showstopper. Any internal data exposed by the oracle/transcript endpoints is currently public.

---

## WORLD-CLASS GAP CONSENSUS

*(Items 2+ models would have flagged — inferred from Grok's findings. Applies only where Grok's language suggests universal best-practice violations.)*

**WCG1 — No Graceful Degradation Path**
A world-class product handles total API failure visibly and gracefully. "Loading…" forever is a failure mode, not a UX. Every async region needs: loading → success → error → empty — four distinct states, all rendered.

**WCG2 — No Authentication Layer on Data Endpoints**
Every production-grade data API has authentication. This is not a nice-to-have; it is the baseline. World-class products protect their data.

**WCG3 — No Observability / Structured Error Logging**
`console.error` on the frontend and silent catches on the backend are not sufficient. World-class systems emit structured logs (with request IDs, timestamps, error codes) that feed into monitoring dashboards. There is no evidence of structured logging or error telemetry.

**WCG4 — No Accessibility (ARIA / Screen Reader Support)**
Premium data products in 2025+ have WCAG 2.1 AA compliance at minimum. No ARIA labels, no `role` attributes on dynamic regions, no keyboard navigation evidence. This is a gap relative to world-class standards.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Add @login_required / token auth to all oracle and transcript API routes
            | routes.py:~10803, ~9801 and all /api/oracle/* routes
            | models: grok (unique — but universally accepted security standard)
            | why: Unauthenticated data exposure is a production showstopper

P0 CRITICAL | Implement Flask-Limiter rate limiting on all /api/oracle/* and /api/stage/* routes
            | routes.py: all route decorators; stage.html:~915 (client cooldown)
            | models: grok
            | why: External API quota exhaustion + DOS vector; 1000-user spec requires load handling

P0 CRITICAL | Replace console.error catch blocks with DOM error state updates
            | stage.html:~474, ~732, ~929; all fetchTO() catch branches
            | models: grok
            | why: Silent failures are a correctness violation and UX failure; spec requires functional UI

P1 HIGH     | Add DB index on OracleSession.created_at (and audit all other sort columns)
            | models/oracle_session.py or Alembic migration (not shown)
            | models: grok
            | why: Full table scan at 1000 concurrent users is a compliance violation per spec

P1 HIGH     | Replace manual HTML escaping with DOMPurify (frontend) + bleach allowlist (backend)
            | stage.html:~803, ~808, ~850; routes.py:~10821
            | models: grok
            | why: XSS risk from transcript file content; allowlist is the only safe approach

P1 HIGH     | Move AVATAR_BASE and all config URLs to environment variables
            | stage.html:~670 → Flask config → Jinja2 injection
            | models: grok (UI3)
            | why: Twelve-factor compliance; enables dev/staging/prod without code changes

P1 HIGH     | Add pagination (?limit=N&offset=M) to /api/stage/transcripts and /api/oracle/recent
            | routes.py:~10845, ~9807
            | models: grok (M3)
            | why: Unbounded response size is a memory and performance risk under load

P2 MEDIUM   | Fix objURL cleanup — null guard + revoke before new blob assignment
            | stage.html:~869, ~881
            | models: grok (M1)
            | why: Memory leak on rapid avatar requests; low effort fix

P2 MEDIUM   | Parallelize transcript file reads with ThreadPoolExecutor or add TTL cache
            | routes.py:~10829-10844
            | models: grok (M2)
            | why: O(n) blocking I/O in synchronous route; degrades under concurrent load

P2 MEDIUM   | Add DOM existence guards before all direct element access
            | stage.html:~673 and all avatarVid / direct querySelector usages
            | models: grok (UI2)
            | why: Silent JS failures if template structure drifts; defensive hygiene

P2 MEDIUM   | Add empty/error fallback to ticker animation
            | stage.html:~494-512, ~78
            | models: grok (UI1)
            | why: Visual break on empty API response; low effort guard

P2 MEDIUM   | Add ARIA labels, role="status", aria-live="polite" to dynamic regions
            | stage.html: all icon buttons, loading containers, oracle output regions
            | models: grok (UI5)
            | why: WCAG 2.1 AA compliance; world-class accessibility baseline

P2 MEDIUM   | Audit setBusy() for async pre-check gap; add synchronous flag before any await
            | stage.html:~869
            | models: grok (UI4)
            | why: If setBusy is async, rapid clicks can slip through; verify and patch
```

---

## CYCLE 1 VERDICT

**NOT ready for a clean second build pass without prerequisite actions.**

The code has two P0 security/correctness violations (missing auth, missing rate limiting) that must be resolved before any other improvements are meaningful. You cannot ship an authenticated feature without authentication on its data endpoints.

**However:** The codebase is not fundamentally broken. The architecture is sound, the stack is compliant, the ORM usage is correct, and the frontend loading patterns are well-structured. This is a **maturity gap**, not a design failure. A focused second pass implementing all P0 and P1 items will bring this to a shippable state.

**Prerequisite before Cycle 2 audit:**
1. Rotate the leaked Gemini API key immediately. Audit Gemini API usage logs for unauthorized calls.
2. Resolve GPT-4o quota. Confirm billing is active before re-running.
3. Re-run all three models to get true consensus confidence on these findings.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/ORACLE_STAGE_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/oracle-stage_CONSENSUS_C1.md.

This is the SECOND PASS for oracle-stage.
The first build was reviewed by 1 independent AI model (Grok-3) across 1 cycle.
Gemini and GPT-4o failed due to API errors — treat findings as single-expert review.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add authentication checks (@login_required or token validation) to ALL
            | /api/oracle/* and /api/stage/* routes.
            | File: routes.py ~10803, ~9801 and all oracle route decorators.

P0 CRITICAL | Implement Flask-Limiter rate limiting on all oracle and stage API routes.
            | Add client-side cooldown lock in requestBrief() and requestGreet().
            | File: routes.py (all route decorators), stage.html ~915.

P0 CRITICAL | Replace all console.error-only catch blocks with DOM error state rendering.
            | Every async region must have: loading → success → error → empty states.
            | File: stage.html ~474, ~732, ~929 and all fetchTO() catch branches.

P1 HIGH     | Add SQLAlchemy Index on OracleSession.created_at.
            | Audit all other ORDER BY / filter columns and add missing indexes.
            | File: OracleSession model definition or Alembic migration.

P1 HIGH     | Replace manual HTML escaping with DOMPurify on frontend + bleach allowlist
            | sanitizer on backend for all transcript content before render.
            | File: stage.html ~803, ~808, ~850; routes.py ~10821.

P1 HIGH     | Move AVATAR_BASE and all hardcoded config URLs to environment variables.
            | Inject into template via Flask config + Jinja2. Remove from stage.html.
            | File: stage.html ~670, Flask config, .env.

P1 HIGH     | Add pagination to /api/stage/transcripts and /api/oracle/recent.
            | Support ?limit=N&offset=M, default limit 20, max 100, return total count.
            | File: routes.py ~10845, ~9807.

P2 MEDIUM   | Fix objURL memory leak — add null guard and revoke before new blob assignment.
            | File: stage.html ~869, ~881.

P2 MEDIUM   | Parallelize file reads in transcript endpoint with ThreadPoolExecutor
            | or add a TTL-based in-memory cache to avoid repeated disk I/O.
            | File: routes.py ~10829-10844.

P2 MEDIUM   | Add DOM existence guards before all direct element access (avatarVid etc.).
            | File: stage.html ~673 and all direct querySelector/getElementById calls.

P2 MEDIUM   | Add empty/error fallback text to ticker animation — guard against empty content.
            | File: stage.html ~494-512, ~78.

P2 MEDIUM   | Add ARIA labels to all icon buttons, role="status" to loading containers,
            | aria-live="polite" to dynamic oracle/transcript output regions.
            | File: stage.html (all interactive and dynamic DOM regions).

P2 MEDIUM   | Audit setBusy() — if it contains any await before setting the busy flag,
            | add a synchronous pre-check before the first await.
            | File: stage.html ~869.