# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_2319
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 100 s finish=stop usage in 8105 / out 1927 usd_reported=0.000490 usd~0.053 (upper-bound price)

The code implements RULING 130 (3) to ensure that vision model billing—which often exceeds output caps and thus results in bills that are a small fraction of the total usage list price—still triggers the "reserve tripwire" if the actual bill exceeds the specific amount reserved for that call.

### Analysis

1.  **Fraction vs. Bills**: The `reserve_list_fraction` of `0.6` for `xai_vision:grok-4.7` is correctly derived from the provided data (max bill $0.1752 / list bound $0.2965 $\approx$ 59.1%). This provides a safe ceiling based on historical evidence.
2.  **Tripwire Logic**: 
    *   The modification to `providers.py` introduces `over_held`. This correctly identifies cases where the bill exceeds the `held` reservation, regardless of whether it exceeds the `fraction * list_price`.
    *   The check `_num(f)` and `_num(held)` prevents the tripwire from firing on models without a configured fraction or calls where no reservation was made.
    *   The logic is additive; it does not remove the existing `over_list` check, ensuring that standard models (like Grok) continue to behave as expected.
3.  **Governing Laws**: 
    *   The changes are confined to the infrastructure/billing layer. They do not touch the editorial pipeline, rendering logic, or QA gates.
    *   There are no violations of the Sentence Law, Selection Lock, or any of the L-series laws.
    *   Law 20/M2 is respected as no quality gate thresholds were modified to force a pass.
4.  **Tests**:
    *   `test_ruling_130_a_bill_above_its_reserve_trips_even_below_the_fraction_of_list` specifically validates the new `over_held` path.
    *   `test_ruling_130_the_vision_check_is_reserved_at_its_fraction` validates that the `reserve_list_fraction` is correctly applied during the reservation phase.

### Findings

No defects found. The implementation is precise and the tests are comprehensive.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 97 s finish=stop usage in 7790 / out 8273 usd_reported=0.006261 usd~0.147 (upper-bound price)



# Code Audit: pp-selectid — RULING 130 (3) Vision Reserve Tripwire

## Scope Reviewed

The diff modifies three files to fix a gap in the RULING 123 tripwire: vision calls whose usage runs past their output cap produce bills that are only 24–29 % of the list price of their *actual* usage, so the old `bill > fraction × list_of_usage` test never fired. The fix adds a second condition: `bill > held` (the amount actually reserved for the call).

---

## Findings

### [P3] Theoretical `held == 0` path is unreachable but unguarded

`over_held` requires `_num(held)`. If `_num(0)` returns `True` (it does for a standard `isinstance(x, (int, float))` check), then a call with `held = 0` would trip on any positive bill. In practice this is unreachable: `held = round(upper * frac, 6)` with `frac ∈ {0.25, 0.6}` and `upper > 0` (a zero-estimate call is rejected before settlement). No code change needed; noted for completeness against the audit question "cannot fire on a call that reserved nothing."

### [P3] `reserve_list_fraction_why` is a documentation-only JSON key

The 200-word rationale string in `model_providers.json` is never read by `providers.py` (only `reserve_list_fraction` is). It is clearly suffixed `_why` and sits alongside functional keys, so the risk of a future reader mistaking it for a parameter is low. No action required.

### [P3] Integration test reads live config

`test_ruling_130_the_vision_check_is_reserved_at_its_fraction` loads `P.CONFIG` and constructs a real vendor via `P.VENDORS["xai_vision"](...)`. This is appropriate (it verifies the *configured* backend end-to-end) but makes the test sensitive to config drift. If `price_usd_per_1m` or `min_out` change, the test's arithmetic shifts. Acceptable for a ruling-verification test; a pure-unit twin would be more robust for CI.

---

## Verification Against the Four Audit Questions

**(1) Fraction against the bills.**
Max recorded bill $0.1752 / list bound $0.2965 = 59.1 %. The configured fraction is 0.60, which exceeds the observed maximum. The `why` string documents the full distribution (min / median / p90 / max). Correct.

**(2) New tripwire test and the "reserved nothing" guard.**
- `over_held = bill is not None and _num(f) and _num(held) and bill > float(held)`.
- If `f` is absent (`_num(f)` False), neither `over_list` nor `over_held` evaluates → no trip. Backends without a fraction are unaffected.
- If `held` is `None` (no reservation made), `_num(None)` False → no trip.
- The test `test_ruling_130_a_bill_above_its_reserve_trips_even_below_the_fraction_of_list` exercises exactly the gap: bill $0.25 > held $0.2295 but < 0.6 × $0.755 (list of actual usage). The trip fires via `over_held`, the `why` string names "above its reserve," and the next call on the same day is reserved at full list and hits `SpendLimit`. Correct.

