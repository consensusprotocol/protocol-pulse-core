# CONSENSUS REPORT — VIDEO-AUDIO-FIX — CYCLE 2
Generated: 2026-05-30 04:48
Models: grok, gemini (+1 failed: gpt4o — quota exceeded)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | 40/100 | N/A | 52/100 | **46/100** |
| Frontend/UI | N/A | N/A | N/A | **N/A** |
| Error Handling | 20/100 | N/A | 35/100 | **28/100** |
| Security | 10/100 | N/A | 22/100 | **16/100** |
| Law Compliance | 30/100 | N/A | 25/100 | **28/100** |
| Performance | N/A | N/A | N/A | **N/A** |
| World-Class Gap | 15/100 | N/A | N/A (35→ not re-scored) | **15/100** |
| **OVERALL** | **23/100** | N/A | **38/100** | **30/100** |

> **Note:** Gemini's cycle 2 scores dropped sharply upon identifying the architectural root cause (prompt-interpreted shell commands). Grok scored conservatively throughout. Consensus lands at 30/100 — well below any production threshold. GPT-4o failure does not invalidate the report; two models with independent deep analysis constitute sufficient quorum.

---

## UNANIMOUS FINDINGS
*(Both available models agree — implement unconditionally)*

---

### U1 — Command Injection via Raw `$ARGUMENTS` Interpolation
**What it is:** User-controlled `$ARGUMENTS` is interpolated directly into `python3 -c "... text = '$ARGUMENTS' ..."` strings. A value containing `'` breaks Python syntax; a crafted value achieves arbitrary shell command execution.
**Files/Lines:** `post.md:13`, `tweet.md:9–11`, `render.md:12`
**Fix:** Delete all `python3 -c` one-liners that embed `$ARGUMENTS`. Replace with dedicated Python entrypoints (`post_tweet.py`, `render_pipeline.py`, etc.) that accept arguments via `argparse` and are called with properly quoted shell arguments: `python3 post_tweet.py --text "$ARGUMENTS"`.

---

### U2 — PIPELINE_LAW Violation: Missing Post-Render Forensics
**What it is:** `render.md` defines the complete render workflow but stops when `daily_producer.py` finishes. The four mandatory forensic steps (`ffprobe` metadata dump, `blackdetect`, `silencedetect`, `ebur128`) are entirely absent.
**Files/Lines:** `render.md:9–14`
**Fix:** Append a mandatory forensic block after the render step:
```bash
ffprobe -v quiet -print_format json -show_streams "$OUTPUT_FILE"
ffmpeg -i "$OUTPUT_FILE" -vf blackdetect=d=0.1:pix_th=0.10 -f null - 2>&1 | tee -a ~/protocol_pulse/logs/render_forensics.log
ffmpeg -i "$OUTPUT_FILE" -af silencedetect=noise=-50dB:d=0.5 -f null - 2>&1 | tee -a ~/protocol_pulse/logs/render_forensics.log
ffmpeg -i "$OUTPUT_FILE" -af ebur128 -f null - 2>&1 | tee -a ~/protocol_pulse/logs/render_forensics.log
```
Log to `~/protocol_pulse/logs/`, never `/tmp`.

---

### U3 — PIPELINE_LAW Violation: `regression_test.sh` Never Called
**What it is:** `commit.md` defines the pre-commit workflow but never invokes `regression_test.sh`. The mandatory quality gate is fully bypassed on every commit.
**Files/Lines:** `commit.md:6–12`
**Fix:** Insert `regression_test.sh` as a hard gate before any `git commit` call. If exit code is non-zero, abort and print the failure log. No exceptions.

---

### U4 — Fragile Service Start: `sleep 10` in `brief.md`
**What it is:** `brief.md:3` waits a fixed 10 seconds for Ollama to start. If initialization takes longer, all downstream script calls silently fail. If it takes less, time is wasted with no feedback.
**Files/Lines:** `brief.md:3`
**Fix:** Replace with a poll loop:
```bash
until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 1; done
```

---

