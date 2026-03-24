# CONSENSUS REPORT — RENDER-IMPROVEMENT-LOOP — CYCLE 2
Generated: 2026-03-24 05:54
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Integration (Flag/Fire-and-Forget IPC) | 4/10 | 2/10 | 1/10 | **2/10** |
| Qwen Reliability | 4/10 | 4/10 | 3/10 | **4/10** |
| CC Session Detection | 3/10 | 3/10 | 3/10 | **3/10** |
| Token Cost Reality | N/A | 3/10 | 4/10 | **3/10** |
| DIMENSION_MAP Completeness | N/A | 5/10 | 4/10 | **4/10** |
| Overnight Loop Coupling | 1/10 | 2/10 | 2/10 | **1/10** |
| Consensus Failure Handling | N/A | TBD | 3/10 | **3/10** |
| Overall Architecture | N/A | 3/10 | 2/10 | **2/10** |

> **Scoring note:** Gemini's Cycle 2 score for Integration (Flag IPC) rose from 2→4 because the implemented code *avoids* the deadlock failure mode from the spec. Grok went the other direction (2→1) citing new logging gaps. GPT-4o held at 2. Consensus anchors at **2/10** — the fire-and-forget decoupling is a lateral move from blocking-but-loud to non-blocking-but-blind. Both are unacceptable in production.

---

## UNANIMOUS FINDINGS
*(All 3 models agree — implement unconditionally)*

### U1 — Fire-and-Forget / Flag-File IPC Is Critically Broken
**What it is:** The inter-process communication between `overnight_render_loop.py` and the render improvement loop is fundamentally unsafe. In the spec it was a flag-file existence check (prone to stalls, stale flags, race conditions). In the implemented code it is a "fire-and-forget" `.md` write followed by a 30-second sleep — the main loop has **zero confirmation** that the fix was seen, applied, or even attempted. The feedback loop is completely severed.

**File/Line:** `overnight_render_loop.py`, `fire_cc_fix()` function (~line 526–563), flag/handshake check in main iteration loop.

**What to change:**
- Replace the `.md` write + 30s sleep with a **stateful JSON IPC protocol**:
  - `fire_cc_fix` writes `/tmp/fix_request_iterN.json` with `{"status": "pending", "request_timestamp": <ISO>, "iteration": N, "pid": <main_pid>}`
  - The improvement loop overwrites with `{"status": "complete|failed", "completion_timestamp": <ISO>, "dimensions_fixed": [...]}`
  - The main loop, **before** starting render iteration N+1, waits for `fix_request_iterN.json` to reach `"status": "complete"` or `"failed"`, with a **90-minute hard timeout**
  - On timeout: log CRITICAL, send Telegram alert, abort cycle — do not silently continue
  - On startup of `overnight_render_loop.py`: glob and purge all stale `/tmp/fix_request_*.json` and `/tmp/fix_complete_*.json` files

---

### U2 — Qwen / Ollama Has Zero Fault Tolerance
**What it is:** The improvement loop's entire self-healing capability collapses silently if the Ollama service is down, the Qwen model is not loaded, OOMs mid-inference, or returns non-JSON / partial JSON output. No retry, no schema validation, no fallback, no alerting.

**File/Line:** Render improvement loop implementation (un-merged code / GOSPEL spec — the Qwen call site).

**What to change:**
- Wrap every Qwen/Ollama call in a resilience block:
  - Connection timeout: 30s
  - **3 retries with exponential backoff** (2s → 4s → 8s)
  - **JSON schema validation** on every response before use; treat schema violation as a retriable error
  - After 3 exhausted retries: mark affected dimension as `"failed"`, log error with full context, continue to next dimension (graceful degradation — do not halt the loop)
- Add a **pre-flight health check** (`GET localhost:11434/api/tags`) before the loop begins; if Ollama is unreachable, write `"status": "failed"` to the IPC JSON immediately and alert via Telegram

---

