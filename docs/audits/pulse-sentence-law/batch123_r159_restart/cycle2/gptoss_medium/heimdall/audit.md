# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 123 (Protocol Pulse, Python): the session watchdog STARTS a dead kept-alive service (ruling 159 (b)). The diff is the whole change as it now stands. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

CYCLE 1: gemma PASS, gpt-oss PASS (both medium effort); qwen at high effort gave no answer in time. CHANGES SINCE CYCLE 1:
(a) restart_dead resolves `running` and `start_service` per call (they were default arguments). INCIDENT, 23:44 ET Nov 23: a test patched W.start_service, the patch missed the bound default, and the REAL start_service opened a live lock pre-check loop from a git worktree in the live tmux session. It ran 28 min (46 answers, all errors, written only under the worktree; no paid call).
(b) start_service now refuses when PP_HEARTBEAT_DIR is set (pipeline/conftest.py sets it for every pytest session) or when the code's REPO is not the main tree (MAIN_TREE).
(c) The 'alive with no finished pass' finding now names its service with dead=False, and restart_dead acts only on dead=True.
(d) lock_precheck.main starts the 60 s heartbeat thread, also in its `once` mode: a pass can now last 17+ min (a post_live whole-stream download), and before this a long pass read as dead.

TRACE AND ANSWER:
T1. Name every way a test or a copy of the code (a worktree, a scratch copy) could still start a live service through this code.
T2. With (d), the pre-check's record `pid` is a short-lived once process. Walk the case: the loop dies between passes. When does the watchdog act, and what does running() see?
T3. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gptoss  |  **Cost:** $0.0023
## Consensus findings (majority of panel agrees)
- **[high] tools/session_watchdog.py:618** Potential KeyError: restart_dead logs to paths["log"] without checking that the key exists.
  - evidence: `log_line(paths["log"], f"RESTART FAILED {name} in {session}: {type(e).__name__}: {str(e)[:160]}")`
  - fix: Use paths.get("log") and handle None, or validate that the log path is present before calling log_line.
  - raised by gptoss:F2; agree: gptoss
- **[high] tools/session_watchdog.py:622** Potential KeyError: restart_dead logs to paths["log"] without checking that the key exists.
  - evidence: `log_line(paths["log"], f"RESTARTED {name} in {session} (ruling 159 (b)): {f['what']}")`
  - fix: Use paths.get("log") and handle None, or validate that the log path is present before calling log_line.
  - raised by gptoss:F3; agree: gptoss

## Raised but not agreed
- gptoss:F1 [high] Potential KeyError: restart_dead modifies f["what"] without ensuring the key exists. (agree: 0)

## Added in cross-examination (not voted on)
- none
