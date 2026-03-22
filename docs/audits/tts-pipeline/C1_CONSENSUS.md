# CONSENSUS REPORT — TTS-PIPELINE — CYCLE 1
Generated: 2026-03-19 07:32
Models: grok (+2 failed)

---

> ⚠️ **AUDIT INTEGRITY WARNING**
> This consensus report is based on **1 of 3 models** (Grok-3 only). Gemini 2.5 Pro failed with a leaked API key (403), and GPT-4o failed due to quota exhaustion (429). All findings below carry **reduced confidence** — single-model observations cannot be cross-validated. The "Unanimous," "Majority," and "Conflict" sections are structurally degenerate. Treat every finding as a **UNIQUE INSIGHT** requiring human engineering judgment before implementation. A Cycle 2 re-audit with all three models operational is strongly recommended before merging.

> ⚠️ **NO CODE WAS REVIEWED**
> The audit package contained no source files ("No code files found — run after Claude Code session completes"). All findings are **speculative/architectural** — derived from the feature specification, technology stack description, and general engineering best practices. Zero lines of actual code were inspected. The action plan below describes what to *look for and verify*, not confirmed bugs.

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok | Consensus |
|------------------|--------|--------|------|-----------|
| Correctness      | N/A    | N/A    | —*   | **UNSCORED** |
| Law Compliance   | N/A    | N/A    | —*   | **UNSCORED** |
| Security         | N/A    | N/A    | —*   | **UNSCORED** |
| Frontend Quality | N/A    | N/A    | —*   | **UNSCORED** |
| Backend Quality  | N/A    | N/A    | —*   | **UNSCORED** |
| World-Class Gap  | N/A    | N/A    | —*   | **UNSCORED** |
| **Overall**      | N/A    | N/A    | —*   | **UNSCORED** |

*Grok explicitly declined to score without code, correctly identifying that numeric scores without source inspection would be fabricated. This is the correct behavior. Any score assigned here would be meaningless theater.*

---

## UNANIMOUS FINDINGS (all 1 models agree — implement unconditionally)

> With only 1 model operational, "unanimous" means "Grok flagged this." Do not treat these as cross-validated certainties. They are high-probability risk areas based on architectural reasoning.

### U-1: Pipeline Sequencing Integrity
**What it is:** The TTS → Avatar → Lip-sync chain must be strictly sequential or explicitly managed with dependency signaling. If Wav2Lip begins before ElevenLabs audio is fully written to disk/buffer, the result will be corrupted or silent video with no obvious error.
**File/Line:** Unknown — likely the main pipeline orchestrator module (e.g., `pipeline/tts_pipeline.py` or equivalent)
**What to change:** Verify that each stage awaits a success signal (not just "task submitted") from the prior stage before proceeding. Use explicit state transitions (e.g., `PENDING → TTS_COMPLETE → AVATAR_COMPLETE → LIPSYNC_COMPLETE → DONE`), not fire-and-forget calls.

### U-2: API Key Security — No Hardcoding
**What it is:** ElevenLabs and HeyGen API keys must never appear in source files, committed `.env` files, or logs.
**File/Line:** All files referencing `ELEVENLABS_API_KEY`, `HEYGEN_API_KEY`, or equivalent
**What to change:** Confirm keys are loaded exclusively from environment variables, that `.env` is in `.gitignore`, and that no key value appears in any log statement (even debug-level).

### U-3: Authentication Enforcement on Pipeline Endpoints
**What it is:** Pipeline-triggering routes consume paid API credits. Unauthenticated access to these routes is a direct financial liability.
**File/Line:** All route handlers that initiate TTS, avatar, or lip-sync jobs
**What to change:** Confirm every such route has a login-required decorator (e.g., `@login_required`) applied before any API call is made. Verify this is enforced at the framework level, not just UI-level hiding of buttons.

