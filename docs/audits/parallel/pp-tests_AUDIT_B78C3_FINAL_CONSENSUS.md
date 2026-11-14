# pp-tests_b78c3 — FINAL CONSENSUS (two cycles; written by the session, 2026-11-14 ~10:15 ET)

Diff audited: the commit after a55e4dcf that answers the integrator's batch 78 cycle-3 finding (test_f0_cpu_guard.py,
BIBLE_ADDITIONS, and the mutations record). Brief: pp-tests_AUDIT_B78C3_BRIEF.md. The session writes the consensus
because the repo tool's consensus step (claude-sonnet-4-6) cannot run: Anthropic is out of credit. Rule (pp-ingest's):
consensus = the same finding from >= 2 reviewers, or one reviewer's finding verified against the code; refutations
carry their evidence.

## The finding answered
glm F1, agreed by qwen27b: a _key that ALSO side-reads the key file through a child, discards the result and returns
the loader's value passed every assertion. What was done:
- The test denies every process start during the two calls, as it denies opens: subprocess.Popen (run /
  check_output / call / os.popen go through it), os.system, posix_spawn[p], fork / forkpty, exec*, spawn*. Each one
  records the attempt and raises `_Denied` (a BaseException).
- The list of process starters checks itself: a control fails if any listed name is missing from os, so a typo cannot
  silently skip one.
- docs/audits/parallel/pp-tests_AUDIT_B78C3_MUTATIONS.md holds the evidence:
  - three side-read mutations (a Python child without pipes, os.system, os.posix_spawn) PASSED the previous test
    (a55e4dcf) and FAIL the new one, in both bytecode modes;
  - the real _key passes; M1-M5 still fail on their own assertions.
- The boundary is stated as measured:
  - _io.open cannot be denied (io.open_code calls it to read the stub, so denying it broke the load), and therefore
    neither can a reference to open bound before the call (tokenize.open);
  - io.FileIO could be denied (measured) but is outside the integrator's "Nothing else changes";
  - C-level calls are not denied;
  - such code is caught only if what it returns is not the loader's value. A process-wide audit hook is offered as a
    follow-up.

## Cycle 1 (the repo tool's package): pp-tests_AUDIT_B78C3_C1_*.md
- gemini-2.5-pro 99, Heimdall qwen3.8-27b 98, Heimdall glm-5.3-flash 92: all mergeable.
- Implemented:
  - the denial record format (Gemini and glm);
  - the mutation evidence committed in the repo (glm P1);
  - a note that the patches are process-wide (qwen P3).
- Refuted: glm's "the flag / sys.path assertions may have been dropped" (they are unchanged lines outside the hunks,
  and M3 / M4 still fail on them).
- Not done: the sys.modules restore (a private name); the audit hook (outside the integrator's scope; offered).

## Cycle 2 (the tool's cycle-2 template, on the diff after the cycle-1 dispositions): pp-tests_AUDIT_B78C3_C2_*.md
- gemini-2.5-pro: "Yes", no change required. Its one remark, "os.spawn* go through os.fork" is a simplification, is
  now exact: "on POSIX".
- Heimdall qwen3.8-27b: "Yes. Merge." Its P2 was to say why io.FileIO is not denied. DONE, and it corrected my own
  wording: the comment had implied FileIO could not be denied. Measured, it can, so it is now listed as outside this
  fix's scope, separately from _io.open, which cannot be denied.
- Heimdall glm-5.3-flash: "Yes, as-is". Its N1 was that a misspelt starter name is skipped silently by the hasattr
  filter. DONE as the self-check control above; all 22 names exist on this interpreter. N2 and N3 are informational.

## Outcome
No P0, P1 or P2 stands. The process-start gap is closed and evidenced, and the remaining boundary is stated as
measured. Nothing loosens what a check accepts. Spend of this audit: $0.138 (gemini-2.5-pro 2 calls $0.132, Heimdall
$0.006); the session's audit ledger stands at $2.292 of the $3.00 cap.
