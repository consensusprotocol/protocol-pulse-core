**SECTION 1: CORRECTNESS**

The files are Claude Code slash-command and agent definitions. They correctly define a set of operational commands that map to shell invocations. However, several have correctness issues:

- `post.md:14` and `tweet.md:9-11`: `$ARGUMENTS` is directly interpolated into a Python `-c` string without escaping. A tweet containing single quotes or backticks will break the command or cause syntax errors.
- `render.md:12`: `$ARGUMENTS` is passed raw to `daily_producer.py`. No validation of allowed modes.
- `diagnose.md` and `fix.md` both claim to follow "AUDIT-FIRST" but the command definitions themselves do not enforce reading files first — they rely on the model obeying the text.
- Multiple commands assume `~/protocol_pulse` exists and that the user is `ultron`; no fallback or validation.

No race conditions or N+1 issues exist because these are not application code.

**SECTION 2: LAW COMPLIANCE**

- Always run auto-forensic after render → **PARTIAL** (`render.md` does not invoke ffprobe/blackdetect/silencedetect/ebur128).
- Never skip regression_test.sh → **VIOLATION** (no command references `regression_test.sh`).
- AV sync diagnosis first → **VIOLATION** (no command enforces checking raw clips before assembler).
- Audio target (-14 LUFS, -1 dBTP) → **NOT ADDRESSED** (none of the files reference audio normalization).

Most laws are simply outside the scope of these agent/command files.

**SECTION 3: SECURITY**

**Critical issues present:**

- Multiple commands (`post.md:11-20`, `tweet.md:9`, `fix.md`, `commit.md`) perform direct shell interpolation of `$ARGUMENTS` into `python3 -c "..."` or bash. This is a command injection vector.
- `settings.json` registers hooks that run arbitrary scripts on `Write|Edit|MultiEdit`. If an attacker can trigger edits, they can execute code.
- No sanitization or allow-listing of `$ARGUMENTS` anywhere.
- Secrets: no hardcoded keys in these files (good), but the commands assume `.env` exists without verification.

**SECTION 4: FRONTEND QUALITY**

No frontend code provided. N/A.

**SECTION 5: BACKEND QUALITY**

These files are not backend code. The command definitions are fragile because they lack:

- Error handling around external calls (`pgrep`, `curl`, `python3 -c`).
- Consistent use of `set -e` or explicit failure checking.
- Logging of command execution results.

**SECTION 6: WORLD-CLASS GAP ANALYSIS**

These files are operational tooling for an AI agent, not the product itself. The gap that matters is that the commands encourage the model to run raw shell with user input rather than using a proper CLI interface or Python entrypoints. This is the opposite of what a professional system would do (Bloomberg-style tooling uses structured, validated command interfaces).

**SECTION 7: SCORES**

- Backend logic: 55/100
- Frontend/UI: N/A
- Error handling: 40/100
- Security: 25/100
- Performance: 70/100
- Law compliance: 30/100
- World-class gap: 35/100
- **OVERALL: 42/100**

**SECTION 8: PRIORITY ACTION PLAN**

P0 CRITICAL | Command injection via `$ARGUMENTS` interpolation | `post.md:11`, `tweet.md:9`, `render.md:12` | Allows arbitrary command execution
P0 CRITICAL | No enforcement of pipeline laws (ffprobe, regression_test.sh) | `render.md` | Direct violation of governing laws
P1 HIGH | All commands lack input validation/escaping | Multiple files | Breaks on normal user input containing quotes
P2 MEDIUM | No verification that required tools/paths exist before execution | `deploy.md`, `pipeline-check.md` | Silent failures in production
P3 LOW | Repetitive boilerplate across command files | All `.md` command files | Maintenance burden

**SECTION 9: THE ONE THING**

Stop interpolating `$ARGUMENTS` directly into shell and Python `-c` strings — use a proper argument parser or at minimum `shlex.quote`.

**SECTION 10: FINAL VERDICT**

Not ready for production use as written. The command injection risk and complete absence of the required video pipeline forensic steps (ffprobe, regression tests, LUFS checks) are blocking issues. These files should be rewritten to call validated Python entrypoints instead of raw shell interpolation.