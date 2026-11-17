# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1330
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 356 s finish=stop usage in 12037 / out 5611 usd_reported=0.001069 usd~0.120 (upper-bound price)

The code implements the "soft" hook bar for the never-empty pass (Stage 2b) as required by Rulings 136/137/138.

### Analysis

1.  **Hard vs. Soft Logic**: The clean pass (`soft=False`) remains strictly hard because `m["hook_bar_soft"]` is never set, meaning `hook_own` will only return `passes=True` if the hard bar is met (`ok=True`). In the soft pass, `_build` identifies the best `HOOK_SOFT_MAX` (2) hooks that are under the bar (via `hook_bar_under`) and marks them.
2.  **Strictness of `hook_bar_under`**: The function correctly returns `None` (staying HARD) if:
    *   Any rating part is missing or not an integer (`isinstance(x, int) and not isinstance(x, bool)`).
    *   No valid calibration exists (`_live_bar` is `None`).
    *   The rater of the hook does not match the rater of the calibration (`r.get("backend") != live.get("rater")`).
3.  **Vision Cost Bound**: By limiting the soft-pass candidates to `HOOK_SOFT_MAX` before they are added to `rated_open`, the code ensures that at most 2 additional vision checks are performed per medley attempt.
4.  **Flagging and Inventory**: 
    *   The `inventory` function correctly identifies the soft-pass flag via `hook_fl` (extracted from the `hook_own` result) and generates the required plain-sentence warning.
    *   The "medley" row is marked `FLAGGED` only if the verdict passed (`medley[0]`) and the hook was soft-passed.
    *   `package_pin.SOFT_GATES` now includes `"medley"`, allowing the seal to proceed despite the flag.
5.  **Data Integrity**: The use of `with_verdict` (as noted in the prompt) ensures that the `hook_bar_soft` mark is applied to copies of the moment objects, preventing pollution of the original data or the driver's spotlight pass.
6.  **Tests**: The new tests in `test_ruling_137.py` are comprehensive, covering the specific "hard" failure cases (wrong rater, unmeasured parts), the `HOOK_SOFT_MAX` limit, and the end-to-end `Rig` flow from clean-pass failure to soft-pass flagged success.

### Findings

No violations of the Governing Laws or the specific requirements of Rulings 136/137/138 were found. The implementation is precise and the test coverage is sufficient.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 101 s finish=stop usage in 10469 / out 15857 usd_reported=0.002289 usd~0.269 (upper-bound price)

**Findings**

| # | Severity | Issue | Explanation |
|---|----------|-------|-------------|
| 1 | **P0** | **Hook flag never set** | `hook_own()` uses `m.get("hook_bar_soft")` to decide whether to flag a hook. In `_build()` the `hook_bar_soft` flag is added **after** `hook_ratings()` runs, so when `hook_own()` is called the flag is still missing. Consequently `hook_own()` always returns `flag=None`, causing the medley row to never be flagged and the tests that expect a flag to fail. |
| 2 | **P0** | **Inventory flag logic wrong** | `inventory()` pulls the flag from `medley[1].get("hook_own")`. Because `hook_own()` never set `flag`, the flag string is `None`, so the medley row is never marked `FLAGGED` even when the soft pass passes. |
| 3 | **P1** | **Soft‑pass hook ordering may be incorrect** | The current code calculates the “under‑bar” hooks **after** the ratings are attached, but it uses `hook_order()` which depends on the hook ratings. Since the soft‑pass flag is added after the ratings, the ordering may not reflect the intended “best” hooks, potentially allowing a non‑under‑bar hook to be flagged. |
| 4 | **P1** | **Potential performance hit** | The soft‑pass logic still calls `hook_ratings()` for all openers before marking the soft‑pass hooks. This means the vision check is performed for every opener even if it will later be marked as soft‑pass and not actually used. The spec says the soft‑pass should limit vision calls to the best `HOOK_SOFT_MAX` hooks. |
| 5 | **P2** | **`hook_bar_under()` may return `None` for valid under‑bar hooks** | The function returns `None` if any part is unmeasured, the backend mismatches, or the live bar is missing. While this is correct, the logic is duplicated in `hook_own()` and could be simplified by centralising the check. |
| 6 | **P3** | **Redundant `hook_rating` pop** | `_build()` pops `hook_rating` from each moment twice (once before rating, once after). The second pop is unnecessary and could be removed for clarity. |
| 7 | **P3** | **Hard‑coded `HOOK_SOFT_MAX` in tests** | The tests hard‑code `HOOK_SOFT_MAX` to 2. If the constant changes, the tests will break. They should reference the constant directly. |

