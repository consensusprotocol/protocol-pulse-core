# CONSENSUS REPORT — X-SPACES-PIPELINE — CYCLE 2
Generated: 2026-03-18 04:19
Models: grok, gemini (+1 failed — GPT-4o: insufficient_quota)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | UNVERIFIABLE | N/A (failed) | UNVERIFIABLE | UNVERIFIABLE |
| Law Compliance | UNVERIFIABLE | N/A (failed) | UNVERIFIABLE | UNVERIFIABLE |
| Security | UNVERIFIABLE | N/A (failed) | UNVERIFIABLE | UNVERIFIABLE |
| Frontend Quality | UNVERIFIABLE | N/A (failed) | UNVERIFIABLE | UNVERIFIABLE |
| Backend Quality | UNVERIFIABLE | N/A (failed) | UNVERIFIABLE | UNVERIFIABLE |
| World-Class Gap | UNVERIFIABLE | N/A (failed) | PARTIAL | UNVERIFIABLE |

**Score Note:** Gemini downgraded its own World-Class Gap score from PARTIAL (Cycle 1) to UNVERIFIABLE this cycle, citing that the prerequisite for any assessment has not been met across two full cycles. Grok maintained PARTIAL, reflecting its continued willingness to apply conceptual analysis despite the absence of code. The consensus adopts Gemini's stricter position: UNVERIFIABLE. Two cycles have elapsed. The process failure is now confirmed systemic, not transient.

---

## UNANIMOUS FINDINGS
*(Both available models agree — implement unconditionally)*

### U-1 — THE AUDIT PACKAGE CONTAINS NO CODE — EITHER CYCLE
**What it is:** The `THE CODE` section of the audit dispatch package has been empty in both Cycle 1 and Cycle 2. The placeholder text `(No code files found — run after Claude Code session completes)` was never replaced with actual source. This is confirmed by both Gemini and Grok independently, across both review cycles. This is no longer a one-off failure — it is a confirmed systemic break in the audit pipeline tooling.

**Which file/line:** The CI/CD or tooling script responsible for generating the audit package and populating it with source code from the Claude Code session. Likely a shell or Python script in a `.github/workflows/` directory, a `Makefile`, or a bespoke audit dispatch script.

**What to change:**
1. Add a pre-flight guard that reads the `THE CODE` section of the generated audit document before dispatching it to any AI model.
2. If the section is empty or still contains the placeholder string, the pipeline must `exit 1` (hard abort) and fire an alert to the engineering team via Slack or equivalent.
3. Do not retry until the root cause (the Claude Code session not completing or not being waited on) is resolved.
4. Example guard pseudocode:
```python
if "(No code files found" in audit_package_text or len(code_section.strip()) < 100:
    send_alert("AUDIT ABORTED: Code section is empty. Fix Claude Code session handoff.")
    sys.exit(1)
```

**Confidence:** MAXIMUM. Both models flagged this independently in Cycle 1. Both confirmed it persists in Cycle 2. This is the single highest-priority item in this entire report.

---

### U-2 — RATE LIMITING ON PAID API ENDPOINTS IS MANDATORY
**What it is:** Any HTTP endpoint that triggers the x-spaces-pipeline — which in turn calls metered, paid external APIs (ElevenLabs TTS, HeyGen avatar generation, Wav2Lip processing) — must enforce strict per-user rate limiting. Without it, a single malicious or careless user can exhaust API credits for the entire platform in minutes, causing both financial loss and a complete denial of service for all ~1000 concurrent users.

**Which file/line:** Speculative, as no code was provided. Most likely: `app/routes/spaces.py` or equivalent route handler file where the pipeline is initiated.

**What to change:**
1. Implement per-user rate limiting using a token bucket or sliding window algorithm, backed by Redis (or equivalent fast store).
2. Enforce limits at the route level using a decorator (e.g., Flask-Limiter or a custom middleware) before any external API call is made.
3. Return HTTP 429 with a `Retry-After` header when the limit is exceeded.
4. Set conservative initial limits (e.g., 5 pipeline jobs per user per hour) and tune based on observed usage.
5. Separately, implement a global circuit breaker that halts all pipeline initiations if aggregate API spend crosses a configurable daily threshold.

**Confidence:** MAXIMUM. Both models flagged this independently across both cycles. It is the most critical conceptual risk for the feature itself once code is available.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