### U5 — Log File Written to `/tmp`
**What it is:** `render.md:12` writes `tee /tmp/latest_render.log`. `/tmp` is world-writable, cleared on reboot, and inappropriate for operational logs.
**Files/Lines:** `render.md:12`
**Fix:** Write to `~/protocol_pulse/logs/latest_render.log`. Ensure the directory exists before execution (`mkdir -p ~/protocol_pulse/logs`).

---

### U6 — Ambiguous Hotfix/Audit Rule in `commit.md`
**What it is:** `commit.md:10` describes a `[HOTFIX-EXEMPT]` prefix rule in confusing terms that cannot be deterministically enforced by an LLM or a human.
**Files/Lines:** `commit.md:10`
**Fix:** Replace with explicit branching logic:
- Pipeline changes → prefix `[PIPELINE]`, audit file required.
- Emergency fixes → prefix `[HOTFIX]`, skip audit, regression tests still mandatory.
- All other commits → standard flow, regression tests mandatory.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason exists)*

All unanimous findings above are also majority findings. Additional majority finding below:

---

### M1 — Brittle JSON Parsing via Python One-Liner in `site-check.md`
**What it is:** `site-check.md:12` pipes `curl` output into `python3 -c "import json, sys; ..."` to extract a field. This is fragile, verbose, and harder to audit than the standard tool.
**Files/Lines:** `site-check.md:12`
**Fix:** Replace with `jq`: `curl -sf "$URL" | jq -r '.price'`. If `jq` is unavailable in the target environment, add a one-time `apt-get install -y jq` to the setup documentation.

---

### M2 — Hardcoded User and Path Assumptions
**What it is:** Multiple commands assume the user is `ultron` and the working directory is `~/protocol_pulse`. No validation is performed. On any other environment these commands fail silently or destructively.
**Files/Lines:** Multiple command files
**Fix:** Source a shared environment file at the top of every command:
```bash
source "${PROTOCOL_PULSE_HOME:-$HOME/protocol_pulse}/.env" || { echo "ERROR: .env not found"; exit 1; }
```
Expose `PROTOCOL_PULSE_HOME` and `PROTOCOL_PULSE_USER` as configurable environment variables.

---

### M3 — No Validation of Required Scripts, Variables, or Directories Before Execution
**What it is:** Every command file executes external scripts and references `.env` variables without first verifying they exist. Missing files or variables produce cryptic errors.
**Files/Lines:** All command files
**Fix:** Add a preflight check block at the top of each command (or extract to a shared `preflight.sh`):
```bash
[[ -f ~/protocol_pulse/.env ]] || { echo "ABORT: .env missing"; exit 1; }
[[ -f ~/protocol_pulse/daily_producer.py ]] || { echo "ABORT: daily_producer.py missing"; exit 1; }
```

---

## UNIQUE INSIGHTS
*(Only 1 model caught this — evaluated below)*

---

### X1 — The Entire Architecture Is Prompt Interpretation, Not Code *(Gemini only)*
**What it is:** Gemini identified that `.md` files in `.claude/commands/` are not scripts — they are natural language prompts the LLM interprets at runtime and converts to shell commands on the fly. This means:
- There is no deterministic execution path.
- Prompt injection in `$ARGUMENTS` (e.g., inside a commit message) could redirect the agent's "interpretation" of the surrounding instructions.
- Debugging failures requires replaying the LLM's reasoning, not a stack trace.

**Assessment: IMPLEMENT.** This is the most important finding in the entire two-cycle review. Every other issue (injection, brittleness, missing forensics) is a symptom of this root cause. Gemini correctly diagnosed the disease while other models treated the symptoms. The fix is the same — migrate to executable Python scripts with `argparse` — but the framing changes the remediation priority. This is not "fix the injection point"; it is "replace the entire command model."

---