**(3) No change for other back-ends.**
Grok-4.7 (fraction 0.25, bills ≈ $0.01, reserves $0.06–$0.12): `over_list` and `over_held` are both far from triggering. The `not (d.get("reserve_tripped") or {}).get(backend.name)` guard prevents re-tripping. The `bill` extraction refactor (`float(usage["usd_reported"]) if _num(...) else None`) is semantically identical to the old inline check. No behavioural change for non-vision back-ends. Correct.

**(4) Tests.**
- Two new tests in `TestRuling123Reserve` cover: (a) the new `over_held` path with a follow-up `SpendLimit`, and (b) the configured vision backend reserving at its fraction (boundary ± 0.001).
- Existing RULING 123 tests are unchanged and still pass (confirmed by the 852-test suite run).
- Mutation testing: 3/3 killed (V1–V3).
- The `billed` field in the trip record now uses the pre-extracted `bill` variable rather than re-reading `usage["usd_reported"]`—equivalent, slightly cleaner.

---

## Governing-Law Compliance

| Law | Status |
|-----|--------|
| LAW 20 / M2 (thresholds are constants; hard stop) | ✓ — 0.6 is a config constant; the trip is a hard stop (reserve reverts to list for the day). |
| M12 FAIL CLOSED | ✓ — missing `usd_reported` → `bill = None` → no trip (the call still settles; the trip is a cost-control escalation, not a quality gate). |
| Smallest diff / no new renderer | ✓ — 5 lines of logic changed in `providers.py`; no new modules. |
| GPU0 only / no publishing | N/A — spend-routing change. |

No law violations found.

---

## Verdict

The change is correct, minimal, well-tested, and addresses the identified gap (vision bills that never exceeded the fraction-of-actual-usage threshold). The new `over_held` condition is properly guarded, the trip record is informative, and the follow-up reservation at full list is verified by test.

**P1_OR_WORSE: 0**

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_2319 (RULING 130 (3): the vision reserve priced from the bills)

