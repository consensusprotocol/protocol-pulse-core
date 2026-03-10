# CONSENSUS REPORT — SESSION1-TERMINAL — CYCLE 2
Generated: 2026-03-10 04:08
Models: gpt4o, gemini, grok

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend logic | 0/100 | 0/100 | 0/100 | **0/100** |
| Frontend/UI | 0/100 | 0/100 | 0/100 | **0/100** |
| Error handling | 0/100 | 0/100 | 0/100 | **0/100** |
| Security | 0/100 | 0/100 | 0/100 | **0/100** |
| Performance | 0/100 | 0/100 | 0/100 | **0/100** |
| Law compliance | 0/100 | 0/100 | 0/100 | **0/100** |
| World-class gap | 0/100 | 0/100 | 0/100 | **0/100** |
| **OVERALL** | **0/100** | **0/100** | **0/100** | **0/100** |

> **Scoring note:** All three models independently arrived at identical scores across all subsystems in both Cycle 1 and Cycle 2. Scores reflect package auditability, not the unseen codebase. The unseen implementation remains in an unknown state — not "scored zero," but **unverifiable**.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Code package is empty; audit is structurally impossible
**All three models (GPT-4o, Gemini, Grok) flagged this as the absolute primary blocker.**
- **What it is:** The `THE CODE` section of the audit package explicitly states `(No code files found — run after Claude Code session completes)`. No routes, models, migrations, templates, static assets, jobs, config, or tests were submitted in either Cycle 1 or Cycle 2.
- **File/Location:** Audit package → `THE CODE` section
- **What to change:** The audit pipeline must be halted until the full git diff or complete changed file set for `feature/session1-terminal` is attached. This is a process enforcement issue, not a code fix.
- **Impact:** Without code, every downstream audit section — correctness, security, performance, law compliance, UI quality — is structurally blocked. No finding in this report below this line has been verified against actual implementation.

### U2 — Governing laws section is empty
**All three models flagged this as a P0 blocker independent of the missing code.**
- **What it is:** The spec's `GOVERNING LAWS` section contains no content. For a Bitcoin intelligence product with user sessions, external AI API calls, voice synthesis, and financial data presentation, multiple legal frameworks likely apply and have not been identified.
- **File/Location:** `docs/gospels/SESSION_1_TERMINAL_SPEC.md` → `GOVERNING LAWS` section
- **What to change:** Define, in writing, every applicable regulation before development is considered complete. Probable candidates (flagged across models): GDPR/CCPA for user session/voice data; SEC/FINRA/MiFID II if the terminal influences trading decisions; CFAA if session access controls are insufficient.
- **Impact:** Shipping a financial intelligence feature without a defined legal framework is negligent. Compliance cannot be verified, implemented, or tested against undefined requirements.

### U3 — Rate limiting for paid external APIs is unspecified
**All three models identified this as a critical financial and operational risk.**
- **What it is:** The feature integrates ElevenLabs (TTS), HeyGen (avatar), and Wav2Lip (lip-sync). None of the submitted materials specify per-user or per-session rate limits, quota caps, or spending controls on these APIs.
- **File/Location:** Spec: session1-terminal requirements; implementation (location unknown — no code submitted)
- **What to change:** Define and implement per-user rate limits, per-session API call budgets, and hard circuit breakers that fail gracefully rather than escalating charges. Document these limits in the spec.
- **Impact:** Without controls, a single malicious or runaway user session can exhaust paid API quotas in minutes. This is both a financial risk and a denial-of-service vector.

### U4 — Timeout, retry, and circuit-breaker strategy is unspecified
**All three models flagged the absence of resilience patterns for external API calls.**
- **What it is:** No evidence of defined timeout windows, retry policies, or circuit-breaker logic for ElevenLabs, HeyGen, or Wav2Lip integrations.
- **File/Location:** Service wrappers / API integration layer (location unknown — no code submitted)
- **What to change:** Every external API call must have: an explicit timeout (e.g., 10s for TTS, 30s for avatar rendering); a retry strategy with exponential backoff and jitter; a circuit-breaker that fails fast after N consecutive failures; a user-facing graceful degradation message.
- **Impact:** Without these, any external service degradation causes indefinite user hangs, cascading queue failures, and possible orphaned billable jobs.

