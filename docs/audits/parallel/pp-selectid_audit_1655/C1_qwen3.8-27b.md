# qwen3.8-27b (qwen/qwen3.8-27b) 41 s finish=stop usage in 11562 / out 1376 usd~0.055 (upper-bound price)

# Audit: pp-selectid-1655 (C1_STEP.diff)

## P0 Findings
None.

## P1 Findings
None.

## P2 Findings

**1. `pipeline/package.py` (diff line 56): `registered` parameter is silently ignored when `candidate` is not `None`.**
The check `if candidate is None else None` correctly implements the requirement that a candidate's own try is never skipped. However, if a caller passes both `candidate` and `registered`, the `registered` map is discarded without warning. This is safe (the candidate build is the only path where `candidate` is set, and it should not skip), but a future caller might accidentally pass both and expect the skip to apply. A `log` or assertion would make the intent explicit. *Low risk; current call sites are correct.*

**2. `tests/package/test_ledger_build.py` (diff lines 135–141): `refused_only()` patches `os.makedirs` globally within its scope.**
The context manager patches `os.makedirs` with `side_effect=AssertionError`. If any code path *inside* the `with` block legitimately calls `os.makedirs` (e.g., a cleanup routine, a temp-file helper that creates a directory), the test will fail with a confusing `AssertionError` rather than the intended refusal message. In the current diff, the guarded blocks only call `PLG.main(...)` and file reads, so this is safe. But the guard is broad: it will catch *any* `os.makedirs` call, not just the one that would write a proof dir. A more targeted patch (e.g., patching the specific `os.makedirs` call in the driver) would be more robust. *Low risk; current usage is correct.*

**3. `pipeline/candidates.py` (diff line 18): `registered()` raises `ValueError` on malformed entries, but the error message includes the raw `lu` value via `!r`.**
If `lu` is a large or sensitive object, the error message could be verbose or leak internal state. In practice, `lu` is a list of strings from a JSON registry, so this is not a concern. *Negligible.*

## Verification Against Required Checks

| Check | Result |
|---|---|
| Registered line-up can never be judged or written by the search, on any path | **PASS.** The check at diff line 56 occurs *after* the line-up is formed (`segs` is not `None`) and *before* `n_lineup += 1` and `spins += 1`. The `break` exits the angle loop. No verdict call, no write call, no `CA.seed` call occurs. All formation paths (first formed, swapped, reordered, pool-filled) converge at this point. |
| The skip never counts as a judged line-up and cannot loop | **PASS.** `n_lineup` and `spins` are incremented *after* the registered check (diff lines 65–66). The `break` exits the angle loop, so no further line-ups are formed for that angle. The `spins > 4 * lineups` guard is never reached for a skipped line-up. |
| Nothing changes what any gate, verdict, or the seal accepts | **PASS.** The diff adds no new gate, no new verdict logic, no new seal check. The `registered` parameter only causes an early `break` with a recorded `why` string. No existing gate threshold, verdict schema, or seal computation is modified. |
| The candidate's own try is never skipped | **PASS.** `held` is set to `None` when `candidate is not None` (diff line 56). The test at diff lines 246–249 confirms: a build from a candidate with the same line-up in `registered` still judges and writes it (`medley_calls == [["h","x","y"]]`, `class == "package"`). |
| The refusal guard cannot leak into other tests | **PASS.** `refused_only()` is a `@contextlib.contextmanager` that uses `mock.patch` as a context manager. The patches are active only within the `with` block. The `yield` is inside the `with`, so the patches are applied before the test body runs and removed after it exits. No global state is modified. The two call sites (diff lines 153, 162) each have their own `with` block. |

## Additional Observations

- **`candidates.registered()` validation is correct.** It checks: `lu` is a list, non-empty, all elements are non-empty strings, and `key(lu) == k`. The test at diff lines 111–114 covers `["a","b"]` (wrong length for key `a+b+c`), `None`, `"abc"`, `["a","","c"]` (empty string), `["a",2,"c"]` (non-string). All raise `ValueError`.

- **The driver's refusal block (diff line 76) calls `CA.registered(reg)` before any write.** If it raises, the `except` at diff line 77 catches it and exits with code 2. The test at diff lines 170–181 confirms: a malformed registry causes `PLG.main` to return 2, the error message contains `"matching its key"`, and the registry file is never rewritten.

- **The `registered` parameter in `package.build` is optional (defaults to `None`).** Existing callers that do not pass it are unaffected. The driver (diff line 87) passes it explicitly.

- **The `rec["registered"]` and `rec["why"]` fields are new keys in the `tried` record.** They do not conflict with existing keys. The test at diff line 234 confirms `medley_ok` is not in the record (no `CA.seed` call).

## SHIP: yes

The fix is correct, minimal, and well-tested. The registered line-up is unconditionally skipped before any judgment or write, the skip does not count toward the line-up budget, the candidate's own try is preserved, and the refusal guard is properly scoped. No gate, verdict, or seal logic is modified. The two P2 items are minor and do not block shipping.