# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0707
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 157 s finish=stop usage in 8625 / out 4758 usd~0.097 (upper-bound price)

# Spend-Guard Audit — Ruling 48 (limit_basis="reported")

Scope: only the 170-line diff provided. Everything below is verified against the diff text; where the diff doesn't show the underlying code (e.g. `_settle`, `_ledger`, the `router()` test helper), I say so.

---

## What the diff establishes (verified)

- `providers.py:15-17` — `limit_basis` validated at construction: only `"estimate"` / `"reported"`; anything else raises `ValueError`. Default `"estimate"` preserves old behaviour for every caller that doesn't pass it. ✔
- `providers.py:25-32` — `_basis_total`: reported basis = `usd_reported + usd_unreported_estimate`; estimate basis = `usd_estimate`. ✔
- `providers.py:34-39` — `spent()` reads the basis under `self._lock()`, returns `0.0` when `spend_path` is unset. ✔
- `providers.py:41-56` — `_reserve` now compares `spent (on the basis) + held + upper > limit_usd`. The reservation itself is still the price-table `upper` (docstring, line 44-45: "The reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late"). The lock, the `reserved` dict, the key format, and the `round(upper, 6)` booking are untouched by the diff. ✔
- `proof_ly.py:115-118` — `LY_LIMIT_USD = 12.0`, `LY_LIMIT_BASIS = "reported"`, `LY_STOP_USD = 10.0`; the driver's Router passes the basis (lines 127-128). ✔
- `proof_ledger.py:66-76` — Router constructed with the basis; pre-build stop check `spent0 >= PL.LY_STOP_USD` → REFUSED, exit 3, before any paid call; otherwise the running total is logged. Post-build, `spend_ruling_48 {before, after, cap, stop, basis}` is written into `package.json` (lines 84-87). ✔

---

## Findings

### P1-1 — `proof_ledger.py:84` — `res["spend_ruling_48"] = ...` can raise `KeyError`/`TypeError` when the build produced no package, killing the post-build accounting

`proof_ledger.py:80-83`:

```python
    else:
        say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
+   res["spend_ruling_48"] = {"before": round(spent0, 4), "after": round(router.spent(), 4), "cap": PL.LY_LIMIT_USD,
+                             "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
```

The assignment is outside the `if/else`, so it runs in both branches — good, that's the intent. But it assumes `res` is a dict. From the diff alone I cannot verify that `PK.build` always returns a dict (it might return `None` on some failure path, in which case `res.get('why_none')` at line 83 would already have failed, which weakly suggests `res` is always a dict — but that's inference, not verification). If `PK.build` can return `None`, the diff turns a graceful "no package" outcome into a crash after the paid calls, losing the spend record the ruling demands ("Keep the running total on STATE line 1 with every build").

Additionally, even if `res` is a dict, note the ruling says the running total goes on **STATE line 1**; the diff logs it via `say(...)` (lines 75-76, 86-87) and into `package.json`. Whether `say()` writes to STATE line 1 depends on code not in the diff — I cannot verify that the ruling's STATE requirement is literally satisfied. Flagging as unverifiable-from-diff, not as a defect.

**Scenario:** `PK.build` returns `None` → line 84 raises `AttributeError`/`TypeError` → `package.json` never written, `logf.close()` (line 90) never reached, post-build spend never recorded — exactly the accounting the ruling asks to keep.

**Fix (1 line):** `res = res or {}` before line 84, or guard the assignment.

### P1-2 — `providers.py:31` — reported-basis total silently treats missing ledger keys as 0.0, diverging from the estimate basis's strictness

```python
+        if self.limit_basis == "reported":
+            return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
+        return float(d["usd_estimate"])
```

The estimate basis uses `d["usd_estimate"]` (KeyError → fail-closed, consistent with M12). The reported basis uses `.get(..., 0.0)`: an old ledger written before this diff that lacks `usd_reported`/`usd_unreported_estimate` reads as **$0.00 spent**, so `_reserve` will happily admit calls until reservations alone pass the cap, and `spent()` reports $0.00.

Is that a real scenario? The background says `_settle` maintains all three totals, and the measured ledger (usd_estimate $39.49, usd_reported $3.46, usd_unreported_estimate $1.81) evidently has them. But the diff's own test writes all keys explicitly (line 145-146), so the test never exercises a legacy ledger. Whether any ledger in this order predates the `usd_reported` fields is not verifiable from the diff. If one does, the guard under-counts — the opposite failure direction of the docstring's "can only stop early, never late" claim, which that claim (line 44-45) only makes about *reservations*, so the docstring is technically consistent

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 8688 / out 384 usd~0.053 (upper-bound price)

