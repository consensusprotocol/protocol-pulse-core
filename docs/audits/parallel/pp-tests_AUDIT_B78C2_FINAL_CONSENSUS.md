# pp-tests_b78c2 — FINAL CONSENSUS (two cycles; written by the session, 2026-11-14 ~09:35 ET)

Diff audited: the commit after d7ed4ff8 that answers the integrator's batch 78 cycle-2 finding (test_f0_cpu_guard.py and
BIBLE_ADDITIONS). Brief: pp-tests_AUDIT_B78C2_BRIEF.md. The session writes the consensus because the repo tool's
consensus step (claude-sonnet-4-6) cannot run: Anthropic is out of credit. Rule (pp-ingest's): consensus = the same
file, function and root cause from >= 2 reviewers, or one reviewer's finding verified against the code; refutations
carry their evidence.

## The finding answered
The integrator's consensus (qwen27b, glm and Grok): the key test pinned configuration (a source string search and a
constant equality). What was done:
- The AST scan is kept as test_no_file_of_this_suite_names_the_key_file.
- New behavioural test test_the_baseline_reads_a_key_only_by_name_through_its_loader.
  - It loads a fresh copy of frontier_blind and points its KEY_LOADER at a stub loader file. The stub's get_key
    records each name in a module the test owns, returns a sentinel and counts its loads.
  - Two calls are made with open, io.open and os.open patched to raise a BaseException, and with bytecode writing on.
  - Asserted: nothing opened; both returns are the sentinel (a failure shows types, never values); the stub saw exactly
    those names and was loaded once; sys.path unchanged; the flag restored; no __pycache__ beside the stub.
- The path equality is kept only as a labelled H.control (a configuration pin).
- Scratch mutations, run both with bytecode on and under -B: the real _key passes. Each of these fails on its own
  assertion:
  - a _key that parses a file with open();
  - a _key that parses through os.open / os.read;
  - a _key that bypasses the loader;
  - grok_audit's sys.path form;
  - a _key that leaves bytecode on.

## Cycle 1 (the repo tool's package): pp-tests_AUDIT_B78C2_C1_*.md
- gemini-2.5-pro 98, Heimdall qwen3.8-27b 95, Heimdall glm-5.3-flash 92: all ready.
- Implemented (pp-tests_AUDIT_B78C2_C1_CONSENSUS.md):
  - glm P1: force bytecode writing ON for the calls. Measured before: the leave-bytecode-on mutation PASSED under -B.
  - glm P2: the stub-record insertion moved inside the try.
  - glm P2: a docstring on the fresh-copy assumptions.
  - glm and qwen P3: a comment on the double patch and io.open_code.
- Refuted:
  - qwen's sys.modules cleanup: nothing is registered (measured).
  - Gemini's "deny os.environ and subprocess": the value check already fails any _key whose value is not the
    loader's (measured), and relay.get_key legitimately reads the environment first.
  - glm's "dead path parameter": it is the mutation seam, now documented.

## Cycle 2 (the tool's cycle-2 template, on the diff after the cycle-1 dispositions): pp-tests_AUDIT_B78C2_C2_*.md
- gemini-2.5-pro: "Yes", no new finding.
- Heimdall qwen3.8-27b: "Yes". Its P2 read the flag check as "_key does not restore the flag", which is a misreading:
  _key turns writing off for the load and restores the previous value. The forced False makes `flag_after is False`
  the proof of restoration, and the no-__pycache__ check the proof that writing was off. Acted on as a clarity fix:
  the comment now says both in so many words.
- Heimdall glm-5.3-flash: "Yes", 97. Two items:
  - N5: os.open is not denied, so the rule's wording claims more than the check. DONE, stricter than its doc-only
    suggestion: os.open is denied too, and PP-E32 now says what is and is not denied. New mutation (parse through
    os.open / os.read) fails "_key opened a file" in both bytecode modes.
  - P2-1, a finally that could mask the original error: informational. The finally holds plain assignments only, and
    a comment says so.

## Outcome
No P0 or P1 stands. The new test is behavioural; four mutation kinds plus the os.open one fail it, each on its own
assertion, in both bytecode modes. Nothing loosens what a check accepts. Spend of this audit: $0.135, all logged.
