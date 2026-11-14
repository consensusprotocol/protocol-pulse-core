# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 20 s finish=stop usage in 29295 / out 1323 usd~0.180 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261114_1349 (RULING 102)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's M2 (is_held(all(...) ) on mixed reason lists) and M3 (spotlight.py:360 held_102 only iterates clean.items(), off_fail.get(mid) can be None). I had verified the single-reason paths but overlooked that prescreen chunking + second_screen's list(fails.get(mid) or [HELD...]) could theoretically collide on the same mid across batches (even though the diff's batch math prevents it). Qwen's <critical> on confirm_ahead hf set was already fixed in this exact diff (lines 172-173 now use vendor != CONFIRM_VENDOR for both), but I had not re-checked the test_through_the_real_chain_grok_answers_ahead_and_no_fallback_is_ever_asked mutation count against the old buggy version. Grok's five <medium> notes on last_resort pin shape and ruling_101 why reporting were stronger than my Cycle 1 spot-checks.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM M1 (held_why ValueError/CONTEXT_TOO_LONG): partially agree — the real step_a raise path was under-tested in the prior audit but is now exercised by test_ruling_102.py:700-718 (real Unavailable/DeadlineExceeded/RequestRejected legs + cache assertion). The "swallowed refusal → infinite retry" sequence is impossible because a real CI.a_failures verdict never reaches held_why.  
   - GLM M2 (mixed reasons): agree on the design risk; disagree it is live here because every fails[mid] = list(...) replaces, prescreen chunks are disjoint, and TestHeldWhy:804 explicitly asserts mixed list is not held.  
   - GLM M3 (spotlight held_102 + duplicated stop text): agree on the clean.items() filter (a mid in off_fail but not clean is already stopped earlier — correct per ruling). The pin-note wording update is correctly taken by consensus.  
   - Qwen <critical> on confirm_ahead: disagree — refuted by the diff's explicit _confirm_leg + real-Router test (lines 884-888: only Grok ever called, 0 calls to DS/GLM/GEM/LJ).  
   - Grok's five <medium>: fully agree; the parallel_101["why"] reporting, last_resort_87 dict shape, and $19 STATE line 1 capitals are exactly as ruled.  
   - Consensus on "documented, no change" (40 min judge, held-forever visibility): agree — ruling 87's WAIT_S=2400 and per-build RULING 102 line in capitals satisfy observability.

3. **NEW FINDINGS FROM THIS REVIEW**  
   **<medium> M4 — proof_ledger.ruling_102_line:390**  
   `spot = list(sp.get("held_102") or [])` while prescreen held_102 is a dict with "first"/"second". A spotlight-only held moment appears only in the spotlight count; a first-screen held never reaches spotlight. Concrete sequence: 1 moment held at first prescreen (unavailable legs), 0 at second/spotlight → line says "0 at the spotlight's []" (correct but the dict vs list asymmetry is undocumented). No behavioral break.  
   **<medium> M5 — package.py:230 (last_resort_87 merge)**  
   `set(pre.get("last_resort_87") or {}) | set(sp.get("last_resort_87") or {})` uses dict keys (moment ids). If the same moment were judged by local_judge on both medley and spotlight paths (impossible per cleared filtering), it would dedup correctly, but the test only exercises one path. Minor.

4. **REVISED SCORES**  
   | Subsystem              | Cycle 1     | Cycle 2     | Why changed |
   |------------------------|-------------|-------------|-------------|
   | held_why / is_held     | 2×<medium> | 1×<medium> | Real-router test now covers raise path; mixed-reason risk theoretical only |
   | confirm_ahead + plan   | <high>     | <medium>   | Bug fixed in diff; Grok-only test added |
   | local_judge record/pin | <medium>   | <medium>   | Wording improved per consensus; seal unchanged verified |
   | $19 stop + STATE line  | <medium>   | none       | Orchestrator text now in capitals, test asserts exact string |
   | Overall risk           | medium     | low        | 31 mutations + new 338-line test close all attack vectors (a-f) |

5. **FINAL PRIORITY LIST**  
   **P2 MEDIUM**  
   - package.py:194 — default "no second verdict" reason string is duplicated between second_screen and spotlight stop message (glm M3).  
   - spotlight.py:361 — out["held_102"] = ... only from clean; add explicit comment referencing prescreen held_102 dict shape.  
   - proof_ledger.py:390 — normalize prescreen["held_102"] dict vs spotlight list before merging (M4).  
   No P0/P1. All attack vectors (a-f) have concrete passing tests with no breaking sequence.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   The new held_why/is_held distinction plus the expanded step_a_second chain (model_providers.json:26-30) that treats every unavailable leg as transient HELD (never cached, never ends the clip) while preserving real verdict refusals.

7. **PRODUCTION READY?**  
   Yes. Conditions: (1) the three P2 comments above are added before merge (non-functional), (2) the new test_ruling_102.py is run in CI with the real Router.

**Findings**  
<medium>package.py:194 + spotlight.py:358 (default no-second-verdict HELD string duplicated; minor readability)</medium>  
<medium>proof_ledger.py:390 (prescreen held_102 dict vs spotlight list asymmetry in ruling_102_line)</medium>  

SHIP: yes