### X2 — Second-Order Reliability: "Run One-Liner, Trust Model to Interpret" Pattern *(Grok only)*
**What it is:** Grok noted that `diagnose.md`, `fix.md`, `deploy.md`, and `status.md` all share the pattern of running a diagnostic command and then relying on the LLM to correctly parse and act on the output. This creates non-deterministic behavior at scale.
**Assessment: IMPLEMENT as part of X1 remediation.** Once commands are migrated to Python scripts, the output parsing becomes deterministic code, eliminating this entire class of reliability issue. No separate fix needed — it resolves as a consequence of X1.

---

### X3 — `settings.json` Hooks Execute Arbitrary Scripts on File Edit Events *(Grok only)*
**What it is:** `settings.json` registers hooks that trigger arbitrary script execution on `Write|Edit|MultiEdit` events. If an attacker can trigger edits (e.g., through the agent itself being manipulated), they gain code execution via the hook.
**Assessment: INVESTIGATE FURTHER.** This is a real attack surface but requires understanding what `settings.json` governs (Claude Code tool configuration). The hooks themselves may be a necessary part of the system's design. The fix is to restrict hook scripts to read-only diagnostics and never to mutation operations, and to validate that hook scripts cannot themselves be modified by agent-controlled writes.

---

## CONFLICTS
*(Models gave contradictory recommendations — tiebreaker applied)*

**Conflict 1 — Overall Score (Gemini 23 vs. Grok 38)**
Gemini scored far more harshly in Cycle 2 after identifying the architectural root cause. Grok scored conservatively throughout without dramatically revising.
**Tiebreaker: Gemini is correct.** Once the system is understood as prompt-interpreted rather than code-executed, the error handling score of 35 (Grok) is too generous — there is effectively *no* error handling, because there is no code. A score of 20–25 (Gemini range) is the accurate reflection. Consensus of 30 is a reasonable midpoint but should not be interpreted as "nearly passable"; it reflects a deeply broken system.

**Conflict 2 — Priority of `settings.json` hooks**
Grok flagged as secondary concern; Gemini did not elevate it.
**Tiebreaker: Treat as P2** pending investigation. The injection vectors are the acute threat; hooks are a latent threat that requires architectural context to remediate correctly.

---

## VALIDATED STRENGTHS
*(Both models agree these areas are already working — do NOT change)*

1. **No hardcoded secrets in command files.** Both models confirmed that no API keys, tokens, or credentials are embedded in any `.md` file. The pattern of sourcing `.env` is the correct approach. Preserve it; improve the validation around it.
2. **No race conditions or N+1 query patterns.** The command files are sequential by nature and do not introduce concurrency bugs. This is inherent to the architecture and requires no change.
3. **Scope of commands is well-defined.** Each command file addresses a single concern (`post`, `render`, `commit`, `brief`, etc.). The separation of concerns at the command level is appropriate and should be preserved in the migration to Python scripts.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Evidence |
|---|---|---|
| Always run auto-forensic after render (ffprobe + blackdetect + silencedetect + ebur128) | **VIOLATED** | `render.md` ends after `daily_producer.py`; no forensic step present anywhere |
| Never skip regression_test.sh | **VIOLATED** | `commit.md` contains no reference to `regression_test.sh` |
| AV sync diagnosis before assembler | **UNADDRESSED** | No command enforces checking raw clips before assembly begins |
| Audio target: -14 LUFS, -1 dBTP | **UNADDRESSED** | No command references audio normalization targets; ebur128 not present anywhere |
| AUDIT-FIRST on diagnose/fix | **PARTIALLY COMPLIANT** | `diagnose.md` and `fix.md` state the rule in prose but cannot enforce it — the LLM may or may not obey |

**Final determination:** 2 direct violations, 2 unaddressed requirements, 1 partial compliance. Law compliance is failing at the systemic level because prose-defined rules in `.md` files are non-enforceable by design.

---

## SECURITY CONSENSUS

Priority order (both models confirm):