In this cycle, with only 2 models available (GPT-4o failed), every finding that both models agree on is already classified as Unanimous. There are no findings that fall strictly into a "majority but not unanimous" category given the 2-model constraint. The following items were raised by both models and are thus treated at unanimous confidence, but are listed here separately because they are secondary to U-1 and U-2:

### M-1 — PIPELINE STATE MACHINE / JOB TRACKING
**What it is:** The x-spaces-pipeline is a multi-step asynchronous process (e.g., download → transcribe → TTS → lip-sync → deliver). Both models independently identified that there must be a persistent state machine in the database tracking each job through its lifecycle. Without it, failures at any step are silent, unrecoverable, and invisible to the user.

**Which file/line:** Speculative — `app/services/pipeline_manager.py` or equivalent.

**What to change:** Design a `PipelineJob` database model with at minimum the following states: `PENDING`, `DOWNLOADING`, `TRANSCRIBING`, `SYNTHESIZING`, `LIP_SYNCING`, `COMPLETE`, `FAILED`. Each state transition must be atomic. Failed jobs must record the step at which they failed and the error message, enabling both user-facing status display and engineering debugging. Implement retry logic with exponential backoff for transient failures (e.g., API timeouts).

### M-2 — N+1 QUERY PREVENTION UNDER CONCURRENT LOAD
**What it is:** Both models flagged that any list or dashboard view of pipeline jobs risks N+1 query patterns in SQLAlchemy, which will collapse database performance at ~1000 concurrent users.

**Which file/line:** Speculative — any SQLAlchemy query in list/dashboard route handlers.

**What to change:** Audit all SQLAlchemy queries that return collections of `PipelineJob` records. Ensure related data (user metadata, associated media records) is fetched with `joinedload()` or `selectinload()` rather than defaulting to lazy loading. Add a query analysis step to the CI pipeline (e.g., using SQLAlchemy's event system to log query counts per request in staging).

### M-3 — API TIMEOUT AND FAILURE HANDLING FOR ALL EXTERNAL CALLS
**What it is:** Both models identified that ElevenLabs, HeyGen, and Wav2Lip are external failure points. Any of them can be slow (30+ seconds), rate-limited by the provider, or fully unavailable. Without explicit timeout configuration and failure handling, the Flask worker threads will hang indefinitely, exhausting the worker pool.

**Which file/line:** Speculative — all service wrapper files for external API calls.

**What to change:** Set explicit timeouts (e.g., `requests.post(..., timeout=30)`) on every outbound HTTP call. Wrap all external calls in try/except blocks that catch `requests.Timeout` and `requests.ConnectionError` explicitly. On failure, transition the `PipelineJob` state to `FAILED` with an actionable error message, and surface this status to the user. Do not let exceptions propagate silently.

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluate carefully)*

### UI-1 (Grok only) — SCALABILITY INFRASTRUCTURE: QUEUE SYSTEM FOR HEAVY PROCESSING
**Grok's observation:** The pipeline involves computationally expensive operations (TTS synthesis, Wav2Lip lip-sync video generation). Grok specifically flagged that the code must be checked for a proper async task queue (e.g., Celery with Redis) to offload these tasks from the main Flask application process, and that workers must be horizontally scalable.

**Assessment: IMPLEMENT.** This is a high-value architectural concern that Gemini did not explicitly surface in Cycle 2 (though it was implicit in pipeline state management discussions). Processing audio and video synchronously in a Flask request/response cycle is not viable at any meaningful scale. A Celery + Redis (or equivalent: RQ, Dramatiq, or cloud-native queues like SQS) architecture is non-negotiable for production. This must be verified when code becomes available.

### UI-2 (Grok only) — REAL-TIME COST MONITORING AND ALERTING FOR API USAGE
**Grok's observation:** Beyond rate limiting per user, Grok flagged the need for aggregate real-time cost monitoring: logging per-user API credit consumption and alerting administrators when thresholds are breached, to prevent unexpected billing overruns.

**Assessment: IMPLEMENT.** This is distinct from and complementary to per-user rate limiting (U-2). Rate limiting prevents abuse. Cost monitoring provides financial observability. Both are needed. Implement a lightweight cost-tracking layer: log estimated cost per API call (ElevenLabs charges per character, HeyGen per second of video) to a metrics store (e.g., Prometheus, Datadog, or even a simple database table). Create an admin dashboard widget and an automated alert (e.g., email/Slack) if daily spend exceeds a configurable threshold.

