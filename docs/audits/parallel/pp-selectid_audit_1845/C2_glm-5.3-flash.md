# glm-5.3-flash (z-ai/glm-5.3-flash) 86 s finish=stop usage in 5668 / out 2530 usd~0.055 (upper-bound price)

# pp-selectid — CYCLE 2 AUDIT (ruling 73 switch: RULES + DECODER)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honestly: very little of substance, because the diff is small and all three reviewers converged on the same reading. But reviewing their outputs against the diff line by line, three things they surfaced that I under-weighted:

- **GLM's P2-2 (repo-wide grep for `25cd6f15e6c9`)** — the strongest catch. The diff only shows the constant swap in `lock_precheck.py`; if any *other* module, cleanup routine, or doc hard-codes the old decoder sha, stale answers would be silently read. I treated the 15 green suites as sufficient; GLM correctly noted they are evidence, not proof, and named the concrete closing action (grep). I did not flag this.
- **GLM's P2-1 (consumer side of the `cut` field)** — the docstring now documents ruling-73 semantics, but the production code in this diff never *reads* `cut`; the new test's passing entry carries `cut` and passes, which only proves extra fields are tolerated, not that the consumer validates them. I noted the hold path but did not separately flag that the pass-with-`cut` path's consumption is unverified in this diff.
- **QWEN's framing of the M12 fail-closed chain** — that the "old answers never read" guarantee rests on the *pre-existing* `entry["rules"] == RULES` equality check, which the diff does not show. All three said this; it is the single largest trust assumption in the change, and it deserves to be stated as such rather than absorbed into "tests pass."

What nobody missed, and what I confirm: the constant values, the docstring, the two renamed expected filenames, the newer-old-rules-entry test, and the ruling-73 hold test all match the notice exactly.

## 2. WHERE DO I AGREE OR DISAGREE?

**GLM P2-1 (cut-field consumer unverified) — AGREE.** The diff's production change is two constants. The `cut` dict in the new test (line 67–68) exercises the *pass* path, but nothing in the diff shows `answer()`/`check()` distinguishing a ruling-73 pass from a ruling-72 pass. If the consumer ignores `cut` entirely, the test still passes. That is acceptable for a constant swap, but it is a real, if low, gap.

**GLM P2-2 (old-decoder exclusion rests on the read path) — AGREE, and it is the best finding of Cycle 1.** The filename convention (`<...>.<decoder[:12]>.json`, docstring line 7) plus the renamed test expectations (lines 37, 55) imply the read path derives the name from `DECODER`, but the diff shows neither `result_file`'s body nor the glob. If `25cd6f15e6c9` is hard-coded anywhere else, the guarantee "old decoder never read" breaks *silently* — exactly the failure mode the notice warns about. A repo-wide grep closes it; nobody ran one (none of us could, from a diff).

**GLM P2-3 (truncated) — AGREE that it's truncated;** its visible content duplicates P2-1, so nothing lost.

**GROK's output — AGREE, with one caveat.** Its "P2: none (from diff only)" is defensible: every concern it might have raised is outside the diff. But "no P2" slightly overstates certainty; GLM's P2-2 is a genuine residual risk that a diff-only review *cannot* clear, and saying "none" hides that. Partially agree: correct conclusion, incomplete confidence accounting.

**QWEN's compliance mapping (M12 fail-closed, LAW 20/M2, smallest diff) — AGREE.** The change is a versioning/identity switch, not a gate relaxation; thresholds untouched; the diff is minimal (two constants, one docstring, tests). Its conclusion that the filtering mechanism is "existing and tested" is the right reading, but it is an *assumption* licensed by the green suites, not a verified fact — QWEN says so itself, and I agree.

**Consensus framing — AGREE.** All three said SHIP: yes, no P0/P1. Nothing in their outputs contradicts the diff.

## 3. NEW FINDINGS FROM THIS REVIEW

**N-1 (P2, new): the "old rules never read" test does not exercise the decoder dimension, and the decoder tests do not exercise the rules dimension — the two guarantees are tested independently, never jointly.** Look at the diff:

- Lines 45–46: the old-**rules** entry is put into a file whose *name* (per the `entry`/`put` helpers, unchanged) presumably carries the **new** decoder — so it proves rules filtering only.
- Lines 37 and 55: the renamed filenames prove the *expected* name uses the new decoder, but no test places an entry under a `25cd6f15e6c9`-named file and asserts it is never read.

So the combined guarantee — "an answer under the old decoder *and* old rules, in an old-named file, is never read" — is never directly tested. It almost certainly holds (the filename derivation plus the rules equality are independent filters), but the notice's "Re-ask" requirement is a conjunction, and the test suite verifies each conjunct separately. This is a test-coverage observation, not a code defect; nobody in Cycle 1 noted the conjunctive gap.

