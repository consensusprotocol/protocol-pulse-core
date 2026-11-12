# claude-fable-5-2 (effort high) 284 s stop_reason=end_turn usage=in 73056 / out 27789

# pp-selectid: Cycle 2 review (chunk B: tests, proof, docs)

**Not ready to wire R1 into production; the two new modules can merge unwired.** Three limits on this review:

- **My Cycle 1 output is missing.** The prompt has only a placeholder where it should be, so I cannot compare against it or quote my Cycle 1 scores.
- **I see only chunk B.** The fixed `eligibility.py`, `select_by_id.py` and the R1 patch are not in it, so I judge those fixes through their tests.
- **I ran nothing.** Every finding is from reading the code.

## 1. What they caught that I missed

I cannot answer this honestly without my Cycle 1 text. The unanimous findings (U1–U4) and both majority findings (M1, M2) are real defects, and I take them as the baseline.

## 2. Agree / disagree

| Finding | Position | Why |
|---|---|---|
| U1: inner sentence skips D4 | Agree, but the fix is untested and can be bypassed | No must-fail test for `[*, unrelated, *]` (N4), and the model can mark the sentence as a story statement instead (N1). |
| U2: missing time read as 0 | Agree, fixed | `test_eligibility.py` 514-531 isolates both the hook-lead and D4 (b) cases. |
| U3: gates, `why`, infrastructure HOLD | Agree, only partly tested | The smoke test has one cluster, so "a gate on every screened cluster" and the HOLD decision are never exercised. |
| U4: vacuous tests | Agree, mostly fixed | Each bad reply now asserts its own reason (`test_select_by_id.py` 1891-1906). |
| M1: R1 drops model gates | Agree on `verify_support` and `verify_reaction`; disagree with "floors superseded, nothing to rank" | L-o says targets rank. With nothing ranking, the floors are simply gone (N2). |
| M2: transport errors, `finally` | Agree | Only `URLError` and the GPU0 guard are tested (2007-2022). The smoke test never asserts `stop()` or `close()` ran. |
| Fable 2: Recorder caches before validation | Agree, fix looks partial | The seed is in the key and empty replies are skipped (2031-2039). A non-empty invalid reply is still served, as far as the tests show. |
| Fable 4: ledger rule routed around by retry | Agree, fixed for the retry | 1934-1943. A first reply naming neighbouring sentences of the delivered event still passes; that may match today's behaviour. |
| Sonnet 3: `file_head` default | Agree, fixed in tests | Callers now assert `file_head` and `vod` explicitly (line 446 tests a window's first words). |
| Opus: `registry` / `os` undefined in the patch | Resolved if the smoke test passes | It runs the patched `select_story` end to end; I have no output to confirm. |

## 3. New findings

**N1. HIGH: marking a sentence as a story statement bypasses D4 and the coverage check.**
- `verify_reaction` is asked only for non-statement sentences ("never the all-statement clip", 1978-1998).
- `verify_support` runs on the claim only, per the consensus M1 text.
- The must-pass test depends on this: Natalie's two follow-on sentences pass only because the story call marks them as statements (1750-1754; NOTE-PS6, 235-242).
- So an off-topic sentence the model lists in `story` goes on screen with no D4 (a), (b) or (c) check, provided the clip as a whole names Bitcoin.
- The second channel's membership is also never checked against the claim. Today each video is checked against the event.
- Fix: run today's `verify_support` on every story member, with the claim sentence as the event.

**N2. HIGH: L-o is implemented as "never reject", but nothing ranks.**
- `targets_missed` is only a fact. A 2.4 s hook passes (472-474) and a 35 s "sentence" only "ranks" (685-686).
- The design doc cites `edl_rules` R5 (8-25 s) and `stand_alone` at validate (lines 127, 129) and says no existing file is edited.
- If those are unchanged, selection can now pick a line-up that validate must hold. That is the disagreement class this step was meant to remove. I cannot see those files.
- A clip opening on a conjunction needs a scorer verdict at validate; Cycle 1 reviewers quoted `to_passages` writing `clip_score: None`.

**N3. HIGH: the approved preview fails the new hard rule.**
- The approved trio estimates ~54.4 s and is rejected (1770-1771).
- The test and the smoke test pass only by adding a fourth segment that was never approved (1773, 1288).
- Either the estimate is wrong or L-o fails the reference; PBX needs to decide which.
- The estimate's overhead is not pinned to the renderer (`TestPinned`, 322-348). Only the lower bound is tested (562-566).

**N4. MEDIUM: no regression test for U1 or the cap.**
- `test_anchor_and_adjacency` (488-500) uses a single statement with trailing sentences only.
- The `Span(0, 3)` case cannot tell D4 (a) from the two-per-side cap.

**N5. MEDIUM: Recorder against L-l.**
- Only the empty reply is shown as not served again (2037-2039).
- A truncated or prose reply is recorded per seed, so a rerun in the same hour would replay all three failures without calling the model. This needs a commit-after-`check()` hook; I cannot verify whether chunk A has one.

**N6. MEDIUM: the proof's "second angle" is the same angle.**
- `resolve()` re-reads the same record through the same functions (863-881).
- The re-check is the same predicate (906-907).
- The word-record hash covers `segments`, not the `words` actually used (803).
- The context has no ledger (922), so `already_delivered` never fires.
- The generator stand-ins use JSON mode or are another model (1471, 1520), so gemma3:27b's strict-JSON rejection rate is unmeasured.
- The consensus header says no XAI key is available, yet the judge needs `XAI_API_KEY_MEDLEY` (1612). If it is absent, every check is a model error and no line-up can be accepted.
- I see no evidence the proof was regenerated after L-o and ModelChecks.

**N7. MEDIUM: the design doc is stale.**
- T8, T10 and L1 (lines 127, 129, 150) predate L-o.
- Section 5 still says checks "may" run (162-166).
- Line 71 gives the Recorder key without the seed.
- Section 6 is a placeholder (169-172).
- The `standins.py` docstring names Gemini as the substitute (1373-1375).

**N8. LOW: `proof_table.py` bugs.**
- It prints `price_assumption_usd_per_1m` (1107), which `_account` never writes (1436-1448), so the table says "None".
- It crashes without `SPEND.json` (1087).
- Its docstring and `OUT` name different files (1051, 1061).

**N9. LOW: inconsistency and coverage gaps.**
- A claim opening on "But" is rejected (588-595), while a hook or clip conjunction is only a target (458-462, 539).
- Missing tests:
  - registry entry with `enabled` absent;
  - the 48 h and 72 h boundaries;
  - a range with `last < first`;
  - the runtime upper bound;
  - `ReplayMiss` and `SpendLimit` passing through `_ask`;
  - a valid reply with a trailing newline.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| Reply contract (ids only, verbatim) | n/a | 88 | No fail-open path found by anyone; tests are now reason-specific. |
| Eligibility predicate | n/a | 72 | U1 and U2 fixed; L-o leaves length unranked; U1 fix untested. |
| Model checks | n/a | 68 | Claim and reaction checks restored; story members unchecked (N1). |
| R1 wiring | n/a | 62 | Likely disagreement with validate (N2); gates and `finally` untested. |
| Tests | n/a | 74 | Stronger, with the gaps in N4 and N9. |
| Proof and docs | n/a | 60 | Not independent, not on the production model, stale doc. |
| **Overall** | n/a | **71** | Cycle 1 column blank because my Cycle 1 output was not supplied. |

## 5. Final priority list

Line numbers are from the chunk B diff. For files outside it I can cite only the function.

**P0:** none provable from this chunk.

**P1**
1. `select_by_id.ModelChecks`: check every story member against the claim (N1). Add a must-fail test beside `test_select_by_id.py` 1945-1998.
2. L-o: make targets rank (for example, across attempts or groups). Also confirm `edl_rules` R5 and `stand_alone.check_edl` accept what selection now accepts, with a test that runs an L-o line-up through validate (N2; `test_eligibility.py` 472-474).
3. Get a PBX ruling on the approved preview against the 60-70 s rule, and pin the runtime estimate to the renderer (N3; 322-348, 562-566, 1770-1773, 1288).
4. Run one shadow selection on gemma3:27b under the final contract before R1 merges (N6).

**P2**
5. Add the U1 must-fail test and a cap test (488-500).
6. Recorder: commit only after `check()` accepts or declines, and test that an invalid non-empty reply is not served (2024-2039).
7. Smoke test: use two clusters, assert the "not evaluated" gate, and assert `stop()` and `close()` were called (1195, 1221, 1323).
8. Proof: give it a real second angle, hash the words, pass the ledger, and regenerate it (863-881, 803, 922).
9. Update the design doc and fix `proof_table.py` (N7, N8).
10. Decide the claim-opener rule under L-o and add the missing tests in N9.

## 6. The single highest-leverage change

Check every story member against the claim sentence with today's `verify_support`, so that marking a sentence as a statement cannot stand in for both the two-channel coverage check and D4.

## 7. Production ready?

**No** for wiring R1. **Yes with conditions** for merging `eligibility.py` and `select_by_id.py` unwired, since they are inert until R1.

Conditions for R1:
- P1 items 1-4 are done.
- The proof is regenerated under L-o and ModelChecks.
- The smoke test output is attached.
- The chunk A fixes for U1, U2 and M2 are confirmed by someone who can see that chunk.