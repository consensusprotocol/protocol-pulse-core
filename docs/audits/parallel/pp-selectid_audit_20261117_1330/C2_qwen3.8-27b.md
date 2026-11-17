# qwen3.8-27b (qwen/qwen3.8-27b) 191 s finish=stop usage in 11254 / out 14114 usd_reported=0.010587 usd~0.245 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: pp-selectid-20261117_1330 — RULING 137 Stage 2b (Soft Hook Bar)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1 I (like Gemma) concluded the code was clean with zero P1-or-worse findings. Re-reading the diff with the other models' annotations in hand, I confirm that conclusion was correct, but I want to be explicit about what I *nearly* missed and what the other models surfaced that I should have flagged:

- **Qwen's P2 on `CLIP_PLACE['hook']` coupling** (the flag sentence depends on a constant not defined in this diff): I noted the sentence format but did not call out the cross-file dependency. It is a real maintainability smell, though by design (stages 1 and 2a use the same pattern).
- **Qwen's P3 on the `False`-as-int test gap**: I saw the `isinstance(x, bool)` guard and the `True` test case but did not note that `False` is also an `int` subclass and deserves its own test line. Trivial, but a one-liner closes the gap.
- **GPT-OSS's P3 on hard-coded `HOOK_SOFT_MAX == 2` in the test**: I read the test and saw `self.assertEqual(PK.HOOK_SOFT_MAX, 2)` and accepted it as "by design" (the ruled value is pinned). GPT-OSS framed it as a brittleness concern. I partially agree: the assertion is intentional (it pins the ruled constant), but the *slice* `under[:PK.HOOK_SOFT_MAX]` correctly uses the constant, so the test would still pass if the constant changed to 3 — it would just assert `PK.HOOK_SOFT_MAX == 2` and fail. That's the right behavior. No change needed.

Nothing the other models caught changes my correctness assessment.

---

## 2. WHERE DO I AGREE OR DISAGREE?

### GPT-OSS-20B (2 P0, 2 P1 claimed)

| # | Claim | Verdict | Reasoning |
|---|-------|---------|-----------|
| P0-1 | "Mark set after `hook_own` runs, so flag is never set" | **DISAGREE — refuted** | The mark is set at diff line 69 (`m["hook_bar_soft"] = True`). `hook_own` is first called *after* that, at line 76 (`rated_open = [m for m in cleared.values() if can_open(m)]`), and again in every downstream reader (coherence :2089, medley :2153, rulings 62/63, hook_weak, coherence floors). The end-to-end test through `Rig.run` (the real `_build`) seals with the medley row `FLAGGED` in the exact sentence. Mutation H1 (mark not opening) is killed. |
| P0-2 | "Inventory never flags" | **DISAGREE — refuted** | Same root cause. `medley[1]["hook_own"]` carries `"flagged"` because the verdict's `hook_own(segs[0])` runs after the mark. The test `test_a_hook_under_the_bar_seals_flagged_only_in_the_never_empty_pass` asserts `pk["gates"]["medley"]["status"] == "FLAGGED"` and `review_flags_of` equals the exact sentence. |
| P1-3 | "A non-under-bar hook may be flagged" | **DISAGREE — refuted** | The `under` list is filtered by `hook_bar_under(m)` (line 66), which returns `None` for any hook that passes (empty `under` list → `"; ".join(...)` is `""` → `or None`). `hook_order` only *sorts* that already-filtered set. Mutations H6 and H12 are killed. |
| P1-4 | "Vision paid for every opener before marking" | **DISAGREE — refuted** | `hook_ratings` (line 60) is the Grok text-based hook *rating* (scroll/alone/setup 1–5), not a vision call. The vision check is `see(rated_open)` at :3343, which runs *after* the mark and *after* `rated_open` is computed. `rated_open` includes at most `HOOK_SOFT_MAX = 2` extra hooks. The cap bounds the extra vision calls. |
| P2-5 | Duplication between `hook_bar_under` and `hook_own` | **DISAGREE — declined** | `hook_bar_under` is the single source of the soft detail string. `hook_own` calls it. There is no duplicated logic. |
| P3-6 | "Double pop of `hook_rating`" | **DISAGREE — refuted** | One `pop` at line 57 (start of hook stage). The later line 63 *assigns* `m["hook_rating"] = rated.get(mid) or {...}`. That's a set, not a second pop. |
| P3-7 | Hard-coded `HOOK_SOFT_MAX` in test | **PARTIALLY AGREE** | The assertion `self.assertEqual(PK.HOOK_SOFT_MAX, 2)` is intentional (pins the ruled value). The slice uses the constant. No change needed, but the comment could say "ruled value" to prevent future confusion. |

**GPT-OSS's P1_OR_WORSE: 2 → my correction: 0.** Every P0 and P1 is refuted by the code flow and the passing end-to-end tests.

