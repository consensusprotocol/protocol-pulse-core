# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 431 s finish=stop usage in 9594 / out 20641 usd_reported=0.002208 usd~0.338 (upper-bound price)

# Code Audit: pp-selectid (RULING 119 — Stand-Alone Calibrated Floor)

## Verification of the Four Requested Checks

### (1) Nothing under 3.0 and nothing from another scorer code is ever affirmed

**PASS.** In `scorer_verdicts`, the floor gate is:
```python
floor = not rule and str(sc["scorer_sha"]).startswith(PPN.STAND_ALONE_FLOOR_SCORER) and \
    v["score"] >= PPN.STAND_ALONE_FLOOR
```
All three conjuncts must hold: the render's own rule (3.5) must refuse, the scorer_sha must match the measured code, and score must be ≥ 3.0. A score of 2.9 fails the third conjunct; a different scorer_sha fails the second. The `affirmed` field is `rule or floor`, so nothing below 3.0 and nothing from an unmeasured scorer can be affirmed.

In `affirmed_verdict` (the pin check), `on_floor` independently re-verifies `bar == "calibrated"`, `floor == 3.0`, `score >= 3.0`, and the scorer_sha prefix — so even a hand-crafted verdict dict cannot smuggle a floor affirmation through the pin. The test's mutation loop (removing `bar`, lowering `floor`, dropping `score` to 2.9, swapping `scorer_sha`, changing `threshold`) confirms every partial field is refused.

### (2) The render's own bar and checks are untouched

**PASS.** The `rule` computation, the `disagree` gate (`(v.get("affirmed") is True) != rule → skip`), the `threshold == SCORER_MIN` check in `affirmed_verdict`, and the `scorer_problems` / `trim_refused` guards are all unchanged. The floor is layered *after* the disagree gate and only *widens* `affirmed` when the render's rule already refused — it never narrows or bypasses the 3.5 bar. `affirmed_render` preserves the original rule result for audit. The description confirms `stand_alone.check_edl` (all clips together, 3.5) is untouched.

### (3) The mark is outside the seal

**PASS.** `to_pin` adds `stand_alone_bar` to the pin dict via a conditional spread, and the test asserts `marked["package_sha256"] == plain["package_sha256"]` — the seal is byte-identical with and without the mark. In `build()`, the mark is added to `out["package"]` alongside the existing `lineup_bar` mark (which is also documented as outside the seal), following the same established pattern.

### (4) The tests

**PASS.** Three tests cover: (a) floor affirms 3.0–3.5 only on the measured scorer, 2.9 refused, other scorer → 3.5 only; (b) pin check accepts a floor affirmation only whole (5 mutations all refused); (c) mark present/absent correctly, pin carries it outside the seal. The mutation family F1–F6 (6/6 killed) and full-suite pass are reported.

---

## Findings

**[P3]** `stand_alone_mark` returns `"scorer_sha": PPN.STAND_ALONE_FLOOR_SCORER` which is the 12-character prefix `"edd54964a5ab"`, not a full 64-character sha256. The field name implies a full digest. A consumer reading the mark could mistake it for a complete hash. The test does not assert this field. Consider renaming to `scorer_sha_prefix` or storing the full measured sha.

**[P3]** The `affirmed_render` field is written into every verdict dict in `scorer_verdicts` but is never read anywhere in the visible diff (only asserted in one test line). If it is consumed only by the integrator's out-of-tree Telegram note, that is fine, but it is dead code from this repo's perspective and worth a comment or removal to avoid confusion with `affirmed`.

**[P3]** Both `scorer_verdicts` and `affirmed_verdict` use `str(...).startswith(STAND_ALONE_FLOOR_SCORER)` — a 12-character prefix match on what is otherwise a 64-character sha256. While a sha256 collision on 12 hex chars (48 bits) is computationally infeasible to exploit, an exact `==` comparison against the full measured digest would be strictly safer and costs nothing. The test's `SHA = "edd54964a5ab" + "0" * 52` confirms the full value is available.

No [P0] or [P1] findings. The floor logic is correctly gated, the render's bar is untouched, the mark is outside the seal, and the tests are thorough.

P1_OR_WORSE: 0