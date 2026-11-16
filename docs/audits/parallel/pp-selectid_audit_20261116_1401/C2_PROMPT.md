# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1401
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 266 s finish=stop usage in 9204 / out 4247 usd_reported=0.000812 usd~0.091 (upper-bound price)

The code implements RULING 123 (1) to reduce the budget reservation for the Grok backend to 25% of its list price, with a "tripwire" that reverts the reservation to 100% for the remainder of the day if any single call's reported cost exceeds that 25% threshold.

### Analysis

1.  **Tripwire Logic**: In `Router._settle`, the condition `float(usage["usd_reported"]) > float(f) * usd` correctly compares the actual billed amount against the fraction of the list price (`usd` is the list-price estimate passed into `_settle`). The check `not (d.get("reserve_tripped") or {}).get(backend.name)` ensures the trip is recorded only once per ledger day.
2.  **Persistence**: The trip state is stored in the ledger (`d["reserve_tripped"]`), which is the canonical source of truth for the day's spend. `Router._reserve_fraction` correctly reads this state to determine whether to apply the fraction or revert to `None` (which triggers the full list-price reservation in `Router.call`).
3.  **Specificity**: The logic is gated by the presence of `reserve_list_fraction` in the backend's spec. This ensures that only the xAI reasoning backend (as configured in `model_providers.json`) is affected, leaving other backends at 100% reservation.
4.  **Safety/Fail-Closed**: If `spend_path` is missing or the spec is malformed, `_reserve_fraction` returns `None`, and `Router.call` defaults to the full `upper` (list price) reservation. This prevents under-reserving budget in ambiguous states.
5.  **Tests**: `TestRuling123Reserve` comprehensively covers:
    *   Successful calls staying under the threshold.
    *   A call exceeding the threshold triggering the tripwire.
    *   Subsequent calls being refused due to the reverted (higher) reservation.
    *   The reset of the tripwire upon starting a new day's ledger.
    *   Isolation (ensuring non-fractional backends remain at list price).

### Findings

No defects found. The implementation strictly adheres to the orchestrator's order and the governing laws of the system.

P1_OR_WORSE: 0

## MIMO-V2.6-FLASH-RL — CYCLE 1 OUTPUT
# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 276 s finish=stop usage in 8644 / out 17135 usd_reported=0.001862 usd~0.283 (upper-bound price)

# CODE AUDIT — pp-selectid (RULING 123 (1): Grok reserve at 25 % with tripwire)

Reviewer pass on the four requested checks, plus a general sweep. Findings are tagged by severity.

---

## CHECK (1): The tripwire's comparison, and that it cannot be missed

**What is correct:**
- The comparison `float(usage["usd_reported"]) > float(f) * usd` matches the order's operative threshold — "bills above 25 % of the **list** price of what it used" — where `usd` is the list cost of the call's usage (confirmed by the test asserting `trip["list"] == 0.055`, the true list cost of 1 000 × $5/M + 2 000 × $25/M, not the reserved 0.095 625). The order's looser phrase "compare what was billed with what was reserved" is correctly resolved in favour of the explicit "above 25 % of list" rule.
- `usage = usage or {}` executes before `usage.get(...)`, so a `None` usage cannot crash the settle path.
- The `and` chain short-circuits safely: no fraction → no trip attempt; non-numeric billed → no trip attempt; already tripped → no duplicate record.
- The trip record is written into the same ledger dict `d` that `_reserve_fraction` reads, under the same `self._lock()`, and is persisted (the test reads it back from the file). `held` is captured from `d["reserved"].pop` before use, so `reserved` in the record is the actual amount held for the offending call.
- The trip fires during the settle of the offending call itself, so the offending call is the accepted "one call's overshoot"; every subsequent `_reserve_fraction` read sees the trip.

**Vectors by which a trip could be missed:**