Seats (Heimdall only): qwen3.8-27b (effort medium, 24,000), gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3
(mimo EMPTY at 32,000). P1_OR_WORSE: qwen 0, gemma 0. Cycle 1 $0.0099 of Heimdall, not capped.
qwen's three P3s, no change: (1) held == 0 cannot reach the new test: over_held needs a configured fraction, and such a
back-end's reservation is fraction x a positive upper bound; a back-end without one (Heimdall, uncapped) never trips;
(2) reserve_list_fraction_why is documentation only, as its suffix says; (3) the vision test reads the live config on
purpose: it takes every number from the configured spec (price, min_out, fraction), none typed, so a price change moves
its expectations with it. dev52: mutations V1-V3 3 of 3 killed after a control run; 40 suite files by exit code, 852
tests.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_2319/C2_STEP.diff (100 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 3814b5c..9322b8c 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -109,6 +109,8 @@
   6 |     "family": "grok"
   7 |    },
   8 |    "xai_vision:grok-4.7": {
   9 | +   "reserve_list_fraction": 0.6,
  10 | +   "reserve_list_fraction_why": "RULING 130 (3) (orchestrator 23:00 ET Nov 16): priced from the real bills: every vision bill recorded in VISUAL_CACHE.json when it was set (32), the largest $0.1752, 59.1 % of the reserve's list bound ($0.2965); median 16.7 %, p90 31.4 %. The tripwire (rulings 123 (1) / 130 (3)): the first bill above what was reserved puts the reserve back to list for the rest of the day.",
  11 |     "vendor": "xai_vision",
  12 |     "model": "grok-4.7",
  13 |     "price_usd_per_1m": [
  14 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  15 | index 21184cd..09c9f62 100644
  16 | --- a/pipeline/providers.py
  17 | +++ b/pipeline/providers.py
  18 | @@ -1028,13 +1028,18 @@ class Router:
  19 |              if backend is not None:
  20 |                  usage = usage or {}
  21 |                  f = backend.spec.get("reserve_list_fraction")      # RULING 123 (1): the tripwire, after every call
  22 | -                if _num(f) and _num(usage.get("usd_reported")) and float(usage["usd_reported"]) > float(f) * usd and \
  23 | -                        not (d.get("reserve_tripped") or {}).get(backend.name):
  24 | +                bill = float(usage["usd_reported"]) if _num(usage.get("usd_reported")) else None
  25 | +                over_list = bill is not None and _num(f) and bill > float(f) * usd
  26 | +                over_held = bill is not None and _num(f) and _num(held) and bill > float(held)   # RULING 130 (3): a
  27 | +                #   bill above what was RESERVED for the call trips too (a vision reply's usage runs past its output
  28 | +                #   cap, so its bill is a small share of the list price of its usage and the first test never fires)
  29 | +                if (over_list or over_held) and not (d.get("reserve_tripped") or {}).get(backend.name):
  30 |                      trip = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "role": role,
  31 | -                            "billed": round(float(usage["usd_reported"]), 6), "list": round(usd, 6),
  32 | +                            "billed": round(bill, 6), "list": round(usd, 6),
  33 |                              "fraction": float(f), "reserved": held,
  34 | -                            "why": f"billed above {float(f):.0%} of list: reserved at list for the rest of the day "
  35 | -                                   f"(ruling 123 (1))"}
  36 | +                            "why": (f"billed above {float(f):.0%} of list" if over_list else
  37 | +                                    f"billed above its reserve (${float(held):.4f})") +
  38 | +                                   ": reserved at list for the rest of the day (rulings 123 (1) / 130 (3))"}
  39 |                      d.setdefault("reserve_tripped", {})[backend.name] = trip
  40 |                      self.notices.append(f"RESERVE BACK TO LIST: {backend.name} {trip['why']}: billed "
  41 |                                          f"${trip['billed']:.4f}, list ${trip['list']:.4f}")
  42 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
  43 | index b627add..44e0235 100644
  44 | --- a/tests/providers/test_providers.py
  45 | +++ b/tests/providers/test_providers.py
  46 | @@ -860,6 +860,53 @@ class TestRuling123Reserve(unittest.TestCase):
  47 |              day2.call("judge", p, 12000)              # a new day's ledger: 25 % again
  48 |              self.assertEqual(g.calls, 4)
  49 |  
  50 | +    def test_ruling_130_a_bill_above_its_reserve_trips_even_below_the_fraction_of_list(self):
  51 | +        """RULING 130 (3): a reply whose usage runs past its output cap (a vision check's) bills a small share of the
  52 | +        list price of its usage, so 'billed above the fraction of list' never fires; a bill above what was RESERVED for
  53 | +        the call trips the reserve back to list for the day."""
  54 | +        with tempfile.TemporaryDirectory() as d:
  55 | +            led = self.ledger(d, 0.40)
  56 | +            v = Fake("xai_vision:v", "xai", answer="{}", price=(5, 25),
  57 | +                     usage={"in": 1000, "out": 30000, "usd_reported": 0.10})   # its usage at list: $0.755
  58 | +            v.spec["reserve_list_fraction"] = 0.6
  59 | +            r = router(d, [v], {"judge": ["xai_vision:v"]}, spend_path=led, limit_usd=0.80, limit_basis="reported")
  60 | +            p = "p" * 3000                            # upper: 1.25 x (1,200 x $5/M + 12,000 x $25/M) = $0.3825
  61 | +            r.call("judge", p, 12000)                 # reserved 0.6 x 0.3825 = $0.2295; billed $0.10: no trip
  62 | +            self.assertIsNone(json.load(open(led)).get("reserve_tripped"))
  63 | +            v._usage = {"in": 1000, "out": 30000, "usd_reported": 0.25}    # above its $0.2295 reserve, below 0.6 x $0.755
  64 | +            r.call("judge", p, 12000)
  65 | +            trip = json.load(open(led))["reserve_tripped"]["xai_vision:v"]
  66 | +            self.assertEqual((trip["billed"], trip["reserved"]), (0.25, round(0.3825 * 0.6, 6)))
  67 | +            self.assertIn("above its reserve", trip["why"])
  68 | +            led2 = self.ledger(d, 0.40, "same_day.json")                    # 0.40 + 0.2295 fits 0.70; 0.40 + 0.3825 not
  69 | +            json.dump(dict(json.load(open(led2)), reserve_tripped={"xai_vision:v": trip}), open(led2, "w"))
  70 | +            r2 = router(d, [v], {"judge": ["xai_vision:v"]}, spend_path=led2, limit_usd=0.70, limit_basis="reported")
  71 | +            with self.assertRaises(P.SpendLimit):     # tripped: at list for the rest of the day
  72 | +                r2.call("judge", p, 12000)
  73 | +
  74 | +    def test_ruling_130_the_vision_check_is_reserved_at_its_fraction(self):
  75 | +        """RULING 130 (3): the configured vision back-end reserves its fraction of the list bound, not the whole."""
  76 | +        import visual_pin as VP
  77 | +        spec = json.load(open(P.CONFIG))["backends"]["xai_vision:grok-4.7"]
  78 | +        with tempfile.TemporaryDirectory() as d:
  79 | +            v = Fake("xai_vision:grok-4.7", "xai_vision", answer="{}", price=tuple(spec["price_usd_per_1m"]),
  80 | +                     usage={"in": 3000, "out": 2000, "usd_reported": 0.01})
  81 | +            v.spec.update({k: x for k, x in spec.items() if k in ("reserve_list_fraction", "min_out")})
  82 | +            v.vision = True                           # an image back-end (the router's own test)
  83 | +            v.upper_usd = P.VENDORS["xai_vision"]("xai_vision:grok-4.7", spec, env_path=os.devnull).upper_usd
  84 | +            prompt = {"text": VP.PROMPT.format(n=12, text="x" * 400), "images": ["A"]}
  85 | +            up = v.upper_usd(prompt, 1500)
  86 | +            for spent, runs in ((0.70 - up * spec["reserve_list_fraction"] - 0.001, True),
  87 | +                                (0.70 - up * spec["reserve_list_fraction"] + 0.001, False)):
  88 | +                led = self.ledger(d, spent, f"l{spent:.4f}.json")
  89 | +                r = router(d, [v], {"visual_check": ["xai_vision:grok-4.7"]}, spend_path=led, limit_usd=0.70,
  90 | +                           limit_basis="reported")
  91 | +                if runs:
  92 | +                    r.call("visual_check", prompt, 1500)
  93 | +                else:
  94 | +                    with self.assertRaises(P.SpendLimit):
  95 | +                        r.call("visual_check", prompt, 1500)
  96 | +
  97 |      def test_only_a_back_end_that_names_the_fraction_is_reserved_below_list(self):
  98 |          with tempfile.TemporaryDirectory() as d:
  99 |              led = self.ledger(d, 0.69)
 100 | 
