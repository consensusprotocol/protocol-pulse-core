# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 62 s finish=stop usage in 7842 / out 1190 usd~0.069 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid-0500 (Ruling 37)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok caught the narrow test coverage of eligibility for real middle/last-clip paths (only a synthetic ctx("clip") is exercised). Qwen caught the comment timestamp mismatch, the KeyError risk on `segs[1]["moment_id"]` if the dict shape ever changes, and that the diff alone cannot prove loop termination or that `ly_shape` is always invoked post-reline. GLM caught the predicate/render text-identity risk and the `if/elif` shadowing possibility in `ly_shape`. I had focused only on the re-line/drop mechanics and eligibility guard in Cycle 1; I missed the test-gap and KeyError surface.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 (ly_shape shadowing) & P1-4 (re-line termination): Partially agree — the `elif` placement and unseen loop were legitimate diff-only concerns; consensus verification (bounded `while n_lineup < lineups`, `ly_shape` required in every sealed inventory) resolves them.  
- GLM P1-2 (`segs[1]` on 1-segment): Agree — consensus proves `lineup_for` always yields hook + 2–4 clips (≥3 segments), so unreachable.  
- GLM P1-3 (predicate vs render R1 text): Agree — verified verbatim `approved_text` flow and integrator confirmation close the gap.  
- Qwen P1-1 (termination not shown): Disagree on P1 severity; the added test rig and consensus loop bound make it P2 at worst.  
- Qwen P1-2 (only `js[0]` checked): Agree — intentional and correct; Ruling 37 + render R1 only care about the immediate post-hook join; later clip-clip joins remain bridgeable.  
- Grok P2 items (position assumptions, test coverage): Fully agree; both are real but non-blocking given the new integration tests and production join-label assertion.  
- All three models on eligibility change and “hook-only” enforcement: Complete agreement — the `and role != "hook"` guard plus explicit clip test satisfy the ruling without relaxing any standing law.

3. **NEW FINDINGS FROM THIS REVIEW**  
- `package.py:37` new `elif` now sits *before* the bridged-vs-flagged check; a question-hook + flagged first join therefore emits the specific “ruling 37” message instead of a generic bridge mismatch. This is an improvement in diagnostics.  
- The C2 test `test_ly_shape_refuses_a_question_hook_whose_first_join_was_flagged` supplies the must-pass case (question hook + empty flagged list) that GLM flagged as missing in C1.  
- No evidence of canonisation or normalisation between pin text and EDL text; `question_hook` and render R1 now read identical strings.  
- `dropped.add(...)` and `dropped |= weak` share the same set; combined with the verified loop bound, infinite re-line is impossible.  
- No other modules, gates, or standing laws (L-m, L-j, L-y, M12, etc.) are touched.

4. **REVISED SCORES**

| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| eligibility.py     | P2      | P2      | Test coverage gap noted by Grok but still sufficient for the narrow rule change. |
| package.py:build   | P1      | P2      | Consensus + new Rig test prove termination, segment count, and verbatim text; segs[1] safe. |
| package.py:ly_shape| P2      | P2      | `elif` ordering clarified; specific error message is a net positive. |
| tests              | P2      | P1      | Added must-pass case, production join-label assertion, and bridge-between-clips test close prior gaps. |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** none  
**P1 HIGH:** none  
**P2 MEDIUM:**  
- `pipeline/package.py:48` — `segs[1]["moment_id"]` KeyError surface if moment dict ever lacks the key (test fixture supplies it, but no explicit guard).  
- `tests/package/test_medley.py:120` — production join-label assertion is valuable but could be moved to a shared fixture rather than a test method.  
- `pipeline/eligibility.py:11` — comment cites exact ruling timestamp; the test file comment should match for audit traceability (minor).

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The paired re-line drop (`build:47-51`) + `ly_shape` refusal (`ly_shape:37-39`) together with the verbatim `question_hook` predicate ensure the pin stage can never seal a package whose first join is both questioned and flagged, exactly matching the render’s updated R1 without relaxing any other gate.

7. **PRODUCTION READY?**  
Yes with conditions: (a) full regression suite (including all non-medley EDL paths) must pass unchanged, (b) integrator must deploy the matching edl_rules R1 change in the same release window so that sealed clips-alone PASS packages are not later refused, (c) the two P2 items above should be addressed for robustness and traceability.

**P0: none**  
**P1: none**  
**P2: package.py:48 (KeyError risk on moment_id), test_medley.py:120 (assertion placement)**  

**SHIP: yes with conditions** (see #7 above)