### U3 — CC/Tmux Session Detection Is Naive and Deadlock-Prone
**What it is:** All three models flagged that detecting Claude Code sessions by simple `tmux ls` name-matching is dangerously insufficient. Zombie sessions (tmux alive, `claude` process dead or hung) will be incorrectly identified as active, potentially causing the improvement loop to deadlock waiting for a response that will never come, or to skip launching a new session when one is needed.

**File/Line:** Render improvement loop — wherever `tmux list-sessions` / session detection logic lives (GOSPEL spec + implementation).

**What to change:**
- Session detection must perform **process-level verification**:
  1. Check tmux session exists by name
  2. Verify an active `claude` process is running within that session (`tmux list-panes -t <session> -F "#{pane_pid}"` → check `/proc/<pid>/status`)
  3. Check session has had **recent activity** within a configurable window (default: 10 minutes) using `tmux display-message -t <session> -p "#{session_activity}"`
- If session exists but fails liveness checks → kill it (`tmux kill-session -t <session>`), log the zombie kill, and launch fresh
- Hard timeout on waiting for any CC session response: **30 minutes**, after which mark the fix attempt as `"failed"` and write to IPC JSON

---

## MAJORITY FINDINGS
*(2 of 3 models agree — implement unless compelling reason not to)*

### M1 — No Circuit Breaker for Stalled Watchdog (Gemini + Grok)
**What it is:** If the render improvement loop process crashes, is never started, or is persistently broken, the main loop has no circuit breaker. It will burn all `MAX_ITERATIONS` render cycles generating fix requests into a void, grading the same failures over and over, and report a terminal `HOLD`/`DEGRADED` without ever detecting that its repair subsystem was offline the entire time.

**File/Line:** `overnight_render_loop.py`, main iteration loop / `run_single_render`.

**What to change:**
- Add `_consecutive_fix_failures` counter to the main loop state
- After the P0 stateful handshake detects **2 consecutive fix timeouts or failures**: abort the full cycle, send a CRITICAL Telegram alert ("Repair watchdog appears offline — aborting render cycle"), and exit with a non-zero status code
- Reset counter to 0 on any successful fix confirmation

---

### M2 — Hard-Coded 30-Second Sleep Is Architecturally Incorrect (Gemini + Grok)
**What it is:** The current 30-second pause in `fire_cc_fix` is both too short (a complex fix may take 20+ minutes) and too long (a trivial fix wastes 30 seconds of latency). It is a polling anti-pattern masquerading as coordination.

**File/Line:** `overnight_render_loop.py`, ~line 563.

**What to change:**
- Remove the hard-coded `time.sleep(30)` entirely
- Replace with active polling against the IPC JSON file status (as prescribed in U1), with a configurable poll interval (default: 60 seconds) and the 90-minute hard timeout

---

### M3 — No Recovery Tracking for Partial Fixes (Gemini + Grok)
**What it is:** If the improvement loop fixes 3 of 5 flagged dimensions before crashing or timing out, the main loop has no record of which dimensions were already addressed. The next iteration will attempt to fix all 5 again, causing redundant and potentially conflicting patches.

**File/Line:** IPC JSON schema + improvement loop implementation.

**What to change:**
- Extend the IPC JSON schema to include `"dimensions_fixed": []`, `"dimensions_failed": []`, `"dimensions_skipped": []`
- The improvement loop writes these arrays atomically before marking `"status": "complete"` or `"failed"`
- The main loop reads this manifest before triggering a new fix cycle and passes it as context so already-fixed dimensions are excluded

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated individually)*

### UI1 — Stale Fix Applied to Wrong Iteration (Gemini only)
**What it is:** Gemini identified a race condition where if the improvement loop for iteration 2 takes 20+ minutes, the main loop may have advanced to iteration 4. When the backlogged fix finally completes, it patches the codebase against iteration-2 state, which may be incompatible with the current iteration-4 code, producing unpredictable render behavior.

**Assessment: IMPLEMENT.** This is a subtle but real concurrency hazard. The stateful JSON handshake (U1) partially addresses it by enforcing back-pressure (main loop waits for confirmation), but the fix must also include an **iteration number validation**: the improvement loop must refuse to apply a fix if the request's iteration number does not match the current known render iteration. Write `"status": "stale"` to the IPC JSON and alert.