```

---

pp-selectid: RULING 130 (3) (orchestrator 23:00 ET Nov 16), verbatim: "Vision checks reserve at list ($0.30 for two that
billed $0.1245): price the reserve from the real bills with the ruling 123 tripwire." Files: pipeline/providers.py,
pipeline/model_providers.json, tests/providers/test_providers.py.

THE BILLS (measured from every vision bill recorded in tests/package/proof/VISUAL_CACHE.json: 32): min $0.0072, median
$0.0496, p90 $0.0932, max $0.1752; as a share of the reserve's list bound ($0.2965: 1.25 x list at the call's real
output cap, ruling 121 (1)): median 16.7 %, p90 31.4 %, max 59.1 %. A vision reply's usage runs PAST its output cap
(max_out 8,000; recorded "out" up to 28,400 tokens), so every bill is only 24-29 % of the list price of its USAGE.

THE CHANGE:
(a) model_providers.json: xai_vision:grok-4.7 gains reserve_list_fraction 0.6 (the largest bill on record is 59.1 % of
    the list bound), with its why. UNCHANGED code reads it: Router._reserve_fraction (providers.py:1002 in the copy, ruling
    123 (1), 8d878e7f: the fraction unless the day's ledger has reserve_tripped for that back-end) and the reserve call
    (providers.py:1396: key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)).
(b) providers.Router._settle's tripwire (ruling 123 (1)): it fired only when a bill exceeded the fraction times the
    list price of the call's USAGE, which a vision bill never does (24-29 %). It now ALSO fires when the bill exceeds the
    amount RESERVED for that call (held, the reservation it settles). Either way: reserve_tripped for that back-end in
    the day's ledger (the reserve back to list for the rest of the day), the notice, and the record's why names which
    test fired. For Grok (fraction 0.25, bills about $0.01 against reserves of $0.06-0.12) nothing changes in practice.
    The worst overrun past the stop is one call's bill above its reserve, once a day, before the trip.

TESTS (TestRuling123Reserve): new: a bill above its reserve but below the fraction of list trips (and the same day's
next call is reserved at list); the configured vision back-end is reserved at its fraction (a call fits a limit just
above fraction x upper and is refused just below it). The ruling 123 tests unchanged and passing. Mutations V1-V3 after a
control run: 3 of 3 killed. Suites: 40 files by exit code, 852 tests.

PLEASE CHECK: (1) the fraction against the bills; (2) the tripwire's new test (bill vs the held reservation) and that
it cannot fire on a call that reserved nothing; (3) that nothing else changes for the other back-ends; (4) the tests.


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
