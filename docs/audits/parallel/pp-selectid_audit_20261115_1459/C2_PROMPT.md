# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1459
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## DEEPSEEK-V4.1-FLASH — CYCLE 1 OUTPUT
# deepseek-v4.1-flash (deepseek/deepseek-v4.1-flash) 267 s finish=stop usage in 8737 / out 15028 usd_reported=0.003337 usd~0.252 (upper-bound price)

[P1] `hook_bar.bar()` accepts non-finite floats for `valid_h` (e.g. `NaN`, `Infinity`, `-Infinity`) and arbitrarily large numbers. `type(vh) in (int, float)` and `vh <= 0` do not reject `float('nan')` or `float('inf')`; `timedelta(hours=vh)` then raises `ValueError`/`OverflowError` instead of returning a clean refusal. This violates M12 fail-closed (an exception should reject, but it must not crash the build) and can take down a build from a corrupt calibration file. Fix: require `math.isfinite(vh)` and bound `vh` to a safe maximum (e.g. `timedelta.max` in hours). Add tests for `NaN`, `inf`, `-inf`, and `1e308`.

[P2] Test coverage for `valid_h` is incomplete. The new test checks `0`, `-1`, `"24"`, and `True`, but not non-finite floats or huge numbers. Add the cases above to `test_a_calibration_lasts_as_long_as_its_own_valid_h_says`.

[P3] The `valid_h` type check `type(vh) not in (int, float)` correctly rejects `bool` (since `type(True) is bool`), but the intent is non-obvious. A comment or `isinstance(vh, bool) or not isinstance(vh, (int, float))` would be clearer.

[P3] The `valid_h_note` string in `hook_calibration.json` is long and duplicates the module docstring. Consider moving it to a comment or a separate doc to keep the sealed JSON minimal.

[P2] The live bar now carries an extra `"valid_h"` key. If any consumer of `_live_bar()` performs a strict schema check or equality comparison on the returned dict, this could break. No such consumer is shown in the diff, but it is worth confirming.

[P3] The `bar()` docstring says “and is within its own ‘valid_h’ (null: no expiry)”, but the function also refuses a missing `valid_h`. The docstring could mention that a missing key is refused.

P1_OR_WORSE: 1

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 28 s finish=stop usage in 8627 / out 556 usd_reported=0.020587 usd~0.057 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1459 (RULING 115 interim hook bar)**

**Summary**  
The diff implements exactly the semantics described in the PR text and the four explicit "PLEASE CHECK" items:  
- No calibration can be valid forever except by an explicit `"valid_h": null`.  
- All pre-existing validation (sha256 seal, rater/question_version/seed/asking match, timezone, skew, floor >= 3) is untouched and executed in the same order.  
- The reading of rulings 115 (1) and (3) matches the provided text (interim bar sourced from a single fixed ALONE_TEST.json therefore does not carry the once-per-day expiry that belongs to the later question-version calibration).  
- Tests are expanded, pass, and kill the four relevant mutations.  

The change is isolated to hook calibration expiry, does not touch rendering, selection logic, EDLs, final bytes, sentence boundaries, credits, voice-over, or any gate that affects L-a through L-l, LAW 20/M2, M12, or LAW 22. No new renderer/compositor/selector. Fail-closed behavior is preserved (missing/invalid `valid_h` → no hook passes). The updated JSON is correctly re-sealed.

**Findings**  
[P3] hook_bar.py top comment still contains "(fail closed, law L-m)". L-m is not defined in the governing laws (they stop at L-l before LAW 20). While the *behavior* is correct (M12 fail-closed is respected), the reference should be removed or updated.  
[P3] bar() uses `type(vh) not in (int, float)` rather than `isinstance`. Functionally harmless for JSON-loaded primitives but deviates from Python norms.  
[P3] TestTheLiveCalibration.test_the_interim_bar_does_not_expire calls `HB.bar(...)` with a 30-day-future timestamp; this is correct but the test name and docstring could be more precise about also exercising the real production calibration file (already done in the subsequent test).  
[P2] "Smallest diff" (M1) is stretched by 176 lines that are 70 % test/docstring updates. The functional delta is ~15 lines; the remainder, while justified for coverage, could have been split into a pure test-only follow-up commit.