### U-4: Temporary File Cleanup
**What it is:** Audio and video files generated mid-pipeline must be deleted after delivery or on failure. Accumulated temp files will exhaust disk space on the Ultron server under production load.
**File/Line:** Pipeline orchestrator and any error/exception paths
**What to change:** Implement `try/finally` blocks that delete temp files regardless of success or failure. Consider a cron-based fallback cleanup for orphaned files older than N hours.

### U-5: GPU Memory Release After Each Request
**What it is:** Wav2Lip on 2x RTX 4090 must explicitly release GPU memory after processing. Unreleased tensors/buffers will cause OOM errors under concurrent load.
**File/Line:** Wav2Lip invocation wrapper
**What to change:** Confirm `torch.cuda.empty_cache()` (or equivalent) is called after each inference job. Confirm that the model is not loaded per-request (expensive) but also not leaking session state between users.

---

## MAJORITY FINDINGS (2 of 1 models agree)

> Structurally impossible with 1 model. This section is void.

**VOID** — Cannot have majority agreement with a single respondent. All findings are either unanimous (U-*) or unique (UI-*).

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

Since all findings come from one model, every item not already listed above is presented here with an explicit recommendation.

---

### UI-1: Race Conditions on Concurrent File Writes
**Observation:** With ~1000 concurrent users, non-unique temp file naming (e.g., `output.mp3`, `render.mp4`) will cause overwrites between simultaneous pipeline runs.
**Assessment:** **IMPLEMENT** — This is a fundamental correctness issue for any multi-user system. Verify that every temp file is namespaced by user ID + UUID + timestamp. This is table-stakes engineering.

### UI-2: N+1 Query Risk on Pipeline Status Polling
**Observation:** If a status-check endpoint fetches pipeline metadata and then iterates to fetch related records (e.g., per-step logs), each iteration may trigger a separate DB query.
**Assessment:** **INVESTIGATE** — Cannot confirm without code. If SQLAlchemy relationships are used, verify `joinedload()` or `selectinload()` is applied where appropriate. Check the status polling route specifically.

### UI-3: Input Validation on TTS Text
**Observation:** Empty string, extremely long strings, or strings containing control characters/code could cause unexpected behavior at the ElevenLabs API boundary or in log output.
**Assessment:** **IMPLEMENT** — Add explicit validation: minimum 1 character, maximum N characters (check ElevenLabs API limits), strip dangerous characters. Return a clear 400 error with user-facing message, not a 500.

### UI-4: Rate Limiting on Pipeline Endpoints
**Observation:** No per-user or per-IP rate limiting on pipeline-triggering routes would allow a single actor to exhaust ElevenLabs/HeyGen quotas or saturate the GPU queue.
**Assessment:** **IMPLEMENT** — Apply rate limiting (e.g., Flask-Limiter) to pipeline initiation endpoints. Suggested: max 10 pipeline requests per user per hour, configurable via environment variable.

### UI-5: External API Timeout and Retry Logic
**Observation:** ElevenLabs and HeyGen calls without explicit timeouts will hang indefinitely if the external service is degraded, blocking worker threads.
**Assessment:** **IMPLEMENT** — All external HTTP calls must have a timeout parameter (suggest 30s for TTS, 120s for video rendering). Implement exponential backoff retry (max 3 attempts) on 429/503 responses. On final failure, return a structured error to the user — never silently drop the job.

### UI-6: Loading / Error / Empty States in UI
**Observation:** Every async pipeline operation must expose three UI states: loading (with progress indication), error (with actionable message), and empty (when no prior outputs exist).
**Assessment:** **IMPLEMENT** — World-class products never leave users staring at a frozen screen. This is a UX non-negotiable.

### UI-7: Missing Voice/Avatar Customization
**Observation:** A premium pipeline offering ElevenLabs + HeyGen without user-selectable voices or avatar styles feels like a demo, not a product.
**Assessment:** **INVESTIGATE FURTHER** — This may be an intentional MVP scope decision. If so, document it as a known gap. If voice/avatar selection is feasible in the current sprint, it meaningfully elevates product quality and should be prioritized.