**P1_OR_WORSE**: **2** (issues 1 and 2)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 248 s finish=stop usage in 11347 / out 18818 usd_reported=0.013945 usd~0.316 (upper-bound price)



# CODE AUDIT — pp-selectid / RULING 137 Stage 2b (Soft Hook Bar)

## Scope Reviewed
`pipeline/package.py` (hook_bar_under, hook_own, _build, inventory, build wrapper), `pipeline/package_pin.py` (SOFT_GATES), `tests/package/test_ruling_137.py` (6 new tests), `tests/package/test_medley.py` (Rig.run kwarg passthrough).

---

## Findings

### [P2] `hook_bar_under` re-invoked up to 4× per flagged hook in the same `_build` call

In `_build`, for each hook that ends up in `under`:

1. `hook_bar_under(m)` in the list-comprehension filter (line 66)
2. `hook_bar_under(m)` inside `hook_own(m)` when `can_open` / `rated_open` reads it (line 44 of the diff)
3. `hook_bar_under(m)` in the `prescreen["soft_hook_bar"]` dict comprehension (line 71)
4. `hook_bar_under(m)` in the `log(...)` f-string join (line 73)

Each call re-reads `_live_bar()` (which may hit a file or cache) and re-evaluates the parts. With `HOOK_SOFT_MAX = 2` the absolute cost is trivial, but if the cap is ever raised or `_live_bar` becomes expensive (e.g., re-parsing a calibration JSON), the redundancy becomes a hot path. Suggest computing the detail string once per hook and storing it on the moment (e.g., `m["_hook_bar_detail"]`) or in a local dict, then reusing it.

**Not a correctness issue** — the function is pure and idempotent — but it's a small maintainability / performance smell.

---

### [P2] `inventory` flag sentence depends on `CLIP_PLACE['hook']` being a human-readable label

```python
f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated "
f"it under the hook bar ({hook_fl})."
```

The test asserts the exact string `"The opening clip (Scott Melker): …"`, which means `CLIP_PLACE['hook']` must resolve to `"The opening clip"`. If `CLIP_PLACE` is ever refactored (e.g., to a numeric index or a different phrasing), the flag sentence silently changes and the `review_flags_of` / `gate_problems` equality checks in the test will break. More importantly, the **plain-language contract** (RULING 138 (3): "one plain sentence per clip") is now coupled to a constant that isn't defined in this diff.

Suggestion: either (a) assert the expected sentence in a dedicated test that pins `CLIP_PLACE['hook']`, or (b) build the sentence from a dedicated constant (e.g., `HOOK_FLAG_PREFIX = "The opening clip"`) so the coupling is explicit.

---

### [P3] `hook_bar_under` treats `True`/`False` as invalid part scores via `isinstance(x, bool)` guard — good, but the test only covers `True`

```python
if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
    return None
```

The test exercises `self.hm(True, 5, 5)` (scroll = `True`) and expects `None`. It does **not** exercise `False` (which is also an `int` subclass in Python and would be caught by the same guard). Adding `self.hm(False, 5, 5)` to the hard-case loop would close the gap at zero cost.

---

### [P3] `test_at_most_the_best_two_under_the_bar_open` — ordering assertion is implicit

```python
under = [m for m in ("h", "x", "z", "y") if m in rated]   # hook_order: rating, then sum
self.assertEqual(list(rec["soft_hook_bar"]), under[:PK.HOOK_SOFT_MAX])
```