### U5 — The pre-merge quality gate process is broken
**All three models identified the meta-process failure as a finding in its own right.**
- **What it is:** A formal two-cycle multi-model audit was executed with no code artifact in either cycle. The process accepted and processed an empty submission without hard rejection.
- **File/Location:** Release process / CI pipeline configuration
- **What to change:** The audit pipeline must hard-fail and block reviewer invocation if `THE CODE` section is empty or contains the placeholder string `(No code files found`. This check must precede any AI model invocation.
- **Impact:** A quality gate that passes empty submissions provides false assurance and wastes review capacity. It is more dangerous than no gate, because it creates an audit paper trail for unreviewed code.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Multi-step AI pipeline requires atomic workflow with rollback (Gemini + GPT-4o)
- **What it is:** The TTS → avatar → lip-sync pipeline is a multi-step, multi-vendor workflow. A failure at step 3 (lip-sync) after step 1 (TTS) and step 2 (avatar) have already executed and incurred charges creates orphaned billable artifacts.
- **File/Location:** Background job / orchestration layer (unknown — no code submitted)
- **What to change:** Implement a transactional saga or state-machine pattern for the pipeline. Each step must record its state. On failure, compensating actions must clean up upstream artifacts (delete temp audio, cancel pending avatar renders). Define explicit rollback paths for each step.
- **Consensus assessment:** Implement. This is a correctness and financial integrity requirement, not speculation.

### M2 — Temporary file generation must use UUIDs for concurrency safety (Gemini + Grok)
- **What it is:** At ~1000 concurrent users, any temp file (audio clips, video frames) generated without globally unique names risks one user's process overwriting another's.
- **File/Location:** File I/O layer / temp file management (unknown — no code submitted)
- **What to change:** All temporary artifacts must be namespaced with a UUID tied to the session ID. Temp file cleanup must occur on both success and failure paths.
- **Consensus assessment:** Implement unconditionally.

### M3 — Input validation including length limits is required (Gemini + Grok)
- **What it is:** A terminal accepting user text input with no length cap can trigger arbitrarily expensive TTS calls. Empty input must also be handled without crashing.
- **File/Location:** Input validation layer / terminal route handler (unknown — no code submitted)
- **What to change:** Define and enforce minimum and maximum input lengths. Sanitize input for injection vectors. Return a user-friendly validation error for out-of-range input before any API call is made.
- **Consensus assessment:** Implement. This is both a security and a cost-control requirement.

### M4 — DB indexing on all sortable/filterable columns is unverified (GPT-4o + Gemini)
- **What it is:** With ~1000 concurrent users, any unindexed sort or filter on a high-write table will cause full table scans and severe query latency.
- **File/Location:** Database migrations (unknown — no code submitted)
- **What to change:** Every column used in `ORDER BY`, `WHERE`, or `JOIN` conditions in terminal-related queries must have a confirmed index. This must be validated in migration files.
- **Consensus assessment:** Implement. Standard production-readiness requirement.

### M5 — Structured logging, trace IDs, and failure metrics are unspecified (GPT-4o + Grok)
- **What it is:** No observability strategy is present in the submitted materials. For a multi-step AI pipeline at scale, correlating failures across TTS/avatar/lip-sync without trace IDs is operationally infeasible.
- **File/Location:** Logging configuration / middleware (unknown — no code submitted)
- **What to change:** Every request must carry a trace ID through all pipeline steps. Failures at each step must emit structured log events. Key metrics (API call latency, failure rates, queue depth) must be instrumented.
- **Consensus assessment:** Implement before production deployment.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — User experience latency thresholds must be defined (Grok only)
- **What it is:** Grok noted that for a terminal interface specifically, latency is not just a performance metric but a UX perception issue. Waiting for HeyGen avatar rendering without progress feedback makes the product feel broken regardless of correctness.
- **Assessment:** **Implement.** This is a valid and under-discussed point. Define acceptable latency thresholds (e.g., TTS response < 2s, avatar render status update < 500ms polling) and implement a status/progress feedback mechanism for long-running pipeline steps. Users must know their request is processing, not hung.

