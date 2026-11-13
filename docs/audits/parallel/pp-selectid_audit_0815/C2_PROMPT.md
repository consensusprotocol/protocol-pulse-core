# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0815
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 177 s finish=stop usage in 8925 / out 4983 usd~0.102 (upper-bound price)

# Audit: ruling 52 — the hook rated on its own job (pp-selectid)

Scope note: I can only verify what the diff shows. `medley()`'s tail (the `ok` computation, `flagged`, the return) is truncated at diff line 81/82 — the last visible lines are the `tl`/`flagged` assignments and the start of the `ok =` expression. I assume the remainder is unchanged; where that matters I say so.

## P0

None.

## P1

**P1-1 — The hook's derived rating is computed after the contract check but the derivation itself is unvalidated only by construction of `min()`; however the reply's `hook` parts are validated, so this is actually fine — the real P1 is the truncated `ok` line.**
File: pipeline/package.py, diff lines 78–81 (hunk `@@ -944,6 +959,7 @@`).

The diff shows:

```python
v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
tl = v["through_line"] if isinstance(v["through_line"], str) else ""
flagged = [j for j in js if v["joins"][j]["followable"] is False]
ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
```

and then the diff ends. The pass rule per the brief is `min(all ratings) >= COHERENCE_MIN and flagged <= LY_MAX_BRIDGES`. Since the derivation at line 78 injects the hook's rating into `v["clips"]` *before* `ok` is computed, the hook's derived rating participates in the min **only if** the unchanged remainder of the `ok` expression still mins over `v["clips"].values()`. That is the pre-existing pattern (the old code validated `set(v["clips"]) == set(labs)` and presumably minned over it), and the new code keeps `v["clips"]` complete (hook + others) at that point, so the unchanged tail should pick it up. But I cannot see the tail, so I cannot confirm the hook's derived rating actually reaches the pass rule — if the tail mins over the *original* `v["clips"]` captured before line 78, or over a separately-held dict, the hook would silently drop out of the pass rule and a hook part at 3 would pass. The new test `test_ruling_52...` does assert `assertFalse(ok)` for `setup: 3`, which would catch this — so conditional on that test actually exercising `medley()` (it calls `PK.medley(r, self.SEGS, ...)` directly, yes it does), this is covered. Downgrade: verified by test, not by diff. Keep as P1-verified-by-test-only: **the pass rule's treatment of the derived hook rating is not visible in the diff; it is covered only by the new test.** If the test suite is trusted, this is fine; if the diff is the sole evidence, the tail must be shown.

**P1-2 — `verdict["hook_rule"]` is added at the top level of the verdict, but the brief says the parts stay in `verdict["hook"]` and the rule in `verdict["hook_rule"]`; downstream readers of the verdict dict are said to be "unchanged", yet the verdict now carries two new keys (`hook`, `hook_rule`) that any strict-shape consumer (e.g. the sealed medley row, logs) may reject.**
File: pipeline/package.py, diff line 78.

`v = dict(v, clips={...}, hook_rule=HOOK_RULE)` — this adds `hook_rule` as a *new top-level key* to the verdict that `medley()` returns. The brief asserts "Every downstream reader (weak-segment detection, ruling 41's hook swap, the logs, the sealed medley row) is unchanged." I cannot verify from this diff that the sealed medley row (whatever serializes the verdict) tolerates extra keys. If it does a strict `set(v) == {...}` check like `medley()` itself does on the judge's reply (line 67: `set(v) != {"through_line", "hook", "clips", "joins"}` — note it demands *exactly* those keys), the added `hook_rule` (and `hook`) would fail it. Concrete scenario: the sealed medley row writer does `set(row) != {"through_line","clips","joins","flagged","measured","error"}` → KeyError/never-sealed → the run HOLDs. This is the same class of bug the code itself guards against internally, so it's plausible the row writer is equally strict. Not verifiable from the diff; flag for the author to confirm, or show the row-writer's shape check.