No gate logic, byte fidelity, sentence-law edge handling, release_auth, canon.py usage, or protected preview reference is altered. All must-fail/must-pass examples cited in the governing laws remain unaffected. The interim bar now behaves as ruling 115 requires without weakening any other law.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 91 s finish=stop usage in 9411 / out 3457 usd_reported=0.003875 usd~0.080 (upper-bound price)

I have reviewed the diff for `pp-selectid` (RULING 115 (1) follow-up). The change moves the hook calibration expiry from a hardcoded 24-hour constant to a file-driven `valid_h` field, allowing `null` for indefinite validity (specifically for the interim bar).

Here is my audit:

### Findings

**1. [P1] Type Check Vulnerability: `bool` is a subclass of `int`**
In `pipeline/hook_bar.py`, the validation for `valid_h` is:
```python
if type(vh) not in (int, float) or vh <= 0:
```
In Python, `bool` is a subclass of `int`. Therefore, `type(True)` is `bool`, which is **not** in `(int, float)`? Wait, `isinstance(True, int)` is `True`, but `type(True) is int` is `False`.
Let's check the code: `type(vh) not in (int, float)`.
If `vh` is `True`: `type(True)` is `bool`. `bool` is not `int` (it is a subclass, but `type()` returns the exact class). So `type(True) not in (int, float)` evaluates to `True`. The code **refuses** `True`.
If `vh` is `False`: `type(False)` is `bool`. Refused.
So the code correctly rejects booleans via the `type()` check.
*Correction*: The test suite explicitly tests `True` and expects it to be refused (line 138-140 in diff: `for bad in (0, -1, "24", True): ... self.assertIsNone(self.bar()[0], bad)`).
Since `type(True)` is `bool`, and `bool` is not in `(int, float)`, the condition `type(vh) not in (int, float)` is `True`, so it returns `None` (refused). This is correct behavior.
However, relying on `type()` exact match is brittle if someone passes a numpy integer or similar, but in this context (JSON load), it's safe.
**Wait**, let's look closer at the logic.
`if type(vh) not in (int, float) or vh <= 0:`
If `vh` is `True`: `type(True)` is `bool`. `bool` is not in `(int, float)`. Condition is True. Returns `None`. Correct.
If `vh` is `1`: `type(1)` is `int`. `int` is in `(int, float)`. Condition is False. Checks `1 <= 0` (False). Passes. Correct.
If `vh` is `1.0`: `type(1.0)` is `float`. Passes. Correct.
If `vh` is `"24"`: `type("24")` is `str`. Refused. Correct.

Is there a P1 here?
Actually, there is a subtle issue with `type(vh) not in (int, float)`.
If `vh` is a `numpy.int64` (unlikely from JSON, but possible if the file was manipulated or loaded via a different path), it would be refused. But `json.load` returns standard Python types.
The logic seems sound for the stated purpose.

**2. [P2] `valid_h` is not included in the SHA256 seal verification logic explicitly in the diff, but `load()` checks the whole file.**
The diff shows `hook_calibration.json` is re-sealed with a new SHA256 (`6978392...`). The `load()` function (not shown in diff, but referenced) checks the SHA256 of the file content. Since the file content changed (added `valid_h`), the SHA256 must match the new one. The diff updates the SHA256 in the JSON. This is consistent.

**3. [P2] Documentation/Comment Consistency**
The docstring in `hook_bar.py` line 35 says: `and is within its own "valid_h" (null: no expiry)`.
The code implements this.
The `hook_calibration.json` has `valid_h: null`.
The test `test_the_interim_bar_does_not_expire` verifies that `valid_h: null` allows the bar to be valid 30 days later.
This aligns with Ruling 115 (1).

**4. [P3] Nit: `valid_h_note` is not validated**
The `valid_h_note` field is added to the JSON. It is not used in the logic, only for documentation. This is fine.

**5. [P1] Potential Logic Gap: `valid_h` validation order**
In `bar()`:
```python
if "valid_h" not in cal:
    return None, "..."
vh = cal["valid_h"]
if vh is not None:
    if type(vh) not in (int, float) or vh <= 0:
        return None, "..."
    if age > timedelta(hours=vh):
        return None, "..."
```
If `vh` is `None`, it skips the type check and the age check. This is correct for "no expiry".
If `vh` is a number, it checks type and age.
This logic is correct.

