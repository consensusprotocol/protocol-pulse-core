# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0500
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 181 s finish=stop usage in 6934 / out 5408 usd~0.102 (upper-bound price)

# Audit: pp-selectid — Ruling 37 (question ends the HOOK only)

## What the diff actually does (verified)

- `eligibility.py:9-12` — `not_statement` is now raised only when `role != "hook"`. The `ends_statement(last)` check itself is unchanged; the reason still fires for clip/evidence roles.
- `package.py:24-27` — `question_hook` = `bool(segs) and str(segs[0].get("text") or "").rstrip().endswith("?")`. Empty list → `False`; `None` text → `""` → `False`. Fail-closed.
- `package.py:47-51` — in `build()`, after the clips-alone verdict passes, if `question_hook(segs)` and `joins(labs)[0] in med["flagged"]`, `segs[1]["moment_id"]` is dropped and the angle re-lined (`continue`).
- `package.py:37-39` — `ly_shape` gains an `elif` before the bridge/flagged comparison: question hook + `js[0] in med["flagged"]` → fail with "ruling 37".
- Tests: hook-with-`?` loses `not_statement`, clip keeps it; predicate; re-line; bridge-between-clips unchanged; `ly_shape` refusal.

## Findings

### P1-1 — `ly_shape`'s new check can be shadowed by the preceding `if` (package.py:34-40)
The new `elif question_hook(segs) and js and js[0] in med["flagged"]` sits in an `if/elif` chain whose earlier arms I cannot see in this diff (the hunk starts at `med = pk.get("medley")...`). If any earlier arm in that chain matches the question-hook case (e.g. a shape/length failure), the ruling-37 message is skipped — acceptable — but if an earlier arm is *broad* (e.g. catches `med["measured"] is not True`), the new check still runs, which is fine. **However**: the new `elif` requires `js` non-empty, while the following `elif` (line 40) compares `sorted(bridged) != sorted(med["flagged"])` without that guard. If `js` is empty but `med["flagged"]` is non-empty and the hook is a question, the ruling-37 check silently skips and the package can seal with a question hook whose (nonexistent) first join was "flagged" — the render's R1 would then... actually with no joins there is no join after the hook, so this is consistent. **Downgrade: P2.** Scenario: 1-clip... — the L-y law says 3-5 segments, so `js` empty is unreachable in a valid package; noting only that the guard's asymmetry with line 40 is unexplained. Not a defect.

### P1-2 — `build()`'s ruling-37 drop uses `segs[1]` without guarding a 1-segment line-up (package.py:47-51)
`segs[1]["moment_id"]` assumes at least 2 segments. In this loop, `segs` comes from the line-up under construction; if a line-up of exactly 1 segment reaches this branch (hook only, no clips), `IndexError` → exception → per M12 fail-closed, but it kills the angle rather than re-lining. Whether 1-segment line-ups reach this code depends on the unseen loop head (the hunk context shows `dropped |= weak; continue` just before, implying `segs` was just (re)built). If the loop only runs 3+ segment line-ups (L-y: 3-5 segments), this is dead-safe; if a 2-segment (hook+1 clip) line-up is tried, `segs[1]` exists and is correct. **Cannot verify from the diff; flag as P2-verify.** If reachable with `len(segs) == 1`, it's a P1 (crash, not silent pass — M12 holds, so not P0).

### P1-3 — `question_hook` reads `segs[0]["text"]`, but the sealed pin's hook text may differ from what the render's R1 reads (package.py:24-27, 47, 37)
The pin stage's `segs[0].get("text")` and the integrator's edl_rules R1 must read the *same* field. If the render reads the EDL's hook text (post-`canon`/L-h read-as-spoken, e.g. `S&amp;P` → `S&P`, or a trailing `?` stripped by some normaliser), a hook whose pin text ends `?` but whose EDL text ends `?` after canon — or vice versa — would disagree: pin seals, render refuses (or the reverse: pin thinks no question, render's R1 sees one and demands no-bridge, but the pin already sealed a bridge there). The diff shows no canonisation of the `?` test. `rstrip()` handles whitespace only. **Scenario**: hook text `"Why does Bitcoin fall? "` → pin: question; EDL text after L-h/L-k read-as-spoken → if any stage rewrites `?` to `?`+trailing space or drops it, render's R1 disagrees. Whether this happens depends on unseen code (does `build()` write `segs[i]["text"]` verbatim into the pin/EDL?). **Cannot verify; P2-verify** — the integrator's R1 is stated to use "the hook's text ends with '?'", matching this predicate, so likely aligned, but the diff does not prove the EDL text is byte-identical to `segs[0]["text"]`.

