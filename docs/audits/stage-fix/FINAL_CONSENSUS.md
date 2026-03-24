# CONSENSUS REPORT — STAGE-FIX — CYCLE 2
Generated: 2026-03-24 19:41
Models: Grok, Gemini (+1 failed — GPT-4o rate limit exceeded)

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok | Consensus |
|------------------|--------|--------|------|-----------|
| Correctness      | 4/10   | N/A    | 5/10 | **4/10**  |
| Law Compliance   | 0/10   | N/A    | 0/10 | **0/10**  |
| Security         | 2/10   | N/A    | 4/10 | **3/10**  |
| Frontend Quality | 5/10   | N/A    | 6/10 | **5/10**  |
| Overall          | 3/10   | N/A    | 5/10 | **4/10**  |

> **Scoring note:** GPT-4o failed due to token rate limit. Consensus scores are derived from two models only. Where models diverge, the lower score is weighted more heavily given the security-critical nature of the findings — particularly Gemini's observation that the avatar server is a public-facing internet service, which substantially elevates all security findings.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — Race Condition: Queue Read-Modify-Write Is Not Atomic
- **File:** `services/stage_broadcast_service.py`, lines 122–144
- **What it is:** `_add_to_queue()` performs read → modify → write using `fcntl` locks, but the lock is released between the read and write phases. Two concurrent cron instances (running every 5 minutes, overlap is common) can both read identical queue state, both append their item, and the second writer silently overwrites the first's addition. Broadcast segments are lost with no error.
- **What to change:** Refactor so a single `fcntl.LOCK_EX` context manager wraps the entire read-modify-write sequence as one atomic operation. Do not release the lock between phases. Add a stale-lock timeout to prevent permanent deadlock if a process crashes mid-write.

### U2 — No Authentication on Any Avatar Server Endpoint
- **File:** `oracle/avatar_server.py`, all routes (including `/generate`, `/oracle/chat`)
- **What it is:** The avatar server — confirmed by Gemini to be internet-facing at `https://avatar.protocolpulse.io` — exposes routes that trigger calls to paid third-party APIs (Anthropic Claude, ElevenLabs TTS) with zero authentication. Any actor on the internet can invoke these endpoints freely.
- **What to change:** Implement shared-secret token authentication at minimum (`X-Internal-Token` header checked as middleware on all routes). For the `/oracle/chat` endpoint, this is a P0 financial and security emergency. A compromised key or even unintentional public discovery could drain API budgets within minutes.

### U3 — No Server-Side Rate Limiting on Paid-API-Backed Endpoints
- **File:** `oracle/avatar_server.py`, all routes
- **What it is:** Directly consequent to U2. Without authentication, rate limiting cannot be user-scoped. Even with authentication added, no server-side per-client or global rate limiting exists to cap spending on paid APIs.
- **What to change:** Add server-side rate limiting (e.g., Flask-Limiter or a Redis-backed sliding window) on all endpoints that trigger paid API calls. Set hard caps per token/IP and global daily budget limits. Note: Grok correctly observed that the frontend (`templates/stage.html`, line 1373) implements client-side cooldowns, but these are trivially bypassed and do not constitute server-side protection.

### U4 — Silent API Failure Returns Zeroed Data Instead of Failing Loudly
- **File:** `services/stage_brief_pipeline.py`, lines 113–115; `services/stage_broadcast_service.py`, line 186
- **What it is:** When BTC price or other data fetches fail (network timeout, HTTP error, etc.), functions return zeroed-out dictionaries silently. The pipeline continues, generates a brief using price=0, and publishes it. No critical alert is raised. Users receive factually incorrect intelligence.
- **What to change:** Replace silent fallback returns with explicit exception raising (or at minimum `logging.critical()` + a hard abort flag). Briefs should not be generated or published if foundational data is unavailable. Implement a minimum-data-quality gate before script generation proceeds.

### U5 — Brief Type Determined by Wall-Clock Time at Start of Long-Running Process
- **File:** `services/stage_brief_pipeline.py`, lines 713–720
- **What it is:** The `brief_type` (morning/midday/evening) is set from `now.hour` captured at function start. If data-gathering and LLM scripting take 2–5 minutes and the job starts near a boundary (e.g., 09:58 UTC), the brief is generated as "morning" but should be "midday." This is a guaranteed failure mode in production.
- **What to change:** Pass `brief_type` as an explicit command-line argument from the scheduler (cron). Remove the time-inference logic entirely. The scheduler knows what it's scheduling; the pipeline should not re-derive it.