**6. [P1] Missing Check: `valid_h` must be finite?**
If `valid_h` is `float('inf')`, `type(vh)` is `float`. `vh <= 0` is False. `age > timedelta(hours=inf)` is False. So it would be treated as "no expiry".
Is `inf` a valid JSON value? No, standard JSON does not support `Infinity`. `json.load` will raise an error or return `None`/`NaN` depending on `parse_constant`. By default, `json.load` raises `ValueError` for `Infinity`/`NaN` unless `parse_constant` is set.
If the file contains `Infinity`, `json.load` will fail, and `load()` will likely return `None` (fail closed).
So this is not a vulnerability.

**7. [P2] Test Coverage for `valid_h` in `bar()` return value**
The test `test_a_calibration_lasts_as_long_as_its_own_valid_h_says` checks `live["valid_h"]` is `None` when `valid_h` is `None`.
It does not explicitly check that `live["valid_h"]` is `24` when `valid_h` is `24`.
However, the code returns `"valid_h": vh`. This is a minor test gap, not a code defect.

**8. [P1] Critical: `type(vh) not in (int, float)` rejects `bool` correctly, but what 

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1459 (ruling 115: the calibration's expiry is the file's own)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and deepseek-v4.1-flash (1; glm-5.3-flash's ruling-99 breaker is open, so
the driver took deepseek); they disagree on a P1, so Grok was asked (0). Cycle 1: $0.0278 vendor-reported.

THE P1 (deepseek): "valid_h NaN / Infinity / -Infinity / a huge number: type(vh) in (int, float) and vh <= 0 let them
through, and timedelta(hours=vh) then RAISES (ValueError / OverflowError): a corrupt calibration would crash a build
instead of refusing it". REAL (Python's json.load reads NaN and Infinity by default). FIXED: valid_h must be an
int / float with 0 < valid_h <= MAX_VALID_H (24 x 366 hours); every comparison with NaN is false and +-Infinity is
outside the range, so neither reaches timedelta. And the same class one line up, found while fixing it: a floor of
Infinity made int() raise OverflowError, which the floors' except did not catch; it is caught now (a NaN floor already
raised ValueError, caught). Tests: valid_h NaN, Infinity, -Infinity and 1e300 are refused without raising; a floor
of Infinity or NaN is refused without raising. Mutations (after a control run): no upper bound on valid_h, and
OverflowError not caught: both KILLED; with V1-V4: 6 of 6.

NOT CHANGED:
- qwen "bool is a subclass of int": type(vh) is compared exactly, so True (type bool) is refused; tested.
- qwen "VALID_H referenced elsewhere?": grep over pipeline/ and tests/: no other reference.
- deepseek P2 "the live bar carries a new key valid_h": its consumers read named keys (hook_own, hook_bar_mark, the
  build line); none compares the dict whole.
- Grok P3 "law L-m is not in the governing list": it is this project's law (no verdict is never a pass), cited
  across the package code; the audit package's list is the gospel excerpt.
