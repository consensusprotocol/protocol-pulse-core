# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261118_1012
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 176 s finish=stop usage in 11258 / out 3541 usd_reported=0.000788 usd~0.087 (upper-bound price)

The code implements Rulings 148 (1) and 149, introducing a "never-empty" pass floor for medley runtimes.

### Analysis

1.  **Floor Leakage & Scope**: The use of the global `_FLOOR` is safely encapsulated within `build()` using a `try...finally` block. This ensures that the floor is only active during the `_build(soft=True)` call and is guaranteed to be reset to `None` regardless of whether the build succeeds or raises an exception. It cannot leak into the clean pass or subsequent builds.
2.  **Boundary Enforcement**:
    *   **Under 30s**: `ly_lo(lo)` returns `min(lo, 30.0)`. If a lineup's duration is $< 30.0\text{s}$, `lineup_ok` and `lineup_for` will correctly reject it.
    *   **Over 70s**: The upper bound `hi` (from `RUNTIME_S[1]`) remains unchanged in `lineup_ok`, ensuring videos over 70s are still rejected.
    *   **Non-Medleys**: `runtime_short(pk)` explicitly checks `pk.get("shape") != "medley"`. If the shape is not a medley, the function returns `None`, and `rt_ok` reverts to the standard `RUNTIME_S` range check.
3.  **Takeaway Budget Fallback**: The logic in `takeaway_budget` correctly handles the case where the standard range `lo..hi` is empty (meaning the content is too short to hit the 60s target). It allows a fallback range `(max(MIN, cap - 4), cap)` only when `_FLOOR` is active and the content meets the 30s minimum. This enables the "soft" pass to seal packages that the "clean" pass would have rejected.
4.  **Gate Integration**:
    *   `cheap_checks` now treats a package as `rt_ok` if it is either in the standard range OR has a valid `runtime_short` string.
    *   `inventory` correctly overrides the `status` of the "runtime" gate to `FLAGGED` when `short` is provided and `rt_ok` is True.
    *   `package_pin.SOFT_GATES` now includes `"runtime"`, allowing the integrator to authorize these flagged packages.
5.  **Tests**: The new test suite `TestRuling148RuntimeFloor` comprehensively covers the clean pass vs. soft pass distinction, the 30s hard floor, the 36.7s soft floor, and the takeaway budget logic.

### Findings

*   **[P3] Rounding in `runtime_short`**: `int(round(est))` may round a value like $59.6$ up to $60$. Since the function only executes if `est < 60`, it is possible to produce the string `"This video runs 60 seconds, shorter than usual."` for a video that is technically $59.6\text{s}$. This is a minor cosmetic discrepancy.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 53 s finish=stop usage in 9715 / out 8443 usd_reported=0.001347 usd~0.156 (upper-bound price)

**Findings**

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | Global `_FLOOR` can leak between concurrent builds | **P1** | `_FLOOR` is a module‑level variable that is set to `LY_FLOOR_S` before the soft pass and cleared in a `finally` block. If two `build()` invocations run concurrently, the second may see the `_FLOOR` value set by the first, causing the soft‑pass logic (e.g., `ly_lo`, `runtime_short`, `takeaway_budget`) to behave incorrectly for the first build or to leak into the clean pass. This race condition can lead to false positives/negatives in the runtime gate and other floor‑dependent checks. |
| 2 | None | **P0** | No other defects that would cause a gate to incorrectly pass or fail were identified. All logic paths in the new code satisfy the specified rules and tests. |

**P1_OR_WORSE:** 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 249 s finish=stop usage in 10567 / out 9710 usd_reported=0.008868 usd~0.177 (upper-bound price)



# Code Audit — pp-selectid (RULINGS 148(1)/149: 30 s floor + "runs short" flag)

## Findings

### [P2] `_FLOOR` global is not safe under concurrent `build()` calls

`pipeline/package.py` introduces a module-level mutable `_FLOOR` that is set and cleared around the never-empty pass:

```python
global _FLOOR
_FLOOR = LY_FLOOR_S
try:
    soft = _build(*args, soft=True, **kw)
finally:
    _FLOOR = None
```