### UI-8: Output Caching / CDN Delivery
**Observation:** Processing every request on-demand with no caching will create latency issues at scale. Bloomberg-comparable products pre-cache or CDN-serve repeated outputs.
**Assessment:** **INVESTIGATE** — Determine if any pipeline outputs are deterministic enough to cache (e.g., same text + same voice → same audio). Even short-TTL caching would reduce GPU pressure significantly.

### UI-9: Structured Error Logging
**Observation:** Production debugging requires that errors include user ID, pipeline job ID, timestamp, and full stack trace. Generic `print()` or unstructured logs make incident response nearly impossible.
**Assessment:** **IMPLEMENT** — Confirm all `except` blocks log structured data, not bare exception strings. Use a consistent logger (e.g., Python `logging` module with a formatter), not `print()`.

### UI-10: GDPR/CCPA Temporary Data Handling
**Observation:** User text inputs and generated audio/video files are personal data under GDPR/CCPA. Retention without consent or deletion mechanisms is a compliance risk.
**Assessment:** **IMPLEMENT** — Confirm: (a) temp files are deleted promptly after delivery, (b) any persisted outputs have a documented retention policy, (c) users can request deletion of their generated content.

---

## CONFLICTS (models disagree — your tiebreaker)

> Cannot exist with 1 model. **VOID.**

No conflicts to resolve. This is itself a risk signal — lack of disagreement from multiple independent reviewers means blind spots are not being surfaced. Strongly recommend re-running with Gemini and GPT-4o operational, against actual code.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> Cannot validate anything without code inspection. **VOID.**

No strengths can be confirmed. This section must remain empty until at least one model has reviewed actual source files. Do not interpret the absence of validated strengths as a weakness — it is simply an absence of data.

---

## LAW COMPLIANCE CONSENSUS

**Status: UNDETERMINED — no code reviewed**

| Law/Regulation | Status | Basis |
|----------------|--------|-------|
| GDPR (data privacy, temp file retention) | ⚠️ RISK — UNVERIFIED | Grok flagged architectural risk; cannot confirm without code |
| CCPA (California privacy) | ⚠️ RISK — UNVERIFIED | Same as GDPR — user-generated content retention policy unknown |
| WCAG 2.1 (accessibility) | ⚠️ RISK — UNVERIFIED | CSS/SVG UI with async states — screen reader support unverified |
| API ToS Compliance (ElevenLabs, HeyGen) | ⚠️ RISK — UNVERIFIED | Usage logging and attribution requirements unknown |

**Final Determination:** No law can be declared compliant or violated without code review. The GDPR/CCPA temporary file retention risk (UI-10) is the highest-priority compliance item to verify.

---

## SECURITY CONSENSUS

**Status: ARCHITECTURAL RISKS IDENTIFIED — cannot confirm exploitability without code**

Priority order of security concerns (single-model, speculative):

| Priority | Issue | Severity |
|----------|-------|----------|
| 1 | Unauthenticated pipeline endpoint access (free API credit consumption) | CRITICAL |
| 2 | API keys hardcoded or committed to version control | CRITICAL |
| 3 | No rate limiting on pipeline triggers (quota exhaustion/DoS) | HIGH |
| 4 | Unvalidated TTS text input reaching external APIs | HIGH |
| 5 | SQL injection via unsanitized input to SQLAlchemy | MEDIUM |
| 6 | Temp file namespace collision (user data cross-contamination) | MEDIUM |

All of these require code-level verification. Items 1 and 2 are so foundational that they should be verified manually by the engineering team immediately, regardless of audit status.

---

## WORLD-CLASS GAP CONSENSUS

> Requires 2+ models to agree. With 1 model, no item meets the threshold. All gaps are single-model observations.

**VOID by threshold rule.**