**P1-3 — `min(v["hook"][k] for k in HOOK_PARTS)` — the derivation reads `v["hook"]` after `v` was reassigned by `dict(v, ...)`, which is fine, but the derivation happens *outside* the try/except.**
File: pipeline/package.py, diff lines 74–78.

Look at the control flow:

```python
    except ... :
        if r is not None and isinstance(e, (ValueError, TypeError)):
            router.reject(r)
        return False, {"error": ..., "measured": False, "flagged": None}
+   v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=EXACT)
```

Wait — actually, reading the hunk header `@@ -944,6 +959,7 @@` with context: the `except` block's last line (line 77 in the diff, `return False, {...}`) is context, and the new line 78 is inserted *after* the `return`, i.e. after the try/except completes. That means: if the JSON parse or contract check raised, we r

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 37 s finish=stop usage in 8997 / out 442 usd~0.056 (upper-bound price)

**P0: None**

**P1: pipeline/package.py:67-70 (validation block)**  
Concrete scenario: JSON reply contains `"hook":{"scroll":4,"alone":4,"setup":4.0}` (integral float after json.loads). The `type(x) is not int` check rejects it, routing to the `except` block → `measured=False`, `ok=False`. This matches the strict contract test added at test_medley.py:160 but is stricter than the "harmless variations (integral float as int)" rule stated in L-l / test_editorial_robust.py (not visible in this diff). Uncertain whether downstream LLM JSON parser or cache re-validation would ever surface a float.

**P2: pipeline/package.py:78 & tests/package/test_medley.py:94,138**  
The derivation is hardcoded to `min(...)` and `HOOK_RULE` explicitly calls it "the lowest". This matches the audit's stated choice (K1) and the new test assertions. The ruling text only required "derived, never free-form"; min is a reasonable reading but was not the only possible formula.

All other checked items verify cleanly from the diff:
- Hook is no longer rated on through-line (prompt text, `"For each clip AFTER the hook"`, `set(v["clips"]) == set(labs[1:])`, test that `"hook": 1` is absent from prompt).
- Clips after hook rated exactly as before (unchanged prompt language and validation).
- Derived rating cannot be free-form/missing (strict key+type+range contract; every malformed case in test_out_of_contract... returns False/measured=False).
- Joins, flagged-bridge logic, and pass/fail rule are byte-identical to prior version.
- `verdict["clips"]["hook"]` receives the derived integer (line 78) so weak-segment detection / ruling-41 hook swap continue to see it under the expected key.

test_medley.py passes (82 OK); no other suites touched.

**SHIP: yes with conditions** (tighten hook-part validator to accept integral float or rely on shared LLM parser; add float test case).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 29 s finish=stop usage in 9654 / out 1126 usd~0.046 (upper-bound price)

# Code Audit: pp-selectid-0815 (Ruling 52 Implementation)

## Findings

### P0: None
The implementation correctly enforces the "fail closed" requirement for malformed inputs. The contract validation in `pipeline/package.py` (lines 67-73 of the diff) ensures that any deviation from the expected JSON structure (missing keys, wrong types, out-of-range values) results in `ok=False` and `measured=False`. The derived hook rating is strictly computed as `min(v["hook"][k] for k in HOOK_PARTS)` (line 78), preventing free-form or missing ratings.

### P1: None
The logic for the hook's derived rating and the pass/fail condition is sound.
1.  **Hook Rating:** The hook is no longer rated on the through-line. It is rated on `scroll`, `alone`, and `setup`. The final rating is the minimum of these three. This matches the "derived, not free-form" instruction and the stated choice K1 (min formula).
2.  **Pass Condition:** The `ok` variable (line 81) checks `min(v["clips"].values()) >= COHERENCE_MIN`. Since `v["clips"]` now includes the derived hook rating (injected at line 78), the hook must meet the bar (4) via its derived score. The clips after the hook are rated on the through-line as before.
3.  **Joins:** The join logic is unchanged. `flagged` is computed from `v["joins"]` (line 80), and the pass condition still limits flagged joins to `LY_MAX_BRIDGES` (1).

### P2: Observations / Minor Notes

