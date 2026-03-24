# ARCHITECTURE AUDIT REPORT — RENDER IMPROVEMENT LOOP

Below is a detailed analysis of the Gospel Spec for the autonomous render improvement loop, addressing the 8 critical questions with specific failure modes, severity ratings, mitigations, and citations to the relevant sections of the gospel (assumed structure based on context since the gospel text is not provided in full).

---

### Q1 — INTEGRATION RISK
- **STATE the failure mode(s) clearly**: The use of flag files (`/tmp/render_fix_complete_iterN`) for integration with `overnight_render_loop.py` introduces several risks: (1) Race conditions where the render loop checks for the flag file before the improvement loop writes it, causing premature continuation or timeout; (2) Stale flag files from previous iterations or crashes not being cleaned up, leading to false positives; (3) A crash in the improvement loop preventing the flag file from being written, potentially blocking the overnight loop indefinitely if it waits for the flag.
- **RATE the severity**: CRITICAL
- **PRESCRIBE the exact mitigation**: Implement a robust file locking mechanism (e.g., using `fcntl` or a dedicated lock file) to prevent race conditions. Add a cleanup routine at the start of each iteration to remove stale flag files based on timestamp or iteration number. Introduce a timeout mechanism in the overnight loop to proceed if the flag isn't written within a specified window (e.g., 60 minutes), logging the event as a failure. Define a heartbeat file updated by the improvement loop to signal it is alive, allowing the overnight loop to detect crashes.
- **CITE the gospel section that needs updating**: Section on "Integration with Overnight Render Loop" (assumed title). Add a subsection titled "Flag File Management and Failure Recovery" detailing the locking, cleanup, timeout, and heartbeat mechanisms.

---

### Q2 — QWEN RELIABILITY
- **STATE the failure mode(s) clearly**: The loop's dependency on Qwen3:30b via Ollama at `localhost:11434` risks failure if (1) Ollama is down or unreachable, (2) the Qwen model is not loaded or crashes during inference, or (3) Qwen returns malformed JSON, causing parsing errors downstream. Without graceful degradation, this could halt the entire render cycle.
- **RATE the severity**: HIGH
- **PRESCRIBE the exact mitigation**: Implement a fallback mechanism where, if Qwen fails (connection error, timeout, or malformed output), the loop defaults to a predefined heuristic or skips the dimension with a logged warning, ensuring the render cycle continues. Add a health check for Ollama before starting the loop (e.g., a simple API ping). Include retry logic (e.g., 3 attempts with exponential backoff) for transient failures. Document a manual override to use an alternative local model or external API if Qwen is persistently unavailable.
- **CITE the gospel section that needs updating**: Section on "Qwen3:30b Integration" (assumed title). Add a subsection titled "Reliability and Fallbacks" to specify health checks, retries, fallback heuristics, and manual overrides.

---

### Q3 — CC SESSION DETECTION
- **STATE the failure mode(s) clearly**: Polling tmux for CC session slots risks misidentification if zombie sessions from previous crashes persist, leading to the loop waiting indefinitely or incorrectly assuming a slot is occupied. The gospel does not specify how to differentiate live CC sessions from dead ones, risking deadlock or resource waste.
- **RATE the severity**: HIGH
- **PRESCRIBE the exact mitigation**: Use `tmux list-sessions -F '#{session_name} #{session_attached} #{session_activity}'` to check if a session is actively attached and recently active (based on timestamp). Define a threshold (e.g., no activity for 30 minutes = zombie) to consider a session dead, and forcefully terminate such sessions with `tmux kill-session`. Add a validation step to check if the session is running the expected CC command by inspecting `tmux capture-pane` output for specific CC process signatures.
- **CITE the gospel section that needs updating**: Section on "CC Session Polling" (assumed title). Add a subsection titled "Zombie Session Detection and Cleanup" detailing the tmux commands, activity thresholds, and validation logic.

---

### Q4 — TOKEN COST REALITY
- **STATE the failure mode(s) clearly**: The gospel's $2 soft limit per cycle appears optimistic. With 4-6 failing dimensions per cycle, each requiring Qwen (local, free) plus 2 external LLM calls (~2000 tokens each), at typical API rates (e.g., $0.005/1000 tokens for input, $0.015/1000 for output), a single dimension fix costs ~$0.04-$0.06 (4000 tokens total). For 6 dimensions, this is $0.24-$0.36 per cycle, but retries or additional context could push costs to $0.50-$1.00 per cycle, far exceeding $2 over multiple cycles or days.
- **RATE the severity**: MEDIUM
- **PRESCRIBE the exact mitigation**: Revise the cost estimate to a realistic $1 per cycle cap with a hard $5 daily limit, logging a warning and pausing external calls if exceeded. Optimize token usage by summarizing inputs (e.g., truncate grade reports to essential data) and caching common queries. Allow configurable limits per dimension to prioritize critical fixes (e.g., avatar over pacing). Add a cost tracking mechanism to log token usage per call for transparency.
- **CITE the gospel section that needs updating**: Section on "Cost Management" (assumed title). Update to include realistic cost projections, token optimization strategies, and hard daily caps under a subsection titled "Token Cost Control and Monitoring."

---

