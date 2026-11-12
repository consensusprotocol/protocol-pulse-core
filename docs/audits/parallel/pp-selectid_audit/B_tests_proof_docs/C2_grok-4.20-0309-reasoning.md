# grok-4.20-0309-reasoning (xAI, medley key) 51 s usage={'prompt_tokens': 48007, 'completion_tokens': 1497, 'total_tokens': 50661, 'prompt_tokens_details': {'text_tokens': 48007, 'audio_tokens': 0, 'image_tokens': 0, 'cached_tokens': 128}, 'completion_tokens_details': {'reasoning_tokens': 1157, 'audio_tokens': 0, 'accepted_prediction_tokens': 0, 'rejected_prediction_tokens': 0}, 'num_sources_used': 0, 'cost_in_usd_ticks': 665093500}

**CYCLE 2 REVIEW — pp-selectid (after consensus + L-o fixes)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I correctly flagged the strict JSON/id contract, the verbatim-only output path, and the Recorder caching-before-validation defect (my D2). I completely missed the `_anchor` core-range bug (sentences strictly between two `*` statements skipped D4(a)/(b)/cap — the unanimous U1). I also missed the timestamp-default-to-0 fail-open in hook_lead / adjacent_not_admissible / duration (unanimous U2), the lost ledger gates on unevaluated clusters and the empty `why` lookup (U3), and the vacuous test assertions plus the production branch never being exercised in the original test suite (U4). I under-weighted how badly the original R1 patch deleted the independent `verify_support` / `verify_reaction` gates without a replacement that still operated on verbatim text only. The three Claude reviews surfaced these with concrete scenarios (Yahoo middle sentence, missing `end` timestamps, Natalie Brunell clip) that my first pass did not exercise.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **Unanimous U1–U4**: Full agreement. The fixes in the supplied diff (inner-sentence loop in `_anchor`, `_time()` helper that treats missing timestamps as “not measured”, `Outcome.to_dict` carrying `why`, gate on every screened cluster, per-reason assertions, Recorder branch exercised by ScriptedLLM) are exactly right and close the holes I missed.  
- **Majority M1 (R1 dropping floors + verify_* gates)**: Agree with the disposition. Law L-o correctly reclassifies hook/clip duration windows, score floors and conjunction openers as ranking targets only; the hard rule is now total runtime 60–70 s. The added `ModelChecks` (today’s prompts/validators on verbatim claim and non-statement sentences) restores the lost judgements without reintroducing model-written text. The “inconclusive = model_error” path is the correct fail-closed behaviour.  
- **Majority M2 (OllamaModel exceptions / finally)**: Full agreement. The adapter now maps transport errors to `ModelError`, the GPU0 guard still propagates, and `L.stop()` / `E.close()` are in a `finally`. My Cycle 1 version only partially caught the escape; the Claudes’ concrete “Ollama timeout leaves GPU0 loaded” scenario was sharper.  
- **Sonnet’s Source.file_head default and R4 prerequisite**: Partial disagreement. The fixed code correctly defaults `file_head=False` and only asserts it for full-video store records. The backtest window case is now documented (E-FAIL-PS1) and excluded from on-screen roles. No blocker.  
- **All three on ledger “already_delivered” retry loophole**: Agree it is closed; the identity check now runs before the model is asked again and a delivered match is a final decline for that group.

No material disagreements remain after the fixes.

**3. NEW FINDINGS FROM THIS REVIEW**  
The combined Cycle 1 consensus + L-o + the supplied fixed diff (tests/eligibility/test_eligibility.py, proof_saved_runs.py, smoke_wiring_patch.py, standins.py, docs) is remarkably clean. Two minor new observations:  
(a) The `ModelChecks` wrapper correctly re-raises `LLMParseError` as `model_error` (line ~1978 in test_select_by_id), but the production `OllamaModel.complete` still catches only `ModelError` and `SpendLimit`. If `story_semantics.LocalLLM` can raise other exceptions besides those wrapped by `ModelChecks`, they would still escape. The test `test_the_ollama_adapter_fails_closed_on_transport…` only exercises `URLError` and the GPU0 guard.  
(b) `proof_saved_runs.py:948` uses a CPU-only `word_source` that prefers punctuated records; the comment acknowledges that a CPU replay may legitimately return None for videos without sentence-ready records. The production wiring still runs the GPU0 word pass, so the live path is unaffected. This is disclosed but worth PBX visibility.  
No new fail-open paths, no model text leakage, and the L-o runtime estimate is correctly the sole hard reject (tests pass).

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Fail-open safety       | 82      | 96      | U1/U2/U3 fixes + strict decline on empty ranges + ModelError path now exhaustive |
| Faithfulness to laws   | 68      | 94      | L-o targets vs hard runtime clarified; ModelChecks restore verify_support/reaction on verbatim text; all pinned constants match |
| Verbatim guarantee     | 90      | 97      | Confirmed in proof runs and smoke test; claim and every segment are `Span.text` only |
| Wiring / R1 patch      | 55      | 91      | Gates restored on every cluster, ledger why carried, INFRA_HOLD kept, finally blocks added |
| Tests & proof          | 72      | 95      | Vacuous assertions replaced by per-reason checks; smoke now exercises Recorder + ModelChecks + fabricated-id HOLD; proof table covers all saved universes |
| **Overall**            | **73**  | **95**  | Consensus defects implemented; new L-o integrated without reintroducing text laundering |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL** — none.  
**P1 HIGH**  
- (select_by_id.py:1694) Ensure `OllamaModel.complete` maps every exception that `LocalLLM._post` or the `ModelChecks` wrapper can raise to `ModelError` (or let the GPU0 guard propagate). Current test covers only two cases.  
**P2 MEDIUM**  
- (docs/audits/parallel/pp-selectid_BIBLE_ADDITIONS.md:228) NOTE-PS5 whole-record L-e behaviour is kept but still removes clean clips; PBX should confirm this is acceptable post-R1.  
- (proof_saved_runs.py:948) Document the CPU-replay “no word record” case in the integrator README so operators know why a replay may show “not asked (no word record)”.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The single eligibility predicate (`eligible(item, ctx)`) combined with the id-only contract and `ModelChecks` on verbatim text eliminates the entire class of E-FAIL-036/037/038 rewrite-laundering bugs while restoring every substantive law that mattered.

**7. PRODUCTION READY?**  
**Yes with two conditions**: (1) the smoke_wiring_patch.py must pass against the exact integrator commit that will receive the patch, and (2) at least one live run (or the full proof suite) must exercise the `ModelChecks` verify_support / verify_reaction paths and confirm `eligibility_recheck=True` and `ids_resolve=True` on the accepted line-up. With those satisfied, ship.