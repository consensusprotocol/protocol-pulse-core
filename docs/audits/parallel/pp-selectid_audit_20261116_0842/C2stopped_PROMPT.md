# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_0842
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 371 s finish=stop usage in 10320 / out 5349 usd_reported=0.000983 usd~0.111 (upper-bound price)

The code implements **RULING 119 (1)**, introducing a calibrated floor of **3.0** for the stand-alone clip scorer on the candidates path, restricted to a specific scorer SHA (`edd54964a5ab`), while maintaining the render's standard bar of **3.5**.

### Audit Findings

1.  **Floor Threshold & Scorer Restriction**: 
    *   In `package_pin.py` (lines 71-72), `STAND_ALONE_FLOOR` is correctly set to `3.0` and `STAND_ALONE_FLOOR_SCORER` to `"edd54964a5ab"`.
    *   In `package_pin.py` (line 91), the `on_floor` logic strictly requires the score to be $\ge 3.0$ AND the `scorer_sha` to start with the approved prefix.
    *   In `package.py` (line 18), the same restrictions are applied when identifying floor-affirmed verdicts.
    *   **Result**: Compliant. Nothing under 3.0 or from another scorer is affirmed.

2.  **Render Bar Integrity**:
    *   The render's standard bar (`SCORER_MIN = 3.5`) remains the primary check.
    *   In `package_pin.py` (line 93), the logic `(v["score"] >= SCORER_MIN or on_floor)` ensures that any clip meeting the 3.5 bar passes normally, while only those specifically marked as `calibrated` (and meeting the 3.0 floor) are granted the exception.
    *   **Result**: Compliant. The render's own bar is untouched; the floor is an additive exception for specific approved clips.

3.  **Seal and Marking**:
    *   `package.py` (lines 38-47) correctly identifies segments affirmed *only* on the floor and creates a `stand_alone_bar` mark.
    *   `package_pin.py` (line 102) adds `stand_alone_bar` to the pin dictionary.
    *   The test `test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal` (lines 159-164) confirms that adding this mark does not change the `package_sha256`.
    *   **Result**: Compliant. The mark is carried outside the seal.

4.  **Test Validation**:
    *   `test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on` verifies the 3.0 threshold and the SHA restriction (ensuring other SHAs still require 3.5).
    *   `test_the_pin_check_accepts_a_floor_affirmation_only_whole` ensures that any mutation to the `bar`, `floor`, `score`, or `sha` results in a failure.
    *   **Result**: Compliant.

### Final Verification
- **Nothing < 3.0 affirmed?** Yes (`v["score"] >= 3.0`).
- **Nothing from other scorer affirmed?** Yes (`startswith("edd54964a5ab")`).
- **Render bar untouched?** Yes (3.5 still the default).
- **Mark outside seal?** Yes (verified by hash comparison in tests).

P1_OR_WORSE: 0

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
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

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 66 s finish=stop usage in 9764 / out 2432 usd_reported=0.003126 usd~0.066 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 119 (1)) against the Governing Laws and the specific instructions.

### Analysis

**1. Compliance with Governing Laws**
*   **LAW 20 / M2 (Gate Thresholds):** The change introduces a "calibrated floor" of 3.0 for the *candidates path* (stand-alone scoring) while keeping the *render path* (validate) at 3.5. The code explicitly distinguishes between `affirmed_render` (the strict 3.5 rule) and `affirmed` (which can be true via the floor). The render's own validation logic (`stand_alone.check_edl`) is stated to be unchanged and is not touched in this diff. This complies with the law that gate thresholds are constants and failing gates are hard stops, provided the "floor" is a documented, calibrated exception for a specific sub-process (candidates) and does not weaken the final render gate. The prompt confirms "the render's own validate (3.5) is unchanged".
*   **L-j (Release Authorised on Bytes):** The `stand_alone_bar` mark is placed *outside* the seal in `to_pin`. This is correct because the seal (`package_sha256`) should reflect the core content, while metadata about *how* it was approved (the floor) is auxiliary. The test `test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal` verifies that `package_sha256` remains identical whether the mark is present or not. This is a strong design choice for auditability without breaking byte-identity of the core package.
*   **M12 (Fail Closed):** The `affirmed_verdict` function in `package_pin.py` is strict. It requires `bar == "calibrated"`, `floor == STAND_ALONE_FLOOR`, `score >= STAND_ALONE_FLOOR`, and `scorer_sha` to match the specific measured code. If any of these are missing or wrong, it falls back to the standard `SCORER_MIN` (3.5) check. If the score is 2.9, it fails both. This is fail-closed.