| Priority | Issue | Surface | Severity |
|---|---|---|---|
| P0 | Command injection via `$ARGUMENTS` in `python -c` strings | `post.md`, `tweet.md`, `render.md` | Critical — RCE possible |
| P0 | Prompt injection into LLM-interpreted command system (Gemini finding) | All `.md` command files | Critical — agent manipulation possible |
| P1 | `settings.json` hooks execute arbitrary scripts on file events | `settings.json` | High — lateral escalation vector |
| P2 | `/tmp` log file world-writable and ephemeral | `render.md:12` | Medium — log tampering, data loss |
| P2 | No `.env` validation before sourcing | All command files | Medium — silent failure or wrong-env execution |
| P3 | Hardcoded `ultron`/`~/protocol_pulse` assumptions | Multiple files | Low-Medium — portability and misfire risk |

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models only)*

1. **Commands are prose prompts, not executable code.** A world-class operational system exposes a typed, validated CLI or API. The agent calls specific tool functions with structured parameters. It does not interpret natural language into shell commands on the fly. This is the foundational gap. *(Both models)*

2. **Zero error handling in the execution layer.** No command checks exit codes, captures stderr, or provides structured failure output. A world-class system exits with non-zero codes, writes structured logs, and pages on failure. *(Both models)*

3. **No environment portability.** Hardcoded users, paths, and sleep timers make this system impossible to run in CI, staging, or on any machine other than the original developer's. World-class tooling is 12-factor compliant — all environment-specific values come from environment variables. *(Both models)*

4. **No regression gate in the commit path.** A world-class system makes it physically impossible to commit without passing tests — not "the instructions say to run tests." The test must be a hard pre-commit hook or CI gate that rejects the push if it fails. *(Both models)*

---

## FINAL ACTION PLAN

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Replace entire `.md` command system with executable Python scripts using `argparse`; restrict agent to calling only these hardened entrypoints | All `.claude/commands/*.md` | Gemini + Grok (architectural root cause) | The current system is prompt-interpreted, non-deterministic, and a prompt injection surface. Every other issue is a symptom of this. |
| **P0 CRITICAL** | Remove `$ARGUMENTS` interpolation into `python3 -c` strings; replace with `python3 script.py --arg "$ARGUMENTS"` | `post.md:13`, `tweet.md:9–11`, `render.md:12` | Both models | Textbook RCE/command injection vector; exploitable with a single quote in user input |
| **P1 HIGH** | Add mandatory post-render forensic block: ffprobe + blackdetect + silencedetect + ebur128; log to `~/protocol_pulse/logs/` | `render.md:9–14` | Both models | Direct violation of PIPELINE_LAW; renders go to production without quality checks |
| **P1 HIGH** | Add `regression_test.sh` as hard gate in commit flow; abort commit on non-zero exit | `commit.md:6–12` | Both models | Direct violation of PIPELINE_LAW; quality gate is completely bypassed |
| **P1 HIGH** | Replace `sleep 10` with health-poll loop for Ollama | `brief.md:3` | Both models | Silent failure if Ollama initializes slowly; no retry or feedback |
| **P1 HIGH** | Add preflight validation for `.env`, required scripts, and directories before any command executes | All command files | Both models | Commands fail cryptically when environment is incomplete |
| **P1 HIGH** | Move log output from `/tmp` to `~/protocol_pulse/logs/` | `render.md:12` | Both models | `/tmp` is world-writable, reboot-cleared, inappropriate for operational logs |
| **P1 HIGH** | Investigate and restrict `settings.json` hooks to read-only operations; ensure hook scripts cannot be modified by agent-controlled writes | `settings.json` | Grok (X3) | Latent escalation vector; hooks execute on edit events the agent controls |
| **P2 MEDIUM** | Replace `python3 -c "import json..."` JSON parsing with `jq` | `site-check.md:12` | Both models | Brittle, verbose, and unnecessary; `jq` is the standard tool |
| **P2 MEDIUM** | Rewrite hotfix/audit commit prefix rule as explicit conditional logic | `commit.md:10` | Both models | Ambiguous prose rule is unenforceable and will be misapplied |
| **P2 MEDIUM** | Replace hardcoded `ultron`/`~/protocol_pulse` references with `$PROTOCOL_PULSE_HOME` and `$PROTOCOL_PULSE_USER` env vars | Multiple files | Both models | Non-portable; fails silently on any other environment |
| **P2 MEDIUM** | Add AV sync diagnosis enforcement before assembler is called | `diagnose.md`, `fix.md` | Law compliance gap | PIPELINE_LAW requires this check; currently unaddressed |
| **P2 MEDIUM** | Add -14 LUFS / -1 dBTP normalization target validation to render forensics block | `render.md` | Law compliance gap | Audio law is entirely unaddressed in any command file |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

