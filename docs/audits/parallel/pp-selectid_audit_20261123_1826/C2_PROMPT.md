# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261123_1826
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 41 s finish=stop usage in 6931 / out 6910 usd_reported=0.000760 usd~0.124 (upper-bound price)

**Answers to the four questions**

1. **Can the clean pass, or a verdict that was never measured, get a line through?**  
   No. In the clean pass `soft` is `False`, so the first `if` block that would set `soft=True` is never executed. The second guard (`if not val["ok"] and not val.get("soft")`) then triggers, appending the line to `value_lost` and preventing the package from being built. Likewise, if a verdict is never measured (`val.get("measured") is False` or `None`), the soft block is skipped and the line is lost. Thus a line cannot slip through in either of those scenarios.

2. **Do fidelity, context, length and the banned‑words checks stay HARD for a soft‑value line?**  
   Yes. The soft flag is added only to the `value` gate. The subsequent gates (`takeaway_fidelity`, `takeaway_context`, `takeaway_length`, `takeaway_banned`, etc.) are still evaluated as hard gates. The log message in the soft block explicitly states that “fidelity, length and the banned words stay HARD.” Therefore a soft‑value line is still subject to the hard‑gate checks.

3. **Is the FLAGGED row consistent with what the render reads (its text = the shipped closing line)?**  
   Yes. The inventory code adds `status: "FLAGGED"` and a `flags` list containing the exact line text (`VALUE_FLAG.format(line=value.get("text"))`). The test `TestRuling150ValueSoft` asserts that `row["text"]` equals `TM.Rig.LINE`, which is the line that the render will use. Hence the FLAGGED row is consistent with the rendered closing line.

4. **Is there any path where the never‑empty pass now seals a closing line with no value verdict at all?**  
   No. If a value verdict is not present (`val.get("measured") is not True`), the soft block is bypassed and the line is treated as a loss (`value_lost`). Therefore the never‑empty pass cannot seal a line that has no value verdict.

---

### Findings (severity tags)

| # | Finding | Severity |
|---|---------|----------|
| 1 | The code checks `val.get("measured") is True`. If `measured` is ever stored as a non‑boolean (e.g., string `"True"` or integer `1`), the soft flag will never be set. | P2 |
| 2 | The inventory logic adds `status: "FLAGGED"` only when `value.get("soft")` and `value.get("ok") is not True`. If `value.get("ok")` were `None` (unlikely but possible if the gate logic changes), the row would not be flagged. | P3 |
| 3 | There is a theoretical path where a line could pass the value gate with `ok=True` but without a value verdict (`measured` missing). The current code would treat it as a clear‑yes line, potentially violating the intent that a line must have a value verdict. | P2 |
| 4 | No other critical issues were identified. |  |

**P1_OR_WORSE:** 0 (no P0 or P1 findings)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 79 s finish=stop usage in 7449 / out 6556 usd_reported=0.016196 usd~0.121 (upper-bound price)



# Code Audit — RULING 150 (pp-selectid)

## Findings

### [P2] RULING 150 flag can indirectly hard-stop via REVIEW_FLAGS_MAX

The new `VALUE_FLAG` is added to the `takeaway_value` row's `flags` list. The description confirms the unchanged `REVIEW_FLAGS_MAX = 3` (package_pin.py:55) "counts every flag." If a package already carries 3 flags from other gates (e.g., `runtime`, `hook_onset`, `graphics`), the RULING 150 flag becomes the 4th and trips the cap, producing a `gate_problems` entry that blocks the package. The ruling's intent is that a measured-but-not-clear-yes value verdict is *soft* (the line ships, flagged for review), yet the cap converts it into a hard stop. The ruling text does not exempt this flag from the cap, so the code is technically compliant, but the interaction defeats the softness in the common never-empty-pass scenario where other soft gates (runtime, hook_onset) are also flagged.

**Suggestion:** Either (a) document in the ruling that the RULING 150 flag counts toward the cap (accepting the risk), or (b) exclude `takeaway_value` flags from the `REVIEW_FLAGS_MAX` count, or (c) raise the cap to 4 for the never-empty pass. As written, a package that would otherwise ship with a flagged closing line can be rejected solely because the flag pushed the count to 4.

---

### [P3] Inconsistent access style in the inventory condition (line 38)

```python
if value.get("soft") and value.ok is not True else {}
```

