# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1305
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 219 s finish=stop usage in 9634 / out 4432 usd_reported=0.000848 usd~0.095 (upper-bound price)

The code correctly addresses the two identified gaps in the "nothing new" guard (RULING 107 (1)).

### Analysis

1.  **Gap 1: Money Refusals (pipeline/providers.py & tests/package/proof_ledger.py)**
    *   **Mechanism**: The `Router` now tracks `spend_refused` as a list of backend names. The `_reserve` method (the central gate for all paid calls) now wraps the reservation logic in a `try...except SpendLimit` block.
    *   **Correctness**: Any call refused due to spend limits (including ledger read failures that raise `SpendLimit`) is recorded. Since `list.append` is atomic in CPython, this is thread-safe for the worker pools used in the pipeline.
    *   **Integration**: `proof_ledger.py:main` captures this list at the end of a build and passes it to `open_work`. This ensures that if a build was stopped by money, `open_work` will be $> 0$, forcing the next build to retry even if inputs are identical.

2.  **Gap 2: Soft Pass Holds (tests/package/proof_ledger.py)**
    *   **Mechanism**: `open_work` now accesses the `never_empty` (soft pass) record.
    *   **Correctness**: It uses a set difference: `set(soft_holds) - set(clean_holds)`. This correctly identifies unique IDs that were held during the soft pass but missed by the clean pass, preventing double-counting while ensuring all "undone" work is captured.

3.  **Safety and Regression**
    *   **Looping/Payment**: A build stopped by money costs nothing (the call is refused *before* the API hit) and does not produce a reply. The next build will attempt the call again. If the budget is still $0$, it will refuse again and mark `open_work > 0`. This is the intended behavior for budget-constrained resumes.
    *   **Laws**: The changes are confined to the build orchestration and spend tracking. They do not modify the Sentence Law, Selection Lock, or any rendering/selection logic (M1). They adhere to M12 (Fail Closed) by ensuring refusals are treated as undone work.
    *   **Tests**: The new tests in `test_ledger_router.py` and `test_ruling_107_guard.py` specifically target the edge cases: free calls not being counted, ledger failures being counted, and the set logic for soft pass holds.

### Findings

No [P0], [P1], or [P2] defects found. The implementation is precise and follows the provided specifications.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 229 s finish=stop usage in 9111 / out 8488 usd_reported=0.007736 usd~0.155 (upper-bound price)



# Code Audit: pp-selectid — RULING 107(1) Spend-Refusal Tracking

## Scope Reviewed
- `pipeline/providers.py` — `Router.spend_refused`, `_reserve` → `_reserve_capped` refactor
- `tests/package/proof_ledger.py` — `open_work(res, sp, refused=())`, never-empty soft-pass holds, `main()` wiring
- `tests/package/test_ledger_router.py` — `TestRuling107TheBuildsRouterNamesEveryCallItRefusedForMoney`
- `tests/package/test_ruling_107_guard.py` — `test_money_refused_calls_and_the_never_empty_pass_holds_are_left_undone`

---

## Findings

### [P2] Potential unbounded build retry loop when the spend limit never resets

The fix correctly makes a money-refused build write `open_work > 0`, so the next build runs. However, if the daily spend limit is exhausted and no reset occurs (e.g., a misconfigured `limit_usd` of $0.00, or a stuck ledger), every subsequent build will:

1. Pass the "nothing new" gate (open_work > 0 from the last *finished* build).
2. Start, hit the limit on the first paid call, refuse, write `open_work > 0` again.
3. Repeat indefinitely.

The description notes that `start_refused` (:380) writes no FINGERPRINT, which stops the loop *only* if the build cannot start at all. A build that starts and then refuses mid-build (the case this fix targets) does write a fingerprint with `open_work > 0`, perpetuating the cycle.

**Mitigation already present:** the spend limit is presumably daily-reset. The `start_refused` path handles the "can't even begin" case.

**Recommendation:** Add a max-consecutive-refused-builds counter (e.g., 3) in the build driver. If the last N finished builds all have `spend_refused` non-empty and no new replies were recorded, emit a hard `HOLD` with a human-action-required message rather than silently re-running. This is a pre-existing gap in the retry philosophy, not a regression from this diff, but the fix makes the loop more likely to be hit (previously the build would silently skip; now it retries).

---

### [P2] One mutation survived (6 of 7 killed) — the untested `main()` wiring

The description explicitly flags: *"NOT UNIT-TESTED, PLEASE READ: the one wiring line in main() (open_work(res, sp, money) at :767-:773); no full-run driver harness exists."*

