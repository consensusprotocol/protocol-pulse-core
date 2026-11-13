# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 14517 / out 1410 usd~0.108 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-2315 (ledger_build path)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
In Cycle 1 I focused on subprocess isolation risks, the render-clock `now` propagation, and whether `M.record` + `rank_score` could leak unverified ledger fields. I completely missed GLM's concrete vacuous-None SHA case and the exact mechanics of `why` accumulation in `word_source` (lines 90/98/106). I also under-weighted Grok's empty-ledger-as-success scenario because I had not yet traced how the new `report["contract"]` guard interacts with the adapter's own `excluded` counts. Qwen's point on `rs[0]` channel identity for multi-row videos was invisible to me until the consensus table highlighted the per-video assumption.

2. WHERE DO YOU AGREE OR DISAGREE?
- GLM P0-1 (missing `transcript_sha256`): Disagree. `None != ts.segments_sha256(...)` correctly skips; the new test (test_a_record_whose_sha_does_not_match...) plus the post-edit SHA re-test refute the vacuous-pass worry.
- GLM P0-2 / Qwen P0-1 (punctuated sort + silent fall-through): Partially agree on visibility. The sort key is correct (`"punct" not in p` puts punctuated first), and the test `test_the_punctuated_record_is_read_first` proves it. However, the final `why` returned (and stored in `no_word_record_why`) loses which punctuated file was rejected; the report therefore still cannot distinguish "preferred punctuated record present but not sentence-ready" from "no record at all".
- Grok P0 (empty successful adapter read): Agree. The docstring update, explicit `if (out["report"] or {}).get("contract")` raise, and the empty-mock test now align with L-m / L-j. Empty is a measured result, not a quiet success.
- Grok P1 / GLM P1-1 (snap can change meaning): Agree the original was a real risk; the new `SNAP_GUARD` + test `test_a_snap_never_adds_a_negation_or_a_number` plus the exact 3-word boundary tests are a targeted, high-leverage mitigation. The ledger scores stay attached to the original mined text while the clip uses the word-record sentences — exactly what L-o and the ruling require.
- Qwen P0-2 (snapped span may not be sentence-ready): Disagree. `E.sentence_ready(src)` is a record-level property; `reanchor` only ever returns whole sentences `k0..k1` of that record. The consensus correctly refutes this.
- Qwen P1-1 (rs[0] channel_id): Agree it is a latent assumption but harmless under the integrator contract (one channel per video_id in the ledger).

3. NEW FINDINGS FROM THIS REVIEW
**P2-1: pipeline/ledger_build.py:156-157 (`no_word_record_why` key reuse)**  
When `src is None`, `path` is actually the `why` string returned by `word_source`. Thus `report["no_word_record_why"]` ends up with keys that are sometimes file paths and sometimes messages ("no word record in the store", "a word record that is not sentence-ready (law L-e)", etc.). Concrete inputs: 5 rows on vidA with no records + 3 rows on vidB whose punctuated record exists but fails `E.sentence_ready` → the dict mixes a path key with two distinct message keys and the counts are aggregated under the last `why` seen. The log line prints only totals; downstream report consumers expecting paths will see non-path strings. Counted, not silent, but violates the "every drop counted" promise of the diff header. (Test only exercises one why at a time.)

**P2-2: pipeline/ledger_build.py:89 + 157 (why accumulation loses first-failure information)**  
`why = why or "new message"` on read error but unconditional assignment on SHA and sentence-ready failures means the returned `why` is always the *last* failure encountered. A punctuated record that cannot be read *and* has a bad SHA will report only the SHA message. Combined with the key-reuse above, the report never surfaces the full set of reasons per video. Not a bypass of any law, but weakens the auditability the orchestrator ruling demands.

No P0 or P1 gaps; the SNAP_GUARD, adapter fail-closed contract, duplicate-span deduplication, and delivered-span overlap check are all solid and tested.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Adapter / rows()       | P1      | P2      | Explicit contract + tests now prove empty is never misread as failure |
| word_source() + report | P2      | P1      | Missed the why/path key mixing and lossy accumulation until Cycle 1 consensus |
| reanchor() / snap      | P1      | P2      | SNAP_GUARD + new tests close the meaning-change vector I originally rated higher |
| Test coverage          | P2      | P2      | No change; still no multi-why report test but otherwise comprehensive |

5. FINAL PRIORITY LIST
**P0 CRITICAL:** None.  
**P1 HIGH:**  
- pipeline/ledger_build.py:156-157 — change `no_word_record_why` to a list of `(why, count)` or a proper `Counter` so path strings never leak into the why dict and every distinct reason is visible.  
**P2 MEDIUM:**  
- pipeline/ledger_build.py:90-106 — make `why` accumulation explicit (e.g. `reasons.add(...)`) so the first failure that eliminated the preferred punctuated record is not lost.  
- tests/package/test_ledger_build.py — add a case exercising multiple distinct `no_word_record` reasons for the same video to protect the report shape.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Fix the report dict to separate "no record reasons" from paths so every drop is unambiguously categorized; this single cleanup would make the "every drop counted" claim actually true for downstream consumers and auditors.

7. PRODUCTION READY?
Yes with conditions: (1) refactor `no_word_record_why` to a clean `Counter` of reason strings (no path/why mixing), (2) add the multi-reason test, (3) update the dated proof pins in proof_ledger.py to a neutral placeholder or remove the default so the driver cannot accidentally use stale delivered spans.

**SHIP: yes with conditions**