### UI2 — Audit trail for financial disclaimer acknowledgment (Grok only)
- **What it is:** If the terminal provides financial intelligence and disclaimers are legally required (e.g., "not financial advice"), user acknowledgment of those disclaimers must be logged to create a defensible audit trail.
- **Assessment:** **Investigate further.** This is a high-quality legal risk observation. However, it depends on: (a) whether applicable laws actually require disclaimers (unresolved until U2 is addressed), and (b) whether the terminal's outputs constitute financial advice under relevant jurisdiction. Do not implement blindly — resolve U2 first, then determine if disclaimer logging is legally required.

### UI3 — External API SLA contingency plan / fallback providers (Grok only)
- **What it is:** Grok noted that dependency on ElevenLabs, HeyGen, and Wav2Lip without documented contingency creates a single-point-of-failure risk if any vendor has an outage or discontinues service.
- **Assessment:** **Investigate further.** This is a valid business continuity concern for a production product. For a v1 launch, a graceful degradation path (e.g., text-only mode if TTS is unavailable) may be sufficient. Full alternative-provider redundancy is likely a post-launch consideration. Document the risk; define the degradation behavior for v1.

### UI4 — Commit SHA / file manifest should be pinned in the audit package (GPT-4o only)
- **What it is:** GPT-4o recommended that audit packages include a stable git commit SHA and full file manifest so all reviewers are provably reviewing the same revision.
- **Assessment:** **Implement as process standard.** Simple to add; eliminates ambiguity about which revision was reviewed. Add to the audit package template immediately.

### UI5 — Second review cycle initiated without resolving Cycle 1 P0 blocker (Gemini only)
- **What it is:** Gemini specifically called out that initiating Cycle 2 without attaching code after Cycle 1 flagged its absence as P0 Critical indicates a systemic process failure beyond the missing artifact itself.
- **Assessment:** **Implement process fix.** This is a correct and important observation. The team must establish a gate: Cycle 2 cannot be initiated until the Cycle 1 P0 CRITICAL items are resolved. This should be enforced in the CI/CD pipeline or audit orchestration tooling, not left to human discipline.

---

## CONFLICTS (models disagree — tiebreaker)

**There are no genuine conflicts between models in this review cycle.** All three models reached identical conclusions on all primary issues, which is expected given the complete absence of code to create interpretive divergence. The variation across models was in framing, depth, and emphasis — not in contradictory findings.

The closest thing to a divergence: GPT-4o was more emphatic that scores should be described as "unauditable / not reviewable" rather than "0/100," arguing that 0 implies "the code is bad" rather than "the code is unknown." This is a semantic distinction, not a factual conflict. **Resolution:** The score table uses 0/100 for operational consistency with the scoring format. The caveat that these scores reflect package auditability, not implementation quality, is noted at the top of the scores section.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

**None.**

This is not a criticism of the development team — it is a direct consequence of the empty audit package. No component, pattern, implementation choice, test, or configuration has been presented for review. There is nothing to validate as strong.

> **Important:** Do not interpret the absence of validated strengths as evidence of a bad implementation. It is evidence of an unreviewed implementation. When code is submitted, genuine strengths will be identified and protected.

---

## LAW COMPLIANCE CONSENSUS

| Law / Framework | Status | Basis |
|---|---|---|
| GDPR (user session data, voice synthesis) | **NOT ASSESSABLE** | Governing laws section empty; no code submitted |
| CCPA (California user data rights) | **NOT ASSESSABLE** | Same |
| SEC / FINRA (financial advice / intelligence) | **NOT ASSESSABLE** | Same |
| MiFID II (EU financial instruments) | **NOT ASSESSABLE** | Same |
| CFAA (unauthorized access / session controls) | **NOT ASSESSABLE** | Same |
| Any other applicable law | **NOT ASSESSABLE** | Same |

