# gpt-oss-20b (openai/gpt-oss-20b) 74 s finish=stop usage in 11689 / out 11276 usd_reported=0.001757 usd~0.204 (upper-bound price)

**FINAL AUDIT – RULING 141 (2) STAND_ALONE SOFT (Feature pp‑selectid‑20261117_1351)**  

| # | Finding | Severity | Why it matters | Fix / Status |
|---|---------|----------|----------------|--------------|
| 1 | `stand_plain` previously returned the raw `SA.opener` string when the regexes failed, potentially exposing a code‑style string that violates RULING 138 (3). | **P1** | The integrator expects a *plain‑words* reason; a code string would break the audit. | **Fixed** – now returns the generic sentence “the clip scorer does not confirm it stands alone”. |
| 2 | `stand_plain` fallback now returns a human‑readable sentence. | **P0** | No defect. | ✅ |
| 3 | `stand_soft_rows` maps segments to labels by position (`zip(labels(len(segs)), segs)`). | **P0** | Design invariant; no bug. | ✅ |
| 4 | `stand_soft_rows` logic correctly rejects any row that fails anything other than the opener or is not marked. | **P0** | Correct. | ✅ |
| 5 | `stand_ok` returns `True` if the check passes or if any soft rows exist. | **P0** | Correct. | ✅ |
| 6 | `stand_with_soft` attaches `soft_rows` to the stand result when present. | **P0** | Correct. | ✅ |
| 7 | `_build`’s `stand_back` logic correctly re‑introduces moments that fail only the opener, removes them from `no_role`, and attaches the `stand_soft` mark. | **P0** | Correct. | ✅ |
| 8 | `inventory` now flags a `stand_alone` gate with the exact prefix and reason when `soft` and `soft_rows` are present. | **P0** | Correct. | ✅ |
| 9 | `package_pin.SOFT_GATES` now includes `"stand_alone"` so the gate is considered a soft gate. | **P0** | Correct. | ✅ |
|10 | Tests added for `stand_plain` fallback, `stand_soft_rows` edge cases, end‑to‑end never‑empty pass, and flagging logic. | **P0** | Coverage improved. | ✅ |
|11 | No test currently covers the `not in trims` guard in `stand_back`. | **P3** | Cosmetic; no functional impact. | Optional – add a unit test if desired. |
|12 | No test covers a non‑conjunction moment with a low clip score that is brought back as a hook. | **P3** | Cosmetic; no functional impact. | Optional – add a unit test if desired. |
|13 | `soft_record` now includes `"soft_stand"` when present. | **P0** | Correct. | ✅ |
|14 | No double‑period issue in `stand_plain` (the two regexes never end with a period). | **P0** | Correct. | ✅ |
|15 | Dense comprehension in `stand_back` is a readability issue. | **P3** | Cosmetic. | Optional – refactor for clarity. |

### Revised Scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `stand_plain` | P1 | **P0** | Fixed fallback. |
| `stand_soft_rows` | P0 | P0 | No change. |
| `stand_ok` | P0 | P0 | No change. |
| `stand_with_soft` | P0 | P0 | No change. |
| `_build` | P0 | P0 | No change. |
| `inventory` | P0 | P0 | No change. |
| `package_pin.SOFT_GATES` | P0 | P0 | No change. |
| Tests | P0 | P0 | Added new tests. |

**P1_OR_WORSE: 0**

### Final Priority List

| Priority | Item | File / Line | Action |
|----------|------|-------------|--------|
| **P0** | All critical logic now correct. | – | No changes required. |
| **P3** | Add unit test for `not in trims` guard. | `tests/package/test_ruling_137.py` | Optional. |
| **P3** | Add unit test for non‑conjunction low‑clip‑score hook scenario. | `tests/package/test_ruling_137.py` | Optional. |
| **P3** | Refactor dense comprehension in `stand_back` for readability. | `pipeline/package.py` | Optional. |

### Single Highest‑Leverage Change

**Fixing `stand_plain` to return a plain‑words sentence instead of the raw `SA.opener` string** – this eliminates the risk of exposing a code‑style string that violates RULING 138 (3) and ensures the integrator’s render receives a human‑readable reason.

### Production Ready?

**Yes, with conditions.**  
All critical and high‑severity issues have been resolved. The added tests cover the new logic and confirm that the never‑empty pass correctly flags soft rows. Optional cosmetic improvements can be made, but they are not required for a production release.