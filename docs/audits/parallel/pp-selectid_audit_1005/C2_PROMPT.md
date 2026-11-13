# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1005
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 88 s finish=stop usage in 7927 / out 2468 usd~0.061 (upper-bound price)

# Audit: pp-selectid — coherence verdict adopts ruling 52's hook rating

Scope: I can only verify what the diff shows. I did not see `medley()`, `HOOK_PARTS`, `HOOK_RULE`, `Canned`, or the surrounding `package.py` context; statements about those are inferences from the diff and the stated background, flagged where they matter.

## What the diff establishes

**One definition of the hook's job.** `HOOK_QUESTION` is defined once (package.py:9-13) and interpolated into both prompts: `MEDLEY_PROMPT` at line 27 (`"2) " + HOOK_QUESTION + """`), `COHERENCE_PROMPT` at line 43. The test asserts the prompt carries it and that it also appears in `MEDLEY_PROMPT` (test_medley.py:122-123). The claim that the formatted `MEDLEY_PROMPT` is byte-identical to the committed one is consistent with the diff — the moved text is character-for-character the same, including the line-wrap "1 = not
   at all" — but I cannot execute the comparison; I trust the stated verification.

**Clips-alone verdict unchanged.** The only edits to `MEDLEY_PROMPT` are the extraction of the question into `HOOK_QUESTION` and its re-embedding. No rating rule, threshold, or wording changes. No change to `medley()` appears in the diff. Verified as far as the diff goes.

**Coherence clips/vo_point judged as before.** In the old code the model rated every label in `labs` and the contract checked `set(v["clips"]) == set(labs)`; the pass rule took `min(v["clips"].values() + [vo_point])`. In the new code the model rates only `labs[1:]` (prompt line 48-49 writes the keys via `clip_keys`), the contract checks `set(v["clips"]) == set(labs[1:])` (line 78), and the hook's rating is *derived* — `min(v["hook"][k] for k in HOOK_PARTS)` — then injected as `clips[labs[0]]` (line 85). The final `min(...)` at line 88 therefore ranges over exactly the same set of numbers as before: every clip label plus `vo_point`, with the hook's contribution now the lowest of its three parts instead of a free-form 1-5. The pass rule expression itself (line 87-88: through-line non-empty, not `NO_LINE`, ≥ 4 words, `min(...) >= COHERENCE_MIN`) is untouched. So the *rule* is unchanged; the *hook's number* changes semantics by ruling 52's intent — that is the point of the change, not a regression.

**Malformed reply never a pass.** The contract check (lines 75-80) requires: exact top-level key set `{"through_line", "hook", "clips", "vo_point"}`; `hook` a dict with exactly `set(HOOK_PARTS)`; every hook value `type(x) is not int or not 1 <= x <= 5` → raise; `clips` exactly `set(labs[1:])`; every clips value and `vo_point` int 1-5. Any violation raises `ValueError`, caught at line 81, returning `(False, {"error": ..., "measured": False})` — and the test at test_medley.py:132-139 covers: missing `hook` key, `hook` missing a part, `clips` containing the extra `hook` label (the old contract), and a part out of range (`setup: 0`). All four assert `(ok, measured) == (False, False)` and `r.rejected == ["fake:coherence_verdict"]`. Note the rejection happens only when `r is not None and isinstance(e, (ValueError, TypeError))` — a `ProviderError`/`SpendLimit` returns unmeasured without reject, which is pre-existing behavior, unchanged.

**Derived rating feeds the pass rule.** Line 85 rebuilds `v` with `clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"], hook_rule=HOOK_RULE}`. Since this happens *before* the `ok` computation at line 87-88, the derived hook rating participates in the `min()`. The test at lines 118-130 confirms: `setup: 3` → `clips["hook"] == 3`, `ok` False; all parts 4 → `clips["hook"] == 4`, `ok` True. `hook_rule=HOOK_RULE` is also added to the verdict dict; I cannot see whether any downstream reader of the verdict dict does exact-key-set comparison that this extra key would break — the diff shows no such reader, and the stated downstream readers (takeaway-redo reads `min(coh["clips"])` and `vo_point`; weak-clip drop reads `segments[1:]`) are unaffected. Flagging as unverifiable-from-diff, low risk.

## Findings