`value.get("soft")` uses dict-style access; `value.ok` uses attribute access. Both work only because the runtime object supports both (the test passes, confirming this). The inconsistency is a readability hazard: a future reader may "fix" one to match the other and break the code, or may not realise the object is not a plain `dict`. The `_build` side stores it as `dict(val, soft=True)`, which *is* a plain dict — so if `inventory` receives that same dict, `value.ok` would raise `AttributeError`. The test passing implies `inventory` receives a wrapped object, but the diff does not show the wrapping. Worth a one-line comment or a uniform `value.get("ok")`.

---

### [P3] `val["ok"]` is a hard key access (KeyError on missing key)

In the `_build` write loop, `val["ok"]` is accessed directly (not `.get("ok")`). If the value-measurement backend returns a dict without an `"ok"` key (e.g., a partial failure that still sets `measured=True`), this raises `KeyError`. Under M12 (fail closed) the build would abort, which is the correct *outcome*, but the error message would be a bare `KeyError: 'ok'` rather than a descriptive "value verdict missing required field." A `val.get("ok")` with an explicit `if val.get("ok") is None: raise` (or log + reject) would make the failure self-documenting in the build log.

---

### [P3] `rec["value_soft"]["answers"]` silently drops keys absent from `val`

```python
"answers": {k: val.get(k) for k in ("adds", "no_restate", "missed", "short")}
```

If the measured verdict omits any of these four sub-fields (e.g., the backend only returned `adds` and `no_restate`), the record stores `None` for the missing ones. This is not a correctness bug (the line still ships, the flag is still correct), but the audit trail in `rec["value_soft"]` would show `{"adds": "yes", "no_restate": "no", "missed": None, "short": None}`, which a reviewer might misread as "the verdict said 'missed' is None" rather than "the field was not reported." A small sentinel or a note in the log line would disambiguate.

---

## Answers to the four requested checks

1. **Can the clean pass or an unmeasured verdict get a line through?** No. Clean pass: `soft` is `False`, so the RULING 150 branch is unreachable; the unchanged `if not val["ok"] and not val.get("soft")` fires and the line is lost. Unmeasured: `val.get("measured") is True` is `False`, same result. Both are covered by `test_the_clean_pass_never_takes_it` and `test_no_verdict_stays_hard`.

2. **Do fidelity, context, length and banned words stay HARD?** Yes. The `soft` flag is set only on the value-verdict dict. The subsequent paid gates (fidelity + context at package.py:4420, length, banned words) are separate checks that read the line text and the source independently; none of them consult `val["soft"]`. The log line and the ruling text both confirm this.

3. **Is the FLAGGED row's text the shipped closing line?** Yes. The inventory row's `text` field is `value.get("text")` (the takeaway text stored by the value measurement), and the flag string is `VALUE_FLAG.format(line=value.get("text"))` — the same source. The test asserts `row["text"] == TM.Rig.LINE` and the flag contains the same string.