**Final determination:** Law compliance is **entirely unverifiable**. The governing laws section must be populated before any compliance status can be assigned. Given the nature of the product (Bitcoin intelligence, user sessions, voice synthesis, potential financial signals), the legal surface area is broad. This is not a low-risk gap.

---

## SECURITY CONSENSUS

All three models identified the same security risk categories. No code was present to confirm or deny any of these as actual vulnerabilities.

| Risk | Models | Priority | Status |
|---|---|---|---|
| Rate limiting absent on paid API endpoints | All 3 | P0 | Unverified — no code |
| Input validation / injection (terminal input) | All 3 | P0 | Unverified — no code |
| Auth/authz gaps on session endpoints | All 3 | P0 | Unverified — no code |
| Secret / API key leakage in config or logs | All 3 | P0 | Unverified — no code |
| CSRF/XSS in terminal frontend | GPT-4o + Grok | P1 | Unverified — no code |
| Temp file path traversal / UUID collision | Gemini + Grok | P1 | Unverified — no code |
| Session isolation / state contamination | All 3 | P1 | Unverified — no code |
| SQL injection via terminal query inputs | GPT-4o + Grok | P1 | Unverified — no code |

**Security consensus:** Eight distinct security risk categories have been identified speculatively. None can be confirmed without code. All eight must be explicitly verified in the next audit cycle once code is submitted.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2 or more models as missing from a truly world-class "Bloomberg Terminal"-level product:

