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
| 2 | Does any reader of `hook_own["passes"]` let through something it should not? | **No.** `passes=True` is the *intended* signal for "this hook is allowed to open in the soft pass." Every listed reader (`_can_open`, coherence, medley, ruling 62/63, `hook_weak`, coherence floors) correctly treats the hook as openable. The medley row is **FLAGGED** (not PASS), so the doubt is recorded exactly once. Coherence stays PASS because coherence is about clip-to-clip flow, not the hook bar. The `flagged` key is available to any future reader that needs to distinguish. |
| 3 | Cost bound on vision | **Bounded at 2.** `HOOK_SOFT_MAX = 2` caps the number of hooks that receive the soft mark. Each marked hook enters `rated_open` and pays the per-opener vision check. The mark is set *after* `hook_ratings` (which rates all openers) and *before* `rated_open` is computed, so the cap directly limits the extra vision calls to ≤ 2 per soft-pass build. |
| 4 | Plain sentence and one-flag count | **Correct.** The sentence is built from `CLIP_PLACE['hook']` + channel + `hook_bar_under` detail. It appears exactly once, on the medley row's `flags` list. `review_flags_of` returns that single-element list. `gate_problems` is empty because `"medley"` is in `SOFT_GATES` and `flagged_ok` is satisfied (non-empty string flags, `replayed=False`). Coherence is PASS, not FLAGGED — one doubt, one flag. |
| 5 | Tests | **Comprehensive.** 6 new tests cover: the plain-text detail and every hard case; only the soft mark opens; end-to-end clean-vs-never-empty through the real `Rig`; carried-in mark is popped; inventory row flags only in soft + passing; at-most-2 cap. The 12/12 mutation kill rate is reported. The one gap is the `False`-as-int edge (P3 above). |

---

## Law Compliance Spot-Check

- **LAW 20 / M2** (thresholds are constants; a failed gate is a hard stop; never reclassify a failing gate as a false positive): The hook bar threshold is unchanged. In the clean pass the hook still fails. In the never-empty pass the hook is **FLAGGED**, not reclassified as PASS. The flag is visible in the sealed package. Compliant.
- **M12 FAIL CLOSED**: No calibration → `hook_bar_under` returns `None` → hook stays hard → doesn't open. Model failure → no ratings → no hooks open. Exception → propagates → no package. Compliant.
- **LAW 22** (v2f byte-identical re-render): This change only activates in the `never_empty` / `soft=True` path. The v2f reference was produced by the clean pass. No impact. Compliant.
- **Smallest diff / no new renderer / GPU0 / no publishing**: The diff touches only `package.py`, `package_pin.py`, and tests. No new renderer, compositor, or selector. Compliant.

---

P1_OR_WORSE: 0