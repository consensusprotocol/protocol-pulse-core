# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0510
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 59 s finish=stop usage in 13963 / out 3493 usd~0.094 (upper-bound price)

# Audit: pp-selectid-0510 (Ruling 41 — line-up search)

Scope: only the diff shown (package.py, test_medley.py). I cannot see `lineup_for`, `medley`, `Rig`, or the rest of package.py, so several conclusions are conditional on the stated contracts.

## P0

None found.

## P1

**P1-1 — `swap_lineup` can re-judge a moment already in `dropped`/`doomed` via the weak-set path, but not via the swap candidates — actually the reverse: candidates are filtered, but the *kept* segments are not re-checked against `dropped` added in the same iteration.**
package.py:206–213 (diff lines). Flow: `weak` moments are added to `dropped` (line 206) *and* swapped out, so they cannot reappear as kept segments. Candidates come from `cleared` minus `used` minus `avoid = dropped | doomed` (line 208), so dropped moments cannot be re-picked. However, `avoid` is only passed at the swap call; on the *next* loop iteration when `swapped` is not None, the swapped line-up is judged without re-deriving `avoid` — that's fine. The real risk: if `swap_lineup` returns `(None, None)` (no swap fits), the code falls through with `swapped = None` and the next iteration calls `lineup_for(..., frozenset(dropped | doomed))` — correct. But note `rec["why"]` says "no swap fits... re-lined" while `continue` re-enters the loop and `lineup_for` may return the *same* line-up minus dropped moments; since `dropped` grew, it differs. Verified no infinite loop **only if** `lineup_for` always returns a line-up excluding `dropped` (contract assumed, not visible). If `lineup_for` can return a line-up containing a just-dropped moment (e.g. when the supply exception forces `repeat_ok`), the loop could re-judge the same failing line-up until `total` hits 8 — bounded, so not a hang, but it burns the 8-line-up budget. **Scenario:** 11 moments, one angle, a clip rated 2 that `lineup_for` keeps selecting because it's the only clip-eligible moment for its channel; each iteration drops it, swaps fail, `lineup_for` re-picks... — actually once dropped it's excluded, so this converges. Downgrade: bounded by `total < 8` either way. Keep as P1 only for the *budget* consequence: each wasted re-line still counts against `total` and the search budget, with no `rec["why"]` distinguishing "re-judged identical" — observability, not correctness. Conditional; flag for author confirmation that `lineup_for` excludes `dropped` (the call passes `frozenset(dropped | doomed)`, so likely yes).

**P1-2 — `package_over` is checked only inside the writes loop, not before `medley()` or between the clips-alone verdict and the first write.**
package.py:216–224 (diff). `line = (time.time(), _spent(spend))` is taken *before* `medley(...)` (line 191), and `package_over(line)` is first consulted at the top of the `while w_used < writes` loop (line 220). If `medley` itself (a model call) blows the 15-min/$1.50 package budget, the overrun is only discovered at the first write check — the package still gets its writes (up to `writes` more calls) before `package_over` breaks. Actually the check *does* happen before write 1, so at most the overrun is detected one check late; but if `w_used` starts at 0 and the first `over_budget(ai)` (search) passes while `package_over` fails, the line-up's `rec["why"]` is set and the loop breaks — yet the code then proceeds to the no-voice / package-assembly path below (lines 227–236) guarded by `if not out["packages"] and not rec.get("why")...`. Wait: the `w_over` break sets `rec["why"]`, and the later block at line 231 only fires when there's no `why` — good. But does the broken-write line-up still get its clips-alone `med` recorded and, if a *previous* write in the same line-up passed its gates, still ship a package? If a package was already produced, `out["packages"]` is non-empty and the budget stop is moot — fine. Residual: the 15-min wall is enforced only at write boundaries; a line-up whose writes never start (e.g. `medley` fails) never checks `package_over` at all, so its `line` spend is silently absorbed into the search. That matches "the search goes on" semantics, but it means a *delivered package's* preceding failed line-ups' spend is not counted against the $1.50 — is that intended? Ruling 41 says "per PACKAGE delivered... counted from its own line-up's clips-alone verdict." The code counts from *before* the clips-alone verdict (`line` is set before `medley`), i.e. it includes the clips-alone call's cost. That's *stricter* than the ruling, not looser — acceptable, but the docstring says "counted from its own line-up's clips-alone verdict" while the code starts the clock before the verdict. Minor spec/code mismatch: **P1-2** (docstring/line 191 vs ruling text). Not a dodge; the package cannot exceed $1.50 by this.

