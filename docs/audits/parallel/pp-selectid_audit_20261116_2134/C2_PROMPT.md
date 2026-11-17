# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_2134
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 136 s finish=stop usage in 10245 / out 2863 usd_reported=0.000673 usd~0.074 (upper-bound price)

The code implements RULING 127 (2) with high precision. The objective is to ensure that any verdict (PASS or REFUSE) from the local judge (`gemma3:27b`) is treated as provisional, never cached, and never used to seal a package, forcing a retry with a "Heimdall family" (external high-tier models) in subsequent builds.

### Analysis of Implementation

1.  **Prevention of Finality (HELD status):**
    *   In `prescreen`, the logic `if str(backend).startswith(LAST_RESORT):` immediately diverts all results from the local judge into the `fails` dictionary using `local_held()`. The `continue` statement ensures these results never enter `a_by` (the set of successful first-screen verdicts).
    *   In `second_screen`, the `elif str(a2.get("backend") or "").startswith(LAST_RESORT):` block ensures that if the second-screen verdict comes from the local judge, it is marked as `HELD` rather than `PASS`.
    *   The `local_held` helper correctly wraps both passes and refusals in the `HELD` prefix, satisfying the requirement that a local REFUSE is not final.

2.  **Cache and Store Avoidance:**
    *   **Reading:** The `pick` lambda in `prescreen` now includes `and not name.startswith(LAST_RESORT)`, and the DB record check includes `and not str(rec.get("backend")).startswith(LAST_RESORT)`. This ensures that any legacy or accidentally cached local verdicts are ignored, forcing a fresh call to the router.
    *   **Writing:** Because the `prescreen` loop `continue`s when the backend is the local judge, the results are never added to the successful `a_by` collection, which is the source for subsequent caching/storage operations.

3.  **Sealing Protection:**
    *   The `second_screen` modification prevents the local judge from satisfying the "second family" requirement. Since `second_screen` is the final gate for `STEP_A` clearance, no package can be sealed based on a local judge's second verdict.

4.  **Test Coverage:**
    *   `test_every_faster_leg_unavailable_the_local_judges_answer_is_provisional_never_a_pass_never_cached` verifies the full lifecycle: Local Judge answers $\rightarrow$ Result is HELD $\rightarrow$ Not cached $\rightarrow$ Retried when DeepSeek returns.
    *   `test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read` confirms that REFUSE is treated as HELD and that the cache/store is bypassed.
    *   `test_a_second_verdict_from_the_local_judge_never_seals_a_package` confirms the build-level failure to seal.

### Verdict
The implementation is minimal, targeted, and strictly adheres to the ruling. No regressions were introduced to the logic of other backends.

P1_OR_WORSE: 0

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 305 s finish=stop usage in 9660 / out 11967 usd_reported=0.010502 usd~0.208 (upper-bound price)



# Code Audit — RULING 127 (2): Local Judge Verdicts Are Provisional

## Scope

I reviewed the 183-line diff (C1_STEP.diff) implementing RULING 127 (2) across `pipeline/package.py` and `tests/package/test_ruling_102.py`, checking the four requested areas against the governing laws (M12 fail-closed, LAW 20 hard-stop, smallest-diff / M1).

---

## 1. Can any path still seal or cache on a local verdict?

**No.** I traced every write path:

| Path | Guard | Verdict |
|---|---|---|
| `prescreen` – after a backend call | `if str(backend).startswith(LAST_RESORT): … continue` (line 46-49) skips vendor/family tracking, `a_by` insertion, cache write, and store write | ✅ blocked |
| `prescreen` – reading shared cache | `pick` lambda now has `and not name.startswith(LAST_RESORT)` (line 27-28) | ✅ blocked |
| `prescreen` – reading build store (`db`) | `if not (… and not str(rec.get("backend")).startswith(LAST_RESORT))` (line 37-38) forces re-ask | ✅ blocked |
| `second_screen` – second verdict | `elif str(a2.get("backend") or "").startswith(LAST_RESORT): fail[mid] = [local_held(a2)]` (line 57-58) | ✅ blocked |
| `last_resort_of` / `last_resort_note` | Unchanged; now unreachable because local verdicts never enter `a_by` | ✅ inert |