- **[P3]** An abandoned / `unreported` call (no numeric `usd_reported` in usage) that in fact bills above 25 % of list never trips the wire. The order says "after every outside call"; unreported calls are outside calls whose billing we simply do not know, and the ledger carries a `usd_unreported_estimate` that the tripwire ignores. Evidence base is 127/127 reported calls, so likelihood is low, but the gap is real and the failure direction is the unsafe one (reserve stays at 25 % → a later, larger overshoot).
- **[P3]** `_settle(key, backend=None, ...)` skips the tripwire block entirely (`if backend is not None:`). If any settle path for an xAI call passes `backend=None`, that call's trip is silently missed. This is pre-existing structure (the `by_backend` accounting has the same gate), but the order's "after every outside call" makes it worth confirming that all xAI settle paths pass the backend.
- **[P3]** Race window: `_reserve_fraction(b)` (lock acquired and released) and `self._reserve(...)` (separate lock acquisition) are not atomic with respect to a concurrent `_settle` trip write. A trip landing between the two leaves one in-flight call reserved at 25 % after the trip is recorded. This is within the order's explicitly accepted "one call's overshoot" tail, but it is not literally "at once"; closing it would mean re-checking the trip inside `_reserve` under the same lock.
- **[P3]** If `_settle`'s ledger persistence fails after the in-memory trip write, the trip may be lost for the day. This inherits the ledger's existing write-failure behaviour (which raises, fail-closed), so it is consistent with M12, but the trip specifically is a fail-open artifact.

No P0/P1 here: the comparison itself is right, and every miss vector either matches the spec's wording or fails in the conservative direction.

---

## CHECK (2): That the trip holds for the day

**Correct.**
- `_reserve_fraction` reads the ledger under `self._lock()` and returns `None` (list reserve) whenever `reserve_tripped[b.name]` is present — so from the moment of the trip, every subsequent reserve for that backend in that ledger's day is at list.
- The trip is persisted in the ledger file, so it survives across `Router` instances pointed at the same day's ledger.
- Day rollover: `proof_ly.day_ledger` gives one ledger per day (21:10 ET → 21:10 ET); a new day's ledger has no `reserve_tripped` key, and `(d.get("reserve_tripped") or {}).get(...)` handles the absent key gracefully (backward compatible with pre-change ledgers). The test's day-2 leg proves the fraction re-applies on a fresh ledger.
- The trip is recorded once (guarded by `not ... .get(backend.name)`), matching "the first call that bills above 25 %".

**[P3]** Test nit: the day-2 leg does not assert day-2's ledger state. With the mutated `g._usage` (`usd_reported=0.02`), day 2's single call actually trips day-2's ledger too during settle — the test neither expects nor checks this. The claim under test ("a new day's ledger: 25 % again") is still proven by the call running, but the unasserted side effect is worth a line of assertion for clarity.

No P0/P1.

---

## CHECK (3): That nothing but the named back-end changes

**Correct.**
- `model_providers.json`: exactly one key added, to the xAI rea

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 70 s finish=stop usage in 8815 / out 5781 usd_reported=0.004532 usd~0.113 (upper-bound price)

I will analyze the provided diff for `pipeline/providers.py` and `tests/providers/test_providers.py` against the specific instructions in "RULING 123 (1)" and the general "Governing Laws" (specifically M12 Fail Closed and Law 20/22 regarding constants and hard stops).

### Analysis of `pipeline/providers.py`

**1. `_reserve_fraction` method (Lines 23-33)**
*   **Logic:** Returns the fraction if `reserve_list_fraction` is in the spec, `_num` is valid, and `spend_path` exists. It checks the ledger for `reserve_tripped`.
*   **Potential Issue:** It accesses `self._ledger()` inside `self._lock()`. This is consistent with other ledger operations.
*   **Fail Closed (M12):** If `spend_path` is None, it returns `None` (which means reserve at list price). This is safe. If the ledger read fails, `_ledger()` likely raises or returns a default. Assuming `_ledger()` is robust (as implied by existing code structure), this is acceptable.

**2. `_settle` method modification (Lines 38-56)**
*   **Logic:** After popping the reservation `held`, it checks if the backend has `reserve_list_fraction`.
*   **Comparison:** `float(usage["usd_reported"]) > float(f) * usd`.
    *   `usd` here is the argument passed to `_settle`. Looking at the call site in `Router.call` (not fully shown but implied by context), `usd` is typically the *list price* estimate or the *actual* cost?
    *   Let's look at the tripwire logic: "compare what was billed with what was reserved... first call that bills above 25 % of list".
    *   The code calculates `float(f) * usd`. If `usd` is the *list price* of the usage, then `0.25 * usd` is the threshold.
    *   The condition is `usage["usd_reported"] > threshold`.
    *   **Critical Check:** Does `usd` passed to `_settle` represent the *list price* of the tokens used?
        *   In `Router.call` (Line 63-66), `upper = b.upper_usd(...)`. This is the list price upper bound.
        *   The reservation `key` is created with `round(upper * frac, 6)`.
        *   When `_settle` is called, it needs to know the *list price* of the actual usage to compare against the fraction.
        *   The code uses `usd` (the parameter). We must verify that `usd` passed to `_settle` is indeed the list price of the *actual* usage, not the reserved amount.
        *   Looking at standard patterns in such routers: `_settle` usually receives the actual cost or the list cost of the actual tokens.
        *   The trip record stores `"list": round(usd, 6)`. This implies `usd` is the list price.
        *   The comparison is `billed > fraction * list`. This matches the ruling: "bills above 25 % of list".
