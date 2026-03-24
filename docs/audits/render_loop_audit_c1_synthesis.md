# RENDER IMPROVEMENT LOOP — CYCLE 1 SYNTHESIS
# Date: 2026-03-24
# Models: Gemini 2.5 Pro, GPT-4o (FAILED — TPM exceeded), Grok-3

---

## Q1 — INTEGRATION RISK (Flag File IPC)

**Gemini said:** CRITICAL. Identified 3 failure modes: (1) indefinite stall if improvement loop crashes before writing flag, (2) stale flag misdirection from previous crash, (3) race condition with tmpwatch. Prescribed stateful JSON handshake with PID, iteration, timestamps, glob-cleanup on startup, and hard 90-min timeout.

**GPT-4o said:** N/A — rate limited (TPM exceeded on cycle 1).

**Grok said:** CRITICAL. Identified same stall and stale-flag risks. Prescribed file locking via fcntl, cleanup routine based on timestamp/iteration, 60-min timeout, and heartbeat file from improvement loop.

**Consensus finding:** CRITICAL — UNANIMOUS. Both models independently rated this the highest-severity risk. The flag-file existence check is fatally fragile. A crash = permanent stall; a stale flag = false positive.

**What must change in gospel:** Replace flag-file IPC with stateful JSON handshake protocol. Main loop writes `fix_request_iterN.json` with `{pid, iteration, request_timestamp}`. Improvement loop writes `fix_complete_iterN.json` with `{request_timestamp, completion_timestamp, status, dimensions_fixed[]}`. Add glob-cleanup of all `/tmp/fix_*.json` on startup. Add 90-min per-iteration hard timeout with Telegram alert and fail-forward.

---

## Q2 — QWEN RELIABILITY

**Gemini said:** HIGH. Identified hard failure (Ollama down), malformed output (JSONDecodeError), and silent semantic failure (structurally valid but useless JSON like `{"fix_spec": null}`). Prescribed resilience wrapper with try/except, retry with backoff, schema validation via jsonschema, and graceful per-dimension degradation.

**GPT-4o said:** N/A.

**Grok said:** HIGH. Identified same failure modes. Prescribed fallback mechanism, Ollama health check, 3 retries with exponential backoff, manual override for alternative model.

**Consensus finding:** HIGH — UNANIMOUS. Both models agree Qwen has zero fault tolerance. Any failure cascades to full loop crash or silent corruption.

**What must change in gospel:** Add resilience wrapper on all Ollama calls: 30s connection timeout, 3 retries with exponential backoff (2s→4s→8s), JSON schema validation, semantic null check (assert fix_spec is non-null), graceful per-dimension degradation on exhausted retries. Add pre-flight health check (`GET localhost:11434/api/tags`) before loop start — if unhealthy, alert and skip entire improvement phase.

---

## Q3 — CC SESSION DETECTION

**Gemini said:** HIGH. Zombie sessions cause indefinite deadlock. Prescribed process-level verification: `tmux list-panes -s -F "#{pane_pid}"` → `ps -p <pid> -o comm=` to verify `claude` process. Also proposed CC session heartbeat file updated every 30s.

**GPT-4o said:** N/A.

**Grok said:** HIGH. Same zombie concern. Prescribed `tmux list-sessions -F '#{session_name} #{session_attached} #{session_activity}'` with 30-min inactivity threshold, forceful kill of zombie sessions, and `tmux capture-pane` validation.

**Consensus finding:** HIGH — UNANIMOUS. Both models agree `tmux ls` alone is dangerously insufficient. Two-layer verification required: session exists + process is alive inside it.

**What must change in gospel:** Replace simple tmux check with: (1) verify session exists, (2) `tmux list-panes -t <session> -F "#{pane_pid}"` → verify PID is alive via `/proc/<pid>/status`, (3) check session activity < 10 min, (4) kill zombie sessions exceeding threshold, (5) hard 30-min timeout on waiting for CC session response.

---

## Q4 — TOKEN COST REALITY

**Gemini said:** HIGH (operational/business). The $2 soft limit is fundamentally flawed — it ignores the dominant cost driver: CC Opus sessions consuming 100k-200k tokens ($2-$4 per fix). A cycle with 3-4 dimensions = $5-$10. Prescribed per-dimension budgets, tiered model selection (Sonnet for simple, Opus for complex).

**GPT-4o said:** N/A.

**Grok said:** MEDIUM. External LLM calls alone = $0.24-$1.00/cycle with retries. Prescribed $1/cycle soft cap with $5 daily hard limit, token optimization via summarization and caching.

**Consensus finding:** HIGH — Gemini's analysis is more complete. The CC Opus session cost dominates and was missed by Grok. Realistic budget: per-dimension $0.75-$2.00, cycle soft cap $7.50, daily hard cap $25.

**What must change in gospel:** Rewrite cost section with realistic estimates. Add per-dimension budget field to DIMENSION_MAP. Implement token counting before CC dispatch. Add tiered model selection: Sonnet for targeted fixes, Opus for architectural refactors. Add configurable hard cap via `MAX_TOKENS_PER_FIX_CYCLE` env var.

