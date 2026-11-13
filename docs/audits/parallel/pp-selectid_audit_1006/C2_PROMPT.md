# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1006
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 156 s finish=stop usage in 7820 / out 3315 usd~0.073 (upper-bound price)

# Audit: pp-selectid — Ruling 57 fresh-first selection preference

Scope: I reviewed only the diff provided (package.py, test_medley.py). I cannot see the surrounding module (E, lineup_for's internals beyond the diff, pm/Rig helpers, ctx.now's provenance), so anything I say about those is inference from the diff, flagged as such.

## P0

None found.

## P1

**P1-1 — `first_fresh` calls `lineup_for` without `dropped`/`doomed`, so the angle ordering can be computed on a line-up that will never be used (package.py:1528-1531, diff lines 62-70).**
`build()`'s later call passes `frozenset(dropped | doomed)`; `first_fresh` passes neither. Scenario: angle A's only fresh clip is in `doomed` (e.g. dropped by an earlier angle's L-u one-clip-per-channel rule, or a prior line-up's doomed set). `first_fresh(A)` finds a fresh line-up → A is tried first; the real `lineup_for(A, cleared, dropped|doomed, ...)` then returns a stale-only (or no) line-up. The build then tries A's stale package before B's fresh one — the ruling's preference silently inverted for that build. Conversely an angle whose fresh clip is only reachable via `repeat_ok=True` (pool_fill path) is also mis-ordered, since `first_fresh` uses the strict no-repeat, no-dropped call. This is a preference, not a gate, so it's not a LAW 20 violation, but it means the implemented order can diverge from the ruling's stated intent with no test covering it. Mitigation: it's still deterministic and the fallback order is the writer's order, so it degrades to the old behavior, not to a wrong package. I'd want either `first_fresh` to use the same dropped/doomed set (if available at that point in `build()` — I cannot verify from the diff whether `dropped`/`doomed` are populated before the angle loop; if they're per-iteration, the current code may be the only correct choice, and the divergence is inherent) or a comment/test acknowledging the divergence.

**P1-2 — `fresh_key`'s "counts as the oldest" for unknown publish time is implemented as `max(known)+1.0`, which is not the oldest when all ages are unknown (package.py:36-43, diff lines 36-43).**
If `ages` is entirely `None` (no clip has a readable publish time), `known` is empty, `oldest = 0.0 + 1.0 = 1.0` hour, so the mean is 1.0 h — the line-up ranks as *very fresh* in the second key component, while the first component correctly says not-fresh. Scenario: two angles, both all-unknown publish times, one whose clips are actually 70 h old. Both get fresh=False, mean 1.0. Tie broken by the proposer's-earliest key — so behavior is likely still sane, but the docstring's "counts as the oldest" is not what the code does in the all-unknown case. Also, when *some* ages are known: a line-up with one 0.5 h-old clip and one unknown clip gets mean (0.5+1.0)/2 = 0.75 h, ranking it newer than a line-up of two 0.8 h-old clips with known times — the unknown clip is treated as 1.0 h old, i.e. *newer than every known age* whenever the max known age < 1 h. "Counts as the oldest" should mean older than the oldest known, i.e. `max(known)+1.0` is only "oldest+1h" — it's older than all known clips, which is arguably right, but note the all-None case where 1.0 h is younger than reality. Concrete failure: within the not-fresh group, an all-unknown line-up beats a 70 h-old line-up on the second key. Whether that's wrong depends on the ruling's intent; the docstring and code disagree, which is the finding.

**P1-3 — `E.age_hours(published_at, now)` semantics are unverifiable from the diff, and the whole feature hinges on them (package.py:39).**
I cannot see `E.age_hours`. If it returns `now - published_at` in hours, fine. But if it returns None for unparseable strings (the diff's test only exercises `published_at=None`, not a *malformed* string), or raises on a timezone-naive/aware mismatch, `fresh_key` will either misrank or throw. M12 FAIL CLOSED: an exception inside `fresh_key` inside `first_fresh` inside `build()`'s angle sort would fail the whole build, not just the preference — is that the intended fail-closed behavior for a *preference*? Plausibly yes (M12), but it's worth stating: a malformed `published_at` on one moment now has the power to fail the build at the sort, before any line-up is even attempted, whereas before this diff a malformed publish time only affected... (I cannot verify what it affected before; `usable()`'s L-v 3 check presumably already read these fields, so the exposure is not new). Downgrade to P1 only because the field was already load-bearing for L-v 3; if `age_hours` is new in this diff, it's P0-adjacent. Flagging as "verify": does `age_hours` return None (not raise) on unparseable input, and does it handle tz-aware vs naive `published_at`?

## P2

**P2-1 — Cost of the extra `lineup_for` per angle (package.py:1528-1531).**
`first_fresh` runs a full `lineup_for` (with `need_onset` and `need_stand_alone`, i.e. 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 47 s finish=stop usage in 7934 / out 290 usd~0.047 (upper-bound price)

**P0: none**

**P1: none**

**P2:**
- pipeline/package.py:66 (first_fresh): extra lineup_for() call per angle (up to 3) solely for sorting; cost is verifiable in the added lines and test coverage but not measured.
- pipeline/package.py:56 (key = (f[0], f[1], ...)): prepends (has_fresh, -mean_age) ahead of prior positional/duration keys; matches stated K3 but changes every call site that passes now.
- pipeline/package.py:68 (sorted(..., key=lambda a: not first_fresh(a))): reordering is stable and purely by whether the *best* lineup under the new key contains a fresh clip; verified by TestRuling57Fresh but relies on cleared/ctx.now defined earlier in build().
- pipeline/package.py:39 (fresh_key): no-published_at case treated as oldest (max(default=0.0)+1); test at line 120 confirms but behavior for mixed known/unknown lists is only partially exercised.
- No diff lines alter accept=half, need_onset, need_stand_alone, dropped sets, or any gate/usable() logic; time-sensitive enforcement (L-v 3) untouched.

All stated K1-K3 readings match the code. TestRuling57Fresh and existing callers (now=None path) pass.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 59 s finish=stop usage in 8438 / out 1807 usd~0.052 (upper-bound price)

# Audit: pp-selectid-1006 (Ruling 57 Freshness Preference)

## P0 Findings
None.

## P1 Findings

**1. `fresh_key` treats "no readable time" as the oldest, which can invert the "newest clips" tie-breaker**
`pipeline/package.py:41-43` (in `fresh_key`)

```python
oldest = max(known, default=0.0) + 1.0
return (any(a is not None and a <= FRESH_H for a in ages),
        -sum(a if a is not None else oldest for a in ages) / max(1, len(ages)))
```

Scenario: Two line-ups both have `fresh == False` (no clip ≤ 24 h).
- Line-up A: clips aged 100 h, 100 h, 100 h. Mean = 100. Key = -100.
- Line-up B: clips aged 100 h, 100 h, `None` (no publish time). `oldest` = 101. Sum = 100+100+101 = 301. Mean = 100.33. Key = -100.33.

Since the key is compared with `>` (higher is better), -100 > -100.33, so Line-up A wins. This is correct *if* "no time" should be treated as oldest. However, the docstring says "counts as the oldest," but the implementation uses `max(known) + 1.0`, which is only *slightly* older than the oldest known clip. If a line-up has *only* clips with no readable time, `known` is empty, `oldest` = 1.0, and the mean is 1.0, making it appear *newer* than a line-up with clips aged 50 h. This is a bug: a line-up with entirely unknown publish times will rank as "newer" than one with known old clips.

**Concrete scenario:**
- Line-up X: 3 clips, all `published_at=None`. `known=[]`, `oldest=1.0`, mean=1.0, key=-1.0.
- Line-up Y: 3 clips, all aged 50 h. `known=[50,50,50]`, `oldest=51`, mean=50, key=-50.0.
- -1.0 > -50.0, so Line-up X (all unknown) is preferred over Line-up Y (all 50 h old). This contradicts the intent that unknown time = oldest.

**Fix:** When `known` is empty, the mean should be a large sentinel (e.g., `float('inf')` or a very large number) so the key is very negative, ensuring it ranks last.

## P2 Findings

**2. Extra `lineup_for` call per angle in `build()` adds latency**
`pipeline/package.py:1528-1529`

```python
def first_fresh(a):
    segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now)
    return bool(segs) and fresh_key(segs, ctx.now)[0]
```

This calls `lineup_for` for every angle *before* the main loop, then the main loop calls `lineup_for` again for the same angle. For 3 angles, this doubles the `lineup_for` invocations. `lineup_for` is O(n²) in the number of moments (it iterates over all permutations of hook + clips). With ~24 moments, this is non-trivial. The result of the first call is discarded (only `bool(segs)` and `fresh_key` are used). Consider caching the result or computing freshness from the angle's moments directly without a full `lineup_for` call.

**3. `fresh_key` is called on `[h] + order` in `lineup_for`, but the hook is included in the mean age**
`pipeline/package.py:57-58`

```python
f = fresh_key([h] + order, now)
key = (f[0], f[1], key[0], key[1])
```

The docstring for `fresh_key` says "the mean age in hours" of the line-up's segments. The hook is included. This matches K2 ("the hook included"), so this is consistent with the stated reading. However, if the hook is a very old clip (e.g., 70 h) and the two clips are fresh (5 h, 10 h), the mean is (70+5+10)/3 = 28.3 h, which is > 24 h, so `fresh` is still `True` (because `any` is used for the first element). This is correct per the ruling ("at least one clip from the last 24 h"). No issue, but worth noting that the hook's age dilutes the "newest" ranking.

**4. Test coverage gap: no test for the "all unknown publish times" case**
`tests/package/test_medley.py:120`

```python
self.assertFalse(PK.fresh_key([dict(ms[0], published_at=None)], NOW)[0])
```

This tests that a single clip with no time is not fresh, but does not test the *ranking* behavior when all clips have no time (the P1 bug above). A test should verify that a line-up with all-unknown times ranks below a line-up with known old times.

**5. `pool_fill` passes `now` through, but the test for `pool_fill` with `now` is not shown**
`pipeline/package.py:27-28`

The diff shows `pool_fill` passing `now` to `lineup_for`, but the test file only shows tests for `lineup_for` and `build()`. There is no explicit test that `pool_fill` with `now` produces a fresh-first line-up. This is a minor coverage gap.

## Verification of Stated Readings

- **K1:** Correct. The build stops at the first passing package, so the preference is applied to the *order of trying*. The diff confirms this: `lineup_for` returns the best line-up under the new key, and `build()` re-orders angles by freshness before the main loop.
- **K2:** Correct. `fresh_key` includes the hook in the mean age calculation.
- **K3:** Correct. The key is `(fresh, newest, proposer_earliest, seconds_nearest_middle)`, so recency ranks above the proposer's earliest-moment preference. The play order is preserved (the clips are still in the proposer's order; only the *selection* of which line-

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1006 (RULING 57: prefer line-ups with the newest clips): cycle 1 consensus

**Run.** Verdicts:
- grok: no P0 / P1, "SHIP: yes";
- glm: "yes with conditions";
- qwen: "SHIP: NO", on one P1 that holds (glm found it too).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | qwen P1 / glm P1-2: "counts as the oldest" was max(known ages) + 1 h, so a line-up whose ages are ALL unknown read as 1 h old, the NEWEST | A fixed sentinel, UNKNOWN_AGE_H = 1e6 h: a clip with no readable time is the oldest there is, in every line-up. Tested: an all-unknown line-up ranks below one aged 50-70 h. |

## Answered (verified from the code)

| # | claim | the code |
|---|---|---|
| A1 | glm P1-1: first_fresh() calls lineup_for without dropped / doomed | It runs right after the angle call, before any line-up, so nothing is dropped or doomed yet (both start empty in the loop). The line-up it computes is the one the loop's first lineup_for returns. |
| A2 | glm P1-3: age_hours' semantics | eligibility.age_hours(published_at, now) = (now - the parsed time) in hours, or None when the time cannot be parsed (_parse_time). An unparseable time is therefore never fresh (F1). |
| A3 | qwen P2-2: the extra lineup_for call per angle | Recorded, no change: the cleared pool after both screens is 5-13 moments; one more call per angle (3 at most) is milliseconds. |
| A4 | qwen P2-5 / glm: no test of pool_fill with now | Recorded: pool_fill passes now straight to lineup_for, whose preference is tested. |

## Verification

- test_medley 92 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1006/C2_STEP.diff (135 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index c1d391f..6d6fcf0 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -62,6 +62,8 @@ RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the packaging target the fact
   6 |  VO_S = (6.0, 22.0)                 # the PBX MAX v3 VO's seconds (intro + bridges), content_range()'s slack
   7 |  R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
   8 |  TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
   9 | +FRESH_H = 24.0                     # ruling 57 (09:59 Nov 13): a line-up with a clip this fresh is preferred
  10 | +UNKNOWN_AGE_H = 1.0e6              # ruling 57: a clip with no readable publish time counts as the oldest there is
  11 |  PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
  12 |  PRESCREEN_BATCH = 8                # excerpts per step-A call
  13 |  PRICE_PREDICTIONS_MAX = 1          # L-u: at most one per video
  14 | @@ -925,7 +927,7 @@ def placement(m):
  15 |      return "" if opens else " | cannot open (never the hook)"
  16 |  
  17 |  
  18 | -def pool_fill(angle, pool, dropped=frozenset()):
  19 | +def pool_fill(angle, pool, dropped=frozenset(), now=None):
  20 |      """PROPOSAL 1: an angle whose own moments form no line-up (lineup_for, one clip per channel, then L-y 4's
  21 |      exception) is completed from the WHOLE cleared pool, as ruling 41's swap fills a place: the pool's other moments
  22 |      are appended to the angle's after its own, best by rank_score, and lineup_for runs again under every unchanged
  23 | @@ -944,7 +946,8 @@ def pool_fill(angle, pool, dropped=frozenset()):
  24 |      mine = set(own)
  25 |      half = lambda segs: 2 * sum(m["moment_id"] in mine for m in segs) >= len(segs)   # the angle's own: >= half
  26 |      for repeat_ok in (False, True):
  27 | -        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half)
  28 | +        segs = lineup_for(ext, pool, dropped, repeat_ok=repeat_ok, need_onset=True, need_stand_alone=True, accept=half,
  29 | +                          now=now)
  30 |          if segs is not None:
  31 |              return segs, [m["moment_id"] for m in segs if m["moment_id"] not in mine]
  32 |      return None, None
  33 | @@ -960,8 +963,16 @@ def supply_exception(segs, ctx):
  34 |              f" gives two clips, from two videos (L-y 4)")
  35 |  
  36 |  
  37 | +def fresh_key(segs, now):
  38 | +    """RULING 57: how a line-up ranks by its clips' age on the render clock `now`: (holds a clip <= FRESH_H old, minus
  39 | +    the mean age in hours). A clip with no readable publish time is never fresh and counts as the oldest."""
  40 | +    ages = [E.age_hours(m.get("published_at"), now) for m in segs]
  41 | +    return (any(a is not None and a <= FRESH_H for a in ages),                # audit 1006 C1 (qwen, glm): a fixed
  42 | +            -sum(UNKNOWN_AGE_H if a is None else a for a in ages) / max(1, len(ages)))   # sentinel, never "newest"
  43 | +
  44 | +
  45 |  def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
  46 | -               need_stand_alone=False, accept=None):
  47 | +               need_stand_alone=False, accept=None, now=None):
  48 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
  49 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
  50 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
  51 | @@ -1004,6 +1015,9 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  52 |                  if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  53 |                      continue
  54 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  55 | +                if now is not None:                       # ruling 57: a fresh clip first, then the newest clips,
  56 | +                    f = fresh_key([h] + order, now)       # then the proposer's earliest (its play order is kept)
  57 | +                    key = (f[0], f[1], key[0], key[1])
  58 |                  if best is None or key > best[0]:
  59 |                      best = (key, [h] + order)
  60 |          if best:
  61 | @@ -1513,6 +1527,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  62 |      if not angles:
  63 |          return out
  64 |      out.pop("why_none", None)
  65 | +    def first_fresh(a):                                   # ruling 57: the angles whose first line-up holds a clip
  66 | +        segs = lineup_for(a, cleared, need_onset=True, need_stand_alone=True, now=ctx.now)   # <= FRESH_H old go first
  67 | +        return bool(segs) and fresh_key(segs, ctx.now)[0]
  68 | +    angles = sorted(angles, key=lambda a: not first_fresh(a))      # stable: the writer's order within each group
  69 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
  70 |      out["angle_backend"], out["angle_tried"] = angle_reply.backend, [list(x) for x in angle_reply.tried]   # ruling 5
  71 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
  72 | @@ -1663,15 +1681,15 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  73 |                      exception = supply_exception(segs, ctx)
  74 |                  else:
  75 |                      segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
  76 | -                                                 need_stand_alone=True), None
  77 | +                                                 need_stand_alone=True, now=ctx.now), None
  78 |                      if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
  79 |                          segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
  80 | -                                          need_stand_alone=True)
  81 | +                                          need_stand_alone=True, now=ctx.now)
  82 |                          if segs is not None:
  83 |                              exception = supply_exception(segs, ctx)
  84 |                      filled = None
  85 |                      if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
  86 | -                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
  87 | +                        segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed), ctx.now)   # FIRST: the
  88 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
  89 |                          exception = supply_exception(segs, ctx) if segs is not None else None
  90 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
  91 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
  92 | index 814be17..85ce18f 100644
  93 | --- a/tests/package/test_medley.py
  94 | +++ b/tests/package/test_medley.py
  95 | @@ -1191,6 +1191,39 @@ class TestProposal1PoolFill(unittest.TestCase):
  96 |          self.assertIsNotNone(out["package"])
  97 |  
  98 |  
  99 | +class TestRuling57Fresh(unittest.TestCase):
 100 | +    """RULING 57 (09:59): with a 72 h window, a line-up with at least one clip from the last 24 h is preferred over one
 101 | +    with none, then the newest clips. The build stops at its first passing package, so the preference decides what is
 102 | +    TRIED first: inside an angle and across angles."""
 103 | +
 104 | +    def at(self, mid, ch, dur, hours_ago, **kw):
 105 | +        return dict(pm(mid, ch, dur, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat(),
 106 | +                    hook_onset={"pass": True})
 107 | +
 108 | +    def test_a_line_up_with_a_fresh_clip_is_tried_first(self):
 109 | +        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 110 | +              self.at("z", "D", 13.0, 5)]                                  # only z is under 24 h
 111 | +        by = {m["moment_id"]: m for m in ms}
 112 | +        a = angle(["h", "x", "y", "z"], "h")
 113 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by, need_onset=True)], ["h", "x", "y"])
 114 | +        segs = PK.lineup_for(a, by, need_onset=True, now=NOW)              # without now: the proposer's earliest
 115 | +        self.assertIn("z", [m["moment_id"] for m in segs])                 # with now: a fresh clip first
 116 | +        self.assertTrue(PK.fresh_key(segs, NOW)[0])
 117 | +        old = dict(by, z=self.at("z", "D", 13.0, 40))                      # nothing fresh: the newest clips next
 118 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, old, need_onset=True, now=NOW)], ["h", "x", "z"])
 119 | +        self.assertFalse(PK.fresh_key([dict(ms[0], published_at=None)], NOW)[0])   # no readable time: never fresh
 120 | +        unknown = [dict(m, published_at=None) for m in ms[:3]]              # audit 1006 C1 (qwen P1): all unknown
 121 | +        self.assertLess(PK.fresh_key(unknown, NOW), PK.fresh_key(ms[:3], NOW))   # ranks below 50-70 h, never newest
 122 | +
 123 | +    def test_the_angle_with_a_fresh_line_up_is_judged_first(self):
 124 | +        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
 125 | +              self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
 126 | +        rig = Rig(ms, [["h", "x", "y"], ["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
 127 | +        out = rig.run()
 128 | +        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])             # the writer's 2nd angle, fresh, first
 129 | +        self.assertEqual(out["angles"][0]["hook"], "f")
 130 | +
 131 | +
 132 |  class TestRuling41Search(unittest.TestCase):
 133 |      """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 134 |      place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 135 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, a hook + 2-4 clips from YouTube
channels). Your role: a strict reviewer of a selection preference.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background:
- A build reads moments from videos inside a publish window, screens them, asks an angle writer for up to 3 angles
  (a sentence + clip ids in play order), and tries line-ups. lineup_for() picks one line-up per angle under every
  rule; its preference was (the proposer's earliest moments: the lowest sum of play positions, then the seconds
  nearest the middle of the range). The search stops at the FIRST package that passes every gate.
- Time-sensitive moments ('today', a price level) must come from a source <= 24 h old (L-v 3; usable() enforces it on
  the build clock, and the render re-checks on its own clock). The window itself is the build driver's --hours (72 by
  default), not in this diff.