| Gap | Models | Notes |
|---|---|---|
| Explicit DB indexes on all sort/filter columns | GPT-4o + Gemini | Table scans at 1000 concurrent users are unacceptable |
| Request timeouts + retries + circuit breaking for all external APIs | All 3 | Non-negotiable for production reliability |
| Background job isolation for GPU/video/TTS workloads | GPT-4o + Gemini | Heavy workloads must not block web request threads |
| Per-user rate limiting and quota enforcement | All 3 | Financial protection and abuse prevention |
| Structured logs, trace IDs, failure metrics | GPT-4o + Grok | Operational visibility at scale requires full observability |
| Tests covering core session-terminal flows and failure modes | All 3 | Quality gate is meaningless without test coverage evidence |
| Atomic multi-step pipeline with rollback and orphan cleanup | Gemini + GPT-4o | Saga pattern required for TTS→avatar→lip-sync |
| Input length validation and cost controls | Gemini + Grok | Prevent runaway API spend from unconstrained input |
| UUID-namespaced temp files for concurrency safety | Gemini + Grok | Required at 1000 concurrent users |
| Progress/status feedback for long-running pipeline operations | Grok + (implied by all) | UX perception of "world-class" depends on this |

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Halt audit process; attach complete git diff or changed file set for `feature/session1-terminal` before any further review | Audit package → `THE CODE` section | All 3 | No forensic review is possible without implementation artifacts; two cycles have been wasted |
| **P0 CRITICAL** | Hard-reject audit packages with empty `THE CODE` section at pipeline level before AI models are invoked | CI/audit orchestration pipeline | All 3 | Quality gate with empty submissions provides false assurance — more dangerous than no gate |
| **P0 CRITICAL** | Populate `GOVERNING LAWS` section with all applicable legal frameworks before development is considered complete | `docs/gospels/SESSION_1_TERMINAL_SPEC.md` → GOVERNING LAWS | All 3 | Bitcoin intelligence + user sessions + voice synthesis = broad legal surface; compliance cannot be verified against undefined requirements |
| **P0 CRITICAL** | Define and implement per-user rate limits and hard quota caps for all paid external APIs (ElevenLabs, HeyGen, Wav2Lip) | API integration layer / rate limiting middleware (location TBD) | All 3 | A single runaway session can exhaust paid API budgets in minutes |
| **P0 CRITICAL** | Define and implement timeouts, exponential-backoff retries, and circuit breakers for every external API call | Service wrappers for ElevenLabs, HeyGen, Wav2Lip (location TBD) | All 3 | External service degradation must not cause indefinite user hangs or cascading failures |
| **P1 HIGH** | Implement atomic saga / state-machine pattern for TTS → avatar → lip-sync pipeline with compensating rollback at each step | Background job / orchestration layer (location TBD) | Gemini + GPT-4o | Partial pipeline failures create orphaned billable artifacts and inconsistent state |
| **P1 HIGH** | Namespace all temp files with session-scoped UUIDs; ensure cleanup on both success and failure paths | File I/O / temp file management (location TBD) | Gemini + Grok | At 1000 concurrent users, non-unique temp file names cause cross-session data corruption |
| **P1 HIGH** | Enforce input validation: minimum/maximum length, sanitization, rejection before any API call | Terminal route handler / input validation layer (location TBD) | Gemini + Grok | Prevents empty-input crashes, injection attacks, and unbounded API spend |
| **P1 HIGH** | Confirm DB indexes exist for all columns used in ORDER BY, WHERE, JOIN in terminal-related queries | Database migrations (location TBD) | GPT-4o + Gemini | Unindexed sort/filter columns cause full table scans at scale |
| **P1 HIGH** | Implement structured logging with trace IDs propagated through all pipeline steps; instrument key metrics | Logging config / middleware (location TBD) | GPT-4o + Grok | Without trace IDs, correlating failures across TTS/avatar/lip-sync at scale is operationally infeasible |
| **P1 HIGH** | Include comprehensive tests covering happy path, API failure modes, empty input, concurrent sessions | `tests/` directory for session1-terminal | All 3 | Quality gate is meaningless without test coverage demonstrating failure handling |
| **P1 HIGH** | Pin git commit SHA and full changed-file manifest in audit package header | Audit package template | GPT-4o (unique) | Ensures all reviewers provably review identical revision; eliminates audit ambiguity |
| **P1 HIGH** | Define and implement user-facing progress/status feedback for long-running pipeline operations (e.g., avatar rendering) | Terminal frontend / job status endpoint (location TBD) | Grok + implied by all | Long operations without feedback make a "Bloomberg Terminal"-level product feel broken |
| **P2 MEDIUM** | Isolate background GPU/video/TTS jobs from web request threads | Job queue configuration (location TBD) | GPT-4o + Gemini | Heavy workloads on web threads degrade response times for all concurrent users |
| **P2 MEDIUM** | Document contingency/degradation plan for external API outages (e.g., text-only fallback if TTS unavailable) | `docs/architecture/session1-terminal.md` | Grok (unique) | Single-vendor dependency without degradation path is a business continuity risk |
| **P2 MEDIUM** | Implement audit trail for financial disclaimer acknowledgment if applicable laws require it | Session/user interaction log (location TBD — resolve U2 first) | Grok (unique) | Investigate after governing laws are defined; may be legally required for financial intelligence output |
| **P2 MEDIUM** | Enforce Cycle 2 initiation gate: require P0 items from Cycle 1 to be resolved before second cycle begins | Audit orchestration process | Gemini (unique) | Prevents repeated empty-package review cycles; protects review capacity |

---

## CYCLE 2 VERDICT

**This code is not production-ready. It is not audit-ready. It is not review-ready.**

After two full cycles of three-model independent review, the state of this submission is unchanged from Cycle 1: the audit package contains no code, no governing laws, no tests, no config, and no implementation artifacts of any kind.

**The absolute final blockers before this feature can be considered for any further review:**

1. **The complete changed file set for `feature/session1-terminal` must be attached.** Without this, every other action item in this report is speculative. The implementation may already be excellent or may be catastrophic — it is currently unknowable.

2. **The governing laws section must be populated.** A financial intelligence product touching user data, voice synthesis, and Bitcoin signals cannot be shipped without a defined legal framework.

