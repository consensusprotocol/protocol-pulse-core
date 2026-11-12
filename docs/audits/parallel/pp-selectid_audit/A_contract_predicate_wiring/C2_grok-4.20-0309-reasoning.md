# grok-4.20-0309-reasoning (xAI, medley key) 261 s usage={'prompt_tokens': 43181, 'completion_tokens': 1491, 'total_tokens': 45747, 'prompt_tokens_details': {'text_tokens': 43181, 'audio_tokens': 0, 'image_tokens': 0, 'cached_tokens': 128}, 'completion_tokens_details': {'reasoning_tokens': 1075, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}, 'num_sources_used': 0, 'cost_in_usd_ticks': 602568500}

**CYCLE 2 AUDIT — pp-selectid (A_contract_predicate_wiring)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Cycle 1 I focused heavily on the id-parsing surface, the strict JSON contract, and the fail-closed paths for malformed replies. I under-weighted three things the Claude trio surfaced:  
- The `_anchor` inner-sentence gap (sentences strictly between two core `*` sentences bypassed D4(a)/(b) and the cap). My review treated the min/max core as the entire window.  
- Timestamp defaulting to 0 (both in eligibility.py and the row-marks helper) violating “unmeasured fails closed”.  
- The Recorder’s write-before-validate + seed omission, which defeats L-l retry semantics and makes empty/truncated replies sticky.  
I also did not notice that the original R1 patch erased the “HOLD (infrastructure)” decision and the per-cluster gate for unevaluated tiers.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **Unanimous U1–U4**: Full agreement. The supplied diff implements exactly the fixes the consensus demanded (inner-sentence loop in `_anchor`, `_time()` returning None, `Outcome.to_dict` carrying `why`, gate written on every screened cluster, non-vacuous test assertions, Recorder now includes seed and writes only after acceptance).  
- **M1 (R1 dropping scorer floors / verify_support / verify_reaction)**: Partial agreement. Law L-o reclassifies floors as ranking targets; the new `ModelChecks` wrapper (verify_support on claim + verify_reaction on non-core sentences) restores the independent verbatim checks without re-introducing a ranked pool. This is an acceptable evolution provided the checks actually run against the production `LocalLLM` (they do).  
- **M2 (Ollama transport escaping, missing finally)**: Full agreement on the original defect. The new `try/finally` around `L.stop()`/`E.close()` plus the explicit `urllib.error`/`TimeoutError` mapping to `ModelError` closes it. The GPU0 guard exception is intentionally left propagating — correct.  
- **Sonnet’s file_head default and backtest window issue**: Agree this was a latent bug; the diff correctly hard-codes `file_head=True` only for full-video store records and updates the backtest `offline_words` docstring + behavior.  
- Minor disagreements: Claude-Fable’s “three missing measurements pass silently” is now fixed by explicit “not measured” reasons. The ledger identity rule is now enforced at eligibility time with a final `Declined`, satisfying DEC-9.

**3. NEW FINDINGS FROM THIS REVIEW**  
- **Positive**: The new `PLAIN` mapping + `explain()` function makes every eligibility rejection legible to the model on retry; retry prompts are now concise and never leak sentence indices. `lineup_table` correctly star-marks only sentences that pass `states()` + `near()` within 30 s. Runtime estimate now includes the measured `TAIL_S` constant derived from the preview.  
- **Residual**:  
  - `Recorder.complete` still writes the file *after* the inner call but *before* the eligibility check in the outer `_ask` path. A `ModelError` after a successful model reply but before eligibility would leave a cache entry that later replays as “accepted” raw text (though eligibility would still reject it). Low probability but violates “cache only validated”.  
  - `to_passages` hard-codes `"score": None, "clip_score": None, "relevance": None`. Downstream `select_passages` / edl_rules that assumed numeric scores may need an explicit “selected_by”: “select_by_id” guard (already present but thin).  
  - `STORY_MAX_ROWS=160` and `LINEUP_MAX_ROWS=160` are generous; with gemma3:27b’s 16k context the safety margin is real, but the audit package should pin the exact token count of the worst-case prompt.  
  - No test exercises the `max_story_calls` budget path or a `ReplayMiss` in production wiring.

**4. REVISED SCORES**

| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| Q1 (fail-open)     | 88      | 97      | All previously identified holes closed; only remaining edge is Recorder + ModelError ordering (low impact). |
| Q2 (faithfulness)  | 71      | 94      | L-o targets, ModelChecks restoration, inner-sentence fix, timestamp handling, and gate wiring now match or exceed original strictness. |
| Q3 (verbatim)      | 95      | 98      | No model text reaches claim/segments/ledger; only forensic `attempts[].raw`. |
| Q4 (wiring)        | 68      | 93      | Patch now preserves pool laziness, free screen, word pass, finally blocks, gates on every cluster, and HOLD(infra). Minor Recorder ordering nit remains. |
| Q5 (tests)         | 75      | 96      | Vacuous assertions removed; smoke test now exercises Recorder branch and real eligibility reasons. |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL** (must fix before ship)  
- None. All consensus blockers are resolved in the diff.

**P1 HIGH**  
- Recorder: move the cache write into the success path *after* eligibility (select_by_id.py:1598–1605). Add seed to the replay key is already done; the ordering is the last gap.  
- Add a production smoke test that forces a `ModelError` mid-run and asserts GPU0 is released and remaining pools are abandoned cleanly (tests/select_by_id/smoke_wiring_patch.py).  

**P2 MEDIUM**  
- Complete R2 (one home for law constants) and R5 (fold BIBLE_ADDITIONS into QWEN_CONTEXT_BIBLE.md).  
- Explicit test for `max_story_calls` budget and `ReplayMiss` offline path.  
- Downstream `select_passages.py` / edl_rules should treat `selected_by == "select_by_id"` as authoritative and skip legacy clip-scoring paths.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The single predicate `eligibility.eligible(Lineup)` that judges every rule on verbatim `Span.text` + strict id-only model contract eliminates the entire class of “model hallucinated claim text” failures that plagued the previous pipeline.

**7. PRODUCTION READY?**  
**Yes with conditions.**  
Conditions: (1) the P1 Recorder ordering fix lands, (2) the updated backtest offline_words change from R4 is merged, (3) at least one full production dry-run with the real gemma3:27b model is performed and its `select_by_id` record inspected for unexpected rejections, (4) downstream consumers of passages.json explicitly handle the new `"selected_by": "select_by_id"` and null scores. Once those four items are complete the feature is safer than the code it replaces.