The surviving mutation is almost certainly in this wiring: e.g., passing `money` where `res` is expected, or omitting the `money` argument (falling back to the default `()`). A typo here would silently drop all spend-refusal counts from `open_work` without any test catching it.

**Recommendation:** Add a minimal integration test that calls `main()` (or the relevant block) with a mocked router whose `spend_refused = ["xai:g"]` and a mocked `res`/`sp` that yield `open_work == 0` without the `refused` argument. Assert the FINGERPRINT.json written contains `"open_work": 1` and `"spend_refused": ["xai:g"]`. Even a 10-line test with `unittest.mock.patch` on `json.dump` would kill this mutation.

---

### [P3] Thread-safety relies on CPython GIL for `list.append`

The justification *"list.append from the worker threads is atomic under the GIL"* is correct for CPython 3.12 (the stated runtime). However, this is an implementation detail, not a language guarantee. If the project ever moves to a free-threaded build (CPython 3.13+ `--disable-gil`, or PyPy with STM), the append is no longer atomic.

**Recommendation:** Add a one-line comment at the `spend_refused` declaration:
```python
self.spend_refused = []  # CPython GIL: list.append is atomic; revisit if free-threaded
```
No code change needed today.

---

### [P3] Deeply nested `.get()` chain for the soft-pass record is fragile to read

```python
s = ((((res or {}).get("never_empty") or {}).get("soft_record") or {}).get("prescreen") or {}).get("held_102") or {}
```

This is correct (every level defaults to `{}`), but a future reader may miscount the parentheses or miss a level. A small helper or a `try/except KeyError` with a local variable per level would be more maintainable. Not a defect.

---

### [P3] `spend_refused` records backend names, not call identities

Two different calls to the same backend (e.g., two different "judge" prompts) both append `"xai:g"`. The `open_work` count is correct (each refusal is one unit of undone work), but the FINGERPRINT.json's `"spend_refused"` list is not deduplicated and doesn't identify *which* calls were refused. For debugging, a tuple `(backend, role, prompt_hash)` would be more actionable.

This is a nit — the count is what drives the retry logic, and the count is correct.

---

## Verification of the Five Requested Checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can any money refusal escape the count, or any non-money failure be counted? | **No.** The only path to `spend_refused.append` is `except SpendLimit` from `_reserve_capped`. Free/uncapped backends return early. Non-`SpendLimit` exceptions 

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1305, ruling 107 (1)'s two gaps)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none, a traced review. gemma-4-31b-it: P0/P1/P2 none, a traced review
(mechanism, set difference, looping). gpt-oss-20b: its 32,000-token cap ran out with no answer.

## qwen's findings
- [P2] "unbounded retry while the spend limit never resets": BY DESIGN, DECLINED. Ruling 107 (1)'s rule is about dollars:
  "a build that judges nothing new must cost $0.00". A build whose router refused money writes open_work > 0, so the next
  build runs. That build's recorded replies replay free (Router.call reads the record before any reservation), and its
  refused calls cost nothing (the refusal comes before any request). Builds are paced by the watcher (a new or
  word-ready moment, or the 30-minute fallback), never by this guard. The day's stop resets at 21:10 ET.
- [P2] "the main() wiring is not unit-tested": KNOWN AND DISCLOSED. It is one line (proof_ledger.py:767-773), and the
  next paid build's own log line ("N item(s) left undone (k of them paid call(s) the spend stop refused)") and its
  FINGERPRINT.json ("spend_refused") show it working. A full-run driver harness does not exist and is not built here.
- [P3] the GIL for list.append: ACCEPTED AS WRITTEN. The pipeline runs on CPython. A lost append could only under-count
  a list already non-empty from another refusal.