The order this diff implements (ORCHESTRATOR RULING 57, 09:59 ET Nov 13, the part that is code): "When several line-ups
pass, prefer the one with the newest clips; a line-up with at least one clip from the last 24 h is preferred over one
with none."

The change (pipeline/package.py, tests/package/test_medley.py):
1. FRESH_H = 24.0. fresh_key(segs, now) = (holds a clip <= FRESH_H old on the clock `now`, minus the mean age in
   hours). A clip with no readable publish time is never fresh and counts as the oldest.
2. lineup_for(..., now=None):
   - with now, its key is (fresh, newest, the proposer's earliest, the seconds nearest the middle);
   - without now, the key is unchanged, so every other caller behaves as before;
   - every rule is unchanged, and the chosen clips still play in the proposer's order.
3. pool_fill(..., now=None) passes now through. build() passes ctx.now to lineup_for and pool_fill.
4. build(): before the line-ups, the angles are stably re-ordered so that an angle whose first line-up (lineup_for
   with now) holds a fresh clip is tried before one whose line-up does not. Within each group the writer's order
   stands. out["angles"] records the order tried.
5. tests:
   - with now, a line-up with a fresh clip is chosen over the proposer's earliest;
   - with nothing fresh, the newest clips are chosen;
   - without now, nothing changes;
   - no readable time is never fresh;
   - the build judges the writer's second angle first when only its line-up holds fresh clips.
- test_medley 92 OK; every other suite OK.

Stated readings (say so if you read the ruling differently):
- K1: a build stops at its first passing package, so "when several line-ups pass, prefer..." is applied to the ORDER
  of trying: the fresh-first line-up inside an angle, and fresh-first angles across the build. The alternative,
  continuing to search after a pass to compare passing packages, would spend the search budget twice.
- K2: "newest clips" is the mean age of the line-up's segments, the hook included.
- K3: recency now ranks above the proposer's earliest-moment preference (a heuristic, not a law); the proposer's PLAY
  ORDER is kept.

Check in particular: that no line-up rule changed; that time-sensitive moments are not affected; that the angle
re-order is stable and only by freshness; the cost of the extra lineup_for call per angle; the no-time cases.

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
