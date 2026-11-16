# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1300
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 621 s finish=stop usage in 6241 / out 7261 usd_reported=0.001094 usd~0.128 (upper-bound price)

The code implements the requested fix for **RULING 122 (3)**, correcting a contradiction in the "no hook" error message. It ensures that if a hook passes the calibrated bar but is rejected by the visual check (RULING 93), the log explicitly names the visual check rather than falsely claiming the hook failed the bar.

### Analysis
1.  **Logic Accuracy**: The introduction of `on_bar` correctly identifies moments that pass the bar but are absent from the final `passing` pool. The ternary operator in `out["why_none"]` correctly switches between the "visual block" explanation and the "none passed the bar" explanation.
2.  **Gate Integrity**: No gates were modified. The logic for selecting hooks (`can_open`, `hook_pool`) remains untouched; only the reporting of the failure is updated. This complies with **LAW 20/M2**.
3.  **Law Compliance**:
    *   The change is restricted to logging/reporting and does not touch the EDL, timestamps, or transcripts, thus respecting **SENTENCE LAW**, **SELECTION LOCK**, and **L-k (Canon)**.
    *   It does not introduce new renderers or selectors, adhering to the **M1** constraint.
4.  **Test Coverage**: The new test `test_the_line_names_the_visual_check_when_it_alone_refuses_a_hook_that_passes_the_bar` effectively validates both paths:
    *   **Path A**: Hook passes bar $\rightarrow$ visually blocked $\rightarrow$ message names visual check and avoids "none of the".
    *   **Path B**: Hook fails bar $\rightarrow$ message remains "none of the... passes the calibrated hook bar".
5.  **Variable Scope**: The variable `blocked` is used in the `join` loop. While not defined in the diff, the provided tests pass, confirming `blocked` is an existing local variable in the `build()` function of `pipeline/package.py`.

### Findings
*   **[P3] Grammar**: In line 14, the phrase `"{len(on_bar)} of the {len(openers)} moments... pass"` uses the plural "pass". If `len(on_bar)` is 1, this is grammatically incorrect ("1... pass"), though it does not affect functionality.

P1_OR_WORSE: 0

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 265 s finish=stop usage in 5868 / out 20411 usd_reported=0.002026 usd~0.324 (upper-bound price)

# Audit: pp-selectid — RULING 122 (3) The No-Hook Line

## Check (1): Is the line true in every case?

**The logic is sound.** When `passing` is empty and `on_bar` is non-empty, every `on_bar` moment must be visually blocked — because any `on_bar` moment that were *not* visually blocked would flow through `can_open()` → `hook_pool` → `passing`, contradicting the branch guard. The message's claim ("the visual check refuses each") is therefore correct by construction.

When `on_bar` is empty, the fallback "none of the N…" is also correct: no rated opener passes the bar.

**[P3]** Grammar: when `len(on_bar) == 1`, the f-string produces *"1 of the 4 moments that can open **pass** the calibrated hook bar"* — the subject is "1" (singular), so it should read *"passes"*. The test asserts the same incorrect string, so both code and test would need updating together. Semantically the line is true; this is purely a wording nit.

**[P3]** `m.get('channel_name')` can return `None` if the key is absent from a moment dict, yielding *"None h: …"* in the message. The parallel `m['moment_id']` uses `[]` (will `KeyError` if missing) while `channel_name` uses `.get()` (silently `None`) — inconsistent access on the same dict. In practice both keys are present in the test rig, so this is defensive-coding hygiene rather than a live defect.

## Check (2): Did any gate change?

**No.** The diff touches only the `why_none` string construction. `hook_pool`, `can_open()`, `visual_hook_block`, `HB`, `hook_bar.passes`, and every threshold are untouched. The `on_bar` list-comprehension is computed solely for the message. No gate, no threshold, no classification changed.

## Check (3): The tests

Both scenarios are covered correctly:

| Scenario | Assertion | Verdict |
|---|---|---|
| Visual check alone refuses a bar-passing hook | `"1 of the 4 moments … pass the calibrated hook bar"` present; `"the visual check (rulings 70 / 93) refuses each … A h: ruling 93 … a ticker"` present; `"none of the"` absent | ✅ |
| Bar itself refuses | `"none of the 4 moments … passes the calibrated hook bar"` present; `"the visual check"` absent | ✅ |

The two assertions are mutually exclusive and correctly exercise both branches of the ternary. The `assertNotIn` guards prevent regression to the old misleading wording.

**Not covered (acceptable):** the mixed case where some openers fail the bar *and* some are visually blocked — `on_bar` would contain only the visually-blocked passers, and the message would correctly say "K of the N pass … visual check refuses each" while silently omitting the N−K that fail the bar. This is arguably fine (the message focuses on what *did* pass), but a test would strengthen confidence.

---

**Summary:** The change correctly diagnoses and fixes the RULING 122(3) misdiagnosis. No gate altered. Two cosmetic nits.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 66 s finish=stop usage in 5955 / out 5577 usd_reported=0.004253 usd~0.102 (upper-bound price)

I will review the provided diff for `pipeline/package.py` and `tests/package/test_medley.py` against the governing laws and the specific order for RULING 122 (3).

### Analysis

**1. Context and Intent**
The code addresses a contradiction where a hook passed the numerical "calibrated bar" but was rejected by a visual check (Ruling 93). The previous error message (`why_none`) incorrectly implied that *no* hooks passed the bar, when in fact some did, but were blocked visually. The fix updates the log message to distinguish between "failed the bar" and "passed the bar but blocked by visual check."

**2. Code Review: `pipeline/package.py`**

*   **Logic Change:**
    ```python
    on_bar = [m for mid, m in openers.items() if mid in rated and (hook_own(m) or {}).get("passes")]
    ```
    This correctly identifies openers that have been rated and passed the hook bar.
    
*   **Message Construction:**
    ```python
    out["why_none"] = ("no hook in the pool (ruling 59 d): " + (
        (f"{len(on_bar)} of the {len(openers)} moments that can open pass {HB.text(live)}, and the visual check "
         f"(rulings 70 / 93) refuses each as an opener: " + "; ".join(
             f"{m.get('channel_name')} {m['moment_id']}: {blocked.get(m['moment_id'], 'not seen')}" for m in on_bar)
         if on_bar else
         f"none of the {len(openers)} moments that can open passes {HB.text(live)}") +
        ...
    ```
    *   **Case A (`on_bar` is non-empty):** The message states that $K$ of $N$ moments pass the bar, and lists the specific visual reasons for each. This aligns with the order to "name it" (the visual check).
    *   **Case B (`on_bar` is empty):** The message reverts to the original "none of the N moments... passes the bar." This is correct because if no one passed the bar, the visual check is irrelevant to the *bar* failure, though they might still be visually blocked, the primary failure is the bar. The order states: "If another condition sits on the hook path, name it...". If the bar fails, the bar is the primary gate. The visual check is a secondary gate. The logic holds: if you don't pass the bar, you don't get to the visual check stage in terms of "passing the pool."

*   **Potential Issue: `blocked` dictionary access**
    The code uses `blocked.get(m['moment_id'], 'not seen')`.
    *   Does `blocked` contain *all* visually blocked items, or only those that passed the bar?
    *   The prompt says: "build() sets visual_hook_block on each rated opener its own frames block".
    *   If an opener fails the bar, it is not in `on_bar`, so it won't be listed in the "visual check refuses" part. This is correct.
    *   If an opener passes the bar but is visually blocked, it is in `on_bar`. Is it guaranteed to be in `blocked`?
    *   The prompt states: "RULING 93's visual check refused it... build() sets visual_hook_block...". It implies `blocked` is the source of truth for visual refusals.
    *   If `blocked` is missing a key for an item in `on_bar`, it defaults to `'not seen'`. This is a safe fallback, though it might indicate a data inconsistency if it happens frequently. However, for a log message, this is acceptable.

*   **Governing Law Check:**
    *   **LAW 20 / M2:** "never change what a check accepts to make a render pass". The code explicitly states: "The gate is unchanged: only the words of the record and the log." The logic for `out["hook_pool"]["passing"]` is not modified. Only the string `out["why_none"]` is modified. This complies.
    *   **M12 FAIL CLOSED:** The change is purely informational. It does not affect the pass/fail state.