The comment explains the sort key, but the test would be more self-documenting (and more robust to a future `hook_order` change) if it asserted the expected order explicitly:

```python
self.assertEqual(list(rec["soft_hook_bar"]), ["h", "x"])
```

As written, if `hook_order` changes its tie-break, the test still passes as long as the first two of the new order happen to be in `rated` — which is the same set. The explicit assertion makes the intent unambiguous.

---

### [P3] Stage label change `"2a" → "2b"` is a one-character edit with no migration note

```python
-    info = {"stage": "2a", ...}
+    info = {"stage": "2b", ...}
```

Any downstream consumer (dashboard, alerting, ledger query) that filters on `never_empty.stage == "2a"` will silently stop matching. The diff doesn't include a grep or a note about existing consumers. If this is a brand-new field (first introduction of the `stage` key), no issue. If it was already emitted as `"2a"` in a prior deploy, a one-line migration note or a backward-compatible alias (`"2a" | "2b"`) would be prudent.

---

## Verification of the Five Requested Checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can a hook with no calibration / another rater / unmeasured part open, or can the clean pass open a hook under the bar? | **No.** `hook_bar_under` returns `None` in all three hard cases (no `live`, `backend ≠ rater`, any part not a non-bool int). `hook_own` then sets `flag = None`, so `passes` stays `False`. In the clean pass `soft` is `False`, so `under = []` and no `hook_bar_soft` mark is ever set. The `test_a_mark_carried_in_is_never_read` test confirms a pre-set mark is popped. |
| 2 | Does any reader of `ho

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1330, stage 2b (1): the soft hook bar)

SEATS ANSWERED: 3 of 3. qwen3.8-27b: P0/P1 none (two P2s). gemma-4-31b-it: P0/P1 none. gpt-oss-20b: 2 P0 and 2 P1
claimed; every one is refuted below from the code and the passing tests.

## gpt-oss's claims
1. [P0] "the mark is set after hook_own runs, so no flag": REFUTED. hook_own is not run once and stored. Every reader
   calls it when it reads: _can_open for rated_open (package.py:3342, AFTER the mark), the clips-alone verdict (medley,
   :2153), coherence (:2089), rulings 62 / 63, hook_weak and the coherence floors in the line-up loop. All run after the
   mark, which is set right after the ratings are attached. The end-to-end test through test_medley's Rig (the real
   build) seals with the medley row FLAGGED in the exact sentence, and mutation H1 (the mark not opening) is killed.
2. [P0] "the inventory never flags": REFUTED, for the same reason. The verdict's hook_own (medley stub and real medley()
   both copy hook_own(segs[0])) carries "flagged", and the end-to-end test asserts the FLAGGED row and review_flags_of.
3. [P1] "a hook not under the bar may be marked": REFUTED. The marked set is filtered by hook_bar_under(m), which is None
   for a passing hook; hook_order only orders that set. Tests: the best-two test; mutations H6 and H12 are killed.
4. [P1] "vision is paid for every opener before marking": REFUTED. hook_ratings is the Grok hook RATING (unchanged, cached
   per moment), not vision. Vision is see(rated_open) at :3343, AFTER the mark; rated_open is can_open: the passing hooks
   (as before) plus at most HOOK_SOFT_MAX = 2 marked ones.
5. [P2] duplication between hook_bar_under and hook_own: DECLINED. hook_bar_under is the one source of the soft detail;
   hook_own calls it.
6. [P3] "hook_rating popped twice": REFUTED (one pop at the hook stage's start; the later line assigns the new rating).
7. [P3] the test pins HOOK_SOFT_MAX == 2: BY DESIGN (the ruled value is checked; the slice uses the constant).

## qwen's P2s
- hook_bar_under called up to 4 times per marked hook: DECLINED. Each call reads the per-minute cached bar (_live_bar);
  a handful of dict reads per build.
- "The opening clip" readability: by design (CLIP_PLACE, ruling 138 (3), as stage 1 and 2a's flags).

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1330/C2_STEP.diff (229 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 5b9ed6d..68e6942 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -981,6 +981,10 @@ opens the video. The hook is shown for context only: it is NOT rated here (its o
   6 |  Return ONLY this JSON object: {{"through_line": "...", "clips": {{{clip_keys}}}, "joins": {{{joins}}}}}"""
   7 |  HOOK_PARTS = ("scroll", "alone", "setup")   # ruling 52 (08:06 Nov 13): the hook's own job, each part rated 1-5
   8 |  HOOK_RULE = "the lowest of scroll / alone / setup (ruling 52): every part must reach the bar"
   9 | +HOOK_PART_WORDS = {"scroll": "stopping the scroll", "alone": "making sense on its own",   # RULING 137 stage 2b: a
  10 | +                   "setup": "setting up what follows"}                                  # part in PBX's words
  11 | +HOOK_SOFT_MAX = 2      # RULING 137 stage 2b: the never-empty pass lets the best 2 hooks under the bar open (each is seen
  12 | +#   by the paid vision check before any angle, as every opener is)
  13 |  HOOK_OWN = ("scroll", "alone")     # RULING 61 (12:00): the hook's OWN-JOB rating, cached and never re-asked per line-up
  14 |  HOOK_OWN_RULE = ("the lowest of scroll / alone, cached (ruling 61); 'sets up what follows' is judged at the hook -> "
  15 |                   "clip_01 join")
  16 | @@ -1667,6 +1671,21 @@ def hook_bar_mark(live=None):
  17 |              "calibration_sha256": (live or {}).get("sha256"), "ruling": "115"}
  18 |  
  19 |  
  20 | +def hook_bar_under(m):
  21 | +    """RULING 137 stage 2b (the calibrated hook bar SOFT in the never-empty pass): the plain detail of a hook rated UNDER
  22 | +    the bar by the bar's own rater, every part measured, e.g. "stopping the scroll 2 of 5, needs 3"; None when it
  23 | +    passes, a part is unmeasured, another back-end rated it, or no calibration is valid (those stay hard, law L-m)."""
  24 | +    r = (m or {}).get("hook_rating") or {}
  25 | +    parts = {k: r.get(k) for k in HOOK_PARTS}
  26 | +    if not all(isinstance(x, int) and not isinstance(x, bool) for x in parts.values()):
  27 | +        return None
  28 | +    live, _ = _live_bar()
  29 | +    if live is None or r.get("backend") != live.get("rater"):
  30 | +        return None
  31 | +    under = [p for p in HOOK_PARTS if parts[p] < live["floors"][p]]
  32 | +    return "; ".join(f"{HOOK_PART_WORDS[p]} {parts[p]} of 5, needs {live['floors'][p]}" for p in under) or None
  33 | +
  34 | +
  35 |  def hook_own(m):
  36 |      """RULING 61 / RULING 115: a hook's OWN-JOB rating, the cached one ruling 59 gave it ("hook_rating"): {"scroll",
  37 |      "alone", "setup", "rating": the lower of scroll and alone (it ORDERS hooks), "passes": RULING 115, every part at
  38 | @@ -1679,9 +1698,11 @@ def hook_own(m):
  39 |          return None
  40 |      live, why = _live_bar()
  41 |      ok, short = HB.passes(dict(parts, backend=r.get("backend")), live)
  42 | -    return dict(parts, rating=min(parts[k] for k in HOOK_OWN), passes=ok, short=why if live is None else short,
  43 | +    flag = hook_bar_under(m) if not ok and m.get("hook_bar_soft") else None    # RULING 137 stage 2b: a hook the
  44 | +    return dict(parts, rating=min(parts[k] for k in HOOK_OWN), passes=ok or bool(flag),   # never-empty pass marked
  45 | +                short=why if live is None else short,                                    # opens, flagged
  46 |                  bar=HB.text(live), source="the hook's cached own-job rating (ruling 61), on the calibrated bar (ruling 115)",
  47 | -                rule=HOOK_OWN_RULE)
  48 | +                rule=HOOK_OWN_RULE, **({"flagged": flag} if flag else {}))
  49 |  
  50 |  
  51 |  def opens_16x9(m):
  52 | @@ -3299,7 +3320,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  53 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
  54 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
  55 |      for m in cleared.values():                                           # a rating is this build's own (its
  56 | -        m.pop("hook_rating", None)                                       # cache's), never one carried in
  57 | +        m.pop("hook_rating", None)                                       # cache's), never one carried in; nor is
  58 | +        m.pop("hook_bar_soft", None)                                     # RULING 137 stage 2b's soft mark
  59 |      openers = {mid: m for mid, m in cleared.items() if can_open(m)}      # RULING 59 (a): every one that can open,
  60 |      rated, hook_err = hook_ratings(router, list(openers.values()), ctx, wv, wf, cache=hook_cache) if openers else \
  61 |          ({}, None)                                                        # each alone (ruling 115), cached
  62 | @@ -3307,6 +3329,14 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  63 |          m["hook_rating"] = rated.get(mid) or {"rating": None, "why": (f"not rated: {hook_err}" if mid in openers else
  64 |                                                                        "cannot open (hook eligibility, G17a or the "
  65 |                                                                        "render's hook rule)")}
  66 | +    under = hook_order([m for mid, m in openers.items() if mid in rated and hook_bar_under(m)])[:HOOK_SOFT_MAX] \
  67 | +        if soft else []                                                   # RULING 137 stage 2b: the hook bar is SOFT
  68 | +    for m in under:                                                       # in the never-empty pass: the best
  69 | +        m["hook_bar_soft"] = True                                         # HOOK_SOFT_MAX hooks under it open, flagged
  70 | +    if under:
  71 | +        out["prescreen"]["soft_hook_bar"] = {m["moment_id"]: hook_bar_under(m) for m in under}
  72 | +        log(f"  RULING 137 NEVER EMPTY (stage 2b): {len(under)} hook(s) rated under the calibrated bar by its own rater "
  73 | +            f"open, flagged: " + ", ".join(f"{m['moment_id'][:8]} ({hook_bar_under(m)})" for m in under))
  74 |      for m in cleared.values():
  75 |          m.pop("visual_hook_block", None)
  76 |      rated_open = [m for m in cleared.values() if can_open(m)]              # RULING 70: the hooks that would open,
  77 | @@ -4295,7 +4325,7 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
  78 |      (kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: the clean pass sealed nothing ({out.get('why_none')}); "
  79 |                               f"the second pass lets step A's soft refusals back, flagged (stage 1)")
  80 |      soft = _build(*args, soft=True, **kw)
  81 | -    info = {"stage": "2a", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
  82 | +    info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
  83 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
  84 |              "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
  85 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
  86 | @@ -4334,6 +4364,7 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  87 |          return None if any(not isinstance(x, bool) for x in values) else any(values)
  88 |      det = fid["deterministic"]
  89 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
  90 | +    hook_fl = ((medley[1].get("hook_own") or {}).get("flagged") if soft and medley is not None else None)   # 2b
  91 |      lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
  92 |      edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
  93 |                 if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
  94 | @@ -4387,7 +4418,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
  95 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
  96 |                            **votes_of(coh)),
  97 |          **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
  98 | -                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
  99 | +                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"),
 100 | +                           **({"status": "FLAGGED", "flags": [            # RULING 137 stage 2b: the hook under the bar
 101 | +                               f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated "
 102 | +                               f"it under the hook bar ({hook_fl})."]} if hook_fl and medley[0] else {}))}
 103 |             if medley is not None else {}),
 104 |          **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 105 |             if shape is not None else {}),
 106 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 107 | index 180aba9..1fb3855 100644
 108 | --- a/pipeline/package_pin.py
 109 | +++ b/pipeline/package_pin.py
 110 | @@ -35,8 +35,10 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 111 |  # with "flags", plain words, sealed with the gates; the pin's moments_package "review_flags" is derived from them
 112 |  # (review_flags_of), at most REVIEW_FLAGS_MAX. STAGE 1: step A's row only. A HARD gate still needs exactly PASS.
 113 |  SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 114 | -                        "cuttable"})                       # stage 2a: a sentence edge at a word boundary (L-v 2's
 115 | -#   word check, "second_pass", stays HARD)
 116 | +                        "cuttable",                        # stage 2a: a sentence edge at a word boundary (L-v 2's
 117 | +                        #   word check, "second_pass", stays HARD)
 118 | +                        "medley"})                         # stage 2b: the hook under the calibrated bar (its own
 119 | +#   rater's rating; no calibration or another rater stays HARD)
 120 |  REVIEW_FLAGS_MAX = 3
 121 |  
 122 |  
 123 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 124 | index 3fc3227..0e4d42a 100644
 125 | --- a/tests/package/test_medley.py
 126 | +++ b/tests/package/test_medley.py
 127 | @@ -850,6 +850,7 @@ class Rig:
 128 |              kw["registered"] = self.registered
 129 |          if self.lock_check is not None:
 130 |              kw["lock_check"] = self.lock_check
 131 | +        kw.update(getattr(self, "build_kw", None) or {})  # RULING 137: never_empty / flagged_today, when a test sets
 132 |          if getattr(self, "stories_path", None):            # RULING 118 (4): the stories file (default: none read)
 133 |              kw["stories_path"] = self.stories_path
 134 |          if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
 135 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 136 | index c322e28..f61260a 100644
 137 | --- a/tests/package/test_ruling_137.py
 138 | +++ b/tests/package/test_ruling_137.py
 139 | @@ -207,6 +207,89 @@ class TestStage2a(unittest.TestCase):
 140 |                                                     "flags": ["a word differs"]}), "r")
 141 |  
 142 |  
 143 | +class TestStage2bHookBar(unittest.TestCase):
 144 | +    """RULING 137 STAGE 2b (1) (line 1, 13:20 ET): the calibrated hook bar is SOFT in the never-empty pass. A hook its
 145 | +    own rater rated UNDER a floor opens, flagged in plain words (the best HOOK_SOFT_MAX of them); no calibration,
 146 | +    another rater or an unmeasured part stay hard, and the clean pass never opens it. The rigs' bar (conftest):
 147 | +    scroll 3, alone 4, setup 3, rated by "xai:grok"."""
 148 | +
 149 | +    def hm(self, sc, al, se, backend="xai:grok", mark=False):
 150 | +        m = {"moment_id": "h1", "hook_rating": {"scroll": sc, "alone": al, "setup": se, "backend": backend}}
 151 | +        return dict(m, hook_bar_soft=True) if mark else m
 152 | +
 153 | +    def test_under_the_bar_in_plain_words_and_what_stays_hard(self):
 154 | +        self.assertEqual(PK.hook_bar_under(self.hm(2, 5, 5)), "stopping the scroll 2 of 5, needs 3")
 155 | +        self.assertEqual(PK.hook_bar_under(self.hm(2, 3, 2)), "stopping the scroll 2 of 5, needs 3; making sense on "
 156 | +                         "its own 3 of 5, needs 4; setting up what follows 2 of 5, needs 3")
 157 | +        for m in (self.hm(3, 4, 3), self.hm(2, 5, 5, backend="heimdall:qwen"), self.hm(None, 5, 5),
 158 | +                  self.hm(True, 5, 5), {}, None):
 159 | +            self.assertIsNone(PK.hook_bar_under(m), m)
 160 | +        with mock.patch.object(PK, "_live_bar", lambda: (None, "no valid hook calibration")):
 161 | +            self.assertIsNone(PK.hook_bar_under(self.hm(2, 5, 5)))
 162 | +
 163 | +    def test_only_the_soft_pass_mark_opens_it(self):
 164 | +        own = PK.hook_own(self.hm(2, 5, 5))
 165 | +        self.assertEqual((own["passes"], "flagged" in own), (False, False))
 166 | +        own = PK.hook_own(self.hm(2, 5, 5, mark=True))
 167 | +        self.assertEqual((own["passes"], own["flagged"]), (True, "stopping the scroll 2 of 5, needs 3"))
 168 | +        own = PK.hook_own(self.hm(2, 5, 5, backend="heimdall:qwen", mark=True))
 169 | +        self.assertEqual((own["passes"], "flagged" in own), (False, False))         # another rater: hard
 170 | +        own = PK.hook_own(self.hm(3, 4, 3, mark=True))
 171 | +        self.assertEqual((own["passes"], "flagged" in own), (True, False))          # a pass is never flagged
 172 | +
 173 | +    def rig(self, hooks, never_empty):
 174 | +        import test_medley as TM
 175 | +        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None], hooks=hooks)
 176 | +        r.build_kw = {"never_empty": never_empty}
 177 | +        return r, r.run()
 178 | +
 179 | +    UNDER = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}   # h: the best hook, under the bar
 180 | +
 181 | +    def test_a_hook_under_the_bar_seals_flagged_only_in_the_never_empty_pass(self):
 182 | +        _, clean = self.rig(self.UNDER, False)
 183 | +        self.assertIsNone(clean["package"])
 184 | +        self.assertIn("no hook in the pool", clean["why_none"])
 185 | +        r, out = self.rig(self.UNDER, True)
 186 | +        pk = out["package"]
 187 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]][0], "h")
 188 | +        ch = pk["segments"][0].get("channel")
 189 | +        want = [f"The opening clip ({ch}): the checker rated it under the hook bar (stopping the scroll 2 of 5, "
 190 | +                f"needs 3)."]
 191 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", want))
 192 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
 193 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
 194 | +        self.assertEqual(pk["gates"]["coherence"]["status"], "PASS")                 # flagged once, on its own row
 195 | +        self.assertEqual(out["never_empty"]["stage"], "2b")
 196 | +        self.assertEqual(list(out["prescreen"]["soft_hook_bar"])[0], "h")
 197 | +
 198 | +    def test_a_mark_carried_in_is_never_read(self):
 199 | +        import test_medley as TM
 200 | +        ms = [dict(m, hook_bar_soft=True) for m in TM.TestBuildLoop.MS]      # the clean pass pops it with the rating
 201 | +        r = TM.Rig(ms, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE)], [None], hooks=self.UNDER)
 202 | +        r.build_kw = {"never_empty": False}
 203 | +        self.assertIsNone(r.run()["package"])
 204 | +
 205 | +    def test_the_medley_row_flags_only_in_the_soft_pass_and_only_on_a_passing_verdict(self):
 206 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 207 | +        med = {"backend": "xai:grok", "replayed": False, "measured": True, "flagged": [],
 208 | +               "hook_own": {"passes": True, "flagged": "stopping the scroll 2 of 5, needs 3"}}
 209 | +        row = lambda ok, soft: PK.inventory(**TestStage2a().base(t), medley=(ok, med), soft=soft,
 210 | +                                            who={"hook": "Scott Melker"})["medley"]
 211 | +        self.assertEqual((row(True, True)["status"], row(True, True)["flags"]), ("FLAGGED", [
 212 | +            "The opening clip (Scott Melker): the checker rated it under the hook bar (stopping the scroll 2 of 5, "
 213 | +            "needs 3)."]))
 214 | +        self.assertEqual((row(True, False)["status"], "flags" in row(True, False)), ("PASS", False))
 215 | +        self.assertEqual(row(False, True)["status"], "FAIL")
 216 | +
 217 | +    def test_at_most_the_best_two_under_the_bar_open(self):
 218 | +        r, out = self.rig({"h": (2, 5, 5), "x": (2, 5, 4), "y": (1, 5, 5), "z": (2, 5, 3)}, True)
 219 | +        rec = out.get("prescreen") if out.get("package") else out["never_empty"]["soft_record"]["prescreen"]
 220 | +        rated = (out.get("hook_pool") or out["never_empty"]["soft_record"]["hook_pool"])["ratings"]
 221 | +        under = [m for m in ("h", "x", "z", "y") if m in rated]                       # hook_order: rating, then sum
 222 | +        self.assertEqual(list(rec["soft_hook_bar"]), under[:PK.HOOK_SOFT_MAX])
 223 | +        self.assertEqual(PK.HOOK_SOFT_MAX, 2)
 224 | +
 225 | +
 226 |  class TestTheDayCount(unittest.TestCase):
 227 |      def test_counted_per_day_ledger(self):
 228 |          with tempfile.TemporaryDirectory() as d:
 229 | 
```

