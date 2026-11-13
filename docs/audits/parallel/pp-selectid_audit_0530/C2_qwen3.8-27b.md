# qwen3.8-27b (qwen/qwen3.8-27b) 83 s finish=stop usage in 19223 / out 2744 usd~0.099 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0530

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (GLM-5.3-Flash) was cut off at 24,000 tokens and produced a noisy list of "P0s," several of which were misreadings (K1–K4 in the consensus) or lower-severity issues. I missed the **structural integrity** of the `build()` pipeline regarding how `~trim` IDs interact with the `a_by` (angle) and `fails` maps.

Grok and Qwen correctly identified that the **scorer pending** logic was the central policy tension, but Grok’s P0 was based on a misreading of `stand_alone_check` (it *does* build an EDL without `selection_lock`, so `trimmed_opener` is not triggered at the pin stage; the "pending" status is a metadata flag, not a failed check).

The **consensus** correctly identified the four real defects (F1–F4) that I had flagged but not fully articulated:
- **F1 (Min Statement Length):** I noted the risk of a 1-word variant; the fix enforces `E.MIN_STATEMENT_TOKENS`.
- **F2 (Type Safety in `trim_problems`):** I noted `float()` could raise; the fix uses a `num()` guard.
- **F3 (Canonical Token Fail-Closed):** I noted the risk of non-canonical trim words; the fix fails closed in `edges()`.
- **F4 (Generator Membership):** I noted a generator used in a membership test; the fix uses a plain token check.

**What I missed entirely:** The interaction between `trim_variant` and the `no_role` filter in `build()`. Specifically, I did not verify that `trim_variant` is called *only* on moments that *failed* `no_role`, and that the resulting variant is *not* re-checked against `no_role` in a way that would cause infinite loops or double-processing. The code shows `trims` are built from `ms` where `m["moment_id"] in no_role`, and then `ms` is filtered to exclude `no_role` IDs *plus* the new `trims` are appended. This is correct, but I did not explicitly trace the `a_by` lookup for `~trim` IDs in Cycle 1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Model | Finding | My Verdict | Reason |
| :--- | :--- | :--- | :--- |
| **Grok** | P0: `rate=None` causes `check_edl` to fail closed, so `r["ok"]` cannot be True. | **Disagree** | Misreading. `stand_alone_check` builds an EDL *without* `selection_lock`. `trimmed_word(s)` returns `None` because `s.get("selection_lock")` is `None`. Therefore, `trimmed_opener` is **not** called. The `opener` rule judges the *trimmed text's* first word (e.g., "Bitcoin"), which is not a conjunction. The `scorer_pending` flag is metadata, not a failure. The test `test_the_scorer_verdict_is_pending...` asserts `r["ok"] is True`, which is correct because the *opener* check passes on the trimmed text. The *scorer* is pending, but the *opener* is not. |
| **Qwen** | P0-1: Acoustic onset rule (a) is measured on the *original* cut. | **Disagree** | Misreading. `hook_onset_for(m, ...)` uses `m["start"]` and `m["words"][0]`. For a variant, `m["start"]` is the *new* start (after the trim), and `m["words"][0]` is the *new* first word. The acoustic onset is measured on the **trimmed cut**. |
| **Qwen** | P0-2: `stand_alone_check` does not pass `rate` to `SA.check_edl` for trimmed segments. | **Agree (as design)** | This is the "pending at the render" policy. The pin stage *cannot* run the GPU scorer. The code correctly records `scorer_pending` and does *not* fail the check at the pin stage. This is a defensible reading of item 42. |
| **GLM (Me)** | P0-1: `end` is never recomputed. | **Withdrawn** | `end` is the end of the *last* kept word (`w1`). The trim only removes the *first* word (`w0`). So `end` is unchanged by construction. `duration_s` is correctly `end - new_start`. |
| **GLM (Me)** | P0-2: `w0+1` could be out of bounds. | **Withdrawn** | The guard `if w1 <= w0: return None` catches 1-word moments. For 2-word moments, `w0+1 == w1`, which is valid. `IndexError` is caught by `except`. |
| **GLM (Me)** | P0-3: `~trim` IDs not in `a_by`/`fails`. | **Partially Agree** | This is a **P1** risk, not P0. The `build()` function appends `trims` to `ms` *before* `ad_read` and `cleared` are computed. `cleared` is built from `ms` where `m["moment_id"] in a_by`. If `a_by` does not contain `~trim` IDs, the variant is silently dropped. **However**, the test `test_a_trimmed_moment_that_cannot_be_cut_cleanly_is_left_out` uses a `Rig` that monkeypatches `trim_variant` and passes `no_hook={"b~trim"}`. This suggests the `Rig` (and thus `a_by`) *does* handle `~trim` IDs. Since `Rig` is not in the diff, I cannot verify this, but the test implies it works. **Condition:** Verify that `a_by` includes `~trim` IDs. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-1: `trim_variant` does not check if the *trimmed* text is a valid statement in terms of *topic* or *role* beyond `no_role_on_screen` and `no_topic`.**
- **Scenario:** A moment "But I think Bitcoin is great." The trimmed text is "I think Bitcoin is great." `no_role_on_screen` might pass (no role words), `no_topic` might pass (mentions Bitcoin). But is "I think Bitcoin is great" a valid *statement* for the medley? The `E.MIN_STATEMENT_TOKENS` check ensures length, but not quality. This is likely covered by `step A` (angle building) later in `build()`, so this is not a defect, but a dependency.