*   **Locking:** The write to `d["reserve_tripped"]` happens *outside* the `self._lock()` block shown in the snippet?
    *   Wait, let's look at the indentation in the diff.
    *   Lines 44-56 are inside the `if backend is not None:` block.
    *   Is this block inside a lock?
    *   The diff shows:
        ```python
        def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
            try:
                # ...
                d["reserved"].pop(key, None) # Line 43
                if backend is not None:
                    usage = usage or {}
                    f = backend.spec.get("reserve_list_fraction")
                    if _num(f) and _num(usage.get("usd_reported")) and ...:
                        # ...
                        d.setdefault("reserve_tripped", {})[backend.name] = trip # Line 54
        ```
    *   The `try` block usually wraps the ledger access. In the previous code (Line 39-41), `d` is obtained. If `d` is a reference to the ledger dict, and the ledger is protected by a lock *during the read/write*, we need to ensure the write to `reserve_tripped` is atomic with the read of `d`.
    *   The diff does *not* show `with self._lock():` around the `d.setdefault...` line.
    *   However, `_reserve_fraction` *does* use `with self._lock(): d = self._ledger()`.
    *   If `_settle` modifies `d` (the ledger) without holding the lock, and another thread calls `_reserve_fraction` (which reads the ledger under lock), there is a **Race Condition**.
    *   **Scenario:**
        1. Thread A calls `_settle`. It reads `d` (ledger). It sees `reserve_tripped` is empty.
        2. Thread B calls `_reserve_fraction`. It acquires lock, reads `d` (ledger). Sees `reserve_tripped` is empty. Returns 0.25.
        3. Thread A (still in `_settle`, no lock held for the write?) calculates the trip. Writes `d["reserve_tripped"][name] = trip`.
        4. Thread C calls `_reserve_fraction`. Acquires lock, reads `d`. Sees `reserve_tripped` is set. Returns None (List).
    *   The danger is if Thread A's write is not synchronized. If `d` is a shared mutable object (the ledger JSON loaded into memory), and `_settle` modifies it without the lock, it could corrupt the ledger or mis

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_1401 (RULING 123 (1): Grok's reserve at 25 % of list, the tripwire)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: gemma 0,
mimo 0, qwen 1. Cycle 1 $0.0072 of Heimdall, not capped.

qwen's P1 ("the write to reserve_tripped in _settle is not protected by self._lock()"): NOT SO. _settle (dev46
providers.py:1014, unchanged but for the tripwire) does all its work inside "with self._lock():" (:1020, unchanged): it
reads the ledger, pops the reservation, accounts the call, writes the trip (:1038) and saves (:1060) under that one lock,
as every ledger write; _reserve_fraction (:1002) reads under the same lock. The hunk did not show the with line.
What IS true (said, not changed): a call that read the fraction (25 %) an instant before another call's trip, and
reserves after it, still reserves at 25 %: the calls deciding at that instant, each decided before the trip existed.
The ruling accepts that tail ("the worst case is one call's overshoot"); with the build's parallel step-A batches it is
at most the calls in flight then. No change.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_1401/C2_STEP.diff (153 lines)
```
   1 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
   2 | index 980c289..3814b5c 100644
   3 | --- a/pipeline/model_providers.json
   4 | +++ b/pipeline/model_providers.json
   5 | @@ -55,7 +55,8 @@
   6 |     "temperature": 0,
   7 |     "key_name": "XAI_API_KEY_MEDLEY",
   8 |     "family": "grok",
   9 | -   "max_out_cap": 12000
  10 | +   "max_out_cap": 12000,
  11 | +   "reserve_list_fraction": 0.25
  12 |    },
  13 |    "heimdall:qwen/qwen3.8-27b": {
  14 |     "vendor": "heimdall",
  15 | diff --git a/pipeline/providers.py b/pipeline/providers.py
  16 | index a70cdb5..21184cd 100644
  17 | --- a/pipeline/providers.py
  18 | +++ b/pipeline/providers.py
  19 | @@ -999,6 +999,18 @@ class Router:
  20 |              return b.prompt_usd(prompt, system), "list"
  21 |          return round(rate * b.prompt_tokens_upper(prompt, system), 8), "reported_rate"
  22 |  
  23 | +    def _reserve_fraction(self, b):
  24 | +        """RULING 123 (1) (orchestrator 14:05 ET Nov 16): a back-end whose spec names reserve_list_fraction (Grok: 0.25)
  25 | +        is reserved at that fraction of its list-price reserve, until a call of it bills above that fraction of the list
  26 | +        price of what it used: then the day's ledger records the trip (reserve_tripped) and it is reserved at list for
  27 | +        the rest of that ledger's day (proof_ly.day_ledger: a ledger a day). -> the fraction, or None (list)."""
  28 | +        f = b.spec.get("reserve_list_fraction")
  29 | +        if not _num(f) or not self.spend_path:
  30 | +            return None
  31 | +        with self._lock():
  32 | +            d = self._ledger()
  33 | +        return None if (d.get("reserve_tripped") or {}).get(b.name) else float(f)
  34 | +
  35 |      def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
  36 |          """Release a reservation and account the call that answered (a free one too, when the ledger is readable).
  37 |          `unreported` (an abandoned call's booking, ruling 107 Q1) is what the cap's unreported estimate takes in place
  38 | @@ -1012,9 +1024,20 @@ class Router:
  39 |                  if key is None:
  40 |                      return                             # a free call: nothing to guard, nothing to write
  41 |                  raise
  42 | -            d["reserved"].pop(key, None)
  43 | +            held = d["reserved"].pop(key, None)
  44 |              if backend is not None:
  45 |                  usage = usage or {}
  46 | +                f = backend.spec.get("reserve_list_fraction")      # RULING 123 (1): the tripwire, after every call
  47 | +                if _num(f) and _num(usage.get("usd_reported")) and float(usage["usd_reported"]) > float(f) * usd and \
  48 | +                        not (d.get("reserve_tripped") or {}).get(backend.name):
  49 | +                    trip = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "role": role,
  50 | +                            "billed": round(float(usage["usd_reported"]), 6), "list": round(usd, 6),
  51 | +                            "fraction": float(f), "reserved": held,
  52 | +                            "why": f"billed above {float(f):.0%} of list: reserved at list for the rest of the day "
  53 | +                                   f"(ruling 123 (1))"}
  54 | +                    d.setdefault("reserve_tripped", {})[backend.name] = trip
  55 | +                    self.notices.append(f"RESERVE BACK TO LIST: {backend.name} {trip['why']}: billed "
  56 | +                                        f"${trip['billed']:.4f}, list ${trip['list']:.4f}")
  57 |                  b = d["by_backend"].setdefault(backend.name, {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0,
  58 |                                                                "price_usd_per_1m": list(backend.price)})
  59 |                  b.update(calls=b["calls"] + 1, usd_estimate=round(b["usd_estimate"] + usd, 6),
  60 | @@ -1364,7 +1387,8 @@ class Router:
  61 |                  tried.append((name, bwhy))
  62 |                  continue
  63 |              upper = b.upper_usd(prompt, max_tokens, system)
  64 | -            key = self._reserve(b, upper)
  65 | +            frac = self._reserve_fraction(b)          # RULING 123 (1): Grok at 25 % of list until a call bills over it
  66 | +            key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)
  67 |              if isinstance(b, HeimdallBackend):
  68 |                  n = self.heimdall_tripwire()
  69 |                  if n:
  70 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
  71 | index b41e97b..b627add 100644
  72 | --- a/tests/providers/test_providers.py
  73 | +++ b/tests/providers/test_providers.py
  74 | @@ -737,11 +737,13 @@ class TestRuling121Reserve(unittest.TestCase):
  75 |      tokens (step A's 4,000 x 8 was 32,000: $0.80 of Grok output at list, more than the day's $1.00 had left)."""
  76 |      REPLIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "package", "fixtures", "replies")
  77 |  
  78 | -    def xai(self, cap=True, answer='{"ok": true}'):
  79 | +    def xai(self, cap=True, answer='{"ok": true}', frac=True):
  80 |          spec = dict(json.load(open(os.path.join(os.path.dirname(P.__file__), "model_providers.json")))["backends"][
  81 |              "xai:grok-4.20-0309-reasoning"])
  82 |          if not cap:
  83 |              spec.pop("max_out_cap", None)
  84 | +        if not frac:                                  # at list (ruling 123 (1) then reserves Grok at 25 % of it)
  85 | +            spec.pop("reserve_list_fraction", None)
  86 |          b = P.XAIBackend("xai:grok-4.20-0309-reasoning", spec, "/nonexistent")
  87 |          b.sent = []
  88 |          b.key = lambda name: "k"
  89 | @@ -808,7 +810,7 @@ class TestRuling121Reserve(unittest.TestCase):
  90 |                  "calls": 1, "in": 0, "out": 0, "usd_estimate": 0.5835, "usd_reported": 0.5835}},
  91 |                  "by_role": {}, "reserved": {}, "usd_reported": 0.5835, "usd_unreported_estimate": 0.0}, open(led, "w"))
  92 |              for cap, fits in ((True, True), (False, False)):
  93 | -                b = self.xai(cap=cap)
  94 | +                b = self.xai(cap=cap, frac=False)     # ruling 121's check is at list
  95 |                  b.complete = lambda prompt, max_tokens, seed, system=None: ('{"ok": true}', {"in": 2000, "out": 3000}, 0.02)
  96 |                  r = router(d, [b], {"context_verdict": [b.name]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
  97 |                  if fits:
  98 | @@ -818,5 +820,54 @@ class TestRuling121Reserve(unittest.TestCase):
  99 |                          r.call("context_verdict", "p" * 7800, 4000)
 100 |  
 101 |  
 102 | +class TestRuling123Reserve(unittest.TestCase):
 103 | +    """RULING 123 (1) (orchestrator 14:05 ET Nov 16): Grok's reserve at 25 % of list (x 1.25 kept), with a tripwire: the
 104 | +    first call that bills above 25 % of the list price of what it used puts the reserve back to list for the rest of the
 105 | +    day (the day's ledger), written in that ledger and announced."""
 106 | +
 107 | +    def ledger(self, d, spent, name="led.json"):
 108 | +        led = os.path.join(d, name)
 109 | +        json.dump({"usd_estimate": spent, "calls": 1, "by_backend": {}, "by_role": {}, "reserved": {},
 110 | +                   "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 111 | +        return led
 112 | +
 113 | +    def grok(self, usd_reported):
 114 | +        g = Fake("xai:g", "xai", answer="{}", price=(5, 25), usage={"in": 1000, "out": 2000, "usd_reported": usd_reported})
 115 | +        g.spec["reserve_list_fraction"] = 0.25
 116 | +        return g
 117 | +
 118 | +    def test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day(self):
 119 | +        with tempfile.TemporaryDirectory() as d:
 120 | +            led = self.ledger(d, 0.69)
 121 | +            g = self.grok(0.01)                       # its usage at list: 1,000 x $5/M + 2,000 x $25/M = $0.055
 122 | +            r = router(d, [g], {"judge": ["xai:g"]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
 123 | +            p = "p" * 3000                            # the reserve at list: 1.25 x (1,200 x $5/M + 12,000 x $25/M) = $0.38
 124 | +            self.assertAlmostEqual(g.upper_usd(p, 12000), 0.3825, places=6)
 125 | +            r.call("judge", p, 12000)                 # 0.69 + 0.38 > 1.00 at list; at 25 %: 0.69 + 0.096: it runs
 126 | +            r.call("judge", p, 12000)                 # billed $0.01 <= 25 % of $0.055: still 25 %
 127 | +            self.assertEqual((g.calls, json.load(open(led)).get("reserve_tripped")), (2, None))
 128 | +            g._usage = {"in": 1000, "out": 2000, "usd_reported": 0.02}     # billed above 25 % of list ($0.01375)
 129 | +            r.call("judge", p, 12000)
 130 | +            trip = json.load(open(led))["reserve_tripped"]["xai:g"]
 131 | +            self.assertEqual((trip["billed"], trip["list"], trip["fraction"], trip["reserved"]),
 132 | +                             (0.02, 0.055, 0.25, round(0.3825 * 0.25, 6)))
 133 | +            self.assertTrue(any(n.startswith("RESERVE BACK TO LIST: xai:g") for n in r.notices), r.notices)
 134 | +            with self.assertRaises(P.SpendLimit):     # 0.73 + the list reserve 0.38 > 1.00: refused, for the day
 135 | +                r.call("judge", p, 12000)
 136 | +            self.assertEqual(g.calls, 3)
 137 | +            day2 = router(d, [g], {"judge": ["xai:g"]}, spend_path=self.ledger(d, 0.69, "day2.json"), limit_usd=1.0,
 138 | +                          limit_basis="reported")
 139 | +            day2.call("judge", p, 12000)              # a new day's ledger: 25 % again
 140 | +            self.assertEqual(g.calls, 4)
 141 | +
 142 | +    def test_only_a_back_end_that_names_the_fraction_is_reserved_below_list(self):
 143 | +        with tempfile.TemporaryDirectory() as d:
 144 | +            led = self.ledger(d, 0.69)
 145 | +            o = Fake("openai:o", "openai", answer="{}", price=(5, 25), usage={"in": 10, "out": 10, "usd_reported": 0.0})
 146 | +            r = router(d, [o], {"judge": ["openai:o"]}, spend_path=led, limit_usd=1.0, limit_basis="reported")
 147 | +            with self.assertRaises(P.SpendLimit):
 148 | +                r.call("judge", "p" * 3000, 12000)    # list: 0.69 + 0.38 > 1.00
 149 | +
 150 | +
 151 |  if __name__ == "__main__":
 152 |      unittest.main()
 153 | 
```

