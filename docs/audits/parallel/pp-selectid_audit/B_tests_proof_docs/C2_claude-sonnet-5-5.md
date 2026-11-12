# claude-sonnet-5-5 (effort high) 148 s stop_reason=end_turn usage=in 73056 / out 19308

# Cycle 2 review: pp-selectid, chunk B (tests, proof harness, stand-ins, smoke test, docs)

**Missing Cycle 1 text.** The "YOUR CYCLE 1 OUTPUT" slot only says "see below", and no text of mine is included. I won't invent one, so I can't say which of my own points I missed, and the "Cycle 1" column in section 4 is "n/a". I judge the three other reviews and the consensus against what is in this chunk. `eligibility.py`, `select_by_id.py` and the R1 patch are not in this chunk. Anything about them is inferred from the tests and docs and marked as such. I ran nothing.

## 1. What the others caught, and whether it holds in this chunk

| Finding | Verdict | Evidence in chunk B |
|---|---|---|
| U1: a non-statement sentence between two statements skips D4 | Agree. It was a real hole. The fix is claimed, but no regression test exists (new finding N1). | `test_anchor_and_adjacency` (l.488-500) has no `[*, unrelated, *]` case. The only sandwich is the approved Yahoo middle sentence (l.1754-1760), which must pass. |
| U2: a missing time was read as 0 | Agree. It is covered by `test_a_missing_word_time_is_no_measurement` (l.514-531). Coverage is two cases only. | The `start` and `end` of the span's own boundary words, the `prev` direction, and a missing core time are not tested. |
| Fable 2: Recorder caches before validation and ignores the seed | Partially agree. | The seed is now part of the key (l.2031) and an empty reply is not cached (l.2037-2039). A non-empty reply that fails validation is still cached and served on rerun at the same seed, and no test covers it. At a fixed seed the model gives the same reply anyway, so the impact is low. |
| Opus 3, Sonnet 4: transport errors escape `_ask` | Agree. Fixed, but the test covers one exception type. | `test_the_ollama_adapter…` (l.2007-2022) tests only `URLError`, plus a `RuntimeError` for the GPU0 guard. |
| Fable 4: ledger identity is per sentence and the retry loop can route around it | Partially fixed. | Delivered is now final for the group (l.1934-1943). Identity is still `(video_id, ≥5 shared tokens)`. A later video of the same development passes DEC-9. |
| M1: R1 dropped the clip floors, `verify_support` and `verify_reaction` | Agree with the disposition. Floors are superseded by L-o. `verify_reaction` is restored. `verify_support` is restored only for the claim (N2). | `test_model_checks…` (l.1945-1998). |
| Sonnet 3: `file_head` defaults to True | Mostly addressed. The helpers pass `file_head` and `vod` explicitly (l.295-299, 631, 967). | I can't confirm the default in `eligibility.py`. |

## 2. Disagreements and nuances

- **"Floors rank, never reject" (L-o).** I accept that this settles Fable 1 and Opus 2 on the score floors. But `facts["targets_missed"]` has no consumer. The design doc says there is a single model-chosen line-up, so nothing ranks. The targets are only recorded.
- **The runtime window is the only hard length rule.** The approved PBX trio is now rejected: it estimates ~54.4 s, below 60 s (l.1770-1771). The must-pass test therefore accepts a modified four-segment line-up with an extra Yahoo clip. The test name and the docs still say "the approved preview". That is defensible under L-o, but the proof no longer shows that the approved line-up is reachable.

## 3. New findings

**N1. P1: no negative test for the sandwich fix (U1).**
- `test_eligibility.py` l.488-500 and `test_select_by_id.py` l.1748-1784 only test the positive case.
- Add a `[statement, unrelated non-interjection, statement]` span that must fail `adjacent_not_admissible`.
- Also add a case where the middle sentence is more than 8 s from both neighbours.
- Also add a case where the middle sentence is an interjection, which must be transparent.

**N2. P1: `verify_support` runs only on the claim, so the same-event check across channels is gone.**
- Today's code checks each channel's quote against the event (design doc §5, l.162).
- The new test and doc (l.1945-1950, 162) run it on the claim sentence only. The claim is checked against itself, so only `presented_as` carries information.
- Whether the other members are the same development is left to the story call. The doc admits this as a limit (l.176-178).
- The infrastructure exists. Run `verify_support(event=claim, quote=member)` for every non-claim member. A negative verdict should reject and re-ask.
- This is the same L-f law that M1 relied on.
- The production module is not visible, so this is inferred from the doc and test.

**N3. P1: the claim stand-alone rule contradicts L-o as written.**
- `test_the_claim_must_stand_on_its_own` (l.588-595) rejects a claim opening "But that said, …" with `claim_not_standalone`.
- L-o says conjunction openers are targets and never reject. The hook and clip tests agree: "So …" is only a target miss (l.455-462).
- Either the claim keeps a stricter opener law and PBX must confirm that, or the rule is being applied wrongly.
- Design doc G5 (l.143) and rows T8 and T10 (l.127, 129) still describe the pre-L-o behaviour.

**N4. P2: ledger identity misses the same development from a different video.**
- DEC-9 says a delivered event is never selected again. Identity is the same video plus a 5-token run.
- Add it to §7 (known limits), or compare on claim similarity across videos.

**N5. P2: the proof's "independent" recheck is the same predicate.**
- `finish` (l.906-907) calls `E.eligible` again with a fresh `Context` that has no ledger.
- It cannot catch `already_delivered`, and it is not an independent second angle. `resolve` is the genuinely independent check.