3. **The audit pipeline must be fixed to hard-reject empty submissions.** This is not optional process hygiene — it is a prerequisite for the quality gate to have any meaning.

Only after these three conditions are met can a substantive audit begin. At that point, the P1 items above become the primary implementation review targets.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/SESSION_1_TERMINAL_SPEC.md.
Read ~/protocol_pulse/docs/audits/session1-terminal_CONSENSUS_C2.md.

This is the FINAL PASS for session1-terminal.
The feature was reviewed by 3 independent AI models across 2 cycles.
No code was present in either cycle. You are now implementing the feature
AND addressing all consensus findings simultaneously.

PREREQUISITE GATES (verify before writing any code):
1. Confirm GOVERNING LAWS section of SESSION_1_TERMINAL_SPEC.md is populated.
   If empty, STOP and request legal framework before proceeding.
2. Confirm you have the full feature requirements in SESSION_1_TERMINAL_SPEC.md.
   If spec is incomplete, STOP and request completion.

PRIORITY ACTION PLAN — implement every P0 and P1 item:

P0 CRITICAL | Implement per-user rate limiting and hard quota caps for ElevenLabs

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles. It matched GPT-4o's discipline in refusing to fabricate findings, while surpassing both competitors on **depth** (atomicity/saga pattern for the TTS→Avatar→Lip-sync pipeline), **actionability** (specific legal frameworks like SEC/FINRA/MiFID II, UUID isolation for concurrency), and **completeness** (thorough section-by-section pre-emptive checklist rather than a flat refusal or loose speculation). In Cycle 2, Gemini explicitly credited rival models' superior points by name — demonstrating calibrated self-awareness that itself reflects analytical rigor.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered list — implement unconditionally before any merge of `feature/session1-terminal`.

---

## PRIORITY 0 — PROCESS BLOCKERS (must resolve before any other work)

### P0-1 — Attach actual code to the audit pipeline
- The `THE CODE` section must contain the complete git diff or full changed file set for `feature/session1-terminal`
- No audit finding below this line has been verified against real implementation
- **Gate:** Do not merge. Do not re-run audit. Attach code first.

### P0-2 — Define governing laws before a single line ships to production
- The `GOVERNING LAWS` section is empty
- For a Bitcoin intelligence product, the probable applicable frameworks are: **SEC, FINRA, MiFID II, FinCEN/BSA, GDPR/CCPA**
- Legal counsel must confirm which apply and sign off before production deployment
- **Gate:** Compliance is structurally unassessable until this is resolved

---

## PRIORITY 1 — FINANCIAL & OPERATIONAL EXISTENTIAL RISKS

### P1-1 — Rate limiting and quota enforcement on all paid external APIs
- ElevenLabs (TTS), HeyGen (avatar), Wav2Lip each carry per-call costs
- Without hard caps, a single malicious or runaway session can exhaust monthly API budgets in minutes
- **Implementation:** Per-user per-minute call caps enforced server-side, hard monthly budget ceilings with automated shutoff, alerting at 50%/80%/100% thresholds

### P1-2 — Multi-step pipeline atomicity and rollback (Saga pattern)
- The TTS → Avatar → Lip-sync pipeline is multi-step with external charges at each stage
- A failure at step 3 (Lip-sync) must trigger compensating rollback: cancel/delete HeyGen job, delete orphaned TTS audio, refund any internal credit
- **Implementation:** Implement a transactional saga or explicit state machine with rollback handlers at each stage transition; never leave pipeline in a partial-success state

---

## PRIORITY 2 — CONCURRENCY & RELIABILITY

### P2-1 — UUID isolation for all temporary files
- At ~1000 concurrent users, any shared temp file namespace causes silent data corruption
- Audio clips, video frames, and lip-sync outputs must use per-session UUIDs in path construction
- **Implementation:** `/{tmp}/{session_uuid}/{artifact_type}/{uuid4}.ext` — no shared paths, no predictable filenames