---

### UI2 — Token Cost Reality / Budget Overrun Risk (GPT-4o + Grok, scored as unique framing)
**What it is:** GPT-4o and Grok both touched on token cost, but only Grok gave it a dedicated severity rating. With 4–6 dimensions per cycle at ~$0.04–0.06 per LLM call, plus multi-model consensus calls in the broader audit harness, the $2 soft cap per cycle is likely optimistic. Extended failure-recovery cycles could trigger 2–3x normal call volume.

**Assessment: INVESTIGATE FURTHER.** This is a real operational cost risk but not an architectural blocker. Action: instrument actual token counts per improvement cycle in production for 5 runs, then calibrate the soft cap. Add a **hard cost cap** via environment variable (`MAX_TOKENS_PER_FIX_CYCLE`) that gracefully terminates the improvement loop and marks the fix as `"failed"` if breached.

---

### UI3 — No Logging of Improvement Loop Outcomes in Main Loop (Grok only)
**What it is:** Grok noted that `fire_cc_fix` and the main loop emit no structured log entries confirming whether a fix attempt succeeded, failed, or was never confirmed. Post-incident debugging is therefore blind.

**Assessment: IMPLEMENT.** Structured logging for the IPC handshake is a prerequisite for any production observability. Every state transition in the JSON IPC file should trigger a corresponding `logger.info` / `logger.error` entry with iteration number, timestamp, and outcome. This is low-effort and high-value.

---

## CONFLICTS
*(Models gave contradictory recommendations — tiebreaker applied)*

### C1 — Severity of Decoupled "Fire-and-Forget" vs. Original Blocking Design
- **Gemini:** The decoupled fire-and-forget is *worse* than the original blocking design because silent failures are harder to detect and debug than loud deadlocks. Score raised to 4/10 on the IPC subsystem because at least deadlock is now avoided.
- **Grok:** Score lowered to 1/10 because the new design adds lack of logging on top of broken confirmation, making it strictly worse.
- **GPT-4o:** Held at 2/10, treating both designs as equivalently broken.

**Tiebreaker — Gemini is most technically precise.** The implemented code does eliminate the specific "indefinite stall" failure mode correctly identified in Cycle 1, which is a genuine improvement. However, Grok is correct that trading a loud failure for a silent one is architecturally regressive in a self-healing system where **observability is the product**. The consensus score of **2/10** reflects that both failure modes are unacceptable in production, and the "fix" merely changed the failure character without fixing the root cause.

---

### C2 — Token Cost Severity (MEDIUM vs. HIGH)
- **Grok:** Rates token cost risk as HIGH, with a recommended $5 daily hard cap.
- **GPT-4o:** Rates it MEDIUM, suggests further analysis rather than immediate architectural change.

**Tiebreaker — GPT-4o is correct for now.** Token cost is a real operational risk but not an architectural blocker for initial production readiness. Instrument first, then cap based on real data. Elevate to HIGH if the first 5 production cycles show consistent budget overruns. Implement the hard cap as a configurable env variable regardless.

---

## VALIDATED STRENGTHS
*(All models agree these are already excellent — do NOT change)*

> **Note:** The three models were largely in crisis-finding mode and did not identify subsystems to explicitly protect from modification. However, the following implicit consensus exists:

- **Telegram Alerting Integration:** All three models' mitigations referenced Telegram alerts as the correct notification channel and did not propose replacing it. The alerting hook in `fire_cc_fix` is the right mechanism — extend it, don't replace it.
- **Iteration-Scoped File Naming Convention:** The pattern of scoping IPC/output files by iteration number (e.g., `_iterN`) is correct and should be preserved. The problem is the file *format* and *confirmation mechanism*, not the naming convention.
- **`MAX_ITERATIONS` Guard:** All models accepted the existence of a maximum iteration cap as correct architectural hygiene. Do not remove it; the P0 circuit breaker supplements rather than replaces it.

---

## LAW COMPLIANCE CONSENSUS