The tech-stack section states **~1000 concurrent users at peak — every route must handle load**. If `build()` (or any code path that calls `ly_lo`, `takeaway_budget`, `runtime_short`, or `lineup_ok`) can be entered from more than one thread or greenlet while another `build()` is mid-never-empty-pass, the clean pass of the second caller will see `_FLOOR = 30.0` and accept 30–36.7 s line-ups it should refuse, or `runtime_short` will emit a flag for a package that was never in the never-empty pass.

The `finally` block guarantees cleanup for a single sequential call, but it does not protect against interleaving. The pipeline is described as a sequential batch (`run_fresh.py`, GPU0 only), so this may never fire in practice, but the pattern is a latent data-corruption bug the moment a Flask route, a retry, or a test harness calls `build()` concurrently.

**Suggested fix:** pass the floor as an explicit parameter through `_build` → `lineup_ok` / `lineup_for` / `takeaway_budget` / `runtime_short` (or use a `contextvars.ContextVar` if the call depth makes threading a parameter impractical). This also removes the need for the `global` statement and makes the state visible in every function signature.

---

### [P3] `int(round(est))` can display "60 seconds, shorter than usual"

In `runtime_short`:

```python
return RUNTIME_SHORT.format(n=int(round(est)))
```

If `est = 59.999` (just under `RUNTIME_S[0] = 60.0`), the guard `est >= RUNTIME_S[0]` is False, so the function proceeds, but `int(round(59.999))` is `60`. The sealed flag reads *"This video runs 60 seconds, shorter than usual."* — a listener (or a downstream text check under L-k) hears "60 seconds" and "shorter than usual" in the same sentence, which is self-contradictory.

The probability is low (the R4 estimate is a computed float, not a measured one), but the fix is trivial: use `int(est)` (floor) instead of `int(round(est))`, or guard with `est < RUNTIME_S[0] - 0.5` so the displayed integer is unambiguously below 60.

---

### [P3] Dangling comment line in `package_pin.py`

```python
                        "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
#   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
```