**2. Specific Checks Requested**
*   **(1) Nothing under 3.0 or from another scorer code is ever affirmed:**
    *   In `package_pin.affirmed_verdict`: `on_floor` requires `v["score"] >= STAND_ALONE_FLOOR` (3.0) AND `str(v.get("scorer_sha") or "").startswith(STAND_ALONE_FLOOR_SCORER)`. If `scorer_sha` is different, `on_floor` is False. Then it checks `v["score"] >= SCORER_MIN` (3.5). So a score of 3.2 from a different scorer fails (3.2 < 3.5). A score of 2.9 from the correct scorer fails (2.9 < 3.0). Correct.
    *   In `package.scorer_verdicts`: The floor is only applied if `str(sc["scorer_sha"]).startswith(PPN.STAND_ALONE_FLOOR_SCORER)` and `v["score"] >= PPN.STAND_ALONE_FLOOR`. Correct.
*   **(2) The render's own bar and checks are untouched:**
    *   The diff modifies `scorer_verdicts` to *add* a floor affirmation, but it preserves `affirmed_render` which reflects the original rule (`rule`). The `rule` variable is computed based on the standard logic. The `affirmed` field is set to `rule or floor`. The downstream `stand_alone.check_edl` (render validate) is not in this diff and is stated to be unchanged. The `affirmed_verdict` in `package_pin` is used for pin validation. Does pin validation use the render bar or the candidate bar? The prompt says "the render's own validate (3.5) is unchanged and still checks every pin." However, `package_pin.affirmed_verdict` is the function being modified. If `affirmed_verdict` is used by the render's validate, then the render's bar *is* effectively lowered to 3.0 for pins that have the `bar: "calibrated"` mark.
    *   *Critical Check:* The prompt states: "the render's own validate (stand_alone.check_edl, all clips together, 3.5) still checks every pin at render". This implies `stand_alone.check_edl` does *not* use `package_pin.affirmed_verdict` or that `affirmed_verdict` is only used for the *candidates* path pinning. The diff shows `affirmed_verdict` in `package_pin.py`. If `package_pin` is used for the final release pin, and the final release pin allows 3.0, does that violate the "render's own bar is 3.5" constraint?
    *   The prompt clarifies: "the candidates path's calibrated floor... The render's own validate (3.5) is unchanged". This suggests two distinct paths. The `affirmed_verdict` in `package_pin` is likely used to verify that a *candidate* pin is valid for the *candidates* path. The final render gate is separate. The test `test_the_pin_check_accepts_a_floor_affirmation_only_whole` tests `package_pin.affirmed_verdict`. If this function is the *only* gate for pins, and it now accepts 3.0, is that a violation? The prompt says "the render's own validate... is unchanged". It does *not* say `package_pin.affirmed_verdict` is the render's validate. It says `stand_alone.check_edl` is. Therefore, as long as `stand_alone.check_edl` is not modified, the render bar is safe. The `package_pin` change is for the *candidates* path pinning. This seems consistent.
