# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 22 s finish=stop usage in 8842 / out 1178 usd_reported=0.018773 usd~0.074 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid-20261115_1459 (RULING 115 interim hook bar — FIXED)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
In my Cycle 1 I verified ruling alignment, null-vs-omission semantics, test coverage for the new `valid_h` path, and that no other gate (sha256, rater match, skew, floor-min) was altered. I completely missed the non-finite float path (NaN, ±inf) and the related floor `int()` conversion that could raise uncaught `ValueError`/`OverflowError`. Deepseek's P1 was the only reviewer that surfaced the M12 fail-closed violation; the original code would have crashed a build on a corrupted calibration file. I also did not notice that the `except` clause needed expanding or that the test matrix was insufficient for those exact cases.

2. WHERE DO YOU AGREE OR DISAGREE?
- Deepseek [P1] non-finite floats / huge values → fully agree. The original `type(vh) in (int, float)` + `vh <= 0` let NaN/inf through and `timedelta(hours=vh)` exploded. The fix (range check + `OverflowError` catch + explicit tests) is precise and now kills the mutations.
- Deepseek [P2] test coverage gap → agree; the new test `test_a_calibration_lasts_as_long_as_its_own_valid_h_says` now exercises exactly those cases.
- Qwen on bool subclassing → agree the `type(vh) not in (int, float)` check correctly rejects `True`/`False` (exact type, not `isinstance`). No defect.
- Grok [P3] law L-m comment → agree it is project-internal terminology; no need to change.
- Grok [P2] diff size (tests/docstrings) → partially agree. The functional delta is small; bundling proof with behavior is acceptable for a security-critical calibration gate.
- Consensus on live-bar extra key → agree; no consumer performs whole-dict equality or strict schema validation in the visible codebase.
- Consensus on `valid_h_note` length → agree it is verbose but harmless (sealed JSON, purely documentary).

3. NEW FINDINGS FROM THIS REVIEW
[P3] pipeline/hook_bar.py:60 — `type(vh) not in (int, float)` remains non-idiomatic and brittle for any non-JSON path that could produce a numpy int64 or subclass. The test matrix catches `True` but a comment explaining "exact type check to reject bool" would reduce future maintainer surprise.
[P3] pipeline/hook_bar.py:26 and :60 — `MAX_VALID_H = 24.0 * 366` is arbitrary (leap-year assumption). `timedelta.max.total_seconds() / 3600` would be self-documenting and truly bound to what `timedelta` can represent; minor.
[P2] tests/package/test_hook_bar.py:154 — the `for bad in (float("inf"), float("nan"))` floor test only checks the exception path. It does not assert that a *finite but out-of-range* floor value is refused with the correct message (the `any(v < FLOOR_MIN ...)` line is unreachable for NaN/inf because the `int()` conversion fails first). Coverage is adequate but the test name/comment could be tighter.
[P3] pipeline/hook_calibration.json:86 — the `valid_h_note` duplicates most of the module docstring and ruling text. It inflates the sealed blob with no runtime value; could live in a code comment only.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| hook_bar validation    | P2      | P3      | Non-finite handling (original P1) is now fixed and tested; only style nits remain |
| test coverage          | P2      | P2      | Added NaN/inf cases but floor test could still be clearer |
| documentation / comments | P3    | P3      | No material change |
| live_bar / package integration | P3 | P3 | Unchanged and safe |
| overall M12 fail-closed | P1    | P3      | Deepseek's P1 is resolved; no remaining crash vectors |

5. FINAL PRIORITY LIST
[P3] pipeline/hook_bar.py:60 — add comment explaining exact `type()` check is deliberate to reject bool (already tested).
[P3] pipeline/hook_bar.py:26 — replace magic `24.0 * 366` with `timedelta.max.total_seconds() / 3600` or a named constant with rationale.
[P2] tests/package/test_hook_bar.py:150-154 — expand floor test comment to note that the exception path is the only one exercised for non-finite values.
[P3] pipeline/hook_calibration.json:85-86 — move the long `valid_h_note` into the Python module docstring only; keep JSON minimal.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Adding the finite-range guard `0 < vh <= MAX_VALID_H` plus the `OverflowError` catch turns a potential build-crashing calibration file into a clean refusal, fully restoring M12 fail-closed behavior.

7. PRODUCTION READY?
Yes. All P1/P0 issues identified in Cycle 1 are fixed, mutations are killed, tests cover the new edge cases, and no other gate is altered. The four [P2]/[P3] items above are optional clean-ups that can ship after merge.

P1_OR_WORSE: 0