The second line of the comment starts at column 0, outside the `frozenset(...)` call. It is syntactically harmless (it's a module-level comment), but it breaks the visual grouping of the `SOFT_GATES` block and will confuse a reader scanning the set's entries. Move it inside the parenthesised block or attach it to the `"runtime"` line.

---

### [P3] Re-entrancy: a nested `build()` would corrupt the outer pass

If `_build` (or any helper it calls) ever re-enters `build()` — e.g., a future "try a different angle" retry that calls `build` recursively — the inner `build`'s `finally` clears `_FLOOR` to `None` while the outer never-empty pass is still running. The outer pass would then continue with `_FLOOR = None`, silently reverting to the clean-pass floor (36.7 s) for the remainder of its line-up search.

This is extremely unlikely in the current call graph, but the global-state pattern makes it a one-line refactor away from a real bug. The same fix as the [P2] finding (explicit parameter) eliminates this class of issue entirely.

---

## Items verified clean

| Question asked | Verdict |
|---|---|
| Can the floor leak into the clean pass? | No. `_FLOOR` is `None` during the clean pass; it is set only after the clean pass returns `None`. The `finally` clears it. (Subject to the [P2] concurrency caveat.) |
| Can a package under 30 s seal? | No. `lineup_ok` rejects `dur < ly_lo(lo) = 30.0`; `runtime_short` returns `None` when `sum(durations) < _FLOOR`. |
| Can a package over 70 s seal? | No. The upper bound `hi` in `lineup_ok` / `lineup_for` is unchanged. |
| Can a non-medley shape get the flag? | No. `runtime_short` requires `pk.get("shape") == "medley"`. |
| Can a bool sneak past the `isinstance(est, (int, float))` check? | No. `isinstance(est, bool)` is explicitly excluded. |
| Does the takeaway-budget fallback produce a valid (lo ≤ hi) range? | Yes. The guard `LY_TAKEAWAY_MIN_WORDS <= cap` ensures `max(MIN, cap−4) ≤ cap`. |
| Does `bridge_budget` inherit the fallback correctly? | Yes — it calls `takeaway_budget`, which now returns the shortened range in the pass. |
| Is the `SOFT_GATES` addition consistent with L-j (release aut

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261118_1012, rulings 148 (1) / 149: the 30 s floor and its flag)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none. gpt-oss-20b: one P1, REFUTED for this code base:
gpt-oss [P1] "the module-level _FLOOR can leak between concurrent build() calls": REFUTED. No process calls build()
concurrently. The one driver, tests/package/proof_ledger.py, calls PK.build in sequence (lines 607, 626, 638; no thread,
no pool anywhere in the file), then SPOT.build (648) after it. No other module calls package.build (grep). spotlight.py
reads none of ly_lo / runtime_short / takeaway_budget / lineup_ok / lineup_for. Each build is its own process
(build_and_record.sh), so a global is per build. Inside the never-empty pass the floor MUST be visible to the pass's own
worker threads (step A and the writes run on pools), which a thread-local or a context variable would not give (a pool
does not copy the context): the module global, set and cleared in build()'s try/finally, is the mechanism that does.
The clean pass has finished before it is set; the test asserts it is cleared after the pass.
P2/P3 notes: style only.

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261118_1012/C2_STEP.diff (209 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 250c4f1..c32b7d6 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -290,6 +290,12 @@ LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
   6 |  LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
   7 |                                     # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
   8 |  LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)
   9 | +LY_FLOOR_S = 30.0                  # RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18, standing from the 12:00 build):
  10 | +                                   # a medley's clips may total down to this in the never-empty pass; under
  11 | +                                   # medley_content_range()'s lo the package carries RUNTIME_SHORT; under it, refused
  12 | +LY_SHORT_SPAN_WORDS = 4            # clips too short to land 60 s: the takeaway is asked within this of its longest
  13 | +RUNTIME_SHORT = "This video runs {n} seconds, shorter than usual."   # 148 (1): the flag, NN the factory's estimate
  14 | +_FLOOR = None                      # LY_FLOOR_S while build() runs the never-empty pass (set and cleared there only)
  15 |  
  16 |  
  17 |  def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  18 | @@ -301,6 +307,23 @@ def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
  19 |      return round(lo, 2), round(hi, 2)
  20 |  
  21 |  
  22 | +def ly_lo(lo):
  23 | +    """RULINGS 148 (1) / 149: the clips' seconds floor of a line-up: lo, or LY_FLOOR_S under it while the never-empty
  24 | +    pass runs. Only the acceptance reads it; a search's preference keeps the calibrated middle."""
  25 | +    return lo if _FLOOR is None else min(lo, _FLOOR)
  26 | +
  27 | +
  28 | +def runtime_short(pk):
  29 | +    """RULINGS 148 (1) / 149: the plain sentence of a medley sealed under 60 s by the never-empty pass (its clips at
  30 | +    LY_FLOOR_S or more, the factory's estimate under RUNTIME_S[0]): RUNTIME_SHORT with NN the estimate in whole
  31 | +    seconds. None in the clean pass, for any other shape, at 60 s or more, or under the floor."""
  32 | +    est = pk.get("runtime_s_estimate")
  33 | +    if _FLOOR is None or pk.get("shape") != "medley" or not isinstance(est, (int, float)) or isinstance(est, bool) \
  34 | +            or est >= RUNTIME_S[0] or sum(sg["duration_s"] for sg in pk.get("segments") or []) < _FLOOR:
  35 | +        return None
  36 | +    return RUNTIME_SHORT.format(n=int(round(est)))
  37 | +
  38 | +
  39 |  def bridge_budget(content_s):
  40 |      """For a line-up that must carry one bridge (L-y 2), before the bridge is written: (n, (lo, hi)), the largest bridge
  41 |      limit n <= LY_BRIDGE_WORDS words such that ANY bridge of LY_BRIDGE_MIN_WORDS..n words with a takeaway of lo..hi
  42 | @@ -330,7 +353,9 @@ def takeaway_budget(content_s, other=()):
  43 |          lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
  44 |          if lo <= hi:
  45 |              return lo, hi
  46 | -    return None
  47 | +    if _FLOOR is not None and content_s >= _FLOOR and LY_TAKEAWAY_MIN_WORDS <= cap < words_at(RUNTIME_S[0]):
  48 | +        return max(LY_TAKEAWAY_MIN_WORDS, cap - LY_SHORT_SPAN_WORDS), cap     # RULINGS 148 (1) / 149: clips too short
  49 | +    return None                                                               # to land 60 s: the longest takeaway
  50 |  
  51 |  
  52 |  def r4_max_vo_words(content_s, n_vo):
  53 | @@ -1886,8 +1911,8 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  54 |      if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
  55 |          return False, "a short clip that is not last"
  56 |      dur = sum(m["duration_s"] for m in segs)
  57 | -    if not lo <= dur <= hi:
  58 | -        return False, f"{dur:.1f} s outside {lo}-{hi} s"
  59 | +    if not ly_lo(lo) <= dur <= hi:                       # RULINGS 148 (1) / 149: the floor in the never-empty pass
  60 | +        return False, f"{dur:.1f} s outside {ly_lo(lo)}-{hi} s"
  61 |      if not stand_ok(segs):                                   # RULING 141 (2): only marked clips' openers flag
  62 |          return False, "the render's STAND_ALONE"
  63 |      return True, "ok"
  64 | @@ -2021,7 +2046,7 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  65 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
  66 |                      continue
  67 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
  68 | -                if not lo <= dur <= hi:
  69 | +                if not ly_lo(lo) <= dur <= hi:               # RULINGS 148 (1) / 149 (the key below: lo's middle)
  70 |                      continue
  71 |                  if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
  72 |                      continue
  73 | @@ -3077,7 +3102,7 @@ def cheap_checks(pk, a_by, levels, now):
  74 |      man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
  75 |      det = VF.check_deterministic(segs_v, lines, man, levels)
  76 |      dup = duplicates(pk)
  77 | -    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
  78 | +    rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1] or runtime_short(pk) is not None   # 148 (1)
  79 |      r4_res = r4(pk)
  80 |      what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
  81 |      v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
  82 | @@ -3921,7 +3946,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  83 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
  84 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
  85 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
  86 | -                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
  87 | +                                shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]), short=runtime_short(pk),
  88 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  89 |                                  stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
  90 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
  91 | @@ -4435,7 +4460,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  92 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
  93 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
  94 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
  95 | -                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
  96 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk), short=runtime_short(pk),
  97 |                                              style=HS.lint_lines(pk["lines"]),
  98 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  99 |                                              stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 100 | @@ -4556,7 +4581,12 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 101 |          return out
 102 |      (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
 103 |                               f"the second pass lets step A's soft refusals back, flagged (stage 1)")
 104 | -    soft = _build(*args, soft=True, **kw)
 105 | +    global _FLOOR
 106 | +    _FLOOR = LY_FLOOR_S                                  # RULINGS 148 (1) / 149: the floor, in this pass only
 107 | +    try:
 108 | +        soft = _build(*args, soft=True, **kw)
 109 | +    finally:
 110 | +        _FLOOR = None
 111 |      info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 112 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 113 |              "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}}   # its record
 114 | @@ -4572,7 +4602,7 @@ def _spent(spend):
 115 |      return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) else (float(v), float(v))
 116 |  
 117 |  
 118 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 119 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None, short=None,
 120 |                hook=None, stand=None, visual=None, value=None, last_resort=None, soft=False, who=None,
 121 |                seg_flags=None, mids=None):
 122 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 123 | @@ -4619,8 +4649,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 124 |          "duplicate": row(not dup, "code (package.duplicates)"),
 125 |          "price_now": row(not any(v["rule"] == "PRICE_NOW" for v in det["violations"]),
 126 |                           "code (vo_fidelity.price_now)", measured=bool(det.get("price_now_measured"))),
 127 | -        "runtime": row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 128 | -                              f"{FINAL_TAIL_S} s tail)"),
 129 | +        "runtime": dict(row(rt_ok, f"code (the factory's R4 estimate: {R4_WPS} w/s + {R4_PREROLL_S} s a VO line + "
 130 | +                                   f"{FINAL_TAIL_S} s tail)"),
 131 | +                        **({"status": "FLAGGED", "flags": [short]} if short and rt_ok else {})),   # RULINGS 148 (1) / 149
 132 |          "r4": row(bool(r4_res[0]), "package.r4 (moments-first R4, orchestrator 06:00)"),
 133 |          "context_a": dict(row(bool(a_rows) and (not a_codes or soft_a),
 134 |                                sorted({str(a.get("backend")) for a in a_rows}), rep(a.get("replayed") for a in a_rows),
 135 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 136 | index 67a0d4c..6400783 100644
 137 | --- a/pipeline/package_pin.py
 138 | +++ b/pipeline/package_pin.py
 139 | @@ -46,7 +46,9 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 140 |                          "pbx_exception",                   # RULING 144: EXCEPTION_GATE, only on the one excepted pin
 141 |                          "hook_onset",                      # RULING 146 (2): G17a's quiet shortfall (a cut mid-word stays
 142 |                          #   HARD)
 143 | -                        "graphics"})                       # RULING 146 (1): the show's own graphics, 16:9 only
 144 | +                        "graphics",                        # RULING 146 (1): the show's own graphics, 16:9 only
 145 | +                        "runtime"})                        # RULINGS 148 (1) / 149: a medley under 60 s, its clips at
 146 | +#   package.LY_FLOOR_S (30 s) or more, never-empty pass only (the render's G5 follows this sealed row)
 147 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 148 |  REVIEW_FLAGS_MAX = 3
 149 |  PBX_EXCEPTION_CAP = 5   # RULING 147 (orchestrator 08:20 ET Nov 18): the excepted pin's cap (the exception line itself
 150 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 151 | index 5f8d8c9..e7d50a8 100644
 152 | --- a/tests/package/test_ruling_137.py
 153 | +++ b/tests/package/test_ruling_137.py
 154 | @@ -648,6 +648,54 @@ class TestRuling144TheOneException(unittest.TestCase):
 155 |              PP.WINDOW_H = saved
 156 |  
 157 |  
 158 | +class TestRuling148RuntimeFloor(unittest.TestCase):
 159 | +    """RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18; standing from the 12:00 build): in the never-empty pass a
 160 | +    medley's clips may total LY_FLOOR_S (30 s) or more; under medley_content_range()'s lo (36.7 s) the package seals with
 161 | +    its runtime gate row FLAGGED 'This video runs NN seconds, shorter than usual.' (NN the factory's estimate). Under
 162 | +    30 s nothing seals; the clean pass is unchanged."""
 163 | +
 164 | +    def run_rig(self, ms, never_empty):
 165 | +        import test_medley as TM
 166 | +        ids = [m["moment_id"] for m in ms]
 167 | +        r = TM.Rig(ms, ids, [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)], [None],
 168 | +                   follow_up={"angles": [TM.angle(ids, ids[0])]})
 169 | +        r.build_kw = {"never_empty": never_empty}
 170 | +        return r.run()
 171 | +
 172 | +    def test_a_short_lineup_seals_flagged_in_the_never_empty_pass_only(self):
 173 | +        from test_moments import pm
 174 | +        ms = [pm("h", "A", 11.0), pm("x", "B", 11.5), pm("y", "C", 11.4)]          # 33.9 s: under 36.7, over 30
 175 | +        self.assertIsNone(self.run_rig(ms, False)["package"])                       # the clean pass: unchanged
 176 | +        pk = self.run_rig(ms, True)["package"]
 177 | +        self.assertIsNotNone(pk)
 178 | +        est = pk["runtime_s_estimate"]
 179 | +        self.assertLess(est, PK.RUNTIME_S[0])
 180 | +        self.assertEqual((pk["gates"]["runtime"]["status"], pk["gates"]["runtime"]["flags"]),
 181 | +                         ("FLAGGED", [f"This video runs {int(round(est))} seconds, shorter than usual."]))
 182 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])
 183 | +        self.assertIsNone(PK._FLOOR)                                                # cleared after the pass
 184 | +
 185 | +    def test_under_the_floor_nothing_seals(self):
 186 | +        from test_moments import pm
 187 | +        ms = [pm("h", "A", 9.0), pm("x", "B", 9.5), pm("y", "C", 9.4)]              # 27.9 s
 188 | +        self.assertIsNone(self.run_rig(ms, True)["package"])
 189 | +
 190 | +    def test_the_takeaway_budget_and_the_sentence(self):
 191 | +        b40 = PK.takeaway_budget(40.0)
 192 | +        self.assertIsNone(PK.takeaway_budget(33.9))                                 # outside the pass: no length
 193 | +        pk = {"shape": "medley", "runtime_s_estimate": 57.19, "segments": [{"duration_s": 20.0}, {"duration_s": 13.9}]}
 194 | +        self.assertIsNone(PK.runtime_short(pk))                                     # the clean pass: no sentence
 195 | +        with mock.patch.object(PK, "_FLOOR", PK.LY_FLOOR_S):
 196 | +            lo, hi = PK.takeaway_budget(33.9)
 197 | +            self.assertEqual((hi, lo), (PK.LY_TAKEAWAY_MAX_WORDS, PK.LY_TAKEAWAY_MAX_WORDS - PK.LY_SHORT_SPAN_WORDS))
 198 | +            self.assertIsNone(PK.takeaway_budget(29.0))                             # under the floor
 199 | +            self.assertEqual(PK.takeaway_budget(40.0), b40)                          # a full line-up: unchanged
 200 | +            self.assertEqual(PK.runtime_short(pk), "This video runs 57 seconds, shorter than usual.")
 201 | +            for bad in (dict(pk, runtime_s_estimate=60.0), dict(pk, shape="vo"),
 202 | +                        dict(pk, segments=[{"duration_s": 29.9}])):
 203 | +                self.assertIsNone(PK.runtime_short(bad), bad)
 204 | +
 205 | +
 206 |  class TestRuling146(unittest.TestCase):
 207 |      """RULING 146 (orchestrator 07:55 ET Nov 18), the never-empty pass: (1) the source's own on-screen graphics (a ticker,
 208 |      a lower third, a bug) are SOFT in a package sealed 16:9 only, flagged in the ruling's words; (2) G17a's quiet before
 209 | 
