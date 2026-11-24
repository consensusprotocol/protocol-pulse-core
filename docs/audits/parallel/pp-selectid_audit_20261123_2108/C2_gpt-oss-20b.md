# gpt-oss-20b (openai/gpt-oss-20b) 11 s finish=stop usage in 7694 / out 1651 usd_reported=0.000302 usd~0.048 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
- **P1 (content_flags counting more than 3 kinds)** – I incorrectly assumed the cap was enforced on the number of flags, not on the number of *kinds*. The new `content_flags` now deduplicates by `flag_kind`, so a package can still exceed the 3‑kind limit if the same soft code appears on many clips.  
- **P1 (KeyError in `kind_sentences` for unknown codes on ≥2 clips)** – I overlooked that the new multi‑clip path uses `STEP_A_SOFT_MANY`/`EDGE_WORDS_MANY` and falls back to the original dicts only if those look‑ups fail. A future soft/edge code not present in the `_MANY` dicts would raise a `KeyError`.  
- **P2 (6‑clip medley not stripped by `_CLIP_REF`)** – I missed that the regex only matches “Two‑Five clips” and “The opening/second… clip” patterns. A 6‑clip medley would produce “6 clips (…)” which is not stripped, inflating the kind count.  
- **P2 (content_flags filtering only FLAGGED rows)** – I did not notice that the new implementation ignores flags on rows whose status is not `"FLAGGED"`. This is a silent behavioural change from the original.  
- **P3 (identical sentences collapsing)** – I did not consider that two different flags with the same gate string and identical sentence would collapse into one kind.  
- **P3 (missing test for multi‑clip path with unknown code)** – I did not add a regression test for a code that is not in the `_MANY` dicts.  

**2. WHERE DO I AGREE OR DISAGREE?**  

| Finding | Source | My stance | Reason |
|---------|--------|-----------|--------|
| `content_flags` can count >3 kinds | GPT‑OSS P1 | **Agree** – the cap is on kinds, not flags. | The new logic deduplicates by `flag_kind`. |
| `kind_sentences` KeyError | QWEN P1 | **Agree** – missing fallback to original dicts. | The diff shows `or STEP_A_SOFT.get(c) or EDGE_WORDS.get(c)` added, but the original code had no such fallback. |
| 6‑clip regex issue | QWEN P2 | **Agree** – regex does not match “6 clips”. | The regex only covers 2‑5 clips. |
| `content_flags` filtering FLAGGED rows | QWEN P2 | **Partially agree** – the rule says “FLAGGED rows”, so this is intentional, but the change is a silent behavioural shift. | The original code counted all flags regardless of status; the new code only counts FLAGGED. |
| Identical sentences collapse | GPT‑OSS P2 | **Agree** – this is a real risk. | Two different flags with same gate and sentence will be counted as one kind. |
| Missing test for unknown code | QWEN P3 | **Agree** – a regression test is needed. | Future soft/edge codes could break. |
| `_CLIP_REF` not matching “The first clip” | QWEN P3 | **Agree** – low risk but worth documenting. | The regex could be broadened. |

**3. NEW FINDINGS FROM THIS REVIEW**  
- **`flag_kind` does not strip the clip reference for PER_CLIP_KIND gates** – this is intentional, but the comment in the code could be clearer.  
- **`seg_marks` now counts distinct step‑A and edge codes separately** – this matches the rule but may double‑count a code that appears both as a step‑A flag and an edge flag on different clips.  
- **`content_flags` now excludes the exception gate entirely** – this is correct, but the code still includes a check for `g != EXCEPTION_GATE`.  
- **`review_problems` message now mentions “kinds of review flag”** – this is a cosmetic change but improves clarity.  

**4. REVISED SCORES**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `content_flags` | P1 | **P1** | Cap is on kinds; new logic may allow >3 kinds. |
| `kind_sentences` | P3 | **P1** | KeyError risk for unknown codes on ≥2 clips. |
| `_CLIP_REF` regex | P3 | **P2** | 6‑clip medley not stripped. |
| `content_flags` status filtering | P2 | **P2** | Silent behavioural change. |
| `flag_kind` collapse | P2 | **P2** | Identical sentences collapse. |
| Tests coverage | P3 | **P2** | Missing regression test for unknown code. |

**P1_OR_WORSE: 2** (two P1 findings: `content_flags` cap and `kind_sentences` KeyError)

**5. FINAL PRIORITY LIST**

| Priority | Issue | File:Line | Action |
|----------|-------|-----------|--------|
| **P0** | None | – | – |
| **P1** | `content_flags` may allow >3 kinds (cap on kinds) | `pipeline/package_pin.py:118-119` | Add explicit check that the number of distinct kinds ≤ 3 before allowing the package; otherwise return a refusal. |
| **P1** | `kind_sentences` KeyError for unknown codes on ≥2 clips | `pipeline/package.py:36-38` | Ensure fallback to original dicts (`STEP_A_SOFT.get(c) or EDGE_WORDS.get(c)`) before defaulting to `c`. |
| **P2** | 6‑clip regex not stripping “6 clips” | `pipeline/package_pin.py:98-99` | Extend `_CLIP_REF` to match numeric clip counts ≥6 or use a more general pattern. |
| **P2** | Silent status filtering in `content_flags` | `pipeline/package_pin.py:118-119` | Add documentation/assertion that only FLAGGED rows are counted; optionally add a test to confirm no non‑FLAGGED rows carry flags. |
| **P2** | Identical sentences collapse in `flag_kind` | `pipeline/package_pin.py:102-106` | Add a comment explaining the intentional collapse; consider adding a test that two distinct flags with same sentence are counted once. |
| **P2** | Missing regression test for unknown code on ≥2 clips | `tests/package/test_ruling_137.py` | Add a test that feeds a dummy code not in `_MANY` dicts on two clips and asserts no KeyError. |
| **P3** | `_CLIP_REF` not matching “The first clip” | `pipeline/package_pin.py:98-99` | Update regex to include “first” or add a comment. |
| **P3** | `flag_kind` comment clarity | `pipeline/package_pin.py:102-106` | Clarify that PER_CLIP_KIND prefixes are preserved. |

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Add a guard in `content_flags` that counts distinct kinds (via `flag_kind`) and rejects any package with more than three kinds, ensuring the 3‑kind cap is enforced regardless of how many clips a single soft code appears on.

**7. PRODUCTION READY?**  
**No** – the 3‑kind cap and KeyError risk must be fixed before shipping. Once those P1 issues are resolved and the regression tests added, the code can be considered production‑ready.