**P2: pipeline/providers.py:30** (and test at tests/providers/test_providers.py:154)  
The reported basis computes `usd_reported + usd_unreported_estimate` (or falls back to `usd_estimate` for the default "estimate" basis). The diff verifies that every exercised call is counted exactly once under the chosen basis, that a paid call is never charged zero, that the file lock + reservation logic is untouched, and that the guard can only stop early. However, `_settle` (which writes the three ledger fields) is not present in the diff, so correct population for every vendor reply path cannot be verified here.

**P2: tests/package/proof_ledger.py:70** (`if spent0 >= PL.LY_STOP_USD`)  
Implements "at $10 reported stop" by refusing to *start* a build (exit 3, no paid calls) while the hard Router cap remains $12 on the reported basis. A build started below $10 can still spend up to the $12 cap (subject to its own per-build budget). The ruling text is satisfied by this reading; I do not read it differently from the diff + supplied orchestrator wording.

**P2: tests/package/proof_ly.py:116**  
LY_LIMIT_USD / LY_LIMIT_BASIS / LY_STOP_USD constants and all Router construction sites are updated consistently with the new ruling (including the spend_ruling_48 record written to package.json). No other call sites outside the spend-guard path are altered.

No P0 or P1 findings. All other callers retain the old "estimate" default; validation rejects unknown basis values; the test exercises the exact scenario described in Ruling 48 (old estimate 39.5 refused, reported 5.27 allowed, mix of reported/unreported calls counted once, reservations cleared).

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 19 s finish=stop usage in 9491 / out 1170 usd~0.046 (upper-bound price)

# Audit: pp-selectid-0707 (C1_STEP.diff)

## P0 Findings
None.

## P1 Findings
None.

## P2 Findings

**1. `tests/providers/test_providers.py:154` — Fragile floating-point assertion**
The test asserts `self.assertAlmostEqual(r.spent(), 5.27, places=6)`. The ledger is seeded with `usd_reported: 3.46` and `usd_unreported_estimate: 1.81`. In IEEE 754 double-precision, `3.46 + 1.81` evaluates to `5.2700000000000005`. While `assertAlmostEqual` with `places=6` (tolerance `5e-7`) will pass, this is brittle. If the ledger values are ever updated to slightly different decimals (e.g., `3.461` and `1.809`), the sum might drift just enough to fail a strict `places=6` check if the error exceeds `5e-7`. It is safer to use `places=4` or compare against the explicit sum `3.46 + 1.81`.

**2. `pipeline/providers.py:34-39` — `spent()` returns 0.0 when `spend_path` is None**
The `spent()` method returns `0.0` if `self.spend_path` is not set. This is consistent with `_reserve` (which skips reservation if `spend_path` is None), but it means that a Router constructed without a `spend_path` will report `spent() == 0.0` regardless of actual usage. This is likely intentional (no ledger = no tracking), but it is a subtle behavior: if a caller mistakenly omits `spend_path` while expecting spend tracking, they will see `0.0` and no `SpendLimit` will ever be raised. The diff does not change this behavior, but it is worth noting that `spent()` is now a public API surface that silently returns zero when unconfigured.

**3. `tests/package/proof_ledger.py:70-74` — Stop check uses `>=` on `spent0`**
The pre-build check is `if spent0 >= PL.LY_STOP_USD`. This correctly implements "at $10 reported stop" by refusing to *start* a build when the running total is at or above $10.00. A build that starts at $9.99 may spend up to the $12.00 hard cap (bounded by its own per-build budget). This matches the ruling's intent: the $10 threshold is a *start* gate, not a mid-build abort. No issue, but the distinction is critical and correctly implemented.

## Verification of Key Requirements

1. **Reported basis counts every call exactly once:**
   - `_basis_total` returns `usd_reported + usd_unreported_estimate`.
   - Per the background, `usd_reported` covers calls where the vendor reports a cost, and `usd_unreported_estimate` covers calls where it does not (STT, abandoned calls). These are disjoint sets maintained by `Router._settle`.
   - A paid call is never counted in both, and never in neither. **Verified.**