---

pp-selectid: RULINGS 136 / 137 / 138, the hard/soft switch, STAGE 2b (1): THE CALIBRATED HOOK BAR (ruling 115) SOFT in
the never-empty pass. Stages 1 and 2a are LIVE: package.build runs the clean pass, and only when it seals nothing (and the
day allows) runs _build(soft=True). A soft gate there flags in one plain sentence per clip (ruling 138 (3)); at most 3
flags seal (package_pin.REVIEW_FLAGS_MAX, :42). The measured yield: the bar refused 12 of 18 hooks over 7 days. Files:
pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py, tests/package/test_medley.py (Rig.run
passes a test's build_kw).

THE CHANGE (only the never-empty pass; the clean pass is unchanged):
(a) hook_bar_under(m): the plain detail of a hook rated UNDER a floor BY THE BAR'S OWN RATER with every part measured
    ("stopping the scroll 2 of 5, needs 3"). None when it passes, a part is unmeasured, another back-end rated it, or no
    calibration is valid: those stay HARD (law L-m).
(b) hook_own(m) (the ONE record every bar check reads) reports passes=True plus "flagged" only for a hook that carries the
    soft mark "hook_bar_soft" AND is under the bar by (a). Every reader therefore follows with no change of its own:
    _can_open (package.py:1758), coherence's ok (:2089), medley's ok (:2153), ruling 62's last_clip_only (:2173),
    ruling 63's reorder (:3893), hook_weak (:3906), the coherence floors (:4222).
(c) _build sets the mark only when soft, on at most HOOK_SOFT_MAX = 2 hooks, the best by hook_order (:1762), after the
    ratings are attached and before rated_open is seen (:3342-3343: each opener pays the vision check before any angle,
    so the cap bounds the extra vision calls). The mark is popped with the old rating at the start of the hook stage, so a
    mark never carries in. The moments _build marks are its own copies: with_verdict (:1501, :1504) builds a new dict
    for every moment (:3200). The driver's spotlight pass gets the driver's own list (proof_ledger.py SPOT.build), never
    these copies.
(d) inventory: the "medley" row (the clips-alone verdict, which holds the hook's slot) is FLAGGED with one sentence
    ("The opening clip (<channel>): the checker rated it under the hook bar (<detail>).") only when soft, the verdict
    passed, and the verdict's hook_own carries "flagged". package_pin.SOFT_GATES adds "medley". flagged_ok (:387) still
    needs non-empty string flags and replayed False. The coherence row stays PASS (one doubt, flagged once).
(e) The wrapper's record label is now stage "2b".

TESTS (test_ruling_137, 6 new): (a)'s detail and every hard case; only a marked hook opens; END TO END through
test_medley's Rig (the real build, every model stubbed): the clean pass finds no hook, and the never-empty pass seals with
the medley row FLAGGED in the exact sentence, review_flags_of equal to it, gate_problems() empty, coherence PASS; a mark
carried in is never read; the row flags only in the soft pass and only on a passing verdict; at most the best 2 open.
Mutations: 12 of 12 killed.

PLEASE CHECK: (1) can a hook with no calibration, another rater, or an unmeasured part open, or can the clean pass open a
hook under the bar? (2) every reader of hook_own's "passes": does any one of them now let through something it should not
(e.g. ruling 62 / 63 / coherence)? (3) the cost bound on vision; (4) the plain sentence and the one-flag count; (5) the
tests.


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