### UI-3 (Grok only) — ASYNCHRONOUS USER FEEDBACK FOR LONG-RUNNING JOBS
**Grok's observation:** Grok emphasized that for pipeline jobs that may take minutes, the system must provide real-time progress updates to the user (e.g., via WebSockets or polling), or users will retry, compounding load.

**Assessment: IMPLEMENT.** This is a UX correctness issue with direct operational consequences. A user who sees no feedback after clicking "Generate" will click again, potentially spawning duplicate jobs and multiplying API costs. The state machine (M-1) is the backend prerequisite; the frontend must poll or subscribe to job status updates and render progress clearly. A simple polling endpoint (`GET /api/v1/pipeline/jobs/{job_id}/status`) returning the current state machine state is the minimum viable implementation.

### UI-4 (Gemini only) — SECOND CYCLE FAILURE ELEVATES SEVERITY: THIS IS NOW CONFIRMED SYSTEMIC
**Gemini's observation:** Gemini uniquely and explicitly called out that the persistence of the code-absent audit package across two cycles is a qualitatively different problem than a single transient glitch. It highlighted the direct financial waste (five or more expensive AI API calls across two cycles analyzing nothing) and argued this is evidence of a disconnected or broken `Claude Code session` handoff, not a random failure.

**Assessment: IMPLEMENT (process fix).** Gemini's framing is correct and important. The upgrade in severity — from "one-time error" to "confirmed systemic break" — has real implications for how urgently the tooling fix is treated. This should be escalated beyond the engineering team that owns the x-spaces-pipeline to whoever owns the audit infrastructure. It also means any future audit cycle dispatched before the tooling is fixed should be considered invalid and not acted upon.

---

## CONFLICTS
*(Models gave contradictory recommendations — tiebreaker ruling)*

### C-1 — World-Class Gap Score: PARTIAL (Grok) vs. UNVERIFIABLE (Gemini)
**Grok's position:** Maintained PARTIAL, arguing that conceptual analysis across two cycles still constitutes meaningful partial assessment even without code.

**Gemini's position:** Downgraded from PARTIAL to UNVERIFIABLE, arguing that after two failed cycles the prerequisite for any score has not been met and generosity is no longer warranted.

**Ruling: Gemini is correct.** A score of PARTIAL implies that something real was partially assessed. In the absence of any code across two cycles, no actual assessment has occurred — only speculation against a specification. Maintaining PARTIAL is an optimistic fiction that could create false confidence. UNVERIFIABLE is the honest and operationally correct designation. It also correctly signals urgency: the score cannot improve until the process is fixed.

**No other genuine conflicts exist between the two models.** Their analyses were largely convergent, which is expected given that both were analyzing the same empty audit package against the same specification. Convergence in this context reflects shared rationality, not groupthink.

---

## VALIDATED STRENGTHS
*(All available models agree this is already excellent)*

**None can be validated.** With zero lines of source code reviewed across two cycles, it is impossible to identify any aspect of the implementation as confirmed strong. Declaring any area "excellent" without seeing it would be fabrication.

This section will remain empty until a valid audit with actual code is completed.

---

## LAW COMPLIANCE CONSENSUS

**Final Determination: UNVERIFIABLE AND UNSPECIFIABLE.**

Both models noted that the `GOVERNING LAWS` section of the specification was left empty by the product or legal team. This is a dual failure:

1. **No laws were specified** for the feature, meaning no compliance targets exist.
2. **No code was provided** to check against any laws even if they had been specified.

**Required actions before this feature ships:**
- The legal or product team must enumerate the applicable legal frameworks. Given the feature's nature (processing audio content from X/Twitter, generating synthetic voices and avatar videos, storing user data), the minimum expected candidates are: GDPR (if any EU users are served), CCPA (if California users are served), DMCA/copyright law (regarding content sourced from X/Twitter Spaces), and the Terms of Service of ElevenLabs and HeyGen (which are contractual, not statutory, but legally binding).
- Once laws are specified, a compliance-focused audit pass must be performed against the actual code.

---

## SECURITY CONSENSUS

Both models flagged the same class of security concerns conceptually. In priority order for when code becomes available:

1. **API Key / Secrets Management (P0):** All credentials for ElevenLabs, HeyGen, and any other external services must be stored in environment variables or a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault). They must never appear in source code, configuration files committed to git, or logs.

2. **Rate Limiting / Abuse Prevention (P0):** Already detailed in U-2. Financial denial-of-service via API credit exhaustion is a security issue, not just an operational one.

3. **Input Validation and Injection Prevention (P1):** Any user-provided input — Space IDs, text for TTS, configuration parameters — must be validated and sanitized before being passed to database queries (SQL injection), shell commands (command injection), or external API calls (parameter injection).

4. **Authentication and Authorization on Pipeline Endpoints (P1):** Endpoints that initiate pipeline jobs must require authentication. Authorization checks must verify that a user can only access and manage their own jobs, not those belonging to other users (IDOR prevention).

5. **Temporary File Security (P2):** Audio and video processing will produce temporary files on disk or in cloud storage. These must be stored in user-isolated paths, cleaned up after job completion, and not be accessible via predictable public URLs.

---

## WORLD-CLASS GAP CONSENSUS
*(Only items mentioned by 2+ models included)*

Given only 2 models were available and all findings from both models are already captured above, the following represent the combined intelligence's view of what separates the current conceptual design from a truly world-class implementation:

### WCG-1 — No Async Architecture for Heavy Compute (Both models implicitly, Grok explicitly)
A world-class pipeline does not block web workers on audio/video processing. The gap between "it works for 10 users" and "it works for 1000 concurrent users" is almost entirely determined by whether heavy compute is properly offloaded to a dedicated worker pool. This is the single largest architectural gap identified.

### WCG-2 — No Observability Layer (Both models implicitly, Grok explicitly)
A world-class system knows what it is doing at all times: how many jobs are in each state, what the p50/p95/p99 latency is for each pipeline step, what the current API spend rate is, and how many jobs have failed in the last hour. Without instrumentation, this pipeline is a black box that will only be understood retrospectively, after failures have already impacted users.

### WCG-3 — No Graceful Degradation Strategy (Both models)
A world-class pipeline has a defined answer to "what happens when ElevenLabs is down?" — not just "it fails." Options include: queuing jobs for retry, falling back to an alternative TTS provider, notifying users proactively, or offering a degraded mode. The current conceptual design has no answer to this question.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Add pre-flight guard to audit dispatch script that aborts if code section is empty; alert engineering team | CI/CD audit dispatch script (`.github/workflows/` or equivalent) : N/A | Both (Gemini + Grok) | Two full cycles of expensive AI review have produced zero actionable code findings due to this failure. Every additional cycle without this fix is pure waste. |
| **P0 CRITICAL** | Implement per-user rate limiting (token bucket or sliding window, Redis-backed) on all pipeline-initiating endpoints; return 429 + Retry-After | `app/routes/spaces.py` (speculative) : route handler | Both (Gemini + Grok) | Absent this control, one user or script can exhaust all API credits for all users. Financial and operational existential risk. |
| **P0 CRITICAL** | Ensure all external API credentials (ElevenLabs, HeyGen) are stored in environment variables or secrets manager; confirm zero secrets in source or git history | All service wrapper files (speculative) | Both (Gemini + Grok, implied) | Exposed credentials = immediate full compromise of all API accounts. |
| **P1 HIGH** | Design and implement `PipelineJob` state machine in database with atomic state transitions, failure capture, and retry logic | `app/services/pipeline_manager.py` (speculative) | Both | Silent job failures are operationally catastrophic. Without a state machine, there is no recovery path, no user feedback, and no debugging surface. |
| **P1 HIGH** | Implement task queue (Celery + Redis or equivalent) to offload TTS and lip-sync processing from Flask workers; ensure horizontal scalability of workers | `app/workers/` or equivalent (speculative) | Grok (UI-1); implied by both | Synchronous processing of audio/video in Flask workers will exhaust the worker pool under any real load. |
| **P1 HIGH** | Set explicit timeouts on all external HTTP calls; implement try/except for Timeout and ConnectionError; transition job to FAILED state with error detail on exception | All external API service wrappers (speculative) | Both | Hanging workers = denial of service. Silent failures = invisible bugs. |
| **P1 HIGH** | Add authentication + IDOR-preventing authorization checks to all pipeline endpoints | `app/routes/spaces.py` (speculative) | Both (implied) | Unauthenticated endpoints allow anonymous abuse; missing authorization allows users to access each other's jobs. |
| **P1 HIGH** | Implement aggregate real-time API cost monitoring with configurable alert thresholds | `app/services/cost_monitor.py` (speculative) | Grok (UI-2) | Complements rate limiting with financial observability. Prevents billing surprises. |
| **P1 HIGH** | Implement job status polling endpoint and frontend progress display to prevent user-initiated duplicate submissions | `app/routes/spaces.py` + frontend (speculative) | Grok (UI-3) | User retries on long-running jobs multiply API costs and database load. |
| **P2 MEDIUM** | Audit all SQLAlchemy list queries for N+1 patterns; apply `joinedload()`/`selectinload()` where appropriate | All query-heavy route handlers (speculative) | Both | Will not manifest until load increases, but will cause severe database degradation at scale. |
| **P2 MEDIUM** | Add specific edge case handling: empty/silent audio, unsupported languages, invalid Space IDs | Pipeline processing service (speculative) | Both | Unhandled edge cases will produce cryptic errors or silent failures for real users. |
| **P2 MEDIUM** | Scope and document applicable laws (GDPR, CCPA, DMCA, TOS compliance); assign legal review | `docs/` / product spec | Both | Governing laws section is empty. Feature cannot be certified compliant against nothing. Legal team action required. |
| **P2 MEDIUM** | Implement temporary file cleanup after job completion; ensure non-predictable storage paths | Pipeline processing service (speculative) | Both (implied) | Accumulating temp files will exhaust storage; predictable paths are a security risk. |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY. NOT AUDIT READY. NOT CYCLE READY.**