*   **(3) The mark is outside the seal:**
    *   `to_pin` adds `stan

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_0842 (RULING 119 (1): the candidates path's stand-alone floor)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: qwen 0,
gemma 0, mimo 0. Cycle 1: $0.0063 of Heimdall, not capped.

A CORRECTION TO THE QUESTION (the integrator's finding, 08:44 ET): its "UNCHANGED GUARDS" line was WRONG to say the render's
validate "(stand_alone.check_edl, all clips together, 3.5) still checks every pin". Validate re-asks the scorer ONLY for the
clips that need asking (a clip after the hook opening on a conjunction or reply fragment, or a trimmed clip), ALONE, at 3.5,
with its own call or the production cache, and never reads the pin's scorer_verdict or a stand_alone_bar; so a floor on
this side alone would seal pins the render then HOLDs at validate (shown with production's check_edl and a canned 3.0). qwen's
P2 ("if affirmed_verdict is also used by the final render validation") points at exactly this. THE LANDING THEREFORE: both
ends together or not at all (the integrator's half affirms exactly the marked segments at validate, on the same code and
weights and the pin's own seal, never touching the scorer's files), and only on the orchestrator's explicit yes (STATE
08:49, no default: a loosened integrity gate, ruling 106).

CHANGED AFTER CYCLE 1 (in cycle 2's diff):
1. THE WEIGHTS: the calibration was measured on scorer code edd54964a5ab... AND the model's weights (the Ollama digest of
   gemma3:27b, a418f5838eaf). The floor now also requires the VERDICT's own "digest" to start a418f5838eaf (the integrator
   adds a per-verdict digest to its verdicts file in its half, 08:52 ET); a verdict without one gets no floor (fail closed),
   and the sealed verdict carries it; package_pin.affirmed_verdict requires it. Tests: no digest, or another, gives 3.5 only.
2. mimo P3 / qwen P3 (a 12-character prefix match on a 64-character sha256): the scorer code is now compared EXACTLY, the
   full sha256 edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53 (as the verdicts file carries it); the mark's
   scorer_sha is that full value. The weights digest stays a 12-hex prefix: the integrator gave no more of it (48 bits).

P3 noted, not changed: mimo "affirmed_render is written but read only by a test": it is the record of the render's own
verdict beside the floor's, kept for the build's record and the pin, where the integrator can read why a clip was admitted.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_0842/C2_STEP.diff (183 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index fc9cd76..d933663 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1300,6 +1300,7 @@ def scorer_verdicts(path, code_sha):
   6 |      without a numeric score, with an error, or whose "affirmed" disagrees with the render's own moments rule
   7 |      (stand_alone.affirmed(score, fault, moments=True): the score alone) is no verdict."""
   8 |      import stand_alone as SA
   9 | +    import package_pin as PPN
  10 |      num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
  11 |      stage, sc = "open", None
  12 |      try:
  13 | @@ -1332,7 +1333,15 @@ def scorer_verdicts(path, code_sha):
  14 |          if (v.get("affirmed") is True) != rule:
  15 |              disagree.append(pid)
  16 |              continue
  17 | -        out[str(pid)] = {"score": v["score"], "reason": v.get("reason"), "fault": v.get("fault"), "affirmed": rule,
  18 | +        floor = not rule and sc["scorer_sha"] == PPN.STAND_ALONE_FLOOR_SCORER and \
  19 | +            str(v.get("digest") or "").startswith(PPN.STAND_ALONE_FLOOR_DIGEST) and \
  20 | +            v["score"] >= PPN.STAND_ALONE_FLOOR          # RULING 119 (1): the candidates path's calibrated floor, on
  21 | +        #   the scorer code AND the model weights it was measured on: the VERDICT's own digest (exact even if a file
  22 | +        #   mixed weights; the integrator's contract, 08:52 ET Nov 16); no digest on the verdict: no floor, fail closed
  23 | +        out[str(pid)] = {"score": v["score"], "reason": v.get("reason"), "fault": v.get("fault"),
  24 | +                         "affirmed": rule or floor, "affirmed_render": rule,
  25 | +                         **({"bar": "calibrated", "floor": PPN.STAND_ALONE_FLOOR, "digest": v.get("digest")}
  26 | +                            if floor else {}),
  27 |                           "text_sha256": v["text_sha256"], "prompt_sha256": v.get("prompt_sha256"),
  28 |                           "model": sc.get("model"), "kind": sc["kind"], "event": None, "rubric": sc.get("rubric"),
  29 |                           "rule": sc.get("rule"), "scorer_sha": sc["scorer_sha"], "threshold": sc["threshold"],
  30 | @@ -1341,6 +1350,7 @@ def scorer_verdicts(path, code_sha):
  31 |                   "candidates_generated_at": d.get("candidates_generated_at"), "model": sc.get("model"),
  32 |                   "kind": sc["kind"], "rubric": sc.get("rubric"), "scorer_sha": sc["scorer_sha"],
  33 |                   "threshold": sc["threshold"], "verdicts": len(out), "affirmed": sum(v["affirmed"] for v in out.values()),
  34 | +                 "affirmed_on_the_floor": sum(v.get("bar") == "calibrated" for v in out.values()),
  35 |                   "disagree_with_the_rule": disagree}
  36 |  
  37 |  
  38 | @@ -1500,6 +1510,18 @@ def lineup_bar_mark(med, coh):
  39 |              "calibration_sha256": med.get("calibration_sha256"), "ruling": "116"}
  40 |  
  41 |  
  42 | +def stand_alone_mark(segments):
  43 | +    """RULING 119 (1): what a package carries in its record and pin (outside the seal) when the clip scorer affirmed one
  44 | +    of its segments ONLY on the candidates path's calibrated floor: the plain line for the Telegram note, the floor, the
  45 | +    scorer it was measured on and those segments' places. None when every affirmation met the render's own bar."""
  46 | +    import package_pin as PPN
  47 | +    on = [i for i, s in enumerate(segments) if (s.get("scorer_verdict") or {}).get("bar") == "calibrated"]
  48 | +    if not on:
  49 | +        return None
  50 | +    return {"note": PPN.STAND_ALONE_NOTE, "floor": PPN.STAND_ALONE_FLOOR, "scorer_sha": PPN.STAND_ALONE_FLOOR_SCORER,
  51 | +            "segments": on, "ruling": "119"}
  52 | +
  53 | +
  54 |  def hook_bar_mark(live=None):
  55 |      """RULING 115 (2): what a package sealed on the calibrated bar carries in its record (and its pin, outside the seal):
  56 |      the plain line for the Telegram note, the floors and the calibration's sha. `live`: the bar the build judged its
  57 | @@ -3808,6 +3830,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  58 |          lm = lineup_bar_mark(*(lambda c: (c.get("medley"), c.get("coherence")))(out["package"].get("checks") or {}))
  59 |          if lm:                                           # RULING 116 (Q3): and its line-up, when both verdicts were
  60 |              out["package"]["lineup_bar"] = lm            # judged on the calibrated line-up bar
  61 | +        sm = stand_alone_mark(out["package"].get("segments") or [])
  62 | +        if sm:                                           # RULING 119 (1): a clip the scorer affirmed only on the
  63 | +            out["package"]["stand_alone_bar"] = sm       # calibrated floor
  64 |      if candidate is not None:                             # RULING 66: what became of the candidate
  65 |          t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})
  66 |          out["candidate"]["result"] = t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"
  67 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  68 | index 99f6cae..cb76ff4 100644
  69 | --- a/pipeline/package_pin.py
  70 | +++ b/pipeline/package_pin.py
  71 | @@ -155,6 +155,14 @@ TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): pack
  72 |                                                             # must never pull package.py into that process
  73 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
  74 |  SCORER_MIN = 3.5                                           # = stand_alone.CLIP_MIN_SCORE (a test holds them equal)
  75 | +STAND_ALONE_FLOOR = 3.0                # RULING 119 (1) (orchestrator 08:25 ET Nov 16): the candidates path's calibrated
  76 | +STAND_ALONE_FLOOR_SCORER = "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53"   # floor, rulings 115/116's way: the
  77 | +#   lowest score an approved clip takes
  78 | +STAND_ALONE_FLOOR_DIGEST = "a418f5838eaf"  # and the model's weights (the Ollama digest of gemma3:27b) it was measured on
  79 | +STAND_ALONE_NOTE = "stand-alone affirmed on the calibrated floor (3.0)"   # asked ALONE (2.0), never under 3. Measured
  80 | +#   (the integrator's run, docs/audits/ruling119/APPROVED_CLIPS_SCORER.json, 9216cdb9) on this scorer code only: under
  81 | +#   any other scorer_sha the floor is the render's own SCORER_MIN. The render's validate (all clips together, 3.5) is
  82 | +#   unchanged and still checks every pin.
  83 |  
  84 |  
  85 |  WINDOW_H = 12.0          # RULING 76 (orchestrator 18:08 Nov 13): a clip only while its source is <= 12 h old on the
  86 | @@ -250,10 +258,14 @@ def affirmed_verdict(s):
  87 |      v = s.get("scorer_verdict")
  88 |      num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
  89 |      text = s["approved_text"] if "approved_text" in s else s.get("text")
  90 | -    return isinstance(v, dict) and v.get("affirmed") is True and v.get("kind") == "moments" and "event" in v and \
  91 | -        v["event"] is None and num(v.get("score")) and v.get("threshold") == SCORER_MIN and v["score"] >= SCORER_MIN \
  92 | -        and bool(v.get("scorer_sha")) and isinstance(text, str) and \
  93 | -        v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()
  94 | +    if not (isinstance(v, dict) and num(v.get("score"))):
  95 | +        return False
  96 | +    on_floor = v.get("bar") == "calibrated" and v.get("floor") == STAND_ALONE_FLOOR and \
  97 | +        v["score"] >= STAND_ALONE_FLOOR and v.get("scorer_sha") == STAND_ALONE_FLOOR_SCORER and \
  98 | +        str(v.get("digest") or "").startswith(STAND_ALONE_FLOOR_DIGEST)
  99 | +    return v.get("affirmed") is True and v.get("kind") == "moments" and "event" in v and v["event"] is None and \
 100 | +        v.get("threshold") == SCORER_MIN and (v["score"] >= SCORER_MIN or on_floor) and bool(v.get("scorer_sha")) \
 101 | +        and isinstance(text, str) and v.get("text_sha256") == hashlib.sha256(text.encode("utf-8")).hexdigest()
 102 |  
 103 |  
 104 |  def scorer_problems(segments):
 105 | @@ -499,6 +511,8 @@ def to_pin(pk, run_name):
 106 |                                  #   calibrated hook bar's plain line for the Telegram note, floors and sha (outside the seal)
 107 |                                  **({"lineup_bar": pk["lineup_bar"]} if pk.get("lineup_bar") else {}),   # ruling 116 (Q3):
 108 |                                  #   the line-up's, when both its verdicts passed on the calibrated bar (outside the seal)
 109 | +                                **({"stand_alone_bar": pk["stand_alone_bar"]} if pk.get("stand_alone_bar") else {}),
 110 | +                                #   ruling 119 (1): a clip affirmed only on the calibrated floor (outside the seal)
 111 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 112 |                                  **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
 113 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 114 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 115 | index 1adf4a6..ceaebd6 100644
 116 | --- a/tests/package/test_medley.py
 117 | +++ b/tests/package/test_medley.py
 118 | @@ -1725,6 +1725,64 @@ class TestRuling116LineupBar(unittest.TestCase):
 119 |          self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark
 120 |  
 121 |  
 122 | +class TestRuling119StandAloneFloor(unittest.TestCase):
 123 | +    """RULING 119 (1) (orchestrator 08:25 ET Nov 16): the clip scorer asked ALONE (the candidates path) refused four of
 124 | +    PBX's approved clips (the integrator's run: 2.0 and 3.0); the candidates path's calibrated floor is the lowest an
 125 | +    approved clip takes, never under 3: 3.0, for the scorer code it was measured on only. A clip affirmed only on that
 126 | +    floor marks the package and its pin, outside the seal; the render's own validate (3.5) is unchanged."""
 127 | +
 128 | +    SHA, DIGEST = "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53", "a418f5838eaf" + "0" * 52
 129 | +    OPENER = "And Bitcoin is the hardest money ever made, which is why it wins."       # TestRuling56Scorer's opener
 130 | +
 131 | +    def file(self, verdicts, sha, digest=DIGEST):
 132 | +        """The integrator's file with each verdict's own weights digest (their 08:52 contract): None names none."""
 133 | +        vs = {k: dict(v, **({"digest": digest} if digest else {})) for k, v in verdicts.items()}
 134 | +        return TestRuling56Scorer.file(self, vs, scorer_sha=sha, digest=digest)
 135 | +
 136 | +    def test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on(self):
 137 | +        vs = {"a": fv(self.OPENER, 3.0), "b": fv("Bitcoin b.", 3.4), "c": fv("Bitcoin c.", 2.9), "d": fv("Bitcoin d.", 4.0)}
 138 | +        idx, rec = PK.scorer_verdicts(self.file(vs, self.SHA), self.SHA)
 139 | +        self.assertEqual({k: idx[k]["affirmed"] for k in "abcd"}, {"a": True, "b": True, "c": False, "d": True})
 140 | +        self.assertEqual({k: idx[k].get("bar") for k in "abcd"}, {"a": "calibrated", "b": "calibrated", "c": None,
 141 | +                                                                  "d": None})
 142 | +        self.assertEqual((idx["a"]["affirmed_render"], idx["a"]["floor"], idx["d"]["affirmed_render"]), (False, 3.0, True))
 143 | +        self.assertEqual((rec["affirmed"], rec["affirmed_on_the_floor"]), (3, 2))
 144 | +        other = "s" * 64                                                 # other scorer code: the render's own 3.5
 145 | +        idx, rec = PK.scorer_verdicts(self.file(vs, other), other)
 146 | +        self.assertEqual({k: idx[k]["affirmed"] for k in "abcd"}, {"a": False, "b": False, "c": False, "d": True})
 147 | +        self.assertEqual(rec["affirmed_on_the_floor"], 0)
 148 | +        for digest in (None, "f" * 64):                                  # other weights, or none named: 3.5 only
 149 | +            idx, rec = PK.scorer_verdicts(self.file(vs, self.SHA, digest), self.SHA)
 150 | +            self.assertEqual((idx["a"]["affirmed"], idx["b"]["affirmed"], rec["affirmed_on_the_floor"]), (False, False, 0))
 151 | +
 152 | +    def test_the_pin_check_accepts_a_floor_affirmation_only_whole(self):
 153 | +        idx, _ = PK.scorer_verdicts(self.file({"a": fv(self.OPENER, 3.0)}, self.SHA), self.SHA)
 154 | +        seg = {"text": self.OPENER, "scorer_verdict": idx["a"]}
 155 | +        self.assertTrue(package_pin.affirmed_verdict(seg))
 156 | +        self.assertEqual(package_pin.scorer_problems([{"text": "Bitcoin."}, seg]), [])
 157 | +        for k, val in (("bar", None), ("floor", 2.5), ("score", 2.9), ("scorer_sha", "s" * 64), ("threshold", 3.0),
 158 | +                       ("digest", None), ("digest", "f" * 64)):
 159 | +            v = dict(idx["a"], **{k: val}) if val is not None else {x: y for x, y in idx["a"].items() if x != k}
 160 | +            self.assertFalse(package_pin.affirmed_verdict(dict(seg, scorer_verdict=v)), k)
 161 | +
 162 | +    def test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal(self):
 163 | +        import copy
 164 | +        import test_angles as TA
 165 | +        idx, _ = PK.scorer_verdicts(self.file({"a": fv(self.OPENER, 3.0), "d": fv("Bitcoin d.", 4.0)}, self.SHA),
 166 | +                                    self.SHA)
 167 | +        segs = [{"text": "Bitcoin d.", "scorer_verdict": idx["d"]}, {"text": self.OPENER, "scorer_verdict": idx["a"]}]
 168 | +        m = PK.stand_alone_mark(segs)
 169 | +        self.assertEqual((m["note"], m["floor"], m["segments"], m["ruling"]),
 170 | +                         ("stand-alone affirmed on the calibrated floor (3.0)", 3.0, [1], "119"))
 171 | +        self.assertIsNone(PK.stand_alone_mark(segs[:1]))                # every affirmation on the render's own bar
 172 | +        base = TA.TestPinAndTruth.pk(None)
 173 | +        plain = package_pin.to_pin(copy.deepcopy(base), "r")["moments_package"]
 174 | +        marked = package_pin.to_pin(dict(copy.deepcopy(base), stand_alone_bar=m), "r")["moments_package"]
 175 | +        self.assertNotIn("stand_alone_bar", plain)
 176 | +        self.assertEqual(marked["stand_alone_bar"]["note"], "stand-alone affirmed on the calibrated floor (3.0)")
 177 | +        self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal
 178 | +
 179 | +
 180 |  class TestRuling117JoinSearch(unittest.TestCase):
 181 |      """RULING 117 (orchestrator 16:24 ET Nov 15), SEARCH, DO NOT LOOSEN: the join table (the clips-alone verdict's own
 182 |      join question once per ordered pair of an angle's moments, Grok, cached) and the line-ups chosen BY SEARCH over it
 183 | 
```

