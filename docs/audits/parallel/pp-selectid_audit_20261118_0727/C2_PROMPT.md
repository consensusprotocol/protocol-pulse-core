# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_0727
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 280 s finish=stop usage in 6955 / out 6200 usd_reported=0.000984 usd~0.114 (upper-bound price)

The code implements a "clock-shift" hack to bypass a 12-hour expiry rule in the ingest adapter. While the arithmetic correctly tricks the expiry logic, it introduces a critical failure in the data retrieval window.

### [P0] Upper Bound Blind Spot
In `tests/package/proof_ledger.py` (line 27), the code defines `a_now = now - timedelta(hours=a.hours - base_h)` and passes this as the `now` argument to `LB.rows(since, a_now, horizon_h=a.hours)`.

In standard pipeline patterns (and specifically within the `ledger_build` / `ledger` logic referenced), the `now` argument serves two purposes:
1.  **The Expiry Reference:** It is used to calculate if a moment is too old (`published_at + 12h < now`).
2.  **The Query Ceiling:** It is used as the upper bound for the database query (`WHERE timestamp <= now`).

By shifting `a_now` back by 14 hours (when `--hours 26` is used), the code successfully makes a 25-hour-old moment appear 11 hours old (avoiding expiry). However, it simultaneously tells the adapter that the "current time" is 14 hours ago. Consequently, **every moment published within the last 14 hours is excluded from the results** because they fall after the `a_now` ceiling.

This is a catastrophic failure for a "fresh" pipeline. The "Must-produce" requirement for "today's $74K-pullback statements" will fail if those statements were published within the shifted window, as the most recent and relevant data is explicitly filtered out.

### [P2] Tautological Testing
The test in `tests/package/test_ruling_137.py` (lines 65-84) mocks `LB.rows` and asserts that the arguments passed to it are shifted. This tests the *implementation* (that the subtraction happened) rather than the *behavior* (that the correct rows are returned). Because the mock does not simulate the actual filtering logic of the adapter, it fails to catch the [P0] blind spot described above.

P1_OR_WORSE: 1

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 133 s finish=stop usage in 6172 / out 21608 usd_reported=0.002869 usd~0.343 (upper-bound price)

**Findings**

| # | Issue | Severity | Explanation |
|---|-------|----------|-------------|
| 1 | `package_pin.WINDOW_H` is widened in `main()` but never restored | **P2** | If `main()` is invoked more than once in the same process (e.g., during a long‑running service or a test suite that re‑uses the same interpreter), the widened window will persist and affect subsequent runs. The code currently relies on the caller to reset the value, which is fragile. |
| 2 | `a_now = now - timedelta(hours=a.hours - base_h)` can produce a future time when `a.hours < base_h` | **P2** | The logic assumes `a.hours` is always ≥ `base_h`. If a caller passes a smaller value (e.g., due to a bug or a future change in defaults), the subtraction becomes negative, causing `a_now` to be later than `now`. This would incorrectly advance the ingest adapter’s clock and could allow moments that should be excluded. |
| 3 | Test patches `PLG.PS.ledger_entries` to a lambda that returns `[]` | **P3** | While `main()` currently does not call `ledger_entries`, the patch could hide side‑effects if the implementation changes. The test is therefore fragile to future code changes. |
| 4 | Test uses `mock.patch('sys.stdout')` without a context manager | **P3** | The patch suppresses output but does not restore it automatically. In a larger test suite this could affect other tests that rely on `stdout`. |
| 5 | Test compares `back` with a tolerance of `0.05` h (~3 min) | **P3** | The tolerance is generous but acceptable; tightening it would make the test more precise without affecting correctness. |
| 6 | Test’s custom `rows` function raises `Past` to stop `main()` early | **P3** | The test verifies only the clock calculation; it does not assert that the rest of `main()` behaves correctly. This is acceptable for the current intent but could miss regressions in other parts of the function. |
| 7 | Test calculates `back = (t0 - now).total_seconds() / 3600` where `now` is `a_now` | **P3** | The calculation is correct but could be confusing because `now` is not the same as the `now` inside `main()`. Clarifying variable names would improve readability. |

**P1_OR_WORSE: 0**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 202 s finish=stop usage in 6638 / out 7651 usd_reported=0.006773 usd~0.135 (upper-bound price)