The `continue` in `prescreen` is placed immediately after `items, backend = got` and before any state mutation, so no partial write is possible. The `second_screen` check is the **primary** guard for the second screen (which makes its own backend calls independently of `prescreen`), not merely defence-in-depth.

**No finding.**

## 2. Is a local verdict HELD (retried), never a refusal?

`local_held(a)` always returns a string beginning with `HELD` (`"STEP_A_HELD (ruling 102): local, provisional (ruling 127 (2)): …"`). The parenthetical reports what the local judge said (`pass` or `refuse: <reasons>`) as **informational context inside the HELD reason**, not as the verdict itself. `is_held()` checks `str(w).startswith(HELD)` for every element, and the test helper `self.local(fail)` asserts both `PK.is_held(f)` and `"local, provisional" in f[0]`.

The reason text explicitly states *"held for this build, retried next build"*, and the test `test_every_faster_leg_unavailable_…` confirms the next build re-asks DeepSeek (call count 1, verdict from DS, `fail == {}`).

**No finding.**

## 3. Did anything change for the other legs?

The new code is gated exclusively on `startswith(LAST_RESORT)` (i.e. `"local_judge:"`). For every non-local backend:

- `pick` lambda: the added `and not name.startswith(LAST_RESORT)` is `True` for all non-local names → no behavioural change.
- Store-read guard: same prefix check → no change.
- Post-call guard: `str(backend).startswith(LAST_RESORT)` is `False` → the `continue` is never reached → vendor/family tracking, `a_by`, cache, and store writes proceed exactly as before.
- `second_screen`: the new `elif` is only reached when the previous `if` (no-verdict) is `False` **and** the backend is local → no change for DS/G/GEM.

The `off` lambda, the failover chain order, the `time_sensitive` / old-key fallback, and the `STEP_A_SAME_VENDOR` check are all untouched.

**No finding.**

## 4. The tests

I walked each modified/added test against the code paths:

| Test | What it proves | Verdict |
|---|---|---|
| `test_every_faster_leg_unavailable_…_provisional_never_a_pass_never_cached` | All Heimdall legs down → LJ answers → `two == {}`, all HELD, `cached() == {}`; next build with DS back → DS answers, `fail == {}` | ✅ correct |
| `test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read` | (a) Mocked `CI.a_failures` → HELD text contains `"refuse: REFERENT_OUTSIDE"`, still HELD not REFUSE. (b) Cache poisoned with LJ verdict → `pick` skips it, DS called. (c) Store poisoned with LJ verdict → store-read guard skips it, DS called | ✅ correct |
| `test_the_order_is_deepseek_glm_gemini_the_judge` | Chain `(DS,G,GEM) all down → want=None` → `two == {}`, `self.local(fail)`; other cases unchanged | ✅ correct |
| `test_every_leg_out_of_contract_…` | All Heimdall legs out-of-contract → LJ answers → `two == {}`, `self.local(fail)` | ✅ correct |
| `test_a_second_verdict_from_the_local_judge_never_seals_a_package` | End-to-end build: `out["package"] is None`, `last_resort_87 == {}`, `second_vendor` entries all start with `HELD` and contain `"local, provisional"` | ✅ correct |

The mutation-kill claim (5/5) is consistent with the test coverage: each of the four guards (post-call `continue`, `pick` filter, store-read filter, `second_screen` elif) has at least one test that would fail if the guard were removed.

**No finding.**

---

## Findings