---

pp-selectid: RULING 123 (1) (orchestrator 14:05 ET Nov 16), GROK'S RESERVE AT 25 % OF LIST, WITH A TRIPWIRE. Files:
pipeline/providers.py (Router._reserve_fraction; Router.call takes the reserve through it; Router._settle's tripwire),
pipeline/model_providers.json (one key on the xAI reasoning back-end), tests/providers/test_providers.py.

THE ORDER, verbatim: "(1) THE RESERVE: YES. Price Grok's reserve at 25 % of list (x 1.25 kept), on your evidence: all 127
calls since Nov 15 billed 9-12 % of list, the dearest $0.029. WITH A TRIPWIRE: after every outside call compare what was
billed with what was reserved; the first call that bills above 25 % of list puts the reserve back to list at once, for the
rest of the day, and writes it on line 1. The worst case is one call's overshoot (about $0.25) on a day xAI changes its
billing; PBX's dollar is a target he asked me to hold without lowering quality or losing the day, and I accept that tail
for a video today. Audit-first on Heimdall."

THE CHANGE: a back-end whose spec names reserve_list_fraction (the xAI reasoning back-end: 0.25) is reserved at that
fraction of its reserve (upper_usd: ruling 121's characters / 3, its real cap, list, x 1.25), unless the day's ledger
records a trip for it (reserve_tripped[name]). After every call of it that reports a cost, _settle compares the billed
figure with that fraction of the LIST price of what the call used (b.usd(usage)); the first call above it writes
reserve_tripped[name] = {at, role, billed, list, fraction, reserved, why} into the ledger (under the ledger lock, as every
ledger write) and a "RESERVE BACK TO LIST" notice; from then that back-end is reserved at list until the ledger changes
(proof_ly.day_ledger: one ledger a day, 21:10 ET to 21:10 ET). The builder writes the trip on STATE line 1 (its day
keeper reads the ledger). Every other back-end, the cap ($1.00 a day, outside vendors only) and the reservation's
take-settle-release cycle are unchanged (unchanged guards: Router._reserve, the ledger lock, Heimdall uncapped).

TESTS (TestRuling123Reserve): with $0.69 spent of $1.00, a call whose list reserve ($0.38) does not fit runs at 25 %; two
calls billing under 25 % of list keep it; the first billing above it trips (recorded with billed, list, fraction,
reserved; announced); the next call is reserved at list and refused; a new day's ledger is at 25 % again; a back-end
without the key stays at list. Ruling 121's fit test now runs at list (its own check). Mutations Q1-Q4 after a control.

PLEASE CHECK: (1) the tripwire's comparison and that it cannot be missed; (2) that the trip holds for the day; (3) that
nothing but the named back-end changes; (4) the tests.


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
