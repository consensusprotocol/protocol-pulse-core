# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 491 s finish=stop usage in 11056 / out 23957 usd_reported=0.002472 usd~0.393 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid (RULING 119 (1))

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**MIMO's three P3 findings — all correctly identified and all now fixed in this diff:**
- [P3→FIXED] The 12-character prefix `startswith` match on a 64-character sha256 → now exact `==` against the full digest at `package.py:18` and `package_pin.py:100`.
- [P3→FIXED] `stand_alone_mark` returned a 12-char prefix under the field name `scorer_sha` → now returns the full 64-char value (`package.py:50`).
- [P3→FIXED] `affirmed_render` looked like dead code → now asserted at `test_medley.py:145`, giving it a clear audit-trail purpose.

**QWEN's P2 concern about `affirmed_verdict` being the render's validate gate** — correctly diagnosed the risk; the comment at `package_pin.py:82-85` now accurately states that `stand_alone.check_edl` re-asks the scorer independently and never reads this side's verdict, and that the floor holds at validate only through the integrator's half landed together on the orchestrator's yes. The original false claim ("still checks every pin") has been corrected.

**GEMMA** found no issues in Cycle 1 — consistent with my read.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| MIMO P3: prefix match | **Agree — fixed** | `sc["scorer_sha"] == PPN.STAND_ALONE_FLOOR_SCORER` and `v.get("scorer_sha") == STAND_ALONE_FLOOR_SCORER` are now exact 64-char comparisons. |
| MIMO P3: mark's scorer_sha | **Agree — fixed** | `stand_alone_mark` returns `PPN.STAND_ALONE_FLOOR_SCORER` which is now the full sha256. |
| MIMO P3: affirmed_render dead | **Agree — addressed** | Asserted at test line 145; serves as audit trail distinguishing render-rule vs floor affirmation. |
| QWEN P2: affirmed_verdict vs validate | **Agree — comment corrected** | The comment now accurately describes validate's behavior. The integrator's half is the bridge. |
| GEMMA: all compliant | **Agree** | No disputes. |
| Consensus: weights digest added | **Agree — correct addition** | `STAND_ALONE_FLOOR_DIGEST` at `package_pin.py:80` requires the model weights digest to match exactly, closing the gap where only scorer code was checked. |

## 3. NEW FINDINGS FROM THIS REVIEW

I traced every path through both `scorer_verdicts` and `affirmed_verdict` with the new exact-match constants:

**Check 1 — Nothing under 3.0, nothing from another scorer:**
- `package.py:18-20`: `floor` requires `not rule` AND `sc["scorer_sha"] == STAND_ALONE_FLOOR_SCORER` (exact) AND `v.get("digest") == STAND_ALONE_FLOOR_DIGEST` (exact) AND `v["score"] >= 3.0`. All four conjuncts. A 2.9 fails the fourth; a different sha fails the second; a different weights digest fails the third. **PASS.**
- `package_pin.py:99-101`: `on_floor` independently re-verifies `bar == "calibrated"`, `floor == 3.0`, `score >= 3.0`, `scorer_sha == STAND_ALONE_FLOOR_SCORER` (exact), `digest == STAND_ALONE_FLOOR_DIGEST` (exact). A hand-crafted verdict cannot smuggle a floor through. **PASS.**
- The `disagree` gate at `package.py:14` still runs first: if the integrator's file says `affirmed=True` but the render's rule says False, the verdict is skipped entirely — the floor only applies to verdicts where both the integrator and the render's rule agree the clip is refused. **Correct.**

**Check 2 — Render's bar untouched:**
- `rule` computation unchanged. `threshold == SCORER_MIN` (3.5) still required in `affirmed_verdict` (`package_pin.py:103`). `affirmed_render` preserves the original rule result. The floor only *widens* `affirmed` when `rule` is already False — it never narrows or bypasses 3.5. **PASS.**

**Check 3 — Mark outside the seal:**
- `to_pin` adds `stand_alone_bar` via conditional spread (`package_pin.py:112`), outside the `package_sha256` computation. Test at `test_medley.py:180` asserts byte-identical seal. **PASS.**

**Check 4 — Tests:**
- Three tests cover: floor affirms 3.0–3.5 only on measured scorer + measured weights (2.9 refused, other sha → 3.5 only, other/prefix/missing digest → 3.5 only); pin check accepts floor only whole (8 mutations: bar, floor, score, scorer_sha, threshold, digest×3 — all refused); mark present/absent correctly, pin carries it outside seal. **PASS.**

**New [P3] finding:**
- [P3] `tests/package/test_medley.py:140` — the test covers scores 3.0, 3.4, 2.9, and 4.0 but not exactly 3.5. The logic is unambiguous (`rule` is True at 3.5, so `not rule` is False, so `floor` is False), but an explicit boundary case would harden the suite.

No [P0] or [P1] findings.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| package.py (scorer_verdicts, stand_alone_mark, build) | 0 | 0 | Exact-match constants, digest gate, disagree gate all correct |
| package_pin.py (affirmed_verdict, constants, to_pin) | 0 | 0 | Five-conjunct on_floor, threshold still 3.5, mark outside seal |
| tests/package/test_medley.py | 0 | 0 | Thorough; one P3 boundary-case gap |

P1_OR_WORSE: 0

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.
**P1 HIGH:** None.
**P2 MEDIUM:** None.

**P3 (nit):**
- `tests/package/test_medley.py:140` — add a verdict with score exactly 3.5 to confirm `bar` is None (floor not applied) and `affirmed_render` is True.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The exact-match on both the scorer code sha256 and the model weights digest — closing the last gap where a prefix or wrong-weights verdict could have slipped through the floor.

## 7. PRODUCTION READY?

**Yes.** All four requested checks pass; every Cycle 1 finding is addressed; the floor is gated on four exact conditions at both ends; the render's 3.5 bar is untouched; the mark is byte-identical outside the seal; the tests kill all mutations.

---

P1_OR_WORSE: 0