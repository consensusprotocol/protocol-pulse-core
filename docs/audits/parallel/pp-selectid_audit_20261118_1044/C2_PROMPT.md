# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_1044
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 268 s finish=stop usage in 8873 / out 4532 usd_reported=0.000837 usd~0.095 (upper-bound price)

The code implements **RULING 150 (1)**, creating a narrow, logged, and manually-triggered exception for the "takeaway value" verdict (Ruling 91) during the medley build process.

### Analysis

1.  **Logic Accuracy**:
    *   The condition in `pipeline/package.py` (line 21) correctly restricts the "softening" of the gate to:
        *   The "never-empty pass" (`soft` is True).
        *   A verdict that is explicitly `not ok`.
        *   A verdict that was actually `measured` (preventing unmeasured/failed calls from passing).
        *   A line that exactly matches the `VALUE_SOFT_LINE` provided via the CLI.
    *   The subsequent check `if not val["ok"] and not val.get("soft"):` (line 29) correctly allows the loop to proceed only if the `soft` flag was set by the exception logic.
    *   The `inventory` function (lines 39-40) correctly marks the resulting row as `FLAGGED` with the required `VALUE_FLAG` text, ensuring the render and integrator are aware of the exception.

2.  **Safety and Constraints**:
    *   **Hard Gates**: The implementation ensures that other critical gates (fidelity, length, banned words) remain `HARD`. Since the `soft=True` flag is only applied to the `val` object of the value verdict, other gates in the loop will still trigger the `if not val["ok"]` block and fail the build if they are not `ok`.
    *   **CLI Guard**: `tests/package/proof_ledger.py` (line 76) enforces that `--value-soft-line` cannot be used without `--pbx-exception`, preventing accidental use of this override in standard production runs.
    *   **Integration**: Adding `"takeaway_value"` to `package_pin.SOFT_GATES` allows the integrator to accept the `FLAGGED` status for this specific gate without blocking the final pin.

3.  **Law Compliance**:
    *   **Law 20 / M2**: While Law 20 forbids changing thresholds to make a render pass, this is implemented as a "Ruling" (an explicit orchestrator override) for a specific "pin" (a single, named line). This is the established pattern for manual editorial exceptions in this pipeline.
    *   **L-a through L-l**: This change affects the medley assembly (editorial/packaging) and does not touch the audio/video cutting, ASR, or transcription laws.

4.  **Test Coverage**:
    *   `TestRuling150ValueByHand` covers the critical paths:
        *   The named line passes and is flagged.
        *   The clean pass (non-soft) ignores the exception.
        *   Other lines or unmeasured verdicts remain `HARD` failures.

### Findings

No defects found. The implementation is precise, follows the "fail-closed" philosophy for all other cases, and provides the necessary audit trail in the build record.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 171 s finish=stop usage in 8460 / out 6726 usd_reported=0.006288 usd~0.126 (upper-bound price)



# Code Audit — pp-selectid / RULING 150 (1) BY HAND

## Scope Reviewed
`pipeline/package.py`, `pipeline/package_pin.py`, `tests/package/proof_ledger.py`, `tests/package/test_ruling_137.py` (the C1_STEP.diff, 138 lines).

---

## Findings

### [P3] Module-level mutable pin (`VALUE_SOFT_LINE`) is process-global

`package.VALUE_SOFT_LINE` is a bare module attribute mutated by the driver (`PK.VALUE_SOFT_LINE = a.value_soft_line`). If a future refactor ever runs two builds in one process (e.g., a batch driver), the second build would inherit the first build's pin. Today each build is a separate `proof_ledger.py` invocation, so this is safe. Worth a one-line comment at the declaration site stating "process-local; set once by the driver, never by library code" so a future reader doesn't treat it as a configurable knob.

### [P3] No test for the "pin set but verdict passes" path