**N6. P2: spend accounting can undercount.**
- `_Spend.account` is only called after a successful reply (l.1428-1453).
- Retried 5xx calls, the Anthropic client's `max_retries=4`, and refusals on some paths can bill without being recorded.
- `guard()` reads the file without taking the lock (l.1424), so parallel processes can overshoot.
- The comment "a guard may only overcount" (l.1636) is not true on these paths.

**N7. P2: test brittleness and vacuity.**
- `starts[1] == "HC"` (l.2065) hard-codes row id 1. This is the id-hard-coding that U4 removed elsewhere.
- `test_the_prompt_neutralises_transcript_markup` (l.2068-2073) only checks that the raw string `"</sentences> today"` is absent. Any alteration passes.
- The `Replay` test (l.2033-2036) does not check that an unrecorded seed raises `ReplayMiss`.
- Tests depend on the live `channels.json` state, for example `saylor["enabled"] is False` (l.396). A registry edit fails them for non-code reasons.
- The `duration` assertions look contradictory. `test_duration_count_subject_lead` says a short hook is not a `duration` reason, while `test_every_reason_is_reported` expects `duration` on a segment source (l.537). That is consistent because `duration` is now only an unmeasured-time failure, but it needs a comment.

**N8. P2: proof harness portability and time zone.**
- `MAIN = "/home/ultron/protocol_pulse"` is hard-coded (l.740).
- `datetime.fromisoformat(saved["started"]).astimezone(timezone.utc)` (l.921) silently uses the local zone if `started` is naive. That would shift every freshness measurement. Assert `tzinfo`.
- In replay mode `--standin auto` picks the Anthropic name if the OpenAI probe is skipped. Recordings made with another generator raise `ReplayMiss` unless `--generator-name` is given.

**N9. P2: stale or inconsistent docs.**
- Design doc §6 is an empty placeholder (l.169-172).
- It cites `pp-selectid_PROOF.md`, but `proof_table.py` writes `pp-selectid_PROOF_TABLE.md` (l.1061).
- §2 still says the Recorder key is `sha256(model, prompt, max_tokens)` (l.69). The seed is now in the key.
- §4 has no row for the `runtime` reason or for L-o.

**N10. P2, unverified (module not shown): `states()` is a loose match.**
- A sentence counts as a story statement by a 5-token run, not by id (l.132, 511).
- A later sentence in the same video that repeats such a run would become "core" without the model choosing it. In `_anchor` that would exempt it from D4.
- Please confirm that a statement match is limited to the ids the model chose.

**Smoke test.**
- The scripted checker always affirms (l.1208-1219). The smoke therefore exercises only the positive ModelChecks path, which is acceptable because the negative path is covered by unit tests.
- The `sys.path` and `__file__` assertion (l.1255) means it must run as a standalone process, never inside pytest.

## 4. Scores

I did not receive my Cycle 1 scores, so that column is n/a. The scores below are for this chunk only.

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| Tests: eligibility | n/a | 78 | Reason-specific must-fail cases and parity and pinning are strong. No negative sandwich test, and the missing-time coverage is thin. |
| Tests: select_by_id | n/a | 74 | Each bad reply asserts its own reason. Adapter, Recorder and replay tests are thin. Some brittle ids. |
| Proof harness and stand-ins | n/a | 70 | Well constructed and read-only. The recheck is not independent, spend accounting can undercount, and the time zone and paths are fragile. |
| Smoke / wiring | n/a | 80 | It applies the real patch and checks that a fabricated id holds the run. It affirms every check, so it is positive-path only. |
| Docs | n/a | 62 | Stale against L-o, the empty §6, and the broken file reference. |
| Overall (this chunk) | n/a | 73 | |

## 5. Priority list

**P0 (blocks merge): none inside this chunk.** The production modules were not visible to me. The consensus fixes for fail-open and verbatim text look consistent with the tests.

**P1 (before merge)**
1. Add the sandwich regression tests (`test_eligibility.py` after l.500).
2. Run `verify_support` for each non-claim story member with the claim as the event. Test it with a negative-verdict judge (N2; `test_select_by_id.py` l.1945-1998 and the module).
3. Resolve the claim-opener contradiction with L-o and fix G5 in the docs (l.143, 588-595; N3).
4. Cover more adapter failure types: `TimeoutError`, `ConnectionResetError`, bad JSON from the server, and a missing response key. The GPU0 `RuntimeError` must still propagate (l.2007-2022).

**P2**
5. Test that a non-empty rejected reply is not committed, or document that it is (l.2024-2039).
6. Make the proof recheck independent: include the ledger, or label it as the same predicate (l.906).
7. Fix spend accounting: lock `guard()`, and account for retried calls or relabel the number as a lower bound (l.1411-1453).
8. Assert `tzinfo` in `run_saved`, and remove the absolute `MAIN` path (l.740, 921).
9. Update the docs: fill §6, correct the file name, and revise §2, T8, T10 and the L rows for L-o and `runtime`. Add the delivered-from-another-video limit to §7.
10. Remove the hard-coded row id and make the neutralisation test assert escape behaviour (l.2065, 2073).
11. Confirm that `states()` is bounded by the model's ids (N10).

## 6. Highest-leverage change

Add the missing negative regression tests and the per-member `verify_support` check, so the sandwich fix and the "same development" claim are enforced by tests and checks rather than by trust.

## 7. Production ready?

**Yes with conditions, for the selection contract. No for merging R1 as it stands.**

Conditions before merge:
1. Items 1-4 of the P1 list above are done, with the sandwich and per-member support tests passing.
2. PBX confirms two points: that the claim keeps a stricter opener rule than hooks and clips under L-o, and that the approved trio's ~54 s runtime is correctly rejected under L-o.
3. Someone with the production modules confirms `states()` cannot match a sentence the model did not choose (item 11), and that the smoke test passes on the patched tree.