2. **Lock and reservation logic unchanged:**
   - `_reserve` still acquires `self._lock()`, reads the ledger, sums `reserved`, and compares `spent + held + upper > limit_usd`.
   - The only change is that `spent` is now `self._basis_total(d)` instead of `d["usd_estimate"]`.
   - Reservations remain price-table upper bounds. **Verified.**

3. **Nothing else changes for callers that do not pass `limit_basis`:**
   - The default is `limit_basis="estimate"`, which returns `d["usd_estimate"]` from `_basis_total` — identical to the old behavior.
   - The `ValueError` guard only triggers for invalid strings, not for the default. **Verified.**

4. **Build can never start at or over $10; hard cap is $12:**
   - `proof_ledger.py` exits with code 3 if `spent0 >= LY_STOP_USD` ($10.00).
   - `Router` raises `SpendLimit` if `spent + reserved + upper > limit_usd` ($12.00).
   - **Verified.**

5. **"At $10 reported stop" interpretation:**
   - The ruling says "At $10 reported stop and tell me." The implementation stops *starting* new builds at $10, but allows a running build to continue to the $12 hard cap. This is a reasonable reading: "stop" refers to initiating new work, not aborting in-flight work. The $12 cap is the absolute boundary. **No issue.**

## SHIP: yes

The diff correctly implements Ruling 48. The spend guard now counts vendor-reported dollars (plus estimates for unreported calls) against a $12.00 cap, with a $10.00 pre-build stop. The default behavior for other callers is unchanged. The test coverage is adequate, with one minor floating-point fragility (P2) that does not block shipping.

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0707 (RULING 48: the spend cap on vendor-reported dollars): cycle 1 consensus

**Run.** Verdicts:
- grok: no P0 / P1, "SHIP: yes";
- qwen: no P0 / P1, "SHIP: yes";
- glm: no P0, "SHIP: yes with conditions" (P1-1, P1-2).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | glm P1-2: the reported basis reads a missing usd_reported / usd_unreported_estimate as 0.0, a silent fail-open on a legacy ledger | _basis_total refuses (SpendLimit) a ledger that has calls but neither key. _settle creates one of the two keys on every settled call, a free one included, so only a ledger that predates them can lack both. Tested. |
| F2 | glm P1-1, the part that holds: after the build, router.spent() raises SpendLimit on an unreadable ledger, before package.json is written, so the build's record would be lost | The post-build read is caught. spend_ruling_48.after then records "unreadable: ...", and the record is always written. |

## Refuted (verified from the code)

| # | claim | the code |
|---|---|---|
| R1 | glm P1-1: `res["spend_ruling_48"] = ...` raises when the build produced no package | res is the dict PK.build returns on every path (out). The line before it already does res.update(...). A build that raises never reaches either line, as before. |

## Verification