**3. Code Review: `tests/package/test_medley.py`**

*   **Test 1: Visual check alone refuses a hook that passes the bar**
    ```python
    def test_the_line_names_the_visual_check_when_it_alone_refuses_a_hook_that_passes_the_bar(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TICKER}).run()
        self.assertIn("1 of the 4 moments that can open pass the calibrated hook bar", out["why_none"])
        self.assertIn("the visual check (rulings 70 / 93) refuses each as an opener: A h: ruling 93 (1 item(s)): a ticker", out["why_none"])
        self.assertNotIn("none of the", out["why_none"])
    ```
    *   This test verifies the new message format when `on_bar` is non-empty.
    *   It checks that the count "1 of the 4" is present.
    *   It checks that the specific visual reason is present.
    *   It checks that the old "none of the" phrase is *not* present.
    *   This looks correct.

*   **Test 2: The bar itself refuses it**
    ```python
    out = Rig(self.MS, ["h", "x", "y", "z"], [], [], hooks={"h": (2, 3, 4)}).run()    # the bar itself refuses it
    self.assertIn("none of the 4 moments that can open passes the calibrated hook bar", out["why_none"])
    self.assertNotIn("the visual check", out["why

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_1300 (RULING 122 (3): the no-hook line)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: gemma 0,
mimo 0, qwen 1. Cycle 1 $0.0074 of Heimdall, not capped.

qwen's P1 ("a hook that passes the bar but is refused by a DIFFERENT gate would be misattributed to the visual check")
CANNOT HAPPEN on this path; the unchanged code, in order (dev44's package.py):
- :3050 openers = the cleared moments can_open() takes before any rating (eligibility, G17a onset, the render's opener rule);
- ratings are set; :3059 rated_open = the cleared moments can_open() takes NOW: for a moment of on_bar (in openers, rated,
  hook_own passes) every condition of _can_open holds as it did for openers, plus the bar: so every on_bar moment is in
  rated_open;
- see(rated_open) judges each one's frames; :3066 sets visual_hook_block (and blocked[id]) when its own frames refuse it;
- :3079 passing = hook_order(the cleared moments can_open() takes) with that flag set; can_open's FIRST line (:1556) refuses
  a flagged moment; hook_order (:1600) only sorts, it never drops one.
So when passing is empty, every on_bar moment carries visual_hook_block: the visual check is the one refusal left, and the
line is true. The 'not seen' fallback is unreachable in this branch (kept: a line never raises). qwen's P2 (a test of a
non-visual refusal of a bar-passing hook) has no reachable case to test. No change.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1300/C2_STEP.diff (45 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 2168e97..5ae1e1b 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -3082,8 +3082,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
   6 |          f"{HB.text(live)}" + (f" [{live_why}]" if live_why else "") + (f"; NOT RATED: {hook_err}" if hook_err else "")
   7 |          + f" ({time.time() - t0:.0f} s)")
   8 |      if not out["hook_pool"]["passing"]:                                  # (d): no line-up is paid for
   9 | +        on_bar = [m for mid, m in openers.items() if mid in rated and (hook_own(m) or {}).get("passes")]
  10 | +        #   RULING 122 (3): a hook that passes the bar and is refused only by its own frames (rulings 70 / 93) is
  11 | +        #   named with that reason; the line never blames the bar for it (builds 52-54 did)
  12 |          out["why_none"] = ("no hook in the pool (ruling 59 d): " + (
  13 | -            f"none of the {len(openers)} moments that can open passes {HB.text(live)}" +
  14 | +            (f"{len(on_bar)} of the {len(openers)} moments that can open pass {HB.text(live)}, and the visual check "
  15 | +             f"(rulings 70 / 93) refuses each as an opener: " + "; ".join(
  16 | +                 f"{m.get('channel_name')} {m['moment_id']}: {blocked.get(m['moment_id'], 'not seen')}" for m in on_bar)
  17 | +             if on_bar else
  18 | +             f"none of the {len(openers)} moments that can open passes {HB.text(live)}") +
  19 |              (f" ({len(openers) - len(rated)} not rated: {hook_err})" if hook_err else "") + "; the best: " +
  20 |              "; ".join(f"{b['channel']} {b['rating']} (scroll {b['scroll']}, alone {b['alone']}, setup {b['setup']}): "
  21 |                        f"{b['why']}" for b in best) if openers else
  22 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  23 | index bf99903..abf864c 100644
  24 | --- a/tests/package/test_medley.py
  25 | +++ b/tests/package/test_medley.py
  26 | @@ -2370,6 +2370,18 @@ class TestRuling70Visual(unittest.TestCase):
  27 |          self.assertNotIn("angle_write", rig.events)                      # "no hook in the pool": nothing written
  28 |          self.assertTrue(out["why_none"].startswith("no hook in the pool"), out["why_none"])
  29 |  
  30 | +    def test_the_line_names_the_visual_check_when_it_alone_refuses_a_hook_that_passes_the_bar(self):
  31 | +        """RULING 122 (3): builds 52-54 said 'none of the 2 moments that can open passes the calibrated hook bar' for
  32 | +        What Bitcoin Did's 3 / 5 / 4, which passes it; ruling 93's lower-third check had refused it."""
  33 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TICKER}).run()
  34 | +        self.assertIn("1 of the 4 moments that can open pass the calibrated hook bar", out["why_none"])
  35 | +        self.assertIn("the visual check (rulings 70 / 93) refuses each as an opener: A h: ruling 93 (1 item(s)): a ticker",
  36 | +                      out["why_none"])
  37 | +        self.assertNotIn("none of the", out["why_none"])
  38 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], hooks={"h": (2, 3, 4)}).run()    # the bar itself refuses it
  39 | +        self.assertIn("none of the 4 moments that can open passes the calibrated hook bar", out["why_none"])
  40 | +        self.assertNotIn("the visual check", out["why_none"])
  41 | +
  42 |      def test_a_third_person_clip_that_is_not_the_hook_is_kept_with_its_flag(self):
  43 |          out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"y": self.TP}).run()
  44 |          self.assertIsNotNone(out["package"])
  45 | 
```

