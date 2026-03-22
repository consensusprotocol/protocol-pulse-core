# CONSENSUS REPORT — TTS-PIPELINE — CYCLE 2
Generated: 2026-03-19 07:35
Models: Grok (+2 failed: Gemini 403 PERMISSION_DENIED — leaked API key; GPT-4o 429 insufficient_quota)

---

> ⚠️ **REDUCED CONFIDENCE NOTICE**: This consensus is derived from a single model (Grok) across 2 cycles. Gemini and GPT-4o failed due to infrastructure errors unrelated to code quality. All findings below reflect one model's perspective. Cross-validation is absent. Treat every finding as **requiring human expert verification before implementation**. The "consensus" sections are structural placeholders; true consensus requires 2+ models.

> ⚠️ **ADDITIONAL NOTICE**: No code files were available in either cycle ("No code files found — run after Claude Code session completes"). All findings are **architectural/speculative**, derived from feature description, technology stack, and expected patterns. Zero findings have been validated against actual source code. This report must be regenerated once code is available.

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok       | Consensus  |
|-----------------|--------|--------|------------|------------|
| Correctness     | FAILED | FAILED | UNSCORED   | UNSCORED   |
| Law Compliance  | FAILED | FAILED | UNSCORED   | UNSCORED   |
| Security        | FAILED | FAILED | UNSCORED   | UNSCORED   |
| Frontend Quality| FAILED | FAILED | UNSCORED   | UNSCORED   |
| Backend Quality | FAILED | FAILED | UNSCORED   | UNSCORED   |
| World-Class Gap | FAILED | FAILED | UNSCORED   | UNSCORED   |
| **Overall**     | FAILED | FAILED | **UNSCORED** | **UNSCORED** |

**Scoring rationale**: Grok explicitly declined to score in both cycles due to absence of code. Gemini and GPT-4o did not produce outputs. No numeric scores exist anywhere in the audit corpus. Fabricating scores would be a false record — they are left UNSCORED. Regenerate after code is available.

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

> With only 1 model, "unanimous" means "flagged consistently across both Grok cycles." These are the highest-confidence speculative findings, but remain unvalidated against code.

---

### U-1 — Pipeline Sequencing / State Machine Integrity

**What it is**: The TTS → Avatar → Lip-sync pipeline must enforce strict dependency ordering. Without explicit state transitions (e.g., `PENDING → TTS_COMPLETE → AVATAR_COMPLETE → LIPSYNC_COMPLETE → DONE`), stage 2 or 3 may begin before upstream artifacts (audio file, avatar frame) are ready, producing corrupted or silent outputs.

**Which file/line**: Unknown — no code provided. Expected locations: pipeline orchestrator module, task queue handler, async workflow definition.

**What to change**:
- Implement a formal state machine or dependency graph for pipeline stages
- Each stage must await a confirmed success signal (not just task dispatch) from the prior stage
- Persist state in DB (SQLite via SQLAlchemy) so in-flight jobs survive process restarts
- Reject stage N execution if stage N-1 has not reached `COMPLETE` status

**Confidence**: High (architectural necessity for any multi-stage async pipeline). Human verification required before implementation.

---

### U-2 — API Key Security (ElevenLabs / HeyGen — No Hardcoding)

**What it is**: ElevenLabs and HeyGen API keys must not appear in source code, config files committed to version control, or log output. Exposure enables unauthorized API usage, financial loss from drained credits, and potential account termination.

**Which file/line**: Unknown — no code provided. Expected risk locations: `config.py`, `settings.py`, `.env` files, any file instantiating ElevenLabs or HeyGen SDK clients.

**What to change**:
- All API keys must be loaded exclusively from environment variables or a secrets manager
- Add `.env` to `.gitignore` immediately if not already present
- Add a pre-commit hook or CI check (e.g., `git-secrets`, `trufflehog`) to block key commits
- Audit git history for any previously committed keys; rotate immediately if found

**Confidence**: High (universal security baseline). Human verification required.

---

### U-3 — GPU Resource Contention (Wav2Lip)