After two complete cycles involving three AI models (one of which failed due to quota exhaustion, itself an operational concern), the x-spaces-pipeline feature has received zero lines of actual code review. The audit process is broken at the tooling level.

**The absolute final blocker is singular and non-negotiable:**

> **The CI/CD audit dispatch pipeline must be fixed to include actual source code in the audit package before any further review cycles are executed, any merge is considered, or any production deployment is discussed.**

Until that blocker is resolved, all other findings in this report are conceptual risk assessments against a specification — valuable for planning, but not a substitute for a genuine code audit. The feature should be considered unaudited and must not be merged to main or deployed.

**Secondary verdict:** When code does become available, the most dangerous risk is the absence of rate limiting on paid API endpoints (U-2). This must be the first thing verified in any future audit cycle, before any other code quality concern.

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/X_SPACES_PIPELINE_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/x-spaces-pipeline_CONSENSUS_C2.md.

This is the FINAL PASS for x-spaces-pipeline.
The feature was reviewed by 2 independent AI models across 2 cycles.
No source code was available during either cycle due to a tooling failure.
Your first task is to fix the tooling, then implement all P0 and P1 items.
Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Add pre-flight guard to audit dispatch script | CI/CD audit dispatch script | Both models | Abort and alert if code section is empty; prevents wasted review cycles
P0 CRITICAL | Implement per-user rate limiting on all pipeline endpoints | app/routes/spaces.py | Both models | Prevents API credit exhaustion and financial denial of service
P0 CRITICAL | Move all external API credentials to env vars / secrets manager | All service wrappers | Both models | Exposed secrets = immediate full compromise
P1 HIGH     | Design PipelineJob state machine with atomic transitions and failure capture | app/services/pipeline_manager.py | Both models | Required for job recovery, user feedback, and debugging
P1 HIGH     | Implement Celery + Redis (or equivalent) task queue for TTS and lip-sync | app/workers/ | Grok | Flask workers cannot handle synchronous audio/video processing at scale
P1 HIGH     | Set explicit timeouts and exception handling on all external HTTP calls | All external API service wrappers | Both models | Hanging workers = denial of service
P1 HIGH     | Add authentication and IDOR-preventing authorization to all pipeline routes | app/routes/spaces.py | Both models | Prevent anonymous abuse and cross-user data access
P1 HIGH     | Implement real-time API cost monitoring with configurable alert thresholds | app/services/cost_monitor.py | Grok | Financial observability to complement rate limiting
P1 HIGH     | Implement job status polling endpoint and frontend progress display | app/routes/spaces.py + frontend | Grok | Prevent user retries from multiplying API calls and DB load
P2 MEDIUM   | Audit SQLAlchemy list queries for N+1 patterns; apply joinedload/selectinload | All query-heavy route handlers | Both models | Will cause DB degradation at scale
P2 MEDIUM   | Add edge case handling for empty/silent audio, unsupported languages, invalid Space IDs | Pipeline processing service | Both models | Prevents cryptic errors for real users
P2 MEDIUM   | Document and obtain legal review for GDPR, CCPA, DMCA, T

