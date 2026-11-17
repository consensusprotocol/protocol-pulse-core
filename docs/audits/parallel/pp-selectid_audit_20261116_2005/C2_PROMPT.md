# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_2005
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 152 s finish=stop usage in 10434 / out 3201 usd_reported=0.000720 usd~0.079 (upper-bound price)

The code implements RULING 126 (1) as requested. It correctly shifts the "show date" from UTC to ET and modifies the Step-A cache key to be date-agnostic for non-time-sensitive moments, while providing a migration path for existing cached verdicts.

### Analysis

**1. ET Date Conversion**
- `context_integrity.show_date(now)` uses `zoneinfo.ZoneInfo("America/New_York")`. This is the correct way to handle the ET calendar date, including DST transitions.
- The change is applied to both `contexts_from_sources` (used in context checks) and `package.prescreen` (used in Step-A), ensuring consistency across the pipeline.

**2. Cache Key Logic (`step_a_key`)**
- The logic `kc = context if time_sensitive(m) else {k: v for k, v in context.items() if k != "show_date"}` ensures that for moments without time-sensitive flags/words, the `show_date` is excluded from the SHA256 hash.
- This prevents "re-paying" for the same verdict when the calendar date rolls over, satisfying the ruling.

**3. Migration Path (`step_a_old_keys` & `prescreen`)**
- The `step_a_old_keys` function reconstructs the keys used by the previous version of the code (which used UTC dates).
- The window `k in (0, 1)` (today and yesterday UTC) is sufficient to cover the ~12-hour offset between UTC and ET.
- In `prescreen`, the recovery logic is correctly gated: `if rec is None and not time_sensitive(m)`. This ensures that time-sensitive moments are **never** recovered from old keys and must be re-evaluated for the new date.
- Recovered verdicts are stored in the `moved` dictionary and merged into the cache via `_cache_put`, ensuring they are found via the new key in subsequent runs.

**4. Test Coverage**
- `test_ruling_126_the_show_date_is_the_et_date` verifies the UTC $\rightarrow$ ET conversion (e.g., 00:30 UTC Nov 11 is Nov 10 ET).
- `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved` comprehensively tests:
    - Recovery of non-time-sensitive verdicts from old UTC keys.
    - Rejection of time-sensitive verdicts from old keys.
    - Successful migration (writing under the new key).
    - Correctness of the date window.

### Findings

No [P0], [P1], or [P2] defects found. The implementation is precise and the tests are robust.

P1_OR_WORSE: 0

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261116_2005 (RULING 126 (1): the ET show date; the time-word cache key)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 1 of 3.
- gemma: P1_OR_WORSE 0 ("No [P0], [P1], or [P2] defects found").
- qwen: cut off at its 16,000-token cap with no closing count: NO ANSWER. Its tagged fragments each end in its own
  "correct" / "consistent" / "sound" (the old-key context reconstruction; no migration for time-sensitive moments; the
  two show_date sites agree; a run at 23:00 UTC found again at 01:00 UTC under yesterday's UTC date; the test's old-key
  format): none is a defect, checked against the diff.
