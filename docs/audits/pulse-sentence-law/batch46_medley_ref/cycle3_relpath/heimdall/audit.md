# Heimdall audit

**Question:** Batch 46 cycle 3 (a fix found by running regression.sh step 8 after the commit): check_medley_reference.main was given a RELATIVE reference path by step 8; the scratch dir's symlinks (os.symlink(os.path.join(ref, d), ...)) then pointed to a relative target that resolves from /tmp and the cut table crashed (FileNotFoundError, exit 1: fail closed). Fix: ref = os.path.abspath(ref) at the top of main; the command-line test now passes the path RELATIVE from the repo root (proven: it fails without the fix, passes with it). FIND: any other place in check_medley_reference.py where a relative ref path still breaks, a way the fix changes what the check accepts, or a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0012
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] The fix makes main() resolve the ref path against the process CWD, so the check's meaning now depends on where it is invoked from: a relative REF_DIR that exists from one CWD silently resolves differently (or to a different/missing dir) from another, changing exit 2 (SKIP) vs 1 vs 0. Previously a relative path was resolved lazily at each open; now it is frozen once at entry. (agree: 1)
- glm:F2 [low] The test does not test what it claims: it asserts the subprocess's CWD is the repo root (cwd=C.REPO) while passing a repo-relative path, so it only proves the fix works when CWD == REPO. regression.sh step 8's actual CWD is not exercised, and the pre-fix failure mode (symlinks resolving from /tmp) is only reproduced if step 8 also runs from the repo root; if step 8 runs from elsewhere the test passes while the real invocation still fails. (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] Symlink targets are absolute now, but the scratch-dir cleanup (shutil.rmtree) does not unlink the symlinks' targets — fine — yet if write_lock_cut_table raises, the finally block removes tmp while the exception propagates, so the cut-table failure yields an uncaught traceback (exit 1 via crash) rather than the documented 'exit 1 = a decision changed' path; the docstring's fail-closed semantics rely on the crash, not _report.
