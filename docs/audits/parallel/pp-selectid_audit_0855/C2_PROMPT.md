# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0855
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 68 s finish=stop usage in 6211 / out 1886 usd~0.047 (upper-bound price)

# Audit: pp-selectid-0855 — placement() markings vs lineup_for

## Verification of the three markings against the stated rules

The rules given: hook needs hook eligibility AND passed hook onset (G17a); a clip under SHORT_CLIP_S may play only LAST among the clips after the hook (`order[:-1]` over clips after the hook; `clips[:-1]` in lineup_ok with `clips = segs[1:]`). So a short clip may be the hook, and a short clip may be last; it may not sit mid-line-up.

New placement() (package.py:30-38):

- `opens = hook.eligibility.ok AND hook_onset.pass is True` — matches the hook rule, including the `is True` strictness (a truthy non-True, e.g. `"yes"`, would count as not-opens; the diff's test at test_medley.py:57-58 uses `{"pass": True}` so the strict comparison is exercised for the True case only — I cannot verify from the diff whether any caller stores a truthy non-boolean, but the old code used the identical expression, so behavior is unchanged there).
- Short + opens → `" | under 8 s: only the hook or the LAST clip"` — correct: hook allowed (hook is exempt from the short rule since the rule applies to `order[:-1]` of the clips after the hook), LAST allowed, mid not. Matches.
- Short + not opens → `" | under 8 s: only the LAST clip"` — correct: cannot be hook (no onset/eligibility), cannot be mid (short), only LAST remains. Matches.
- ≥8 s + not opens → `" | cannot open (never the hook)"` — correct: a long clip has no placement restriction other than the hook rule. Matches.
- ≥8 s + opens → `""` — correct.

Edge: short + not-opens previously produced two markings ("may only play LAST | cannot open"); now one. Since "only the LAST clip" logically implies "cannot open", no information is lost. The prompt sentence (package.py:12-14) now names all three markings, so the proposer sees the same constraint set. Consistent.

Boundary semantics: "under 8 s" is `< SHORT_CLIP_S` in both placement() (line 32) and the stated lineup rule; the prompt says "under 8 s" via the f-string `{SHORT_CLIP_S:.0f}` — if SHORT_CLIP_S were ever not exactly 8.0, the rounding `:.0f` could print e.g. "under 8 s" while the code tests `< 7.6`. Pre-existing pattern (old code had the same `:.0f`), not introduced here. P2 at most; not verifiable from the diff whether SHORT_CLIP_S is exactly 8.

## "Nothing else changed"

The diff touches only the PLACEMENT LIMITS prompt sentence (package.py:9-15), placement() (package.py:22-38), and the test. Within the prompt hunk, the trailing `Give as many good angles as the clips allow (aim for {k}); for` is preserved across the rewrap (lines 11/14-15) — the stray `; for` continuation is unchanged, so no accidental prompt-text loss. The `swap_lineup` context lines are context only. No other hunks.

## Test hunk review (test_medley.py:46-62)

- Line 51: `id=s | C | 6.9 s | under 8 s: only the LAST clip` — s is 6.9 s, no_hook={"s","y"} so not-opens → short+not-opens marking. Correct, and it also verifies the old "may only play LAST (under 8 s) | cannot open" double marking is gone.
- Line 52: y, 13.8 s, no_hook → "cannot open (never the hook)". Correct.
- Line 53: z, 9.5 s, no restriction → `| "`. Correct (9.5 ≥ 8, opens).
- Line 55: prompt-text assertion updated to the new wrapped wording; I cannot verify the exact wrap position in the rendered prompt from the diff alone (the assertion spans a line break: `"only the hook or the LAST\nclip"`), so this depends on the prompt's actual wrapping at ~the same column as the old assertion. If the wrap column differs, the test fails, not the code — the suite reportedly passes (90 OK), which is the only evidence the wrap matches. Flag as trust-the-suite, not independently verifiable.
- Lines 57-62: the 08:46 regression. `short_opener` = 7.3 s, hook_onset pass → placement() == " | under 8 s: only the hook or the LAST clip" (asserted, line 58). Then a 4-clip lineup b(7.3, hook) + c(13.9) + w(9.5) + a(6.9, not-opens) = 37.6 s, fed to the real `PK.lineup_for` with `need_onset=True`, asserting the order survives. This exercises: short clip as hook (the defect), short clip last (a, 6.9 s, in `clips[:-1]`... wait — a is LAST, so it is in `clips[-1]`, i.e. exempt; the mid positions are c and w, both ≥8 s). Good: the mid-positions are all long, so the lineup is formable, which is the 08:46 shape. One nuance: the test never asserts a short clip FAILS mid-line-up (i.e., that lineup_for rejects e.g. b,c,a,w). That negative case is the other half of the rule; it is presumably covered by the pre-existing lineup_for tests, not by this diff. P2: the corrective test proves the marking matches a formable lineup but not that the marking's "never in between" claim is enforced — acceptable, since the enforcement (lineup_for) was not changed.

Arithmetic: 7.3+13.9+9.5+6.9 = 37.6 ✓ (comment says 37.6 s). The 08:46 ledger figures 7.26+13.94+9.46+6.93 = 37.59 ✓, and the test's 7.3/13.9

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 16 s finish=stop usage in 6323 / out 134 usd~0.035 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none** (The three limit strings now emitted by placement() exactly match the three cases described in the new docstring and in the updated PLACEMENT LIMITS sentence. The added test at test_medley.py:57-62 exercises the precise 08:46 shape that previously failed (short hook + short last clip) and confirms both placement() and lineup_for produce the expected order. No other logic, prompt text, or call sites are altered in the diff. The updated code is consistent with the Ruling 54 description supplied in the audit package.)

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 35 s finish=stop usage in 6649 / out 1192 usd~0.038 (upper-bound price)

# Audit: pp-selectid-0855 (C1_STEP.diff)

## Verification of the Core Logic

I verified the new `placement()` logic against the stated `lineup_for`/`lineup_ok` rules. The mapping is **correct**:

1.  **Short Clip + Can Open** (`duration < 8s`, `hook.ok` & `hook_onset.pass`):
    *   **New Code:** Returns `" | under 8 s: only the hook or the LAST clip"`.
    *   **Rule Check:** `lineup_for` allows a short clip to be the hook (index 0) or the last clip (index -1). It forbids it in the middle (`order[:-1]` check). The prompt text accurately reflects this.
2.  **Short Clip + Cannot Open** (`duration < 8s`, `!hook.ok` or `!hook_onset.pass`):
    *   **New Code:** Returns `" | under 8 s: only the LAST clip"`.
    *   **Rule Check:** Since it cannot be the hook, the only valid position for a short clip is the last one. The prompt text accurately reflects this.
3.  **Long Clip + Cannot Open** (`duration >= 8s`, `!hook.ok` or `!hook_onset.pass`):
    *   **New Code:** Returns `" | cannot open (never the hook)"`.
    *   **Rule Check:** Long clips have no "last only" restriction, but they still cannot be the hook if ineligible. The prompt text accurately reflects this.
4.  **Long Clip + Can Open** (`duration >= 8s`, `hook.ok` & `hook_onset.pass`):
    *   **New Code:** Returns `""` (empty).
    *   **Rule Check:** No restrictions. Correct.

The prompt sentence in `package.py` (lines 12-14 of the diff) correctly enumerates these three states and their allowed positions.

## Findings

### P1: Missing Test Case for "Short Clip + Can Open" in Prompt Context
**File:** `tests/package/test_medley.py` (lines 51-58 of diff)
**Scenario:** The test verifies that `placement()` returns the correct string for a short clip that *can* open (`short_opener`). However, the test at line 51 (`self.assertIn('id=s | C | 6.9 s | under 8 s: only the LAST clip | "', p)`) only checks the case where the short clip *cannot* open (because `no_hook={"s", "y"}` in the `Rig` setup).
While the unit test for `placement()` itself (line 58) covers the "can open" case, the **prompt generation** test does not verify that the prompt correctly renders the "only the hook or the LAST clip" string for a short clip that *is* eligible to open.
**Risk:** Low. The logic is simple string interpolation. However, a regression where the prompt fails to include the "hook" option for eligible short clips would not be caught by the current prompt assertion.
**Recommendation:** Add a test case where a short clip is eligible to open, and assert that the prompt contains `"under 8 s: only the hook or the LAST clip"`.

### P2: Ambiguity in "LAST clip" vs "LAST id of an angle's list"
**File:** `pipeline/package.py` (lines 12-14 of diff)
**Scenario:** The prompt says: `a clip marked "only the hook or the LAST clip" is the first or the LAST id of an angle's list`.
The term "LAST clip" in the marking is slightly ambiguous. Does it mean "the last clip in the *entire* video" or "the last clip in the *angle's* list"?
The prompt clarifies this by saying "is the first or the LAST id of an angle's list". This is correct because `lineup_for` operates on the angle's list. However, the marking itself (`"only the hook or the LAST clip"`) could be misinterpreted by the LLM as "the last clip in the final video output" if the LLM is not careful.
**Risk:** Very Low. The prompt explicitly defines the meaning of the marking. The LLM is instructed to follow the prompt's definition.
**Recommendation:** No change needed, but ensure the LLM prompt is robust to this ambiguity. The current prompt is clear enough.

### P2: No Change to `lineup_for` or `lineup_ok`
**File:** `pipeline/package.py`
**Scenario:** The diff only changes `placement()` and the prompt. It does not change `lineup_for` or `lineup_ok`.
**Verification:** This is correct. The defect was that `placement()` did not match `lineup_for`'s rules. The fix is to make `placement()` match `lineup_for`, not to change `lineup_for`.
**Risk:** None.

## SHIP: yes with conditions

**Condition:** Add a test case to `tests/package/test_medley.py` that verifies the prompt contains `"under 8 s: only the hook or the LAST clip"` for a short clip that is eligible to open. This will ensure that the prompt correctly communicates the hook exception to the LLM.

The core logic is correct, and the fix addresses the measured defect. The missing test case is a minor gap in test coverage, not a functional bug.

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0855 (ruling 54's placement limits corrected): cycle 1 consensus

- grok: no P0 / P1, "SHIP: yes"; glm: "SHIP: yes"; qwen: "yes with conditions" (one P1).
- IMPLEMENTED (qwen P1): the prompt-level test now shows a short clip that CAN open: its line in the angle prompt reads
  "under 8 s: only the hook or the LAST clip". The test already showed the short clip that cannot open, the long clip
  that cannot open, and the unlimited clip.
- Verification: test_medley 90 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0855/C2_STEP.diff (73 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index b849a45..c1d391f 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -507,9 +507,10 @@ it is today's.
   6 |  With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
   7 |  clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
   8 |  introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
   9 | -channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "may only play LAST" is the
  10 | -LAST id of an angle's list or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as
  11 | -the clips allow (aim for {k}); for
  12 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. PLACEMENT LIMITS: a clip marked "only the hook or the LAST
  13 | +clip" is the first or the LAST id of an angle's list, never in between; a clip marked "only the LAST clip" is the LAST
  14 | +id or is not in it; a clip marked "cannot open" is never the hook. Give as many good angles as the clips allow (aim for
  15 | +{k}); for
  16 |  each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
  17 |  survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
  18 |  "hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
  19 | @@ -913,14 +914,15 @@ def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
  20 |  
  21 |  
  22 |  def placement(m):
  23 | -    """RULING 54: a clip's placement limits as the angle proposer is told them, by the line-up's own rules: under
  24 | -    SHORT_CLIP_S it may only play LAST; without hook eligibility and a passed hook onset (G17a) it cannot open."""
  25 | -    lim = []
  26 | +    """RULING 54: a clip's placement limits as the angle proposer is told them, exactly lineup_for's rules. Without hook
  27 | +    eligibility and a passed hook onset (G17a) it cannot open. Under SHORT_CLIP_S it may not play mid-line-up: the
  28 | +    short-clip rule binds the clips AFTER the hook only, so a short clip that can open may be the hook or the LAST clip,
  29 | +    and one that cannot open only the LAST (the 08:46 build: a 7.26 s opener was the only formable hook)."""
  30 | +    opens = bool((m.get("eligibility") or {}).get("hook", {}).get("ok")) and \
  31 | +        (m.get("hook_onset") or {}).get("pass") is True
  32 |      if m["duration_s"] < SHORT_CLIP_S:
  33 | -        lim.append(f"may only play LAST (under {SHORT_CLIP_S:.0f} s)")
  34 | -    if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True):
  35 | -        lim.append("cannot open (never the hook)")
  36 | -    return "".join(f" | {x}" for x in lim)
  37 | +        return f" | under {SHORT_CLIP_S:.0f} s: " + ("only the hook or the LAST clip" if opens else "only the LAST clip")
  38 | +    return "" if opens else " | cannot open (never the hook)"
  39 |  
  40 |  
  41 |  def pool_fill(angle, pool, dropped=frozenset()):
  42 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  43 | index e2a34c8..814be17 100644
  44 | --- a/tests/package/test_medley.py
  45 | +++ b/tests/package/test_medley.py
  46 | @@ -1164,15 +1164,23 @@ class TestProposal1PoolFill(unittest.TestCase):
  47 |          self.assertEqual(([m["moment_id"] for m in segs], added), (["h", "x", "f"], ["f"]))
  48 |  
  49 |      def test_ruling_54_the_proposer_is_told_each_clips_placement_limits(self):
  50 | -        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
  51 | +        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5),
  52 | +              pm("o", "F", 7.3)]
  53 |          rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
  54 |          rig.run()
  55 |          p = next(p for r, p in rig.prompts if r == "angle_write")
  56 | -        self.assertIn('id=s | C | 6.9 s | may only play LAST (under 8 s) | cannot open (never the hook) | "', p)
  57 | +        self.assertIn('id=o | F | 7.3 s | under 8 s: only the hook or the LAST clip | "', p)   # audit 0855 C1, qwen
  58 | +        self.assertIn('id=s | C | 6.9 s | under 8 s: only the LAST clip | "', p)            # short, cannot open
  59 |          self.assertIn('id=y | D | 13.8 s | cannot open (never the hook) | "', p)
  60 |          self.assertIn('id=z | E | 9.5 s | "', p)                       # no limit, nothing added
  61 | -        self.assertIn('a clip marked "may only play LAST" is the\nLAST id of an angle', p)
  62 | +        self.assertIn('marked "only the hook or the LAST\nclip" is the first or the LAST id', p)
  63 |          self.assertIn('a clip marked "cannot open" is never the hook', p)
  64 | +        short_opener = dict(pm("b", "F", 7.3), hook_onset={"pass": True})   # the 08:46 build's only formable hook
  65 | +        self.assertEqual(PK.placement(short_opener), " | under 8 s: only the hook or the LAST clip")
  66 | +        both = [short_opener] + [dict(m, hook_onset={"pass": True}) for m in (pm("c", "G", 13.9), pm("w", "H", 9.5))] + \
  67 | +            [dict(pm("a", "I", 6.9), hook_onset={"pass": False})]     # 7.3 + 13.9 + 9.5 + 6.9 = 37.6 s
  68 | +        segs = PK.lineup_for(angle(["b", "c", "w", "a"], "b"), {m["moment_id"]: m for m in both}, need_onset=True)
  69 | +        self.assertEqual([m["moment_id"] for m in segs], ["b", "c", "w", "a"])   # lineup_for agrees: a short hook
  70 |  
  71 |      def test_the_build_records_the_pool_fill_and_judges_the_line_up(self):
  72 |          ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
  73 | 