- mimo: EMPTY at 32,000.
On dev49: mutations R1-R9 after a control run, 9 of 9 killed; 40 suite files by exit code, 849 tests (847 + the 2 new).
Cycle 2: qwen re-seated at reasoning effort MEDIUM with a 24,000 budget (this audit's driver only; audit 0924's
measure: qwen answered at medium where it loops at none), gemma and mimo as before.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261116_2005/C2_STEP.diff (200 lines)
```
   1 | diff --git a/pipeline/context_integrity.py b/pipeline/context_integrity.py
   2 | index 3f32a94..ec86be7 100644
   3 | --- a/pipeline/context_integrity.py
   4 | +++ b/pipeline/context_integrity.py
   5 | @@ -298,6 +298,16 @@ def source_for(x, sources):
   6 |      return sources[x.get("source_key") or x["video_id"]]
   7 |  
   8 |  
   9 | +def show_date(now):
  10 | +    """RULING 126 (1) (orchestrator 20:00 ET Nov 16): the show date step A and the context check carry is the ET calendar
  11 | +    date (PBX's audience and his day), never the UTC date (from 19:00 ET the UTC date is already tomorrow's).
  12 | +    -> 'YYYY-MM-DD', or None without a clock."""
  13 | +    if now is None:
  14 | +        return None
  15 | +    from zoneinfo import ZoneInfo
  16 | +    return now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
  17 | +
  18 | +
  19 |  def contexts_from_sources(package, sources, now=None):
  20 |      """{label: {"text": the window with <selected> marks, "title", "channel", "published", "show_date", "window"}}."""
  21 |      out = {}
  22 | @@ -309,7 +319,7 @@ def contexts_from_sources(package, sources, now=None):
  23 |              continue                                # judged as unavailable (require_all)
  24 |          out[seg["label"]] = {"text": text, "title": src.title or "", "channel": seg["channel"], "window": win,
  25 |                               "published": str(src.published_at or "")[:16],
  26 | -                             "show_date": now.strftime("%Y-%m-%d") if now else None}
  27 | +                             "show_date": show_date(now)}                 # ruling 126 (1): the ET date
  28 |      return out
  29 |  
  30 |  
  31 | diff --git a/pipeline/package.py b/pipeline/package.py
  32 | index 038c3c9..4e971be 100644
  33 | --- a/pipeline/package.py
  34 | +++ b/pipeline/package.py
  35 | @@ -509,6 +509,25 @@ def _load_cache(path):
  36 |          return {}
  37 |  
  38 |  
  39 | +def step_a_key(m, context):
  40 | +    """RULING 58 / RULING 126 (1): a step-A verdict's cache key: the moment id, the sha256 of its text, the sha256 of the
  41 | +    exact context step A reads, and the prompt's version. The show date enters the context's sha ONLY for a moment that
  42 | +    holds time words (time_sensitive: the miner's flag, a recency word or a current price in its own words); a moment
  43 | +    with none is judged the same on any date and is never paid for again because a clock rolled over."""
  44 | +    kc = context if time_sensitive(m) else {k: v for k, v in context.items() if k != "show_date"}
  45 | +    return f"{m['moment_id']}:{text_sha(m['text'])}:{text_sha(json.dumps(kc, sort_keys=True))}:{STEP_A_VERSION}"
  46 | +
  47 | +
  48 | +def step_a_old_keys(m, context, now):
  49 | +    """RULING 126 (1), for a moment with no time words: the keys its verdict was cached under before the date left the
  50 | +    key (the context with the UTC show date in it, today's and yesterday's: all a moment inside the 12-hour window can
  51 | +    hold) -> [key]. Read once; the verdict found is written again under step_a_key."""
  52 | +    from datetime import timedelta
  53 | +    return [f"{m['moment_id']}:{text_sha(m['text'])}:"
  54 | +            f"{text_sha(json.dumps(dict(context, show_date=(now - timedelta(days=k)).strftime('%Y-%m-%d')), sort_keys=True))}"
  55 | +            f":{STEP_A_VERSION}" for k in (0, 1)]
  56 | +
  57 | +
  58 |  def _cache_put(path, new):
  59 |      """Merge {key: {back-end: verdict}} into the cache file (read again under the lock, .tmp then rename)."""
  60 |      if not path or not new:
  61 | @@ -554,6 +573,9 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  62 |      db, cdb = _load_store(store), _load_cache(cache)
  63 |      wv, wf = P._as_set(writer_vendor), P._as_set(writer_family)
  64 |      off = lambda name: (lambda b: b is not None and b.vendor not in wv and b.family not in wf)(router.backends.get(name))
  65 | +    pick = lambda key: next((x for name, x in sorted((cdb.get(key) or {}).items())        # a cached verdict off the
  66 | +                             if isinstance(x, dict) and off(name) and x.get("backend") == name), None)   # writers'
  67 | +    moved = {}                                          # ruling 126 (1): old-key verdicts, written under the new key
  68 |      a_by, fails, vendors, families, todo, contexts, keys = {}, {}, set(), set(), [], {}, {}
  69 |      for m in order:
  70 |          mid = m["moment_id"]
  71 | @@ -563,12 +585,15 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  72 |              continue                # moment is not cleared; it never poisons its batch's call
  73 |          contexts[mid] = {"text": text, "title": src_of(m, sources).title or "", "channel": _name(m, ctx),
  74 |                           "window": win, "published": str(m.get("published_at") or "")[:16],
  75 | -                         "show_date": ctx.now.strftime("%Y-%m-%d")}
  76 | -        keys[mid] = f"{mid}:{text_sha(m['text'])}:{text_sha(json.dumps(contexts[mid], sort_keys=True))}:{STEP_A_VERSION}"
  77 | +                         "show_date": CI.show_date(ctx.now)}       # RULING 126 (1): the ET date
  78 | +        keys[mid] = step_a_key(m, contexts[mid])                          # ruling 126 (1): the date only with time words
  79 |          rec = db.get(f"{mid}:{STEP_A_VERSION}")
  80 |          if not (isinstance(rec, dict) and off(rec.get("backend"))):
  81 | -            rec = next((x for name, x in sorted((cdb.get(keys[mid]) or {}).items())
  82 | -                        if isinstance(x, dict) and off(name) and x.get("backend") == name), None)
  83 | +            rec = pick(keys[mid])
  84 | +            if rec is None and not time_sensitive(m):    # RULING 126 (1): a verdict cached before the date left the key
  85 | +                rec = next((r for r in map(pick, step_a_old_keys(m, contexts[mid], ctx.now)) if r is not None), None)
  86 | +                if rec is not None:
  87 | +                    moved.setdefault(keys[mid], {})[rec["backend"]] = rec
  88 |          if rec is not None:
  89 |              b = router.backends[rec["backend"]]
  90 |              a_by[mid], fails[mid] = rec, CI.a_failures(rec)
  91 | @@ -611,7 +636,7 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
  92 |          with open(store + ".tmp", "w") as f:
  93 |              json.dump(db, f, indent=1)
  94 |          os.replace(store + ".tmp", store)
  95 | -    _cache_put(cache, new)
  96 | +    _cache_put(cache, dict(moved, **new))              # ruling 126 (1): the moved verdicts under their new keys
  97 |      return a_by, fails, vendors, families
  98 |  
  99 |  
 100 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 101 | index c7d52b5..5996416 100644
 102 | --- a/tests/package/test_medley.py
 103 | +++ b/tests/package/test_medley.py
 104 | @@ -1256,12 +1256,14 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 105 |          B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
 106 |          return type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek")}})()
 107 |  
 108 | -    def fake(self, calls, fail=frozenset()):
 109 | +    def fake(self, calls, fail=frozenset(), seen=None):
 110 |          import context_integrity as CI
 111 |          from test_gates import a_item
 112 |  
 113 |          def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
 114 |              calls.append((sorted(contexts), seed))
 115 | +            if seen is not None:
 116 | +                seen.update(contexts)                    # ruling 126 (1): the exact contexts step A was given
 117 |              if set(contexts) & set(fail):
 118 |                  raise RuntimeError("the batch reply was out of contract")
 119 |              b = "heimdall:deepseek" if "xai" in (wv or set()) else "xai:grok"
 120 | @@ -1310,12 +1312,78 @@ class TestRuling58StepAEveryCandidate(unittest.TestCase):
 121 |              calls.clear()
 122 |              later = E.Context(NOW + timedelta(days=1), REG)
 123 |              PK.prescreen(self.router(), ms[:3], srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
 124 | -            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # a new show date
 125 | +            self.assertEqual(calls, [])                  # RULING 126 (1): no time words: a new show date asks nothing
 126 | +            ts = [dict(m, risk=["time_sensitive"]) for m in ms[:2]]          # the miner's flag: time words
 127 | +            PK.prescreen(self.router(), ts, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 128 | +            calls.clear()
 129 | +            PK.prescreen(self.router(), ts, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
 130 | +            self.assertEqual(calls, [])                  # the same show date: paid for once
 131 | +            PK.prescreen(self.router(), ts, srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
 132 | +            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01"])   # time words: a new show date
 133 |              calls.clear()
 134 |              a_by, _, _, _ = PK.prescreen(self.router(), ms[:3], srcs, ctx(), {"xai"}, {"grok"}, cache=cache)
 135 |              self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
 136 |              self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict
 137 |  
 138 | +    def test_ruling_126_the_show_date_is_the_et_date(self):
 139 | +        """RULING 126 (1): the show date step A and the context check carry is the ET date, not the UTC date (19:30 ET
 140 | +        Nov 10 is 00:30 UTC Nov 11)."""
 141 | +        import context_integrity as CI
 142 | +        import tempfile
 143 | +        from datetime import datetime, timezone
 144 | +        evening = datetime(2026, 11, 11, 0, 30, tzinfo=timezone.utc)
 145 | +        self.assertEqual(CI.show_date(evening), "2026-11-10")
 146 | +        self.assertEqual(CI.show_date(datetime(2026, 11, 11, 5, 0, tzinfo=timezone.utc)), "2026-11-11")
 147 | +        self.assertIsNone(CI.show_date(None))
 148 | +        ms, srcs = self.pool(2)
 149 | +        calls, seen = [], {}
 150 | +        self.fake(calls, seen=seen)
 151 | +        with tempfile.TemporaryDirectory() as d:
 152 | +            PK.prescreen(self.router(), ms, srcs, E.Context(evening, REG), {"heimdall"}, {"deepseek"},
 153 | +                         cache=os.path.join(d, "c.json"))
 154 | +        self.assertEqual({c["show_date"] for c in seen.values()}, {"2026-11-10"})
 155 | +        seg = {"label": "clip_01", "video_id": ms[0]["video_id"], "k0": 1, "k1": 1, "words": ms[0]["words"],
 156 | +               "channel": "C00"}
 157 | +        self.assertEqual(CI.contexts_from_sources({"segments": [seg]}, srcs, evening)["clip_01"]["show_date"],
 158 | +                         "2026-11-10")
 159 | +
 160 | +    def test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved(self):
 161 | +        """RULING 126 (1): a moment with no time words finds its verdict under the key it was cached under before (the
 162 | +        UTC show date in it, today's or yesterday's UTC date) and pays nothing; the verdict is written under its new key;
 163 | +        a time-sensitive moment never takes an old key's verdict; older than yesterday is not looked for."""
 164 | +        import tempfile
 165 | +        ms, srcs = self.pool(4)
 166 | +        ms[3] = dict(ms[3], risk=["time_sensitive"])
 167 | +        calls, seen = [], {}
 168 | +        self.fake(calls, seen=seen)
 169 | +        asked = lambda: sorted(sum((c[0] for c in calls), []))
 170 | +        with tempfile.TemporaryDirectory() as d:
 171 | +            c1 = os.path.join(d, "c1.json")
 172 | +            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=c1)
 173 | +            with open(c1) as f:
 174 | +                now_keys = json.load(f)
 175 | +            old = {}
 176 | +            for m in ms:                                 # the same verdicts under the keys used before ruling 126 (1)
 177 | +                c = dict(seen[m["moment_id"]], show_date=NOW.strftime("%Y-%m-%d"))
 178 | +                old[f"{m['moment_id']}:{PK.text_sha(m['text'])}:{PK.text_sha(json.dumps(c, sort_keys=True))}:"
 179 | +                    f"{PK.STEP_A_VERSION}"] = now_keys[PK.step_a_key(m, seen[m["moment_id"]])]
 180 | +            for days, want in ((20 / 24, ["m03"]), (1 + 20 / 24, ["m00", "m01", "m02", "m03"])):
 181 | +                c2 = os.path.join(d, f"c2_{days:.2f}.json")
 182 | +                with open(c2, "w") as f:
 183 | +                    json.dump(old, f)
 184 | +                calls.clear()
 185 | +                later = E.Context(NOW + timedelta(days=days), REG)
 186 | +                a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, later, {"heimdall"}, {"deepseek"}, cache=c2)
 187 | +                self.assertEqual((asked(), len(a_by)), (want, 4), days)
 188 | +                if days < 1:
 189 | +                    with open(c2) as f:
 190 | +                        moved = json.load(f)
 191 | +                    for m in ms[:3]:                     # written under the new key: found there next time
 192 | +                        self.assertIn(PK.step_a_key(m, seen[m["moment_id"]]), moved)
 193 | +                    calls.clear()
 194 | +                    PK.prescreen(self.router(), ms, srcs, later, {"heimdall"}, {"deepseek"}, cache=c2)
 195 | +                    self.assertEqual(calls, [])
 196 | +
 197 |      def test_ruling_101_plan_only_lists_what_the_screen_would_ask_and_asks_nothing(self):
 198 |          import tempfile
 199 |          ms, srcs = self.pool(10)
 200 | 
```