### QWEN3.8-27B (2 P2, 3 P3)

| # | Claim | Verdict |
|---|-------|---------|
| P2-1 | `hook_bar_under` called up to 4× per marked hook | **AGREE it's true, DECLINE the severity.** Each call reads the per-minute cached `_live_bar()`. With `HOOK_SOFT_MAX = 2`, that's ≤ 8 dict reads per build. Not a hot path. If the cap is ever raised or `_live_bar` becomes expensive, it's a one-line fix (cache the detail in a local dict). P3 at most. |
| P2-2 | `CLIP_PLACE['hook']` coupling | **PARTIALLY AGREE.** The flag sentence depends on a constant defined outside this diff. By design (stages 1 and 2a use the same pattern), but a dedicated test pinning `CLIP_PLACE['hook'] == "The opening clip"` would make the coupling explicit. P3. |
| P3-1 | `False`-as-int test gap | **AGREE.** One line: add `self.hm(False, 5, 5)` to the hard-case loop. Zero cost. |
| P3-2 | Implicit ordering assertion | **AGREE.** `self.assertEqual(list(rec["soft_hook_bar"]), ["h", "x"])` is more self-documenting than the computed `under[:PK.HOOK_SOFT_MAX]`. |
| P3-3 | Stage label `"2a" → "2b"` | **AGREE it's a valid concern IF the field was previously emitted.** The spec says stages 1 and 2a are LIVE, so `"2a"` was already in production. Any downstream consumer filtering on `never_empty.stage == "2a"` will silently stop matching. A one-line migration note or a backward-compatible alias would be prudent. However, the diff context shows this is the *first* introduction of the `stage` key in the `never_empty` info dict (the old line was `"2a"` for the soft-back stage, now `"2b"` for the hook-bar stage). If no external consumer reads this field yet, it's a non-issue. **P3 with a caveat.** |

### GEMMA-4-31B-IT (0 findings)

**AGREE.** Gemma's analysis is thorough and correct. The hard/soft logic, strictness of `hook_bar_under`, vision cost bound, flagging/inventory, data integrity via `with_verdict`, and test coverage are all correctly characterized. No violations found.

### CLAUDE'S CYCLE 1 CONSENSUS

**AGREE with all refutations and declines.** The consensus correctly identifies that GPT-OSS's P0s are based on a misreading of the call order (mark set at line 69, `hook_own` first called at line 76), and that Qwen's P2s are valid observations but not correctness issues.

---

## 3. NEW FINDINGS FROM THIS REVIEW

After re-reading the diff line-by-line with all Cycle 1 annotations in context, I found:

### [P3] `HOOK_PART_WORDS` and `HOOK_PARTS` must stay in sync

Diff lines 7–10: `HOOK_PARTS = ("scroll", "alone", "setup")` and `HOOK_PART_WORDS = {"scroll": ..., "alone": ..., "setup": ...}`. If a future ruling adds a fourth part to `HOOK_PARTS` but forgets `HOOK_PART_WORDS`, `hook_bar_under` raises `KeyError` at line 32 (`HOOK_PART_WORDS[p]`). A one-line assertion at module load (`assert set(HOOK_PART_WORDS) == set(HOOK_PARTS)`) would catch this at import time.

### [P3] `hook_own` returns `None` when parts are unmeasured, but `can_open` must handle that

Diff line 39: `hook_own` returns `None` if any part is not a non-bool int. The callers (`can_open` at :1758, coherence at :2089, medley at :2153, etc.) must all handle `None`. The spec says "every reader therefore follows with no change of its own," implying they already handle `None` (they did before this change, when a hook had no rating). The end-to-end test confirms this works. No code change needed, but a comment at the `hook_own` call sites noting "returns None when unmeasured; caller treats as cannot-open" would aid future readers.

### [P3] The `test_at_most_the_best_two_under_the_bar_open` test's `rec` extraction is fragile

Diff lines 219–220:
```python
rec = out.get("prescreen") if out.get("package") else out["never_empty"]["soft_record"]["prescreen"]
rated = (out.get("hook_pool") or out["never_empty"]["soft_record"]["hook_pool"])["ratings"]
```
This handles both the "sealed" and "not sealed" cases, but the logic is dense. If the `never_empty` record structure changes, this breaks silently. A small helper (`_get_prescreen(out)`) would make the intent clearer. Not a correctness issue.

### [P3] The `who` parameter in `inventory` is used for the flag sentence but not validated

Diff line 101: `(who or {}).get('hook') or 'its channel'`. If `who` is `None` or lacks the `'hook'` key, the sentence falls back to `'its channel'`. The test uses `who={"hook": "Scott Melker"}`. No validation that `who` is a dict or that `'hook'` is a string. In practice, `who` is always a dict from the caller. P3.

