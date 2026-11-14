# pp-tests_b78c3 — CYCLE 1 CONSENSUS (written by the session; 2026-11-14 ~10:00 ET)

Why the session writes it: the repo tool's consensus step (claude-sonnet-4-6) cannot run, because Anthropic is out of
credit. Rule (pp-ingest's): consensus = the same finding from >= 2 reviewers, or one reviewer's finding verified against
the code. Refutations carry their evidence.

Reviewers (the same AUDIT_PACKAGE.md, 19,211 chars, built by the repo tool):
- gemini-2.5-pro: 99, merge-ready, one P3.
- Heimdall qwen3.8-27b: 98, one P2 and one P3.
- Heimdall glm-5.3-flash: 92, "mergeable as-is", one P1, one P2 and two P3.
- gpt-4o: OpenAI 429. Grok: not run (unmetered).

## Dispositions
1. Gemini P3 and glm P3, the denial record format: `f"{what}{a[:1]!r}"` printed a trailing tuple comma. CONSENSUS
   (two reviewers). DONE: `f"{what}({a[0]!r})"`, or `f"{what}()"` when there are no arguments.
2. glm P1, "the mutation evidence is not in the diff, so the change cannot be verified from it". ACCEPTED, verified:
   it lived only in the session's scratchpad. DONE: docs/audits/parallel/pp-tests_AUDIT_B78C3_MUTATIONS.md holds:
   - every mutation's exact `_key`;
   - how they were run (test_f0's own `_load_frontier_blind` and `_check_key_behaviour`, own process, under the
     suite's guards, bytecode on and under -B);
   - the verbatim results, re-run after item 1: the real _key passes; M1-M8 each fail on their own assertion;
   - the three side reads (M6 a Python child without pipes, M7 os.system, M8 os.posix_spawn) PASSING the previous
     test (a55e4dcf).
3. glm P2, "show the flag_after / sys.path restoration assertions, or they may have been dropped". REFUTED: they are
   unchanged lines outside the diff's hunks. `assert sys.path == path_before`, `assert flag_after is False` and the
   no-__pycache__ assert all follow the `denied == []` assert in `_check_key_behaviour`. M3 (sys.path) and M4
   (bytecode) still fail on them in both bytecode modes (the mutations record).
4. glm P3, "restore a pre-existing sys.modules['_pp_key_stub_record'] instead of popping it". NOT ACTED ON: the name is
   private to this test, and nothing else creates it.
5. qwen P2, "use sys.addaudithook to also see io.FileIO, a pre-bound open and C-level calls". NOT DONE: the integrator
   ordered "Nothing else changes". The boundary is documented in the code and in BIBLE PP-E32, and offered to the
   integrator as a follow-up.
6. qwen P3, "note that the test patches process-global state". DONE: a comment, "process-wide patches, for the two
   calls only (not thread-safe)".

No P0. Nothing loosens what a check accepts. Cycle 2 reviews the updated diff, with the mutations record included.
