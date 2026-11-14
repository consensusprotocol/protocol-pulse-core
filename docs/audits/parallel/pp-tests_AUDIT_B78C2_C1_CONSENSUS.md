# pp-tests_b78c2 — CYCLE 1 CONSENSUS (written by the session; 2026-11-14 ~09:25 ET)

Why the session writes it: the repo tool's consensus step (claude-sonnet-4-6) cannot run, because Anthropic is out of
credit. Rule (pp-ingest's): a finding is consensus when >= 2 reviewers raise the same file, function and root cause, or
when one reviewer's finding is verified against the code. Refutations carry their evidence.

Reviewers (the same AUDIT_PACKAGE.md, 19,897 chars, built by the repo tool):
- gemini-2.5-pro: 98, ready, one P2.
- Heimdall qwen3.8-27b: 95, ready, one P2 and one P3.
- Heimdall glm-5.3-flash: 92, ready, one P1, two P2 and three P3.
- gpt-4o: OpenAI 429. Grok: not run (unmetered).

## Dispositions
1. glm P1, "force sys.dont_write_bytecode False around the calls, or under -B / PYTHONDONTWRITEBYTECODE the 'no
   bytecode beside the loader' check passes vacuously". ACCEPTED, verified. Measured before the fix: the mutation
   that leaves the flag alone PASSED under `python3 -B`.
   - Now the check sets the flag False for the calls and restores the environment's value in the finally. It asserts
     _key left it False, plus the old no-__pycache__ check.
   - Measured after the fix: all four mutations FAIL, each on its own assertion, both with bytecode on and under -B;
     the real _key passes in both.
2. glm P2, "the stub-record module can leak into sys.modules if a statement before the try raises". ACCEPTED: the
   insertion now sits inside the try / finally.
3. glm P2, "say what the fresh-copy trick assumes". ACCEPTED (docstring: top level only sets constants, no
   self-lookup, not registered in sys.modules).
4. glm P3, "the `path` parameter is dead". REFUTED: it is the seam the scratch mutations used (run.py passes a
   mutated copy). It is now documented as such.
5. glm P3 and qwen P3, "comment the double patch and the io.open_code dependency". ACCEPTED (one comment line). Raised
   by two reviewers.
6. glm P3, "show len(got)". NOT ACTED ON: the message already lists one type per call.
7. qwen P2, "clean up _pp_fb_under_test in sys.modules". REFUTED, measured: module_from_spec + exec_module register
   nothing. After a full check, no `_pp_fb*`, `_pp_baseline*` or `_pp_key*` module is left in sys.modules.
8. Gemini P2, "also deny os.environ and subprocess, so a _key cannot bypass the loader through them". REFUTED.
   - The behaviour asserted is that the VALUE comes from the loader: the sentinel must come back and the stub must see
     the name. A _key reading the environment or a child process returns something else and fails there (measured on
     the bypass mutation: "did not return the loader's value").
   - Denying the environment would also deny what the house loader legitimately does (relay.get_key reads the
     environment first).

No P0. Nothing implemented loosens what a check accepts: items 1 and 2 make the check stricter. Cycle 2 reviews the
UPDATED diff.
