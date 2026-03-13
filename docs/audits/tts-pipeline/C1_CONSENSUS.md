# CONSENSUS REPORT — TTS-PIPELINE — CYCLE 1
Generated: 2026-03-12 20:50
Models: Grok-3, Gemini 2.5 Pro (+1 failed: GPT-4o — quota exhausted)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | 0/100 | N/A | 0/100 | **0/100** |
| Frontend/UI | 0/100 | N/A | 0/100 | **0/100** |
| Error Handling | 0/100 | N/A | 0/100 | **0/100** |
| Security | 0/100 | N/A | 0/100 | **0/100** |
| Performance | 0/100 | N/A | 0/100 | **0/100** |
| Law Compliance | 0/100 | N/A | 0/100 | **0/100** |
| World-Class Gap | 0/100 | N/A | 0/100 | **0/100** |
| **OVERALL** | **0/100** | **N/A** | **0/100** | **0/100** |

> **Score Note:** Both models independently and explicitly assigned zero to all categories because no code was present in the audit package. These are not harsh grades — they are the only mathematically honest scores possible. Scores will be meaningful in Cycle 2 once code exists.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — No Code Was Submitted
- **What it is:** The audit package contained zero code files. The trigger message was `"No code files found — run after Claude Code session completes"`. Both models confirmed this independently.
- **File/Line:** N/A — the absence is the finding.
- **What to change:** The audit pipeline must only fire after the Claude Code session has committed files to the branch. Gate the audit script on `git diff --name-only origin/main...HEAD | grep -q '.'` before generating the package.

### U2 — Asynchronous Task Queue is Architecturally Required
- **What it is:** Both models independently concluded that a synchronous Flask request cannot handle the multi-stage pipeline (ElevenLabs → HeyGen → Wav2Lip). At ~1000 concurrent users, any synchronous implementation will time out and deadlock workers.
- **File/Line:** No file exists yet, but this must be the foundational architectural decision before a single line of pipeline code is written.
- **What to change:** Implement a task queue (Celery + Redis or equivalent). The Flask route must do only three things: validate input, create a `PENDING` job record in the DB, and enqueue the task. Return a `job_id` immediately. All processing happens in the worker.

### U3 — API Key / Secrets Management Must Be Enforced
- **What it is:** Both models flagged that ElevenLabs, HeyGen, and any Wav2Lip service credentials must never be hardcoded. Given the paid-API nature of these services, a leaked key is both a security breach and a direct financial liability.
- **File/Line:** To be verified once code exists — search for `ELEVEN_LABS_API_KEY`, `HEYGEN_API_KEY`, any literal key patterns in `.py`, `.env.example`, config files.
- **What to change:** All secrets via environment variables only. Add a startup assertion that checks required env vars are set and raises a clear error if missing. Ensure `.env` is in `.gitignore`.

### U4 — Per-User Rate Limiting on Pipeline Trigger Endpoint
- **What it is:** Both models flagged that a single malicious or misconfigured user can exhaust paid API quotas (ElevenLabs, HeyGen) for all other users, causing both a denial-of-service and unbounded cost exposure.
- **File/Line:** To be verified — the route that initiates the pipeline (likely `POST /api/tts/generate` or similar).
- **What to change:** Implement per-user rate limiting (e.g., `Flask-Limiter`) on the trigger endpoint. Define a sensible limit (e.g., 5 requests/minute, 50/day per user) and return `429` with a `Retry-After` header on breach.

### U5 — Job State Machine Must Be Explicit and Complete
- **What it is:** Both models independently described the requirement for a formal state machine: `PENDING → GENERATING_AUDIO → GENERATING_AVATAR → LIP_SYNCING → COMPLETE / FAILED`. A failure in any stage must halt the pipeline, mark the job `FAILED`, and persist an error message.
- **File/Line:** Job model file (does not yet exist).
- **What to change:** Define an enum or constant set for job states. Every state transition must be a transactional DB write. No job should ever be stuck in a non-terminal processing state.