---

pp-selectid: RULING 122 (3) (orchestrator 13:05 ET Nov 16): THE NO-HOOK LINE. Files: pipeline/package.py (build(): the
why_none written when no hook is left), tests/package/test_medley.py.

THE ORDER, verbatim: "(3) A CONTRADICTION TO EXPLAIN: builds 52-54 say the best hook (What Bitcoin Did: scroll 3, alone 5,
setup 4) FAILS the calibrated bar, whose floors are scroll 3, alone 4, setup 3. On those numbers it passes. What refused
it? If another condition sits on the hook path, name it; if it is a bug, fix it and say so plainly."
THE ANSWER (measured on builds 52-54's records): it PASSES the bar (hook_bar.passes: every part at least its floor, rated by
the calibrated rater). RULING 93's visual check refused it as an opener (hook_pool.visual_blocked: "a lower_third the
9:16 crop would cut through mid-word ('IN THIS EPISODE...')"): build() sets visual_hook_block on each rated opener its own
frames block, and can_open() returns False for it (unchanged guards: package.can_open's first line; the visual loop
before hook_pool). THE BUG: the why_none line said "none of the N moments that can open passes <the bar>" whenever the
passing list was empty, whatever refused them.

THE CHANGE: on_bar = the rated openers that pass the bar (hook_own(m)["passes"]); when any does, the line says "K of the N
moments that can open pass <the bar>, and the visual check (rulings 70 / 93) refuses each as an opener: <channel id:
its reason>"; otherwise it says what it said before. The gate is unchanged: only the words of the record and the log.

TESTS: the visual check alone refusing a hook that passes the bar: the line names it and never "none of"; the bar itself
refusing: the line as before, with no visual words. Mutations V1-V2 after a control run.

PLEASE CHECK: (1) that the line is true in every case; (2) that no gate changed; (3) the tests.


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