### P2-2 — Timeouts, retries, and circuit breakers for all external service calls
- ElevenLabs, HeyGen, and Wav2Lip are network-bound; absence of timeouts causes thread exhaustion
- **Implementation:** Per-call timeout (recommend ≤10s for TTS, ≤30s for avatar/video), exponential backoff with jitter on retry (max 3 attempts), circuit breaker opens after 5 consecutive failures, falls back to degraded mode with user notification

### P2-3 — Session isolation under concurrent load
- Terminal sessions must carry no shared mutable state between users
- **Implementation:** Audit every in-memory cache, global variable, and singleton for thread-safety; enforce session-scoped state containers only

---

## PRIORITY 3 — SECURITY

### P3-1 — Input validation and injection prevention
- Terminal-style interfaces are high-risk surfaces for command injection, SQL injection, and prompt injection against AI backends
- **Implementation:** Whitelist-based command parser, parameterized queries only, strict length limits on all user inputs, sanitize before passing to any external API

### P3-2 — Authentication and authorization gates on all terminal endpoints
- Every route in `session1-terminal` must require authenticated session
- **Implementation:** Middleware-level auth check, no security-by-obscurity, verify ownership of session ID on every request

### P3-3 — Secret and credential hygiene
- No API keys (ElevenLabs, HeyGen) in source, logs, or error responses
- **Implementation:** Secrets manager or environment variables only, log scrubbing middleware, ensure keys are not echoed in stack traces

---

## PRIORITY 4 — PERFORMANCE & DATABASE

### P4-1 — DB indexes on all sort/filter columns
- Any terminal displaying market data, transaction history, or ranked lists will sort/filter at query time
- Missing indexes cause full-table scans that collapse under load
- **Implementation:** Audit every `ORDER BY`, `WHERE`, and `GROUP BY` column; add composite indexes where multi-column filtering occurs; verify with `EXPLAIN ANALYZE`

### P4-2 — N+1 query elimination
- List views fetching related objects in a loop will degrade severely at scale
- **Implementation:** Audit all ORM queries in terminal data-fetch paths; replace with `JOIN`-based or batch-fetch queries; add query count assertions to tests

---

## PRIORITY 5 — FRONTEND & UX RESILIENCE

### P5-1 — Loading, error, and empty states on every terminal view
- A Bloomberg Terminal-grade product must never show a blank screen or raw exception
- **Implementation:** Every async data fetch must have: (a) loading skeleton, (b) error state with actionable message, (c) empty state with guidance — no exceptions

### P5-2 — Input length and cost controls visible to user
- Users must know if their input will trigger a billable API call and what limits apply
- **Implementation:** Character counters, cost estimates where applicable, hard client-side and server-side length enforcement

---

## PRIORITY 6 — OBSERVABILITY (prerequisite for production confidence)

### P6-1 — Structured logging with session and request correlation IDs
- Without correlated logs, debugging multi-step pipeline failures in production is effectively impossible
- **Implementation:** Every log line in the TTS/avatar/lip-sync pipeline must carry `session_id`, `request_id`, `pipeline_stage`, and `external_service` fields

### P6-2 — Alerting on pipeline failure rates and API cost anomalies
- Silent failures and runaway costs are the two most likely production incidents
- **Implementation:** Alert on: pipeline failure rate >1%, API spend rate exceeding baseline by >2x, circuit breaker open events, session error rate spikes

---

## ENFORCEMENT GATE

```
DO NOT MERGE feature/session1-terminal until:
  [ ] P0-1: Code attached to audit and re-reviewed
  [ ] P0-2: Governing laws confirmed by legal
  [ ] P1-1: API rate limiting implemented and tested
  [ ] P1-2: Pipeline saga/rollback implemented and tested
  [ ] P2-1: UUID file isolation verified
  [ ] P2-2: Timeouts/retries/circuit breakers in place
  [ ] P3-1–P3-3: Security controls verified
  [ ] P4-1–P4-2: DB performance verified via EXPLAIN ANALYZE
  [ ] P5-1–P5-2: All UI states implemented
  [ ] P6-1–P6-2: Observability confirmed in staging
```