---

# WINNER DETERMINATION

# WINNER: **Gemini** — Gemini delivered superior analytical rigor across both cycles by immediately and forcefully flagging the meta-process failure with clear formatting ("AUDIT ALERT: NO CODE PROVIDED"), providing domain-specific edge cases tailored to audio pipeline processing rather than generic placeholders, and demonstrating intellectual honesty in Cycle 2 by self-correcting its own World-Class Gap score from PARTIAL to UNVERIFIABLE — a disciplined epistemological move that Grok failed to make, reflecting higher standards for what constitutes a defensible finding.

---

## FINAL SECOND-PASS PRIORITY LIST
*Definitive ordered implementation list derived from both cycles and the consensus report.*

---

### P0 — BLOCKING (Do not merge, do not proceed)

**P0-1: Fix the audit package generation tooling**
- Locate the CI/CD script (`.github/workflows/`, `Makefile`, or bespoke audit dispatcher) responsible for populating `THE CODE` section
- Add a hard pre-flight assertion: if `THE CODE` block is empty or contains the literal string `No code files found`, abort the dispatch and fail the workflow with a non-zero exit code
- Gate the AI reviewer invocation behind this check — zero tolerance for dispatching empty audits

**P0-2: Validate Claude Code session handoff**
- The placeholder `(No code files found — run after Claude Code session completes)` was never replaced across two full cycles, indicating the Claude Code session output is not being piped into the audit package generator
- Confirm the session export mechanism, file path resolution, and timing dependency between session completion and audit dispatch
- Add an integration test that asserts the audit package byte count exceeds a minimum threshold before dispatch

---

### P1 — HIGH PRIORITY (Implement before first real audit cycle)

**P1-1: Rate limiting on all paid external API endpoints**
- ElevenLabs TTS and HeyGen avatar endpoints must have request rate limiting, retry-with-backoff, and circuit breaker logic implemented before any production traffic
- Specifically: implement token-bucket or leaky-bucket limiting per user session, not globally, to prevent one user from exhausting quota for all 1000 concurrent users

**P1-2: Pipeline state persistence and failure recovery**
- Each pipeline job (download → transcribe → TTS → lip-sync → avatar) must have its state persisted in the database with discrete status fields (PENDING, IN_PROGRESS, FAILED, COMPLETE)
- A failure at step N must not silently drop the job — it must mark state as FAILED with error detail, be retryable, and surface clearly to the user

**P1-3: Secrets management audit**
- API keys for ElevenLabs, HeyGen, and any other external service must not be hardcoded or committed — verify environment variable injection and confirm no secrets appear in git history

---

### P2 — MEDIUM PRIORITY (Implement before load testing)

**P2-1: N+1 query elimination**
- Any dashboard or list view rendering pipeline jobs must use `joinedload` or `selectinload` in SQLAlchemy — audit all ORM queries in list endpoints before the 1000-concurrent-user load test

**P2-2: Race condition protection on shared pipeline resources**
- Verify transaction isolation levels for concurrent job creation and status updates
- Implement optimistic or pessimistic locking on pipeline job rows where simultaneous modification is possible

**P2-3: Domain-specific edge case handling**
- Empty/silent audio input: define and implement a minimum duration threshold with user-facing error
- Unsupported language detection: fail fast with a clear message rather than passing garbage to TTS
- Invalid or expired Space IDs: validate upstream before entering the pipeline

---

### P3 — LOW PRIORITY (Pre-launch hygiene)

**P3-1: Frontend spec compliance verification**
- Once code is available, verify no WebGL usage exists — pure CSS/SVG animations only per spec
- Pixel-perfect UI compliance pass against the design spec

**P3-2: Audit process monitoring**
- Add alerting if an audit dispatch completes with zero findings or with all scores marked UNVERIFIABLE — this condition should trigger a human review flag, not a silent pass

---

*Note: P1 through P3 items are conceptually grounded but require actual code to verify implementation status. All remain UNVERIFIABLE until the P0 tooling failure is resolved and a valid audit package is produced.*