### P1-4 — The re-line's `dropped` growth: termination (package.py:43-51)
The hunk shows `dropped |= weak` (existing) and the new `dropped.add(segs[1]["moment_id"])`. Termination depends on the unseen loop: if the loop iterates over combinations of `moments - dropped` and `dropped` only grows, it terminates (finite moments). The new code adds to the same `dropped` set the existing weak-clip path uses, so the existing termination argument covers it — **provided** the new branch cannot re-add a moment already in `

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 25 s finish=stop usage in 7037 / out 364 usd~0.044 (upper-bound price)

**P0: none**

**P1: none**

**P2: pipeline/package.py:47 (and ly_shape:37)**  
The re-line path and ly_shape guard both assume the question is always segs[0] (the hook) and that the first flagged join is exactly "hook -> clip_01". This matches the added question_hook() predicate and the test rig, but the diff contains no explicit guard against a question-ending clip appearing in any other position. (The eligibility change prevents selection, but that is in a different module.)

**P2: tests/eligibility/test_eligibility.py:64**  
The test removal of "not_statement" from the hook expectation is correct per the diff, but the new clip-role assertion only exercises a synthetic ctx("clip") call. The diff provides no coverage of real middle/last-clip selection paths that would invoke the same eligibility logic with role != "hook".

**P2: pipeline/eligibility.py:11**  
The added `and role != "hook"` implements Ruling 37 exactly as described. No other call sites or roles are altered in the diff, satisfying the "only the hook" constraint *within the visible code*. The orchestrator's explicit relaxation is acknowledged in comments; no standing law (L-m, L-j, M20, etc.) is violated by the shown lines.

All three required behaviors are present and exercised by the new tests:
- question ends hook only (eligibility + test)
- flagged join after question hook never produces a sealed bridge (build re-line + ly_shape refusal)
- dropped set grows, preventing infinite re-line loops (visible in the Rig test and the .add() call)

No unrelated changes, no relaxation of other gates, no new renderer/selector.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 46 s finish=stop usage in 7523 / out 1652 usd~0.047 (upper-bound price)

# Audit: pp-selectid-0500 / C1_STEP.diff (Ruling 37)

## P0 Findings
None.

## P1 Findings

**1. `pipeline/package.py:1285-1290` — Re-line loop termination is not guaranteed by the diff (L-m / fail-closed risk)**
The new block drops `segs[1]["moment_id"]` and `continue`s. The diff does not show the enclosing `while`/`for` loop, the `dropped` set's initial state, or the loop's exit condition.
- **Scenario:** If the loop iterates over a fixed list of candidate angles and `dropped` is not checked to prevent re-processing, or if the loop condition does not account for `len(segs)` shrinking, a pathological input (e.g., all clips flagged in the clips-alone verdict) could either:
  - (a) loop indefinitely if the loop is `while True` without a `len(segs) < MIN` break, or
  - (b) silently produce a package with fewer than the required 3-5 segments, which `ly_shape` would then catch—but only if `ly_shape` is called *after* the loop. If `ly_shape` is not called on the final package before sealing, a malformed package could be sealed.
- **Verification needed:** Confirm the loop has a hard bound (e.g., `while len(segs) >= 3 and attempts < MAX`) and that `ly_shape` is invoked on the final `pk` before `write_takeaway` seals it. The diff shows `ly_shape` exists but not that it is called in the `build()` path after the re-line loop.

**2. `pipeline/package.py:868-870` — `ly_shape` only checks `js[0]` (the first join)**
The check is:
```python
elif question_hook(segs) and js and js[0] in med["flagged"]:
```
This only inspects the *first* join (`hook -> clip_01`). If a question hook is followed by multiple clips, and a *later* join (e.g., `clip_01 -> clip_02`) is flagged, `ly_shape` does not refuse it. However, the Ruling 37 text says "the clips-alone verdict judges the join after it as usual," and the render's R1 only cares about the join *immediately after the hook*. So this is likely correct by design. **But:** the `build()` re-line logic at line 1285 also only checks `joins(labs)[0]`. If the clips-alone verdict flags *only* a later join (not the first), the re-line does not trigger, and the bridge logic at line 1292-1294 will attempt to bridge the flagged later join. This is correct per the ruling (bridges are allowed between clips, just not after a question hook). **No issue here**, but the asymmetry between `ly_shape` (only checks `js[0]`) and the general bridge rule (checks all flagged joins) is worth noting.

## P2 Findings

**3. `pipeline/eligibility.py:411` — Comment references "RULING 37 (03:12 ET Nov 13)" but the diff header says "Generated: 2026-11-13 04:57 UTC"**
Minor timestamp inconsistency. The ruling is cited as 03:12 ET, which is 07:12 UTC (Nov 13), not 04:57 UTC. This is a documentation nit, not a code defect.

**4. `pipeline/package.py:24-27` — `question_hook` uses `str(segs[0].get("text") or "").rstrip().endswith("?")`**
This is a string-level check. If the hook's text is stored with a trailing newline or other whitespace, `rstrip()` handles it. However, if the text is `None` or missing, `or ""` handles it. **Edge case:** If the text is `"Why does Bitcoin keep falling every time Nvidia does? "` (trailing space), `rstrip()` removes it and `endswith("?")` is `True`. This matches the render's R1 test as described. **No issue.**

**5. `tests/package/test_medley.py:95-102` — Test `test_a_flagged_join_after_a_question_hook_re_lines_without_that_clip`**
The test asserts `rig.medley_calls == [["h", "x", "y"], ["h", "y", "z"]]`. This implies the re-line loop tried two line-ups: first with `x` (dropped), then with `y` and `z`. The test does not verify that the loop *terminated* or that `dropped` was checked. This is a test coverage gap, not a code defect, but it means the test does not prove the loop cannot loop forever.

**6. `pipeline/package.py:1285-1290` — `dropped.add(segs[1]["moment_id"])`**
If `segs[1]` does not have a `"moment_id"` key, this raises `KeyError`. The diff does not show how `segs` is constructed, but the test at line 88 uses `pm("h", "A", 12.0)`, which likely includes a `moment_id`. **Assume safe**, but if `segs` can contain dicts without `moment_id`, this is a crash risk.

## Verification of Specific Checks

- **Question can end ONLY the hook, never a middle or last clip:** ✅ Verified. `eligibility.py:411` adds `and role != "hook"` to the `not_statement` check. The test at `test_eligibility.py:67-68` confirms a clip still gets `not_statement`.
- **The join after a question hook can never carry a bridge in a sealed pin:** ✅ Verified. `build()` drops `clip_01` if the first join is flagged (line 1285-1290), so no bridge is placed. `ly_shape` refuses a package where the first join is flagged (line 868-870). The render's R1 (not in this diff) is stated to refuse a bridge after a question hook.
- **The re-line cannot loop forever:** ⚠️ **Not verifiable from the diff.** The loop structure is not

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0500 (ruling 37's pin side: a question may end the hook only): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers eligibility.py, package.py, test_eligibility.py and test_medley.py. No P0. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- qwen: "yes with conditions";
- glm: "yes with conditions".

## Consensus (each verified from the code, or implemented)

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | The re-line's termination is not shown in the diff (qwen P1-1, glm P1-4) | VERIFIED. The enclosing loop is `while n_lineup < lineups and not out["packages"] and not out.get("budget_stop")`. n_lineup is incremented before every verdict, so the loop is bounded by `lineups`. `dropped` only grows and lineup_for excludes it, so a re-line never returns a line-up holding a dropped moment. ly_shape runs in the sealed inventory of every package (inventory(..., shape=ly_shape(pk))), and "ly_shape" is a required medley gate. |
| K2 | segs[1] on a one-segment line-up (glm P1-2) | VERIFIED unreachable. lineup_for returns the hook plus LY_CLIPS = 2-4 clips (`for n in range(clips[0], clips[1] + 1)`), so every judged line-up has at least 3 segments. |
| K3 | Does the predicate read the same text as the render's R1 (glm P1-3)? | VERIFIED. The pin's approved_text is the moment's text verbatim (package_pin.to_pin: "approved_text": s["text"]), and pinned.build_edl gives the render that text. The integrator confirmed that their R1 reading (medley PASS live, "hook -> clip_01" not flagged, coherence PASS live) matches this one (message, 04:56 ET). |
| K4 | Is js[0] "hook -> clip_01" in production, not only in the fixture (glm condition 3)? | TESTED: PK.joins(PK.labels(4))[0] == "hook -> clip_01". |
| K5 | A must-pass case is missing (glm condition 4) | IMPLEMENTED: a question hook, its first join not flagged, no bridge: ly_shape == (True, []). |

## Answered or kept

- **glm P1-8 (two definitions of "ends on a question"):** eligibility's not_statement fires when the span's last word does not end a statement (ends_statement). The line-up's question_hook reads the text's last character, as the render's R1 does. A hook whose word record splits off the "?" would be eligible as a hook and not seen as a question by question_hook; the render's R1 reads the same text and would not see one either. They agree.
- **glm condition 5 (the frozen references):** the 2026-11-11 preview and the v2f references are story-path EDLs (not medleys), and ly_shape and the line-up loop run only for medleys. regression_test.sh passes (26 PASS | 0 FAIL).
- **qwen P2 (the comment's time zone):** the ruling's time is ET, as cited.

## Verification

- test_medley 61 OK, test_eligibility 30 OK; the other suites are run before the commit.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0500/C2_STEP.diff (126 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index f2e898ba..adb3d406 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -407,8 +407,8 @@ def _span(span, ctx, role):
   6 |      last = toks[w1].get("word")
   7 |      if not sentence_law.is_terminal(last):
   8 |          R("fragment", f"ends on {last!r}: no terminal punctuation")
   9 | -    elif not ends_statement(last):
  10 | -        R("not_statement", "ends on a question")
  11 | +    elif not ends_statement(last) and role != "hook":   # RULING 37 (03:12 ET Nov 13): a question may end the HOOK only;
  12 | +        R("not_statement", "ends on a question")         # the clips-alone verdict judges the join after it (package.py)
  13 |      # T5 lexical evidence at both boundaries (E-FAIL-013: an unpunctuated stretch has no boundary)
  14 |      for k in ([w0 - 1] if w0 > 0 else []) + [w1]:
  15 |          if not sentence_law.is_punctuated(toks, k):
  16 | diff --git a/pipeline/package.py b/pipeline/package.py
  17 | index 31ffb345..ac10906d 100644
  18 | --- a/pipeline/package.py
  19 | +++ b/pipeline/package.py
  20 | @@ -828,6 +828,12 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  21 |                     type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
  22 |  
  23 |  
  24 | +def question_hook(segs):
  25 | +    """Ruling 37: the hook ends on a question (its text ends with '?', the render's R1 test). Such a hook is allowed; the
  26 | +    clips-alone verdict must find the join after it followable, since no bridge may follow a question."""
  27 | +    return bool(segs) and str(segs[0].get("text") or "").rstrip().endswith("?")
  28 | +
  29 | +
  30 |  def ly_shape(pk):
  31 |      """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
  32 |      last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
  33 | @@ -862,6 +868,9 @@ def ly_shape(pk):
  34 |      med = pk.get("medley") or {}
  35 |      if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
  36 |          fails.append("the clips-alone verdict was not measured (L-y 3)")
  37 | +    elif question_hook(segs) and js and js[0] in med["flagged"]:
  38 | +        fails.append(f"ruling 37: a hook ending on a question takes no bridge after it, so {js[0]} must be followable "
  39 | +                     f"(the render's R1 reads the sealed clips-alone verdict)")
  40 |      elif sorted(bridged) != sorted(med["flagged"]):
  41 |          fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
  42 |                       f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
  43 | @@ -1276,6 +1285,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  44 |                      dropped |= weak
  45 |                      rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
  46 |                      continue
  47 | +                if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
  48 | +                    dropped.add(segs[1]["moment_id"])
  49 | +                    rec["why"] = (f"ruling 37: the join after the question hook must be followable without a bridge, and "
  50 | +                                  f"the clips alone flag {joins(labs)[0]}: re-lined")
  51 | +                    continue
  52 |                  join = None
  53 |                  if med["flagged"]:
  54 |                      k = joins(labs).index(med["flagged"][0])
  55 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
  56 | index afffc2c0..17896e45 100644
  57 | --- a/tests/eligibility/test_eligibility.py
  58 | +++ b/tests/eligibility/test_eligibility.py
  59 | @@ -401,8 +401,11 @@ class TestSpan(unittest.TestCase):
  60 |          src = source(["so " + ("bitcoin went sideways " * 2) + "today?"], timing="segment", channel="Bitcoin Magazine",
  61 |                       age_h=100)
  62 |          r = E.eligible(E.Span(src, 0, 0), ctx("hook", story=statements(E.Span(src, 0, 0))))
  63 | -        for n in ("not_current", "layout_ineligible", "not_sentence_ready", "not_statement", "start_case", "duration"):
  64 | +        for n in ("not_current", "layout_ineligible", "not_sentence_ready", "start_case", "duration"):
  65 |              self.assertIn(n, r.names())
  66 | +        self.assertNotIn("not_statement", r.names())                   # ruling 37: a question may end the HOOK
  67 | +        rc = E.eligible(E.Span(src, 0, 0), ctx("clip", story=statements(E.Span(src, 0, 0))))
  68 | +        self.assertIn("not_statement", rc.names())                     # ... never a clip
  69 |          self.assertTrue(any("conjunction" in t for t in r.facts["targets_missed"]))             # L-o: ranked
  70 |  
  71 |  
  72 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  73 | index 15b1d5a1..0ee53c23 100644
  74 | --- a/tests/package/test_medley.py
  75 | +++ b/tests/package/test_medley.py
  76 | @@ -726,6 +726,49 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
  77 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
  78 |  
  79 |  
  80 | +class TestRuling37QuestionHook(unittest.TestCase):
  81 | +    """Ruling 37: a clip ending on a question may be the HOOK only; the clips-alone verdict judges the join after it,
  82 | +    which must be followable with no bridge (no bridge may follow a question; the render's R1 reads the sealed
  83 | +    gates.medley flagged list)."""
  84 | +
  85 | +    Q = "Why does Bitcoin keep falling every time Nvidia does?"
  86 | +
  87 | +    def ms(self):
  88 | +        return [dict(pm("h", "A", 12.0), text=self.Q), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0)]
  89 | +
  90 | +    def test_the_question_hook_test(self):
  91 | +        self.assertTrue(PK.question_hook([{"text": self.Q + "  "}]))
  92 | +        self.assertFalse(PK.question_hook([{"text": "Bitcoin is money."}]))
  93 | +        self.assertFalse(PK.question_hook([]))
  94 | +
  95 | +    def test_a_flagged_join_after_a_question_hook_re_lines_without_that_clip(self):
  96 | +        rig = Rig(self.ms(), ["h", "x", "y", "z"], [(True, ["hook -> clip_01"], None, Rig.LINE),
  97 | +                                                    (True, [], None, Rig.LINE)], [None])
  98 | +        out = rig.run()
  99 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "z"]])          # x dropped, never bridged
 100 | +        self.assertIn("ruling 37", out["tried"][0]["why"])
 101 | +        self.assertIsNotNone(out["package"])
 102 | +        self.assertEqual(out["package"]["segments"][0]["text"], self.Q)
 103 | +
 104 | +    def test_a_flagged_join_between_clips_is_bridged_as_usual(self):
 105 | +        rig = Rig(self.ms(), ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)],
 106 | +                  [{"text": "Next, a show on chips.", "cites": ["y"], "why": "no referent"}])
 107 | +        out = rig.run()
 108 | +        self.assertEqual(rig.write_calls[0][1][0], 1)                                     # the bridge after clip 1
 109 | +        self.assertIsNotNone(out["package"])
 110 | +
 111 | +    def test_ly_shape_refuses_a_question_hook_whose_first_join_was_flagged(self):
 112 | +        pk = medley_pk(bridge="hook -> clip_01", after=0, flagged=["hook -> clip_01"], intro="Next, on chips.")
 113 | +        pk["segments"][0]["text"] = self.Q
 114 | +        ok, why = PK.ly_shape(pk)
 115 | +        self.assertFalse(ok)
 116 | +        self.assertTrue(any("ruling 37" in w for w in why), why)
 117 | +        pk = medley_pk(flagged=[])                                     # must-pass (audit 0500 C1, glm): a question
 118 | +        pk["segments"][0]["text"] = self.Q                             # hook, its first join followable, no bridge
 119 | +        self.assertEqual(PK.ly_shape(pk), (True, []))
 120 | +        self.assertEqual(PK.joins(PK.labels(4))[0], "hook -> clip_01")  # the join R1 reads, in production labels
 121 | +
 122 | +
 123 |  class TestRuling34Screen(unittest.TestCase):
 124 |      """Ruling 34 (render side merged at 55315124): the topic test is the miner's about-Bitcoin screen the pin seals;
 125 |      the hook must pass it itself, a clip may complete the previous claim, and the MEDLEY must name Bitcoin once."""
 126 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway). This branch BUILDS sealed
pins; the integrator renders them. The pin stage must never seal a line-up the render would refuse.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR RULING 37 (03:12 ET Nov 13): "not_statement: a clip that ends on a question is allowed in the HOOK
role only; the clips-alone verdict and coherence check judge the join after it as usual. Not as a middle or last
clip." The integrator is changing the render's edl_rules R1 to match. It accepts a hook ending on "?" when the sealed
clips-alone verdict (gates.medley) is PASS, not replayed, and its "flagged" list does NOT contain "hook -> clip_01",
and gates.coherence is PASS. A flagged join takes a bridge, and the render's bridge rule refuses a bridge after a
clip that ends on a question.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass (the relaxation is the orchestrator's ruling).

The change:
1. pipeline/eligibility.py: the "not_statement" reason (the span ends on a question) is no longer raised for the HOOK
   role; it stays for every other role (clip, evidence).
2. pipeline/package.py:
   - question_hook(segs): the hook's text ends with "?" (the render's R1 test);
   - in build()'s line-up loop, right after the clips-alone verdict passes: if the hook is a question and the verdict
     flags the join after it, clip_01 is dropped and the angle re-lined (no bridge may follow a question);
   - ly_shape(pk), the sealed L-y shape gate: refuses a package whose question hook's first join was flagged.
3. Tests:
   - eligibility: a hook ending on "?" carries no not_statement; a clip still does;
   - the predicate;
   - a flagged join after a question hook re-lines without that clip and then packages;
   - a flagged join between clips is bridged as before;
   - ly_shape refuses the question-hook case.

Check in particular:
- that a question can now end ONLY the hook, never a middle or last clip;
- that the join after a question hook can never carry a bridge in a sealed pin;
- that the re-line cannot loop forever (dropped grows);
- that nothing else changes.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