- Grok P2 "the diff is 70 % tests and docstrings": kept together: the behaviour and its proof land as one change.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1459/C2_STEP.diff (190 lines)
```
   1 | diff --git a/pipeline/hook_bar.py b/pipeline/hook_bar.py
   2 | index d29c497..02161ba 100644
   3 | --- a/pipeline/hook_bar.py
   4 | +++ b/pipeline/hook_bar.py
   5 | @@ -6,9 +6,11 @@ value the part took across PBX's approved hooks, under that same asking (the sou
   6 |  ALONE_TEST.json). No floor is set below 3: the order stops a lower one at 3, and the builder reports it.
   7 |  
   8 |  The floors live in ONE calibration file, pipeline/hook_calibration.json, with its sha256. It is valid only for its
   9 | -rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for 24 h after it was
  10 | -measured (ruling 113 (2): again on any change, and once a day). An invalid or stale file passes NO hook, and the
  11 | -build says why in one line (fail closed, law L-m).
  12 | +rater, its question version (package.HOOK_VERSION), its seed and its asking ("alone"), and for as long as the FILE
  13 | +says: "valid_h" hours after it was measured, or null for no expiry. Ruling 115's interim bar is null: its floors come
  14 | +from ONE fixed source (ALONE_TEST.json), and ruling 113 (2)'s once-a-day law is measured against ruling 115 (3)'s
  15 | +question version, not this one; a calibration under that law will carry its 24. A file that names no "valid_h" is
  16 | +refused. An invalid or stale file passes NO hook, and the build says why in one line (fail closed, law L-m).
  17 |  A package sealed on this bar says so in its record (NOTE). PBX's approve or reject of it is appended to the file
  18 |  (add_example), so the approved set grows.
  19 |  """
  20 | @@ -21,8 +23,8 @@ from datetime import datetime, timedelta, timezone
  21 |  PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook_calibration.json")
  22 |  PARTS = ("scroll", "alone", "setup")
  23 |  FLOOR_MIN = 3                       # the order: "If any floor comes out below 3, stop at 3 for that part and tell me."
  24 | -VALID_H = 24.0                      # ruling 113 (2): "once a day"
  25 |  SKEW_MIN = 5.0                      # a measured_at at most this many minutes ahead of now (clock skew) is accepted
  26 | +MAX_VALID_H = 24.0 * 366             # a valid_h above a year is refused (and stays far inside timedelta's range)
  27 |  NOTE = "hook passed on the calibrated bar"
  28 |  
  29 |  
  30 | @@ -61,8 +63,8 @@ def load(path=PATH):
  31 |  
  32 |  def bar(rater, question_version, seed, now=None, path=PATH):
  33 |      """The live bar: {"floors", "sha256", "rater", ...} when the calibration is valid for exactly this question
  34 | -    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is under
  35 | -    VALID_H old; else (None, why), and no hook passes."""
  36 | +    version and seed (and this rater, when one is named; passes() checks each rating's own back-end), and is within
  37 | +    its own "valid_h" (null: no expiry); else (None, why), and no hook passes."""
  38 |      cal, why = load(path)
  39 |      if cal is None:
  40 |          return None, why
  41 | @@ -74,19 +76,26 @@ def bar(rater, question_version, seed, now=None, path=PATH):
  42 |      try:
  43 |          at = datetime.fromisoformat(str(cal["measured_at"]))
  44 |          fl = {p: int(cal["floors"][p]) for p in PARTS}
  45 | -    except (KeyError, TypeError, ValueError):
  46 | +    except (KeyError, TypeError, ValueError, OverflowError):   # Infinity / NaN floors too (audit 1459 C1, deepseek)
  47 |          return None, "the hook calibration has no readable measured_at or floors"
  48 |      if at.tzinfo is None:                # a naive time cannot be compared with now (audit 20261115_1410)
  49 |          return None, "the hook calibration's measured_at has no timezone: refused"
  50 |      age = (now or datetime.now(timezone.utc)) - at
  51 | -    if age < -timedelta(minutes=SKEW_MIN):   # measured "in the future" would stretch the 24 h (audit 1410 C1, qwen)
  52 | +    if age < -timedelta(minutes=SKEW_MIN):   # measured "in the future" would stretch its validity (audit 1410 C1, qwen)
  53 |          return None, f"the hook calibration's measured_at ({cal['measured_at']}) is in the future: refused"
  54 | -    if age > timedelta(hours=VALID_H):
  55 | -        return None, f"the hook calibration is over {VALID_H:g} h old (measured {cal['measured_at']}): re-run it"
  56 | +    if "valid_h" not in cal:                 # explicit: never a calibration valid forever by an omission
  57 | +        return None, "the hook calibration names no valid_h (hours, or null for none): refused"
  58 | +    vh = cal["valid_h"]
  59 | +    if vh is not None:
  60 | +        if type(vh) not in (int, float) or not 0 < vh <= MAX_VALID_H:   # NaN and +-Infinity fail the range too:
  61 | +            return None, (f"the hook calibration's valid_h {vh!r} is not a number of hours in (0, "   # they never
  62 | +                          f"{MAX_VALID_H:g}]: refused")       # reach timedelta (audit 1459 C1, deepseek)
  63 | +        if age > timedelta(hours=vh):
  64 | +            return None, f"the hook calibration is over {vh:g} h old (measured {cal['measured_at']}): re-run it"
  65 |      if any(v < FLOOR_MIN for v in fl.values()):
  66 |          return None, f"a floor under {FLOOR_MIN} in the hook calibration: refused"
  67 |      return {"floors": fl, "sha256": cal["sha256"], "rater": cal["rater"], "question_version": cal["question_version"],
  68 | -            "seed": cal["seed"], "measured_at": cal["measured_at"]}, None
  69 | +            "seed": cal["seed"], "measured_at": cal["measured_at"], "valid_h": vh}, None
  70 |  
  71 |  
  72 |  def passes(rec, live):
  73 | diff --git a/pipeline/hook_calibration.json b/pipeline/hook_calibration.json
  74 | index 4c606ad..5668fb3 100644
  75 | --- a/pipeline/hook_calibration.json
  76 | +++ b/pipeline/hook_calibration.json
  77 | @@ -81,6 +81,8 @@
  78 |   "rule": "a hook passes when EACH of scroll / alone / setup is at least its floor; a floor is the lowest value the part takes across the approved hooks under this asking, never below 3",
  79 |   "ruling": "115 (orchestrator 13:24 ET Nov 15): the hook bar is defined by PBX's approvals",
  80 |   "seed": 7,
  81 | - "sha256": "fb964eb15a242b3ee7e385ce383546baa74e303d5009529eeab3cc18f313320b",
  82 | - "source": "tests/package/proof/hook113/ALONE_TEST.json"
  83 | + "sha256": "6978392df37e5abff8594c6fc293e29cf761718fc0530cd87ed6b3892c3fafd6",
  84 | + "source": "tests/package/proof/hook113/ALONE_TEST.json",
  85 | + "valid_h": null,
  86 | + "valid_h_note": "ruling 115 (1): the interim bar's floors come from ONE fixed source (tests/package/proof/hook113/ALONE_TEST.json), so it does not expire; ruling 113 (2)'s once-a-day law is measured against ruling 115 (3)'s question version (ruling 115 (3)), whose calibration will carry its 24."
  87 |  }
  88 | diff --git a/pipeline/package.py b/pipeline/package.py
  89 | index d96a7cd..5bbda7a 100644
  90 | --- a/pipeline/package.py
  91 | +++ b/pipeline/package.py
  92 | @@ -1407,7 +1407,7 @@ _LIVE = {}
  93 |  
  94 |  def _live_bar():
  95 |      """The calibrated bar, read once per state of the calibration file (its mtime) and per minute: a build reads it a
  96 | -    few times, and a calibration that ages past its 24 h mid-build stops passing hooks within the minute."""
  97 | +    few times, and a calibration that ages past its own valid_h mid-build stops passing hooks within the minute."""
  98 |      import hook_bar as HB
  99 |      try:
 100 |          k = (os.stat(HB.PATH).st_mtime_ns, int(time.time() // 60))
 101 | diff --git a/tests/package/test_hook_bar.py b/tests/package/test_hook_bar.py
 102 | index 793a5f9..0225145 100644
 103 | --- a/tests/package/test_hook_bar.py
 104 | +++ b/tests/package/test_hook_bar.py
 105 | @@ -2,7 +2,8 @@
 106 |  """RULING 115 (orchestrator 13:24 ET Nov 15): THE CALIBRATED HOOK BAR (pipeline/hook_bar.py). A hook passes when each of
 107 |  scroll / alone / setup is at least the LOWEST value that part takes across PBX's approved hooks under the same asking
 108 |  (ALONE, production's seed, Grok); no floor under 3; one sealed calibration file, valid for its rater, question version,
 109 | -seed and asking, for 24 h; a package sealed on it says so; PBX's verdicts on such packages are appended as examples.
 110 | +seed and asking, for as long as the file says (valid_h hours, or null: ruling 115's interim bar); a package sealed on it
 111 | +says so; PBX's verdicts on such packages are appended as examples.
 112 |  The live file is checked against its source and against production's hook job."""
 113 |  import copy
 114 |  import json
 115 | @@ -33,7 +34,7 @@ def cal(parts=((3, 4, 3), (3, 5, 4), (4, 5, 4)), **kw):
 116 |      ap = approved(*parts)
 117 |      fl, low = HB.floors_from(ap)
 118 |      return dict({"rater": G, "asking": "alone", "seed": 7, "question_version": "qv", "measured_at": AT.isoformat(),
 119 | -                 "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)
 120 | +                 "valid_h": 24, "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)
 121 |  
 122 |  
 123 |  class TestFloors(unittest.TestCase):
 124 | @@ -108,15 +109,34 @@ class TestTheFile(unittest.TestCase):
 125 |          HB.write(cal(asking="batched"), self.path)                         # the batch moved single ratings
 126 |          self.assertIsNone(self.bar()[0])
 127 |  
 128 | -    def test_once_a_day_a_stale_calibration_passes_nothing(self):
 129 | -        HB.write(cal(), self.path)
 130 | +    def test_a_calibration_lasts_as_long_as_its_own_valid_h_says(self):
 131 | +        """valid_h hours (a standing-law calibration: ruling 113 (2)'s once a day), or null for none (ruling 115's
 132 | +        interim bar: one fixed source); a file that names no valid_h, or a bad one, passes nothing."""
 133 | +        HB.write(cal(), self.path)                                          # valid_h 24
 134 |          self.assertIsNotNone(self.bar(now=AT + timedelta(hours=23, minutes=59))[0])
 135 |          live, why = self.bar(now=AT + timedelta(hours=24, minutes=1))
 136 |          self.assertIsNone(live)
 137 |          self.assertIn("over 24 h old", why)
 138 | +        HB.write(cal(valid_h=None), self.path)                              # the interim bar: no expiry
 139 | +        live, why = self.bar(now=AT + timedelta(days=30))
 140 | +        self.assertEqual((live["floors"], live["valid_h"], why), ({"scroll": 3, "alone": 4, "setup": 3}, None, None))
 141 | +        c = cal()
 142 | +        del c["valid_h"]
 143 | +        HB.write(c, self.path)                                              # never valid forever by an omission
 144 | +        live, why = self.bar()
 145 | +        self.assertIsNone(live)
 146 | +        self.assertIn("names no valid_h", why)
 147 | +        for bad in (0, -1, "24", True, float("nan"), float("inf"), -float("inf"), 1e300):
 148 | +            HB.write(cal(valid_h=bad), self.path)                       # never raises (audit 1459 C1, deepseek)
 149 | +            self.assertIsNone(self.bar()[0], bad)
 150 | +        for bad in (float("inf"), float("nan")):                        # nor does a floor that is not finite
 151 | +            HB.write(cal(floors={"scroll": bad, "alone": 4, "setup": 3}), self.path)
 152 | +            live, why = self.bar()
 153 | +            self.assertIsNone(live, bad)
 154 | +            self.assertIn("no readable measured_at or floors", why)
 155 |  
 156 |      def test_a_future_or_naive_measured_at_passes_nothing(self):
 157 | -        """Audit 20261115_1410 C1 (qwen): a calibration "measured" ahead of now would stretch its 24 h; a time with no
 158 | +        """Audit 20261115_1410 C1 (qwen): a calibration "measured" ahead of now would stretch its validity; a time with no
 159 |          timezone cannot be compared with now (it must never raise into a build)."""
 160 |          HB.write(cal(), self.path)
 161 |          self.assertIsNotNone(self.bar(now=AT - timedelta(minutes=4))[0])  # clock skew inside 5 min
 162 | @@ -204,7 +224,7 @@ class TestTheMark(unittest.TestCase):
 163 |  
 164 |  class TestTheLiveCache(unittest.TestCase):
 165 |      """package._live_bar: the bar is read once per state of the file and per minute (so a calibration that ages past
 166 | -    its 24 h mid-build stops passing hooks within the minute), and again as soon as the file changes."""
 167 | +    its valid_h mid-build stops passing hooks within the minute), and again as soon as the file changes."""
 168 |      real_hook_bar = True
 169 |  
 170 |      def test_read_once_a_minute_and_again_when_the_file_changes(self):
 171 | @@ -236,9 +256,17 @@ class TestTheLiveCache(unittest.TestCase):
 172 |  class TestTheLiveCalibration(unittest.TestCase):
 173 |      """The calibration production reads (pipeline/hook_calibration.json): its floors are derived from their source
 174 |      (tests/package/proof/hook113/ALONE_TEST.json: Grok asked alone at seed 7; the two out-of-contract first answers
 175 | -    asked once more), and it is for production's question version, seed and hook list."""
 176 | +    asked once more), and it is for production's question version, seed and hook list. Ruling 115's interim bar does
 177 | +    not expire: its floors come from that one fixed source."""
 178 |      real_hook_bar = True
 179 |  
 180 | +    def test_the_interim_bar_does_not_expire(self):
 181 | +        c, why = HB.load()
 182 | +        self.assertIsNone(why)
 183 | +        at = datetime.fromisoformat(c["measured_at"])
 184 | +        live, why = HB.bar(None, c["question_version"], c["seed"], now=at + timedelta(days=30))
 185 | +        self.assertEqual((live is not None, why), (True, None))
 186 | +
 187 |      def test_its_floors_are_its_sources_lowest_parts(self):
 188 |          c, why = HB.load()
 189 |          self.assertIsNone(why)
 190 | 
```

