# qwen3.8-27b (qwen/qwen3.8-27b) 786 s finish=stop usage in 18182 / out 28878 usd_reported=0.024691 usd~0.488 (upper-bound price)



# Code Audit — pp-selectid / RULING 141 (3) THE LINE-UP CHAIN, PHASE A

## Scope of review

I reviewed the 462-line diff (C1_STEP.diff) covering `pipeline/package.py`, `pipeline/package_pin.py`, and `tests/package/test_ruling_137.py`, against the five questions posed, the governing laws, and the technology-stack constraints.

---

## Findings

### [P2] `over_budget(ai)` gate sits before the retry and can silently suppress it

**Location:** `package.py` lines 140–144 (the `_build` loop).

```python
if over_budget(ai):
    break
if total >= lineups:                      # RULING 141 (3): the judged-line-up budget ran out
    k_ = best_kept(kept)
    swapped, retried, accept_key, accept_soft = list(k_["segs"]), True, k_["key"], k_["soft"]
```

The retry is designed to fire when the *judged-line-up* budget (`total < lineups`) is exhausted. However, the per-angle `over_budget(ai)` check executes first and `break`s out of the loop entirely. The retry consumes **zero** new model calls (the verdict is read from `judged[key]`, and `total` does not increment for cached verdicts at line 162). If `over_budget` is a per-angle API-call budget, the retry is correctly blocked. If it is a per-angle *judged-line-up* budget (same axis as `total`), the retry is incorrectly suppressed: a valid kept candidate is discarded even though no new call is needed.

The ruling text says "the judged-line-up budget ran out: only the kept candidate's one retry reaches here." It does not mention the per-angle budget. **Clarify whether `over_budget` is the same axis as `total` or a different one; if it is the same axis, move the retry before the `over_budget` check or add an exception for the cached-retry case.**

---

### [P2] `coherence_soft` does not validate the main verdict's `vo_point` value when a panel is present

**Location:** `package.py` lines 64–69.

```python
if any(type(cl.get(lb)) is not int for lb in labs[1:]) or type(coh.get("vo_point")) is not int:
    return None
rest = lambda a: _line_ok(a.get("through_line")) and type(a.get("vo_point")) is int and \
    a["vo_point"] >= fl["vo_point"]
ans = (coh.get("panel") or {}).get("answers")
if not (sum(bool(rest(a)) for a in ans) * 2 > len(ans) if ans else rest(coh)):
    return None
```

When `ans` is non-empty, the majority-of-answers check is the decision. The main `coh["vo_point"]` is type-checked (line 64) but its **value** is never compared to `fl["vo_point"]`. A coherence verdict with `vo_point = 1` (far below the floor of 3) and a panel where 2-of-3 answers have `vo_point = 4` would pass `coherence_soft`. This is likely intentional (the panel is the decision-maker, not the aggregate), but the ruling text says "the VO point at its floor" without qualifying "per panel answer." **Add a comment or an explicit check on `coh["vo_point"] >= fl["vo_point"]` when a panel is present, to make the intent unambiguous for future readers.**

---

### [P2] `lineup_soft` and `coherence_soft` assume `floors` dict keys without a guard

**Location:** `package.py` lines 37, 63, 67, 71.

```python
floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
# ...
fl = coh.get("floors") or STANDARD_LINEUP["coherence"]
# ...
a["vo_point"] >= fl["vo_point"]
# ...
cl[lb] < fl["clip"]
```

If a medley or coherence verdict carries a `floors` dict that is missing the `"clip"` or `"vo_point"` key, a `KeyError` propagates uncaught. M12 (fail closed) is satisfied in the sense that the exception rejects the package, but the failure mode is an unhandled exception rather than a clean `None` return. **Wrap the key access in a `.get()` with a fallback to the standard floor, or add an explicit key-presence check that returns `None`.**

---

### [P3] `kept` list can accumulate duplicate entries for the same key

**Location:** `package.py` lines 173–179.

If the search re-encounters the same set of segments (same `key`) in a later iteration of the while loop, the candidate is appended to `kept` again. `best_kept` picks the same entry (identical `n` and `low`), so the retry is correct. The duplicate is harmless but wastes a small amount of memory and makes the `soft_record` log noisier. **Consider a `key in {k["key"] for k in kept}` guard before appending.**

---

### [P3] `test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too` has a hard-to-read conditional assertion

**Location:** `test_ruling_137.py` lines 427–429.

```python
self.assertEqual(sum(bool(t.get("kept")) for t in out["never_empty"]["soft_record"]["tried"]
                     if t.get("kept")) if not out.get("package") else len([t for t in out["tried"]
                                                                          if t.get("kept")]), 2)
```

The ternary switches the data source based on whether a package was sealed, making the assertion difficult to verify by eye. **Split into two assertions (one for the no-package case, one for the package case) or extract the count into a named variable with a comment.**

---

### [P3] `rec["kept"]` is written but never read in the logic

**Location:** `package.py` line 179.

```python
rec["kept"] = ks
```

This is purely for the `soft_record` log. It does not influence any gate, retry, or inventory decision. This is fine for observability, but a brief comment noting it is log-only would prevent a future reader from assuming it feeds a decision.

---

### [P3] `coherence_soft`'s `done` parameter is a tuple; membership is O(n)

**Location:** `package.py` line 72.

```python
"n": sum(lb not in done for lb in weak)
```

`done` is `(accept_soft or {}).get("weak") or ()` — a tuple of clip labels. For the expected 2–4 clips this is negligible, but a `frozenset` would make the intent (set membership) clearer and scale if the clip count grows.

---

## Answers to the five posed questions

