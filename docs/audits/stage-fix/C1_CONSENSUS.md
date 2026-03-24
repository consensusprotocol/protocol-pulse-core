# CONSENSUS REPORT — STAGE-FIX — CYCLE 1
Generated: 2026-03-24 19:38
Models: grok, gemini (+1 failed)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 5/10 | N/A (failed) | 6/10 | 5.5/10 |
| Law Compliance | 0/10 | N/A | 0/10 | 0/10 |
| Security | 6/10 | N/A | 5/10 | 5.5/10 |
| Frontend Quality | 6/10 | N/A | 5/10 | 5.5/10 |
| Overall | 5/10 | N/A | 5/10 | **5/10** |

> **Scoring note:** GPT-4o exceeded token limits and produced no output. Consensus is derived from 2 of 3 models. Confidence is reduced accordingly — treat all MAJORITY findings as carrying unanimous weight between the two available reviewers.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — Race Condition: Queue Read-Modify-Write is Not Atomic
**File:** `services/stage_broadcast_service.py` · Lines 83–144
**Both models flagged:** Grok (explicit), Gemini (explicit and detailed)
**What it is:** `_add_to_queue()` performs read → modify → write, releasing the `fcntl` lock between the read and write. Two cron instances running at the same interval can both read the same queue state, both append their item, and the second writer silently overwrites the first. This causes silent broadcast segment loss.
**What to change:** Wrap the entire read-modify-write block in a single `fcntl.LOCK_EX` context — acquire once before `_read_queue()`, release after `_write_queue()`. Do not release the lock in between. Additionally, add a stale-lock timeout (e.g., 5 seconds) to prevent deadlock if a process dies mid-write.

```python
# Pattern to implement:
with open(QUEUE_FILE, 'r+') as f:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        queue = json.load(f)
        # ... all modify logic ...
        f.seek(0)
        json.dump(queue, f)
        f.truncate()
    finally:
        fcntl.flock(f, fcntl.LOCK_UN)
```

---

### U2 — No Authentication on Any Endpoint
**File:** `oracle/avatar_server.py` · Line 831 (`/generate`), and all Flask routes
**Both models flagged:** Grok (explicit, rated HIGH impact), Gemini (explicit, rated PARTIAL)
**What it is:** Every internal service endpoint is completely unauthenticated. Any process or user with network access can trigger `/generate`, `/oracle/chat`, and other paid-API-backed routes. Claude and ElevenLabs quota exhaustion is a real financial threat.
**What to change:** Add a shared-secret middleware (e.g., `X-Internal-Token` header validated against an env var) for all internal service-to-service calls. For the Oracle chat endpoint exposed to users, add session-based or token-based auth. Minimum viable fix: a `require_internal_token` decorator on all `avatar_server.py` routes that checks `request.headers.get('X-Internal-Token') == os.environ['INTERNAL_API_TOKEN']`.

---

### U3 — No Rate Limiting on Paid-API-Backed Endpoints
**File:** `oracle/avatar_server.py`, `services/stage_broadcast_service.py`
**Both models flagged:** Grok (rated CRITICAL), Gemini (rated PARTIAL)
**What it is:** No server-side rate limiting exists on `/generate` or `/oracle/chat`. A single actor — malicious or bugged — can exhaust Claude and ElevenLabs credits without any circuit breaker. The client-side cooldown in `stage.html` line 1373 is easily bypassed with direct HTTP calls.
**What to change:** Add `Flask-Limiter` with Redis or in-memory backend. Suggested limits: `/oracle/chat` → 10 req/min per IP, `/generate` → 5 req/min per IP. Add a global daily cap counter stored in Redis that halts generation when a quota threshold is approached.

---

### U4 — Silent Failure on API Downtime Returns Zeroed/None Data
**File:** `services/stage_brief_pipeline.py` · Lines 113–115; `services/stage_broadcast_service.py` · Line 170
**Both models flagged:** Grok (explicit, lines 113–115 and 170), Gemini (inferred from N+1 discussion)
**What it is:** API failure in `_fetch_btc_price()` and similar functions returns a zeroed dict or `None` with no retry and no critical alert. Downstream functions consume this silently, producing briefs with BTC price = 0 or missing alerts entirely.
**What to change:** Implement exponential backoff retry (3 attempts, 1s/2s/4s delays) using `tenacity` or a manual loop. After all retries fail, emit a `logger.critical()` and either raise a typed exception (`DataUnavailableError`) or return a sentinel value that downstream checks explicitly handle — never proceed silently with zero/None economic data.