4. **Any path where the never-empty pass seals a line with no value verdict at all?** No. The soft branch requires `val.get("measured") is True`. If the value gate never ran or returned an unmeasured result, `val["ok"]` is `Fa

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 3 (qwen3.8-27b, gpt-oss-20b; gemma-4-31b-it HTTP 429, no answer). P0/P1: 0 and 0.
- qwen P2 (the value flag counts toward REVIEW_FLAGS_MAX = 3): BY DESIGN. The orchestrator's rule caps a flagged
  package at 3 flags; its 18:18 ET Nov 23 order lets the builder raise one of ITS counts or caps when that alone blocks
  a through-lined, hard-gated package, written on the state line. No code change.
- qwen P3 ("value.ok" attribute access in inventory): DISPROVED. The diff reads `value.get("soft") and
  value.get("ok") is not True` (package.py:4742's row); there is no attribute access.
- qwen P3 (val["ok"] direct access) and P3 (answers record None for an absent sub-field): pre-existing contract of
  takeaway_value (ok and measured are always set; L-l: a reply counts only whole); no change.
- gpt-oss P2 (measured stored as "True" / 1 never softens): fail-closed by intent (L-l: exact types; a non-True
  measured is not a measured verdict). P3 (ok None not flagged): DISPROVED: `is not True` flags it. P2 (an ok=True line
  with no measured verdict): pre-existing takeaway_value contract (ok only on a measured clear yes); outside this change.
All four questions answered "no / yes / yes / no" by both seats. Nothing to fix; cycle 2 cross-examines the same diff.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261123_1826/C2_STEP.diff (103 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c32b7d6..3c652a6 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -296,6 +296,9 @@ LY_FLOOR_S = 30.0                  # RULINGS 148 (1) / 149 (orchestrator 09:56 E
   6 |  LY_SHORT_SPAN_WORDS = 4            # clips too short to land 60 s: the takeaway is asked within this of its longest
   7 |  RUNTIME_SHORT = "This video runs {n} seconds, shorter than usual."   # 148 (1): the flag, NN the factory's estimate
   8 |  _FLOOR = None                      # LY_FLOOR_S while build() runs the never-empty pass (set and cleared there only)
   9 | +VALUE_FLAG = 'The closing line may mostly restate the clips: "{line}"'   # RULING 150 (standing, orchestrator 18:18 ET
  10 | +#   Nov 23): in the never-empty pass a MEASURED value verdict (ruling 91) that is not a clear yes keeps the closing line
  11 | +#   with this flag, the line verbatim; no verdict, fidelity, length and the banned words stay HARD; the clean pass as ruled
  12 |  
  13 |  
  14 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  15 | @@ -4383,7 +4386,14 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  16 |                      log(f"    value (ruling 91) {'PASS' if val['ok'] else 'LOST'}: " +
  17 |                          (f"{answers}, {val.get('words')} words" if val.get("measured") else
  18 |                           f"no verdict ({str(val.get('why'))[:120]})") + f" ({time.time() - t0:.0f} s)")
  19 | -                    if not val["ok"]:                      # "anything short of a clear yes means no line"
  20 | +                    if soft and not val["ok"] and val.get("measured") is True:     # RULING 150: the grade is SOFT
  21 | +                        val = att["value"] = dict(val, soft=True)
  22 | +                        rec["value_soft"] = {"ruling": "150 (standing from 18:18 ET Nov 23)",
  23 | +                                             "line": fields["takeaway"]["text"], "answers": {k: val.get(k) for k in (
  24 | +                                                 "adds", "no_restate", "missed", "short")}}
  25 | +                        log("    RULING 150: this closing line's measured value verdict is a flag (never-empty pass); "
  26 | +                            "fidelity, length and the banned words stay HARD")
  27 | +                    if not val["ok"] and not val.get("soft"):      # "anything short of a clear yes means no line"
  28 |                          v_lost.append({k: val.get(k) for k in ("text", "measured", "adds", "no_restate", "missed",
  29 |                                                                 "short", "why", "words", "backend")})
  30 |                          rec["value_lost"] = list(v_lost)
  31 | @@ -4735,6 +4745,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  32 |                                                                                                "missed", "short")},
  33 |                                     why=value.get("why"), words=value.get("words"), cap=value.get("cap"),
  34 |                                     rule=f"ruling 91 (medley half): all four a clear yes and at most {LY_TAKEAWAY_MAX_WORDS} "
  35 | -                                        f"words, off every writer's vendor and family")}
  36 | +                                        f"words, off every writer's vendor and family",
  37 | +                                   **({"status": "FLAGGED", "flags": [VALUE_FLAG.format(line=value.get("text"))]}
  38 | +                                      if value.get("soft") and value.get("ok") is not True else {}))}   # RULING 150
  39 |             if value is not None else {}),
  40 |      }
  41 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  42 | index 6400783..9cdc53c 100644
  43 | --- a/pipeline/package_pin.py
  44 | +++ b/pipeline/package_pin.py
  45 | @@ -47,6 +47,8 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
  46 |                          "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
  47 |                          #   HARD)
  48 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
  49 | +                        "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
  50 | +                        #   91), a measured one; fidelity, length and the banned words stay HARD
  51 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
  52 |  #   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
  53 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
  54 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
  55 | index e7d50a8..a614ec0 100644
  56 | --- a/tests/package/test_ruling_137.py
  57 | +++ b/tests/package/test_ruling_137.py
  58 | @@ -648,6 +648,44 @@ class TestRuling144TheOneException(unittest.TestCase):
  59 |              PP.WINDOW_H = saved
  60 |  
  61 |  
  62 | +class TestRuling150ValueSoft(unittest.TestCase):
  63 | +    """RULING 150 (standing; orchestrator 18:18 ET Nov 23: 'the value grade of our closing line' is SOFT): in the
  64 | +    never-empty pass a closing line whose MEASURED value verdict (ruling 91) is not a clear yes keeps its place, flagged
  65 | +    'The closing line may mostly restate the clips: "<line>"', and goes on to fidelity. An unmeasured verdict, and the
  66 | +    clean pass: unchanged (HARD)."""
  67 | +    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
  68 | +              "covers_speaker": False}
  69 | +
  70 | +    def run_rig(self, measured=True, never_empty=True, ticker=True):
  71 | +        import test_medley as TM
  72 | +        from test_moments import pm
  73 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
  74 | +        lost = {"adds": "yes", "no_restate": "no", "why": "it restates the clips"} if measured else {"measured": False}
  75 | +        kw = {"visuals": {"x": {"burned_in": [dict(self.TICKER)]}}} if ticker else {}
  76 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
  77 | +                   values=[dict(lost) for _ in range(6)], follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]}, **kw)
  78 | +        if never_empty:
  79 | +            r.build_kw = {"never_empty": True}
  80 | +        return r, r.run()["package"]
  81 | +
  82 | +    def test_a_measured_loss_seals_flagged(self):
  83 | +        import test_medley as TM
  84 | +        _, pk = self.run_rig()
  85 | +        self.assertIsNotNone(pk)
  86 | +        row = pk["gates"]["takeaway_value"]
  87 | +        self.assertEqual((row["status"], row["flags"], row["text"]), (
  88 | +            "FLAGGED", [f'The closing line may mostly restate the clips: "{TM.Rig.LINE}"'], TM.Rig.LINE))
  89 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
  90 | +
  91 | +    def test_the_clean_pass_never_takes_it(self):
  92 | +        _, pk = self.run_rig(never_empty=False, ticker=False)      # reaches the value gate: HARD
  93 | +        self.assertIsNone(pk)
  94 | +
  95 | +    def test_no_verdict_stays_hard(self):
  96 | +        _, pk = self.run_rig(measured=False)
  97 | +        self.assertIsNone(pk)
  98 | +
  99 | +
 100 |  class TestRuling148RuntimeFloor(unittest.TestCase):
 101 |      """RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18; standing from the 12:00 build): in the never-empty pass a
 102 |      medley's clips may total LY_FLOOR_S (30 s) or more; under medley_content_range()'s lo (36.7 s) the package seals with
 103 | 
```