`TestRuling150ValueByHand` covers: named line + LOST → FLAGGED; clean pass → no package; wrong line / no line / unmeasured → no package. The one untested branch is: `VALUE_SOFT_LINE` is set, the never-empty pass is active, but the value verdict is **ok** (all four "yes"). In that case `not val["ok"]` is False, the soft override is skipped, and the row should carry **no** `status`/`flags` keys (the `**({} if … else {})` adds nothing). The code is correct by inspection, but a one-line test (`values=[{"adds":"yes","no_restate":"yes","missed":"no","short":"no"} …]` with the pin set, assert no `FLAGGED` in the row) would close the matrix and guard against a future refactor that inverts the condition.

### [P3] Exact-string identity check bypasses `canon.py` (L-k)

`fields["takeaway"]["text"] == VALUE_SOFT_LINE` is a raw `==`. L-k mandates `canon.py` for "every text comparison in the pipeline." This is an **identity** check ("is this the exact line the operator typed?"), not a semantic/speech comparison, so `canon` would be wrong here (it would normalise `$40M` → `40 million dollars` and let a different line match). The code is correct; a brief inline comment (`# identity, not canon: the operator must name the exact string`) would pre-empt a future "L-k compliance" sweep from "fixing" it.

### [P3] `VALUE_FLAG` embeds the line in double-quotes without escaping

`VALUE_FLAG = 'The closing line may mostly restate the clips: "{line}"'` — if the closing line itself contains a `"` character, the flag string becomes ambiguous to a human reader. Not a functional bug (the flag is display-only, never parsed), but a `json.dumps(line)` or `repr(line)` would be more robust.

### [P3] `rec["value_by_hand"]["answers"]` copies only four keys

The record stores `adds`, `no_restate`, `missed`, `short` but not `why`, `words`, or `backend`. The log line and the `v_lost` path (for non-soft failures) do include `why`. For a "BY HAND" audit trail, including `why` in the record would make the build log self-contained without cross-referencing the log stream.

---

## Answers to the Three Requested Checks

**(1) Can any line other than the named one, or the clean pass, or an unmeasured verdict get through?**

No. The guard is a five-clause conjunction:

```python
soft                          # never-empty pass only
and not val["ok"]             # verdict must have failed
and val.get("measured") is True  # must be a measured (not INCONCLUSIVE) verdict
and VALUE_SOFT_LINE is not None  # pin must be set
and fields["takeaway"]["text"] == VALUE_SOFT_LINE  # exact string identity
```

- **Different line:** last clause is `False` → no override → `v_lost` append → no package. ✓ (tested: `test_any_other_line_or_no_verdict_stays_hard`)
- **Clean pass:** `soft` is `False` → no override → unchanged. ✓ (tested: `test_the_clean_pass_never_takes_it`)
- **Unmeasured verdict:** `val.get("measured") is True` is `False` → no override → unchanged. ✓ (tested: `run_rig(…, measured=False)`)

**(2) Does fidelity / context / length / banned words stay HARD for the named line?**

Yes. The soft override only mutates the **value** verdict dict (`dict(val, soft=True)`). The subsequent paid gates (fidelity via COMMENTARY/NEEDS_SOURCE, context, length ≤ `LY_TAKEAWAY_MAX_WORDS`, banned words) are independent checks that run unconditionally after the value block. If any of them fails, the build still refuses. The code comment and the log line both state this explicitly. The `SOFT_GATES` addition in `package_pin.py` names only `"takeaway_value"`, not fidelity/context/length/banned-words. ✓

**(3) The row the render reads.**

In `inventory()`, when `value.get("soft")` is `True` and `value.get("ok") is not True`, the row gains:

```python
"status": "FLAGGED",
"flags": ['The closing line may mostly restate the clips: "<line>"']
```

The row's `text` field is `value.get("text")` (the judged line, which equals `VALUE_SOFT_LINE` by the guard). Because `"takeaway_value"` is in `S

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_1044, ruling 150 (1) by hand: the named closing line's value verdict as a flag)