- test_providers 15 OK (the ruling-48 test extended with F1); every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0707/C2_STEP.diff (181 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index e65bca1..49bfc9f 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -501,11 +501,14 @@ class Router:
   6 |      spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
   7 |  
   8 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
   9 | -                 local_llm=None, chains=None):
  10 | +                 local_llm=None, chains=None, limit_basis="estimate"):
  11 |          with open(config) as f:
  12 |              self.config = json.load(f)
  13 |          self.env_path = env_path or ENV_PATH
  14 |          self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
  15 | +        if limit_basis not in ("estimate", "reported"):
  16 | +            raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  17 | +        self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  18 |          self.down, self.notices = {}, []
  19 |          self.backends = {}
  20 |          for name, spec in self.config["backends"].items():
  21 | @@ -575,16 +578,37 @@ class Router:
  22 |          with self._lock():
  23 |              return float(self._ledger()["usd_estimate"])
  24 |  
  25 | +    def _basis_total(self, d):
  26 | +        """The ledger total limit_usd is checked against. "estimate": the price-table estimate of every call (an upper
  27 | +        bound). "reported" (ruling 48, orchestrator 2026-11-13 07:02): the vendors' own reported dollars, plus the
  28 | +        estimate for each call whose vendor reports none (usd_unreported_estimate: those calls, and a call abandoned at
  29 | +        its deadline, booked at its upper bound)."""
  30 | +        if self.limit_basis == "reported":
  31 | +            if d.get("calls", 0) and "usd_reported" not in d and "usd_unreported_estimate" not in d:
  32 | +                raise SpendLimit("the ledger has calls but keeps no vendor-reported figures: the reported basis "
  33 | +                                 "cannot be read (fail closed; audit 0707 C1, glm P1-2)")
  34 | +            return float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
  35 | +        return float(d["usd_estimate"])
  36 | +
  37 | +    def spent(self):
  38 | +        """The ledger's total on this router's limit basis (0.0 with no ledger; raises SpendLimit when unreadable)."""
  39 | +        if not self.spend_path:
  40 | +            return 0.0
  41 | +        with self._lock():
  42 | +            return self._basis_total(self._ledger())
  43 | +
  44 |      def _reserve(self, b, upper):
  45 |          """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
  46 | -        SpendLimit when spent + reserved + this call's upper bound would pass the limit."""
  47 | +        SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
  48 | +        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late."""
  49 |          if not self.spend_path or b.free():
  50 |              return None
  51 |          with self._lock():
  52 |              d = self._ledger()
  53 |              held = sum(float(x) for x in d["reserved"].values())
  54 | -            if d["usd_estimate"] + held + upper > self.limit_usd:
  55 | -                raise SpendLimit(f"spend estimate {d['usd_estimate']:.2f} USD + reserved {held:.2f} + this call's upper "
  56 | +            spent = self._basis_total(d)
  57 | +            if spent + held + upper > self.limit_usd:
  58 | +                raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's upper "
  59 |                                   f"bound {upper:.2f} > the limit {self.limit_usd} USD")
  60 |              key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
  61 |              d["reserved"][key] = round(upper, 6)
  62 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  63 | index 44aaa8e..637e675 100644
  64 | --- a/tests/package/proof_ledger.py
  65 | +++ b/tests/package/proof_ledger.py
  66 | @@ -121,7 +121,15 @@ def main(argv=None):
  67 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
  68 |                    f, indent=1, default=str)
  69 |      router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
  70 | -                      chains=PL.chains())
  71 | +                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains())
  72 | +    spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
  73 | +    if spent0 >= PL.LY_STOP_USD:
  74 | +        say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
  75 | +            f"vendor reports none), at or over the ${PL.LY_STOP_USD:.2f} stop: no build starts; the orchestrator decides")
  76 | +        logf.close()
  77 | +        return 3
  78 | +    say(f"  spend (ruling 48): ${spent0:.2f} of ${PL.LY_LIMIT_USD:.2f} vendor-reported before this build (no build "
  79 | +        f"starts at ${PL.LY_STOP_USD:.2f})")
  80 |      own, used = PL.meter(router), PL.reply_meter(router)
  81 |      t0 = time.time()
  82 |      res = PK.build(router, moments, sources, ctx, delivered=delivered, optout=M.optout_ids(), log=say,
  83 | @@ -144,6 +152,14 @@ def main(argv=None):
  84 |              say(f"PIN REFUSED: {e}")
  85 |      else:
  86 |          say(f"no package ({res.get('why_none')}); usable {res['usable']}, cleared {res['prescreen'].get('cleared')}")
  87 | +    try:                                         # the record is written whatever the ledger says (audit 0707 C1)
  88 | +        after = round(router.spent(), 4)
  89 | +    except Exception as e:                       # noqa: BLE001
  90 | +        after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
  91 | +    res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
  92 | +                              "stop": PL.LY_STOP_USD, "basis": PL.LY_LIMIT_BASIS}
  93 | +    say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
  94 | +        f"vendor-reported after this build (before it: ${spent0:.2f})")
  95 |      with open(os.path.join(out_dir, "package.json"), "w") as f:
  96 |          json.dump(res, f, indent=1, default=str)
  97 |      logf.close()
  98 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  99 | index 75193f6..c958eab 100644
 100 | --- a/tests/package/proof_ly.py
 101 | +++ b/tests/package/proof_ly.py
 102 | @@ -18,8 +18,9 @@ is out too. What is left:
 103 |  CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
 104 |  
 105 |  SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
 106 | -vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). Its guard is LY_LIMIT_USD by the
 107 | -estimate (an upper bound). No budget was stated at 20:30; the cap is the builder's, and STATE says so.
 108 | +vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). RULING 48 (orchestrator 07:02 Nov 13):
 109 | +its guard is LY_LIMIT_USD on VENDOR-REPORTED dollars, the estimate counted only for a call whose vendor reports none
 110 | +(Router limit_basis="reported"); at LY_STOP_USD no new build starts (proof_ledger) and the orchestrator is told.
 111 |  
 112 |  Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
 113 |  """
 114 | @@ -46,10 +47,10 @@ import speakers as SP  # noqa: E402
 115 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
 116 |  OUT = os.path.join(HERE, "proof")
 117 |  SPEND = os.path.join(OUT, "SPEND_LY.json")
 118 | -LY_LIMIT_USD = 40.0                # the price-table estimate (an upper bound): xAI's own figure ran 1/8 of it on
 119 | -                                   # this order's first calls (estimate $0.636 vs reported $0.078 for 3 grok calls),
 120 | -                                   # so about $5 real; each paid call also RESERVES its upper bound (~$0.26-0.96)
 121 | -                                   # while in flight, and three workers run concurrently
 122 | +LY_LIMIT_USD = 12.0                # ruling 48 (07:02 Nov 13): $12.00 VENDOR-REPORTED in total for this order (the
 123 | +LY_LIMIT_BASIS = "reported"        # old $40 cap by the price-table estimate read ~12x high: $39.49 = $3.46 reported);
 124 | +LY_STOP_USD = 10.0                 # the estimate counts only where a vendor reports none. At $10 no build starts.
 125 | +                                   # Each paid call still RESERVES its price-table upper bound while in flight.
 126 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 127 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
 128 |          "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
 129 | @@ -274,7 +275,8 @@ def main(argv=None):
 130 |      if a.table:
 131 |          print(table())
 132 |          return 0
 133 | -    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD, chains=chains())
 134 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD,
 135 | +                      limit_basis=LY_LIMIT_BASIS, chains=chains())
 136 |      own = meter(router)
 137 |      used = reply_meter(router)
 138 |      os.makedirs(a.work_dir, exist_ok=True)
 139 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
 140 | index fca9414..fb94590 100644
 141 | --- a/tests/providers/test_providers.py
 142 | +++ b/tests/providers/test_providers.py
 143 | @@ -185,6 +185,37 @@ class TestRouter(unittest.TestCase):
 144 |              a.answer = '{"ok": 1}'
 145 |              self.assertEqual((r.call("write", "p").text, a.calls), ('{"ok": 1}', 2))
 146 |  
 147 | +    def test_ruling_48_the_limit_counts_vendor_reported_dollars(self):
 148 | +        """Ruling 48 (07:02 Nov 13): the cap counts the vendors' own reported dollars, plus the estimate for a call
 149 | +        whose vendor reports none; the price-table estimate (12x high on xAI) no longer binds."""
 150 | +        with tempfile.TemporaryDirectory() as d:
 151 | +            led = os.path.join(d, "SPEND.json")
 152 | +            json.dump({"usd_estimate": 39.5, "calls": 400, "by_backend": {}, "by_role": {}, "reserved": {},
 153 | +                       "usd_reported": 3.46, "usd_unreported_estimate": 1.81}, open(led, "w"))
 154 | +            a = Fake("openai:x", "openai", answer="{}", usage={"in": 1000, "out": 100})        # no vendor figure
 155 | +            rep = Fake("openai:y", "openai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
 156 | +            p = "p" * 50_000
 157 | +            with self.assertRaises(P.SpendLimit):                   # the old basis: 39.5 + the upper bound > 40
 158 | +                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=40).call("write", p)
 159 | +            r = router(d, [a, rep], {"write": ["openai:x"], "judge": ["openai:y"]}, spend_path=led, limit_usd=12,
 160 | +                       limit_basis="reported")
 161 | +            self.assertAlmostEqual(r.spent(), 5.27, places=6)
 162 | +            r.call("write", p)                                      # 5.27 + its upper bound < 12: it runs
 163 | +            self.assertAlmostEqual(r.spent(), 5.27 + 0.02, places=6)                 # no figure: its estimate counts
 164 | +            r.call("judge", p)
 165 | +            self.assertAlmostEqual(r.spent(), 5.29 + 0.001, places=6)                # a figure: only the figure counts
 166 | +            self.assertGreater(json.load(open(led))["usd_estimate"], 39.5)
 167 | +            r.limit_usd = r.spent() + 0.05
 168 | +            with self.assertRaises(P.SpendLimit):                   # spent + this call's upper bound > the limit
 169 | +                r.call("write", p)
 170 | +            self.assertEqual(json.load(open(led))["reserved"], {})
 171 | +            with self.assertRaises(ValueError):
 172 | +                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_basis="dollars")
 173 | +            json.dump({"usd_estimate": 1.0, "calls": 3, "by_backend": {}, "by_role": {}, "reserved": {}},
 174 | +                      open(led, "w"))                       # calls, but no reported figures: never a silent 0.0
 175 | +            with self.assertRaises(P.SpendLimit):
 176 | +                r.spent()
 177 | +
 178 |      def test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit(self):
 179 |          with tempfile.TemporaryDirectory() as d:
 180 |              led = os.path.join(d, "SPEND.json")
 181 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging). This branch's builds call