- [P3] the nested .get chain: DECLINED (cosmetic).
- [P3] back-end names, not call identities: BY DESIGN. Only the count decides; the names are evidence.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1305/C2_STEP.diff (157 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 09c9f62..0372f28 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -760,6 +760,8 @@ class Router:
   6 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
   7 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
   8 |          self.uncapped = tuple(uncapped)           # RULING 118 (b): vendors recorded in the ledger but never capped
   9 | +        self.spend_refused = []                   # RULING 107 (1): the back-end of every paid call _reserve refused for
  10 | +        #   money (list.append: one per refusal, from any worker thread); a build records them as work left undone
  11 |          self.reserve_wait_s = float(reserve_wait_s)   # _reserve: 0 (the default) refuses at once, as every caller had
  12 |          self.reserve_poll_s = RESERVE_POLL_S          # it; a batch build that may wait for calls in flight opts in
  13 |          import threading
  14 | @@ -944,6 +946,14 @@ class Router:
  15 |          after batch while those four ran."""
  16 |          if not self.spend_path or b.free() or not self._capped(b.name):     # ruling 118 (b): Heimdall is free
  17 |              return None
  18 | +        try:
  19 | +            return self._reserve_capped(b, upper)
  20 | +        except SpendLimit:                        # RULING 107 (1) (build 134, 12:57 ET Nov 17): a call refused for
  21 | +            self.spend_refused.append(b.name)     # money is work left undone, never "nothing new"
  22 | +            raise
  23 | +
  24 | +    def _reserve_capped(self, b, upper):
  25 | +        """_reserve for a capped paid back-end: reserve `upper` or raise SpendLimit (its docstring)."""
  26 |          t_end, waited = time.time() + max(0.0, float(self.reserve_wait_s)), False
  27 |          while True:
  28 |              with self._lock():
  29 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  30 | index 3779fe1..3359471 100644
  31 | --- a/tests/package/proof_ledger.py
  32 | +++ b/tests/package/proof_ledger.py
  33 | @@ -170,16 +170,22 @@ def _errors(x):
  34 |      return 0
  35 |  
  36 |  
  37 | -def open_work(res, sp):
  38 | +def open_work(res, sp, refused=()):
  39 |      """RULING 107 (1): what a finished build left undone, which the next build must try again whatever its inputs:
  40 | -    the moments ruling 102 held (no leg answered), any segment the render's lock gave no verdict on in time, and any
  41 | -    visual check left unmeasured. -> int (0: nothing left)."""
  42 | +    the moments ruling 102 held (no leg answered), in the clean pass and, the ones it did not hold too, in the
  43 | +    never-empty pass (its own record, rulings 136 / 137); any segment the render's lock gave no verdict on in time;
  44 | +    any visual check left unmeasured; and every paid call the build's router refused for money (`refused`:
  45 | +    Router.spend_refused; build 133's two clips-alone verdicts at its $0.00 stop, 12:56 ET Nov 17, left the kept
  46 | +    line-up unjudged, and build 134 then asked nothing). -> int (0: nothing left)."""
  47 |      pre, sp = (res or {}).get("prescreen") or {}, sp or {}
  48 |      h = pre.get("held_102") or {}
  49 |      held = len(h.get("first") or []) + len(h.get("second") or []) + len(sp.get("held_102") or [])
  50 | +    s = ((((res or {}).get("never_empty") or {}).get("soft_record") or {}).get("prescreen") or {}).get("held_102") or {}
  51 | +    held += len(set((s.get("first") or []) + (s.get("second") or [])) -
  52 | +                set((h.get("first") or []) + (h.get("second") or [])))
  53 |      no_verdict = _errors(res) + _errors(sp)        # by structure, never a string search (audit 2155g C1, qwen)
  54 |      vis = (res or {}).get("visual") or {}
  55 | -    return held + no_verdict + int(vis.get("unmeasured") or 0)
  56 | +    return held + no_verdict + int(vis.get("unmeasured") or 0) + len(refused or ())
  57 |  
  58 |  
  59 |  HOOK_SHADOW = {"coherence_verdict:hook": "heimdall:qwen/qwen3.8-27b"}   # RULING 115: recorded, never deciding
  60 | @@ -760,10 +766,13 @@ def main(argv=None):
  61 |          json.dump(res, f, indent=1, default=str)
  62 |      if cand is None:                             # RULING 107 (1): the next build compares its inputs with these, as
  63 |          fp_end, parts_end = fingerprint(pool, delivered, pins, since, now, reg, a.routing)   # at this build's END
  64 | -        left = open_work(res, sp)
  65 | +        money = list(router.spend_refused)       # the calls this build's router refused for money: left undone
  66 | +        left = open_work(res, sp, money)
  67 |          with open(os.path.join(out_dir, FINGERPRINT), "w") as f:
  68 | -            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "build": name}, f, indent=1)
  69 | -        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone")
  70 | +            json.dump({"fingerprint": fp_end, "parts": parts_end, "open_work": left, "spend_refused": money,
  71 | +                       "build": name}, f, indent=1)
  72 | +        say(f"  RULING 107 (1): fingerprint {fp_end[:12]}, {left} item(s) left undone"
  73 | +            + (f" ({len(money)} of them paid call(s) the spend stop refused)" if money else ""))
  74 |      logf.close()
  75 |      return 0
  76 |  
  77 | diff --git a/tests/package/test_ledger_router.py b/tests/package/test_ledger_router.py
  78 | index 45b760c..bbf08b9 100644
  79 | --- a/tests/package/test_ledger_router.py
  80 | +++ b/tests/package/test_ledger_router.py
  81 | @@ -104,6 +104,50 @@ class TestRuling118TheBuildsRouterCapsOnlyOutsideVendors(unittest.TestCase):
  82 |              self.assertAlmostEqual(json.load(open(led))["by_backend"]["heimdall:q"]["usd_reported"], 3.5, places=6)
  83 |  
  84 |  
  85 | +class TestRuling107TheBuildsRouterNamesEveryCallItRefusedForMoney(unittest.TestCase):
  86 | +    """RULING 107 (1) (build 134, 12:57 ET Nov 17): the build's router names the back-end of every paid call it refused
  87 | +    for money in spend_refused, and the build records them as work left undone, so the next build is never "nothing
  88 | +    new" on their account. A free call, an answered paid call or a recorded reply is no refusal."""
  89 | +
  90 | +    def router_at(self, d, xai_spent):
  91 | +        led = os.path.join(d, "SPEND.json")
  92 | +        json.dump({"usd_estimate": 0.0, "calls": 1, "by_backend": {
  93 | +            "xai:g": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": xai_spent}},
  94 | +            "by_role": {}, "reserved": {}, "usd_reported": xai_spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
  95 | +        with contextlib.ExitStack() as st:
  96 | +            for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
  97 | +                                   (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")),
  98 | +                                   (HH, "STATE", os.path.join(d, "HEALTH.json")),
  99 | +                                   (CB, "STATE", os.path.join(d, "BREAKERS.json")),
 100 | +                                   (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
 101 | +                                   (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
 102 | +                st.enter_context(mock.patch.object(mod, name, val))
 103 | +            r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 104 | +        h = Fake("heimdall:q", "heimdall", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
 105 | +        x = Fake("xai:g", "xai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.01})
 106 | +        r.backends, r.chains["check"], r.chains["judge"] = {"heimdall:q": h, "xai:g": x}, ["heimdall:q"], ["xai:g"]
 107 | +        return r, led, x
 108 | +
 109 | +    def test_each_refusal_for_money_is_named_and_nothing_else(self):
 110 | +        with tempfile.TemporaryDirectory() as d:
 111 | +            r, led, x = self.router_at(d, 0.95)
 112 | +            self.assertEqual(r.spend_refused, [])
 113 | +            r.call("check", "p")                                     # Heimdall: free, never reserved
 114 | +            for n in (1, 2):
 115 | +                with self.assertRaises(P.SpendLimit):
 116 | +                    r.call("judge", "p")                             # 0.95 + its upper bound > the $1.00 stop
 117 | +                self.assertEqual(r.spend_refused, ["xai:g"] * n)
 118 | +            self.assertEqual(x.calls, 0)
 119 | +            open(led, "w").write("{not json")                        # an unreadable ledger refuses for money too
 120 | +            with self.assertRaises(P.SpendLimit):
 121 | +                r.call("judge", "p")
 122 | +            self.assertEqual(r.spend_refused, ["xai:g"] * 3)
 123 | +        with tempfile.TemporaryDirectory() as d:
 124 | +            r, led, x = self.router_at(d, 0.0)
 125 | +            self.assertEqual((r.call("judge", "p").backend, r.spend_refused), ("xai:g", []))   # answered: none
 126 | +            self.assertEqual((r.call("judge", "p").backend, x.calls, r.spend_refused), ("xai:g", 1, []))   # replayed
 127 | +
 128 | +
 129 |  class TestTheLedgerBuildsRouterWaitsForCallsInFlight(unittest.TestCase):
 130 |  
 131 |      def test_a_call_kept_out_only_by_a_call_in_flight_waits_and_answers(self):
 132 | diff --git a/tests/package/test_ruling_107_guard.py b/tests/package/test_ruling_107_guard.py
 133 | index 8411c19..6155523 100644
 134 | --- a/tests/package/test_ruling_107_guard.py
 135 | +++ b/tests/package/test_ruling_107_guard.py
 136 | @@ -129,6 +129,20 @@ class TestOpenWorkAndNothingNew(unittest.TestCase):
 137 |          self.assertEqual(PLG.open_work({"a": [{"b": {"verdict": "error"}}, {"verdict": "pass"}]}, {}), 1)   # nested
 138 |          self.assertEqual(PLG.open_work({"why": 'a log line quoting "verdict": "error"'}, {}), 0)   # a string is no verdict
 139 |  
 140 | +    def test_money_refused_calls_and_the_never_empty_pass_holds_are_left_undone(self):
 141 | +        """Build 134 (12:57 ET Nov 17) asked nothing: free build 133's two clips-alone verdicts, refused at its $0.00
 142 | +        stop, were not counted as undone, and the never-empty pass's own record was not read."""
 143 | +        self.assertEqual(PLG.open_work({}, {}, ["xai:grok", "xai:grok"]), 2)      # each refused call
 144 | +        self.assertEqual((PLG.open_work({}, {}, ()), PLG.open_work({}, {}, None)), (0, 0))
 145 | +
 146 | +        def soft(first, second):
 147 | +            return {"never_empty": {"soft_record": {"prescreen": {"held_102": {"first": first, "second": second}}}}}
 148 | +        self.assertEqual(PLG.open_work(soft(["a"], ["b"]), {}), 2)                # the soft pass's own holds
 149 | +        both = dict(soft(["a"], ["b", "c"]), prescreen={"held_102": {"first": ["a"], "second": ["b"]}})
 150 | +        self.assertEqual(PLG.open_work(both, {}), 3)      # a and b once (the clean pass held them too), c new
 151 | +        self.assertEqual(PLG.open_work(dict(both, never_empty=None), {}, ["x"]), 3)   # no soft pass: clean + money
 152 | +        self.assertEqual(PLG.open_work({"never_empty": {"stage": "2a"}}, {}), 0)      # a soft pass that held nothing
 153 | +
 154 |      def test_only_the_newest_finished_build_counts(self):
 155 |          with tempfile.TemporaryDirectory() as d:
 156 |              def build(name, fp=None, left=0):
 157 | 
```

---

pp-selectid: RULING 107 (1)'s guard ("a build that judges nothing new must cost $0.00") has two gaps, found 12:57 ET
Nov 17. The build driver (tests/package/proof_ledger.py) fingerprints its inputs; when they equal the newest finished
build's and that build's FINGERPRINT.json says open_work == 0, it asks no model (nothing_new, proof_ledger.py:207 and
:219, called at :538 before any router exists). open_work counted only the clean pass's ruling-102 holds, lock no-verdicts
and unmeasured visuals. GAP 1: a paid call the router REFUSED FOR MONEY was never counted. Free build 133 (stop = the day's
spend + $0.001) refused the kept line-up's two clips-alone verdicts by design, recorded "0 items left undone", and paid
build 134 with the same inputs then asked nothing. GAP 2: the never-empty pass (rulings 136/137: package.build runs a
soft pass when the clean pass seals nothing; its record is res["never_empty"]["soft_record"]) was never read.

THE CHANGE:
(a) pipeline/providers.py: Router.spend_refused = [] (in __init__). _reserve (providers.py:931; its only callers are
    Router.call at :1406 and Router.transcribe at :1518; RoleModel at :1566 only converts a refusal already raised by
    them) keeps its free / uncapped early return and now calls _reserve_capped (:955, the old body UNCHANGED, which
    raises SpendLimit at :969 over the limit, and via _ledger at :855 or _basis_total at :912 on an unreadable or
    unreported ledger). Every SpendLimit from it appends the back-end's name to spend_refused and re-raises.
    list.append from the worker threads (step A, vision run in pools) is atomic under the GIL.
(b) tests/package/proof_ledger.py open_work(res, sp, refused=()): + len(refused); + the soft pass's held_102 ids not
    already held by the clean pass (a set difference: the soft pass re-runs step A on the same pool, so its first-screen
    holds repeat the clean pass's). At the build's end (:767, only for a full build, not --from-candidate), the driver
    passes list(router.spend_refused) (the one router of the build, built at :551) and records it in FINGERPRINT.json.
(c) Any code change moves the fingerprint (code by content), so the next build runs anyway; after this, a build stopped
    by money writes open_work > 0 and the next one retries. A build that cannot start at the stop (start_refused,
    :380) still writes no FINGERPRINT.

TESTS: test_ruling_107_guard (open_work: each refused call counts; the soft pass's holds count once; none or empty is 0)
and test_ledger_router (the build's own router from PLG.build_router: Heimdall free call and an answered or replayed paid
call add nothing; each refusal over the $1.00 stop and an unreadable ledger each add the back-end). Mutations: 6 of 7
killed. NOT UNIT-TESTED, PLEASE READ: the one wiring line in main() (open_work(res, sp, money) at :767-:773); no
full-run driver harness exists.

PLEASE CHECK: (1) can any money refusal escape the count, or any non-money failure be counted? (2) can a build now loop
forever or pay twice for the same judgment? A build whose router refused money writes open_work > 0, so the next build
runs; its recorded replies replay free and its refused calls cost nothing. (3) thread safety of the append; (4) the soft
pass's set difference; (5) the tests.


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