# Code Audit — pp-selectid / RULING 144 Part 2 (Ingest Adapter Clock Shift)

## Scope Reviewed

`tests/package/proof_ledger.py` (the `a_now` shift + log line) and `tests/package/test_ruling_137.py` (the new `test_the_ingest_adapter_is_asked_as_of_hours_minus_12_earlier`).

---

## Findings

### [P3] Redundant local import in test

`test_ruling_137.py` line 56: `import tempfile` inside the test method, but `tempfile` is already imported at module level (line 42). Harmless, but inconsistent with the rest of the file.

### [P3] `seen[-1]` is fragile if the adapter is ever called more than once

The test asserts on `seen[-1]` without first checking `len(seen) == 1`. If a future refactor causes `LB.rows` to be invoked twice (e.g., a retry path), the test would silently validate the second call's arguments and could pass while the first call's clock is wrong. A `self.assertEqual(len(seen), 1)` before the assertions would make the failure mode explicit.

### [P3] Variable name `a_now` shadows the argparse namespace `a`

In `proof_ledger.py` the local `a` is the argparse namespace; `a_now` reads as "argparse-namespace-now" at a glance. `adapter_now` or `shifted_now` would remove the ambiguity. Purely cosmetic.

---

## Verification of the Four Requested Checks

**(1) Can this admit anything the exception did not authorise?**

No. The adapter's internal expiry drops a moment when `given_now ≥ min(expires_at, published_at + 12 h)`. With `given_now = now − (hours − 12)`, the effective drop condition becomes `now − published_at ≥ hours`. A moment exactly `--hours` old satisfies the "at or past" boundary and is dropped; anything older is also dropped. The adapter's other filters (delivered-in-24 h, opt-out, hard flags) are unchanged and still run on the returned rows. `horizon_h` was already `a.hours` before this change, so the search range is not widened beyond what the exception authorises.

**(2) Can it leak into a build without the flag?**

No. The ternary `now - timedelta(hours=a.hours - base_h) if a.pbx_exception else now` evaluates to `now` when the flag is absent. `base_h` is read before the `if a.pbx_exception:` block that mutates `package_pin.WINDOW_H`, so even if the flag were somehow set and then unset in the same process, the arithmetic would use the original 12. Without the flag, `package_pin.WINDOW_H` is never touched.

**(3) Boundary arithmetic**

With `--hours 26`, `base_h 12`: `a_now = now − 14 h`.
- Moment at `now − 26 h`: expiry = `now − 14 h` = `a_now` → "at or past" → **dropped**. ✓
- Moment at `now − 25.999 h`: expiry = `now − 13.999 h` > `a_now` → **admitted**. ✓
- Moment at `now − 1 h`: expiry = `now + 11 h` > `a_now` → **admitted**. ✓

The `timedelta` subtraction is exact (no floating-point drift at these magnitudes). The log line correctly reports the shifted clock and the effective window.

**(4) The test**

- Correctly patches `PLG.LB.rows` to capture `(now, horizon_h)` and raise, so no downstream code runs.
- Two iterations: no-flag (expects `back ≈ 0`, `h == 12.0`) and `--hours 26 --pbx-exception` (expects `back ≈ 14.0`, `h == 26.0`).
- `t0` is captured immediately before `PLG.main`; the 0.05 h (180 s) delta absorbs any scheduling jitter.
- `PP.WINDOW_H` is saved/restored per iteration, preventing cross-contamination.
- Both stated mutations (clock never moved; shifted by `hours` instead of `hours − 12`) are killed: the first would give `back ≈ 0` in the exception case; the second would give `back ≈ 26`.

---

## Law Compliance

| Law | Status |
|-----|--------|
| LAW 20 / M2 (thresholds are constants; no reclassification) | ✓ — the 12 h constant is unchanged; the exception is a PBX-authorised one-process override, not a threshold edit. |
| M12 FAIL CLOSED | ✓ — if the adapter returns zero rows the build has no candidates and fails; no new pass path. |
| Smallest diff / M1 | ✓ — 4 lines of production logic + 1 log line; no new module, renderer, or selector. |
| GPU0 / no publishing | ✓ — no GPU or network calls in this diff. |

No law violations found.

---

