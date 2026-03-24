# CONSENSUS REPORT — RENDER-IMPROVEMENT-LOOP — CYCLE 1
Generated: 2026-03-24 05:51
Models: grok, gemini (+1 failed — GPT-4o TPM limit exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Integration (Flag IPC) | 2/10 | N/A | 2/10 | **2/10** |
| Qwen Reliability | 4/10 | N/A | 4/10 | **4/10** |
| CC Session Detection | 3/10 | N/A | 3/10 | **3/10** |
| Token Cost Reality | 3/10 | N/A | 4/10 | **3/10** |
| DIMENSION_MAP Completeness | 5/10 | N/A | 4/10 | **4/10** |
| Overnight Loop Coupling | 2/10 | N/A | 2/10 | **2/10** |
| Consensus Failure Handling | N/A (cut off) | N/A | N/A (cut off) | **TBD** |
| Overall Architecture | 3/10 | N/A | 3/10 | **3/10** |

> **Note:** GPT-4o failed due to rate limiting (TPM exceeded). All consensus determinations are based on 2 of 3 models. Where both Gemini and Grok agree, confidence is rated HIGH. No findings are rated UNANIMOUS (requires all 3); they are instead rated MAJORITY (2/2 available models).

---

## UNANIMOUS FINDINGS (all 2 available models agree — implement unconditionally)

### U1 — Flag-File IPC Is Fatally Fragile
**What it is:** Both models independently flagged the `/tmp/render_fix_complete_iterN` flag-file mechanism as critically broken. A crash before the flag is written causes `overnight_render_loop.py` to stall forever. A stale flag from a previous crash causes the main loop to falsely believe the current iteration was fixed and proceed with unfixed code.

**Which file/line:** `overnight_render_loop.py` — flag-write/flag-read logic; gospel Section on Inter-Process Communication.

**What to change:**
- Replace bare flag-file existence checks with a **stateful JSON handshake**:
  - Main loop writes `/tmp/fix_request_iterN.json` containing `{pid, iteration, request_timestamp}`.
  - Improvement loop reads it, executes, then writes `/tmp/fix_complete_iterN.json` containing `{original_request_timestamp, completion_timestamp, status, dimensions_fixed[]}`.
  - Main loop validates that `fix_complete.request_timestamp == fix_request.request_timestamp` before accepting the result as valid for *this* run.
- `overnight_render_loop.py` must **glob-delete all `/tmp/fix_*.json` files on startup** to ensure clean state.
- The main loop's wait must have a **hard 90-minute per-iteration timeout** independent of the render timeout, with Telegram alert and graceful fail-forward on breach.

---

### U2 — Qwen Has No Fault Tolerance
**What it is:** Both models flagged that if Ollama is down, OOM-killed, returns malformed JSON, or returns a valid-structure but semantically null response, the entire loop crashes or silently produces no fix with no operator awareness.

**Which file/line:** Improvement loop — all `ollama` / `localhost:11434` call sites; gospel Section on Local LLM Integration.

**What to change:**
- Wrap every Ollama call in a resilience block: `try/except` with connection timeout (30s), **3 retries with exponential backoff** (15s, 30s, 60s).
- Validate JSON response against a declared schema (use `jsonschema`). Treat schema mismatch as a hard failure triggering retry logic.
- On definitive unavailability: log error, fire Telegram alert `"Qwen unavailable — skipping fix for [dimension]"`, **skip that dimension gracefully**, continue to next. Do NOT crash the loop.
- Add a **pre-flight health check** (`GET localhost:11434/api/tags`) before starting the improvement loop. If it fails, alert and skip the entire improvement phase rather than failing mid-cycle.

---

### U3 — tmux Zombie Sessions Cause Indefinite Deadlock
**What it is:** Both models flagged that polling `tmux ls` for CC session existence cannot distinguish a live session from a zombie shell left behind by a crash. The loop will wait forever on a zombie.

**Which file/line:** Improvement loop — CC session polling/detection logic; gospel Section on CC Session Orchestration.

**What to change:**
- **Do not rely on session existence alone.** Two-layer verification required:
  - Layer 1: `tmux list-panes -s -F "#{pane_pid}" -t cc_session` → get the shell PID.
  - Layer 2: `ps -p <pid> -o comm=` → verify the expected process (`claude` or `claude_code`) is actually running inside it.
- Implement a **heartbeat file**: when the loop spawns a CC session, instruct the session to write `/tmp/cc_session.heartbeat.json` with current timestamp every 30 seconds. The polling logic checks: file exists AND `(now - heartbeat_timestamp) < 60s`. If stale > 60s → session is zombie → `tmux kill-session -t cc_session` → re-spawn.
- Define a **zombie activity threshold**: if session exists but no valid heartbeat for 30 minutes, classify as dead, kill, and re-attempt.

---

### U4 — Overnight Loop Timeout Is Not Coordinated With Improvement Loop Duration
**What it is:** Both models flagged that the overnight loop's fixed render timeout (14400s / 4 hours) does not account for the cumulative time consumed by improvement iterations. With 8 iterations at up to 90 minutes each, the total time could exceed 12 hours, causing the render to abort mid-fix.

**Which file/line:** `overnight_render_loop.py` — timeout constants; gospel Section on Integration/Timeout Coordination.

**What to change:**
- The render timeout must be **dynamically extended** based on active improvement activity. When the improvement loop signals it is working (via heartbeat or request JSON), the main loop pauses its timeout countdown.
- Implement a **hard cap on total improvement loop time per cycle** (e.g., 2 hours across all iterations combined) to prevent runaway.
- Expose these as **config variables** (not hardcoded): `MAX_IMPROVEMENT_TIME_SECONDS`, `MAX_ITERATIONS`, `PER_ITERATION_TIMEOUT_SECONDS`.
- Log a warning and proceed without further improvement attempts if the cap is hit, rather than crashing or stalling.

---

## MAJORITY FINDINGS (2 of 2 available models agree)

> All findings below are 2/2 since GPT-4o was unavailable. These carry the same weight as UNANIMOUS in this cycle.

### M1 — Token Cost Analysis Is Unrealistically Low
**Gemini finding:** The most expensive call is the Claude Code (Opus) session, not the analysis calls. A single CC session can consume 100k–200k tokens in context (code + gospel + audit). At Opus pricing (~$20/M blended), one fix = $2–$4. A cycle with 3–4 failing dimensions = **$5–$10 per cycle**, not $2.

**Grok finding:** At typical API rates with 4–6 failing dimensions, costs run $0.24–$1.00 per cycle for external calls alone, and can exceed $2 with retries.

**Consensus:** Both models agree the $2 soft limit is insufficient. Gemini's framing is more precise (focuses on CC session cost) and should be treated as the primary concern.

**What to change:**
- Rewrite cost analysis in gospel with **per-dimension budgets**: simple fix = $0.75, complex refactor = $2.00, per-cycle soft cap = $7.50, per-day hard cap = $25.
- Implement **token counting before firing the CC session**. If estimated tokens exceed per-dimension budget, alert and require manual override.
- Apply **tiered model selection**: Sonnet for targeted single-function fixes, Opus only for architectural refactors, controlled by a `fix_complexity` field in the DIMENSION_MAP entry.
- Log all token usage per call to a persistent cost ledger (`/tmp/cost_ledger_YYYYMMDD.json`).

---

### M2 — DIMENSION_MAP Has No Unknown-Dimension Handler
**Gemini finding:** If Gemini's grading prompt is updated to include a new dimension not in the map, the code will `KeyError` crash or silently skip via `.get()`.

**Grok finding:** Unmapped dimensions are silently ignored, leaving critical flaws unaddressed. No catch-all exists.

**What to change:**
- Replace bare dict access with `DIMENSION_MAP.get(dimension_name, DEFAULT_HANDLER)`.
- Implement a `DEFAULT_HANDLER` that: logs a `WARNING: Unknown dimension '[name]' encountered`, fires a Telegram alert, routes to a generic "investigate and summarize" CC prompt rather than a specific fix template, and queues the dimension for manual review.
- Document all currently supported dimensions explicitly in the gospel.
- Add a **quarterly schema drift check**: compare live Gemini grading output keys against `DIMENSION_MAP` keys and alert on divergence.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — Gemini: Silent Semantic Failure from Qwen (Structurally Valid but Meaningless JSON)
**Model:** Gemini only.

**What it is:** Qwen could return `{"fix_spec": null, "reason": "I cannot fulfill this request."}` — structurally valid JSON that passes schema validation but contains no actionable fix data. The loop might interpret null fix_spec as "nothing to fix" and advance, leaving the dimension broken.

**Assessment: IMPLEMENT.** This is a subtle and real failure mode that schema validation alone will not catch. Add a **semantic validation layer**: after schema validation, assert that required non-null fields (`fix_spec`, `action`, etc.) are actually populated. If null/empty, treat as a Qwen failure and trigger retry/degradation logic. This is a 10-line addition with high safety value.

---

### UI2 — Gemini: Stateful JSON Handshake Should Include `dimensions_fixed[]` Array
**Model:** Gemini only (as part of IPC redesign).

**What it is:** The fix-complete JSON should include which dimensions were actually fixed, not just a binary success/fail. This allows the main loop to make informed decisions (e.g., re-queue unfixed dimensions, generate accurate audit trails).

**Assessment: IMPLEMENT.** Costs nothing extra to add, significantly improves observability and retry intelligence. Add `dimensions_fixed[]`, `dimensions_skipped[]`, and `dimensions_failed[]` arrays to the handshake JSON schema.

---

### UI3 — Grok: External LLM Fallback for Unknown Critical Dimensions
**Model:** Grok only.

**What it is:** If a dimension is unknown AND its score is below a critical threshold (e.g., < 5/10), query a lightweight external LLM for guidance rather than just logging and alerting.

**Assessment: INVESTIGATE FURTHER.** The concept is sound but adds external API dependency and cost for a rare edge case. A simpler and safer approach is to use the DEFAULT_HANDLER (UI2 above) which fires a generic CC prompt. Escalating to an external LLM specifically for unknown dimensions adds complexity without proportional benefit. Defer to a future cycle after the DEFAULT_HANDLER proves insufficient.

---

### UI4 — Grok: Heartbeat File for Improvement Loop → Main Loop Communication
**Model:** Grok (as distinct from the CC session heartbeat Gemini proposed).

**What it is:** The improvement loop itself (not just the CC session inside it) should write a heartbeat file to the main loop, allowing the main loop to distinguish "improvement loop is alive and working" from "improvement loop has crashed."

**Assessment: IMPLEMENT.** This is distinct from the CC session heartbeat (U3) and addresses a different failure mode: the improvement loop process itself crashing silently. Low-cost addition — the improvement loop writes `/tmp/improvement_loop.heartbeat.json` every 60 seconds while active. The main loop checks it during its wait cycle.

---

### UI5 — Grok: Configurable Per-Dimension Cost Limits to Prioritize Critical Fixes
**Model:** Grok only.

**What it is:** Allow each dimension entry in `DIMENSION_MAP` to carry a `max_cost_usd` field, so high-priority dimensions (e.g., `avatar_quality`) get larger budgets than low-priority ones (e.g., `background_music_balance`).

**Assessment: IMPLEMENT (P2).** Elegant and operationally sensible. Add a `priority` field (`critical/high/medium/low`) and a `max_cost_usd` field to each DIMENSION_MAP entry. The budget enforcement logic uses these per-dimension rather than a flat cap. Implement after core IPC and reliability fixes are stable.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Timeout Value for Per-Iteration Wait
**Grok says:** 60-minute wait per flag check, cap total at 2 hours.
**Gemini says:** 90-minute hard timeout per iteration, independent of render timeout.

**Tiebreaker: Gemini is right on the per-iteration value; Grok is right on the aggregate cap.** A 90-minute per-iteration timeout is more realistic for complex CC sessions that may need to load large codebases. However, Grok's 2-hour aggregate cap is essential to prevent runaway. **Implement both**: 90-minute per-iteration timeout AND 2-hour total improvement budget per cycle. These are complementary, not contradictory.

---

### C2 — Cost Per Cycle Estimate
**Grok says:** $0.24–$1.00 per cycle for external calls; revise soft limit to $1 with $5 daily hard cap.
**Gemini says:** $5–$10 per cycle driven by CC Opus sessions; revise to $7.50 cycle soft cap.

**Tiebreaker: Gemini is correct.** Grok's estimate focuses on analysis-tier calls (cheap) and ignores that Claude Code (Opus) sessions are the dominant cost driver. Gemini correctly identifies that a single CC session can consume 100k–200k tokens. The $7.50/cycle and $25/day caps from Gemini's analysis are the realistic operational targets. **Implement Gemini's figures.** Grok's token-optimization recommendations (summarize inputs, cache common queries) are complementary and should also be implemented.

---

### C3 — Fallback for Unavailable Qwen: Skip vs. Heuristic
**Grok says:** Fall back to a predefined heuristic or skip the dimension.
**Gemini says:** Skip the dimension and alert — no heuristic fallback.

**Tiebreaker: Gemini is right.** A "predefined heuristic" for a code fix is undefined, unmaintainable, and likely to produce worse outputs than skipping. The correct behavior when Qwen is unavailable is: skip the dimension, log it, alert via Telegram, and allow the overnight cycle to complete without that fix. Adding a fallback heuristic adds complexity without safety guarantees. **Implement Gemini's skip-and-alert approach.**

---

## VALIDATED STRENGTHS (all available models agree this is already excellent)

Both models reviewed the architecture and found **no areas to validate as production-ready** in this cycle. The overall architecture score of 3/10 indicates foundational issues that must be resolved before any subsystem can be declared stable.

> The multi-LLM consensus approach itself (the audit layer above the render loop) was implicitly validated as architecturally sound by both models — neither suggested removing or replacing it. **Do not change the audit orchestration pattern.**

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Determination |
|---|---|---|
| Never block indefinitely | ❌ VIOLATED | Flag-file wait has no timeout → indefinite stall on crash |
| Fail loudly, not silently | ❌ VIOLATED | Missing dimension keys silently ignored; Qwen errors may pass through |
| Clean up after yourself | ❌ VIOLATED | Stale flag files and zombie tmux sessions not cleaned |
| Alert humans on critical failures | ⚠️ PARTIAL | Telegram alerts exist but not on all critical failure paths |
| Cost must be bounded | ❌ VIOLATED | No enforced token/cost cap; $2 limit is unrealistic and unenforced |
| Validate external inputs | ❌ VIOLATED | Qwen JSON not schema-validated; semantic null not checked |
| Idempotent startup | ❌ VIOLATED | No cleanup of prior run artifacts on start |

**Final determination:** The system violates 6 of 7 fundamental operational laws. It is **not production-safe** in its current form.

---

## SECURITY CONSENSUS

| Issue | Models | Priority |
|---|---|---|
| `/tmp` flag files are world-readable/writable — an adversarial process could write a false completion flag | Grok (implied), Gemini (implied) | P1 |
| No authentication on `localhost:11434` Ollama endpoint — any local process can inject responses | Neither model explicitly flagged | Note for future cycle |
| tmux session names are predictable — a rogue process could create `cc_session` to block legitimate CC spawning | Grok (implied) | P2 |

**Security consensus:** The `/tmp` IPC mechanism is the highest-priority security issue. Mitigation is to scope the JSON handshake files with restrictive permissions (`chmod 600`) and include a session-unique token in the handshake JSON to prevent replay/injection attacks.

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models)*