### Q5 — DIMENSION_MAP COMPLETENESS
- **STATE the failure mode(s) clearly**: If the `DIMENSION_MAP` in the gospel omits any Gemini grade dimensions (e.g., new ones like "narrative_cohesion" or "background_music_balance" added in future updates), the loop will fail to address unmapped issues, silently ignoring critical flaws. Without a catch-all strategy, the loop risks incomplete fixes.
- **RATE the severity**: HIGH
- **PRESCRIBE the exact mitigation**: Include a default handler in `DIMENSION_MAP` for unmapped dimensions, routing them to a generic fix template with a warning logged for manual review. Periodically update the map based on Gemini grade schema changes (e.g., via a quarterly audit). Add a fallback to query a lightweight external LLM for guidance on unknown dimensions if critical (score < 5/10). Document all 24 Gemini dimensions explicitly in the gospel to ensure coverage.
- **CITE the gospel section that needs updating**: Section on "Dimension Mapping" (assumed title). Add a subsection titled "Handling Unknown Dimensions" to specify the default handler, update process, and fallback strategy.

---

### Q6 — OVERNIGHT LOOP COUPLING
- **STATE the failure mode(s) clearly**: The overnight loop's 14400s (4-hour) render timeout could be exceeded if the improvement loop takes 90 minutes (common for long CC sessions), especially across multiple iterations, causing the render to abort mid-fix. The gospel's "wait up to 60 min" per flag check may not account for cumulative delays over 8 iterations.
- **RATE the severity**: CRITICAL
- **PRESCRIBE the exact mitigation**: Extend the overnight loop's render timeout dynamically based on active improvement iterations (e.g., add 90 minutes per iteration to the base 14400s). Implement a progress heartbeat from the improvement loop to the overnight loop, allowing it to pause its timeout if a fix is in progress. Cap total improvement loop time per cycle (e.g., 2 hours across all iterations) to prevent runaway delays. Synchronize timing via a shared config file or environment variable defining max wait times.
- **CITE the gospel section that needs updating**: Section on "Integration with Overnight Render Loop" (assumed title). Add a subsection titled "Timeout Coordination" detailing dynamic timeout extensions, heartbeat signals, and hard caps.

---

### Q7 — CONSENSUS FAILURE HANDLING
- **STATE the failure mode(s) clearly**: If LLMs disagree on critical dimensions (e.g., avatar, freeze, visual_polish), the loop skips them and sends a Telegram alert, risking no progress. Repeated disagreements could trap the loop in identical iterations, wasting resources and delaying Grade A renders indefinitely.
- **RATE the severity**: CRITICAL
- **PRESCRIBE the exact mitigation**: Implement a tiebreaker mechanism: after 2 consecutive disagreements on a dimension, default to the highest-scoring model's recommendation (based on historical accuracy) or a predefined priority (e.g., prioritize fixes for avatar over pacing). Limit identical iterations to 3, after which the loop escalates to a human-in-the-loop via Telegram with a detailed diagnostic log. Track disagreement history per dimension to adjust future consensus thresholds dynamically.
- **CITE the gospel section that needs updating**: Section on "Consensus and Disagreement Handling" (assumed title). Add a subsection titled "Preventing Infinite Loops" to specify tiebreaker rules, iteration limits, and escalation protocols.

---

### Q8 — IMPLEMENTATION CORRECTNESS
- **STATE the failure mode(s) clearly**: CC (Opus 4.6) may overstep fix specs, refactoring unrelated code, altering function signatures, or introducing dependencies, breaking other pipeline stages (e.g., changing `daily_producer.py` interfaces used by `assembler.py`). This risks cascading failures across the render pipeline.
- **RATE the severity**: CRITICAL
- **PRESCRIBE the exact mitigation**: Enforce strict guardrails in CC prompts, explicitly instructing it to limit changes to specified files/lines and preserve existing interfaces (e.g., "Do not modify function signatures or add external dependencies"). Require CC to output a diff for review before applying changes, logged for audit. Implement a post-fix regression test (e.g., `regression_test.sh`) to validate pipeline integrity after each CC session, rolling back if failures occur. Add a sandbox mode for CC to test changes in isolation before committing.
- **CITE the gospel section that needs updating**: Section on "CC Fix Implementation" (assumed title). Add a subsection titled "Change Containment and Validation" to detail prompt constraints, diff logging, regression testing, and sandboxing.

---

### FINAL VERDICT
- **How many CRITICAL issues did you find?**: 4 (Q1: Integration Risk, Q6: Overnight Loop Coupling, Q7: Consensus Failure Handling, Q8: Implementation Correctness)
- **Is this gospel ready to build from, or does it need fundamental rework?**: The gospel is **not ready to build from** and requires fundamental rework. The critical issues identified—particularly around integration, timing, consensus, and CC correctness—pose significant risks of pipeline failure, infinite loops, and unintended side effects, which must be addressed before implementation.
- **What is the single most dangerous gap?**: The most dangerous gap is in **Consensus Failure Handling (Q7)**, as repeated disagreements on critical dimensions could result in an infinite loop of identical renders with no improvement, stalling the entire production pipeline indefinitely and wasting significant resources.

This audit underscores the need for robust failure handling, precise integration mechanisms, and strict control over automated fixes to ensure the render improvement loop enhances rather than disrupts the existing system.