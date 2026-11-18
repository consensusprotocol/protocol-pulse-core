# qwen3.8-27b (qwen/qwen3.8-27b) 202 s finish=stop usage in 6638 / out 7651 usd_reported=0.006773 usd~0.135 (upper-bound price)



# Code Audit — pp-selectid / RULING 144 Part 2 (Ingest Adapter Clock Shift)

## Scope Reviewed

`tests/package/proof_ledger.py` (the `a_now` shift + log line) and `tests/package/test_ruling_137.py` (the new `test_the_ingest_adapter_is_asked_as_of_hours_minus_12_earlier`).

---

## Findings

### [P3] Redundant local import in test

`test_ruling_137.py` line 56: `import tempfile` inside the test method, but `tempfile` is already imported at module level (line 42). Harmless, but inconsistent with the rest of the file.

### [P3] `seen[-1]` is fragile if the adapter is ever called more than once

The test asserts on `seen[-1]` without first checking `len(seen) == 1`. If a future refactor causes `LB.rows` to be invoked twice (e.g., a retry path), the test would silently validate the second call's arguments and could pass while the first call's clock is wrong. A `self.assertEqual(len(seen), 1)` before the assertions would make the failure mode explicit.

### [P3] Variable name `a_now` shadows the argparse namespace `a`

In `proof_ledger.py` the local `a` is the argparse namespace; `a_now` reads as "argparse-namespace-now" at a glance. `adapter_now` or `shifted_now` would remove the ambiguity. Purely cosmetic.

---

## Verification of the Four Requested Checks

**(1) Can this admit anything the exception did not authorise?**

No. The adapter's internal expiry drops a moment when `given_now ≥ min(expires_at, published_at + 12 h)`. With `given_now = now − (hours − 12)`, the effective drop condition becomes `now − published_at ≥ hours`. A moment exactly `--hours` old satisfies the "at or past" boundary and is dropped; anything older is also dropped. The adapter's other filters (delivered-in-24 h, opt-out, hard flags) are unchanged and still run on the returned rows. `horizon_h` was already `a.hours` before this change, so the search range is not widened beyond what the exception authorises.

**(2) Can it leak into a build without the flag?**

No. The ternary `now - timedelta(hours=a.hours - base_h) if a.pbx_exception else now` evaluates to `now` when the flag is absent. `base_h` is read before the `if a.pbx_exception:` block that mutates `package_pin.WINDOW_H`, so even if the flag were somehow set and then unset in the same process, the arithmetic would use the original 12. Without the flag, `package_pin.WINDOW_H` is never touched.

**(3) Boundary arithmetic**

With `--hours 26`, `base_h 12`: `a_now = now − 14 h`.
- Moment at `now − 26 h`: expiry = `now − 14 h` = `a_now` → "at or past" → **dropped**. ✓
- Moment at `now − 25.999 h`: expiry = `now − 13.999 h` > `a_now` → **admitted**. ✓
- Moment at `now − 1 h`: expiry = `now + 11 h` > `a_now` → **admitted**. ✓

The `timedelta` subtraction is exact (no floating-point drift at these magnitudes). The log line correctly reports the shifted clock and the effective window.

**(4) The test**

- Correctly patches `PLG.LB.rows` to capture `(now, horizon_h)` and raise, so no downstream code runs.
- Two iterations: no-flag (expects `back ≈ 0`, `h == 12.0`) and `--hours 26 --pbx-exception` (expects `back ≈ 14.0`, `h == 26.0`).
- `t0` is captured immediately before `PLG.main`; the 0.05 h (180 s) delta absorbs any scheduling jitter.
- `PP.WINDOW_H` is saved/restored per iteration, preventing cross-contamination.
- Both stated mutations (clock never moved; shifted by `hours` instead of `hours − 12`) are killed: the first would give `back ≈ 0` in the exception case; the second would give `back ≈ 26`.

---

## Law Compliance

| Law | Status |
|-----|--------|
| LAW 20 / M2 (thresholds are constants; no reclassification) | ✓ — the 12 h constant is unchanged; the exception is a PBX-authorised one-process override, not a threshold edit. |
| M12 FAIL CLOSED | ✓ — if the adapter returns zero rows the build has no candidates and fails; no new pass path. |
| Smallest diff / M1 | ✓ — 4 lines of production logic + 1 log line; no new module, renderer, or selector. |
| GPU0 / no publishing | ✓ — no GPU or network calls in this diff. |

No law violations found.

---

P1_OR_WORSE: 0