---

## MAJORITY FINDINGS (both models flagged — implement)

> With only two models, all shared findings are unanimous. The following were raised by both but with different emphasis levels; they are presented here as a structured sub-tier for implementation ordering.

### M1 — No File Locking on `latest.json` Write
- **File:** `services/stage_brief_pipeline.py`, line 795
- **Both models noted:** `latest.json` is written without `fcntl` lock protection, unlike other shared files in the service. Concurrent brief generations (e.g., if the scheduler fires twice) can corrupt or overwrite this file.
- **Fix:** Wrap the write in an exclusive `fcntl.LOCK_EX` lock, consistent with the approach already used elsewhere in the codebase.

### M2 — Brittle JSON Structure Guessing in `_load_pulse_check_script`
- **File:** `services/stage_brief_pipeline.py`, lines 225–293
- **Both models noted:** The function iterates through a list of magic keys to guess the structure of an upstream `script.json`. If the upstream format changes, it silently falls back to dumping raw JSON into the LLM prompt, producing low-quality or nonsensical briefs.
- **Fix:** Define and enforce a formal data contract (schema) for `script.json`. Validate the file on load and fail explicitly if the schema doesn't match, rather than silently degrading output quality.

---

## UNIQUE INSIGHTS (single model — evaluate carefully)