### WCG1 — No Observability Layer
Both models noted the absence of a structured audit trail. A world-class system would maintain a persistent run log per cycle: which dimensions failed, which were fixed, which were skipped, cost per dimension, time per dimension, CC session outcome. This data enables trend analysis (is the render quality improving over weeks?) and cost optimization. **Currently: zero structured telemetry.**

### WCG2 — No Graceful Degradation Hierarchy
Both models prescribed skip-and-continue behavior when components fail, but the gospel has no documented degradation hierarchy. A world-class system defines explicitly: if Qwen is down → skip local analysis, continue with external LLM analysis only. If CC session fails → skip fix, continue to next dimension. If all dimensions fail → complete the render cycle anyway, flag for human review. **Currently: any component failure threatens the entire cycle.**

### WCG3 — Static Configuration in a Dynamic System
Both models noted hardcoded values (timeouts, cost limits, iteration counts, model names). A world-class system externalizes all operational parameters to a config file (`render_improvement_config.yaml`) that can be modified without code changes, supports per-environment overrides (dev/staging/prod), and is validated on startup. **Currently: magic numbers scattered through code and gospel.**

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 CRITICAL

| Priority | Change | File/Location | Models | Why |
|---|---|---|---|---|
| P0 | Replace flag-file IPC with stateful JSON handshake (`fix_request_iterN.json` / `fix_complete_iterN.json`) including session token, timestamps, and dimension arrays | `overnight_render_loop.py` + improvement loop IPC layer | grok + gemini | Indefinite stall and stale-flag false-positive are both crash-severity production failures |
| P0 | Add glob-cleanup of all `/tmp/fix_*.json` and `/tmp/render_fix_*` files on `overnight_render_loop.py` startup | `overnight_render_loop.py` — startup block | grok + gemini | Stale artifacts from prior crashes will corrupt current run without this |
| P0 | Implement 90-minute per-iteration timeout + 2-hour aggregate improvement budget in main loop's wait logic, with Telegram alert and graceful fail-forward on breach | `overnight_render_loop.py` — wait/timeout logic | grok + gemini (reconciled) | Prevents indefinite stall; coordinates overnight loop with improvement loop duration |
| P0 | Implement dynamic render timeout extension: pause countdown while improvement loop heartbeat is active | `overnight_render_loop.py` — render timeout logic | grok + gemini | Fixed 4-hour timeout is exceeded by multi-iteration improvement cycles |
| P0 | Add two-layer CC session liveness check: pane PID + process name verification; kill zombie sessions exceeding 30-minute heartbeat silence | Improvement loop — CC session polling | grok + gemini | Zombie sessions cause indefinite deadlock with no self-recovery |