**What it is**: Wav2Lip lip-sync processing is GPU-bound. With ~1000 concurrent users and shared RTX 4090 hardware, unqueued parallel requests will cause CUDA OOM errors, process crashes, or silent failures. Grok elevated this from edge case to core concern in Cycle 2.

**Which file/line**: Unknown — no code provided. Expected location: Wav2Lip invocation module, task worker configuration.

**What to change**:
- Implement a GPU task queue with bounded concurrency (e.g., max N simultaneous Wav2Lip jobs per GPU)
- Return HTTP 429 or queue position to users when GPU is saturated rather than accepting and silently failing
- Wrap GPU calls in try/except for `RuntimeError: CUDA out of memory` with graceful fallback and retry logic
- Consider separate worker pools for CPU-bound (TTS, avatar) vs. GPU-bound (lip-sync) stages

**Confidence**: High (architectural necessity at stated concurrency target). Human verification required.

---

## MAJORITY FINDINGS (2 of 1 models agree)

> With only 1 model across 2 cycles, "majority" is undefined in the strict sense. This section captures issues Grok raised in both Cycle 1 and Cycle 2 (repeated across cycles = elevated confidence within the single-model constraint).

---

### M-1 — Race Conditions on Temporary Files

**What it is**: With ~1000 concurrent users, temporary audio and video files generated at each pipeline stage risk name collisions or overwrites if not uniquely scoped per request/user/session.

**What to change**: Use UUID-based or session-scoped unique paths for all temporary artifacts (e.g., `/tmp/tts/{job_uuid}/audio.mp3`). Implement atomic write patterns.

**File/line**: Unknown. Expected: file I/O utilities, pipeline stage handlers.

---

### M-2 — Temporary File Cleanup

**What it is**: Grok raised this in Cycle 2 as an escalation of the race condition concern. Without explicit cleanup of temp files post-completion or post-failure, disk space on the Ultron server will be exhausted under sustained load, causing cascading failures.

**What to change**: Implement cleanup in a `finally` block or dedicated cleanup task after each pipeline job terminates (success or failure). Add disk usage monitoring alert.

**File/line**: Unknown. Expected: pipeline orchestrator, task teardown logic.

---

### M-3 — Error Propagation and User Feedback

**What it is**: Pipeline failures (API timeout, GPU OOM, avatar render failure) must propagate meaningful status to the user. Silent failures leave users with no output and no understanding of what happened or whether to retry.

**What to change**: Define an error taxonomy for each stage. Store failure reason in job status record. Expose failure reason via API response and/or UI notification (e.g., "TTS generation failed — ElevenLabs timeout. Retry?").

**File/line**: Unknown. Expected: error handling middleware, job status model, frontend status polling.

---

### M-4 — Input Validation / Rate Limiting

**What it is**: Unvalidated text input to the TTS stage (empty string, excessively long text, malformed characters) may cause downstream API errors or unexpected behavior. No rate limiting means a single user or bot could exhaust API credits or GPU capacity.

**What to change**: Validate and sanitize text input before dispatching to ElevenLabs. Enforce per-user rate limits on pipeline initiation (e.g., max N requests per minute per user). Return HTTP 422 for invalid input, HTTP 429 for rate limit exceeded.

**File/line**: Unknown. Expected: request handler, input validation layer.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

> All findings in this audit are from a single model. The items below were raised only in Cycle 2 (not Cycle 1), making them "new" within the Grok corpus.

---

### X-1 — Accessibility Scope Ambiguity (WCAG)

**What it is**: Grok raised WCAG compliance in Cycle 1 but partially walked it back in Cycle 2, noting that if `tts-pipeline` is purely backend/API-driven with no direct UI, WCAG may not apply to this feature.

**Assessment**: **Investigate further.** Before spending effort on frontend accessibility for this feature specifically, confirm whether `tts-pipeline` has a user-facing interface or is consumed exclusively via API by other frontend components. If the latter, WCAG compliance belongs to the consuming UI feature, not this pipeline. Do not implement frontend accessibility work against this audit without scope confirmation.