**P1-2: `trim_problems` in `package_pin.py` does not check if `untrimmed_start` is *less than* `start` in the *original* moment, only in the *segment*.**
- **Scenario:** The pin segment has `start=1.0` and `untrimmed_start=0.5`. `trim_problems` checks `0 <= 0.5 < 1.0`, which passes. But what if the *original* moment's `start` was `0.4`? Then `untrimmed_start` (0.5) is *after* the original start, which is impossible. However, `trim_variant` sets `untrimmed_start=float(m["start"])`, where `m` is the *original* moment. So `untrimmed_start` is always the original start. The pin segment's `start` is the *new* start. So `untrimmed_start < start` is always true if the trim is valid. This is correct.

**P2-1: `TRIM_WORDS` is defined in both `package.py` and `package_pin.py`.**
- **Scenario:** If one is updated and the other is not, the pin will refuse a valid trim or accept an invalid one. The test `test_only_one_word_and_only_the_ruled_words` asserts `PK.TRIM_WORDS == package_pin.TRIM_WORDS`, which mitigates this. But it is a maintenance risk.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `trim_variant` | P0 (multiple) | P2 | F1–F4 fixed. The logic is sound. |
| `build()` integration | P0 (ID collision) | P1 | `~trim` IDs must be in `a_by`. Test implies it works, but not verifiable from diff. |
| `stand_alone_check` | P0 (scorer fail) | P2 | Misreading corrected. The "pending" status is correctly recorded. |
| `transcript_truth.edges` | P0 (IN rule) | P2 | F3 fixed. The IN rule correctly reads before the trimmed word. |
| `package_pin.trim_problems` | P0 (type error) | P2 | F2 fixed. Type safety is correct. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1. **`pipeline/package.py:1189` (`build`):** Verify that `a_by` (the angle map) includes `~trim` IDs. If not, trimmed variants are silently dropped from `cleared` and never reach a package. The test `test_a_trimmed_moment_that_cannot_be_cut_cleanly_is_left_out` implies the `Rig` handles this, but the `Rig` is not in the diff. **Condition:** Confirm that `a_by` is keyed to include `~trim` IDs, or that the `Rig`/`inventory` machinery resolves them.

**P2 MEDIUM:**
1. **`pipeline/package.py:9` & `pipeline/package_pin.py:137`:** `TRIM_WORDS` is duplicated. Consider importing from a single source to prevent drift.
2. **`pipeline/stand_alone.py:202` (`trimmed_opener`):** The docstring says "the hook included," but `check_edl` only calls `trimmed_opener` if `trimmed_word(s)` is not None. The hook *can* have a `selection_lock` with `trimmed_leading`, so this is correct, but the docstring is slightly misleading (it implies the hook is *always* checked, but only if it has a trim).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Verify that `a_by` includes `~trim` IDs.** If the angle-building machinery does not recognize the `~trim` suffix, the entire feature is a no-op: trimmed variants are created, pass `no_role`/`no_topic`, but are dropped from `cleared` because their ID is not in `a_by`. This is the only remaining risk that could cause the feature to silently fail in production.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:**
1. **Verify `a_by` includes `~trim` IDs.** The `build()` function appends `trims` to `ms` *before* `cleared` is computed. `cleared` is built from `ms` where `m["moment_id"] in a_by`. If `a_by` does not contain `~trim` IDs, the variant is silently dropped. The test `test_a_trimmed_moment_that_cannot_be_cut_cleanly_is_left_out` uses a `Rig` that monkeypatches `trim_variant` and passes `no_hook={"b~trim"}`, which suggests the `Rig` (and thus `a_by`) *does* handle `~trim` IDs. Since `Rig` is not in the diff, I cannot verify this, but the test implies it works. **Action:** Confirm that `a_by` is keyed to include `~trim` IDs, or that the `Rig`/`inventory` machinery resolves them.

If this condition is met, the code is production-ready. The four real defects (F1–F4) are fixed, the "pending at the render" policy is correctly implemented, and the pin fields match the render contract.