---

pp-selectid: RULING 115 (1), a follow-up to the landed calibrated hook bar (da7b1160, audit 20261115_1410): THE
CALIBRATION'S EXPIRY IS THE FILE'S OWN, and ruling 115's interim bar does not expire. Files: pipeline/hook_bar.py,
pipeline/hook_calibration.json, pipeline/package.py (one docstring), tests/package/test_hook_bar.py.

WHY: the landed code expired every calibration 24 h after it was measured (VALID_H, "ruling 113 (2): once a day").
Read again, the orders do not ask that of the interim bar. Ruling 115 (1): "A hook passes when EACH of its three parts
(scroll, alone, setup) is at least the LOWEST value that part takes across the five approved hooks under that same
asking (ALONE_TEST.json is the source; write the three floors into one calibration file with its sha ...)": ONE fixed
source. Ruling 115 (3): "The standing law of ruling 113 (2) is then measured against that version" (the new question
version with examples), so the once-a-day law belongs to THAT version's calibration. With the 24 h, every build from
13:07 ET Nov 16 would have stopped at "no hook in the pool" (the bar invalid), with no committed tool to re-measure.

THE CHANGE:
- hook_bar.bar(): the expiry is the calibration file's own "valid_h": a positive number of hours after measured_at,
  or null for no expiry. A file with NO "valid_h" key is refused (never valid forever by an omission); a valid_h that
  is not a positive int/float (0, -1, "24", true) is refused. Every other check is unchanged: the sha seal, the rater
  / question version / seed / asking, a timezone on measured_at, not in the future beyond SKEW_MIN, no floor under 3.
  The live bar carries "valid_h". VALID_H (the module constant) is gone.