```

---

pp-selectid: RULINGS 148 (1) / 149 (orchestrator 09:56 ET Nov 18, standing from the 12:00 ET build): "the 30 s floor with
a 'runs short' flag up to 36.7 s". A medley's clips may total LY_FLOOR_S (30.0 s) or more; under the calibrated floor
(medley_content_range()'s lo, 36.7 s: one 20-word takeaway landing 60 s) the package carries the flag "This video runs NN
seconds, shorter than usual." (NN = the factory's runtime estimate, whole seconds); under 30 s still refused.
SCOPE: the NEVER-EMPTY pass only (a flag belongs to it; the clean pass is unchanged). build() sets the module's _FLOOR to
LY_FLOOR_S around _build(soft=True) and clears it in a finally (the soft pass runs after the clean pass, in sequence).
THE CHANGE (pipeline/package.py, pipeline/package_pin.py):
1. ly_lo(lo): lo, or min(lo, _FLOOR) in the pass. Used ONLY by the two acceptance checks (lineup_ok's seconds test,
   lineup_for's); lineup_for's preference key keeps the calibrated middle (lo + hi) / 2. The angle writer's prompt
   keeps the calibrated lo/hi (unchanged text: cached replies stay valid).
2. takeaway_budget: when neither LY_AIM_S nor 60-70 s can be landed, in the pass, with content_s >= _FLOOR and
   LY_TAKEAWAY_MIN_WORDS <= cap < the words that would land 60 s: (max(MIN, cap - 4), cap), the longest takeaway house
   style and R4 allow. Full line-ups: unchanged (tested). bridge_budget follows (it calls takeaway_budget).
3. runtime_short(pk): the sentence, only with _FLOOR set, shape "medley", a numeric estimate under RUNTIME_S[0] (60 s),
   and the clips' seconds >= _FLOOR; else None. cheap_checks: rt_ok = 60-70 s OR runtime_short(pk) (so no RUNTIME
   violation / rewrite for an accepted short medley). inventory(short=runtime_short(pk)) at both call sites: the
   "runtime" gate row becomes {"status": "FLAGGED", "flags": [sentence], ...row} (rt_ok must hold).
4. package_pin.SOFT_GATES += "runtime" (the integrator's check_pin_only reads SOFT_GATES live; its render's G5 / R4
   follow this sealed FLAGGED row, its batch 115). The flag counts toward the cap (content_flags), as ruled.
TESTS (test_ruling_137.TestRuling148RuntimeFloor, the real build() on the stubbed rig): 33.9 s of clips: the clean pass
seals nothing, the never-empty pass seals with runtime FLAGGED and the exact sentence, gate_problems none, _FLOOR cleared;
27.9 s: nothing; the takeaway budget at 33.9 / 29.0 / 40.0 s with and without the floor; the sentence's refusals.
Mutations: 7 of 7 killed (no floor in the acceptance; no short budget; no sentence; build() never sets the floor;
runtime not a soft gate; the row never flagged; rt_ok ignoring the floor); control passes.
PLEASE CHECK: (1) can the floor leak into the clean pass or a later build (the global)? (2) can a package under 30 s,
over 70 s, or of another shape seal through it? (3) the takeaway budget's fallback; (4) the tests.


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