For transparency, the gaps Grok identified (which *would* require cross-model validation before inclusion):
- Voice/avatar customization controls
- Output caching and CDN delivery
- Pipeline usage analytics (credit consumption, success rates)
- Preview-before-render functionality
- Progress indication during long GPU processing jobs

These are genuine product quality concerns — but without cross-model validation, they cannot be listed as consensus gaps. They should be captured in the product backlog for human prioritization.

---

## FINAL ACTION PLAN (sorted by consensus priority)

> All items are single-model, speculative (no code reviewed). Treat as an audit checklist, not a confirmed bug list. Priority reflects potential impact severity, not confirmed presence.

```
P0 CRITICAL | Verify authentication decorator on ALL pipeline routes | pipeline/routes.py (estimated) | models: unique (Grok) | Unauthenticated access burns paid API credits and exposes GPU resources
P0 CRITICAL | Verify API keys are not in source or committed .env | All files, .gitignore | models: unique (Grok) | Leaked keys = immediate financial and security incident
P0 CRITICAL | Verify GPU memory release after each Wav2Lip inference | wav2lip wrapper (estimated) | models: unique (Grok) | OOM crash under load takes down the entire server
P0 CRITICAL | Verify temp file cleanup in try/finally on all paths | pipeline orchestrator | models: unique (Grok) | Disk exhaustion under production load
P0 CRITICAL | Verify pipeline stage sequencing is synchronous/awaited | pipeline orchestrator | models: unique (Grok) | Silent failures producing corrupt output with no error signal
P1 HIGH     | Add per-user rate limiting on pipeline trigger endpoints | pipeline/routes.py | models: unique (Grok) | Single user can exhaust all API quotas or saturate GPU queue
P1 HIGH     | Add explicit timeout + retry on ElevenLabs/HeyGen calls | api_clients/ (estimated) | models: unique (Grok) | Hung threads block all workers; no user feedback on failure
P1 HIGH     | Add input validation on TTS text (length, content) | pipeline/routes.py or validators | models: unique (Grok) | Malformed input causes 500s or unexpected API behavior
P1 HIGH     | Implement structured logging with user/job ID in all except blocks | All backend modules | models: unique (Grok) | Production incidents are undebuggable without structured logs
P1 HIGH     | Verify unique temp file naming (user_id + UUID + timestamp) | pipeline orchestrator | models: unique (Grok) | File collisions between concurrent users corrupt output
P2 MEDIUM   | Add loading / error / empty states to all pipeline UI components | frontend components | models: unique (Grok) | Users see frozen UI during 30-120s processing jobs
P2 MEDIUM   | Audit SQLAlchemy status queries for N+1 patterns | db/models or routes | models: unique (Grok) | Performance degradation under polling load
P2 MEDIUM   | Document or implement GDPR/CCPA temp data retention policy | pipeline + privacy docs | models: unique (Grok) | Compliance risk; user data persists without legal basis
P2 MEDIUM   | Add voice/avatar selection UI if MVP scope permits | frontend + pipeline API | models: unique (Grok) | Product feels like a demo without customization
P2 MEDIUM   | Investigate output caching for deterministic pipeline runs | pipeline orchestrator | models: unique (Grok) | Repeated identical requests waste GPU and API credits
```

---

## CYCLE 1 VERDICT

**❌ NOT READY FOR SECOND BUILD PASS**

This audit is **invalid as a code review** because no source code was available for inspection. The audit package itself was empty. Additionally, 2 of 3 models failed due to infrastructure issues (leaked API key, quota exhaustion), leaving a single model operating on zero actual code.

**Required before proceeding:**

1. **Fix the audit infrastructure** — Rotate the Gemini API key immediately (the existing one is reported as leaked and is a live security incident regardless of this audit). Resolve the GPT-4o billing situation.
2. **Ensure code is committed** before triggering the audit pipeline — the audit script must run *after* the Claude Code session produces committed files.
3. **Re-run Cycle 1 with all three models** against actual code before generating a consensus report with real confidence.
4. **Human engineering review** of P0 items (authentication, API keys, GPU memory) should happen immediately — do not wait for audit tooling to be fixed before checking these manually.