---

pp-selectid: RULING 126 (1) (orchestrator 20:00 ET Nov 16), verbatim: "THE SHOW DATE: it is meant to be the ET date (PBX's
audience and his day), not UTC, and a verdict should carry the date in its cache key ONLY when the moment holds time words
(the free time-word screen already knows which do); a moment with no time words is judged the same on any date and must
never be re-paid because a clock rolled over. Build both, audit-first on Heimdall, and LAND THEM AFTER TONIGHT'S BUILDS".
Files: pipeline/context_integrity.py, pipeline/package.py, tests/package/test_medley.py.

THE CHANGE:
(1) context_integrity.show_date(now): the ET calendar date of the clock (zoneinfo America/New_York), None without one.
    Used by contexts_from_sources (the context check's excerpts; its callers, UNCHANGED, pass the build's clock:
    package.py:2467, 2516, 2561, 2691; spotlight.py:1125, 1143) and by package.prescreen's step-A contexts. Before, both
    used now.strftime on the run clock, which is UTC (eligibility.py:167: "Context.now must be an aware datetime (the
    run clock, UTC)"), so from 19:00 ET the show date was tomorrow's.
(2) package.step_a_key(m, context): the step-A cache key (moment id, sha256 of its text, sha256 of the context step A
    reads, the prompt's version, as before) hashes the context WITHOUT its show_date when the moment is not
    time-sensitive. The time-word screen is UNCHANGED package.time_sensitive (package.py:210): the miner's
    "time_sensitive" risk flag, OR a recency word in the clip's own words (vo_fidelity.time_words, vo_fidelity.py:411),
    OR a current-kind price. The prompt itself still carries the (ET) show date; only the cache key leaves it out.
(3) package.step_a_old_keys(m, context, now) + prescreen: for a moment that is NOT time-sensitive and has no verdict
    under its new key, the keys the code used before (the context hashed WITH the UTC show date, today's and
    yesterday's UTC dates: a moment inside the 12-hour publish window cannot hold an older one) are read, with the same
    "off the writers" filter (pick, as before); a verdict found there is used (no call) and written under the new key
    (moved, merged into the one cache write; _cache_put UNCHANGED, package.py:512). A time-sensitive moment never takes
    an old key's verdict. Without this, landing (2) would re-pay every cached moment once.

NOT CHANGED: the context check (CI.check_contexts) has no per-moment cache: its replies are replayed by the exact prompt,
which now carries the ET date (a line-up re-asked on a new ET date is asked again; it was so before, on the UTC date).

TESTS (test_medley TestRuling58StepAEveryCandidate): the cross-build test now asks: a new show date asks NOTHING for
moments with no time words, and asks again for time-sensitive ones (the miner's flag); new: the ET date at 00:30 UTC
(19:30 ET) in step A's contexts and in contexts_from_sources; new: an old-key verdict is read once (no call) for a
moment without time words, written under its new key (no call the next time), never taken by a time-sensitive moment,
and not looked for past yesterday's UTC date. Mutations R1-R9 after a control run.

PLEASE CHECK: (a) that a time-sensitive moment's verdict can never be reused across show dates; (b) the old-key read
(the exact old key format, the date window, the writers' filter, the write under the new key); (c) the ET date at the
DST edges (zoneinfo); (d) the tests.


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