**[P3] `local_held` f-string is 4 lines and dense.** The reason string is correct and the tests pin its content, but a future reader will need to parse the nested conditional `('refuse: ' + '+'.join(…)

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_2134 (RULING 127 (2): the local judge's step-A verdicts are provisional)

Seats (Heimdall only): qwen3.8-27b (reasoning effort medium, 24,000 budget, as audit 2005's cycle 2), gemma-4-31b-it,
mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3 (mimo EMPTY at 32,000). P1_OR_WORSE: qwen 0, gemma 0. Cycle 1 $0.0144 of
Heimdall, not capped. On dev50: mutations L1-L5 after a control run, 5 of 5 killed (L4, the build's own store, killed after
its test was given a router that holds the local judge as a real back-end: the first run of the test left the guard
unreached, 4 of 5); 40 suite files by exit code, 850 tests. No change for cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_2134/C2_STEP.diff (183 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 4e971be..70e79be 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -469,6 +469,16 @@ def is_held(why):
   6 |      return bool(why) and all(str(w).startswith(HELD) for w in why)
   7 |  
   8 |  
   9 | +def local_held(a):
  10 | +    """RULING 127 (2) (orchestrator 21:30 ET Nov 16): a step-A verdict from the local judge (gemma3:27b, ruling 87's last
  11 | +    resort), PASS or REFUSE, is never final while a Heimdall family can be asked: HELD, 'local, provisional', never
  12 | +    cached, asked again next build; a sealed package needs the second screen from a real second family. -> the reason."""
  13 | +    why = CI.a_failures(a)
  14 | +    return (f"{HELD}: local, provisional (ruling 127 (2)): the local judge {a.get('backend')}'s verdict "
  15 | +            f"({'refuse: ' + '+'.join(map(str, why)) if why else 'pass'}) is never final while a Heimdall family can "
  16 | +            f"be asked; never cached; held for this build, retried next build")
  17 | +
  18 | +
  19 |  def last_resort_of(verdicts):
  20 |      """RULING 102: the back-ends among `verdicts` (A items) that are the local judge's (ruling 87's last resort)."""
  21 |      return sorted({str(a.get("backend")) for a in verdicts or () if isinstance(a, dict)
  22 | @@ -574,7 +584,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  23 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  24 |      off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
  25 |      pick = lambda key: next((x for name, x in sorted((cdb.get(key) or {}).items())        # a cached verdict off the
  26 | -                             if isinstance(x, dict) and off(name) and x.get("backend") == name), None)   # writers'
  27 | +                             if isinstance(x, dict) and off(name) and x.get("backend") == name    # writers', never
  28 | +                             and not name.startswith(LAST_RESORT)), None)                         # the local judge's
  29 |      moved = {}                                          # ruling 126 (1): old-key verdicts, written under the new key
  30 |      a_by, fails, vendors, families, todo, contexts, keys = {}, {}, set(), set(), [], {}, {}
  31 |      for m in order:
  32 | @@ -588,7 +599,8 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  33 |                           "show_date": CI.show_date(ctx.now)}       # RULING 126 (1): the ET date
  34 |          keys[mid] = step_a_key(m, contexts[mid])                          # ruling 126 (1): the date only with time words
  35 |          rec = db.get(f"{mid}:{STEP_A_VERSION}")
  36 | -        if not (isinstance(rec, dict) and off(rec.get("backend"))):
  37 | +        if not (isinstance(rec, dict) and off(rec.get("backend"))
  38 | +                and not str(rec.get("backend")).startswith(LAST_RESORT)):        # ruling 127 (2): never the local judge's
  39 |              rec = pick(keys[mid])
  40 |              if rec is None and not time_sensitive(m):    # RULING 126 (1): a verdict cached before the date left the key
  41 |                  rec = next((r for r in map(pick, step_a_old_keys(m, contexts[mid], ctx.now)) if r is not None), None)
  42 | @@ -623,6 +635,10 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  43 |                  fails[m["moment_id"]] = [held_why(e)]
  44 |              continue
  45 |          items, backend = got
  46 | +        if str(backend).startswith(LAST_RESORT):         # RULING 127 (2): the local judge's verdicts are provisional:
  47 | +            for mid, a in items.items():                 # held, never a pass or a refusal, never cached, no vendor
  48 | +                fails[mid] = [local_held(dict(a, backend=backend))]
  49 | +            continue
  50 |          b = router.backends.get(backend)
  51 |          vendors.add(b.vendor if b else backend)
  52 |          families.add(b.family if b else backend)
  53 | @@ -810,6 +826,8 @@ def second_screen(router, cleared, a_by, sources, ctx, log=print, cache=None):
  54 |              if fails.get(mid) or a2 is None:            # ruling 102: no verdict at all is HELD, retried next build
  55 |                  fail[mid] = list(fails.get(mid) or [f"{HELD}: no second verdict (law L-m); held for this build, "
  56 |                                                      f"retried next build"])
  57 | +            elif str(a2.get("backend") or "").startswith(LAST_RESORT):   # RULING 127 (2): never the second family
  58 | +                fail[mid] = [local_held(a2)]
  59 |              elif b2 is None or b2.vendor == k[0] or (k[1] and b2.family == k[1]):
  60 |                  fail[mid] = [f"STEP_A_SAME_VENDOR: the second verdict came from {a2.get('backend')}, not off the "
  61 |                               f"first's vendor {k[0]} and family {k[1]} (law L-m)"]
  62 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
  63 | index 08e48db..5c086fa 100644
  64 | --- a/tests/package/test_ruling_102.py
  65 | +++ b/tests/package/test_ruling_102.py
  66 | @@ -108,21 +108,70 @@ class TestTheSecondFamily(unittest.TestCase):
  67 |          with open(self.cache) as f:
  68 |              return {k: sorted(v) for k, v in json.load(f).items()}
  69 |  
  70 | -    def test_every_faster_leg_unavailable_the_local_judge_answers_and_is_the_last_resort(self):
  71 | +    def local(self, fail):
  72 | +        """RULING 127 (2): every moment HELD as the local judge's provisional verdict, never a pass or a refusal."""
  73 | +        self.assertEqual(sorted(fail), sorted(self.cleared))
  74 | +        self.assertTrue(all(PK.is_held(f) and "local, provisional" in f[0] for f in fail.values()), fail)
  75 | +
  76 | +    def test_every_faster_leg_unavailable_the_local_judges_answer_is_provisional_never_a_pass_never_cached(self):
  77 | +        """RULING 127 (2) (21:30 ET Nov 16): the local judge answers the second screen and its verdict is HELD as
  78 | +        'local, provisional' (no seal can rest on it), never cached; the next build asks Heimdall again."""
  79 |          legs = [Leg(X), Leg(DS, P.Unavailable("HTTP 503")), Leg(G, P.Unavailable("HTTP 503")),
  80 |                  Leg(GEM, P.Unavailable("HTTP 429")), Leg(LJ)]
  81 |          two, fail = self.screen(legs)
  82 | -        self.assertEqual(fail, {})
  83 | -        self.assertEqual({mid: [a["backend"] for a in v] for mid, v in two.items()},
  84 | -                         {mid: [X, LJ] for mid in self.cleared})                 # off Grok: the last leg answered
  85 | +        self.assertEqual(two, {})
  86 | +        self.local(fail)
  87 |          self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])               # in order, each once, never Grok
  88 | -        self.assertEqual({mid: PK.last_resort_of(v) for mid, v in two.items()}, {mid: [LJ] for mid in self.cleared})
  89 | +        self.assertEqual(self.cached(), {})                                      # never remembered
  90 | +        legs = [Leg(X), Leg(DS), Leg(G), Leg(GEM), Leg(LJ)]                       # the next build: deepseek is back
  91 | +        two, fail = self.screen(legs)
  92 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {DS}))   # asked again, answered
  93 | +
  94 | +    def test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read(self):
  95 | +        """RULING 127 (2): a REFUSE from the local judge is not final either; a local verdict found in the cache (from
  96 | +        before the rule) is passed over and Heimdall is asked."""
  97 | +        legs = [Leg(X)] + [Leg(n, P.Unavailable("down")) for n in (DS, G, GEM)] + [Leg(LJ)]
  98 | +        with mock.patch.object(PK.CI, "a_failures", lambda a: ["REFERENT_OUTSIDE"]):
  99 | +            two, fail = self.screen(legs)
 100 | +        self.assertEqual(two, {})
 101 | +        self.local(fail)
 102 | +        self.assertTrue(all("refuse: REFERENT_OUTSIDE" in f[0] for f in fail.values()), fail)
 103 | +        self.assertEqual(self.cached(), {})
 104 | +        ctx = TM.ctx()
 105 | +        for m in self.ms:                                # a local verdict cached under each moment's key
 106 | +            legs = [Leg(X), Leg(DS)]
 107 | +            rr = router(self.d.name, legs)
 108 | +            PK.prescreen(rr, [m], self.srcs, ctx, {"xai"}, {"grok"}, cache=self.cache, kind="step_a_second",
 109 | +                         failover=True)
 110 | +            with open(self.cache) as f:
 111 | +                d = json.load(f)
 112 | +            k = next(k for k in d if k.startswith(m["moment_id"] + ":"))
 113 | +            d[k] = {LJ: dict(d[k][DS], backend=LJ)}      # the same verdict, as if the local judge had given it
 114 | +            with open(self.cache, "w") as f:
 115 | +                json.dump(d, f)
 116 | +        legs = [Leg(X), Leg(DS), Leg(G), Leg(GEM), Leg(LJ)]
 117 | +        two, fail = self.screen(legs)
 118 | +        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {DS}))   # Heimdall asked again
 119 | +        self.assertEqual(legs[1].calls, 1)
 120 | +        store = os.path.join(self.d.name, "store.json")  # nor from the build's own ledger (store)
 121 | +        with open(store, "w") as f:
 122 | +            json.dump({f"{m['moment_id']}:{PK.STEP_A_VERSION}": dict(a_item(m["moment_id"]), backend=LJ)
 123 | +                       for m in self.ms}, f)
 124 | +        os.remove(self.cache)
 125 | +        legs = [Leg(X), Leg(DS), Leg(G), Leg(GEM), Leg(LJ)]   # the local judge a real back-end here: off the writers
 126 | +        a_by, fails, vendors, _ = PK.prescreen(router(self.d.name, legs), self.ms, self.srcs, ctx, {"xai"}, {"grok"},
 127 | +                                               store=store, cache=self.cache, kind="step_a_second", failover=True)
 128 | +        self.assertEqual(({a["backend"] for a in a_by.values()}, legs[1].calls), ({DS}, 1))
 129 |  
 130 |      def test_the_order_is_deepseek_glm_gemini_the_judge(self):
 131 | -        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), LJ)):
 132 | +        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), None)):
 133 |              legs = [Leg(n, P.Unavailable("down") if n in down else None) for n in LEGS]
 134 |              two, fail = self.screen(legs)
 135 | -            self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
 136 | +            if want is None:                             # RULING 127 (2): the judge answers, provisional, held
 137 | +                self.assertEqual(two, {})
 138 | +                self.local(fail)
 139 | +            else:
 140 | +                self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
 141 |              os.path.exists(self.cache) and os.remove(self.cache)
 142 |          legs = [Leg(n) for n in LEGS]                         # a first verdict from glm: Grok confirms, as before
 143 |          two, _ = self.screen(legs, first=G)
 144 | @@ -132,7 +181,8 @@ class TestTheSecondFamily(unittest.TestCase):
 145 |          legs = [Leg(X), Leg(DS, out_of_contract=True), Leg(G, P.DeadlineExceeded("no answer within 60 s")),
 146 |                  Leg(GEM, P.RequestRejected("refused this request")), Leg(LJ)]
 147 |          two, fail = self.screen(legs)
 148 | -        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {LJ}))
 149 | +        self.assertEqual(two, {})                        # ruling 127 (2): the judge's answer is provisional, held
 150 | +        self.local(fail)
 151 |          self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])
 152 |  
 153 |      def test_no_leg_answers_the_clip_is_held_never_cached_and_retried_next_build(self):
 154 | @@ -182,7 +232,9 @@ class TestInTheBuild(unittest.TestCase):
 155 |          self.assertTrue(PK.is_held(out["prescreen"]["failed"]["z"]))
 156 |          self.assertIsNotNone(out["package"])                      # the build goes on without it
 157 |  
 158 | -    def test_a_pin_judged_by_the_local_judge_says_so(self):
 159 | +    def test_a_second_verdict_from_the_local_judge_never_seals_a_package(self):
 160 | +        """RULING 127 (2): even when a screen hands the build the local judge's second verdicts as answers, each is
 161 | +        HELD ('local, provisional'): no clip passes the second family on it, so no package seals on it."""
 162 |          rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None])
 163 |          rig.router.backends[LJ] = type("B", (), {"vendor": "local_judge", "family": "gemma"})()
 164 |          pre = rig.prescreen
 165 | @@ -196,13 +248,10 @@ class TestInTheBuild(unittest.TestCase):
 166 |              return got, fails, v, f
 167 |          rig.prescreen = judged
 168 |          out = rig.run()
 169 | -        segs = out["package"]["segments"]
 170 | -        self.assertEqual(out["prescreen"]["last_resort_87"], {mid: [LJ] for mid in sorted(out["prescreen"]
 171 | -                                                                                         ["last_resort_87"])})
 172 | -        self.assertTrue({sg["moment_id"] for sg in segs} <= set(out["prescreen"]["last_resort_87"]))
 173 | -        row = out["package"]["gates"]["context_a"]
 174 | -        self.assertEqual(row["last_resort"]["verdicts"], {sg["label"]: LJ for sg in segs})
 175 | -        self.assertEqual(row["status"], "PASS")
 176 | +        self.assertIsNone(out["package"])
 177 | +        self.assertEqual(out["prescreen"]["last_resort_87"], {})
 178 | +        local = {mid: w for mid, w in out["prescreen"]["second_vendor"].items() if "local, provisional" in str(w)}
 179 | +        self.assertTrue(local and all(str(w).startswith("HELD") for w in local.values()), out["prescreen"])
 180 |  
 181 |      def test_a_re_screen_off_the_writers_with_no_verdict_and_no_reason_is_held(self):
 182 |          """The writers' re-screen (order 06:22 item 44): a clip it returns nothing at all for is HELD (its default
 183 | 
```