---

## Q5 — DIMENSION_MAP COMPLETENESS

**Gemini said:** MEDIUM. Unmapped dimensions cause KeyError or silent skip. Prescribed `.get()` with default handler, fuzzy matching fallback, Telegram alert on unknown dimension.

**GPT-4o said:** N/A.

**Grok said:** HIGH. Same silent-skip concern. Prescribed default handler routing to generic fix template, quarterly audit of Gemini schema, lightweight LLM fallback for unknown critical dimensions.

**Consensus finding:** MEDIUM-HIGH. Both agree unmapped dimensions are handled unsafely. The DEFAULT_HANDLER approach is the correct mitigation.

**What must change in gospel:** Add DEFAULT_HANDLER for unknown dimensions: log WARNING, fire Telegram alert, route to generic CC prompt, queue for manual review. Document all currently supported Gemini grade dimensions explicitly. Add startup assertion that all known dimensions are mapped.

---

## Q6 — OVERNIGHT LOOP COUPLING

**Gemini said:** CRITICAL. 14400s render timeout + multi-iteration improvement time can exceed 4 hours, killing the process mid-fix. Prescribed dynamic timeout management, timeout heartbeat/extension mechanism, or simple increase to 21600s.

**GPT-4o said:** N/A.

**Grok said:** CRITICAL. Same cumulative timeout concern across 8 iterations. Prescribed dynamic timeout extension per iteration, progress heartbeat, 2-hour total improvement cap, configurable timeout variables.

**Consensus finding:** CRITICAL — UNANIMOUS. The fixed render timeout is incompatible with variable-length improvement iterations. Timing must be coordinated.

**What must change in gospel:** Add dynamic timeout management: (1) main loop pauses its timeout while improvement loop heartbeat is active, (2) hard 2-hour aggregate cap on total improvement time per cycle, (3) expose all timeouts as config variables: `MAX_IMPROVEMENT_TIME_SECONDS`, `PER_ITERATION_TIMEOUT_SECONDS`, `MAX_ITERATIONS`. (4) 90-min per-iteration timeout (Gemini) + 2-hour aggregate cap (Grok) — both implemented.

---

## Q7 — CONSENSUS FAILURE HANDLING

**Gemini said:** CRITICAL. Infinite identical loops when all critical dimensions produce disagreements. Prescribed stateful stalemate detection, escalation protocol: Tier 2 adjudicator model, known-safe default fixes, or fail the cycle after 2 consecutive disagreements.

**GPT-4o said:** N/A.

**Grok said:** CRITICAL. Same infinite loop risk. Prescribed tiebreaker mechanism after 2 disagreements (use highest-scoring model's recommendation), 3-iteration limit on identical iterations, human escalation via Telegram.

**Consensus finding:** CRITICAL — UNANIMOUS. Without stalemate detection, the loop can burn infinite resources with zero improvement.

**What must change in gospel:** Add stalemate detection: track skipped dimensions across iterations. After 2 consecutive disagreements on same dimension: (1) apply conservative safe default if available, (2) use highest-confidence model's recommendation as tiebreaker, (3) if no resolution after 3 identical iterations, abort cycle with CRITICAL Telegram alert. Add `CONSENSUS_STRATEGY = "majority_conservative"` config constant.

---

## Q8 — IMPLEMENTATION CORRECTNESS

**Gemini said:** CRITICAL. CC may refactor surrounding code, introduce dependencies, or implement the wrong fix. Prescribed mandatory post-commit regression test, automated `git revert HEAD` on test failure, and diff sanity check (if spec targets 1 file but diff shows 5 files → reject).

**GPT-4o said:** N/A.

**Grok said:** CRITICAL. Same over-scope and incorrect implementation risks. Prescribed strict prompt constraints, diff output for review before applying, post-fix regression test with rollback, sandbox mode for isolated testing.

**Consensus finding:** CRITICAL — UNANIMOUS. Unguarded autonomous code modification is the single highest-risk operation in the system.

**What must change in gospel:** Add mandatory guardrails: (1) diff sanity check — if files changed > expected, reject immediately, (2) `regression_test.sh` must pass before commit is accepted, (3) automated `git revert HEAD` + Telegram alert on test failure, (4) CC prompt must include explicit constraints: "Do not modify function signatures. Do not add external dependencies. Do not touch files not specified in the fix spec." (5) Max allowed diff size per fix: 50 lines.

---

## OVERALL ASSESSMENT

- **CRITICAL issues found:** 5 (Q1, Q6, Q7, Q8, plus Q3 deadlock aspect)
- **HIGH issues found:** 3 (Q2, Q3, Q4)
- **Gospel ready to build?** NO — requires fundamental rework on IPC, fault tolerance, stalemate handling, and CC guardrails
- **Single most dangerous gap:** Lack of automated test-and-revert guardrail for CC commits (Q8) — allowing autonomous code modification without validation is unacceptable operational risk