```

---

You are auditing a small corrective diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips).
Your role: a strict reviewer.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- Ruling 54 (committed an hour ago at ebf6ff32) tells the angle proposer each clip's placement limits, so it proposes
  formable angles. lineup_for's rules:
  - the hook needs hook eligibility and a passed hook onset (G17a);
  - a clip under SHORT_CLIP_S (8 s) may play only LAST AMONG THE CLIPS AFTER THE HOOK. In code:
    `[m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]` over the clips after the hook, and
    lineup_ok's `clips[:-1]` with `clips = segs[1:]`.
  So a short clip MAY be the hook.
- THE DEFECT (measured at 08:46 ET, ledger_20261113_134638): the committed placement() marked every short clip "may
  only play LAST". The only formable line-up of that build opened on a 7.26 s clip (Bitcoin Mechanic): 7.26 + 13.94 +
  9.46 + 6.93 = 37.59 s, the short 6.93 s clip last. Told that the opener "may only play LAST", the writer returned no
  angle, which check_angles refuses ("no readable angles"). The limits did not match lineup_for's rules, which ruling 54
  requires.

The change (pipeline/package.py, tests/package/test_medley.py):
1. placement(m) states exactly lineup_for's rules:
   - under 8 s and able to open: "under 8 s: only the hook or the LAST clip";
   - under 8 s and not able to open: "under 8 s: only the LAST clip";
   - 8 s or more and not able to open: "cannot open (never the hook)";
   - otherwise nothing.
2. The angle prompt's PLACEMENT LIMITS sentence names the three markings and what each allows.
3. tests:
   - the limits for each case;
   - the 08:46 shape: lineup_for itself accepts the 7.3 s hook with the short clip last, and placement() says
     "only the hook or the LAST clip" for it.
- test_medley 90 OK; every other suite OK.

Check: that the three markings are exactly the rules lineup_for and lineup_ok apply (in particular the hook exception
of the short-clip rule), that nothing else changed, and the prompt sentence.

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
