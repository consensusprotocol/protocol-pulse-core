# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 6910 / out 852 usd_reported=0.021523 usd~0.056 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1700 (RULING 117 join moments)**

**Summary**  
The diff extracts the candidate-moment selection for the join table into `join_moments()`, replaces the previous inline list-building logic in `build()`, and adds two targeted tests. The new logic implements the exact ordering and filtering described in the ruling and the 16:54 replay analysis: hook first, writer's viable moments, then cleared-pool moments preferring fresh channels before rank-order repeats, while excluding any moment that `lineup_ok` could never accept beside the hook (same video, not clip-eligible, doomed). The join table, `join_table()` question, cache, search, verdicts, and all downstream logic are untouched. All existing tests (including the 40-suite regression), mutation families (K1-K9, J1-J14), and the v2f reference continue to pass.

**Compliance with Governing Laws**  
- **SENTENCE LAW, ONSET/TAIL, L-b EDGE WORDS WHOLE, L-c DISSENT IS RIGHT, L-e PUNCTUATED BEFORE READ, L-g WRITTEN FORMS, L-h TEXT READ AS SPOKEN, L-k ONE CANONICAL FORM**: No transcript, punctuation, boundary, fade, or word-level logic touched. Compliant.  
- **SELECTION LOCK, SNAP LIMIT, NEIGHBOUR**: Selection locks and cut points are set upstream; this stage only chooses which already-locked moments may participate in a coherence search. No recomputation of first/last words. Compliant.  
- **L-f CHANNELS FIRST / L-i THE CLAIM IS THE EVENT**: This change is downstream of cluster selection. The channel-first ordering inside the join candidate list is orthogonal and does not alter cluster formation or claim derivation. Compliant.  
- **CREDITS, L-a SIGN-OFF NAMES ALL, L-d PROTECTED PREVIEW, L-j RELEASE IS AUTHORISED ON THESE BYTES, LAW 22 (v2f byte-identical)**: No renderer, credit card, voice-over, preview reference, attestation, or delivery path modified. The protected 2026-11-11 preview and v2f continue to render identically. Compliant.  
- **M1 (Smallest diff; no new renderer, compositor or selector), M12 FAIL CLOSED, LAW 20 / M2**: The added function is a pure extraction of the previously inline (and buggy) candidate list. It does not add a new selection algorithm, only makes the existing rule explicit, testable, and correct. No gate was relaxed; impossible moments are now simply omitted from the search space so that viable line-ups can still be found within the JOIN_MOMENTS_MAX cap. The change is the minimal surgical fix required to make the ruling work. Compliant.  
- **L-l A MODEL REPLY COUNTS ONLY WHOLE**: No model calls or JSON validation paths touched. Compliant.

**Findings**  
[P3] Docstring for `join_moments` repeats the full ruling text; a reference to the canonical ruling document plus a one-sentence summary would be cleaner.  
[P2] `can()` predicate duplicates the clip-eligibility and video-id checks already present in `lineup_ok`. While currently identical, a future change to one without the other would be a maintenance hazard. Consider a shared helper (`can_stand_beside_hook(m, hook_video, doomed)`) used by both.  
[P3] The nested `bool(((m.get("eligibility") or {}).get("clip") or {}).get("ok"))` is defensively correct but visually noisy; a small helper `is_clip_eligible(m)` would improve readability without changing semantics.  
[P3] Test `test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first` has a very long name; consider splitting into two shorter tests (one for exclusion, one for channel-first ordering).  

All tests, mutation coverage, and regression gates pass. The fix correctly resolves the zero-line-up problem without loosening any join law or violating any governing constraint.

**P1_OR_WORSE: 0**