| Law / Principle | Status | Finding |
|---|---|---|
| **Single Responsibility** | ❌ VIOLATED | `fire_cc_fix` conflates fix-request writing, Telegram alerting, and (incorrectly) coordination timing in one function |
| **Fail Fast / Loud** | ❌ VIOLATED | Fire-and-forget design fails silently — the antithesis of fail-fast |
| **Idempotency** | ❌ VIOLATED | No protection against duplicate fix requests for the same iteration if the main loop retries |
| **Observability** | ❌ VIOLATED | No structured logging of IPC handshake state transitions |
| **Defense in Depth** | ❌ VIOLATED | Single point of failure on Ollama/Qwen with no fallback |
| **Timeout Everything** | ❌ VIOLATED | No timeout on fix waiting, no timeout on Qwen calls |
| **Clean Startup State** | ❌ VIOLATED | Stale IPC files from previous crashed runs not cleaned on startup |
| **Separation of Concerns** | ✅ COMPLIANT | The improvement loop is a separate process from the render loop — the architecture is correct in principle |
| **Telegram as Alert Bus** | ✅ COMPLIANT | Consistent use of Telegram for human notification is correct |

**Final determination:** 6 of 8 core engineering laws are violated. This is consistent with a **pre-production prototype** grade, not a shippable feature.

---

## SECURITY CONSENSUS

| Issue | Models | Priority |
|---|---|---|
| **`/tmp` IPC files are world-readable** — the fix request JSON may contain render metadata, code snippets, or scoring data that another process or user could read | Implied by all (Gemini most explicit) | P1 |
| **No validation of the fix spec file before execution** — if a malicious or corrupted `.md`/`.json` is written to `/tmp/fix_request_iterN.json`, the improvement loop may execute unvalidated instructions against the codebase | Grok (explicit), Gemini (implied) | P1 |
| **Ollama runs on `localhost:11434` with no authentication** — any process on the machine can submit inference requests | Grok (explicit) | P2 |
| **tmux session names are predictable** — `cc_session` naming is guessable; a runaway or malicious process could inject into or kill the session | All (implied via zombie session discussion) | P2 |

**Priority order:** IPC file permissions → IPC content validation → Ollama access control → tmux session hardening.

---

## WORLD-CLASS GAP CONSENSUS
*(Items 2+ models mentioned as missing from a truly world-class implementation)*

1. **No Feedback Loop Verification** (all 3 models): A world-class self-healing system measures whether its fixes actually *improved* the metric they targeted. The current design has no mechanism to compare the CLIP/quality score before and after a fix, meaning the system cannot learn or calibrate. A fix that makes things worse is indistinguishable from one that makes things better.

2. **No Fix Quality / Regression Guard** (Gemini + Grok): Applying a fix from an LLM to a codebase without running a fast sanity-check render (even a 5-frame preview) before committing to a full render cycle risks the fix introducing a regression worse than the original bug.

3. **No Persistent Fix History / Learning** (Grok + GPT-4o): The system has no memory across nights. A dimension that fails repeatedly should trigger escalation (human review, gospel update), but currently each night starts with zero institutional knowledge of previous failures. A simple append-only `fix_history.jsonl` log would enable pattern detection.

