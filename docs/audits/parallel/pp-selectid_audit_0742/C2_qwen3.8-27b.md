# qwen3.8-27b (qwen/qwen3.8-27b) 56 s finish=stop usage in 28994 / out 2931 usd~0.131 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0829
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Grok's P0 (R4 share change 40%→45% loosening the gate):** I missed this in Cycle 1. Grok correctly identified that `R4_MOMENTS_SHARE` changed from 0.40 to 0.45, which expands the acceptance region. However, the Cycle 1 consensus **refuted** this as a defect: the orchestrator's ruling 9 (08:29) explicitly changed the cap to 45%, and the deployed `edl_rules.py` reads `MOMENTS_VO_SHARE = 0.45`. The gate now mirrors the factory's own constant. The 63-word package that previously failed R4 at 41% now passes R4 at 38.9% but **fails the 70s runtime gate** (72.41s > 70s). The test `test_the_moments_r4_on_tonights_numbers` confirms this: `self.assertFalse(PK.RUNTIME_S[0] <= p63["runtime_s_estimate"] <= PK.RUNTIME_S[1])`. So the package is still refused, just by a different gate. This is **not** a LAW 20 violation — the orchestrator ruled the change. I agree with the consensus disposition.

**GLM's P0-1 (majority drops violations on unknown slots):** I missed this. GLM identified that a violation with a typo'd slot key (e.g., `"intro "` with trailing space) would be silently dropped. The Cycle 1 consensus **refuted** this on the code: `check_verdict` raises `ValueError` on a claim whose line is not a slot, producing `VERDICT_UNAVAILABLE` with slot `"-"`. Additionally, the C2 diff **hardened** this (H1): the `whole` lambda at line 325 now treats any violation whose slot is not in `slots` as a whole-reply failure: `whole = lambda v: v.get("slot") == "-" or v.get("slot") not in slots`. This means an unknown slot now fails **every** slot, not just gets dropped. I agree with the refutation and the hardening.

**Qwen's P0-3 (runtime mirror faithfulness):** I missed this. Qwen correctly noted that the diff does not show `edl_rules.py`, so the mirror's faithfulness cannot be verified from the diff alone. However, the test at line 658 pins the expected values (`14.30`, `2.5`, `1.0`), and the docstring explicitly references `edl_rules._r4_moments` at `main a5ec0f17`. The `pin_and_verify.py` script (lines 394-395) copies the **deployed** `edl_rules.py` and runs `edl_rules.rule_r4` against the pin, providing an end-to-end verification. I agree this is a P1 uncertainty, not a P0.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My Position | Reasoning |
|---|---|---|
| Grok P0: R4 share 40%→45% | **Disagree** (not a defect) | Orchestrator ruling 9 explicitly changed the cap. The deployed factory uses 0.45. The 63-word package is still refused by the runtime gate. LAW 20 is not violated because the orchestrator ruled the change. |
| GLM P0-1: majority drops unknown-slot violations | **Disagree** (refuted + hardened) | `check_verdict` raises on unknown slots. C2 H1 hardening: `whole` lambda treats unknown slots as whole-reply failures. |
| Qwen P0-3: runtime mirror faithfulness | **Partially agree** (P1 uncertainty) | Cannot verify from diff alone, but `pin_and_verify.py` provides end-to-end verification against the deployed factory. |
| Grok P1: R4 algebra proof | **Agree** (addressed) | C2 adds `test_the_r4_word_bounds_invert_runtime_and_the_share_exactly` (lines 807-822), which exhaustively checks the algebra over content 15-50s and 1-4 VO lines. |
| GLM P1-2: unmeasured-run vote | **Agree** (correct) | The logic is sound: unmeasured runs vote "fail", and `2 * n_measured > len(runs)` ensures a majority of measured runs. |
| Qwen P0-2: self_repair span/compare | **Disagree** (not a bug) | The span is correctly rebuilt from `sw[1:]`, and the primary text does not contain the self-repair token. The comparison aligns. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `once_then_majority` does not verify that all runs used the same text.**
File: `pipeline/package.py`, lines 139-149.
The function takes `run(seed)` and `ok(result)` as callbacks. The caller (e.g., `fidelity()` in `run_given_package.py`, lines 540-553) passes a lambda that calls `VF.check` with the same `segs_v` and `lines`. However, there is no assertion that the text is unchanged across runs. If a bug or race condition causes the text to change between runs, the majority vote would be meaningless. The orchestrator's ruling says "a verdict that flips on **unchanged text**." The code does not enforce this.
**Failure scenario:** A concurrent write to `segs_v` or `lines` between runs causes different text to be evaluated. The majority vote passes a slot that would have failed on the original text.
**Mitigation:** Add a hash of the text to each run's result and assert equality in `once_then_majority`.