**No new P0 or P1 findings.**

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `hook_bar_under` (new function) | Clean | Clean | Confirmed correct. All hard cases (no calibration, wrong rater, unmeasured part, bool-as-int) return `None`. Detail string format matches tests. |
| `hook_own` (modified) | Clean | Clean | `flag` is only set when `not ok and m.get("hook_bar_soft")`. `passes=ok or bool(flag)` is correct. No reader is affected incorrectly. |
| `_build` mark logic (lines 66–73) | Clean | Clean | Mark set after ratings attached, before `rated_open` computed. `HOOK_SOFT_MAX` cap enforced. `prescreen` and `log` correct. |
| `inventory` flag (lines 90, 100–102) | Clean | Clean | Flag only when `soft and medley is not None and hook_fl and medley[0]`. One sentence. `SOFT_GATES` includes `"medley"`. |
| `package_pin.SOFT_GATES` | Clean | Clean | `"medley"` added. Seal proceeds despite flag. |
| `build` wrapper (stage label) | Clean | Clean (P3 note) | `"2a" → "2b"`. Valid concern if external consumers exist, but likely first introduction of the field. |
| Tests (6 new) | Sufficient | Sufficient (3 P3 nits) | End-to-end through `Rig` is strong. 12/12 mutations killed. Nits: `False`-as-int gap, implicit ordering, `CLIP_PLACE` pinning. |
| `test_medley.Rig` (build_kw passthrough) | Clean | Clean | One-line addition. Correct. |

**No score changed from Clean to a defect.** The P3 nits are documentation/test-robustness improvements, not correctness issues.

---

## 5. FINAL PRIORITY LIST

| Priority | Finding | File / Line | Action |
|----------|---------|-------------|--------|
| **P0** | *(none)* | — | — |
| **P1** | *(none)* | — | — |
| **P2** | `CLIP_PLACE['hook']` coupling: the flag sentence depends on a constant not defined in this diff. A refactor of `CLIP_PLACE` silently changes the plain-language contract (RULING 138 (3)). | `pipeline/package.py` line 101; `pipeline/package_pin.py` (where `CLIP_PLACE` is defined) | Add a dedicated test that pins `CLIP_PLACE['hook'] == "The opening clip"`, or extract `HOOK_FLAG_PREFIX` as a named constant. |
| **P3** | `False`-as-int test gap: the hard-case loop tests `True` but not `False`. | `tests/package/test_ruling_137.py` line 158 | Add `self.hm(False, 5, 5)` to the loop. |
| **P3** | Implicit ordering assertion in `test_at_most_the_best_two_under_the_bar_open`. | `tests/package/test_ruling_137.py` line 222 | Replace `under[:PK.HOOK_SOFT_MAX]` with the explicit list `["h", "x"]`. |
| **P3** | `HOOK_PART_WORDS` / `HOOK_PARTS` sync: no assertion that the two are in lockstep. | `pipeline/package.py` lines 7–10 | Add `assert set(HOOK_PART_WORDS) == set(HOOK_PARTS)` at module level. |
| **P3** | Stage label `"2a" → "2b"`: if any external consumer filters on `never_empty.stage == "2a"`, it silently stops matching. | `pipeline/package.py` line 82 | Add a one-line comment: `"2b" replaces "2a" (stage 2a was the soft-back label; no external consumers as of this commit)`. |
| **P3** | `hook_bar_under` called up to 4× per marked hook in `_build`. | `pipeline/package.py` lines 66, 71, 73, and inside `hook_own` | Not a correctness issue. If `HOOK_SOFT_MAX` is ever raised or `_live_bar` becomes expensive, cache the detail in a local dict. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The code is correct and the tests are strong (12/12 mutations killed, end-to-end through the real `Rig`); the single highest-leverage change is **adding a one-line test that pins `CLIP_PLACE['hook']` to `"The opening clip"`**, because the plain-language flag sentence (RULING 138 (3)) is a user-facing contract that is currently coupled to a constant defined outside this diff, and a silent refactor of that constant would break the contract without any test failing.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all P2/P3, none blocking):
1. The `CLIP_PLACE['hook']` pinning test (P2) should be added before the next release that touches `CLIP_PLACE`, but does not block this merge.
2. The `False`-as-int test line (P3) and the explicit ordering assertion (P3) are zero-cost improvements that can land in a follow-up commit.
3. The `HOOK_PART_WORDS` / `HOOK_PARTS` sync assertion (P3) is a defensive measure for future changes.
4. The stage-label comment (P3) is documentation.

None of these conditions affect correctness. The hard/soft logic is sound: the clean pass is unchanged, the soft pass opens at most 2 under-bar hooks flagged in plain words, every hard case (no calibration, wrong rater, unmeasured part, bool-as-int) stays hard, the vision cost is bounded by `HOOK_SOFT_MAX`, the flag appears exactly once on the medley row, and the seal proceeds via `SOFT_GATES`.

P1_OR_WORSE: 0