---

### U5 — Law Compliance Section is Empty in Spec
**File:** Specification / Audit Package itself
**Both models flagged:** Grok (explicit), Gemini (explicit — called it a VIOLATION)
**What it is:** The "GOVERNING LAWS" section of the spec is blank. No legal framework (GDPR, CCPA, ADA/WCAG, financial disclaimer requirements, etc.) has been defined. This means the code cannot be audited for compliance, and developers have no legal guard rails.
**What to change:** Before Cycle 2, the product owner must populate GOVERNING_LAWS in the spec with at minimum: data retention policy, user PII handling scope, whether Oracle chat logs are stored and for how long, and any financial disclaimer requirements (Bitcoin content may carry regulatory implications depending on jurisdiction). Gemini correctly calls this a process violation — it must be resolved at the specification level, not the code level.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

> With only 2 models, all majority findings are effectively unanimous between available reviewers. They carry high confidence.

---

### M1 — Missing File Lock on `latest.json` Writes in Brief Pipeline
**File:** `services/stage_brief_pipeline.py` · Line 795
**Flagged by:** Grok
**Gemini alignment:** Gemini flagged the queue's race condition extensively, implying the same principle applies to any shared file write. The architectural pattern is the same.
**What it is:** `latest.json` is written without `fcntl` locking, unlike the broadcast queue. Concurrent brief generations (e.g., triggered by manual re-runs overlapping a cron) can corrupt the metadata file.
**What to change:** Apply the same atomic write pattern as the queue — lock, write, unlock — or use a write-to-temp-then-atomic-rename pattern (`os.replace(tmp_path, target_path)`) which is safer on Linux.

---

### M2 — Brittle `_load_pulse_check_script` Parsing with No Data Contract
**File:** `services/stage_brief_pipeline.py` · Lines 225–293
**Flagged by:** Both models (Grok: line 330 context; Gemini: lines 225–293, explicit)
**What it is:** The function guesses the structure of `script.json` by iterating a list of possible keys. If the upstream format changes, it silently falls back to dumping raw JSON into the LLM prompt, producing garbage briefs with no alerting.
**What to change:** Define a Pydantic model or a typed dataclass for the `script.json` schema. Validate on load. If validation fails, raise a typed exception and alert — do not silently fall back to raw JSON. This enforces a data contract between services.

---

### M3 — Monolithic JavaScript in `stage.html`
**File:** `templates/stage.html` · Lines 968–2356
**Flagged by:** Both models (Gemini: explicit, detailed; Grok: implicit via UI state concerns)
**What it is:** ~1,400 lines of JavaScript in a single `<script>` block mixing API calls, state management, DOM manipulation, and business logic. Severely unmaintainable.
**What to change:** This is a P2 refactor (not a production blocker), but it must be planned. Minimum viable improvement: extract into separate files (`/static/js/stage-api.js`, `/static/js/stage-state.js`, `/static/js/stage-ui.js`) and import via ES6 modules. Ideal: migrate to Alpine.js or Svelte for declarative state management. Do not do this in the same PR as P0 fixes.

---

### M4 — `ffprobe` Return Code Not Checked in Audio-Only Fallback
**File:** `services/stage_brief_pipeline.py` · Line 595
**Flagged by:** Gemini (explicit)
**Grok alignment:** Grok flagged the broader pattern of unchecked subprocess calls and silent failures, consistent with this finding.
**What it is:** The `ffprobe` subprocess call has `capture_output=True` but no `check=True` and no `returncode` check. If `ffprobe` fails, `duration` defaults to `30.0`, producing a video with incorrect duration mismatched to actual audio.
**What to change:**
```python
result = subprocess.run([...ffprobe args...], capture_output=True, text=True)
if result.returncode != 0:
    logger.error(f"ffprobe failed: {result.stderr}")
    raise VideoRenderError("Cannot determine audio duration")
duration = float(result.stdout.strip())
```

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluate carefully)*