The action plan above is a valid *pre-flight checklist* that the engineering team can use right now, but it is not a substitute for an actual multi-model code audit.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/TTS_PIPELINE_AUDIT_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/tts-pipeline_CONSENSUS_C1.md.

This is the SECOND PASS for tts-pipeline.
The first build was reviewed by 1 independent AI model across 1 cycle.
NOTE: Cycle 1 had NO CODE available for review and 2 of 3 models failed.
This second pass is therefore also a FIRST REAL CODE REVIEW.
Implement every P0 and P1 item from the consensus checklist below.
Use judgment on P2. Do not implement anything that contradicts the gospel.

PRIORITY ACTION PLAN:

P0 CRITICAL | Verify and enforce authentication decorator on ALL pipeline-triggering routes — no unauthenticated request should reach ElevenLabs, HeyGen, or Wav2Lip
P0 CRITICAL | Audit all source files for hardcoded API keys (ElevenLabs, HeyGen); confirm .env is in .gitignore and keys are loaded exclusively from environment variables
P0 CRITICAL | Confirm GPU memory is explicitly released (torch.cuda.empty_cache() or equivalent) in a try/finally block after every Wav2Lip inference call
P0 CRITICAL | Confirm all temp audio/video files are deleted in try/finally blocks on both success and failure paths — implement cron fallback for files older than 4 hours
P0 CRITICAL | Confirm pipeline stages (TTS → Avatar → Lip-sync) await explicit success signals before proceeding — no fire-and-forget stage transitions
P1 HIGH     | Add per-user rate limiting (max 10 pipeline jobs/hour, configurable) to all pipeline initiation endpoints using Flask-Limiter or equivalent
P1 HIGH     | Add explicit HTTP timeout (30s TTS, 120s video) and exponential backoff retry (max 3 attempts, 429/503) to all ElevenLabs and HeyGen API calls
P1 HIGH     | Add input validation to TTS text endpoint: min 1 char, max per ElevenLabs API limit, strip control characters, return 400 with user-facing message on failure
P1 HIGH     | Replace all bare print()/unstructured logging in except blocks with structured logger calls including user_id, job_id, timestamp, and full stack trace
P1 HIGH     | Confirm all temp files are named with user_id + UUID + timestamp to prevent namespace collisions between concurrent users
P2 MEDIUM   | Add loading, error, and empty states to all pipeline-related frontend components — no async operation should leave the user with no feedback
P2 MEDIUM   | Audit SQLAlchemy queries in pipeline status/history routes for N+1 patterns; apply joinedload/selectinload where relationships are traversed
P2 MEDIUM   | Document temp data retention policy for GDPR/CCPA compliance; confirm users can request deletion of their generated content
P2 MEDIUM   | If within MVP scope, add voice selection (ElevenLabs voice ID) and avatar selection (HeyGen avatar ID) to the pipeline UI and API
P2 MEDIUM   | Investigate caching for deterministic pipeline runs (same text + same voice = same audio); even a short TTL cache reduces GPU and API load

VALIDATED (do NOT touch — all models confirmed excellent):
[NONE — no code was reviewed in Cycle 1; no strengths have been validated]
[Do not assume any area is safe from review]

After implementing all P0 and P1 items:
1. Run regression_test.sh — must show zero FAILs before committing
2. Manually verify: hit a pipeline endpoint without auth — must return 401/403
3. Manually verify: check git log and grep source for API key values — must find none
4. git add -A && git commit -m "feat(tts-pipeline): post-audit pass — consensus improvements (C1)"
5. git push origin feature/tts-pipeline

IMPORTANT: After pushing, re-trigger the three-model audit pipeline (Cycle 2).
Cycle 1 was infrastructure-compromised. Cycle 2 will be the first real code audit.
```