---

### X-2 — SQLAlchemy N+1 Query Risk

**What it is**: Grok noted in Cycle 1 that pipeline status/history queries could degrade into N+1 patterns (fetching related records per pipeline step in a loop).

**Assessment**: **Investigate further.** This is a real and common SQLAlchemy pitfall. Once code is available, audit all ORM queries in the pipeline status and history retrieval paths. Use `joinedload` or `selectinload` where relationships are accessed. This is P2 until code reveals an actual N+1 pattern, at which point it becomes P1.

---

## CONFLICTS (models disagree — your tiebreaker)

> With only 1 model, no inter-model conflicts exist. The single intra-model conflict (Grok's shifting position on WCAG scope) is addressed in X-1 above.

**Structural note for future cycles**: If Gemini and GPT-4o are restored, prioritize resolving any conflicts on:
- Whether GPU queuing should be a hard blocker (P0) or architectural recommendation (P1)
- Whether temporary file cleanup belongs in application code or infrastructure-level (cron/cloud storage lifecycle policy)
- Scoring methodology given absence of code in both cycles

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> No validated strengths can be established. Zero models reviewed actual code. Zero positive assessments were grounded in source inspection.

**Do not treat any aspect of this codebase as audit-validated.** When code becomes available, re-run the full 3-model audit from Cycle 1.

---

## LAW COMPLIANCE CONSENSUS

**Status**: **INDETERMINATE — no code reviewed, no governing laws provided.**

The audit package references "see gospel" for governing laws, but the gospel content was not available to any model. No model could confirm or deny violations.

**Speculative risk areas** (require legal review once code and laws are available):

| Area | Risk Level | Basis |
|------|-----------|-------|
| GDPR/CCPA — user text input storage | Medium | TTS input text may constitute personal data if it contains PII |
| GDPR/CCPA — generated audio/video retention | Medium | Output files tied to user identity; must have defined retention/deletion policy |
| DMCA/Copyright — avatar or voice cloning | High | ElevenLabs voice cloning and HeyGen avatar generation may have copyright/likeness implications depending on training data and consent |
| Accessibility (WCAG) | Low-Medium | Scope-dependent; see X-1 |

**Final determination**: Cannot be made without (a) actual code, (b) governing laws from the gospel document, (c) legal counsel on voice/avatar IP implications.

---

## SECURITY CONSENSUS

Single-model security findings, prioritized:

| Priority | Issue | Confidence |
|----------|-------|-----------|
| P0 | API key hardcoding (ElevenLabs/HeyGen) | High |
| P0 | No input sanitization on TTS text (injection/abuse risk) | Medium |
| P1 | No rate limiting (credential/credit exhaustion) | High |
| P1 | Temporary file exposure (insecure paths, no cleanup) | Medium |
| P2 | GPU task endpoint not authenticated/authorized | Unknown — needs code review |
| P2 | Error messages may leak internal state or API details | Unknown — needs code review |

**Note**: All security findings are speculative. A proper security audit requires code, dependency manifest review, and infrastructure configuration review.

---

## WORLD-CLASS GAP CONSENSUS

> Only items raised by 2+ models qualify per instructions. With 1 model, this section is structurally empty. Items below are raised by Grok across 2 cycles — treated as "elevated single-model concern" rather than true consensus.

**Gap 1 — Production-Grade Pipeline Observability**
A world-class TTS pipeline at ~1000 concurrent users requires distributed tracing (e.g., OpenTelemetry), per-stage latency metrics, and real-time alerting on failure rates. No evidence this exists. Without it, debugging production incidents is blind.

**Gap 2 — Graceful Degradation Strategy**
A world-class product defines what happens when ElevenLabs is down, HeyGen is slow, or the GPU is saturated. Does the system queue, fallback to a lower-quality TTS engine, return partial results, or fail fast with a clear message? None of this was mentioned in the feature spec.

**Gap 3 — Job Persistence Across Restarts**
For long-running GPU jobs, a world-class system persists job state such that a server restart or crash does not silently discard in-progress work. Users should be able to poll job status and receive results after a transient failure.

> **These gaps require 2-model confirmation before becoming action items. Flag for the restored-model audit.**

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| P0 CRITICAL | Enforce strict pipeline state machine with explicit `PENDING → TTS_COMPLETE → AVATAR_COMPLETE → LIPSYNC_COMPLETE → DONE` transitions; reject stage N if stage N-1 not `COMPLETE` | Pipeline orchestrator — file unknown | Grok (both cycles) | Silent failures and corrupted output under any concurrency |
| P0 CRITICAL | Move all ElevenLabs and HeyGen API keys to environment variables; add `.env` to `.gitignore`; add pre-commit secret scanning; rotate any exposed keys immediately | `config.py` / `settings.py` / client init files — locations unknown | Grok (both cycles) | Financial loss, account termination, credential abuse |
| P0 CRITICAL | Implement GPU task queue with bounded concurrency for Wav2Lip; wrap in CUDA OOM error handler; return 429 when saturated | Wav2Lip invocation module — location unknown | Grok (Cycle 2 escalation) | CUDA OOM crashes entire worker process, affects all concurrent users |
| P1 HIGH | Use UUID-scoped temp file paths for all pipeline artifacts; implement atomic writes | File I/O utilities, stage handlers — location unknown | Grok (both cycles) | File overwrites and race conditions at scale |
| P1 HIGH | Implement `finally`-block or post-job cleanup for all temp audio/video files | Pipeline orchestrator, task teardown — location unknown | Grok (Cycle 2) | Disk exhaustion on Ultron server under sustained load |
| P1 HIGH | Define error taxonomy per stage; persist failure reason in job status; expose via API response and UI notification | Error handling middleware, job status model, frontend — location unknown | Grok (Cycle 2) | Users receive no feedback on failure; no debuggability |
| P1 HIGH | Validate and sanitize TTS text input (reject empty, enforce max length, strip dangerous chars); enforce per-user rate limits | Request handler, input validation layer — location unknown | Grok (both cycles) | API credit exhaustion, downstream errors, potential abuse |
| P2 MEDIUM | Audit SQLAlchemy queries for N+1 patterns in pipeline status/history paths; apply `joinedload`/`selectinload` | ORM query layer — location unknown | Grok (Cycle 1) | Latency degradation at scale; escalate to P1 if confirmed in code |
| P2 MEDIUM | Confirm WCAG scope — if `tts-pipeline` has a user-facing UI, audit for screen reader and keyboard navigation support | Frontend components — location unknown | Grok (conditional) | Accessibility compliance; skip if feature is API-only |
| P2 MEDIUM | Add distributed tracing and per-stage latency metrics | Observability layer — location unknown | Grok (Cycle 2, world-class gap) | No production debuggability; 2-model confirmation needed before implementing |

---

## CYCLE 2 VERDICT

**Production-ready: NO.**

**Not because the code is bad** — the code has never been seen by any model. The audit infrastructure failed in both cycles: no code was provided to any model, Gemini's API key was leaked and revoked, and GPT-4o exceeded quota. This report is built entirely on architectural speculation about a feature that may or may not have these problems.

**Absolute final blockers before this audit can be considered valid:**

1. **The code must exist and be provided to the audit system.** Re-run from Cycle 1 after `Claude Code session completes`.
2. **Gemini API key must be replaced** (current key reported as leaked — this is also a security incident for the audit infrastructure itself).
3. **GPT-4o quota must be restored** before multi-model consensus is possible.
4. **The gospel document** (`TTS_PIPELINE_AUDIT_GOSPEL.md`) must be made available to auditing models so law compliance can be evaluated against actual governing requirements.

**If the speculative P0 findings (U-1, U-2, U-3) happen to be real issues in the actual code**, they are genuine production blockers. But their existence cannot be confirmed without source review.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/TTS_PIPELINE_AUDIT_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/tts-pipeline_CONSENSUS_C2.md.

This is the FINAL PASS for tts-pipeline.
The first build was reviewed by 1 independent AI model (Grok) across 2 cycle(s).
NOTE: Gemini failed (leaked API key — rotate before re-auditing) and GPT-4o
failed (quota exceeded). All findings are speculative — validate against actual
code before implementing. Do not implement any item where the described problem
does not exist in the actual source.

Implement every confirmed P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Enforce pipeline state machine (PENDING→TTS_COMPLETE→AVATAR_COMPLETE→LIPSYNC_COMPLETE→DONE); reject stage N if N-1 not COMPLETE | Pipeline orchestrator | Grok both cycles | Silent failures and corrupted output under concurrency
P0 CRITICAL | Move ElevenLabs/HeyGen API keys to env vars; add .env to .gitignore; add pre-commit secret scanning; rotate any exposed keys | config.py/settings.py/client init | Grok both cycles | Credential exposure, financial loss
P0 CRITICAL | Implement GPU task queue with bounded concurrency for Wav2Lip; handle CUDA OOM; return 429 when saturated | Wav2Lip module | Grok Cycle 2 | Process crashes affect all concurrent users
P1 HIGH | UUID-scoped temp file paths; atomic writes | File I/O utilities, stage handlers | Grok both cycles | Race conditions at scale
P1 HIGH | finally-block temp file cleanup after job success or failure | Pipeline orchestrator, teardown | Grok Cycle 2 | Disk exhaustion under load
P1 HIGH | Error taxonomy per stage; persist failure reason; expose via API and UI | Error middleware, job model, frontend | Grok Cycle 2 | No user feedback or debuggability on failure
P1 HIGH | Validate/sanitize TTS input (reject empty, max length, strip dangerous chars); per-user rate limits | Request handler, input validation | Grok both cycles | API abuse, credit exhaustion
P2 MEDIUM | Audit SQLAlchemy queries for N+1 in status/history paths; apply joinedload/selectinload if found | ORM query layer | Grok Cycle 1 | Latency at scale
P2 MEDIUM | Confirm WCAG scope; if UI exists, audit screen reader and keyboard nav | Frontend components | Grok conditional | Accessibility compliance
P2 MEDIUM | Add distributed tracing and per-stage latency metrics | Observability layer | Grok Cycle 2 | Production debuggability

VALIDATED (do NOT touch — all models confirmed excellent):
NONE — no code was reviewed by any model. No area has been confirmed as
excellent. Exercise standard engineering judgment on all untouched areas.

INFRASTRUCTURE ISSUES TO RESOLVE BEFORE NEXT AUDIT:
1. Replace Gemini API key (current key is LEAKED — security incident)
2. Restore GPT-4o quota
3. Ensure code files are present before audit runs ("No code files found" in both cycles)
4. Provide gospel document to audit models for law compliance evaluation

After implementing confirmed findings:
regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(tts-pipeline): post-audit pass — consensus improvements"
git push origin feature/tts-pipeline
```

---

# WINNER DETERMINATION

## WINNER: **Grok**

Grok is the only model that produced output in both cycles, and critically, it demonstrated **epistemic integrity** by explicitly refusing to fabricate findings, scores, or code analysis when no source code was present — a quality that outweighs any depth comparison with absent competitors.

---

## HONEST ASSESSMENT AGAINST YOUR FOUR CRITERIA

Before the priority list, the evaluation must be stated plainly:

**This is not a meaningful competition.** Gemini failed with a leaked API key error (403). GPT-4o failed with quota exhaustion (429). Grok "won" by default. Judging Grok against four quality criteria in isolation produces a misleading scorecard, so here is the accurate one:

| Criterion | Grok Score | Notes |
|---|---|---|
| **Accuracy** | Unverifiable | No code existed to validate against. Grok's speculative findings (state machine gaps, API key exposure) are *plausible* for this stack but unconfirmed. |
| **Depth** | Low–Medium | Grok identified reasonable architectural risks (pipeline sequencing, concurrency, N+1 queries) but explicitly acknowledged these were pattern-matched assumptions, not code-derived findings. |
| **Actionability** | Medium | Recommendations like "use explicit state transitions PENDING → TTS_COMPLETE → AVATAR_COMPLETE" and "rotate API keys via environment variables" are implementable, but carry no confidence weight without code validation. |
| **Completeness** | Structurally complete, substantively hollow | Grok covered all six audit sections in Cycle 1. In Cycle 2 it correctly identified it was reviewing *its own* output (noting the other models' outputs were absent), which is an honest structural observation rather than a quality finding. |

---

## FINAL SECOND-PASS PRIORITY LIST

These are ordered by risk severity for a TTS pipeline on the described stack (ElevenLabs + HeyGen + Wav2Lip + SQLite/SQLAlchemy + ~1000 concurrent users). Every item is **speculative until code is reviewed**.

---

### PRIORITY 1 — BLOCKER (Do not ship without verifying)

**P1-A: API Key Exposure**
- Risk: ElevenLabs and HeyGen API keys hardcoded or committed to version control
- Action: Audit `.env`, `settings.py`, and git history (`git log -S "sk_"`) before any deployment
- Why first: A leaked key was already confirmed in this audit run (Gemini's 403 error originated from a leaked key in the audit package itself — this is not hypothetical)

**P1-B: Pipeline State Integrity**
- Risk: No atomic state transitions between TTS → Avatar → Lip-sync steps; partial failures leave orphaned jobs or corrupt output
- Action: Verify each pipeline stage writes a completion state before the next stage reads it; add a dead-letter queue or explicit FAILED state for each step
- Why first: Silent failures in a multi-GPU async pipeline are unrecoverable without this

**P1-C: Concurrent File Collision**
- Risk: Temporary audio/video files named without session isolation; ~1000 concurrent users will produce collisions
- Action: Confirm all temp files use UUIDs or user-session-scoped paths; verify cleanup on failure paths, not just success paths

---

### PRIORITY 2 — HIGH (Fix before public release)

**P2-A: GPU Memory Exhaustion**
- Risk: Wav2Lip jobs queued without GPU memory bounds checking; OOM kills the worker process silently
- Action: Implement a job queue with concurrency limits matching GPU VRAM capacity; add explicit OOM error handling with job retry logic

**P2-B: N+1 Queries on Pipeline Status**
- Risk: Dashboard or status polling fetches pipeline metadata in a loop per job record
- Action: Run SQLAlchemy query logging under simulated load; add `.joinedload()` or batch fetch where applicable

**P2-C: Input Validation on TTS Text**
- Risk: Empty string, null, or malformed Unicode passed to ElevenLabs API produces unhandled exceptions
- Action: Validate and sanitize all text input before API call; define explicit max character limits aligned with ElevenLabs tier

---

### PRIORITY 3 — MEDIUM (Fix within first sprint post-launch)

**P3-A: External API Timeout Handling**
- Risk: ElevenLabs or HeyGen API calls block indefinitely on network degradation
- Action: Add explicit timeouts (recommended: 30s connect, 120s read for video APIs) and exponential backoff with circuit breaker

**P3-B: GDPR/Data Retention for Generated Media**
- Risk: User-generated audio/video stored indefinitely with no deletion policy
- Action: Define and implement retention policy; add deletion endpoint and confirm storage cleanup on account deletion

**P3-C: Error Observability**
- Risk: Pipeline failures logged to console only; no structured error tracking at scale
- Action: Integrate Sentry or equivalent; ensure each pipeline stage emits structured logs with job ID, user ID (hashed), and failure reason

---

### PRIORITY 0 — REGENERATE THIS AUDIT

**Before implementing any of the above:**

The entire audit ran against no code. Every finding above is architectural pattern-matching. The correct next step is:

```
1. Complete the Claude Code session
2. Confirm code files are present in the audit package
3. Rerun all three models with actual source code
4. Use that output — not this one — as the implementation guide
```

This report should be archived as a **pre-implementation risk register**, not treated as a code audit result.