---

pp-selectid: RULING 119 (1) (orchestrator 08:25 ET Nov 16), the stand-alone scorer's calibrated floor on the CANDIDATES
path. Files: pipeline/package.py (scorer_verdicts, stand_alone_mark, the mark in build()), pipeline/package_pin.py
(affirmed_verdict; the floor's constants; the mark carried outside the seal), tests/package/test_medley.py.

THE ORDER, verbatim: "If any approved clip is refused, say so plainly and propose the calibrated floor the same way as
rulings 115/116 (the lowest score an approved clip takes under the same asking, never under 3), with DEFAULT IN 20 MIN:
APPLY, audit-first, marked on the pin and in the Telegram note in one plain line."
THE MEASURE (the integrator's run on GPU0, production's scorer code unchanged, scorer_sha edd54964a5ab, three askings per
clip, docs/audits/ruling119/APPROVED_CLIPS_SCORER.json in the main tree): asked ALONE (each clip in its own asking: the
candidates path the builds read), four approved clips are refused: the preview's clip_01 and clip_02 (2.0) and 41f29b1f's
clip_01 and clip_02 (3.0); all clips together (the render's validate) every approved clip is affirmed (lowest 4.0). The
lowest an approved clip takes alone is 2.0; never under 3: THE FLOOR IS 3.0 (from the render's 3.5).

THE CHANGE:
- package_pin: STAND_ALONE_FLOOR = 3.0, STAND_ALONE_FLOOR_SCORER = "edd54964a5ab" (the measured scorer code),
  STAND_ALONE_NOTE (the plain line). affirmed_verdict accepts a verdict at the render's own SCORER_MIN (3.5) as before, OR
  one marked bar "calibrated" with floor == 3.0, score >= 3.0 and a scorer_sha of the measured code; every other check
  (affirmed true, kind "moments", event null, threshold == SCORER_MIN, the text's sha) is unchanged.
- package.scorer_verdicts: the integrator's "affirmed" must still agree with the render's own rule (3.5) or the verdict is
  no verdict (unchanged); a verdict is affirmed on the floor when the render's rule refuses it, its scorer_sha is the
  measured code and its score >= 3.0: "affirmed" true, "affirmed_render" false, bar "calibrated", floor 3.0; the record
  counts affirmed_on_the_floor. Under any other scorer_sha the floor is never applied.
- package.stand_alone_mark(segments) and build(): a sealed package with a segment affirmed only on the floor carries
  moments_package.stand_alone_bar {note, floor, scorer_sha, segments, ruling}; package_pin.to_pin carries it OUTSIDE the
  seal (package_sha256 unchanged). The integrator's Telegram note prints its note (their side, told separately).

UNCHANGED GUARDS (not in the diff): the render's validate (stand_alone.check_edl, all clips together, 3.5) still checks
every pin at render; scorer_verdicts' file checks (kind moments, no event, scorer_sha == the render's code now, threshold ==
CLIP_MIN_SCORE); package_pin.scorer_problems (an opener needs an affirmation); trim_refused (a trimmed text needs one).

TESTS (test_medley TestRuling119StandAloneFloor, 3): the floor affirms 3.0-3.5 only on the measured scorer (2.9 refused;
another scorer_sha: 3.5 only); the pin check accepts a floor affirmation only whole (no bar, another floor, 2.9, another
sha, another threshold: refused); the mark on a package with a floor-affirmed segment, none without, and the pin carries it
outside the seal. Mutations F1-F6 after a control run: 6 of 6 killed. All suite files.

PLEASE CHECK: (1) that nothing under 3.0 and nothing from another scorer code is ever affirmed; (2) that the render's own
bar and checks are untouched; (3) that the mark is outside the seal; (4) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