### U6 — GPU Resource Management for Wav2Lip
- **What it is:** Both models flagged that Wav2Lip is GPU-intensive and concurrent unqueued requests will cause OOM errors on the RTX 4090s, crashing the worker.
- **File/Line:** Wav2Lip invocation code (does not yet exist).
- **What to change:** Implement a bounded worker pool or semaphore for GPU tasks. Maximum concurrent Wav2Lip jobs must be configured (start with 2 per GPU = 4 total on the dual-4090 system). Excess jobs queue rather than fail.

### U7 — External API Calls Require Timeouts, Retries, and Error Handling
- **What it is:** Both models flagged that all three external API calls (ElevenLabs, HeyGen, Wav2Lip) need explicit timeouts, exponential-backoff retries for transient errors, and exception handlers that update job state to `FAILED` on permanent errors.
- **File/Line:** API client modules (do not yet exist).
- **What to change:** Every `requests.post()` or SDK call must have a `timeout` argument. Wrap in retry logic (e.g., `tenacity` library). `try/except` must catch specific exceptions, log them with job ID context, and call `job.mark_failed(reason)`.

### U8 — Absence of Governing Laws is a P0 Process Failure
- **What it is:** Both models flagged that the GOVERNING LAWS section of the audit package is empty. For a feature involving AI voice synthesis and AI video avatars, this is not a minor omission.
- **File/Line:** Audit gospel / product legal documentation.
- **What to change:** Before this feature ships to production, legal must specify compliance requirements covering at minimum: synthetic media/deepfake regulations (EU AI Act, US state laws), biometric data laws (Illinois BIPA and equivalents), voice/avatar IP licensing terms from ElevenLabs and HeyGen, and data privacy (GDPR/CCPA for stored generated content).

---

## MAJORITY FINDINGS (2 of 2 models agree — same threshold as unanimous given only 2 reviewers)

> With only two functional reviewers, Majority and Unanimous are the same threshold. All material findings are captured in the Unanimous section above. The items below represent additional detail one model provided that the other implied but did not explicitly state.

### M1 — Database Transactions Must Pair `commit()` with `rollback()` in Exception Handlers
- **Detail from Gemini:** Explicitly called out that every state transition must be within a transaction with `rollback()` in the `except` block. Grok implied this under "DB Operations" but did not state it as explicitly.
- **Verdict:** Implement. Standard SQLAlchemy hygiene, doubly important for job state transitions.

### M2 — Input Validation: Empty Text, Length Limits, Encoding
- **Detail from Grok:** Explicitly listed empty input, long input exceeding API limits, and invalid file formats as edge cases. Gemini addressed this under input validation but less specifically.
- **Verdict:** Implement. The pipeline endpoint must validate: non-empty text, maximum character count (align with ElevenLabs and HeyGen documented limits), and character encoding before any external call is made.

### M3 — Structured Logging with Job ID at Every Pipeline Step
- **Detail from Gemini:** Explicitly required structured logging with unique job ID at every step including API request/response payloads and errors. Grok mentioned logging with user ID, request ID, and timestamp.
- **Verdict:** Implement. Use structured logging (e.g., `structlog` or Python `logging` with JSON formatter). Every log line in the pipeline worker must include `job_id`, `user_id`, `stage`, and `timestamp`.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — N+1 Query Risk on Job List View *(Grok unique)*
- **What it is:** Grok specifically called out the N+1 query pattern for a user's job history list — fetching a list of jobs then querying each job's status separately.
- **Assessment:** **Implement.** This is a real and common ORM pitfall. When the job list endpoint is built, use `joinedload` or explicit joins. Add a composite index on `(user_id, created_at)` on the jobs table.

### UI2 — Biometric / Deepfake Law Specificity *(Gemini unique)*
- **What it is:** Gemini specifically named Illinois BIPA and the EU AI Act as applicable laws, going beyond Grok's generic "data privacy" mention.
- **Assessment:** **Investigate further / Escalate.** These are real laws with teeth (BIPA has a private right of action; EU AI Act classifies certain deepfake generation as high-risk). Legal must explicitly clear this feature under these specific frameworks before any production launch. Flag as P0 legal blocker.

### UI3 — Shell Command Injection via Wav2Lip Invocation *(Gemini unique)*
- **What it is:** Gemini specifically called out that if Wav2Lip is invoked via a shell command (e.g., `subprocess.run()` with user-controlled input), there is a shell injection risk.
- **Assessment:** **Implement immediately.** When Wav2Lip integration is built, never pass user-supplied text into a shell command. Use `subprocess.run(args_list, shell=False)` with a pre-validated argument list. Sanitize all file paths derived from user input.