4. **No Stateful Handshake / Confirmation Protocol** (all 3 models): Already captured in U1, but worth restating as a world-class gap: fire-and-forget is not acceptable in any self-healing production system. Confirmation, back-pressure, and outcome tracking are table stakes.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Replace fire-and-forget `.md` write + 30s sleep with stateful JSON IPC handshake (`/tmp/fix_request_iterN.json`); main loop waits for `"complete"/"failed"` before next render; 90-min hard timeout; startup cleanup of stale files | `overnight_render_loop.py`, `fire_cc_fix()` ~L526–563, main iteration loop ~L581 | ALL | The feedback loop is completely severed in current implementation; no confirmation = no self-healing |
| **P0 CRITICAL** | Wrap all Qwen/Ollama calls in resilience block: 30s connection timeout, 3 retries with exponential backoff, JSON schema validation, graceful per-dimension degradation on exhausted retries, pre-flight Ollama health check | Improvement loop — Qwen call site | ALL | Zero fault tolerance on the single most critical external dependency |
| **P0 CRITICAL** | Implement zombie-safe CC/tmux session detection: verify `claude` process liveness within session, check session activity timestamp, auto-kill and relaunch zombie sessions, 30-min hard timeout on waiting for session response | Improvement loop — session detection logic | ALL | Naive `tmux ls` check will deadlock on zombie sessions with no recovery path |
| **P1 HIGH** | Add `_consecutive_fix_failures` circuit breaker: abort cycle and send CRITICAL Telegram alert after 2 consecutive fix timeouts/failures | `overnight_render_loop.py`, main iteration loop | Gemini + Grok | Prevents burning all render cycles when watchdog is silently offline |
| **P1 HIGH** | Remove hard-coded `time.sleep(30)`; replace with active polling on IPC JSON status at 60s intervals with 90-min ceiling | `overnight_render_loop.py`, ~L563 | Gemini + Grok | 30s is simultaneously too short (complex fixes) and architecturally wrong (polling anti-pattern) |
| **P1 HIGH** | Extend IPC JSON schema with `dimensions_fixed`, `dimensions_failed`, `dimensions_skipped` arrays; main loop passes manifest as context to avoid re-fixing already-addressed dimensions | IPC JSON schema + both loop files | Gemini + Grok | Partial fix state is lost on crash; redundant/conflicting patches on retry |
| **P1 HIGH** | Add structured logging for every IPC state transition (pending → waiting → complete/failed/timeout) with iteration number, timestamp, and outcome | `overnight_render_loop.py` + improvement loop | Grok + implied all | Zero observability into fix pipeline makes post-incident debugging impossible |
| **P1 HIGH** | Validate IPC JSON content before the improvement loop acts on it; reject malformed, oversized, or schema-invalid requests; use mode 0600 on all `/tmp` IPC files | Improvement loop — IPC reader | Grok + Gemini (implied) | Security: unvalidated instructions executed against codebase; world-readable fix specs |
| **P1 HIGH** | Add iteration number validation: improvement loop must refuse to apply a stale fix if its request iteration ≠ current render iteration; write `"status": "stale"` and alert | IPC JSON schema + improvement loop | Gemini (unique — but implement) | Race condition: backlogged fix for iter 2 applied to iter 4 codebase causes unpredictable corruption |
| **P2 MEDIUM** | Add hard cost cap env variable (`MAX_TOKENS_PER_FIX_CYCLE`); instrument actual token counts per fix cycle; gracefully terminate and mark `"failed"` if cap is breached | Improvement loop — Qwen call orchestration | GPT-4o + Grok | $2 soft cap is likely optimistic; extended failure cycles could trigger 2–3x normal volume |
| **P2 MEDIUM** | Add `fix_history.jsonl` append-only log persisted across nights; record dimension, fix applied, pre/post score, outcome | New file + both loops | Grok + GPT-4o | Zero institutional memory across nights; same dimensions failing repeatedly cannot be detected or escalated |
| **P2 MEDIUM** | Run a fast sanity-check render (5-frame preview) after applying a fix and before committing to full render cycle; abort and revert if preview score is lower than pre-fix score | Improvement loop — post-fix validation | Gemini + Grok | LLM fix may introduce regression worse than original bug with no guard to catch it |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION-READY.**

After two full cycles of three-model independent review, the verdict is unambiguous. The `render-improvement-loop` feature contains a **fundamental architectural flaw that was not corrected between spec and implementation** — it merely changed character from a loud blocking failure to a silent non-blocking one. The self-healing system, as implemented, cannot verify that it healed anything.

**The single absolute final blocker:** The absence of a stateful confirmation protocol between `overnight_render_loop.py` and the improvement loop means this system will fail silently, waste compute cycles rendering the same broken video repeatedly, and report terminal status codes without ever realizing its repair mechanism was offline. Until P0 Item 1 (stateful JSON IPC handshake) is implemented and verified, all other improvements are irrelevant — the feedback loop is broken at its foundation.