1.  **Prompt Clarity (Line 24):** The prompt explicitly states "For each clip AFTER the hook, rate 1-5...". This is clear. The JSON template (line 30) uses `clip_keys` which is generated from `labs[1:]` (line 61). This correctly excludes the hook from the through-line rating keys in the expected output.
2.  **Test Coverage (Lines 132-149):** The new test `test_ruling_52_the_hook_is_rated_on_its_own_job_in_three_parts` thoroughly verifies:
    *   A low part score (3) leads to a derived hook score of 3 and a FAIL.
    *   All parts at 4 lead to a derived hook score of 4 and a PASS.
    *   The prompt contains the specific new instructions.
    *   The prompt does *not* ask for a through-line rating for the hook.
    *   A low clip score (3) still leads to a FAIL.
3.  **Out-of-Contract Tests (Lines 151-166):** The tests correctly verify that:
    *   Missing hook parts fail.
    *   Out-of-range hook parts (6) fail.
    *   String hook parts ("5") fail.
    *   Including the hook in the `clips` dict (which should only contain `labs[1:]`) fails.
    *   Missing the `hook` key entirely fails.
4.  **Downstream Compatibility:** The verdict structure `v["clips"]` still contains the key `"hook"` (injected at line 78). This ensures that any downstream code reading `verdict["clips"]["hook"]` for weak-segment detection or ruling 41's swap logic will continue to work without modification, as stated in the background.

## Verification of Specific Checks

*   **Hook can no longer pass/fail on through-line rating:** Verified. The through-line rating is only requested for `labs[1:]`. The hook's rating is derived from `scroll/alone/setup`.
*   **Clips rated exactly as before:** Verified. The prompt and validation for `labs[1:]` remain consistent with the previous behavior (1-5 int, through-line relevance).
*   **Derived rating cannot be free-form/missing:** Verified. The code explicitly calculates `min(...)` and validates the input parts are ints 1-5.
*   **Malformed reply is never a pass:** Verified. The `try/except` block and the strict `if not isinstance...` checks ensure any malformed input returns `False, {..., "measured": False}`.
*   **Joins unchanged:** Verified. The join validation and `flagged` logic are identical to the previous version.
*   **Build loop sees hook rating under "hook":** Verified. `v["clips"]` is updated to include `labs[0]` (the hook) with the derived value.

## SHIP: yes

The diff correctly implements Ruling 52. The hook is now evaluated on its specific job (scroll, alone, setup) with a derived minimum score, while the rest of the medley logic (through-line for clips, joins, pass/fail thresholds) remains intact. The tests are comprehensive and cover the new behavior and edge cases. No violations of the Governing Laws are apparent in this specific diff (which focuses on the editorial/selection logic rather than the audio/video rendering gates).

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0815 (RULING 52: the hook rated on its own job): cycle 1 consensus

**Run.** No P0 from any reviewer. Verdicts:
- grok: "yes with conditions" (P1: an integral float);
- qwen: no P0 / P1, "SHIP: yes";
- glm: "yes with conditions" (confirmations only; it agrees that min is the right derivation).

## Answered (verified from the code; no change)

| # | finding | the code |
|---|---|---|
| A1 | grok P1: a part sent as 4.0 (an integral float) is out of contract | The clips' ratings had exactly the same check before this diff: `type(x) is not int`. The hook's parts follow the same contract, consistent, failing closed (not measured, rejected). Relaxing the existing contract is outside ruling 52. |
| A2 | glm P1-1: the unseen tail of `ok` | The line is unchanged: `ok = ... and min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES`. It runs AFTER the derivation, which wrote the hook's rating into v["clips"]["hook"]. So the hook's derived rating is inside the min; the tests show it (one part at 3 gives a FAIL). |
| A3 | glm P1-2: the verdict's two new top-level keys (hook, hook_rule) and strict-shape readers | No reader checks the verdict's shape. Every one takes keys with .get(): measured, flagged, clips, backend, replayed (package.py: ly_shape, the no-voice guard, the build loop's weak detection and log, inventory's medley row). The sealed medley row (inventory) records status, by, replayed, measured and flagged only, so the new keys never reach the seal. |
| A4 | glm P1-3 / P1-1: the derivation sits outside the try | By construction it runs only after the contract has checked the three parts as ints 1-5, so it cannot raise. glm withdraws it in its own text. |
| A5 | K1, the formula | All three reviewers keep min. glm: "a mean would let a 3 hide behind 5s, and would also break the int invariant of clips values". Recorded in HOOK_RULE, the code, and STATE. |