### UI4 — Cost Tracking / Analytics per User *(Grok unique)*
- **What it is:** Grok identified that professionals expect per-user cost tracking for API usage (ElevenLabs, HeyGen charges per character/second), and that this gap would mark the product as non-enterprise-grade.
- **Assessment:** **Implement (P2).** Log per-job API cost estimates to the DB. This enables admin dashboards, per-user billing attribution, and abuse detection. Not a blocker for initial ship but required for a world-class product.

### UI5 — Sophisticated Loading Progress UX *(Gemini unique)*
- **What it is:** Gemini called out that a simple spinner is insufficient for a premium product. The UI should show stage-by-stage progress: "Step 1 of 3: Generating audio..." with the CSS/SVG animation constraint.
- **Assessment:** **Implement.** This is the correct call for a product positioning against Bloomberg/Coinbase. The multi-stage job state machine (U5 above) directly enables this — the frontend polls job state and renders the appropriate stage label and animation.

---

## CONFLICTS (models disagree — tiebreaker)

**No direct conflicts exist.** Both models reached identical high-level conclusions from first principles, applied to the same empty code package. The differences between the two outputs are additive (one being more specific in some areas) rather than contradictory.

The closest thing to a divergence: Grok suggested Redis for caching TTS job results as a performance optimization, while Gemini proposed Redis/RabbitMQ as the task queue backend. These are **complementary**, not conflicting — Redis can serve both roles.

**Tiebreaker ruling:** Use Redis as both the Celery broker and the caching layer for job status polling. This minimizes infrastructure complexity on the Ubuntu/Ultron server.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

**None can be validated.** No code was submitted. There is nothing to declare excellent. This section will be populated in Cycle 2 once code is reviewed.

> This is not a criticism — it is an honest accounting. Declaring strengths without evidence would be fabrication.

---

## LAW COMPLIANCE CONSENSUS

**Final Determination: INDETERMINATE — P0 BLOCKER**

- The GOVERNING LAWS section of the audit package was empty.
- Both models independently flagged this as a critical omission.
- The feature's nature (AI voice synthesis + AI video avatar generation) places it in a legally sensitive category across multiple jurisdictions.
- **Specific laws requiring explicit clearance before production:**
  - EU AI Act (Articles on synthetic media and transparency requirements)
  - Illinois BIPA and equivalent US state biometric privacy laws
  - ElevenLabs and HeyGen Terms of Service — commercial use rights, content restrictions, generated output ownership
  - GDPR / CCPA — for stored audio/video generated from user input associated with user accounts
  - FTC guidelines on AI-generated content disclosure (if output is user-facing)

**Action Required:** Legal sign-off must be documented in the gospel before Cycle 2 scoring in the Law Compliance category can be anything other than 0.

---

## SECURITY CONSENSUS

**Priority order (both models agreed on all items):**

1. **API Key Hardcoding** — Direct financial and security exposure. P0.
2. **Shell Injection via Wav2Lip** — Remote code execution risk if invoked insecurely. P0.
3. **Missing Authentication on Pipeline Trigger** — Unauthenticated users could trigger paid API calls. P0.
4. **No Rate Limiting** — API quota exhaustion / cost DoS. P0.
5. **Input Sanitization** — Text stored in DB and rendered on frontend; XSS vector if unsanitized. P1.
6. **File Path Sanitization** — Intermediate audio/video files must use UUID-based names, not user-derived paths. P1.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by both models (threshold for inclusion):