paid model vendors through providers.Router, which books every call in a spend ledger (SPEND_LY.json) and refuses a
call that would pass a limit. Your role: a strict reviewer of the spend guard.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- The ledger keeps, per call, the price-table ESTIMATE (usd_estimate: every call, an upper bound) and, separately, the
  vendor's OWN reported cost where the reply carries one (usd_reported: xAI cost_in_usd_ticks, Heimdall usage.cost),
  else the estimate for that call (usd_unreported_estimate: calls with no vendor figure, e.g. speech-to-text, and calls
  abandoned at a deadline, booked at their upper bound). Router._settle maintains all three.
- Before a paid call, Router._reserve reserves the call's price-table upper bound under a file lock and refuses it
  (SpendLimit) when spent + reserved + upper > limit_usd. Until this diff, "spent" was always usd_estimate.
- The build driver (tests/package/proof_ledger.py) and the saved-runs driver (proof_ly.py) construct the Router for
  this order with limit_usd = LY_LIMIT_USD (was 40.0, by the estimate).

The order this diff implements (ORCHESTRATOR RULING 48, 07:02 ET Nov 13, verbatim): "SPEND. The cap is on
VENDOR-REPORTED dollars, not the price-table estimate (the estimate reads 12x high: $40 estimated = $3.46 reported).
New cap for this fresh batch: $12.00 vendor-reported in total, from where you stand ($3.46 used). For calls where a
vendor reports no cost, count the estimate for that call only. Keep the running total on STATE line 1 with every
build: reported / cap. At $10 reported stop and tell me."
- Measured before this diff: usd_estimate $39.49, usd_reported $3.46, usd_unreported_estimate $1.81 (STT and calls
  abandoned at the 300 s deadline). So the running total by the ruling's own rule is $5.26, not $3.46; STATE says so.