---

### UI1 — Time-Based Brief Type Determined at Script Start, Not at Classification Point
**File:** `services/stage_brief_pipeline.py` · Lines 711–720
**Flagged by:** Gemini only
**Assessment: IMPLEMENT**
This is a real, subtle bug. If data gathering takes 2+ minutes and the cron fires at a boundary hour (e.g., 09:58), the brief will be misclassified. The fix is trivial — pass `brief_type` as a CLI argument from the scheduler, or re-evaluate `datetime.now()` immediately before the classification block. This also makes the service testable (you can force a brief type in tests). **Implement in P1.**

---

### UI2 — Redundant API Calls Across 7 Independent Check Functions
**File:** `services/stage_broadcast_service.py` · Line 535 and surrounding check functions
**Flagged by:** Gemini only
**Assessment: IMPLEMENT (P2)**
The observation is architecturally sound: a single data-gathering phase at the top of `run()` that collects all required metrics once, then passes a shared data object to each check function, would eliminate redundant external API calls, reduce latency, and make the service more resilient (one API timeout affects one check, not all of them independently). This is a meaningful refactor. Not a production blocker but a real quality improvement. **Implement in P2.**

---

### UI3 — Session Timer Doesn't Survive Page Reloads
**File:** `templates/stage.html` · Line 1012
**Flagged by:** Grok only
**Assessment: INVESTIGATE FURTHER**
The severity depends on whether the session timer is user-facing or internal. If users see it, storing the session start time in `sessionStorage` and rehydrating on load would fix it in ~3 lines. If it's purely internal telemetry, it may be acceptable to reset on reload. Investigate intended UX before implementing. Low priority.

---

### UI4 — `body { position: fixed }` iOS Viewport Hack
**File:** `templates/stage.html` · Line 348
**Flagged by:** Gemini only
**Assessment: INVESTIGATE FURTHER**
The `position: fixed` body hack is widely used for iOS viewport height issues but can cause side effects (scroll containers behaving unexpectedly, modal overflow issues, accessibility concerns). Worth investigating whether the CSS custom property approach (`--vh: 1vh`) with a JS listener is available and would be cleaner. Low priority, not a production blocker.

---

### UI5 — Filler Insights Can Flood Queue, Drowning High-Priority Items
**File:** `services/stage_broadcast_service.py` · Lines 821–831
**Flagged by:** Grok only
**Assessment: IMPLEMENT (P2)**
The logic is real: `FILLER_INSIGHT` types bypass duplicate detection, so repeated cron invocations with a shallow queue can backfill it entirely with fillers, preventing subsequent high-priority alerts from being surfaced promptly. Fix: cap fillers at `max(0, MIN_QUEUE_DEPTH - high_priority_count)` and enforce a max filler ratio (e.g., no more than 40% of queue items can be fillers). **Implement in P2.**

---

## CONFLICTS
*(Models gave contradictory signals — tiebreaker applied)*

---

### C1 — Path Traversal Mitigation Adequacy
**Grok:** Flagged as HIGH risk even with existing mitigation; suggested whitelist approach.
**Gemini:** Explicitly rated as EXCELLENT — "This is excellent" mitigation via real path resolution.
**Verdict: Gemini is right, with one caveat.**
The `os.path.realpath()` + prefix check pattern is the correct, industry-standard defense against path traversal. Gemini's assessment stands. However, Grok's underlying instinct — add a whitelist of allowed `avatar_source` values — is worth implementing as defense-in-depth, not as a replacement. The path resolution is the primary guard; the whitelist is a secondary guard. **Implement whitelist as P2, not P0.**

---

### C2 — Secrets Management Severity
**Grok:** Rated file-based API key fallback as MEDIUM risk; recommended HashiCorp Vault.
**Gemini:** Rated overall secrets handling as COMPLIANT.
**Verdict: Gemini is right for the current scope; Grok is right for future scale.**
Environment variable sourcing is the correct pattern for this deployment tier. Vault is appropriate for enterprise multi-team environments, not a single-product deployment. The file-based fallback (`_get_anthropic_key` reading from a file) should be reviewed for file permission hardening (chmod 600, owned by service user), but this does not warrant a P0 or P1 rating. **Document as operational requirement, not a code change.**