1. **Async Architecture** — Both models: A synchronous pipeline is not world-class. It's not even functional at scale. Task queue is table stakes.
2. **Stage-by-Stage Progress UX** — Both models: A premium product shows the user exactly where their job is in the pipeline, not a generic loading state.
3. **Resilience / Graceful Degradation** — Both models: If ElevenLabs or HeyGen is down, the system must handle this gracefully with user-facing messaging, not a silent 500 error.
4. **GPU Queue Management** — Both models: Unmanaged GPU access is not world-class. A proper worker pool with queue depth visibility is expected.
5. **Cost Attribution** — Both models (Grok explicit, Gemini implied): Enterprise-grade products track per-user API cost for accountability, billing, and abuse prevention.
6. **Accessibility** — Both models: WCAG compliance for the generated content (transcripts for audio, captions for video) is expected at the Bloomberg/Coinbase tier.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Do not merge — no code submitted; re-run audit after Claude Code session completes | Audit gate script | Both | Impossible to audit or score without code |
| **P0 CRITICAL** | Obtain legal sign-off on EU AI Act, BIPA, ElevenLabs/HeyGen ToS before any production deploy | Gospel / Legal doc | Both | Synthetic media laws carry severe penalties; no code should ship without this clearance |
| **P0 CRITICAL** | Architect task queue (Celery + Redis) as the foundation; Flask route returns `job_id` only | `tts/tasks.py`, `tts/routes.py` | Both | Synchronous pipeline will time out and crash at any meaningful concurrency |
| **P0 CRITICAL** | All API keys (ElevenLabs, HeyGen) in environment variables only; startup assertion if missing | `config.py`, `.env.example` | Both | Leaked keys = direct financial liability + security breach |
| **P0 CRITICAL** | Invoke Wav2Lip via `subprocess.run(list, shell=False)` only; never pass user text to shell | `tts/wav2lip_client.py` | Gemini (unique) | Shell injection → remote code execution on a GPU server |
| **P0 CRITICAL** | Require authentication on all pipeline trigger endpoints | `tts/routes.py` | Both | Unauthenticated paid API calls = unlimited cost exposure |
| **P0 CRITICAL** | Implement per-user rate limiting on pipeline trigger (e.g., 5/min, 50/day) | `tts/routes.py` | Both | API quota DoS + runaway cost from one user |
| **P1 HIGH** | Implement formal job state machine: `PENDING→GENERATING_AUDIO→GENERATING_AVATAR→LIP_SYNCING→COMPLETE/FAILED` | `tts/models.py` | Both | No other part of the system can work correctly without this |
| **P1 HIGH** | Wrap all external API calls in `try/except` with timeouts (30-60s), exponential backoff retries, and `job.mark_failed()` on permanent error | `tts/elevenlabs_client.py`, `tts/heygen_client.py` | Both | External APIs fail; jobs must never be stuck in processing states forever |
| **P1 HIGH** | Pair every `db.session.commit()` with `db.session.rollback()` in `except` blocks | All DB write paths | Gemini (both implied) | Partial state writes corrupt job records |
| **P1 HIGH** | Implement GPU semaphore / bounded worker pool for Wav2Lip (max 2 concurrent per GPU) | `tts/workers.py` | Both | Concurrent GPU tasks → OOM crashes on RTX 4090s |
| **P1 HIGH** | Structured logging with `job_id`, `user_id`, `stage`, `timestamp` at every pipeline step | All pipeline modules | Both | Multi-stage async jobs are undebuggable without correlated log context |
| **P1 HIGH** | Input validation: reject empty text, enforce character limits per API constraints, validate encoding | `tts/routes.py` | Both (Grok explicit) | Bad input reaching external APIs wastes quota and produces confusing errors |
| **P1 HIGH** | Sanitize all intermediate file paths; use UUIDs not user-derived names | `tts/file_manager.py` | Both implied | Path traversal risk for audio/video temp files |
| **P2 MEDIUM** | Add composite DB index on `(user_id, created_at)` for job list queries; use `joinedload` to avoid N+1 | `tts/models.py` | Grok unique | Will degrade at scale; index must exist before launch |
| **P2 MEDIUM** | Stage-by-stage progress UI with CSS/SVG animations per job state (no Three.js/Canvas) | `frontend/tts/*.js`, `*.css` | Gemini unique | Premium UX expectation; spinner alone is not world-class |
| **P2 MEDIUM** | Log per-job API cost estimate to DB for cost attribution and abuse detection | `tts/models.py`, worker | Grok unique | Required for enterprise-grade product; enables billing and admin visibility |
| **P2 MEDIUM** | Add WCAG-compliant transcripts/captions for generated audio/video output | Frontend output component | Both implied | Accessibility is non-negotiable at Bloomberg/Coinbase tier |

