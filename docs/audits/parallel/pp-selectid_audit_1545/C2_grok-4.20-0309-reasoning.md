# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 53 s finish=stop usage in 15515 / out 1342 usd~0.111 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1545 (speakers.py after C1 fixes)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   I missed the unhandled `KeyError`/`TypeError` on missing `"start"` or non-numeric timestamps inside `captions()` (Grok P1) that could abort the entire `attribute_package` before any fallback; the implicit coupling between `check_turn`'s `_norm` lookup and `decide()`'s `others` list that becomes fragile if helpers ever diverge (GLM P1-2); and that the original backchannel merge could swallow a short floor-taking utterance containing a name (Qwen P1-1 + GLM P1-1). The C1 changes (BACKCHANNEL set, guarded parsing, word-boundary slice, broad `except` in `attribute_package`) directly close those gaps. I also under-weighted how the `spans` construction (lines 147, 154) *excludes* backchannel segments from `turn["text"]`, which cleanly refutes Qwen P1-3.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM P1-1 / Qwen P1-1 (backchannel chaining): fully agree pre-fix; partially agree post-fix — the new `backchannel()` predicate (every token must be in the frozen set) plus the added test `test_only_a_backchannel_continues_a_turn_and_a_bad_record_is_skipped` eliminates the concrete "Mark, why?" floor-taking scenario. The while-loop can still chain multiple *valid* backchannels, but that matches K1 and the orchestrator's accepted reading of the 945.28 clip.  
   - Grok P1/P2 (exception paths, slice): agree — both are now guarded; the `TURN_MAX_CHARS` cut is fixed to word boundaries.  
   - GLM P1-3 / Qwen P2-2 (first-store-wins, name-word length filters): agree these remain (see new P2 below); the "first store with any marker" policy is still fail-closed but not optimal.  
   - Qwen P1-3 (quote from backchannel): disagree — `idx` only includes main `spans`, `turn["text"]` never contains skipped interjections, and `check_turn` requires `_within(quote, turn_text)`. The test explicitly asserts `"Tell that to his wife" not in t["text"]`.  
   - All models on lower-third handling: agree with the post-C1 implementation — it never makes a decision alone (K4), only confirms or vetoes, exactly as `decide()` encodes.

3. **NEW FINDINGS FROM THIS REVIEW**  
   None rise to P1. The combined Cycle-1 feedback plus the diff revealed only minor residual inconsistencies and policy gaps that the C1 changes did not touch.

4. **REVISED SCORES**  
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | captions() parsing & guards | P1     | P2     | Broad `try`/`except` + NaN/out-of-order check now skips bad stores without crashing package (Grok + Qwen points addressed). |
   | backchannel merge logic | P1     | P2     | `BACKCHANNEL` set + predicate prevents non-backchannel floor-taking; test added. |
   | exception paths & fallback | P1   | None   | `attribute_package` catch-all, inner `try` in `attribute`, recorded `turn["why"]` — no longer aborts. |
   | turn cut & prompt construction | P2 | P2     | Word-boundary fix applied; prompt now correctly templates the sanitized turn. |
   | decide / check_turn / lower-third | P2 | P2 | Conflict veto, exactly-two-people rule, and "one more piece" semantics verified against K2-K4; minor filter-length inconsistency remains. |

5. **FINAL PRIORITY LIST**  
   **P0 CRITICAL:** None. No path verified in the diff names a speaker on less than turn structure + validated address/self-intro. Conflict forces "unknown"; backchannels are excluded from `turn["text"]`; every quote is checked verbatim.  
   **P1 HIGH:** None. All Cycle-1 P1s are resolved or downgraded.  
   **P2 MEDIUM:**  
   - `pipeline/speakers.py:86` (`for st in stores or (STORE, INGEST_STORE)`): first store with *any* marker wins; a partial main-tree copy containing one stray `>>` but missing the clip's later markers could be chosen over a complete pp-ingest copy (still GLM P1-3).  
   - `pipeline/speakers.py:176` vs `203`: name-word length filters differ (`len(w)>1` in `check_turn`, `>2` for lower-third); a 2-letter name component would be accepted in one path but ignored in the other.  
   - `pipeline/speakers.py:157`: `text.rfind(" ", a0, a1) if ... > a0 else a1` edge case (no whitespace) is untested beyond the long-turn fixture; the fallback could theoretically produce a cut that starts after the clip.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   The new `backchannel()` helper (lines 132-134) that demands *every* token be in the explicit BACKCHANNEL set, combined with excluding those segments from `turn["text"]`, prevents the exact wrong-speaker-name contamination the audit was created to stop.

7. **PRODUCTION READY?**  
   Yes with conditions: (a) add one test asserting that a partial caption store with an early marker but no marker before the clip is rejected in favor of a later complete store (or explicitly document why "first with any marker" is acceptable); (b) harmonize the >1 / >2 name-word filters or document the rationale; (c) confirm in a live pin that `turn["source"]["sha256"]` and `backchannels` are persisted for downstream auditability. With those three items, the implementation faithfully implements Ruling 69 + 70, K1-K4, and the "wrong name worse than unknown" standard.

**SHIP: yes with conditions** (the three items above).