**P1 — package.py:85 — `hook_rule` key added to the verdict dict, downstream exact-key contracts unverified.** `v = dict(v, clips={...}, hook_rule=HOOK_RULE)` adds a key that the old verdict dicts never had. If any consumer compares `set(verdict) == {...}` or serializes the verdict into a schema with a closed key set (the codebase's own style — see the strict `set(v) != {...}` contract at line 75 — suggests such patterns exist), it breaks. The diff shows the immediate consumers are key-lookup based, so this is likely fine, but it is the one behavioral addition beyond the ruling's stated scope. Concrete scenario: an attestation/verdict-logging path that round-trips the verdict through a strict schema. Recommend: confirm or note it.

**P2 — package.py:64,69 — `clip_keys` built from `pk["segments"]` order, not the prompt's label order, and assumes `labs` non-

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 33 s finish=stop usage in 8013 / out 205 usd~0.045 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none** (all claims verifiable from diff only: single HOOK_QUESTION definition at package.py:9 used verbatim in both MEDLEY_PROMPT:27 and COHERENCE_PROMPT:43; MEDLEY_PROMPT after substitution byte-identical to prior committed form per test_medley.py:123 assertion; coherence() contract now requires+validates exact {"hook": {scroll,alone,setup}} 1-5 ints and clips only for labs[1:], rejects all malformed cases as measured=False+rejected per package.py:75-79 + test 134-139; hook rating derived as min-of-parts into clips["hook"] + hook_rule at package.py:85 exactly as in medley() and per orchestrator 09:59 ruling; clips-after-hook + vo_point min used in unchanged pass rule at package.py:88 and test 129-130; TestCoherenceHookRating exercises every listed scenario.)

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 45 s finish=stop usage in 8583 / out 1034 usd~0.041 (upper-bound price)

I have reviewed the diff `C1_STEP.diff` against the governing laws, the orchestrator's ruling (09:59 Nov 13), and the specific technical constraints provided.

### Findings

**P0: None**
No critical violations of the Governing Laws or the Orchestrator's Ruling 52 were found. The implementation correctly isolates the hook's "job" rating from the "through-line" rating and applies the derived minimum rule consistently.

**P1: None**
No significant logic errors or contract violations detected.

**P2: Observations & Verifications**

1.  **Single Definition of Hook Job (Verified):**
    *   `pipeline/package.py:9-13` defines `HOOK_QUESTION`.
    *   `pipeline/package.py:27` embeds it into `MEDLEY_PROMPT`.
    *   `pipeline/package.py:43` embeds it into `COHERENCE_PROMPT`.
    *   This satisfies the Orchestrator's requirement: "One definition of the hook's job everywhere it is rated."

2.  **Clips-Alone Verdict Unchanged (Verified):**
    *   The diff shows `MEDLEY_PROMPT` is reconstructed by replacing the inline text with `HOOK_QUESTION`.
    *   The prompt content for the hook section is semantically identical to the previous version (lines 22-26 removed, line 27 added).
    *   The `medley()` function logic is not touched in this diff, implying the downstream parsing for the clips-alone verdict remains stable.

3.  **Coherence Verdict Contract & Derivation (Verified):**
    *   `pipeline/package.py:75-79`: The validation logic now strictly requires `v` to contain `{"through_line", "hook", "clips", "vo_point"}`.
    *   `pipeline/package.py:76-77`: It validates that `v["hook"]` contains exactly the keys in `HOOK_PARTS` and that all values are integers between 1 and 5. This enforces **Law L-l** (A model reply counts only whole; out-of-contract is a failed call).
    *   `pipeline/package.py:78`: It validates that `v["clips"]` keys match `labs[1:]` (i.e., all clips *except* the hook). This correctly separates the hook's "job" rating from the "through-line" rating of the other clips.
    *   `pipeline/package.py:85`: The hook's rating is derived as `min(v["hook"][k] for k in HOOK_PARTS)` and injected into `v["clips"]` under the key `labs[0]` (the hook's label).
    *   `pipeline/package.py:88`: The pass rule `min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN` now includes the derived hook rating. This ensures the hook must meet the quality bar (4) based on its own job, not just its through-line contribution.

4.  **Fail-Closed Behavior (Verified):**
    *   `pipeline/package.py:81-84`: If the JSON structure is invalid, or if the hook/clips/vo_point values are out of range/type, a `ValueError` is raised.
    *   The `except` block catches this, rejects the provider response (`router.reject(r)`), and returns `(False, {"error": ..., "measured": False})`.
    *   This complies with **Law M12** (Fail closed) and **Law L-l** (Malformed reply is never a pass).