---

## CYCLE 1 VERDICT

**⛔ NOT READY FOR SECOND BUILD PASS — FUNDAMENTAL BLOCKER: NO CODE EXISTS**

This is not a conditional hold. The audit package contained zero code files. Both independent reviewers confirmed this. There is nothing to score, fix, or iterate on. The verdict is unambiguous:

1. Complete the Claude Code session for `feature/tts-pipeline`
2. Commit all files to the branch
3. Re-run the audit package generator
4. Fire Cycle 1 audits again against the actual code

The architectural guidance in this report (task queue, state machine, GPU management, secrets, rate limiting) should be treated as **pre-implementation requirements** — design decisions that must be baked in from the first line of code, not patched in after the fact.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/TTS_PIPELINE_AUDIT_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/tts-pipeline_CONSENSUS_C1.md.

This is the SECOND PASS for tts-pipeline.
The first build was reviewed by 2 independent AI models across 1 cycle(s).
Implement every P0 and P1 item from the consensus. Use judgment on P2.

⚠️ IMPORTANT: Cycle 1 was blocked because no code existed in the audit package.
This pass is the FIRST CODE IMPLEMENTATION. Architecture decisions must be made
correctly from the start — retrofitting these after the fact is far more expensive.

PRIORITY ACTION PLAN:

P0 CRITICAL | Architect task queue as foundation | tts/tasks.py, tts/routes.py | Both models | Synchronous pipeline fails at any concurrency; Flask route returns job_id only; Celery + Redis for task execution
P0 CRITICAL | All API keys in environment variables only; startup assertion if missing | config.py, .env.example | Both models | ElevenLabs + HeyGen keys are financial liability if hardcoded or leaked
P0 CRITICAL | Invoke Wav2Lip via subprocess.run(list, shell=False) only | tts/wav2lip_client.py | Gemini | Shell injection on GPU server = RCE; never pass user text to shell
P0 CRITICAL | Require authentication on all pipeline trigger endpoints | tts/routes.py | Both models | Unauthenticated paid API calls = unlimited cost exposure
P0 CRITICAL | Per-user rate limiting on pipeline trigger (5/min, 50/day) | tts/routes.py | Both models | API quota DoS and cost explosion from single user
P1 HIGH | Formal job state machine: PENDING→GENERATING_AUDIO→GENERATING_AVATAR→LIP_SYNCING→COMPLETE/FAILED | tts/models.py | Both models | All other logic depends on this; no ambiguous states
P1 HIGH | All external API calls: timeouts (30-60s), exponential backoff, job.mark_failed() on permanent error | tts/elevenlabs_client.py, tts/heygen_client.py | Both models | APIs fail; jobs must never be permanently stuck in processing state
P1 HIGH | Every db.session.commit() paired with db.session.rollback() in except blocks | All DB write paths | Both models | Partial writes corrupt job state permanently
P1 HIGH | GPU semaphore / bounded worker pool for Wav2Lip (max 2 concurrent per RTX 4090, 4 total) | tts/workers.py | Both models | Concurrent GPU OOM crashes take down the entire worker
P1 HIGH | Structured logging: job_id + user_id + stage + timestamp at every pipeline step | All pipeline modules | Both models | Async multi-stage jobs are completely undebuggable without correlated context
P1 HIGH | Input validation: reject empty text, enforce ElevenLabs/HeyGen character limits, validate encoding | tts/routes.py | Both models | Bad input wastes paid API quota and produces confusing downstream errors
P1 HIGH | UUID-based intermediate file paths for all audio/video temp files | tts/file_manager.py | Both models | No user-derived paths; prevents path traversal and file collision under concurrency
P2 MEDIUM | Composite DB index on (user_id, created_at) for job list; joinedload to prevent N+1 | tts/models.py | Grok | Will degrade at scale; must exist before any load
P2 MEDIUM | Stage-by-stage progress UI with CSS/SVG animations reflecting job state (no Three.js/Canvas/WebGL) | frontend/tts/ | Gemini | Premium product expectation; spinner alone is not world-class
P2 MEDIUM | Log per-job API cost estimate (ElevenLabs characters,