P1_OR_WORSE: 0

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_0727, ruling 144 part 2: the adapter's clock under the exception)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gpt-oss-20b: P0/P1 none. gemma-4-31b-it: one P0 claimed, BY DESIGN:
gemma [P0] "with a_now 14 h back, every moment published in the last 14 h is out of the adapter's window": TRUE AND
INTENDED. Ruling 144 is ONE video from YESTERDAY'S batch ("ONE VIDEO, NOW, FROM YESTERDAY'S BATCH"); the exception build
runs with --only on six named moments, all 18-22 h old. Today's moments are not this build's business, and every build
without --pbx-exception (every later build) gives the adapter the render clock exactly as before (the test's first
half; mutation A1 killed). The build log line states the clock the adapter was read at. No change.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_0727/C2_STEP.diff (91 lines)
```
   1 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
   2 | index 55b6b06..551e068 100644
   3 | --- a/tests/package/proof_ledger.py
   4 | +++ b/tests/package/proof_ledger.py
   5 | @@ -53,7 +53,7 @@ import json
   6 |  import os
   7 |  import sys
   8 |  import time
   9 | -from datetime import datetime, timezone
  10 | +from datetime import datetime, timedelta, timezone
  11 |  
  12 |  HERE = os.path.dirname(os.path.abspath(__file__))
  13 |  REPO = os.path.dirname(os.path.dirname(HERE))
  14 | @@ -461,6 +461,7 @@ def main(argv=None):
  15 |      if not 0 < a.hours <= cap:                           # ruling 76: "rather than widen the window" (144: one exception)
  16 |          print(f"REFUSED (ruling 76): --hours {a.hours} is outside (0, {cap:g}]", file=sys.stderr)
  17 |          return 2
  18 | +    base_h = package_pin.WINDOW_H                        # 12: the rule (rulings 76 + 77) the exception widens
  19 |      if a.pbx_exception:                                  # RULING 144: this process only; every later build is 12 h
  20 |          package_pin.WINDOW_H = float(a.hours)            # (package.expired, window_problems and the registry read it)
  21 |      try:                                                 # read before anything is written (glm C2 N-4)
  22 | @@ -522,7 +523,12 @@ def main(argv=None):
  23 |          f"{len(delivered)} clip spans out")
  24 |      say(f"  RULING 76: {len(gone)} candidate(s) expired (over {package_pin.WINDOW_H:g} h on the render clock)" +
  25 |          (f": {gone}" if gone else ""))
  26 | -    rows, rep = LB.rows(since, now, horizon_h=a.hours)
  27 | +    a_now = now - timedelta(hours=a.hours - base_h) if a.pbx_exception else now   # RULING 144: the ingest adapter
  28 | +    rows, rep = LB.rows(since, a_now, horizon_h=a.hours)   # (pp-ingest's; its own 12 h expiry, rulings 76 + 77) is read
  29 | +    if a.pbx_exception:                                  # as of this earlier clock, so it admits moments up to --hours
  30 | +        say(f"  RULING 144 ({a.pbx_exception}): the ingest adapter read as of {a_now.isoformat(timespec='seconds')} "
  31 | +            f"({a.hours - base_h:g} h before the render clock), so its own {base_h:g} h expiry admits moments up to "
  32 | +            f"{a.hours:g} h old; every other check runs on the render clock with a {a.hours:g} h window")
  33 |      say(f"  adapter: {len(rows)} rows ({json.dumps(rep.get('excluded'))})")
  34 |      wp, wp_rep = LB.word_pass_index(a.word_pass)
  35 |      wp_refused = wp_rep.get("refused") or []             # final: the worker never re-works them (the inputs keep ids);
  36 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
  37 | index a679178..f2832ff 100644
  38 | --- a/tests/package/test_ruling_137.py
  39 | +++ b/tests/package/test_ruling_137.py
  40 | @@ -8,6 +8,7 @@ import os
  41 |  import sys
  42 |  import tempfile
  43 |  import unittest
  44 | +from datetime import datetime, timezone
  45 |  from unittest import mock
  46 |  
  47 |  HERE = os.path.dirname(os.path.abspath(__file__))
  48 | @@ -593,6 +594,42 @@ class TestRuling144TheOneException(unittest.TestCase):
  49 |          finally:
  50 |              PP.WINDOW_H = saved
  51 |  
  52 | +    def test_the_ingest_adapter_is_asked_as_of_hours_minus_12_earlier(self):
  53 | +        """pp-ingest's adapter drops a moment 12 h after its video's publish time on the clock it is given (rulings 76 +
  54 | +        77); under the exception it is given the render clock minus (hours - 12) h, so it admits moments up to --hours
  55 | +        old. Without the exception it gets the render clock, as ever."""
  56 | +        import tempfile
  57 | +        import proof_ledger as PLG
  58 | +        pins = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "proof", "fresh_20261112_050611", n)
  59 | +                for n in ("MOMENTS_PIN.json", "MOMENTS_PIN_LY.json")]
  60 | +        seen = []
  61 | +
  62 | +        class Past(Exception):
  63 | +            pass
  64 | +
  65 | +        def rows(since, now, horizon_h=None, **k):
  66 | +            seen.append((now, horizon_h))
  67 | +            raise Past()
  68 | +        saved = PP.WINDOW_H
  69 | +        try:
  70 | +            for extra in ([], ["--hours", "26", "--pbx-exception", "PBX exception x"]):
  71 | +                with tempfile.TemporaryDirectory() as d:          # one folder a run: a run's folder is never reused
  72 | +                    os.makedirs(os.path.join(d, "proof"))
  73 | +                    with mock.patch.object(PLG, "HERE", d), \
  74 | +                            mock.patch.object(PLG, "REGISTRY", os.path.join(d, "proof", "CANDIDATES.json")), \
  75 | +                            mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []), \
  76 | +                            mock.patch.object(PLG.LB, "rows", rows), mock.patch("sys.stdout"):
  77 | +                        t0 = datetime.now(timezone.utc)
  78 | +                        with self.assertRaises(Past):
  79 | +                            PLG.main(["--delivered", *pins, *extra])
  80 | +                now, h = seen[-1]
  81 | +                back = (t0 - now).total_seconds() / 3600
  82 | +                self.assertAlmostEqual(back, 14.0 if extra else 0.0, delta=0.05)
  83 | +                self.assertEqual(h, 26.0 if extra else 12.0)
  84 | +                PP.WINDOW_H = saved
  85 | +        finally:
  86 | +            PP.WINDOW_H = saved
  87 | +
  88 |  
  89 |  class TestTheDayCount(unittest.TestCase):
  90 |      def test_counted_per_day_ledger(self):
  91 | 
```