## Verification

- test_medley 82 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0815/C2_STEP.diff (167 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 63f680d..5b7a168 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -516,17 +516,26 @@ Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "
   6 |  "support": {{"id": "..."}}}}]}}"""
   7 |  
   8 |  MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
   9 | -Each clip is a person's own words from a show; the shows were not in one conversation.
  10 | +Each clip is a person's own words from a show; the shows were not in one conversation. The first clip (label "hook")
  11 | +opens the video.
  12 |  
  13 |  {clips}
  14 |  
  15 |  1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
  16 |     "none" if there is none.
  17 | -2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  18 | -3) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  19 | +2) THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
  20 | +   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
  21 | +   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
  22 | +   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
  23 | +   at all)
  24 | +3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  25 | +4) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  26 |     clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
  27 |     words.
  28 | -Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "joins": {{{joins}}}}}"""
  29 | +Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
  30 | +"clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
  31 | +HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
  32 | +HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"
  33 |  
  34 |  WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  35 |  THE ANGLE (the point this video makes): "{angle}"
  36 | @@ -917,10 +926,14 @@ def joins(labs):
  37 |  
  38 |  def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
  39 |      """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
  40 | -    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip, and per join whether a viewer
  41 | -    can follow the jump. Never the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated
  42 | -    (>= 4 words, not 'none'), every clip rates >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable;
  43 | -    verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
  44 | +    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip after the hook on how much it
  45 | +    advances it, and per join whether a viewer can follow the jump. RULING 52: the HOOK is rated on its own job, in
  46 | +    three parts the judge answers separately (HOOK_PARTS: stops a scroll in its first 2-3 s, stands alone, sets up
  47 | +    what follows), and its rating is DERIVED, never free-form: the lowest part (HOOK_RULE), written to
  48 | +    verdict["clips"]["hook"]; the parts stay in verdict["hook"]. Never the vendor / family of the writer. -> (ok,
  49 | +    verdict): ok when the through-line is stated (>= 4 words, not 'none'), every rating (the hook's derived one
  50 | +    included) is >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable; verdict["flagged"] = the joins
  51 | +    a viewer could not follow (a bridge may go only there, L-y 2)."""
  52 |      import providers as P
  53 |      labs = labels(len(segs))
  54 |      js = joins(labs)
  55 | @@ -929,12 +942,14 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
  56 |      r = None
  57 |      try:
  58 |          r = router.call("coherence_verdict",
  59 | -                        MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
  60 | -                            f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
  61 | +                        MEDLEY_PROMPT.format(clips=clips, clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:]),
  62 | +                                             joins=", ".join(f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
  63 |                          1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
  64 |          v = json.loads(r.text.strip())
  65 | -        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
  66 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
  67 | +        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "joins"} or \
  68 | +                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
  69 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
  70 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
  71 |                  any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
  72 |                  not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
  73 |                  any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
  74 | @@ -944,6 +959,7 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
  75 |          if r is not None and isinstance(e, (ValueError, TypeError)):
  76 |              router.reject(r)
  77 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
  78 | +    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
  79 |      tl = v["through_line"] if isinstance(v["through_line"], str) else ""
  80 |      flagged = [j for j in js if v["joins"][j]["followable"] is False]
  81 |      ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
  82 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  83 | index e231c02..062acfe 100644
  84 | --- a/tests/package/test_medley.py
  85 | +++ b/tests/package/test_medley.py
  86 | @@ -44,6 +44,16 @@ def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of
  87 |                            if j in flagged else "same subject"} for j in js}}
  88 |  
  89 |  
  90 | +def reply(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin.", hook=None):
  91 | +    """The clips-alone JUDGE's raw reply (ruling 52): the hook's three parts, the clips after the hook, the joins."""
  92 | +    js = PK.joins(labs)
  93 | +    h = (ratings or {}).get("hook", 5)
  94 | +    return {"through_line": line, "hook": dict({"scroll": h, "alone": h, "setup": h}, **(hook or {})),
  95 | +            "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs[1:]},
  96 | +            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
  97 | +                          if j in flagged else "same subject"} for j in js}}
  98 | +
  99 | +
 100 |  def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
 101 |      """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
 102 |      labs = PK.labels(n)
 103 | @@ -137,7 +147,7 @@ class TestClipsAloneVerdict(unittest.TestCase):
 104 |          return ok, v, r
 105 |  
 106 |      def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
 107 | -        r = Canned(coherence_verdict=[verdict(self.LABS)])
 108 | +        r = Canned(coherence_verdict=[reply(self.LABS)])
 109 |          prompts = []
 110 |          call = r.call
 111 |          r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 112 | @@ -150,24 +160,47 @@ class TestClipsAloneVerdict(unittest.TestCase):
 113 |          self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))
 114 |  
 115 |      def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
 116 | -        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
 117 | +        ok, v, _ = self.run_it(reply(self.LABS, flagged=["clip_01 -> clip_02"]))
 118 |          self.assertTrue(ok)
 119 |          self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
 120 | -        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
 121 | +        ok, v, _ = self.run_it(reply(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
 122 |          self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)
 123 |  
 124 |      def test_no_through_line_or_a_weak_clip_fails(self):
 125 | -        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
 126 | -        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
 127 | -        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])
 128 | +        self.assertFalse(self.run_it(reply(self.LABS, line="none"))[0])
 129 | +        self.assertFalse(self.run_it(reply(self.LABS, line="Bitcoin."))[0])
 130 | +        self.assertFalse(self.run_it(reply(self.LABS, ratings={"clip_02": 3}))[0])
 131 | +
 132 | +    def test_ruling_52_the_hook_is_rated_on_its_own_job_in_three_parts(self):
 133 | +        prompts = []
 134 | +        r = Canned(coherence_verdict=[reply(self.LABS, hook={"setup": 3})])
 135 | +        call = r.call
 136 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 137 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
 138 | +        self.assertFalse(ok)                              # one part under the bar: the hook's derived rating is 3
 139 | +        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
 140 | +        self.assertIn("lowest of scroll / alone / setup", v["hook_rule"])
 141 | +        for part in ('"scroll"', '"alone"', '"setup"', "first 2-3 seconds", "wants the next clip",
 142 | +                     "For each clip AFTER the hook", '"clip_01": 1, "clip_02": 1'):
 143 | +            self.assertIn(part, prompts[0])
 144 | +        self.assertNotIn('"hook": 1', prompts[0])         # the hook is not asked for a through-line rating
 145 | +        ok, v, _ = self.run_it(reply(self.LABS, hook={"scroll": 4, "alone": 4, "setup": 4}))
 146 | +        self.assertTrue(ok)                               # every part at the bar of 4
 147 | +        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
 148 | +        ok, v, _ = self.run_it(reply(self.LABS, ratings={"hook": 5, "clip_01": 3}))
 149 | +        self.assertFalse(ok)                              # the clips keep their own rating and bar
 150 |  
 151 |      def test_out_of_contract_is_not_measured_and_rejected(self):
 152 | -        good = verdict(self.LABS)
 153 | +        good = reply(self.LABS)
 154 |          for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
 155 |                      dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
 156 |                      dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
 157 |                      dict(good, vo_point=5),
 158 | -                    dict(good, clips={"hook": 5, "clip_01": 5})):
 159 | +                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),            # the hook among the clips
 160 | +                    dict(good, hook={"scroll": 5, "alone": 5}),                           # a part missing (ruling 52)
 161 | +                    dict(good, hook={"scroll": 5, "alone": 5, "setup": 6}),
 162 | +                    dict(good, hook={"scroll": "5", "alone": 5, "setup": 5}),
 163 | +                    {k: x for k, x in good.items() if k != "hook"}):
 164 |              ok, v, r = self.run_it(bad)
 165 |              self.assertFalse(ok)
 166 |              self.assertFalse(v["measured"])
 167 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook + 2-4 clips played back to back). Your role: a strict reviewer of the blind "clips-alone" verdict.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- medley() asks a blind judge (never the writer's vendor or family) about the clips alone, in play order: is there a
  through-line a viewer can state; a 1-5 rating per clip of how much it advances it; and per join, can a viewer follow
  it. ok = a stated through-line (>= 4 words, not "none"), every rating >= COHERENCE_MIN (4), at most LY_MAX_BRIDGES
  (1) joins not followable. The returned verdict's "clips" dict (keyed "hook", "clip_01", ...) feeds the build loop:
  a rating under 4 marks that segment weak, and ruling 41's swap replaces it (the hook by the next hook).
- Until now the HOOK was rated like a clip, on "how much it advances the through-line". Builds kept failing on hooks
  rated 3 while their clips were rated 4-5.

The order this diff implements (ORCHESTRATOR RULING 52, 08:06 ET Nov 13, verbatim): "THE HOOK IS RATED ON ITS OWN JOB:
YES. In the clips-alone verdict the hook is no longer rated on 'how much it advances the through-line'. The hook's
rating is: does it stop a scroll in its first 2-3 seconds, does it stand alone, and does it set up what follows (a
viewer who hears it wants the next clip). Bar 4, unchanged. The clips keep their present rating and bar. The join
after the hook is judged as now: followable, or the ONE bridge L-y allows. Two flagged joins still fail. Write the hook
question so the judge answers the three parts separately and the rating is derived, not free-form."

The change (pipeline/package.py, tests/package/test_medley.py):
1. MEDLEY_PROMPT:
   - says the first clip (label "hook") opens the video;
   - asks the hook's three parts separately, each 1-5: "scroll" (do its first 2-3 seconds stop a viewer from
     scrolling past), "alone" (does it stand alone), "setup" (does it set up what follows, so that a viewer who hears
     it wants the next clip);
   - asks the through-line rating only "for each clip AFTER the hook";
   - the join question is unchanged;
   - the JSON shape is {"through_line", "hook": {"scroll", "alone", "setup"}, "clips": {the labels after the hook},
     "joins"}, with the clip keys written out per line-up.
2. medley():
   - the contract requires exactly those keys, the three hook parts as ints 1-5, and the clips after the hook only;
     anything else is out of contract: not measured, rejected, never a pass;
   - the hook's rating is DERIVED as the LOWEST of its three parts (HOOK_RULE: every part must reach the bar) and
     written to verdict["clips"]["hook"]. The parts stay in verdict["hook"], the rule in verdict["hook_rule"];
   - the pass rule is unchanged (min over every rating, the hook's derived one included, >= 4; joins as before).
     Every downstream reader (weak-segment detection, ruling 41's hook swap, the logs, the sealed medley row) is
     unchanged.
3. tests:
   - reply() builds the judge's raw reply in the new shape;
   - the clips-alone tests use it;
   - a new test: one part at 3 gives a derived hook rating of 3 and a FAIL; all parts at 4 pass; the prompt asks the
     three parts and no through-line rating for the hook; a clip at 3 still fails;
   - out-of-contract cases: a part missing, a part out of range or a string, the hook among the clips, no "hook" key.
- test_medley 82 OK; every other suite OK.

A stated choice (K1): the derivation is min(scroll, alone, setup), so the hook passes only when ALL three parts reach
the bar. The ruling says the rating is "derived, not free-form" but does not fix the formula. Say so if you read it
differently (for example, a mean).

Check in particular:
- that the hook can no longer pass or fail on a through-line rating, and that clips are rated exactly as before;
- that the derived rating cannot be free-form or missing, and that every malformed reply is never a pass;
- that the joins (the one bridge, two flagged joins fail) are unchanged;
- that the build loop's weak detection and the hook swap still see the hook's rating under "hook".

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