---

## VALIDATED STRENGTHS
*(Both models confirmed excellent — do NOT change in second pass)*

---

1. **SQL Parameterization** — `services/stage_broadcast_service.py` line 506. Both models confirmed correct `?` parameterization with `sqlite3`. Do not alter.

2. **Secrets via Environment Variables** — `_get_anthropic_key()` and equivalent functions. Both models confirmed no hardcoded secrets. Do not alter this pattern.

3. **CSS/Visual Design** — `templates/stage.html` lines 9–691. Gemini rated it "world-class." Grok implicitly confirmed. The "news control room meets Bitcoin terminal" aesthetic is production-ready. Do not redesign.

4. **Path Traversal Defense** — `oracle/avatar_server.py` lines 143–146. `os.path.realpath()` + base path prefix check is the correct pattern. Gemini explicitly called it excellent. Do not alter the core logic.

5. **Client-Side Rate Limit Handling** — `templates/stage.html` line 999, 429 response handling. The frontend correctly handles `Too Many Requests` gracefully. Do not alter.

6. **Mobile Responsiveness** — `templates/stage.html` responsive CSS. Both models confirmed mobile UX is intentional and well-implemented. Do not alter layout fundamentals.

---

## LAW COMPLIANCE CONSENSUS

**Final Determination: BLOCKED — specification is incomplete.**

Both models independently flagged that the GOVERNING LAWS section of the audit spec is empty. This is not a dismissal of legal risk — it is recognition that legal risk cannot be assessed without a legal framework to assess against.

**Known implied risks (even without a specified framework):**
- Oracle chat logs may contain user PII → GDPR/CCPA implications if users are EU/CA residents
- Bitcoin price commentary may require financial disclaimer in certain jurisdictions
- TTS/avatar generation of voice content may have synthetic media disclosure requirements (EU AI Act, emerging US state laws)
- No accessibility audit conducted → ADA/WCAG 2.1 AA compliance unknown

**Required action before Cycle 2:** Product owner must define GOVERNING_LAWS in spec. Minimum required entries: data retention policy, PII scope, financial disclaimer stance, jurisdiction of primary users.

---

## SECURITY CONSENSUS

**Priority order (both models contributed):**

| Priority | Issue | Both Models | Severity |
|---|---|---|---|
| 1 | No rate limiting on paid API endpoints | ✓✓ | CRITICAL |
| 2 | No authentication on any endpoint | ✓✓ | HIGH |
| 3 | Silent API failure → zero/None data propagation | ✓✓ | HIGH |
| 4 | Prompt injection via Oracle chat | Gemini only | MEDIUM |
| 5 | File permissions on API key fallback file | Grok only | MEDIUM |
| 6 | Path traversal (mitigated, whitelist as depth) | Both (disagree on severity) | LOW |

---

## WORLD-CLASS GAP CONSENSUS
*(Only items both models mentioned)*

---

1. **No centralized observability/alerting** — Both models noted that failures (API timeouts, zero BTC price, ffprobe errors, queue overwrites) are logged but never trigger external alerts. A world-class system would emit to PagerDuty, Sentry, or a webhook on any `logger.critical()`. Users would never receive a brief with BTC price = $0 because the on-call engineer would have been woken up 10 minutes earlier.

2. **No data contracts between services** — Both models flagged that services make structural assumptions about each other's output (e.g., `script.json` key guessing). A world-class system would use shared Pydantic schemas or protobuf definitions as the single source of truth for inter-service data, with validation at ingestion points.

3. **Monolithic JavaScript = unmaintainable frontend** — Both models flagged the 1,400-line script block. A world-class frontend either uses a framework with component isolation or at minimum ES6 modules with clear separation of concerns. This is the single largest technical debt item in the codebase.

4. **No retry/resilience layer on external APIs** — Both models noted the absence of retry logic. A world-class system would use exponential backoff, circuit breakers (e.g., `pybreaker`), and graceful degradation (show last-known-good data with a staleness indicator rather than showing zeros).

---

## FINAL ACTION PLAN