---

pp-selectid: RULING 144 (PBX 07:05 ET Nov 18: "disregard the 12 hour rule for this one exception"), PART 2. Part 1 is
live (fc191b4e, audit 20261118_0711): --pbx-exception TEXT lets --hours reach 30 for ONE build process and widens
package_pin.WINDOW_H for it. The first run (build 144, 07:24 ET) found NONE of the six named moments: the ingest adapter
(pp-ingest's pipeline.ingest.ledger.best_unused_moments, another session's code, run read-only through
pipeline/ledger_build.rows) has its OWN expiry: a moment is dropped when the clock it is GIVEN is at or past
min(expires_at, published_at + 12 h) (rulings 76 + 77; ledger.py:281 and :338). It dropped 3069 rows. File:
tests/package/proof_ledger.py (+ its test in tests/package/test_ruling_137.py).

THE CHANGE (only with --pbx-exception): the adapter is called with a_now = render clock - (hours - 12) h (12 = WINDOW_H
read BEFORE the exception widens it), and horizon_h = hours, so its own 12 h expiry admits moments up to --hours old
(a moment published exactly --hours ago expires at a_now and stays out). A line in the build log names it. Every other
check runs on the real render clock: package.expired and window_problems with the widened window, never-reused against
the delivered pins (package.usable), the exclusions, and the seal. Without the flag: the adapter gets the render clock,
exactly as before. The adapter's other drops (delivered in 24 h, opt-out, hard flags) still run on its rows.

TESTS: the adapter's clock is the render clock without the exception, and 14 h earlier with --hours 26 and the
exception; its horizon is the window. Mutations: 2 of 2 killed (the clock never moved; moved by hours, not hours - 12).

PLEASE CHECK: (1) can this admit anything the exception did not (older than --hours, a delivered or excluded moment)?
(2) can it leak into a build without the flag? (3) the arithmetic at the boundary; (4) the test.


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