---

### P1 HIGH

| Priority | Change | File/Location | Models | Why |
|---|---|---|---|---|
| P1 | Wrap all Ollama calls in resilience block: 30s timeout, 3 retries with exponential backoff (15/30/60s), schema validation via `jsonschema`, semantic null check on `fix_spec` | Improvement loop — all Ollama call sites | grok + gemini + UI1 | Any Qwen failure currently crashes or silently corrupts the loop |
| P1 | Add Ollama pre-flight health check (`GET localhost:11434/api/tags`) before starting improvement loop; on failure, alert and skip entire improvement phase | Improvement loop — startup | grok + gemini | Fail fast before burning cycle time on a loop that cannot function |
| P1 | Add `DEFAULT_HANDLER` for unknown DIMENSION_MAP keys: `DIMENSION_MAP.get(dim, DEFAULT_HANDLER)`, log warning, fire Telegram alert, route to generic CC prompt | Improvement loop — dimension dispatch | grok + gemini | KeyError crash or silent skip on any Gemini schema update |
| P1 | Add improvement loop process heartbeat (`/tmp/improvement_loop.heartbeat.json`, updated every 60s); main loop validates during wait | Improvement loop — main loop + heartbeat writer | grok (UI4) + Gemini (implicit) | Distinguishes "improvement loop working" from "improvement loop crashed silently" |
| P1 | Add CC session heartbeat (`/tmp/cc_session.heartbeat.json`, updated every 30s from within session); polling logic validates `(now - heartbeat) < 60s` | Improvement loop — CC session spawn + polling | grok + gemini | Process-level zombie detection beyond PID/name verification |
| P1 | Rewrite cost analysis: per-dimension budget (simple=$0.75, complex=$2.00), cycle soft cap=$7.50, daily hard cap=$25; implement token counting before CC session dispatch | Gospel cost section + improvement loop — pre-CC dispatch | grok + gemini (reconciled) | Current $2 cap is 3–5x underestimated; no enforcement exists |
| P1 | Implement tiered model selection: Sonnet for targeted fixes, Opus for architectural refactors, governed by `fix_complexity` field in DIMENSION_MAP | Improvement loop — CC session dispatch | gemini | Eliminates unnecessary Opus spend on simple fixes |

---

### P2 MEDIUM

| Priority | Change | File/Location | Models | Why |
|---|---|---|---|---|
| P2 | Externalize all operational parameters to `render_improvement_config.yaml`: timeouts, cost caps, iteration counts, model names, heartbeat intervals | All files + new config file | grok + gemini (implicit) | Magic numbers in code prevent operational tuning without deployments |
| P2 | Add structured per-cycle audit log: dimension outcomes (fixed/skipped/failed), cost per dimension, time per dimension, CC session result | Improvement loop — end of each dimension | grok + gemini | Zero telemetry prevents quality trend analysis and cost optimization |
| P2 | Add `priority` and `max_cost_usd` fields to all DIMENSION_MAP entries; budget enforcement uses per-dimension limits | Improvement loop — DIMENSION_MAP definition + budget logic | grok (UI5) | Ensures critical dimensions get budget priority over cosmetic ones |
| P2 | Add `dimensions_fixed[]`, `dimensions_skipped[]`, `dimensions_failed[]` arrays to fix-complete JSON handshake | Improvement loop — IPC handshake writer | gemini (UI2) | Enables informed retry logic and accurate audit trails in main loop |
| P