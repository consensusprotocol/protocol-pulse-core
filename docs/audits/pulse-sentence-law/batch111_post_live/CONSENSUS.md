# Batch 111 (ruling 142 (3): the post_live whole-stream fallback with the HARD offset guard; decoder lockstep): consensus

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (H1-H4) | FAIL: F1, REAL, fixed (9e10e9a7) | FAIL: F1, NOT a defect |
| 2 (break-it T1-T3) | PASS (0.72), 72.7k characters of reasoning | FAIL: F1 and F2, NOT defects |
| 3 (F1's fix alone) | PASS (0.92) | PASS (1.0) |

## qwen c1 F1, REAL, fixed
- **The defect:** post_live_offset read the word-timing record (and the decode's word times) with no guard. A malformed or missing record, or a non-numeric start, raised a raw exception instead of PinError, the guard's contract.
- **The fix:** both reads are wrapped and raise PinError ("unreadable ... its clock cannot be checked").
- **Must-fail (MUST_FAIL_C1_FIX.log):** the 3 unreadable records and the bad decode time all raise on the code before the fix.

## gpt-oss c1 F1 / c2 F1, NOT defects
- **The claim:** "re / json not imported; REPO undefined".
- **Why not:** pipeline/pinned.py imports re (line 50) and json, and defines REPO (line 57) at module level, outside the diff.

## gpt-oss c2 F2, NOT a defect
- **The claim:** "the cookies argument raises TypeError when None".
- **Why not:** the quoted code is not the diff's. The call site passes `cookies if os.path.exists(cookies) else None` (cookies is _download_window's own path string), and the command builds `(["--cookies", cookies] if cookies else [])`.

## Later change
Batch 112 (on top) routes post_live_offset's word alignment through canon.canon_spans; the canon's own TestSites guard forbids an ad-hoc normaliser. Audited there.

## Own evidence
- MUST_FAIL_OLD_CODE.log: all 11 tests fail on e3bdaf6e (batch 110). The 3 controls fail there because the patched attributes do not exist.
- MUTATIONS.log: 6 of 6 killed.
