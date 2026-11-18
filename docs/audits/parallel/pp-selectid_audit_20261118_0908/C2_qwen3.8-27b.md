# qwen3.8-27b (qwen/qwen3.8-27b) 136 s finish=stop usage in 4534 / out 5412 usd_reported=0.004070 usd~0.095 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## pp-selectid-20261118_0908 · C2_STEP.diff

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GPT-OSS-20B's P0 (L-y 4 violation):** I agree with the consensus refutation. `stand_soft_back` reads from `ms` (originals only). The trim variant is a separate pool entry added at line 23. `lineup_ok` (unchanged) enforces `len({m["video_id"]}) == len(segs)` under the `repeat_ok` exception, and the hard one-clip-per-video rule otherwise. An original and its trim variant share one `video_id`, so no line-up can take both. GPT-OSS conflated "both are in the pool" with "both can be selected." The pool is a candidate set; the line-up is a selection. I should have been more explicit about this distinction in Cycle 1.

**QWEN3.8-27B's two P2s (integration test gap, L-y 4 assertion gap):** These are the most substantive findings in the round. I underweighted test-coverage gaps in Cycle 1. The unit test exercises `stand_soft_back` in isolation with synthetic moments. It does not walk the full `_build` path where a trim variant is created, fails `trim_refused` (ruling 33 HARD), is filtered out of `trims`, and the original is then the sole selectable clip. Nor does it assert that `lineup_ok` rejects a hypothetical two-segment line-up containing both the original and the variant. These are real gaps, though they are gaps in *this diff's* tests, not in the system's safety.

**Gemma-4-31B-IT:** Thorough and correct. I agree with every point. No missed items.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Model | Finding | Verdict | Reasoning |
|-------|---------|---------|-----------|
| GPT-OSS | [P0] L-y 4 violation | **DISAGREE** | Refuted. `stand_soft_back` returns originals from `ms`; the variant is a separate pool entry. `lineup_ok` (unchanged) enforces one clip per video. The two share `video_id`. No line-up can select both. |
| GPT-OSS | [P3] Docstring wording | **AGREE** | The docstring is actually accurate as written ("An affirmed trim variant no longer keeps its original out"). The "old never-empty pass wording" concern is marginal. |
| GPT-OSS | [P3] Not in `__all__` | **AGREE** | Valid nit. `stand_soft_back` is accessed via `PK.stand_soft_back` in tests. Adding to `__all__` would clarify the public API. |
| QWEN | [P2] No integration test for build-147 path | **AGREE** | The motivating regression (trim fails ruling 33 → original lost) is not tested end-to-end in this diff. The existing STAND_ALONE e2e tests were written under the old invariant. |
| QWEN | [P2] L-y 4 mutual-exclusion not asserted | **AGREE** | A one-line assertion that a line-up containing both original and variant is rejected would make the invariant explicit at the point of co-existence. |
| QWEN | [P3] `import inspect` in test method | **AGREE** | Nit. Functionally harmless. |
| Gemma | All findings | **AGREE** | Correct analysis, no errors. |
| Consensus | GPT-OSS P0 refuted | **AGREE** | The refutation is sound. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

After tracing the full `_build` flow with the other models' analyses in hand, I found one additional item nobody explicitly called out:

**[P3] The `stand_soft` flag is set on the original moment's dict in `ms`, but the trim variant (a separate dict in the pool) carries no such flag. This is correct by design, but the interaction with `stand_ok` deserves a comment.**

When the line-up selects the original (flagged), `stand_ok` → `stand_soft_rows` finds it and the line-up passes. When the line-up selects the trim variant (unflagged), `stand_ok` checks STAND_ALONE normally; the variant must pass on its own merits. If the variant fails STAND_ALONE, the line-up is rejected — it cannot lean on the never-empty pass because it was never brought back by it. This is the correct behavior, but a one-line comment at the `stand_ok` call-site or in the `stand_soft_back` docstring noting "the trim variant is NOT flagged; it must pass STAND_ALONE independently" would prevent a future reader from wondering whether the variant inherits the flag.

No new P0, P1, or P2 findings.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `stand_soft_back` logic | PASS | PASS | Unchanged. Correct. |
| `_build` integration | PASS | PASS | Unchanged. The flag is set on originals only; variants are separate. |
| L-y 4 (one clip per video) | PASS | PASS | `lineup_ok` unchanged. Original and variant share `video_id`. |
| M12 (fail-closed) | PASS | PASS | `soft=False` → `{}`. `no_topic(m) is not None` → excluded. `stand_plain(m)` falsy → excluded. |
| RULING 141(2) compliance | PASS | PASS | Only opener-rule failures, no topic refusal, plain reason. |
| RULING 33 (trimmed cut HARD) | PASS | PASS | `trim_refused` unchanged. Variant still must pass independently. |
| Test coverage | PASS (with gap) | PASS (with gap) | Unit test is correct but narrow. Integration gap noted by QWEN. No change in severity. |
| Docstring / API surface | PASS | PASS | Minor nits only. |

No score changed. The code is correct; the gaps are in test breadth, not in logic.

---

## 5. FINAL PRIORITY LIST

| Priority | Finding | File / Line | Action |
|----------|---------|-------------|--------|
| [P2] | No end-to-end regression test for the build-147 path (trim fails ruling 33 → original is sole selectable clip → line-up passes via `stand_ok`) | `tests/package/test_ruling_137.py` (new test after line 50) | Add a test that: (a) creates a moment with an affirmed trim variant, (b) causes `trim_refused` to fire, (c) asserts the original carries `stand_soft` and is selectable, (d) asserts `stand_ok` passes on a line-up containing the original. |
| [P2] | L-y 4 mutual-exclusion not asserted for the new co-existence case | `tests/package/test_ruling_137.py` (companion to above) | Add a one-line assertion: a line-up containing both the original and its trim variant is rejected by `lineup_ok`. |
| [P3] | `stand_soft_back` not in `__all__` | `pipeline/package.py` (module-level `__all__`) | Add `"stand_soft_back"` to the export list. |
| [P3] | `import inspect` inside test method | `tests/package/test_ruling_137.py:49` | Move to top-level import or replace with a comment. |
| [P3] | No comment noting the trim variant is NOT flagged and must pass STAND_ALONE independently | `pipeline/package.py:14` (docstring) or `:28` (call-site) | Add a sentence to the docstring: "The trim variant is a separate pool entry with no `stand_soft` flag; it must pass STAND_ALONE on its own." |

**P1_OR_WORSE: 0**

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the end-to-end regression test for the build-147 path (P2, first item): a moment whose trim variant fails ruling 33 HARD, asserting the original comes back flagged, is selectable, and passes `stand_ok` — this locks in the fix and makes the L-y 4 co-existence invariant explicit at the point where it is introduced.

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

The logic is correct. No P0 or P1 findings. The fix is minimal, surgical, and restores the intended fallback behavior. The L-y 4 constraint is enforced by unchanged code. M12 fail-closed is preserved. RULING 141(2) and RULING 33 are both respected.

**Conditions before merge:**

1. **Add the end-to-end regression test** (P2): a test that walks the full `_build` path where a trim variant fails `trim_refused` and the original is the sole selectable clip. This is the test that would catch a future refactor silently re-introducing the `not in trims` guard.
2. **Add the L-y 4 assertion** (P2): a one-line check that a line-up containing both the original and its trim variant is rejected. This makes the co-existence invariant explicit at the point of introduction.

Both conditions are test additions, not code changes. The production code in `pipeline/package.py` is correct as-is and can ship.

---

P1_OR_WORSE: 0