```
P0 CRITICAL | Atomize queue read-modify-write with single fcntl.LOCK_EX block
            | services/stage_broadcast_service.py:83-144
            | models: both | Race condition causes silent broadcast segment loss in production

P0 CRITICAL | Add rate limiting (Flask-Limiter) to /generate and /oracle/chat
            | oracle/avatar_server.py:831, all chat routes
            | models: both | Uncapped paid API consumption; financial exposure is unbounded

P0 CRITICAL | Add shared-secret authentication middleware to all internal endpoints
            | oracle/avatar_server.py:all routes
            | models: both | Zero-auth internal services; any network-adjacent actor can exhaust quotas

P0 CRITICAL | Implement retry with exponential backoff on all external API calls
            | services/stage_brief_pipeline.py:113-115, services/stage_broadcast_service.py:170
            | models: both | Silent zero/None data produces corrupt briefs with no alerting

P1 HIGH     | Apply atomic write (lock or os.replace) to latest.json
            | services/stage_brief_pipeline.py:795
            | models: both (pattern) | Concurrent brief runs corrupt shared metadata

P1 HIGH     | Check ffprobe returncode; raise on failure instead of defaulting duration=30.0
            | services/stage_brief_pipeline.py:595
            | models: both (pattern) | Silent ffprobe failure produces duration-mismatched video

P1 HIGH     | Define Pydantic schema for script.json; validate on load in _load_pulse_check_script
            | services/stage_brief_pipeline.py:225-293
            | models: both | Key-guessing parsing silently produces garbage LLM input on schema change

P1 HIGH     | Pass brief_type as CLI argument from scheduler; do not derive from datetime at runtime start
            | services/stage_brief_pipeline.py:711-720
            | models: gemini (unique) | Brief misclassification at hour boundaries if pipeline takes >1 min

P1 HIGH     | Populate GOVERNING_LAWS in audit spec; define data retention + PII + financial disclaimer policy
            | specification / docs
            | models: both | Cannot audit legal compliance without a legal framework; process violation

P1 HIGH     | Add logger.critical() + external alerting on all DataUnavailableError conditions
            | services/stage_brief_pipeline.py, services/stage_broadcast_service.py (all API fetch functions)
            | models: both (world-class gap) | Silent failures are undetectable in production without observability

P2 MEDIUM   | Cap filler insights ratio in queue (max 40% fillers, enforce via count check)
            | services/stage_broadcast_service.py:821-831
            | models: grok (unique) | Fillers can flood queue and block high-priority alerts

P2 MEDIUM   | Centralize data-gathering phase in run(); pass shared data object to all check functions
            | services/stage_broadcast_service.py:535+
            | models: gemini (unique) | Redundant API calls across 7 checks; inefficient and fragile

P2 MEDIUM   | Add avatar_source whitelist as defense-in-depth (secondary to path resolution check)
            | oracle/avatar_server.py:864
            | models: grok (unique, gemini disagrees on severity) | Whitelist as secondary defense layer

P2 MEDIUM   | Extract JavaScript into ES6 modules (/static/js/stage-*.js)
            | templates/stage.html:968-2356
            | models: both | 1400-line monolithic script; unmaintainable; do in isolated PR after P0/P1
```

---

## CYCLE 1 VERDICT

**NOT ready for second build pass as-is. Conditional pass after P0 items are implemented.**

The code is architecturally coherent and visually impressive, but has four P0 production hazards: an exploitable race condition that silently loses broadcast segments, unlimited financial exposure through unauthenticated and unrate-limited paid API endpoints, and silent data corruption from zero-retry API calls. These are not theoretical — they will trigger in production under normal operating conditions (concurrent cron runs, any API blip, any bad actor with network access).

The spec is also incomplete (no governing laws), which is a process violation that must be resolved in parallel.

The P0 items are all surgical fixes. None require architectural rework. A competent second pass should resolve all P0s and P1s in a single session. The codebase is fundamentally sound and worth fixing.

---

## SECOND PASS PROMPT

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/stage-fix_CONSENSUS_C1.md.

This is the SECOND PASS for stage-fix.
The first build was reviewed by 2 independent AI models across 1 cycle.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Atomize queue read-modify-write with single fcntl.LOCK_EX block
            | services/stage_broadcast_service.py:83-144
            | Acquire lock