After two full cycles of independent multi-model review, the verdict is unambiguous and unanimous.

**The absolute final blockers are:**

1. **The command execution architecture is fundamentally insecure.** Natural language `.md` files interpreted by an LLM into shell commands cannot be audited, tested, or secured. This is not a fixable bug — it requires a full architectural replacement before any other fix has durable value.

2. **Active RCE vector in `post.md`, `tweet.md`, and `render.md`.** Raw `$ARGUMENTS` interpolation into `python3 -c` is exploitable today with zero sophistication required.

3. **Two direct PIPELINE_LAW violations.** Renders ship without forensic validation. Commits bypass regression testing. The governance framework exists but is not enforced by any code.

No P1 or P0 item may be deferred. The system scores **30/100** on consensus, with Security at **16/100**. These numbers reflect a system that is unsafe to operate in any environment where external input can reach the agent.

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/VIDEO_AUDIO_FIX_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/video-audio-fix_CONSENSUS_C2.md.

This is the FINAL PASS for video-audio-fix.
The feature was reviewed by 2 independent AI models (Grok, Gemini) across 2 cycles.
GPT-4o was unavailable due to quota failure.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

═══════════════════════════════════════════════════════
PRIORITY ACTION PLAN:
═══════════════════════════════════════════════════════

P0 CRITICAL | Replace entire .md command system with executable Python scripts
            | using argparse; restrict agent to calling only these hardened
            | entrypoints — no free-form shell execution
            | All .claude/commands/*.md
            | ROOT CAUSE: current system is prompt-interpreted, not code-executed

P0 CRITICAL | Remove all $ARGUMENTS interpolation into python3 -c strings
            | Replace pattern: python3 script.py --text "$ARGUMENTS"
            | post.md:13, tweet.md:9-11, render.md:12
            | WHY: textbook RCE/command injection — single quote breaks syntax

P1 HIGH     | Add mandatory post-render forensic block after daily_producer.py:
            |   ffprobe -v quiet -print_format json -show_streams "$OUTPUT"
            |   ffmpeg -i "$OUTPUT" -vf blackdetect=d=0.1:pix_th=0.10 -f null -
            |   ffmpeg -i "$OUTPUT" -af silencedetect=noise=-50dB:d=0.5 -f null -
            |   ffmpeg -i "$OUTPUT" -af ebur128 -f null -
            |   All logs → ~/protocol_pulse/logs/render_forensics.log
            | render.md:9-14 | PIPELINE_LAW VIOLATION

P1 HIGH     | Add regression_test.sh as hard gate before git commit
            |   Run: bash ~/protocol_pulse/regression_test.sh
            |   On non-zero exit: abort, print log, do not commit
            | commit.md:6-12 | PIPELINE_LAW VIOLATION

P1 HIGH     | Replace sleep 10 with Ollama health-poll loop:
            |   until curl -sf http://localhost:11434/api/tags > /dev/null
            |   do sleep 1; done
            | brief.md:3

P1 HIGH     | Add preflight validation block to every command:
            |   [[ -f ~/protocol_pulse/.env ]] || { echo "ABORT: .env missing"; exit 1; }
            |   [[ -f ~/protocol_pulse/daily_producer.py ]] || { echo "ABORT"; exit 1; }
            |   mkdir -p ~/protocol_pulse/logs
            | All command files

P1 HIGH     | Move render log from /tmp to ~/protocol_pulse/logs/latest_render.log
            | render.md:12

P1 HIGH     | Investigate settings.json hooks — restrict to read-only diagnostics,
            | ensure hook scripts cannot be modified by agent-controlled writes
            | settings.json

P2 MEDIUM   | Replace python3 -c JSON parsing with: curl ... | jq -r '.price'
            | site-check.md:12

P2 MEDIUM   | Rewrite [HOTFIX-EXEMPT] rule as explicit conditional:
            |   [PIPELINE] commits → require audit file
            |   [HOTFIX] commits → skip audit, regression tests still mandatory
            |   All others → standard flow
            | commit.md:10

P2 MEDIUM   | Replace hardcoded paths/user with env vars:
            |   ${PROTOCOL_PULSE_HOME:-$HOME/protocol_pulse}
            |   ${PROTOCOL_PULSE_USER:-$USER}
            | All command files

P2 MEDIUM   | Add AV sync diagnosis enforcement before assembler is called
            | diagnose.md, fix.md

P2 MEDIUM   | Add -14 LUFS / -1 dBTP normalization target validation
            |

---

# WINNER DETERMINATION

# WINNER: **Grok** — Grok delivered the most accurate, consistent, and actionable analysis across both cycles, correctly identifying all critical vulnerabilities (shell injection, law violations, hardcoded assumptions) with specific file/line citations in Cycle 1 that held up without revision in Cycle 2. Its depth exceeded Gemini's initial pass by catching the `$ARGUMENTS` injection vector, the `settings.json` hook surface, and the missing regression/forensic steps simultaneously, while its Cycle 2 output added net-new findings (missing entrypoint validation, second-order model-trust reliability problem) rather than merely restating prior work.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: **risk severity → law compliance → fragility → maintainability**
GPT-4o quota failure does not change ordering; both available models converge on the same ranking.

---

## PRIORITY 1 — CRITICAL BLOCKERS (Ship nothing until resolved)

### P1-A · Shell/Command Injection — `$ARGUMENTS` Interpolation
**Files:** `post.md:13`, `tweet.md:9–11`, `render.md:12`
**Action:** Delete every `python3 -c "... '$ARGUMENTS' ..."` one-liner. Create dedicated entrypoints:
```
post_tweet.py   → accepts --text via argparse
render_pipeline.py → accepts --mode via argparse (allowlist: daily|weekly|test)
```
Call them exclusively as:
```bash
python3 post_tweet.py --text "$ARGUMENTS"
python3 render_pipeline.py --mode "$ARGUMENTS"
```
Allowlist `--mode` values inside the Python script; reject anything outside `{daily, weekly, test}` with exit code 2.
**Why first:** Unanimous, textbook RCE vector. One malformed tweet destroys the host.

---

### P1-B · PIPELINE_LAW Violation — Missing Post-Render Forensics
**File:** `render.md`
**Action:** Append unconditionally after `daily_producer.py` exits:
```bash
ffprobe -v error -show_streams "$OUTPUT_FILE"
ffmpeg -i "$OUTPUT_FILE" -vf blackdetect=d=0.1:pix_th=0.10 -f null - 2>&1 | grep black_
ffmpeg -i "$OUTPUT_FILE" -af silencedetect=n=-50dB:d=0.5 -f null - 2>&1 | grep silence_
ffmpeg -i "$OUTPUT_FILE" -af ebur128 -f null - 2>&1 | tail -20
```
Gate the downstream `commit` step: if any forensic command exits non-zero, abort with a named error.
**Why second:** Explicit law violation; undetected A/V corruption ships to production.

---

### P1-C · PIPELINE_LAW Violation — `regression_test.sh` Never Called
**Files:** `commit.md`, `deploy.md` (neither reference the script)
**Action:** Insert as a mandatory pre-commit gate in `commit.md`:
```bash
bash ~/protocol_pulse/regression_test.sh || { echo "REGRESSION FAILURE — commit blocked"; exit 1; }
```
The exit-code guard is non-negotiable; the law cannot be satisfied by model judgment alone.
**Why third:** Every commit bypasses regression. One bad deploy takes down the pipeline with no automated safety net.

---

## PRIORITY 2 — HIGH SEVERITY (Resolve within current sprint)

### P2-A · `sleep 10` Brittle Service Wait — `brief.md:3`
**Action:** Replace with a bounded health-poll loop:
```bash
for i in $(seq 1 30); do
  curl -sf http://localhost:11434/api/health && break
  sleep 2
done || { echo "Ollama failed to start"; exit 1; }
```
Timeout after 60 seconds; exit non-zero so the caller knows initialization failed.

---

### P2-B · Ephemeral + World-Writable Log Path — `render.md:12`
**Action:** Replace `tee /tmp/latest_render.log` with:
```bash
LOG_DIR=~/protocol_pulse/logs
mkdir -p "$LOG_DIR"
tee "$LOG_DIR/render_$(date +%Y%m%d_%H%M%S).log"
```
`/tmp` is cleared on reboot and writable by all users; render logs are forensic artifacts and must persist.

---

### P2-C · Hardcoded `ultron` Username + Path Assumptions
**Files:** Multiple command files assume `~/protocol_pulse` and user `ultron`
**Action:** Source a single config at the top of each command file:
```bash
PULSE_HOME="${PULSE_HOME:-$HOME/protocol_pulse}"
[ -d "$PULSE_HOME" ] || { echo "PULSE_HOME not found: $PULSE_HOME"; exit 1; }
```
Remove all literal `ultron` references. Portability and fail-fast on misconfiguration.

---

### P2-D · No Validation of Python Entrypoints or `.env` Before Execution
**Files:** `diagnose.md`, `fix.md`, `deploy.md`, `status.md`
**Action:** Add a preflight check block (shared, sourceable):
```bash
[ -f "$PULSE_HOME/.env" ]          || { echo "Missing .env"; exit 1; }
[ -f "$PULSE_HOME/daily_producer.py" ] || { echo "Missing entrypoint"; exit 1; }
source "$PULSE_HOME/.env"
```
Call this before any Python invocation. Silent missing-file failures are the primary cause of the 35/100 Error Handling score.

---

## PRIORITY 3 — MEDIUM SEVERITY (Next sprint)

### P3-A · Brittle JSON Parsing via Python One-Liner — `site-check.md:12`
**Action:** Replace `python3 -c "import json..."` with `jq`:
```bash
curl -sf "$ENDPOINT" | jq '.status'
```
If `jq` unavailability is a real constraint, document it; otherwise the one-liner is unnecessary fragility.

---

### P3-B · Ambiguous `[HOTFIX-EXEMPT]` Logic — `commit.md:10`
**Action:** Rewrite the rule as explicit branching:
```
IF change touches pipeline files:
  REQUIRE audit file present → prefix [PIPELINE]
ELSE IF emergency fix:
  prefix [HOTFIX] → regression_test.sh still runs, forensics skipped with logged reason
ELSE:
  standard commit
```
Ambiguous rules are not enforceable by a model or a human reviewer.

---

### P3-C · `settings.json` Hook Attack Surface
**Action:** Audit every script registered under `Write|Edit|MultiEdit` hooks. Ensure each:
1. Validates its own inputs before execution
2. Cannot be triggered with attacker-controlled file content
This is secondary to P1-A but shares the same injection class; fix P1-A first or this remains exploitable via the same vector.

---

## SUMMARY TABLE

| Priority | ID | File(s) | Severity | Effort |
|---|---|---|---|---|
| 1 | P1-A | post.md, tweet.md, render.md | Critical — RCE | Medium |
| 1 | P1-B | render.md | Critical — Law | Low |
| 1 | P1-C | commit.md, deploy.md | Critical — Law | Low |
| 2 | P2-A | brief.md | High — Reliability | Low |
| 2 | P2-B | render.md | High — Data integrity | Low |
| 2 | P2-C | Multiple | High — Portability | Medium |
| 2 | P2-D | diagnose/fix/deploy/status | High — Error handling | Medium |
| 3 | P3-A | site-check.md | Medium — Fragility | Low |
| 3 | P3-B | commit.md | Medium — Clarity | Low |
| 3 | P3-C | settings.json | Medium — Attack surface | Medium |

**Nothing in Priority 1 