**P1-NEW-2: `with_votes` selects the first passing run, but the inventory row uses the merged result's `ok`.**
File: `pipeline/package.py`, lines 152-161.
`with_votes` returns `out = dict(rep)` where `rep` is the first passing run (or the first run if not passed). The inventory row (line 180-183) uses `fid.get("verdict")` and `fid.get("ok")` from the merged result. If the first passing run has a different `backend` or `replayed` value than the merged result, the inventory row may be inconsistent.
**Failure scenario:** Run 1 (seed 7) fails, Run 2 (seed 8) passes with backend "A", Run 3 (seed 9) passes with backend "B". `with_votes` returns Run 2's result. The inventory row shows backend "A", but the merged result's `backend` is "A / B". The `replayed` tri-state is computed over all runs, but the `backend` is from the first passing run.
**Assessment:** This is a minor honesty issue, not a gate decision. The `majority` field in the inventory row (lines 182-183) includes the votes and splits, so the full picture is available. **P2.**

**P2-NEW-3: `self_repair` in `edges()` does not check that the repair token is the **first** word of the clip.**
File: `pipeline/transcript_truth.py`, lines 263-265.
In `edges()`, `self_repair(ws, j, first)` is called where `j = i - 1` and `i` is the index of the clip's first word in the second recogniser's words. The `first` parameter is the clip's first word from the primary transcript. However, `self_repair` checks that `words[i+1]` (the next word) is the clip's first word. In `edges()`, `words[i]` is the clip's first word, so `words[i+1]` is the **second** word of the clip. This is correct: the repair token is at `i-1`, and the next word (at `i`) is the clip's first word.
**Re-evaluation:** The logic is correct. The repair token is at `j = i-1`, and `self_repair` checks that `words[j+1]` (i.e., `words[i]`) is the clip's first word. **No defect.**

**P2-NEW-4: `content_range` upper bound uses `VO_S[0]` which may be in words/second units.**
File: `pipeline/package.py`, line 60.
`RUNTIME_S[1] - FINAL_TAIL_S - VO_S[0] - R4_PREROLL_S * n_vo`. If `VO_S` is `(min_wps, max_wps)`, then `VO_S[0]` is a rate (words/second), not a time. Subtracting a rate from a time is dimensionally inconsistent.
**Assessment:** This is carried over from the old code (line 58 in the diff). If it was correct before, it is correct now. The test at line 686 (`self.assertLessEqual(PK.min_vo_words(29.91), PK.r4_max_vo_words(29.91, 3))`) does not exercise `content_range` directly. **P1, uncertain** — cannot verify `VO_S`'s units from the diff.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `package.runtime()` mirror | P1 (uncertain) | P1 (uncertain) | Cannot verify from diff alone, but `pin_and_verify.py` provides end-to-end verification. |
| `vo_fidelity.majority` | P1 (unknown-slot drop) | P2 (hardened) | C2 H1 hardening: unknown slots now fail every slot. |
| `self_repair` | P2 (weak heuristic) | P2 (addressed) | C1 K1: the next word must BE the clip's first word (`_w(next) == _w(first)`). |
| R4 share 40%→45% | P0 (Grok) | P2 (orchestrator ruling) | Orchestrator ruling 9 explicitly changed the cap. The deployed factory uses 0.45. |
| `once_then_majority` text invariance | Not identified | P1 (new) | No assertion that the text is unchanged across runs. |
| `with_votes` backend consistency | Not identified | P2 (new) | Minor honesty issue, not a gate decision. |
| `content_range` dimensional consistency | P1 (uncertain) | P1 (uncertain) | Carried over from old code. Cannot verify `VO_S`'s units. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1. `pipeline/package.py:139-149` — `once_then_majority` does not verify that all runs used the same text. Add a hash of the text to each run's result and assert equality.
2. `pipeline/package.py:60` — `content_range` upper bound uses `VO_S[0]` which may be in words/second units. Verify `VO_S`'s units and fix if dimensionally inconsistent.

**P2 MEDIUM:**
1. `pipeline/package.py:152-161` — `with_votes` selects the first passing run, but the inventory row uses the merged result's `ok`. Minor honesty issue.
2. `pipeline/package.py:17-24` — `runtime()` mirror faithfulness cannot be verified from the diff alone. `pin_and_verify.py` provides end-to-end verification, but the test at line 658 only checks one point.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a text hash to each run's result in `once_then_majority` and assert equality across runs, ensuring the majority vote is only applied to unchanged text as the orchestrator's ruling requires.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. **P1-1:** Add a text hash to each run's result in `once_then_majority` and assert equality across runs.
2. **P1-2:** Verify `VO_S`'s units in `content_range` and fix if dimensionally inconsistent.
3. **P2-1:** Run `pin_and_verify.py` against the deployed factory to confirm the `runtime()` mirror is faithful.
4. **P2-2:** Add a test that exercises `content_range` directly to verify the upper bound is dimensionally consistent.

The code is well-structured, the tests are comprehensive, and the orchestrator's rulings are correctly implemented. The remaining issues are minor and do not affect the gate's correctness for the current use case.