5.  **Test Coverage (Verified):**
    *   `tests/package/test_medley.py:118-130`: `test_the_hook_is_rated_on_its_own_job_and_derived` confirms that a low hook part (e.g., `setup: 3`) causes the overall coherence check to fail (`ok` is `False`), even if other clips are high. It also verifies the derived value is stored in `v["clips"]["hook"]`.
    *   `tests/package/test_medley.py:132-139`: `test_out_of_contract_is_not_measured` confirms that missing hook parts, extra keys in clips, or out-of-range values result in `measured: False` and rejection.

### SHIP: yes

The code correctly implements Ruling 52 for the coherence verdict. It uses a single source of truth for the hook's job definition, strictly validates the model's output to prevent partial or malformed passes, and correctly derives the hook's final rating as the minimum of its three components, feeding it into the existing pass/fail logic. The clips-alone verdict remains unchanged.

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1005 (ruling 52's hook rating in the coherence verdict too): cycle 1 consensus

- grok: no P0 / P1, "SHIP: yes"; qwen: no P0 / P1, "SHIP: yes"; glm: "SHIP: yes", with one P1 to confirm.
- glm's P1, confirmed from the code: no consumer compares the coherence verdict's keys exactly.
  - Every reader in package.py takes specific keys: coh.get("clips"), coh.get("vo_point"), coh.get("through_line"),
    coh.get("measured"), coh.get("backend"), coh["vo_point"], coh["clips"].
  - inventory()'s "coherence" row records status, backend, replayed and measured only (row(...)).
  - package_pin's sealed "checks" is a fixed summary dict, not the verdict.
  - So the new key hook_rule reaches neither the seal nor any strict check, as with the clips-alone verdict (audit
    0815 A3).
- glm's recommended identity check of the derivation: the line in coherence() is the same expression as medley()'s:
  `clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}`.
- No change. Verification: test_medley 92 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1005/C2_STEP.diff (145 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c1d391f..9ba7ed7 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -518,6 +518,12 @@ words on what it adds and why it follows the clip before it (an internal note).
   6 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
   7 |  "support": {{"id": "..."}}}}]}}"""
   8 |  
   9 | +HOOK_QUESTION = """THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
  10 | +   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
  11 | +   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
  12 | +   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
  13 | +   at all)"""                    # ruling 52 + the 09:59 answer: ONE definition of the hook's job, in both verdicts
  14 | +
  15 |  MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
  16 |  Each clip is a person's own words from a show; the shows were not in one conversation. The first clip (label "hook")
  17 |  opens the video.
  18 | @@ -526,11 +532,7 @@ opens the video.
  19 |  
  20 |  1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
  21 |     "none" if there is none.
  22 | -2) THE HOOK is judged on its own job, NOT on the through-line. Rate each of its three parts 1-5 separately:
  23 | -   "scroll": do its first 2-3 seconds stop a viewer from scrolling past? (5 = certainly, 1 = not at all)
  24 | -   "alone": does it stand alone, so that a viewer needs nothing said before it? (5 = fully, 1 = not at all)
  25 | -   "setup": does it set up what follows, so that a viewer who hears it wants the next clip? (5 = certainly, 1 = not
  26 | -   at all)
  27 | +2) """ + HOOK_QUESTION + """
  28 |  3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  29 |  4) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
  30 |     clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
  31 | @@ -579,15 +581,17 @@ picked).
  32 |  """
  33 |  
  34 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
  35 | -different person's own words).
  36 | +different person's own words; the first clip, label "hook", opens the video).
  37 |  
  38 |  {package}
  39 |  
  40 |  1) State the video's through-line in ONE sentence, or "none" if it has none.
  41 | -2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  42 | -3) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
  43 | +2) """ + HOOK_QUESTION + """
  44 | +3) For each clip AFTER the hook, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
  45 | +4) Rate 1-5 whether the voice-over makes a point that the clips support (5 = a clear point, fully supported;
  46 |     1 = no point, or a point the clips do not support).
  47 | -Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "vo_point": 1}}"""
  48 | +Return ONLY this JSON object: {{"through_line": "...", "hook": {{"scroll": 1, "alone": 1, "setup": 1}},
  49 | +"clips": {{{clip_keys}}}, "vo_point": 1}}"""
  50 |  
  51 |  
  52 |  def current_levels(sources, ctx, hours=24.0):
  53 | @@ -1041,22 +1045,29 @@ NO_LINE = re.compile(r"^\W*(none|no\b|n/?a\b|unclear|nothing|there is no)", re.I
  54 |  
  55 |  def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
  56 |      """The blind QUALITY verdict (never the vendor / family of the text it judges): through-line + ratings. ->
  57 | -    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7)."""
  58 | +    (ok, verdict). A through-line that reads 'None.', 'no through-line', 'n/a' or is under 4 words is none (M7).
  59 | +    Ruling 52, as the orchestrator answered at 09:59 Nov 13: the HOOK is rated on its own job here too (HOOK_QUESTION,
  60 | +    the same three parts as the clips-alone verdict), and its rating is DERIVED as the lowest part (HOOK_RULE), written
  61 | +    to verdict["clips"]["hook"]; the clips after the hook and vo_point are rated as before."""
  62 |      import providers as P
  63 |      r = None
  64 | +    labs = [sg["label"] for sg in pk["segments"]]
  65 |      try:
  66 | -        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
  67 | -                        avoid_vendor=writer_vendor, avoid_family=writer_family)
  68 | +        r = router.call("coherence_verdict", COHERENCE_PROMPT.format(
  69 | +                            package=CI.package_view(pk), clip_keys=", ".join(f'"{lb}": 1' for lb in labs[1:])),
  70 | +                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
  71 |          v = json.loads(r.text.strip())
  72 | -        labs = [sg["label"] for sg in pk["segments"]]
  73 | -        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
  74 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
  75 | +        if not isinstance(v, dict) or set(v) != {"through_line", "hook", "clips", "vo_point"} or \
  76 | +                not isinstance(v["hook"], dict) or set(v["hook"]) != set(HOOK_PARTS) or \
  77 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["hook"].values()) or \
  78 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs[1:]) or \
  79 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
  80 |              raise ValueError("coherence verdict out of contract")
  81 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
  82 |          if r is not None and isinstance(e, (ValueError, TypeError)):
  83 |              router.reject(r)
  84 |          return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False}
  85 | +    v = dict(v, clips={labs[0]: min(v["hook"][k] for k in HOOK_PARTS), **v["clips"]}, hook_rule=HOOK_RULE)
  86 |      tl = v["through_line"] if isinstance(v["through_line"], str) else ""
  87 |      ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
  88 |          min(list(v["clips"].values()) + [v["vo_point"]]) >= COHERENCE_MIN
  89 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  90 | index 814be17..f2374ca 100644
  91 | --- a/tests/package/test_medley.py
  92 | +++ b/tests/package/test_medley.py
  93 | @@ -209,6 +209,51 @@ class TestClipsAloneVerdict(unittest.TestCase):
  94 |              self.assertEqual(r.rejected, ["fake:coherence_verdict"])
  95 |  
  96 |  
  97 | +class TestCoherenceHookRating(unittest.TestCase):
  98 | +    """The orchestrator's answer (09:59): ruling 52's hook rating applies to the coherence verdict after the takeaway as
  99 | +    well. ONE definition of the hook's job (HOOK_QUESTION) in both verdicts; the hook's rating derived, never free-form."""
 100 | +    PK_ = {"title": "Nobody bends the rules", "caption": "three clips",
 101 | +           "vo": {"intro": None, "bridges": ["No ruler, just rules."], "bridges_after_clip": [2], "signoff": "S"},
 102 | +           "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
 103 | +                        {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
 104 | +                        {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}
 105 | +
 106 | +    def reply(self, hook=None, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
 107 | +        return {"through_line": line, "hook": dict({"scroll": 5, "alone": 5, "setup": 5}, **(hook or {})),
 108 | +                "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}
 109 | +
 110 | +    def run_it(self, reply):
 111 | +        r = Canned(coherence_verdict=[reply])
 112 | +        prompts = []
 113 | +        call = r.call
 114 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
 115 | +        ok, v = PK.coherence(r, self.PK_, {"heimdall"}, writer_family={"deepseek"})
 116 | +        return ok, v, r, prompts
 117 | +
 118 | +    def test_the_hook_is_rated_on_its_own_job_and_derived(self):
 119 | +        ok, v, _, prompts = self.run_it(self.reply(hook={"setup": 3}))
 120 | +        self.assertFalse(ok)
 121 | +        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
 122 | +        self.assertIn(PK.HOOK_QUESTION, prompts[0])                 # the one definition, as in the clips-alone verdict
 123 | +        self.assertIn(PK.HOOK_QUESTION, PK.MEDLEY_PROMPT)
 124 | +        self.assertIn("For each clip AFTER the hook", prompts[0])
 125 | +        self.assertIn('"clips": {"clip_01": 1, "clip_02": 1}', prompts[0])
 126 | +        ok, v, _, _ = self.run_it(self.reply(hook={"scroll": 4, "alone": 4, "setup": 4}))
 127 | +        self.assertTrue(ok)
 128 | +        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
 129 | +        self.assertFalse(self.run_it(self.reply(clips={"clip_02": 3}))[0])      # clips and vo_point as before
 130 | +        self.assertFalse(self.run_it(self.reply(vo=3))[0])
 131 | +
 132 | +    def test_out_of_contract_is_not_measured(self):
 133 | +        good = self.reply()
 134 | +        for bad in ({k: x for k, x in good.items() if k != "hook"}, dict(good, hook={"scroll": 5, "alone": 5}),
 135 | +                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}), dict(good, hook={"scroll": 5, "alone": 5,
 136 | +                                                                                               "setup": 0})):
 137 | +            ok, v, r, _ = self.run_it(bad)
 138 | +            self.assertEqual((ok, v["measured"]), (False, False))
 139 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"])
 140 | +
 141 | +
 142 |  class TestWriteTakeaway(unittest.TestCase):
 143 |      SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 144 |  
 145 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips, then ONE host
takeaway line). Your role: a strict reviewer of a blind verdict's contract.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- Ruling 52 (committed at 88aa6d9c) changed the CLIPS-ALONE verdict (MEDLEY_PROMPT / medley()). The HOOK is rated on
  its own job in three parts the judge answers separately, each 1-5: "scroll" (its first 2-3 seconds stop a scroll),
  "alone" (it stands alone), "setup" (it sets up what follows). Its rating is DERIVED as the lowest part (HOOK_RULE),
  written to verdict["clips"]["hook"]. The clips after the hook keep their through-line rating; the bar is 4.
- The COHERENCE verdict that runs after the takeaway is written (COHERENCE_PROMPT / coherence()) still rated EVERY
  clip, the hook included, on "how much it advances the through-line", plus vo_point. ok = a stated through-line and
  min(all clip ratings + vo_point) >= 4.
- THE ORCHESTRATOR'S ANSWER (09:59 ET Nov 13, verbatim): "YES. Ruling 52's hook rating (the hook judged on its own job:
  stops the scroll, stands alone, sets up what follows) applies to the coherence verdict after the takeaway as well.
  One definition of the hook's job everywhere it is rated."

The change:
1. HOOK_QUESTION: the hook's three-part question, ONE text, defined before both prompts.
   - MEDLEY_PROMPT now embeds it. Verified: the formatted MEDLEY_PROMPT is BYTE-IDENTICAL to the committed one, so the
     clips-alone verdict is unchanged.
   - COHERENCE_PROMPT embeds the same text. It says the first clip ("hook") opens the video, asks the through-line
     rating "for each clip AFTER the hook", keeps vo_point, and writes the clip keys out per package.
2. coherence():
   - the contract requires exactly {"through_line", "hook" (the three parts, ints 1-5), "clips" (the labels after the
     hook), "vo_point"}; anything else is not measured, rejected, never a pass;
   - the hook's rating is derived as the lowest part and written to verdict["clips"]["hook"], as in medley();
   - the pass rule is unchanged.
   Downstream readers are unchanged: the takeaway-redo branch reads min(coh["clips"]) and vo_point; the weak-clip
   drop reads segments[1:] only.
3. tests/package/test_medley.py:
   - one hook part at 3 fails, all parts at 4 pass, and the derived rating is recorded;
   - the prompt carries HOOK_QUESTION, which is also in MEDLEY_PROMPT;
   - a clip at 3 or vo_point 3 still fails;
   - out-of-contract replies are not measured and are rejected.
- test_medley 92 OK; every other suite OK.

Check in particular:
- that the hook's job has exactly one definition, used by both verdicts;
- that the clips-alone verdict did not change;
- that the coherence verdict's clips and vo_point are judged exactly as before;
- that a malformed reply is never a pass;
- that the derived hook rating feeds the same pass rule.

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