**N-2 (P2, new, minor): the docstring's ruling-73 hold reason is asserted via `assertIn` on a prefix (line 72), not the full string.** The test puts `reason="ruling 73: the render cannot cut this span: OUT before the last locked word's end"` (lines 65–66) and asserts only `"ruling 73: the render cannot cut this span"` is in `why`. If the consumer truncated or mangled the reason's *tail* (the actual diagnostic — which span, which word), the test would still pass. Trivial, but the reason's diagnostic value is the point of ruling 73's hold.

**N-3 (observation, not a finding): the comment on the old DECODER line — "unchanged by ruling 72" — is correctly dropped (line 20→22),** and the new comment correctly carries the full 64-hex sha (line 23) matching the notice. Verified character-for-character against the notice: `8a101f222598a4f725e7cf85626e90fb2fae35df8d81d3ff430469728114e1a7`. ✔

**N-4 (observation): the hold test's second segment (lines 67–68) carries a `cut` with `error: None` and a `cut_duration` (19.9) exactly equal to `cut_out − cut_in` (957.4 − 937.5 = 19.9),** and `lead_in_pad_s` 0.47 — internally consistent. No arithmetic error in the fixture. ✔

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| RULES/DECODER constant correctness vs notice | PASS | PASS | Verified char-for-char against the notice, incl. full 64-hex sha (line 23). Unchanged. |
| Old-answers-never-read (rules dimension) | PASS (test-verified) | PASS (test-verified) | Lines 45–46: newer old-rules entry ignored. Unchanged. |
| Old-answers-never-read (decoder dimension) | PASS (implied) | PASS with caveat | Read path still not in diff; GLM's P2-2 grep recommendation adopted as a condition. Downgraded from implicit-PASS to conditional-PASS. |
| Ruling-73 hold semantics | PASS | PASS | Lines 63–72: hold → ok=False, verdict "hold", reason in `why`; pass-with-`cut` → "pass". Unchanged. |
| "Nothing else changes" | PASS | PASS | Diff touches only the two constants, the docstring/comment, and tests. Unchanged. |
| Test coverage of the *joint* old-decoder+old-rules guarantee | (not assessed) | GAP (P2) | New finding N-1: the two filters are never tested together. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM:**
1. **Old-decoder exclusion rests on unseen read-path code.** `pipeline/lock_precheck.py` (diff lines 19–24; the `result_file`/read implementation is not in the diff). *Action:* repo-wide grep for `25cd6f15e6c9` to confirm no other module, cleanup, or doc reads the old decoder's files. (GLM P2-2, adopted.)
2. **The joint guarantee (old decoder AND old rules, in an old-named file, never read) is never tested as a conjunction.** `tests/package/test_lock_precheck.py` — the old-rules test (diff lines 45–46) sits in a new-decoder-named file; the decoder dimension is only exercised via expected *filenames* (lines 37, 55). *Action:* one test placing an entry in a `...25cd6f15e6c9.json`-named file and asserting `no_difference`/never-read. (New, N-1.)
3. **Pass-with-`cut` consumption is unverified in this diff** — the test's passing entry carries `cut` (lines 67–68) but nothing shows the consumer reads or validates it; extra-field tolerance would suffice to pass. (GLM P2-1, adopted; low risk.)
4. **Hold reason asserted by prefix only** (line 72, `assertIn`), so truncation of the diagnostic tail would go unnoticed. (New, N-2; trivial.)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Run the repo-wide grep for `25cd6f15e6c9` — it is the only action that converts the change's weakest assumption (the read path derives filenames solely from the `DECODER` constant, everywhere) from "implied by green suites" into a verified fact, and it costs one command.

## 7. PRODUCTION READY?

**Yes with conditions.** The diff is correct, minimal, and matches the integrator's notice exactly; all three Cycle-1 reviewers and I agree there is no P0/P1. Conditions, precisely:

1. **Grep** the repo for `25cd6f15e6c9` and confirm the only remaining references (if any) are historical/doc, not read paths. (Closes P2-1.)
2. **Add one test** placing an entry in a `25cd6f15e6c9`-named result file and asserting it is never read, closing the conjunctive-coverage gap. (Closes P2-2; may ship as a fast-follow if the grep in (1) is clean, since the filename derivation plus rules equality make the failure mode practically unreachable.)
3. Optionally, strengthen line 72's assertion to the full reason string. (Trivial; not blocking.)

With (1) done and (2) scheduled, ship.