### [GEMINI ONLY] — Fragile Greedy Regex in LLM Intel Extraction
- **File:** `services/stage_brief_pipeline.py`, line 404
- **What it is:** `re.search(r'\{[\s\S]*\}', raw)` is greedy and will capture everything between the first `{` and last `}` in the LLM response. If the LLM includes explanatory prose with curly braces before or after the main JSON object, the regex captures an invalid string and `json.loads` fails, aborting intel extraction silently.
- **Assessment: IMPLEMENT.** This is a latent but high-probability failure. LLMs frequently include commentary. Replace with structured output parsing: either prompt the LLM to return JSON inside a markdown code fence (` ```json `) and extract from that, or use the Anthropic API's native structured output/tool-use feature to guarantee valid JSON. This is a production correctness issue, not just a code smell.

### [GEMINI ONLY] — Non-Portable Hardcoded Absolute Paths
- **File:** `oracle/avatar_server.py`, lines 78–80
- **What it is:** Absolute paths referencing `/home/ultron/...` are hardcoded. The application cannot be deployed in a container, a different server, or any non-`ultron` user context without code changes.
- **Assessment: IMPLEMENT.** This is a deployment and maintainability blocker. Replace all hardcoded paths with environment variables loaded from `.env` (e.g., `AVATAR_BASE_PATH`). Add validation at startup that these paths exist and are readable.

### [GEMINI ONLY] — Inconsistent `.env` Loading Across Services
- **File:** `services/stage_brief_pipeline.py`, `services/stage_broadcast_service.py`
- **What it is:** The two services use different logic to locate and parse the `.env` file. This creates a class of configuration bugs where one service works in a given environment and another silently does not.
- **Assessment: IMPLEMENT.** Extract `.env` loading into a shared utility module (`utils/config.py` or similar). Both services import from this single source of truth. This also makes future environment changes one-touch.

### [GEMINI ONLY] — Poor Frontend Error Handling for Video Playback
- **File:** `templates/stage.html`, `playVid` function
- **What it is:** Video playback errors are caught and logged to the console only. Users see a broken/blank player with no explanation, no retry prompt, and no fallback message.
- **Assessment: IMPLEMENT (P2).** Add a visible, user-facing error state to the video player component. At minimum: a toast/banner indicating the segment failed to load, with a retry button. This is table-stakes UX for a media product.

### [GROK ONLY] — Potential Deadlock if Process Holding `_render_semaphore` Crashes
- **File:** `oracle/avatar_server.py`, lines 807–811, 929–932
- **What it is:** GPU access is controlled via a semaphore. If the process holding it crashes or hangs, no mechanism releases the lock, and all subsequent requests block permanently.
- **Assessment: IMPLEMENT.** Add a timeout to semaphore acquisition (already noted with `LOCK_TIMEOUT`; verify it is enforced on the acquire side). Implement a periodic watchdog or heartbeat that detects and releases stale locks. Log a critical alert when timeout is triggered.

### [GROK ONLY] — Inefficient In-Memory Frame Accumulation in `wav2lip_generate`
- **File:** `oracle/avatar_server.py`, lines 301–402
- **What it is:** Video frames are accumulated in a Python list before encoding. For 30-second clips at 30fps, this is ~900 frames held in RAM simultaneously.
- **Assessment: INVESTIGATE FURTHER.** Profile actual memory usage under load before investing in a streaming refactor. If the server has sufficient RAM and this service does not run concurrent jobs (semaphore-gated), the risk may be acceptable. Flag for future optimization sprint if memory monitoring shows pressure.

### [GROK ONLY] — Insufficient Sanitization of `avatar_source` Path
- **File:** `oracle/avatar_server.py`, lines 867–869
- **What it is:** While `avatar_source` is checked against `AVATAR_SOURCES` dictionary, the realpath check (lines 144–150) may not fully mitigate path traversal if the dictionary itself is extended dynamically or via config.
- **Assessment: IMPLEMENT with low effort.** Ensure `AVATAR_SOURCES` is a static constant, never modified at runtime. Add an explicit assertion at server startup that all values in `AVATAR_SOURCES` resolve to paths within a known base directory.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1 — Severity of Rate Limiting Finding (Grok vs. Gemini)
- **Grok:** Partially agreed on rate limiting, noting the frontend already implements client-side cooldowns and 429 handling, suggesting some protection exists.
- **Gemini:** Treated the absence of server-side rate limiting as P0 critical, noting client-side controls are trivially bypassed.
- **Tiebreaker: Gemini is correct.** Client-side rate limiting provides zero protection against a scripted caller. Given that the avatar server is internet-facing and triggers paid API calls, server-side rate limiting is non-negotiable and belongs at P0 alongside authentication.

### Conflict 2 — Overall Severity Score (Grok 5/10 vs. Gemini 3/10)
- **Grok** scored the codebase more leniently across all dimensions.
- **Gemini** downgraded significantly upon recognizing the avatar server is public-facing.
- **Tiebreaker: Gemini's scores are more accurate.** The public-facing nature of an unauthenticated API-calling endpoint is a binary production blocker. A 5/10 overall implies the code is "halfway to production-ready," which is materially misleading given that deploying it as-is would create immediate financial and security exposure. The consensus overall score of 4/10 is a compromise that still communicates "not shippable."

---

## VALIDATED STRENGTHS (both models agree — do NOT change)

1. **`fcntl` Lock Usage in `stage_broadcast_service.py`:** The existing file-locking pattern in the broadcast service's queue read/write functions is architecturally sound. The fix required is to extend its scope, not replace it.
2. **Priority Queue Design in `stage_broadcast_service.py`:** The signal priority ordering (price alerts → thought leaders → metrics → fillers) with TTL expiry is a well-designed queue architecture for a real-time broadcast system.
3. **Wav2Lip Chunking Logic:** Chunking long audio for Wav2Lip rendering (`stage_brief_pipeline.py`, lines 503–694) is a correct and thoughtful approach to handling the model's limitations. Do not refactor this.
4. **Frontend Client-Side Cooldowns and 429 Handling (`templates/stage.html`, line 1373, 999):** The existing client-side rate limiting logic and graceful 429 response handling are good defensive patterns and should be preserved when adding server-side controls.
5. **Semaphore-Based GPU Access Control (`oracle/avatar_server.py`):** Using a semaphore to serialize GPU access is the correct pattern for a single-GPU server. The pattern is right; it only needs stale-lock protection added.

---

## LAW COMPLIANCE CONSENSUS

**Determination: Unassessable — specification is incomplete.**

Both models independently scored Law Compliance at 0/10, but both explicitly noted this reflects the absence of governing law specifications in the audit brief, not confirmed violations.

**Known gaps that must be clarified before shipping:**
- If Protocol Pulse distributes Bitcoin price data or market intelligence to users in regulated jurisdictions, financial information service regulations (e.g., FCA in UK, SEC/CFTC guidance in US) may apply.
- If user interaction data is stored (oracle chat history, session data), GDPR/CCPA data retention and consent obligations apply. No privacy policy, consent mechanism, or data deletion pathway was observed in the reviewed code.
- Audio/video content generated by AI and published to users may trigger emerging AI transparency disclosure requirements (EU AI Act transparency obligations for synthetic media).

**Recommendation:** Obtain a legal review covering financial data distribution, AI-generated content disclosure, and user data handling before public launch.

---

## SECURITY CONSENSUS

Both models flagged the same core vulnerabilities. Priority order by consensus:

1. **[P0 — CRITICAL]** No authentication on internet-facing, paid-API-backed endpoints (`oracle/avatar_server.py`). Financial and API-abuse risk. Immediate exposure.
2. **[P0 — CRITICAL]** No server-side rate limiting on the same endpoints. Directly enables budget exhaustion attacks.
3. **[P1 — HIGH]** Non-atomic queue write enables silent data loss under concurrent access (`stage_broadcast_service.py`, lines 122–144).
4. **[P1 — HIGH]** Silent API failure returns incorrect data to production publishing pipeline (`stage_brief_pipeline.py`, line 115).
5. **[P2 — MEDIUM]** Hardcoded absolute paths create deployment attack surface if environment assumptions are wrong (`avatar_server.py`, lines 78–80).
6. **[P2 — MEDIUM]** `avatar_source` path sanitization insufficient for dynamic config extension (`avatar_server.py`, lines 867–869).
7. **[P2 — MEDIUM]** Stale semaphore lock can cause permanent GPU denial-of-service (`avatar_server.py`, lines 807–811).

---

## WORLD-CLASS GAP CONSENSUS

Items raised by 2+ models as missing from a truly world-class product:

### Gap 1 — No Observability Infrastructure
Both models implicitly flagged this through repeated "silent failure" findings. A world-class pipeline has structured logging, distributed tracing (e.g., OpenTelemetry), and alerting (e.g., PagerDuty/Sentry) on every external API call, every queue operation, and every file write. Currently, failures are invisible until a user notices wrong data.

### Gap 2 — No Data Contract Between Services
Both models flagged the brittle `_load_pulse_check_script` parsing. A world-class multi-service architecture defines and validates schemas (e.g., Pydantic models, JSON Schema) at service boundaries. Neither service should guess at the structure of another service's output.

### Gap 3 — No Retry / Circuit Breaker Pattern on External APIs
Both models flagged single-attempt API calls with no retry logic. A world-class system implements exponential backoff with jitter on transient failures and a circuit breaker to prevent cascading failures when an upstream is degraded. The BTC price API, Anthropic, ElevenLabs, and all other external calls need this treatment.

### Gap 4 — No End-to-End Testing or Regression Coverage
Neither model identified any test files in scope. A world-class media pipeline has integration tests that mock external APIs and verify that a full brief cycle (fetch → script → TTS → video → publish) completes correctly and produces valid output artifacts. The `regression_test.sh` reference in the prompt suggests something exists, but it is not in scope and its coverage is unknown.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Implement shared-secret token authentication on all routes | `oracle/avatar_server.py`, all routes | Both | Public-facing service triggers paid APIs with zero auth — immediate financial/security exposure |
| **P0 CRITICAL** | Implement server-side rate limiting on all paid-API routes | `oracle/avatar_server.py`, all routes | Both | Direct consequence of no auth; trivially bypassed client-side controls offer no protection |
| **P1 HIGH** | Make queue read-modify-write atomic with single `fcntl.LOCK_EX` | `services/stage_broadcast_service.py`, lines 122–144 | Both | Concurrent cron jobs silently drop broadcast segments |
| **P1 HIGH** | Pass `brief_type` as explicit CLI argument from scheduler | `services/stage_brief_pipeline.py`, lines 713–720, 814 | Both | Time-boundary drift guarantees mislabeled briefs in production |
| **P1 HIGH** | Fail loudly (not silently) on API data fetch failure | `services/stage_brief_pipeline.py`, line 115; `services/stage_broadcast_service.py`, line 186 | Both | Publishing price=0 briefs is a product correctness failure with reputational risk |
| **P1 HIGH** | Add `fcntl.LOCK_EX` to `latest.json` write | `services/stage_brief_pipeline.py`, line 795 | Both | Unprotected shared file write under concurrent execution |
| **P1 HIGH** | Replace greedy regex with code-fence or structured output JSON extraction | `services/stage_brief_pipeline.py`, line 404 | Gemini | High-probability LLM response format failure silently aborts intel extraction |
| **P1 HIGH** | Replace hardcoded `/home/ultron/...` paths with env vars | `oracle/avatar_server.py`, lines 78–80 | Gemini | Deployment blocker; environment-specific code in a portable service |
| **P2 MEDIUM** | Enforce formal schema validation for `script.json` in `_load_pulse_check_script` | `services/stage_brief_pipeline.py`, lines 225–293 | Both | Silent format guessing degrades brief quality without alerting operators |
| **P2 MEDIUM** | Add error checking for `ffprobe` subprocess call | `services/stage_brief_pipeline.py`, line 595 | Gemini | Unchecked return code produces fallback video with wrong duration |
| **P2 MEDIUM** | Consolidate `.env` loading into shared `utils/config.py` | Both service files | Gemini | Inconsistent config loading causes environment-specific failures |
| **P2 MEDIUM** | Add stale-lock protection and timeout enforcement to `_render_semaphore` | `oracle/avatar_server.py`, lines 807–811, 929–932 | Grok | Process crash leaves GPU permanently locked, blocking all subsequent renders |
| **P2 MEDIUM** | Add user-facing error state to video player on playback failure | `templates/stage.html`, `playVid` function | Gemini | Silent failure leaves users with a blank/broken player and no recourse |
| **P2 MEDIUM** | Assert `AVATAR_SOURCES` is static and all paths resolve within known base dir | `oracle/avatar_server.py`, lines 867–869, 144–150 | Grok | Defense-in-depth against path traversal if config is ever extended |

---

## CYCLE 2 VERDICT

**This code is NOT production-ready.**

The absolute final blockers, in order, are:

1. **The avatar server has no authentication and no rate limiting on internet-facing routes that trigger paid third-party API calls.** This is a P0 security and financial emergency. Deploying to production as-is is equivalent to publishing an open API key. This alone is a hard ship-blocker.

2. **The core publishing pipeline will silently produce and distribute factually incorrect content when data APIs fail.** A Bitcoin intelligence product that publishes price=0 briefs without any alert fails at its most fundamental purpose.

3. **The broadcast queue has a confirmed race condition under normal operating conditions (5-minute cron) that silently drops content.**

All three of these issues are architectural correctness and security failures — not polish items. None require large refactors; all have clear, well-defined fixes. The codebase's core design (chunking, queue priority, semaphore GPU gating) is sound. The path to production is clear: fix P0s, fix P1s, run regression suite, ship.

**Estimated remediation effort: 1–2 focused engineering days for P0+P1 items.**

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/stage-fix_CONSENSUS_C2.md.

This is the FINAL PASS for stage-fix.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement shared-secret token authentication on all routes | oracle/avatar_server.py, all routes | models: both | Public internet-facing service triggers paid APIs (Anthropic, ElevenLabs) with zero auth — immediate financial and security exposure. Add X-Internal-Token header middleware. Reject 401 on all unmatched requests.

P0 CRITICAL | Implement server-side rate limiting on all paid-API-backed routes | oracle/avatar_server.py, all routes | models: both | Client-side cooldowns are trivially bypassed. Use Flask-Limiter or Redis-backed sliding window. Set per-token and global daily budget caps.

P1 HIGH | Make queue read-modify-write atomic with single fcntl.LOCK_EX | services/stage_broadcast_service.py lines 122-144 | models: both | Concurrent cron instances silently drop broadcast segments. Wrap entire read-modify-write in one lock context. Do not release between phases.

P1 HIGH | Pass brief_type as explicit CLI argument from cron scheduler | services/stage_brief_pipeline.py lines 713-720, 814 | models: both | Time-boundary drift (job starts at 13:59, runs 2 min) guarantees mislabeled briefs. Remove time-inference logic. Accept --type morning|midday|evening as required argument.

P1 HIGH | Fail loudly on API data fetch failure — no silent zeroed fallbacks | services/stage

---

# WINNER DETERMINATION

WINNER: Gemini — Gemini consistently identified the highest-severity, most architecturally significant issues that others either missed entirely or caught only partially, including the time-boundary brief-type misclassification (a guaranteed production failure mode), the unchecked `ffprobe` subprocess return code producing silent broken output, and the brittle upstream script parsing as a service contract violation. Critically, Gemini's observation that the avatar server is a public-facing internet service materially elevated the security scoring for the entire audit, demonstrating superior contextual reasoning that shaped the consensus itself.

---

## FINAL SECOND-PASS PRIORITY LIST

### P0 — Fix Immediately (Production-Breaking, Data Loss, or Public Security Exposure)

**P0-1 — Race Condition: Queue Read-Modify-Write (U1)**
- File: `services/stage_broadcast_service.py`, lines 122–144
- Wrap the entire read → modify → write block in a single `fcntl.LOCK_EX` context manager. Do not release between phases. Add a stale-lock timeout (suggest 10s) to prevent deadlock on crash. This is a guaranteed silent data loss bug under normal cron overlap conditions.

**P0-2 — No Authentication on Avatar Server Endpoints (U2)**
- File: `oracle/avatar_server.py`, all routes
- Add token-based authentication (Bearer header, validated against an environment secret) to every route before any other fix. The `/generate` and `/oracle/chat` endpoints are publicly reachable and currently open to arbitrary invocation, cost exploitation, and prompt injection. This is the single highest-severity security finding in the audit.

**P0-3 — Silent API Failure Returns Zeroed Data Without Alerting**
- File: `services/stage_brief_pipeline.py`, lines 113–115 (`_fetch_btc_price`)
- Replace silent return of zeroed dictionary with a raised exception or, at minimum, a `logging.critical()` call followed by pipeline abort. Briefs generated with zeroed BTC data are actively misleading and will reach end users without any system alert.

---

### P1 — Fix Before Next Release (Logic Errors Causing Incorrect Behavior)

**P1-1 — Brief Type Misclassification Across Time Boundaries**
- File: `services/stage_brief_pipeline.py`, lines 711–720
- `brief_type` is determined from `now` captured at function entry. A job starting at 13:59 UTC that runs 2+ minutes will be labeled "midday" when it should be "evening." Pass `brief_type` as an explicit argument from the scheduler rather than inferring it from wall-clock time mid-execution. This is a guaranteed failure mode in production.

**P1-2 — Unchecked `ffprobe` Subprocess Return Code**
- File: `services/stage_brief_pipeline.py`, line 595 (fallback video renderer)
- Add explicit return code checking after the `ffprobe` call. A failure here silently propagates an incorrect default duration into video generation, producing broken output with no error raised. Use `subprocess.run(..., check=True)` or manually inspect `returncode` and raise.

**P1-3 — Brittle Upstream Script Parsing in `_load_pulse_check_script`**
- File: `services/stage_brief_pipeline.py`, lines 225–293
- The function guesses `script.json` structure by iterating a list of possible keys. This violates basic service contract principles and will silently degrade or break when the upstream format changes. Define and validate a fixed schema (use `pydantic` or at minimum a documented required-key contract). Fail loudly on schema mismatch rather than guessing.

---

### P2 — Fix in Current Sprint (Quality, Reliability, Maintainability)

**P2-1 — Missing File Lock on `latest.json` Writes**
- File: `services/stage_brief_pipeline.py`, line 795
- Shared file writes lack the `fcntl` locking that `stage_broadcast_service.py` uses elsewhere. Apply consistent locking strategy across all shared file writes to prevent corruption under concurrent access.

**P2-2 — No Fallback or Enrichment Warning When Pulse Check Script Is Absent**
- File: `services/stage_brief_pipeline.py`, lines 225–293 and line 329
- When `_load_pulse_check_script()` returns `None`, the pipeline logs and continues with degraded context. Add an explicit brief quality flag in output metadata when this occurs so downstream consumers and monitoring can detect low-context brief generation rather than treating degraded output as normal.

**P2-3 — Cron Overlap Risk Has No Concurrency Guard**
- File: Cron configuration (`*/5` schedule)
- The 5-minute cron interval with no PID file or advisory lock means multiple instances routinely overlap. Add a PID-file or `flock`-based guard at the entry point of both pipeline and broadcast service to prevent concurrent execution entirely, reducing the surface area for all race conditions identified above.

---

### P3 — Backlog (Code Health, Hardening, Observability)

- Add structured logging with severity levels and correlation IDs across both services to make production debugging feasible
- Externalize all magic keys, schedule hour boundaries, and file paths to configuration rather than inline constants
- Add integration tests covering the queue read-modify-write path under simulated concurrency
- Document the `script.json` schema contract explicitly so future upstream changes are caught at the boundary rather than inside the consumer
- Audit all remaining `subprocess` calls for unchecked return codes using the same pattern identified in P1-2