**P1-3 — `swap_lineup`'s hook-candidate filter duplicates eligibility logic; divergence risk with `lineup_for`.**
package.py:66–69 vs `lineup

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 13962 / out 306 usd~0.077 (upper-bound price)

**P0 findings:** None verifiable from diff.  
**P1 findings:** None verifiable from diff.  
**P2 findings:**  
- pipeline/package.py:29 (lineup_ok): extracts exactly the rules stated in lineup_for docstring (hook eligibility+G17a, clip eligibility, LY_CLIPS count, one-per-channel or repeat_ok, SHORT_CLIP_S last, crange, stand_alone_check); test at :334 confirms lineup_for outputs pass it.  
- pipeline/package.py:200 (build): weak now includes hook (COHERENCE_MIN=4 unchanged); swap_lineup:200-212 respects dropped/doomed via avoid, grows dropped on no-swap path, free excludes used+avoid → no re-judge/loop possible.  
- pipeline/package.py:158,191,220 (build): total counts every judged line-up across angles (while total < LINEUPS_PER_BUILD); search budget (over_budget) from t0 ends build, package_over from per-line clips-alone start ends only that line-up's writes; test at :281-287 verifies no dodge.  
- pipeline/package.py:172-182,208 (build+swap): swapped line-ups still route through full medley()→gates, supply_exception, no_voice, question_hook, write loop; nothing else altered.  
- tests/package/test_medley.py:308-354: all swap/lineup_ok/build behaviors in ruling 41 description are exercised with exact constants and outcomes.  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 241 s finish=stop usage in 15267 / out 3742 usd~0.102 (upper-bound price)

# Audit: pp-selectid-0510 (Ruling 41: Line-up Search)

## P0 Findings

**1. `pipeline/package.py` (approx. line 158 in diff / `build` loop): Infinite Loop on Swap Failure**
The `while` loop condition is `while total < lineups ...`. Inside the loop, when `medley` fails (`ok_m` is False), the code calls `swap_lineup`.
- If `swap_lineup` returns `(None, None)` (no valid swap found), the code sets `rec["why"]` and executes `continue`.
- Crucially, `total` is **not** incremented in this path (it is only incremented at line 190, *after* a valid `segs` is established and before `medley` is called).
- The `dropped` set is updated with `weak`, but if `swap_lineup` fails, the code does **not** fall back to `lineup_for` to generate a *new* line-up from the remaining pool. It simply `continue`s.
- On the next iteration, `swapped` is `None`, so it calls `lineup_for(angle, cleared, frozenset(dropped | doomed), ...)`.
- **The Bug:** If `lineup_for` returns the **exact same** line-up as before (e.g., because the "weak" moments were not actually excluded from the pool in a way that changes the selection, or if `lineup_for`'s internal logic doesn't strictly respect `dropped` for the *hook* or if the pool is small), the loop will repeat the same `medley` call, fail again, and `continue` again.
- **Wait, let's look closer at `lineup_for` usage:**
  - Line 176: `segs, exception = lineup_for(..., frozenset(dropped | doomed), ...)`
  - If `swap_lineup` fails, `dropped` contains the `weak` moments.
  - If `lineup_for` respects `dropped`, it *should* pick different moments.
  - **However**, consider the case where `weak` contains the **Hook**.
  - `swap_lineup` tries to swap the hook. If it fails, `dropped` now contains the old Hook.
  - Next iteration: `lineup_for` is called with `dropped` containing the old Hook. It picks a new Hook.
  - If the new Hook also fails `medley`, `weak` contains the new Hook. `swap_lineup` tries to swap it.
  - If `swap_lineup` fails again, `dropped` contains both Hooks.
  - This seems safe *if* `lineup_for` always picks a different moment when the previous one is in `dropped`.
  - **BUT**, look at the `continue` path when `swap_lineup` returns `None`.
  - The code does:
    ```python
    swapped, swaps = swap_lineup(...)
    rec["why"] = ...
    continue
    ```
  - It does **not** increment `total`.
  - It does **not** break.
  - It relies on the next `lineup_for` call to produce a *different* line-up.
  - If `lineup_for` returns `None` (no line-up possible), the code breaks (line 187-188).
  - If `lineup_for` returns a line-up, `total` is incremented (line 190).
  - **Is there a scenario where `lineup_for` returns the same line-up?**
    - `lineup_for` takes `dropped` as a parameter. It should exclude those moments.
    - If the pool is exhausted, it returns `None`.
    - If the pool is not exhausted, it picks the best available.
    - So, it *should* pick a different line-up.
    - **However**, there is a subtle issue: `swap_lineup` uses `pool` (the `cleared` dict). `lineup_for` also uses `cleared`.
    - If `swap_lineup` fails because no *valid* swap exists (e.g., all other hooks are ineligible, or all other clips are ineligible), but `lineup_for` *can* still form a line-up (perhaps by changing the *order* or picking a different combination that `swap_lineup` didn't consider because it only swaps *weak* spots), then `lineup_for` will return a new line-up.
    - **The Risk:** If `lineup_for` returns a line-up that is *identical* to the one just failed, we loop.
    - Can `lineup_for` return the same line-up? Only if the `dropped` set does not effectively change the selection.
    - `dropped` is updated with `weak`. `weak` contains the moments that failed.
    - So the failed moments are now in `dropped`.
    - `lineup_for` excludes `dropped`.
    - Therefore, the new line-up *cannot* contain the failed moments.
    - So the line-up *must* be different.
    - **Conclusion:** The loop *should* terminate because the state space of possible line-ups is finite and we are strictly excluding failed moments from future consideration via `dropped`.
    - **Wait**, does `lineup_for` *always* exclude `dropped`?
      - Line 176: `lineup_for(angle, cleared, frozenset(dropped | doomed), ...)`
      - Yes.
    - **So, is it safe?**
      - If `lineup_for` returns `None`, we break.
      - If it returns a line-up, it's different from the last one (because the last one's weak moments are now in `dropped`).
      - So `total` will increment on the next successful `lineup_for` call.
      - **However**, what if `lineup_for` returns a line-up, but `medley` fails, and `swap_lineup` fails, and `lineup_for` returns *another* line-up, and `medley` fails...
      - This is the intended search.
      - **The P0 is actually a P1/P2 risk of inefficiency, not an infinite loop, UNLESS `lineup_for` has a bug where it igno

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0510 (ruling 41: the line-up search): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers package.py and test_medley.py. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- glm: "yes with conditions";
- qwen: "Yes with Conditions". It lists a "P0" (an infinite loop on a swap failure) and then resolves it in its own text.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | After a failed swap, can the re-line re-judge a dropped moment, or loop (qwen "P0"-1 and condition 1, glm P1-1 and condition 2)? | VERIFIED: no. lineup_for begins with `ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]`, and both of build()'s calls (one per channel, and repeat_ok) pass `frozenset(dropped \| doomed)`. The weak moments join `dropped` before the swap, so neither the swap nor the re-line can pick them again. `total` grows before EVERY clips-alone verdict, so the loop is bounded by `lineups` (8). A None line-up ends the angle. |
| K2 | Is the hook in the verdict's ratings, and is the label map right (qwen conditions 2 and 3)? | VERIFIED. medley() rates the labels of labels(n) = ["hook", "clip_01", ...], and the old code's `lb != "hook"` filter on the same dict is the proof that "hook" is a key. by_lab = dict(zip(labs, segs)) maps the same labels to the line-up in order. The tests swap a hook rated 3. |
| K3 | SWAP_TOP truncated the candidates BEFORE the place's own rule, so a fitting deeper candidate could be missed (glm P1-3 and condition 3) | IMPLEMENTED: a clip candidate for a non-last place must be at least SHORT_CLIP_S long BEFORE the cap, and SWAP_TOP is 10. Tested: 12 short clips ranked above a full clip; the full clip fills a middle place. |
| K4 | The package_over docstring says the clock starts "from its clips-alone verdict", while the code takes it just before the call (glm P1-2 and condition 1) | ALIGNED: "counted from the moment its own line-up's clips-alone verdict is asked". It is checked before every write. A line-up that never writes (its verdict failed) spends only the verdict call, which counts toward the search budget. |

## Kept

- **glm P1-2 (the 15-minute wall is enforced at write boundaries):** KEPT. The checks sit before every write, as ruling 5's did ("checked before every line-up and every write", audit 2240). One write plus its gates (about 3-5 min) is the most that can run past.
- **qwen P1s (scope, break conditions):** each verified in its own text.

## Verification

- test_medley 67 OK (the budget test rewritten; 6 search tests; the K3 test). All 11 suites and regression are run before the commit.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0510/C2_STEP.diff (370 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ac10906d..3aa6114f 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -72,6 +72,15 @@ COHERENCE_MIN = 4                  # the blind coherence verdict: every rating >
   6 |  BUDGET_WALL_S = 900.0              # orchestrator 22:40 ruling 5 (Heimdall as the writer; was 05:25 item 5's 360 s x2):
   7 |  BUDGET_USD_REPORTED = 1.50         # per package 15 min wall and $1.50 by the vendors' OWN reported cost,
   8 |  BUDGET_USD_ESTIMATE = 5.00         # with the price-table estimate (it over-states ~7x) only as a hard ceiling
   9 | +LINEUPS_PER_BUILD = 8              # RULING 41 (04:58 ET Nov 13): up to 8 line-ups per BUILD, over every angle. A clips-
  10 | +                                   # alone failure is answered by swapping the segments rated below the bar (swap_lineup);
  11 | +                                   # the bar itself is unchanged
  12 | +SEARCH_USD_REPORTED = 3.00         # ruling 41: a build may spend $3 (vendor-reported) searching, reported in out["search"];
  13 | +SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE delivered (its own line-up). The estimate
  14 | +                                   # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
  15 | +SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
  16 | +SWAP_TOP = 10                      # candidates read per swapped place, best by score first, after the place's own
  17 | +                                   # rules (a short clip only at the last place): audit 0510 C1, glm P1-3
  18 |  NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
  19 |  WRITER_DEADLINE_S = 300.0          # ruling 5: one writer call never waits more than 5 min; it fails over (deepseek ->
  20 |                                     # qwen -> xAI in the writer chain) and the failover is recorded
  21 | @@ -612,6 +621,80 @@ def no_role_on_screen(m):
  22 |      return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
  23 |  
  24 |  
  25 | +def lineup_ok(segs, crange=None, repeat_ok=False):
  26 | +    """The rules lineup_for applies, checked on a GIVEN line-up in play order -> (ok, why): the hook can open (hook
  27 | +    eligibility and the G17a measure), every clip is clip-eligible, the hook + LY_CLIPS clips, one segment per channel
  28 | +    (or, repeat_ok, one channel with two clips from two videos: L-y 4), at most PRICE_PREDICTIONS_MAX price predictions,
  29 | +    a clip under SHORT_CLIP_S only last, the seconds inside crange, and the render's STAND_ALONE (stand_alone_check)."""
  30 | +    lo, hi = crange or medley_content_range()
  31 | +    h, clips = segs[0], segs[1:]
  32 | +    if not LY_CLIPS[0] <= len(clips) <= LY_CLIPS[1]:
  33 | +        return False, f"{len(clips)} clips"
  34 | +    if not ((h.get("eligibility") or {}).get("hook", {}).get("ok") and (h.get("hook_onset") or {}).get("pass") is True):
  35 | +        return False, "the hook cannot open"
  36 | +    if not all((m.get("eligibility") or {}).get("clip", {}).get("ok") for m in clips):
  37 | +        return False, "a clip is not clip-eligible"
  38 | +    chans = [m["channel_id"] for m in segs]
  39 | +    if len(set(chans)) != len(segs) and not (repeat_ok and len(set(chans)) == len(segs) - 1 and
  40 | +                                             len({m["video_id"] for m in segs}) == len(segs)):
  41 | +        return False, "one segment per channel"
  42 | +    if sum("price_prediction" in m.get("risk", []) for m in segs) > PRICE_PREDICTIONS_MAX:
  43 | +        return False, "price predictions"
  44 | +    if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
  45 | +        return False, "a short clip that is not last"
  46 | +    dur = sum(m["duration_s"] for m in segs)
  47 | +    if not lo <= dur <= hi:
  48 | +        return False, f"{dur:.1f} s outside {lo}-{hi} s"
  49 | +    if not stand_alone_check(segs)["ok"]:
  50 | +        return False, "the render's STAND_ALONE"
  51 | +    return True, "ok"
  52 | +
  53 | +
  54 | +def swap_lineup(segs, weak, pool, avoid=frozenset(), crange=None):
  55 | +    """RULING 41: the next line-up after a clips-alone failure. Every segment in `weak` (moment ids rated below the
  56 | +    bar) is swapped AT ITS PLACE for the next candidate by score from the whole cleared pool: the hook for the next hook
  57 | +    by its first 2 s (scores.hook_first_2s), a clip for the next clip by rank_score. The segments rated 4-5 stay where
  58 | +    they are. The first combination (up to SWAP_TOP candidates per place, in score order) that passes lineup_ok wins,
  59 | +    one clip per channel first, then L-y 4's supply exception. -> (segs, {old id: new id}) or (None, None)."""
  60 | +    used = {m["moment_id"] for m in segs}
  61 | +    places = [i for i, m in enumerate(segs) if m["moment_id"] in weak]
  62 | +    if not places:
  63 | +        return None, None
  64 | +    free = [m for m in pool.values() if m["moment_id"] not in used and m["moment_id"] not in avoid]
  65 | +
  66 | +    def cands(i):
  67 | +        if i == 0:
  68 | +            c = [m for m in free if (m.get("eligibility") or {}).get("hook", {}).get("ok")
  69 | +                 and (m.get("hook_onset") or {}).get("pass") is True]
  70 | +            c.sort(key=lambda m: (-m["scores"]["hook_first_2s"], -m["rank_score"], m["moment_id"]))
  71 | +        else:
  72 | +            c = [m for m in free if (m.get("eligibility") or {}).get("clip", {}).get("ok")
  73 | +                 and (i == len(segs) - 1 or m["duration_s"] >= SHORT_CLIP_S)]     # the place's own rule first
  74 | +            c.sort(key=lambda m: (-m["rank_score"], m["moment_id"]))
  75 | +        return c[:SWAP_TOP]
  76 | +    options = [cands(i) for i in places]
  77 | +    for repeat_ok in (False, True):
  78 | +        for combo in itertools.product(*options):
  79 | +            if len({m["moment_id"] for m in combo}) != len(combo):
  80 | +                continue
  81 | +            new = list(segs)
  82 | +            for i, m in zip(places, combo):
  83 | +                new[i] = m
  84 | +            if lineup_ok(new, crange, repeat_ok)[0]:
  85 | +                return new, {segs[i]["moment_id"]: m["moment_id"] for i, m in zip(places, combo)}
  86 | +    return None, None
  87 | +
  88 | +
  89 | +def supply_exception(segs, ctx):
  90 | +    """L-y 4: the reason a line-up takes two clips from one channel (two videos), else None."""
  91 | +    rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs) if sum(m["channel_id"] == c for m in segs) > 1]
  92 | +    if not rep:
  93 | +        return None
  94 | +    return (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
  95 | +            f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
  96 | +            f" gives two clips, from two videos (L-y 4)")
  97 | +
  98 | +
  99 |  def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
 100 |                 need_stand_alone=False):
 101 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 102 | @@ -1052,7 +1135,7 @@ def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 103 |  
 104 |  
 105 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 106 | -          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LY_LINEUPS):
 107 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LINEUPS_PER_BUILD):
 108 |      """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 109 |      item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 110 |      written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 111 | @@ -1142,19 +1225,32 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 112 |      doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 113 |  
 114 |      def over_budget(ai):
 115 | -        """Ruling 5 (22:40): per package 15 min wall / $1.50 reported / the $5 estimate ceiling. Checked before every
 116 | -        line-up and every write (audit 2240 C1, glm), not only when an angle ends. -> the stop record, or None."""
 117 | +        """The SEARCH budget (ruling 41, 04:58): a build may spend $3.00 vendor-reported searching ($10.00 estimate
 118 | +        ceiling), inside SEARCH_WALL_S. Checked before every line-up and every write. -> the stop record (it ends the
 119 | +        build), or None. Ruling 5's 15 min / $1.50 is per PACKAGE delivered: package_over()."""
 120 |          used_s = time.time() - t0
 121 |          est, rep = (a - b for a, b in zip(_spent(spend), usd0))
 122 | -        if used_s <= BUDGET_WALL_S and rep <= BUDGET_USD_REPORTED and est <= BUDGET_USD_ESTIMATE:
 123 | +        if used_s <= SEARCH_WALL_S and rep <= SEARCH_USD_REPORTED and est <= SEARCH_USD_ESTIMATE:
 124 |              return None
 125 | -        out["why_none"] = (f"stopped in angle {ai + 1} of {len(angles)}: {used_s:.0f} s of {BUDGET_WALL_S:.0f} s wall / "
 126 | -                           f"${rep:.2f} of ${BUDGET_USD_REPORTED:.2f} reported / ${est:.2f} of the "
 127 | -                           f"${BUDGET_USD_ESTIMATE:.2f} estimate ceiling (ruling 5, 22:40)")
 128 | +        out["why_none"] = (f"stopped in angle {ai + 1} of {len(angles)}: the search spent {used_s:.0f} s of "
 129 | +                           f"{SEARCH_WALL_S:.0f} s / ${rep:.2f} of ${SEARCH_USD_REPORTED:.2f} reported / ${est:.2f} of "
 130 | +                           f"the ${SEARCH_USD_ESTIMATE:.2f} estimate ceiling (ruling 41, 04:58)")
 131 |          out["budget_stop"] = {"seconds": round(used_s, 1), "usd_reported": round(rep, 4), "usd_estimate": round(est, 4),
 132 |                                "angles_tried": ai + 1, "angles": len(angles)}
 133 |          return out["budget_stop"]
 134 |  
 135 | +    def package_over(line):
 136 | +        """Ruling 5 (22:40) as ruling 41 reads it: per PACKAGE delivered, 15 min wall and $1.50 reported (the $5
 137 | +        estimate ceiling), counted from the moment its own line-up's clips-alone verdict is asked (line = (time, spend
 138 | +        then)). Checked before every write. -> why this line-up stops (the search goes on), or None."""
 139 | +        l_s = time.time() - line[0]
 140 | +        l_est, l_rep = (a - b for a, b in zip(_spent(spend), line[1]))
 141 | +        if l_s <= BUDGET_WALL_S and l_rep <= BUDGET_USD_REPORTED and l_est <= BUDGET_USD_ESTIMATE:
 142 | +            return None
 143 | +        return (f"this line-up's package spent {l_s:.0f} s of {BUDGET_WALL_S:.0f} s / ${l_rep:.2f} of "
 144 | +                f"${BUDGET_USD_REPORTED:.2f} reported / ${l_est:.2f} of the ${BUDGET_USD_ESTIMATE:.2f} estimate (ruling 5, "
 145 | +                f"per package delivered: ruling 41)")
 146 | +
 147 |      def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup):
 148 |          """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 149 |          viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 150 | @@ -1243,23 +1339,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 151 |              f"{sum(m['duration_s'] for m in order):.1f} s, added {added}) ({time.time() - t0:.0f} s)")
 152 |          return pk
 153 |  
 154 | +    total = 0                                             # ruling 41: line-ups judged in this build, over every angle
 155 |      with ThreadPoolExecutor(max_workers=8) as pool:
 156 |          for ai, angle in enumerate(angles):
 157 | -            dropped, n_lineup = set(), 0
 158 | -            while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
 159 | +            dropped, n_lineup, swapped = set(), 0, None
 160 | +            while total < lineups and not out["packages"] and not out.get("budget_stop"):
 161 |                  if over_budget(ai):
 162 |                      break
 163 | -                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 164 | -                                             need_stand_alone=True), None
 165 | -                if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 166 | -                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
 167 | -                                     need_stand_alone=True)
 168 | -                    if segs is not None:
 169 | -                        rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 170 | -                               if sum(m["channel_id"] == c for m in segs) > 1]
 171 | -                        exception = (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
 172 | -                                     f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
 173 | -                                     f" gives two clips, from two videos (L-y 4)")
 174 | +                if swapped is not None:                   # ruling 41: the swapped line-up is judged next
 175 | +                    segs, swapped = swapped, None
 176 | +                    exception = supply_exception(segs, ctx)
 177 | +                else:
 178 | +                    segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
 179 | +                                                 need_stand_alone=True), None
 180 | +                    if segs is None:                      # L-y 4: one clip per channel unless the supply forces otherwise
 181 | +                        segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
 182 | +                                          need_stand_alone=True)
 183 | +                        if segs is not None:
 184 | +                            exception = supply_exception(segs, ctx)
 185 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 186 |                         "supply_exception": exception, "attempts": []}
 187 |                  out["tried"].append(rec)
 188 | @@ -1267,6 +1364,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 189 |                      rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 190 |                      break
 191 |                  n_lineup += 1
 192 | +                total += 1
 193 | +                line = (time.time(), _spent(spend))         # this line-up's package budget counts from here (ruling 41)
 194 |                  ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 195 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 196 |                  log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 197 | @@ -1276,14 +1375,18 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 198 |                  if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 199 |                      by_lab = dict(zip(labs, segs))
 200 |                      weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 201 | -                            if lb in by_lab and lb != "hook" and x < COHERENCE_MIN}
 202 | +                            if lb in by_lab and x < COHERENCE_MIN}      # ruling 41: the HOOK too (the next hook)
 203 |                      if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 204 |                          weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 205 |                      if not med.get("measured") or not weak:
 206 |                          rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 207 |                          break
 208 |                      dropped |= weak
 209 | -                    rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
 210 | +                    swapped, swaps = swap_lineup(segs, weak, cleared, frozenset(dropped | doomed))
 211 | +                    rec["why"] = (f"the clips alone fail (ratings / joins): swapped {swaps}, re-judged (ruling 41)"
 212 | +                                  if swapped is not None else
 213 | +                                  f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 214 | +                                  f"line-up rules: re-lined")
 215 |                      continue
 216 |                  if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
 217 |                      dropped.add(segs[1]["moment_id"])
 218 | @@ -1301,6 +1404,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 219 |                  while w_used < writes:
 220 |                      if over_budget(ai):
 221 |                          break
 222 | +                    w_over = package_over(line)
 223 | +                    if w_over:
 224 | +                        rec["why"] = w_over
 225 | +                        break
 226 |                      w_used += 1
 227 |                      try:
 228 |                          wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 229 | @@ -1448,11 +1555,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 230 |                      if nv is not None:
 231 |                          out["packages"].append(nv)
 232 |                          rec["result"] = "PACKAGE (no voice, ruling 3)"
 233 | +                if not out["packages"] and not rec.get("why") and not rec.get("result"):
 234 | +                    last = (rec.get("attempts") or [{}])[-1]
 235 | +                    rules = sorted({str(v.get("rule")) for v in last.get("violations") or []})
 236 | +                    rec["why"] = f"{w_used} write(s) failed their gates" + (f" ({', '.join(rules)})" if rules else "")
 237 |                  if out["packages"] or not relined:
 238 |                      break
 239 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
 240 |                  break
 241 |      out["package"] = out["packages"][0] if out["packages"] else None
 242 | +    s_est, s_rep = (a - b for a, b in zip(_spent(spend), usd0))
 243 | +    out["search"] = {"lineups": total, "limit": lineups, "usd_reported": round(s_rep, 4),
 244 | +                     "usd_estimate": round(s_est, 4), "seconds": round(time.time() - t0, 1)}
 245 | +    log(f"  search: {total} line-up(s) of {lineups}, ${s_rep:.2f} reported / ${s_est:.2f} estimate (ruling 41: $3.00 "
 246 | +        f"reported per build)")
 247 |      if out["package"] is None and not out.get("why_none"):       # every angle ended without a package: say why
 248 |          out["why_none"] = ("no angle gave a package: " + "; ".join(
 249 |              f"angle {t.get('angle')}: {str(t.get('why') or t.get('result') or 'no reason recorded')[:250]}"
 250 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 251 | index 0ee53c23..d00f10db 100644
 252 | --- a/tests/package/test_medley.py
 253 | +++ b/tests/package/test_medley.py
 254 | @@ -608,23 +608,31 @@ class TestBuildLoop(unittest.TestCase):
 255 |          self.assertEqual(out["angle_backend"], "fake:angle_write")
 256 |          self.assertEqual(out["angle_tried"], [])
 257 |  
 258 | -    def test_the_budget_stops_on_the_reported_cost_or_the_estimate_ceiling(self):
 259 | -        """Ruling 5 (22:40): per package 15 min wall / $1.50 by the vendors' reported cost; the estimate only as a $5
 260 | -        ceiling. Checked before every line-up and every write (audit 2240 C1, glm), not only when an angle ends."""
 261 | -        for spent, why in (((0.10, 1.51), "reported"), ((5.01, 0.20), "estimate ceiling")):
 262 | +    def test_the_search_budget_ends_the_build_and_the_package_budget_ends_only_its_line_up(self):
 263 | +        """Ruling 41 (04:58): a build may spend $3.00 reported searching (a $10.00 estimate ceiling); ruling 5's $1.50 /
 264 | +        15 min is per PACKAGE delivered, counted from its own line-up's clips-alone verdict."""
 265 | +        for spent, why in (((0.10, 3.01), "reported"), ((10.01, 0.20), "estimate ceiling")):
 266 |              reads = [(0.0, 0.0), (0.0, 0.0)]                  # the baseline, then the check before line-up 1
 267 | -            calls = iter(reads + [spent] * 50)                # ... then over budget from the next check on
 268 | +            calls = iter(reads + [spent] * 80)                # ... then over the search budget from the next check on
 269 |              rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(False, [], None, "none")] * 2, [],
 270 |                        spend=lambda: next(calls))
 271 |              out = rig.run()
 272 | -            self.assertIn("ruling 5", out["why_none"], why)
 273 | +            self.assertIn("ruling 41", out["why_none"], why)
 274 |              self.assertEqual(len(rig.medley_calls), 1, why)          # line-up 1 ran; nothing after the stop
 275 |              self.assertEqual(out["budget_stop"]["angles_tried"], 1, why)
 276 | -        over = iter([(0.0, 0.0)] + [(9.0, 9.0)] * 50)               # over budget from the very first check
 277 | +            self.assertEqual(out["search"]["lineups"], 1, why)
 278 | +        over = iter([(0.0, 0.0)] + [(11.0, 11.0)] * 80)             # over the search budget from the very first check
 279 |          rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], spend=lambda: next(over))
 280 |          out = rig.run()
 281 |          self.assertEqual((rig.medley_calls, rig.write_calls), ([], []))   # no clips-alone call, no write paid
 282 |          self.assertIsNone(out["package"])
 283 | +        rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(True, [], None, Rig.LINE)] * 2, [None, None])
 284 | +        rig.spend = lambda: (0.0, 1.6) if rig.medley_calls else (0.0, 0.0)  # line-up 1's package: $1.60 > $1.50
 285 | +        out = rig.run()
 286 | +        self.assertIn("per package delivered", out["tried"][0]["why"])      # only that line-up stopped
 287 | +        self.assertEqual(len(rig.write_calls), 1)                          # line-up 2 (its own $0.00) wrote
 288 | +        self.assertIsNotNone(out["package"])                               # the search went on: $1.60 < $3.00
 289 | +        self.assertEqual((out["search"]["lineups"], out["search"]["usd_reported"]), (2, 1.6))
 290 |  
 291 |      def test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up(self):
 292 |          """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
 293 | @@ -726,6 +734,76 @@ class TestStandAloneAtThePinStage(unittest.TestCase):
 294 |          self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 295 |  
 296 |  
 297 | +class TestRuling41Search(unittest.TestCase):
 298 | +    """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
 299 | +    place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
 300 | +    ones rated 4-5 kept; up to 8 line-ups per build; the bar unchanged."""
 301 | +
 302 | +    def pool(self, *spec):
 303 | +        out = {}
 304 | +        for mid, ch, dur, rank, h2s in spec:
 305 | +            m = dict(pm(mid, ch, dur, rank=rank), hook_onset={"pass": True})
 306 | +            m["scores"] = dict(m["scores"], hook_first_2s=h2s)
 307 | +            out[mid] = m
 308 | +        return out
 309 | +
 310 | +    def test_a_clip_below_the_bar_is_swapped_at_its_place_for_the_next_clip_by_rank(self):
 311 | +        p = self.pool(("h", "A", 12.0, 9.0, 4), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 312 | +                      ("z", "D", 13.0, 5.0, 3), ("w", "E", 13.0, 8.0, 3), ("v", "B", 13.0, 9.5, 3))
 313 | +        segs = [p["h"], p["x"], p["y"]]
 314 | +        new, swaps = PK.swap_lineup(segs, {"x"}, p)
 315 | +        self.assertEqual([m["moment_id"] for m in new], ["h", "v", "y"])     # v: the best rank, x's place, B again
 316 | +        self.assertEqual(swaps, {"x": "v"})
 317 | +        new, swaps = PK.swap_lineup(segs, {"x"}, p, avoid={"v"})
 318 | +        self.assertEqual([m["moment_id"] for m in new], ["h", "w", "y"])     # then the next by rank
 319 | +        self.assertTrue(PK.lineup_ok(new)[0])
 320 | +
 321 | +    def test_a_hook_below_the_bar_is_swapped_for_the_next_hook_by_score(self):
 322 | +        p = self.pool(("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 323 | +                      ("g", "D", 12.0, 1.0, 5), ("k", "E", 12.0, 9.9, 2))
 324 | +        new, swaps = PK.swap_lineup([p["h"], p["x"], p["y"]], {"h"}, p)
 325 | +        self.assertEqual(swaps, {"h": "g"})                                  # by hook_first_2s, not by rank
 326 | +        p["g"]["hook_onset"] = {"pass": False}                               # a hook must still open (G17a)
 327 | +        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], {"h"}, p)[1], {"h": "k"})
 328 | +
 329 | +    def test_the_place_s_own_rule_comes_before_the_cap(self):        # audit 0510 C1, glm P1-3
 330 | +        spec = [("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 1.0, 3), ("y", "C", 13.0, 9.0, 3)]
 331 | +        spec += [(f"s{i}", f"S{i}", 5.0, 9.0 - i / 100, 3) for i in range(12)]        # 12 short clips ranked higher
 332 | +        spec += [("f", "F", 14.0, 2.0, 3)]                                          # a full clip, ranked below them
 333 | +        p = self.pool(*spec)
 334 | +        new, swaps = PK.swap_lineup([p["h"], p["x"], p["y"]], {"x"}, p)              # x's place is not the last
 335 | +        self.assertEqual(swaps, {"x": "f"})
 336 | +
 337 | +    def test_no_swap_when_nothing_fits_the_line_up_rules(self):
 338 | +        p = self.pool(("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 339 | +                      ("s", "D", 3.0, 9.0, 3))                               # 12 + 3 + 13 = 28 s < the medley's seconds
 340 | +        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], {"x"}, p), (None, None))
 341 | +        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], set(), p), (None, None))
 342 | +
 343 | +    def test_lineup_for_s_own_line_ups_pass_lineup_ok(self):
 344 | +        p = self.pool(("h", "A", 12.0, 9.0, 4), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
 345 | +                      ("z", "D", 13.0, 9.0, 3), ("w", "E", 6.0, 9.0, 3))
 346 | +        for order in (["h", "x", "y", "z"], ["h", "w", "x", "y"], ["x", "h", "z", "w"]):
 347 | +            segs = PK.lineup_for(angle(order, order[0]), p, need_onset=True, need_stand_alone=True)
 348 | +            if segs is not None:
 349 | +                self.assertEqual(PK.lineup_ok(segs), (True, "ok"), order)
 350 | +
 351 | +    def test_the_build_swaps_a_low_rated_hook_and_stops_at_8_line_ups(self):
 352 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
 353 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
 354 | +        out = rig.run()
 355 | +        self.assertEqual(rig.medley_calls[0][0], "h")
 356 | +        self.assertNotEqual(rig.medley_calls[1][0], "h")                    # the hook rated 3 was swapped
 357 | +        self.assertIn("swapped", out["tried"][0]["why"])
 358 | +        self.assertIsNotNone(out["package"])
 359 | +        many = [pm(c, c.upper(), 13.0) for c in "abcdefghijklmnop"]
 360 | +        fails = [(False, [], {"clip_01": 2}, Rig.LINE)] * 12
 361 | +        rig = Rig(many, [list("abcdefgh"), list("ijklmnop"), list("aceg")], fails, [])
 362 | +        out = rig.run()
 363 | +        self.assertEqual(len(rig.medley_calls), PK.LINEUPS_PER_BUILD)       # 8, over every angle
 364 | +        self.assertEqual(out["search"]["lineups"], 8)
 365 | +
 366 | +
 367 |  class TestRuling37QuestionHook(unittest.TestCase):
 368 |      """Ruling 37: a clip ending on a question may be the HOOK only; the clips-alone verdict judges the join after it,
 369 |      which must be followable with no bridge (no bridge may follow a question; the render's R1 reads the sealed
 370 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway).

How package.build() works:
- An angle step proposes up to 3 angles, each a set of moments in play order.
- Per angle, lineup_for() picks a line-up: the hook + clips inside the medley's seconds, one per channel, a short clip
  only last, the render's STAND_ALONE.
- A blind clips-alone verdict (medley()) rates each segment 1-5 and judges each join. It passes only with a
  through-line and every rating >= COHERENCE_MIN (4).
- Then the writes and the gates. The first package that passes every hard gate wins.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why: ORCHESTRATOR ORDER 04:58 ET Nov 13, RULING 41 (LINE-UP SEARCH): "With 11 cuttable moments and 8 possible hooks,
two line-ups is not a search. When the clips-alone verdict fails, read WHICH clip rated below the bar and swap that
clip (a hook rated 3 -> the next hook by score; a clip rated 2 -> the next clip), keep the ones rated 4-5, and
re-judge. Up to 8 line-ups per build, inside the package budget ($1.50 / 15 min is per PACKAGE delivered; a build may
spend up to $3 searching, report it). Stop at the first that passes. The bar itself is unchanged."
- Before: 2 line-ups per angle. A low-rated HOOK was never swapped: the old code excluded the hook from the weak set,
  and its angle ended. A low-rated clip was re-lined only from the angle's own moments (often 4).
- Ruling 5's budget (15 min wall / $1.50 reported / $5 estimate) was counted from the build's start, so step A, L-v 2
  and slow angle calls used it up before any line-up.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass. Every line-up the search judges must pass the
  same line-up rules, and the clips-alone bar (COHERENCE_MIN) and every gate are unchanged.

The change (pipeline/package.py):
1. Constants:
   - LINEUPS_PER_BUILD = 8;
   - SEARCH_USD_REPORTED = 3.00, and SEARCH_USD_ESTIMATE = 10.00 (ruling 5's $5.00 : $1.50 ratio, for calls whose
     vendor reports no cost);
   - SEARCH_WALL_S = 2400 (the build ends cleanly before its driver's timeout; a killed build writes no record);
   - SWAP_TOP = 6.
2. lineup_ok(segs, crange, repeat_ok): lineup_for's rules checked on a GIVEN line-up:
   - the hook is hook-eligible and its G17a onset passed;
   - the clips are clip-eligible, and there are 2-4 of them;
   - one segment per channel, or repeat_ok with one channel giving two videos;
   - price predictions are capped;
   - a short clip plays only last;
   - the seconds are inside crange;
   - stand_alone_check passes.
3. swap_lineup(segs, weak, pool, avoid):
   - Each weak segment (rated below the bar) is swapped at its place for the next candidate by score from the WHOLE
     cleared pool: the hook for the next hook by scores.hook_first_2s, a clip by rank_score.
   - The others stay in place.
   - The first combination (up to SWAP_TOP per place) that passes lineup_ok wins, one per channel first, then the supply
     exception. -> (segs, {old: new}) or (None, None).
4. supply_exception(segs, ctx): the L-y 4 text, factored out verbatim, and now also used for swapped line-ups.
5. build():
   - lineups (default LINEUPS_PER_BUILD) counts line-ups judged over the WHOLE build.
   - On a clips-alone failure, the weak set includes the HOOK. No weak segment or an unmeasured verdict ends the
     angle, as before.
   - The weak moments join `dropped`, and swap_lineup proposes the next line-up (judged next). If no swap fits,
     lineup_for re-lines from the angle as before.
   - over_budget(ai) is now the SEARCH budget: $3.00 reported, $10.00 estimate and SEARCH_WALL_S from the build's
     start. It ends the build.
   - package_over(line): ruling 5's 15 min / $1.50 / $5, counted from each line-up's clips-alone verdict. It ends only
     that line-up; the search goes on.
   - A line-up whose writes all fail now records why. out["search"] reports the line-ups, the reported and estimated
     spend, and the seconds, with a log line.
6. Tests (tests/package/test_medley.py):
   - the budget test is rewritten to ruling 41's semantics;
   - swap_lineup (a clip at its place by rank, a hook by hook score, a hook must still open, none when nothing fits);
   - lineup_for's own line-ups pass lineup_ok;
   - the build swaps a low-rated hook, and stops at 8 line-ups over every angle.

Check in particular:
- that every line-up the search judges passes exactly the rules lineup_for applies (lineup_ok vs lineup_for), and the
  bar is unchanged;
- that the weak set, the swap and `dropped` cannot loop or re-judge a dropped moment;
- that the per-package budget cannot be dodged: a package is still bound by 15 min / $1.50 from its own line-up's
  start, and the search by $3.00;
- the counting of line-ups;
- that nothing else changes: the writes, the gates, the no-voice path and the per-clip drops.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
