# gpt-oss-20b (openai/gpt-oss-20b) 51 s finish=stop usage in 10246 / out 8225 usd_reported=0.001336 usd~0.154 (upper-bound price)

**1. What the other models caught that I missed**

| # | Finding | Severity | Why it matters |
|---|---------|----------|----------------|
| 1 | `stand_plain` falls back to the raw `SA.opener` string if the regexes don’t match. | **P1** | The spec says the flag must contain *plain‑words* (“it opens on …”). If the upstream format changes, the flag will contain an unreadable, non‑plain string, breaking the integrator’s human‑readable audit. |
| 2 | No end‑to‑end test for a hard `stand_alone` failure in the pin row. | **P3** | The code is correct, but a regression in `stand_with_soft` could silently downgrade a hard failure to a flag. A test would catch that. |
| 3 | `stand_soft_rows` maps segments to labels by position (`labels(len(segs))`). | **P3** | Future callers could pass segments in a different order, causing a soft row to be mis‑attributed. Not a current bug, but a design‑time risk. |
| 4 | Double period when `SA.opener`’s raw string already ends with a period. | **P3** | Cosmetic, but could be confusing in logs. |
| 5 | Dense comprehension for `stand_back`. | **P3** | Readability issue, no functional impact. |

**2. Agreement / disagreement**

| # | Finding | My stance | Reason |
|---|---------|-----------|--------|
| 1 | `stand_plain` fallback | **Agree (P1)** | The requirement is to expose a *plain‑words* reason. Falling back to the raw string violates that contract. |
| 2 | End‑to‑end test missing | **Agree (P3)** | It’s a test gap, not a code defect. |
| 3 | Mapping order | **Agree (P3)** | Design choice; no current bug. |
| 4 | Double period | **Agree (P3)** | Cosmetic. |
| 5 | Dense comprehension | **Agree (P3)** | Cosmetic. |

**3. New findings from this review**

* The `stand_soft_rows` helper returns `None` when `stand.get("medley_names_bitcoin")` is `None`. This is intentional (treat as hard), but the code could be clearer by explicitly checking for `is not None` before accessing `get("pass")`.  
* The `stand_ok` helper uses `bool(stand_soft_rows(...))`. If `stand_soft_rows` returns an empty dict (which it never does because it returns `None` when empty), the logic is still correct, but the intent could be expressed more clearly with `stand_soft_rows(...) is not None`.  
* The `stand_back` comprehension uses `for p in [stand_plain(m)] if p`. If `stand_plain` returns an empty string (unlikely), the comprehension would silently drop the moment. This is fine but could be documented.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `stand_plain` | P0 | **P1** | Fallback to raw string violates spec. |
| `stand_soft_rows` | P0 | P0 | No functional bug. |
| `stand_ok` | P0 | P0 | Correct logic. |
| `stand_with_soft` | P0 | P0 | Correct logic. |
| `stand_back` | P0 | P0 | Correct logic. |
| `inventory` flagging | P0 | P0 | Correct logic. |
| `package_pin.SOFT_GATES` | P0 | P0 | Correct. |
| Tests | P0 | P0 | No new failures. |

**P1_OR_WORSE: 1**

**5. Final priority list**

| Priority | Item | File / Line | Action |
|----------|------|-------------|--------|
| **P1** | `stand_plain` must not silently return the raw `SA.opener` string. | `pipeline/package.py` lines 13‑30 | 1. Add a clear fallback path: log a warning and return a generic “unknown reason” string. 2. Add a unit test (`test_stand_plain_fallback`) that monkey‑patches `SA.opener` to return an unexpected format and asserts the fallback. |
| **P1** | End‑to‑end test for hard `stand_alone` failure in the pin row. | `tests/package/test_ruling_137.py` | Add a test that builds a pin with `soft=True` where the hook row fails (or topic fails) and asserts the row status is `"FAIL"` and that `gate_problems()` is non‑empty. |
| **P2** | Document the positional invariant of `stand_soft_rows`. | `pipeline/package.py` lines 33‑50 | Add a comment or docstring noting that `segs` must be in the order produced by `stand_alone_check`. |
| **P3** | Cosmetic: double period when `why` already ends with a period. | `pipeline/package.py` line 156 | Add a small helper to strip a trailing period before concatenation. |
| **P3** | Dense comprehension for `stand_back`. | `pipeline/package.py` lines 101‑102 | Rewrite as a clearer loop or list comprehension for readability. |

**6. The single highest‑leverage change**

Add a robust fallback in `stand_plain` that logs a warning and returns a clear, human‑readable “unknown reason” string instead of the raw `SA.opener` output, and add a test to guarantee this behavior.

**7. Production ready?**

**Yes, with conditions.**  
- Implement the `stand_plain` fallback and corresponding test.  
- Add the hard‑failure end‑to‑end test.  
- Document the positional invariant of `stand_soft_rows`.  
Once those changes are in place, the code satisfies the RULING 141 (2) contract and is ready for release.