---

pp-selectid: RULING 127 (2) (orchestrator 21:30 ET Nov 16), verbatim: "A verdict from the local gemma3:27b that REFUSES is
never final while a Heimdall family can still be asked: it is recorded as 'local, provisional' and asked again of
Heimdall; it must not be cached as the second vendor's verdict. ... A local PASS is not final either: a sealed package
needs the second screen from a real second family. If a code change is needed for (2), make the smallest one, audit on
Heimdall (it is a verdict-source rule, so it must be audited)". Files: pipeline/package.py, tests/package/test_ruling_102.py.
The diff is on top of ruling 126 (1)'s (audit 20261116_2005, cleared, not yet landed); only 127 (2)'s lines are new here.

UNCHANGED CODE IT USES (package.py): HELD = "STEP_A_HELD (ruling 102)" (:451), LAST_RESORT = "local_judge:" (:452, the
local judge's back-end names: providers.LocalJudgeBackend, vendor "local_judge"), is_held(why) (:467: every reason
starts with HELD), last_resort_of / last_resort_note (the pin's record of local verdicts: now never reached, left as
they are), second_screen's existing branches (no verdict = HELD; same vendor = refused), CI.step_a's failover (a leg out
of contract or past its deadline moves on; the chain's last leg is the local judge).

THE CHANGE:
(a) package.local_held(a): the reason: "STEP_A_HELD (ruling 102): local, provisional (ruling 127 (2)): the local judge
    <backend>'s verdict (pass | refuse: <reasons>) is never final while a Heimdall family can be asked; never cached;
    held for this build, retried next build".
(b) prescreen, after a call: when the back-end that answered is the local judge's (its name starts with LAST_RESORT),
    each of its moments gets that HELD reason; nothing goes to a_by, the build's store (db), the shared cache (new) or
    the vendor/family sets.
(c) prescreen, reading: a cached verdict (pick) or a stored one (db) from the local judge is never used; the moment is
    asked again.
(d) second_screen: a second verdict whose back-end is the local judge's is HELD with that reason, never a pass (for
    any screen that hands one in; (b) already keeps prescreen from doing so).

TESTS (test_ruling_102): the second screen's chain spent down to the local judge: its answer HELD 'local, provisional',
never cached, deepseek asked again next build; a local REFUSE likewise (its reasons in the HELD text); a local verdict in
the cache or in the build's store is passed over and Heimdall asked; the chain-order test and the out-of-contract test
now end HELD at the judge; in the build, second verdicts handed in from the local judge seal no package
(last_resort_87 empty). Mutations L1-L5 after a control run: 5 of 5 killed. Suites: 40 files by exit code, 850 tests.

PLEASE CHECK: (1) that no path can still seal or cache on a local verdict; (2) that a local verdict is HELD (retried),
never a refusal; (3) that nothing else changed for the other legs; (4) the tests.


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