---

pp-selectid: RULING 150, STANDING (orchestrator 18:18 ET Nov 23: "SOFT, flagged: ... the value grade of our closing
line"; HARD stays: "a line of ours that states a fact the clips do not carry"). It replaces the Nov 18 by-hand version
(one named line on one exception pin, audit 20261118_1044) with the standing rule; the driver option is gone.
THE CHANGE:
- package._build's write loop (package.py:4389): ONLY in the never-empty pass (`soft`, _build's own parameter,
  package.py:3321, False in the clean pass), ONLY for a MEASURED value verdict (val["measured"] is True) that is not
  ok: val becomes dict(val, soft=True), the line-up record gets value_soft {ruling, line, answers}, one log line. The
  UNCHANGED next guard (package.py:4396) `if not val["ok"] and not val.get("soft")` then skips the value-loss branch
  (the rewrite, the no-voice shape, the refusal), so the loop goes on to the paid gates (fidelity + context,
  package.py:4420), HARD as before.
- inventory (package.py:4742): the takeaway_value row gets status FLAGGED and flags [VALUE_FLAG with the line
  verbatim] when value.soft and value.ok is not True.
- package_pin.SOFT_GATES += "takeaway_value" (the unchanged gate_problems, package_pin.py:444, accepts a FLAGGED row
  only for a gate in SOFT_GATES; the unchanged cap REVIEW_FLAGS_MAX = 3, package_pin.py:55, counts every flag).
Files: pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py.
TESTS (TestRuling150ValueSoft, the real build() on the stubbed rig): never-empty pass + a measured loss: seals, the row
FLAGGED with the exact sentence and the line as its text, gate_problems none; the clean pass reaching the value gate:
no package; an unmeasured verdict: no package. Mutations 6 of 6 killed (the clean pass too; unmeasured too; not a soft
gate; another sentence; the row never flagged; the soft line still lost); the control passes.
PLEASE CHECK: (1) can the clean pass, or a verdict that was never measured, get a line through? (2) do fidelity,
context, length and the banned words stay HARD for a soft-value line? (3) is the FLAGGED row consistent with what the
render reads (its text = the shipped closing line)? (4) any path where the never-empty pass now seals a closing line
with no value verdict at all?


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