The change:
1. pipeline/providers.py:
   - Router(..., limit_basis="estimate"): "estimate" keeps the old behaviour for every other caller (the default);
     "reported" checks usd_reported + usd_unreported_estimate; anything else raises ValueError.
   - _basis_total(d) computes the basis; spent() returns it under the ledger lock.
   - _reserve compares spent-on-the-basis + reserved + upper with limit_usd. Reservations stay price-table upper
     bounds, so the guard can only stop early, never late.
2. tests/package/proof_ly.py: LY_LIMIT_USD = 12.0, LY_LIMIT_BASIS = "reported", LY_STOP_USD = 10.0; proof_ly's own
   Router uses the basis.
3. tests/package/proof_ledger.py (one build): the Router uses the basis. Before the build: at or over LY_STOP_USD it
   logs REFUSED and exits 3, with no paid call. Else it logs the running total. After the build it logs and records
   spend_ruling_48 {before, after, cap, stop, basis} in package.json. A build that starts below $10 may still spend
   up to its own per-build budget (ruling 41: $3.00 reported for the search); the Router's $12 cap is the hard stop.
4. tests/providers/test_providers.py: one new test. The old basis refuses at 39.5 + upper > 40. The reported basis
   reads 5.27 and lets a call run. A call with no vendor figure adds its estimate; a call with a figure adds only the
   figure. The limit refuses at spent + upper; reservations are released; an unknown basis is refused.

Check in particular:
- that the reported basis counts every call exactly once (reported OR its estimate), never zero for a paid call, and
  that the lock and reservation logic are unchanged;
- that nothing else changes for callers that do not pass limit_basis;
- that a build can never start at or over $10, and that the hard cap is $12 on the ruling's basis;
- whether "at $10 reported stop" is satisfied by refusing to START a build at $10 while a running build may continue
  to the $12 cap (bounded by its own $3 reported search budget). Say so if you read the ruling differently.

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
