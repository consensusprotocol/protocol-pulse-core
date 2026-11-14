# claude-fable-5-2 (83 s) usage={'input_tokens': 1938, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 8022, 'output_tokens_details': {'thinking_tokens': 6246}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict:** the two guards do what is claimed for every input I can trace, and I found no GPU1 route through them. The new test does not support the claim made for it, and that is BLOCKING for the claim, not for the guards. The diff does not show `FILES`, `run_fresh.stage_env`, the wrapper, `render16.py`, or any test output, so anything resting on those is unverified.

## Production behaviour

1. **NOT BLOCKING. `pipeline/render_vertical.py:25-26`, `segment_v1/qa_gates.py:22-23`.** Unset, `"0"`, `"1"` and `"0,1"` all still become `"0"`, same as before. Behaviour changes only for exactly `""` and `"-1"`.
2. **NOT BLOCKING, unverified.** "Production always has `=0`" rests on code not in the diff. `qa_gates.py` is a script (docstring line 19: "Exit non-zero on any FAIL"). If any launcher starts it or `render_vertical` with a constructed `env=` carrying `""` or `"-1"`, that stage used to be forced onto GPU0 and now runs without CUDA. Check: grep every launcher for `CUDA_VISIBLE_DEVICES`.
3. **NOT BLOCKING. Same lines.** The match is exact. `" "`, `"-1 "`, `"-1,0"` and `"NoDevFiles"` are still overwritten to `"0"`. This fails toward GPU0, not GPU1.

## GPU1 reach

4. **NOT BLOCKING.** After either guard the value is one of `""`, `"-1"`, `"0"`. Two caveats the diff cannot settle:
   - A later writer in the same process, or a child launched with its own `env=` (`qa_gates.py:19` imports `subprocess`), is not constrained.
   - If CUDA was already initialised before these imports, the write has no effect. This is unchanged from before.

## Test weaknesses (`pipeline/test_gpu0.py:567-579`)

5. **BLOCKING. Line 572.** `FILES` is not in the diff. Line 578 reports paths relative to `PIPELINE`, and `qa_gates.py` lives in `segment_v1/`. If `FILES` is pipeline-rooted, one of the two fixed sites is uncovered. "Any module a run imports" also needs `FILES` to be an import closure, which is not shown.
6. **BLOCKING. Line 579.** There is no positive control. Nothing asserts the scan found the three known sites, so it passes vacuously if `FILES` omits them.
7. **BLOCKING. Lines 575-577.** The assigned value is never checked. A guarded `os.environ["CUDA_VISIBLE_DEVICES"] = "1"` or `"0,1"` passes, so the test does not enforce GPU0-only.
8. **BLOCKING. Line 577.** The guard check is a substring match on the previous line. It passes when that line is a comment containing `not in ("", "-1")`, an `if` on a different variable, or an `if` the assignment is not indented under.
9. **BLOCKING. Line 575.** The regex sees one spelling only. Whether any of the forms below exist in the repo is unverifiable from the diff. It misses:
   - `os.environ.update(...)`, `os.putenv(...)` and `os.environ.setdefault("CUDA_VISIBLE_DEVICES", "1")`.
   - `os.environ["CUDA_VISIBLE_DEVICES"] += ",1"`, because `\s*=` does not match `+=`.
   - `os.environ.pop(...)` or `del os.environ[...]`, which exposes all GPUs.
   - Aliases such as `from os import environ` or `e = os.environ`.
   - A key held in a constant.
   - Spaces inside the brackets, or a subscript split across lines.
   - Child environments such as `dict(os.environ, CUDA_VISIBLE_DEVICES=...)`, `env[...] = ...`, or a shell string `"CUDA_VISIBLE_DEVICES=1 ..."`.
10. **NOT BLOCKING.** There is no behavioural test. Nothing imports either module with `""`, `"-1"`, unset or `"1"` and asserts the result, although E-FAIL-053 was a runtime failure.
11. **NOT BLOCKING. Lines 575-577.** The test also fails closed on legitimate code:
    - a one-line `if …: os.environ[…] = "0"`;
    - `('', '-1')` quoting;
    - a blank line or comment between guard and assignment;
    - a commented-out assignment;
    - a deliberate `= ""`.
12. **NOT BLOCKING. Line 573.** `open(f)` has no encoding and is never closed.

## Required before the claim stands

- Show `FILES` and how it is derived.
- Paste the output of a repo-wide `grep -rn CUDA_VISIBLE_DEVICES` (including `.sh`), with each hit dispositioned.
- Show the test failing against the pre-fix `qa_gates.py`.
- Replace the line-regex with an AST check that covers the writers in item 9 and asserts the value is `"0"`.