**(1) Can a HARD failure be kept or accepted?**
No. `lineup_soft` returns `None` (hard) for: not measured, no through-line (`_line_ok` fails), hook failing its own bar (`hook_own(...).get("passes")` is falsy), any clip unrated (`type(cl.get(lb)) is not int`), or nothing to flag. `coherence_soft` returns `None` for: not measured, hook not passing, no through-line, VO point under its floor, any rating missing, or no weak clip. The lock, vision, writes, and re-screen gates run unchanged after the retry and are not softened. The through-line, the hook's own bar, the lock, non-join L-y checks, and coherence's VO point are all hard. **Compliant.**

**(2) Is the clean pass unchanged?**
Yes. Every new code path is gated on `soft` (the `_build` parameter, `False` in the clean pass). Specifically:
- The while condition reduces to the original when `soft` is falsy.
- `soft_joins_of(med)` returns `[]` when `med.get("soft")` is absent, so the `ly_shape` bridge check and the ruling-37 check are byte-identical to the pre-change logic.
- `accept_key` is `None`; `key == accept_key` is never true.
- `coherence_soft` is never called (`key == accept_key` is false).
- In `inventory`, `chain` is `None` (requires `soft`), so `med_fl` contains only the pre-existing hook-bar sentence, `coh_fl` is `[]`, and the `ly_shape` flags block is skipped.
- `package_pin.SOFT_GATES` additions only affect the soft pass's flagging logic.
**Compliant.**

**(3) The retry: once per angle, the cached verdict, the budget condition cannot loop.**
- `retried` is set to `True` at the moment the retry is initiated (lines 144, 154). The while condition includes `not retried`, so the loop exits after the retry iteration. **Once per angle. ✓**
- The retry reuses the kept candidate's segments, which produce the same `key` as the original judgment. The verdict is read from `judged[key]` (cached). `total` does not increment (`med.get("cached")` is true). **Cached verdict. ✓**
- The budget condition `total < lineups` is the primary loop guard. The retry is the *only* path that enters the loop when `total >= lineups` (via `or (soft and kept and not retried)`). After the retry, `retried` is `True`, so the condition is false and the loop exits. **No loop. ✓**
- (Caveat: see the P2 finding on `over_budget`.)

**(4) The cap (unique sentences) and the one-doubt rule.**
- The cap is `REVIEW_FLAGS_MAX = 3`. At KEEP time: `seg_marks(segs) + ks["n"] <= 3`. At COHERENCE time: `seg_marks(segs) + accept_soft["n"] + cs_["n"] <= 3`. `seg_marks` counts per-clip step-A flags, edge flags, stand-soft, and the hook's flagged status. `ks["n"]` is `len(weak) + len(soft_joins)`. `cs_["n"]` is the count of coherence-weak clips **not** already in `accept_soft["weak"]` (the `done` parameter). The total equals the number of unique flag sentences. **Cap enforced. ✓**
- One-doubt rule: `coherence_sentences` reuses the chain's clip-rating sentence (via the `first` dict) for any clip that appears in both `chain["weak"]` and `cs["weak"]`. `review_flags_of` deduplicates by sentence text. A clip flagged by both the clips-alone and coherence verdicts produces exactly one sentence. **One doubt, one sentence. ✓**

**(5) The tests.**
Twelve new test methods cover:
- Unit: `lineup_soft` soft/hard boundaries (through-line, hook bar, unrated clip, question hook, no-flags); `coherence_soft` soft/hard boundaries (VO point, through-line, hook, panel majority, no-weak-clip); `seg_marks` counting.
- End-to-end (via `TM.Rig` running the real `_build`): weak clip seals flagged only in soft pass; two flagged joins (first bridged, second flagged on medley + ly_shape, once in `review_flags`); question hook join flags with no bridge and no write; 3 flags kept / 4th never; clean line-up found later wins; coherence flags only for accepted candidate (VO under floor still fails); one-doubt-per-clip against the cap; best-kept selection and budget-end retry; inventory rows flag only in soft pass and only on passing shape; no through-line never kept.
- Mutation: 22 of 24 killed. C1 (retry's `soft`) is equivalent (kept fills only in soft pass). C12 (coherence widened to any later line-up) is not unit-tested but is noted as reachable only through the writer re-screen's hard refusal and its swap.

The tests are thorough and the end-to-end cases exercise the real build loop. The C12 gap is acknowledged and the risk is low (the path requires a specific sequence of hard refusal + swap after the accepted candidate). **Adequate.**

---

## Governing-law compliance

| Law | Status |
|---|---|
| SENTENCE LAW | Not touched by this diff. |
| SELECTION LOCK | Not touched. |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Not touched. |
| CREDITS / L-a / L-b / L-c / L-d / L-e / L-f / L-g / L-h / L-i / L-j / L-k / L-l | Not touched. |
| LAW 20 / M2 | The soft gates introduce a **FLAGGED** status distinct from **FAIL**. Hard gates (through-line, hook bar, lock, non-join L-y, VO point) remain hard stops. No gate is reclassified as a false positive; the soft failures are a new, explicitly bounded category (≤ 3 flags). Compliant. |
| M12 FAIL CLOSED | Missing data (unmeasured verdict, missing through-line, unrated clip, missing floors key) returns `None` from `lineup_soft`/`coherence_soft`, which means the candidate is not kept. Exceptions propagate (reject). Compliant (see P2 on unguarded `floors` key access). |
| LAW 22 | Not touched. |
| Smallest diff / M1 / GPU0 / no publishing | The diff is confined to the line-up chain logic in `package.py`, two constants in `package_pin.py`, and tests. No new renderer, compositor, or selector. Compliant. |

---

P1_OR_WORSE: 0