SEATS ANSWERED: 2 of 3 with a verdict. qwen3.8-27b and gemma-4-31b-it: P0/P1 none (both traced VALUE_SOFT_LINE's
exact-line, never-empty-pass and measured conditions). gpt-oss-20b gave no verdict (see its file's header).

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_1044/C2_STEP.diff (138 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c32b7d6..3b025fc 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -296,6 +296,10 @@ LY_FLOOR_S = 30.0                  # RULINGS 148 (1) / 149 (orchestrator 09:56 E
   6 |  LY_SHORT_SPAN_WORDS = 4            # clips too short to land 60 s: the takeaway is asked within this of its longest
   7 |  RUNTIME_SHORT = "This video runs {n} seconds, shorter than usual."   # 148 (1): the flag, NN the factory's estimate
   8 |  _FLOOR = None                      # LY_FLOOR_S while build() runs the never-empty pass (set and cleared there only)
   9 | +VALUE_SOFT_LINE = None             # RULING 150 (1) (orchestrator 10:40 ET Nov 18) BY HAND, the one exception pin: the
  10 | +                                   # exact closing line (the driver's --value-soft-line) whose MEASURED value verdict
  11 | +                                   # (ruling 91) the never-empty pass takes as a flag; every other line as ruled
  12 | +VALUE_FLAG = 'The closing line may mostly restate the clips: "{line}"'   # RULING 150: the flag, the line verbatim
  13 |  
  14 |  
  15 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  16 | @@ -4383,7 +4387,15 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  17 |                      log(f"    value (ruling 91) {'PASS' if val['ok'] else 'LOST'}: " +
  18 |                          (f"{answers}, {val.get('words')} words" if val.get("measured") else
  19 |                           f"no verdict ({str(val.get('why'))[:120]})") + f" ({time.time() - t0:.0f} s)")
  20 | -                    if not val["ok"]:                      # "anything short of a clear yes means no line"
  21 | +                    if (soft and not val["ok"] and val.get("measured") is True and VALUE_SOFT_LINE is not None
  22 | +                            and fields["takeaway"]["text"] == VALUE_SOFT_LINE):          # RULING 150 (1) BY HAND
  23 | +                        val = att["value"] = dict(val, soft=True)
  24 | +                        rec["value_by_hand"] = {"ruling": "150 (1), applied by hand to the exception pin",
  25 | +                                                "line": VALUE_SOFT_LINE, "answers": {k: val.get(k) for k in (
  26 | +                                                    "adds", "no_restate", "missed", "short")}}
  27 | +                        log("    RULING 150 (1) BY HAND: this closing line's value verdict is a flag; fidelity, length "
  28 | +                            "and the banned words stay HARD")
  29 | +                    if not val["ok"] and not val.get("soft"):      # "anything short of a clear yes means no line"
  30 |                          v_lost.append({k: val.get(k) for k in ("text", "measured", "adds", "no_restate", "missed",
  31 |                                                                 "short", "why", "words", "backend")})
  32 |                          rec["value_lost"] = list(v_lost)
  33 | @@ -4735,6 +4747,8 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  34 |                                                                                                "missed", "short")},
  35 |                                     why=value.get("why"), words=value.get("words"), cap=value.get("cap"),
  36 |                                     rule=f"ruling 91 (medley half): all four a clear yes and at most {LY_TAKEAWAY_MAX_WORDS} "
  37 | -                                        f"words, off every writer's vendor and family")}
  38 | +                                        f"words, off every writer's vendor and family",
  39 | +                                   **({"status": "FLAGGED", "flags": [VALUE_FLAG.format(line=value.get("text"))]}
  40 | +                                      if value.get("soft") and value.get("ok") is not True else {}))}   # RULING 150
  41 |             if value is not None else {}),
  42 |      }
  43 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  44 | index 6400783..9cdc53c 100644
  45 | --- a/pipeline/package_pin.py
  46 | +++ b/pipeline/package_pin.py
  47 | @@ -47,6 +47,8 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
  48 |                          "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
  49 |                          #   HARD)
  50 |                          "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
  51 | +                        "takeaway_value",                  # RULING 150: the closing line's value verdict (ruling
  52 | +                        #   91), a measured one; fidelity, length and the banned words stay HARD
  53 |                          "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
  54 |  #   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
  55 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
  56 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  57 | index 551e068..0cd6787 100644
  58 | --- a/tests/package/proof_ledger.py
  59 | +++ b/tests/package/proof_ledger.py
  60 | @@ -444,6 +444,10 @@ def main(argv=None):
  61 |                      "build takes only those moments of the pool, every gate as before (one line-up at a time)")
  62 |      ap.add_argument("--stop-usd", type=float, default=None, help="ORDER 17:50 ET Nov 16: this build's outside-dollar "
  63 |                      f"limit (no build starts at it; the router stops outside calls at it), in (0, {STOP_CEILING_USD}]")
  64 | +    ap.add_argument("--value-soft-line", metavar="LINE", default=None,
  65 | +                    help="RULING 150 (1) BY HAND (orchestrator 10:40 ET Nov 18), the one exception pin only (needs "
  66 | +                         "--pbx-exception): this exact closing line's measured value verdict is a flag in the "
  67 | +                         "never-empty pass, logged in the record")
  68 |      ap.add_argument("--pbx-exception", metavar="TEXT", default=None,
  69 |                      help="RULING 144 (PBX 07:05 ET Nov 18): this ONE build's 12 h window is waived, named and logged "
  70 |                           "(TEXT starts 'PBX exception'): --hours may reach PBX_EXCEPTION_MAX_H, every 12 h check of "
  71 | @@ -462,6 +466,10 @@ def main(argv=None):
  72 |          print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {cap:g}]", file=sys.stderr)
  73 |          return 2
  74 |      base_h = package_pin.WINDOW_H                        # 12: the rule (rulings 76 + 77) the exception widens
  75 | +    if a.value_soft_line is not None:                    # RULING 150 (1) BY HAND: the one exception pin only
  76 | +        if not a.pbx_exception or not a.value_soft_line.strip():
  77 | +            raise SystemExit("--value-soft-line needs --pbx-exception and the exact closing line")
  78 | +        PK.VALUE_SOFT_LINE = a.value_soft_line
  79 |      if a.pbx_exception:                                  # RULING 144: this process only; every later build is 12 h
  80 |          package_pin.WINDOW_H = float(a.hours)            # (package.expired, window_problems and the registry read it)
  81 |      try:                                                 # read before anything is written (glm C2 N-4)
  82 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
  83 | index e7d50a8..1ad887d 100644
  84 | --- a/tests/package/test_ruling_137.py
  85 | +++ b/tests/package/test_ruling_137.py
  86 | @@ -648,6 +648,51 @@ class TestRuling144TheOneException(unittest.TestCase):
  87 |              PP.WINDOW_H = saved
  88 |  
  89 |  
  90 | +class TestRuling150ValueByHand(unittest.TestCase):
  91 | +    """RULING 150 (1) (orchestrator 10:40 ET Nov 18), applied BY HAND to the one exception pin: the exact closing line
  92 | +    the driver names (--value-soft-line) keeps its place in the never-empty pass when its MEASURED value verdict (ruling
  93 | +    91) is LOST, flagged 'The closing line may mostly restate the clips: "<line>"'. Any other line, an unmeasured
  94 | +    verdict, and the clean pass: unchanged."""
  95 | +    TICKER = {"kind": "ticker", "text": "S&P 500 Nasdaq Bitcoin", "whole_in_16x9": True, "in_9x16": "cut",
  96 | +              "covers_speaker": False}
  97 | +
  98 | +    def run_rig(self, line, measured=True):
  99 | +        import test_medley as TM
 100 | +        from test_moments import pm
 101 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 102 | +        lost = {"adds": "yes", "no_restate": "no", "why": "it restates the clips"} if measured else {"measured": False}
 103 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 104 | +                   visuals={"x": {"burned_in": [dict(self.TICKER)]}}, values=[dict(lost) for _ in range(6)],
 105 | +                   follow_up={"angles": [TM.angle(["h", "x", "y"], "h")]})
 106 | +        r.build_kw = {"never_empty": True}
 107 | +        with mock.patch.object(PK, "VALUE_SOFT_LINE", line):
 108 | +            return r.run()["package"]
 109 | +
 110 | +    def test_the_named_line_seals_flagged(self):
 111 | +        import test_medley as TM
 112 | +        pk = self.run_rig(TM.Rig.LINE)
 113 | +        self.assertIsNotNone(pk)
 114 | +        row = pk["gates"]["takeaway_value"]
 115 | +        self.assertEqual((row["status"], row["flags"], row["text"]), (
 116 | +            "FLAGGED", [f'The closing line may mostly restate the clips: "{TM.Rig.LINE}"'], TM.Rig.LINE))
 117 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 118 | +
 119 | +    def test_the_clean_pass_never_takes_it(self):
 120 | +        import test_medley as TM
 121 | +        from test_moments import pm
 122 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]           # nothing soft: the clean pass
 123 | +        r = TM.Rig(ms, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 124 | +                   values=[{"adds": "yes", "no_restate": "no", "why": "it restates the clips"} for _ in range(6)])
 125 | +        with mock.patch.object(PK, "VALUE_SOFT_LINE", TM.Rig.LINE):
 126 | +            self.assertIsNone(r.run()["package"])                                   # reaches the value gate: HARD
 127 | +
 128 | +    def test_any_other_line_or_no_verdict_stays_hard(self):
 129 | +        import test_medley as TM
 130 | +        self.assertIsNone(self.run_rig("A different closing line."))
 131 | +        self.assertIsNone(self.run_rig(None))
 132 | +        self.assertIsNone(self.run_rig(TM.Rig.LINE, measured=False))
 133 | +
 134 | +
 135 |  class TestRuling148RuntimeFloor(unittest.TestCase):
 136 |      """RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18; standing from the 12:00 build): in the never-empty pass a
 137 |      medley's clips may total LY_FLOOR_S (30 s) or more; under medley_content_range()'s lo (36.7 s) the package seals with
 138 | 
```

---

pp-selectid: RULING 150 (1) (orchestrator 10:40 ET Nov 18), APPLIED BY HAND to the one exception pin ("as a manual
application of this ruling logged in the build record if the code is not yet built; build the code audit-first right
after"). The ruling: the takeaway's value verdict (ruling 91) is SOFT, flagged 'The closing line may mostly restate the
clips: "<the line>"'; fidelity (COMMENTARY, NEEDS_SOURCE), length and the banned words stay HARD. For THIS pin: seal
build 150's line-up with write 1 as the takeaway if it passes fidelity (its only refusal was VALUE).
THE CHANGE (narrow; the general rule follows in its own audited change):
- package.VALUE_SOFT_LINE (None by default) = the exact closing line the driver names (--value-soft-line LINE, which
  requires --pbx-exception and a non-empty line). In _build's write loop, ONLY in the never-empty pass (soft), ONLY
  for a MEASURED value verdict that is not ok, ONLY when the line written is exactly VALUE_SOFT_LINE: val becomes
  dict(val, soft=True), the line-up's record gets value_by_hand {ruling, line, answers}, a log line; the loop then goes
  on to the paid gates (fidelity + context, HARD as before) instead of the rewrite. Every other case: unchanged.
- inventory: the takeaway_value row (its text is the judged line, as the pin and the render compare) gets status
  FLAGGED and flags [VALUE_FLAG with the line verbatim] when value.soft and value.ok is not True.
- package_pin.SOFT_GATES += "takeaway_value" (the integrator's check_pin_only reads it live; its render reads the
  sealed row: FLAGGED with plain flags, replayed false, text equal to the shipped line).
Files: pipeline/package.py, pipeline/package_pin.py, tests/package/proof_ledger.py, tests/package/test_ruling_137.py.
TESTS (TestRuling150ValueByHand, the real build() on the stubbed rig): the named line seals with the FLAGGED row, the
exact sentence and text, gate_problems none; another line, no line, an unmeasured verdict: no package; the clean pass
reaching the value gate with the line named: no package. Mutations 6 of 6 killed (never by hand; any line; unmeasured
too; the row never flagged; not a soft gate; the clean pass too); control passes.
PLEASE CHECK: (1) can any line other than the named one, or the clean pass, or an unmeasured verdict, get through?
(2) does fidelity / context / length / banned words stay HARD for the named line? (3) the row the render reads.


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