**Estimated remediation scope:** P0 items are 2–3 days of focused engineering. P1 items add another 3–4 days. The system can be production-ready within a single sprint if the action plan is followed in priority order.

---

## SECOND PASS PROMPT

```
Read ~/protocol_pulse/docs/gospels/RENDER_IMPROVEMENT_LOOP_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/render-improvement-loop_CONSENSUS_C2.md.

This is the FINAL PASS for render-improvement-loop.
The feature was reviewed by 3 independent AI models (Gemini 2.5 Pro, GPT-4o, Grok-3)
across 2 full audit cycles. Implement every P0 and P1 item from the consensus.
Use judgment on P2 items — implement if low-risk and self-contained.

PRIORITY ACTION PLAN:

P0 CRITICAL | Replace fire-and-forget .md write + 30s sleep with stateful JSON IPC handshake at /tmp/fix_request_iter

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles. In Cycle 1 it matched Grok's depth on flag-file IPC while producing the most structurally rigorous mitigation (stateful JSON handshake with `request_timestamp` / `completion_timestamp` pairing). Critically, in Cycle 2 it was the **only model** to read the *implemented code* rather than just the spec, correctly identifying that the architectural risk had shifted from "blocking-but-loud" to "non-blocking-but-blind" — a finding that neither GPT-4o nor Grok surfaced and that the consensus report validated as the definitive framing of the IPC problem.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: (severity × likelihood × reversibility cost). Items marked 🔴 CRITICAL must block any production deployment.

---

## 🔴 P1 — Replace Fire-and-Forget IPC with Stateful JSON Handshake
**File:** `overnight_render_loop.py` → `fire_cc_fix()` ~line 526–563
**Why first:** The feedback loop is completely severed. The main loop cannot distinguish between "fix applied successfully," "fix script never ran," and "fix ran and made things worse." Every downstream decision is built on a blind assumption.
**Exact change:**
1. `fire_cc_fix` writes `/tmp/fix_request_iter{N}.json` containing `{pid, iteration, request_timestamp, render_fault_summary}`
2. Improvement loop reads the request file, performs work, writes `/tmp/fix_complete_iter{N}.json` containing `{request_timestamp, completion_timestamp, status: "success"|"failed"|"partial", diff_hash}`
3. Main loop polls for the complete file with a **hard 45-minute timeout** and a **30-second poll interval**; on timeout it logs `FIX_TIMEOUT`, sends Telegram alert, and continues — never silently skips
4. On startup, both processes purge any `fix_request_iter*.json` or `fix_complete_iter*.json` older than 24 hours to eliminate stale-flag misdirection

---

## 🔴 P2 — Add Fault Tolerance Around Qwen / Ollama
**File:** Improvement loop's LLM call site (Ollama `localhost:11434`)
**Why second:** A single Ollama crash, OOM kill, or malformed JSON response currently propagates silently. If Qwen fails mid-loop the fix_complete file is never written, which after P1 is implemented triggers the 45-minute timeout on every subsequent iteration — compounding cost and delay.
**Exact change:**
1. Wrap every Ollama call in a retry decorator: **3 attempts, exponential backoff (10s → 30s → 90s)**
2. Add a **90-second per-call timeout** via `requests` session timeout or `asyncio.wait_for`
3. Validate all LLM responses against a strict JSON schema before acting on them; on schema failure log the raw response, increment a `qwen_failure_count` metric, and write `status: "failed"` to the complete file rather than hanging
4. If all 3 retries fail, send a Telegram alert with the raw error and exit the improvement loop cleanly — never leave `fix_request_iterN.json` in a permanently pending state

---

## 🔴 P3 — Harden CC / tmux Session Detection Against Zombie Sessions
**File:** Session detection logic in improvement loop / `cross_llm_audit.py`
**Why third:** A zombie tmux session that registers as "active" causes the loop to inject fix commands into a dead process. The command appears to succeed, the fix is never applied, and the system proceeds with false confidence. This is the "silent corruption" failure class.
**Exact change:**
1. Do not rely on tmux session *existence* alone — verify the session has a live foreground process via `tmux list-panes -t {session} -F "#{pane_pid}"` and confirm that PID is alive in `/proc/{pid}/status`
2. If the PID check fails, treat the session as dead: log `ZOMBIE_SESSION_DETECTED`, kill the session with `tmux kill-session`, restart it fresh, and record the event in the stateful JSON (P1) so the main loop is aware
3. Add a **per-session command timeout**: if the injected fix command has not produced output within 10 minutes, send SIGTERM to the pane PID and mark the fix attempt as `status: "timeout"`

---

## 🟠 P4 — Implement Token Cost Budgeting with Hard Circuit Breaker
**File:** Improvement loop orchestration, wherever LLM calls are sequenced
**Why fourth:** Multi-model calls per iteration (Qwen analysis + cross-LLM audit) accumulate cost non-linearly across a full overnight run. The $2 soft limit identified by Grok is optimistic for edge cases with large diffs or high iteration counts.
**Exact change:**
1. Instrument every LLM call with an estimated token counter (use `tiktoken` or Ollama's returned `eval_count`)
2. Maintain a **per-run cumulative cost register** in `/tmp/llm_cost_run_{date}.json`
3. Enforce a **hard circuit breaker at $5.00 per run**: if the register exceeds this threshold, skip LLM-assisted fixing for remaining iterations, log `COST_CIRCUIT_OPEN`, and send a Telegram alert
4. Log per-call costs in the stateful JSON complete file (P1) so cost is auditable per iteration

---

## 🟠 P5 — Complete and Validate DIMENSION_MAP Coverage
**File:** `clip_extractor.py` and any config file defining `DIMENSION_MAP`
**Why fifth:** Gaps in `DIMENSION_MAP` cause the extractor to silently skip unmapped render parameters. A fix that modifies an unmapped dimension will score identically to no fix at all — the improvement signal is destroyed before it reaches the scoring layer.
**Exact change:**
1. Enumerate all parameters actually emitted by the render engine and diff them against `DIMENSION_MAP` keys — treat any gap as a failing test
2. Add an **assertion at startup** that every incoming render parameter has a corresponding `DIMENSION_MAP` entry; on assertion failure, log the unmapped key, Telegram-alert, and halt the improvement loop rather than silently continuing
3. Add a nightly CI check that regenerates this diff and fails the build if new unmapped keys appear

---

## 🟡 P6 — Decouple Overnight Loop Coupling via Event Bus or Queue
**File:** `overnight_render_loop.py`, overall architecture
**Why sixth:** The current tight coupling (even after P1) means a slow improvement loop degrades the entire nightly render schedule. This is an architectural risk that manifests only at scale or under failure conditions.
**Exact change:**
1. Move the fix-request / fix-complete handshake onto a **lightweight local queue** (Redis with `fakeredis` for testing, or a `multiprocessing.Queue` if single-host) rather than filesystem polling
2. The overnight loop enqueues a fix job and continues rendering **immediately** without any polling delay
3. Completed fix results are consumed at the *next* iteration boundary — the loop checks the result queue at the top of each iteration, not mid-iteration
4. This converts the architecture from synchronous-with-timeout to asynchronous-with-bounded-consumption, eliminating the 45-minute worst-case stall from P1 entirely in steady state

---

## 🟡 P7 — Formalize Consensus Failure Handling
**File:** `cross_llm_audit.py`, consensus aggregation logic
**Why last:** When models disagree on whether a render is improved, the current handling is underspecified. A tie or split decision on "apply fix / reject fix" defaults to an unknown behavior.
**Exact change:**
1. Define an explicit **consensus policy**: majority-wins for 3-model setups; on a 1-1-1 split, default to **reject the fix** (conservative) and log `CONSENSUS_SPLIT`
2. Expose the policy as a named config constant (`CONSENSUS_STRATEGY = "majority_conservative"`) so it can be audited and changed without code surgery
3. Log every split event with the full per-model verdict