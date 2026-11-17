# qwen3.8-27b (qwen/qwen3.8-27b) 221 s finish=stop usage in 18319 / out 13015 usd_reported=0.010132 usd~0.250 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261117_1435 | RULING 141 (3), THE LINE-UP CHAIN, PHASE A

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GPT-OSS-20B's P0/P1 claims:** All five were refuted by the Cycle 1 consensus, and I confirm the refutations on re-read.

- The `med` / `med[0]` "undefined variable" claim (P0 #1, #2): The code at line 234–238 reads `medley[0]` and `medley[1]` (the tuple unpacked from the `medley` parameter). There is no bare `med` in `inventory`'s scope. `grep` confirms zero occurrences of `med[0]` in the file. **Refuted.**
- The "no join sentences when `medley[0]` is False" claim (P0 #3): For the accepted candidate, line 164 sets `ok_m = True` before the inventory call, so `medley[0]` is True. The two-joins end-to-end test (line 358–368) asserts the medley and ly_shape rows are FLAGGED with the join sentence. **Refuted.**
- The question-hook P1 claims (#4, #5): The coordinator's 14:35 ET scope update makes ruling 37's join SOFT. The bridge is never placed at the question hook's first join (line 40 excludes it; line 198 skips it via `soft_joins_of`). The end-to-end test at line 403–415 asserts `pk.get("bridge")` is None and the write join is None. **Refuted by agreed scope.**

**Qwen's P2s:** All three are by design or correctly declined.

- `over_budget(ai)` before the retry: This is ruling 41's per-angle money stop. The retried candidate would still need to pass the writes and vision gates, which consume budget. If the money says stop, no retry. **By design.**
- `coherence_soft` not checking the summary `vo_point` under a panel: The panel is the decision-maker (majority of answers). The summary `vo_point` is type-checked (line 64) but its value is the panel's aggregate, not an independent gate. **By design.**
- `floors` keys without a guard: `medley()` and `coherence()` always write `floors` from `lineup_floors` (calibrated or standard), which always contains `"clip"` and `"vo_point"`. Every existing reader uses the same unguarded access. **Declined.**

**Gemma's P3** (lambda redefinition in `coherence_soft`): Valid but trivial. The panel has at most a handful of answers; the lambda is redefined once per call, not per answer. No performance concern.

**I missed nothing material.** My Cycle 1 assessment aligned with the consensus.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My position |
|---|---|---|
| `med` undefined / `med[0]` | GPT-OSS P0 #1, #2 | **Agree with refutation.** Code reads `medley[0]`. |
| No join sentences when `medley[0]` False | GPT-OSS P0 #3 | **Agree with refutation.** `ok_m` is forced True for the accepted candidate. |
| Question hook join is hard | GPT-OSS P1 #4, #5 | **Agree with refutation.** Scope update makes it soft; bridge is never placed there. |
| `over_budget` suppresses retry | Qwen P2 | **Agree: by design.** Money stop is a different axis from judged-line-up budget. |
| Panel `vo_point` not checked | Qwen P2 | **Agree: by design.** Panel majority is the decision; summary is type-checked. |
| `floors` keys unguarded | Qwen P2 | **Agree: declined.** Invariant maintained by `lineup_floors`. |
| Duplicate `kept` entries | Qwen P3 | **Agree: harmless.** `best_kept` picks the same entry; one retry. |
| Hard-to-read test assertion | Qwen P3 | **Agree: cosmetic.** The ternary is correct but dense. |
| Lambda redefinition | Gemma P3 | **Agree: trivial.** No functional impact. |

I **disagree with no finding** from any model. The consensus is correct.

---

## 3. NEW FINDINGS FROM THIS REVIEW

After a line-by-line re-read with the other models' outputs in hand, I found **no new P0, P1, or P2 issues**. Two P3 observations:

**[P3] `coherence_sentences` builds `first` for all chain weak clips, not just the overlap.**
Line 94: `dict(zip((chain or {}).get("weak") or {}, chain_sentences(dict(chain, soft_joins=[]), who)))` generates a sentence for every clip in `chain["weak"]`, even those not in `cs["weak"]`. The extra entries are simply never looked up. Wasteful by at most one or two string allocations. No functional impact.

**[P3] `seg_marks` uses `len(m.get("edge_flags") or [])` without `set()`, unlike `step_a_flags`.**
Line 19: `step_a_flags` is deduplicated via `set()`, but `edge_flags` is counted as a raw list. In practice, edge flags are unique per clip (a clip is either cuttable or not, in/out are binary), so duplicates cannot occur. If a future change introduces duplicate edge flags, this would overcount. Not a bug today.

**Verification of the five requested checks:**

1. **Can a HARD failure be kept or accepted?** No. `lineup_soft` returns None for: not measured, no through-line, hook failing its own bar, any clip unrated, nothing to flag. `coherence_soft` returns None for: not measured, hook failing, no through-line, VO point under floor (majority for panel), any clip unrated, no weak clip. The lock, vision, writes, and re-screen are untouched by the soft logic. The through-line is checked in both functions. **Confirmed hard.**

2. **Clean pass unchanged?** Every new code path is gated by `soft` (the `never_empty` pass flag) or by `key == accept_key` (which is None in the clean pass). `soft_joins_of(med)` returns `[]` for non-soft verdicts, so the `ly_shape` and bridge logic at lines 113, 117, 189, 198 are no-ops in the clean pass. The inventory's `med_fl`, `coh_fl`, and `chain` are all empty/None when `soft` is False. **Confirmed unchanged.**

3. **Retry: once per angle, cached verdict, budget condition cannot loop.** `retried` is set to True at the moment of retry (lines 144, 154). The while condition `(total < lineups or (soft and kept and not retried))` becomes False for the retry branch once `retried` is True. The cached verdict is read from `judged[key]` (line 161–162); `total` does not increment for cached/replayed verdicts. The retry fires at exactly two points: the budget-end (line 142) and the search-exhaustion (line 152), both guarded by `not retried`. **Confirmed: one retry, no loop.**

4. **Cap (unique sentences) and one-doubt rule.** The cap is enforced at keep-time (line 176: `seg_marks + ks["n"] <= chain_cap()`) and at coherence-accept-time (line 226: `seg_marks + accept_soft["n"] + cs_["n"] <= chain_cap()`). `cs_["n"]` excludes clips already in `accept_soft["weak"]` (the `done` parameter, line 72). In the inventory, `coherence_sentences` reuses the clips-alone sentence for overlapping clips (line 94–97), so `review_flags_of` sees each sentence once. The test at line 389–401 verifies: clip_02 (in both) gets one sentence; clip_01 (coherence only) gets its own; total is 2, not 3. **Confirmed.**

5. **Tests.** 12 new tests cover: unit tests for `lineup_soft` and `coherence_soft` (including panel majority, hard-failure rejection); end-to-end for weak clip, two joins (bridge + flag), question hook, 3-flag cap, 4-flag rejection, clean-lineup priority, coherence one-doubt, cap with one-doubt, retry selection (fewest flags), budget-end retry, inventory rows (soft pass only, shape must pass), and no-through-line rejection. Mutation testing: 22 of 24 killed. C12 (coherence softening widened to non-accepted candidates) is not unit-tested but is structurally unreachable in the current flow (the writer re-screen's hard refusal and swap at line 4240 would need to produce a new line-up with the same `key` as `accept_key`, which is impossible since `key` is derived from segment IDs). **Adequate coverage.**

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `lineup_soft` / `coherence_soft` (soft-failure classification) | Correct | Correct | No change. Hard/soft boundary verified. |
| `_build` loop (keep, retry, budget) | Correct | Correct | No change. One-retry invariant holds. |
| `ly_shape` (ruling 37 + bridge exclusion) | Correct | Correct | No change. `soft_joins_of` no-op in clean pass. |
| Bridge / write logic (`bj`, `bridge_confirmed_by`) | Correct | Correct | No change. Soft joins excluded from bridging. |
| `inventory` (medley, ly_shape, coherence rows) | Correct | Correct | No change. All FLAGGED paths gated by `soft`. |
| `package_pin.SOFT_GATES` | Correct | Correct | No change. |
| Tests (12 new) | Adequate | Adequate | No change. C12 noted as structurally unreachable. |
| Clean pass isolation | Correct | Correct | No change. |

No score changes.

---

## 5. FINAL PRIORITY LIST

| # | Severity | File / Line | Description |
|---|---|---|---|
| 1 | [P3] | `package.py:94` | `coherence_sentences` builds `first` for all chain weak clips, not just the overlap with `cs["weak"]`. Wasteful by ≤2 string allocations. No functional impact. |
| 2 | [P3] | `package.py:19` | `seg_marks` counts `edge_flags` as a raw list (no `set()`), unlike `step_a_flags`. Duplicates cannot occur today; would overcount if a future change introduces them. |
| 3 | [P3] | `package.py:66` | `rest` lambda redefined on every `coherence_soft` call. Trivial; panel has ≤5 answers. |
| 4 | [P3] | `test_ruling_137.py:427–429` | The conditional assertion in `test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too` switches data source based on whether a package was sealed. Correct but hard to verify by eye. Consider splitting into two assertions. |

**No P0, P1, or P2 findings.**

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `soft` gate on every new code path (keep, retry, coherence acceptance, inventory rows, `ly_shape` exclusions) is the single most important structural decision in this diff: it guarantees the clean pass is byte-for-byte unchanged, and it means the entire RULING 141 (3) mechanism is a no-op unless the never-empty pass is active. If that invariant ever breaks (e.g., a future refactor removes a `soft` check), the clean pass would silently start accepting flagged candidates. A single integration test that asserts `out["package"] is None` for a soft-only failure in the clean pass (which `test_a_weak_clip_seals_flagged_only_in_the_never_empty_pass` already does at line 341–342) is the highest-leverage guard, and it is present.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all met):
- The clean pass is structurally unchanged (every new path gated by `soft` or `accept_key`).
- Hard failures (through-line, hook's own bar, lock, non-join L-y checks, coherence VO point, measured) are never kept or accepted.
- The retry fires exactly once per angle, reads the cached verdict, and cannot loop.
- The flag cap (3) is enforced at keep-time and coherence-accept-time; the one-doubt rule ensures a clip flagged in both clips-alone and coherence is counted once.
- The question hook's first join is soft (per the 14:35 ET scope update); no bridge is written after a question.
- 12 new tests cover all critical paths; 22 of 24 mutations killed; the 911-test suite passes.
- `package_pin.SOFT_GATES` correctly adds `"coherence"` and `"ly_shape"`.

P1_OR_WORSE: 0