- hook_calibration.json: "valid_h": null and a "valid_h_note" citing ruling 115 (1) and (3); re-sealed (sha
  6978392df37e...). The floors, rater, question version (e3cba8d92551), seed and measured_at are unchanged.
- package._live_bar's docstring: "its own valid_h" for "its 24 h".

UNCHANGED GUARDS: load() refuses a body whose sha256 does not match (pipeline/hook_bar.py:51-58); passes() requires the
rating's back-end to be the calibration's rater (:96-104); package._live_bar re-reads the file on any mtime change and
once a minute (pipeline/package.py:1406-1418).

TESTS: test_hook_bar.py: a calibration lasts as long as its own valid_h says (24: valid at 23:59, refused at 24:01;
null: valid 30 days later; no key: refused; 0 / -1 / "24" / true: refused); the live file's interim bar does not
expire (valid 30 days after measured_at). tests/package + the medley and spotlight suites pass (274). Mutations (after
a control run): a valid_h that never expires, an omitted valid_h accepted, a bad valid_h accepted, null treated as a
number: 4 of 4 killed.

PLEASE CHECK: (1) that no calibration can be valid forever except by an explicit null; (2) that every other check of
bar() is unchanged; (3) the reading of rulings 115 (1) and (3) above; (4) the tests.


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
