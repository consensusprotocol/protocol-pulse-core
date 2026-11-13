# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 203 s finish=stop usage in 10623 / out 1237 usd~0.084 (upper-bound price)

**P0/P1/P2 Findings (Cycle 2, from diff only)**

**P2: pipeline/package.py:36** (in `_time_aligned`). Concrete scenario: two matching blocks with materially different per-word clock offsets (e.g. an edited re-post that splices two takes). `statistics.median` on the combined `(y-x)` list yields one offset; words from the minority block fall outside `REPOST_TIME_TOL_S`, potentially dropping `hit` below 80% of shorter length even though difflib found them. The test suite never exercises mixed-offset cases, so behavior is unverified. Risk low but real for any edited re-post.

**P2: pipeline/package.py:23 & 67**. `canon.canon_tokens` is called on whole-text vs. per-word-then-`" ".join`. The diff does not show `canon.py`; equivalence of the two normal forms cannot be verified. Tests pass because they use either exact upper-case (text path) or identical tokens (timed path), but any divergence would silently change grouping.

**P2: pipeline/package.py:108**. `next(x for x in keep if root_of(x) == root_of(mid))` re-walks the union-find for every duplicate. On a 300-moment build with one large transitive group this is negligible, but the linear search over `keep` (size = number of distinct roots) is unnecessary; the root->kept mapping could be built once.

No P0 or P1. All Cycle-1 concerns (text-only false positives, naive-time preference, tie-break, transitive closure, usable-count semantics, placement before STAND_ALONE) are resolved by the added timed-word path, explicit `naive→UTC`, tuple-keyed `min`, and test assertions. The 07:14 pair is correctly kept/recorded. O(n²) pruned by same-channel skip + multiset upper-bound; measured 2.3 s.

**SHIP: yes with conditions**

---

**CYCLE 2 INSTRUCTIONS RESPONSE**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's P1-1 on naive `published_at` handling (treated as unreadable before) and the exact tie-break semantics of the `min(..., key=at)` tuple. Qwen's P0 on short-text 80% fragility ("gold" vs "silver") was the largest miss; I had flagged it only as P2. Grok correctly noted the pre-check is a sound upper bound and that usable-count preservation was intentional. I had not spotted the median-offset technique's sensitivity to mixed clock skew.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM P1-1/P1-3: Agree on both (naive-time risk was real; transitive union-find matches the "ONE moment" intent).  
   - GLM P1-2 (SequenceMatcher non-optimality): Partially agree; still true but the added time-consistency check makes it acceptable.  
   - Qwen P0 (80% false-positive): Agree it was a P0 for the prior text-only version; disagree it remains one—the time-alignment test (different rhythms) directly refutes the gold/silver merge.  
   - Grok P2s: Fully agree; all verifiable invariants (K1-K3, placement, usable count, same-channel exclusion) hold in the diff.  
   - Consensus on K1/K2/K3 readings: Agree with all three.

3. **NEW FINDINGS FROM THIS REVIEW**  
   The two P2 items above (median on mixed offsets; canon call asymmetry; linear search for kept root). Additionally, `REPOST_ALIGN_MIN * short` uses Python float comparison on integers; for short=5 the threshold is exactly 4.0 so `>=` is fine, but any future non-integer threshold would need `math.ceil`. All conditional on unshown `canon.py` / `src_of` behavior.

4. **REVISED SCORES**  
   | Subsystem          | Cycle 1 | Cycle 2 | Why changed |
   |--------------------|---------|---------|-------------|
   | De-duplication logic | P1     | P2     | Time-alignment + explicit tests eliminated short-text false-positive risk I underestimated. |
   | Time / tie-break   | P1     | P2     | Naive-as-UTC fix and tuple-keyed min directly address GLM/Qwen points. |
   | Performance        | P2     | P2     | No change; measured 2.3 s still acceptable. |
   | Test coverage      | P2     | P2     | New `TestRuling53Reposted` is thorough for all stated cases. |

5. **FINAL PRIORITY LIST**  
   **P2 (MEDIUM)**  
   - pipeline/package.py:36 — mixed-offset median scenario (see above).  
   - pipeline/package.py:23 & 67 — verify `canon.canon_tokens` equivalence (cannot confirm from diff alone).  
   - pipeline/package.py:108 — replace linear `next()` with a root→kept dict.  
   No P0 or P1 must-fix items remain.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   Adding `_time_aligned` with median clock offset turns a loose bag-of-words similarity rule into a verifiable "same audio track" test, simultaneously fixing the gold/silver false-positive and satisfying the ruling's "time-aligned" wording.

7. **PRODUCTION READY?**  
   Yes with conditions: (a) confirm all production word records pass the `_timed_words` guards (fallback to equal-text is safe but must be measured), (b) monitor first production runs for any "matched through another copy" reasons on non-reposts, (c) ensure moment_id tie-break produces the numerically lowest id if ids are not zero-padded strings (diff uses Python tuple ordering). All other ruling requirements are met in the diff and tests.