# claude-sonnet-5-5 (effort high) 139 s stop_reason=end_turn usage=in 64690 / out 18022

# Cycle 2 audit: pp-selectid (chunk A: contract, predicate, wiring)

**Caveat on my own Cycle 1.** The prompt says "see below, you wrote this," but my Cycle 1 text is not included. I do not know which model I was, so I won't claim credit for findings I can't see. The other three reports are truncated: Fable's defect 4, Opus's defect 3 onward and Sonnet's defect 5 are cut off. I treat them as incomplete and review the fixed diff directly. I ran nothing. Anything that depends on code outside the diff (`LocalLLM._post`, `story_semantics`, `registry`, `os` in `_select_story`) is marked unverifiable.

## 1. What the others caught that I would have missed

- **Inner-sentence hole in `_anchor`** (Fable 3, Opus 1, Sonnet 1). The fix is in the diff (lines 1033-1044) and is correct.
- **Missing time read as 0** (Fable 7, Opus 6, Sonnet 2). `_time()` (lines 822-825) fixes it in `eligibility`. Not every site was fixed, see N5.
- **Transport errors escaping `OllamaModel`** (Opus 3, Sonnet 4). Now mapped to `ModelError`, and `L.stop()` / `E.close()` are in a `finally`. The adapter's `except` tuple is too narrow, see N6.
- **Lost ledger gates and lost infrastructure HOLD** (Fable Q4, Opus 5, Sonnet 5). Mostly fixed. Wire candidates still get no per-candidate decision, see N8.
- **`Source.file_head` default** (Sonnet 3). The default is now `False`, but `word_source` re-asserts `True` unconditionally, see N3.
- **Recorder key omitted the seed** (Fable 2). Fixed at line 1583.

## 2. Agreement and disagreement

| Finding | Verdict |
|---|---|
| Fable 1 / Opus 2: R1 drops the model gates (floors, `verify_support`, `verify_reaction`) | **Partially agree.** L-o legitimately supersedes the floors. `verify_support` and `verify_reaction` are now back. But the replacement checks the claim only, so a larger gap remains (N1). |
| Fable 2: Recorder caches before validation | **Downgrade to P2.** At temperature 0 with a fixed seed, a replayed bad reply is the same reply a fresh call would give. The remaining problem is that the docstring and L-f(e) wording ("validated replies only") are untrue. |
| Fable 4: delivered ledger is per sentence | **Agree, still open.** `_delivered` (lines 1065-1073) matches the same video plus the same statement. A different channel's sentence about the already delivered event passes. It now fails closed on a hit (Declined), but the identity is unchanged. This matches today's `delivered_match` as far as I can tell, so it is a parity limitation, not a regression. |
| Opus Q4: `registry` and `os` undefined in the hunk | **Agree, unverifiable.** The smoke test must prove them. |
| Sonnet 3: `file_head` | **Agree, and the fix is incomplete** (N3). |
| All three: no fail-open for non-id replies | **Agree.** I re-read `parse_reply`, `_keys`, `_id`, `Table.span`, `check_story` and `check_lineup` and found no path. The `story == []` check with `claim is None` is exact, and `False == []` is False. |

## 3. New findings

**N1. HIGH | Cross-channel same-event coverage is self-attested by the model.**
- **Code:** `ModelChecks.story` (lines 1657-1666) verifies only the claim sentence. `choose_story` (lines 1815-1816) calls it only on `claim_span`.
- **Issue:** Old step 5 ran `adjudicate` per video, counting `counted_as_same_event`. That was the independent proof of G1 (two channels, one event). Now the model's `story` list is the only evidence. Eligibility checks that each sentence names Bitcoin and that two channels appear. It never checks that channel B's sentence states the claim's event.
- **Scenario:** Claim from channel A: "Bitcoin ETFs saw $400M inflows." Story id 2 from channel B: "Bitcoin is a store of value." Both name Bitcoin and are eligible, so the two-channel rule passes. The line-up then stars both, because `lineup_table` stars by `states()` against the story sentences. The video presents one channel's news as corroborated.
- **Fix:** Run `verify_support` (or `adjudicate`) for every story sentence not in the claim's channel against the claim. Require SUPPORTS from at least `MIN_COVERAGE_CHANNELS` channels including the claim's. A negative verdict means Rejected and re-ask.

**N2. HIGH | Unverified GPU0 hand-over between the story call and the line-up call.**
- **Code:** `story_words` (lines 241-324) calls `release_gpu0_for_whisper`, which stops Ollama. `OllamaModel.complete` (line 1566) then calls `self.llm._post(...)` directly for the line-up.
- **Issue:** Old code reached the LLM through `chat_json`, and I cannot see whether `_post` restarts Ollama. If it does not, every line-up call raises `URLError`, which is mapped to `ModelError` (line 1568), which gives `model_error`. Production would then never select, and the smoke test (scripted LLM) cannot detect it.
- **Fix:** Confirm `_post` ensures the server is running. If it does not, call the `LocalLLM` start routine after `ts.release_whisper()`. Add a test in which the stand-in raises `URLError` after a "release".

**N3. HIGH | `word_source` hard-codes `file_head=True, vod=True` (lines 234-239).**
- **Issue:** This asserts "full-video store record" for every `words_fn` record. The backtest's fallback to `_run_transcript` (window transcripts, R4) is exactly the record that is not a full video. With R4 unapplied, the backtest accepts a window's first word as a sentence start and skips the hook lead measurement. R4 is presented as optional.
- **Fix:** Set `file_head` only when the record is demonstrably a store record, for example it lacks a window offset or `source_path`. Otherwise make R4 a prerequisite of R1.

**N4. MEDIUM-HIGH | `TAIL_S = 14.30` is one calibration point (lines 554-556).**
- **Issue:** It comes from one approved preview (71.08 s finished − 56.78 s of word spans, four segments). Per-segment lead/tail pads scale with segment count, but the constant does not. A hook plus 2 clips has fewer pads, so its true runtime can fall below 60 s while the estimate says 60+. The law is a hard rule on actual runtime, and the predicate gates on an estimate.
- **Fix:** Model the tail as a fixed part plus a per-segment part, using at least three real finals with 3 and 4 segments. Re-measure the actual runtime before accepting, or hold when the estimate is within about 2 s of a limit.

**N5. MEDIUM | Selection order is clustering order, not story importance.**
- **Code:** `cluster_groups` (lines 2004-2018) and `run_pools` (first accepted line-up wins, lines 2107-2110).
- **Issue:** Old behaviour: "highest story importance among producible candidates, ties by coverage then clip quality". New behaviour: the first cluster in clustering order that produces any legal line-up wins. The importance, Bitcoin-relevance and recency score is gone, and this is not listed in R1/R3. It is a product-level change.
- **Fix:** Order the groups deterministically (channel count, freshest Bitcoin age, rows), or disclose it as decision D-f.

**N6. MEDIUM | `OllamaModel` exception tuple is narrow, and `ValueError` / `KeyError` hide bugs (lines 1567-1568).**
- `http.client.IncompleteRead` (an `HTTPException`) and `requests` exceptions, if `_post` uses them, are not covered.
- The `ValueError` / `KeyError` catch masks programming errors inside `_post` as a model outage.
- **Fix:** Catch `OSError` and `http.client.HTTPException`. Parse the payload separately inside the adapter.

**N7. MEDIUM | Outages look like editorial declines.**
- **Code:** patch lines 365-370.
- **Issue:** If Ollama is down for all groups, every group ends `model_error`, but the decision text is "HOLD: no candidate is producible". Only GPU0-release and word-pass failures are tagged infrastructure.
- **Fix:** Count `model_error` attempts and include them in the decision text. HOLD (infrastructure) if every evaluated group ended `model_error`.

**N8. MEDIUM | Unsanitized transcript text reaches the re-ask prompt.**
- **Code:** `ModelChecks.lineup` raises `Rejected(... '{text(k)[:80]}' ...)` (lines 1685-1687). `_ask` appends `reason[:400]` to the prompt outside `<sentences>` and outside `_q` (line 1771).
- **Issue:** This is an instruction-position channel for untrusted text. The output is ids only, so harm is bounded by eligibility, but the UNTRUSTED header no longer covers it.
- **Fix:** Drop the text from the reason (use the id), or pass it through `_q`.

**N9. LOW-MEDIUM | Wire candidates get no per-candidate gate (patch lines 356-359).**
- `cands[].decision` is set only when the wire pool was not evaluated. For an evaluated wire pool, the group's outcome is never mapped back. The group label is "wire j", not the candidate. DEC-13 d regresses for that pool.
- **Fix:** Carry the candidate index in the label and write its decision, as is done for clusters.

**N10. LOW-MEDIUM | `max_story_calls` is never passed (patch line 332).**
- Story calls are unbounded across all clusters in a tier, at up to 3 attempts plus checks each. The "story-call budget" gate text (patch line 355) is dead.
- **Fix:** Pass a budget, or remove the dead text.

**N11. LOW | `_time` accepts NaN / inf.**
- `type(v) in (int, float)` lets `NaN` through. `NaN < HOOK_LEAD_S` is False, so `hook_lead` passes. `json.load` accepts `NaN`.
- **Fix:** Add `math.isfinite`.
- Related: `near()` returns True when times are unknown (lines 1006-1010). That is a missing measurement passing, contrary to L-j, though low impact because story spans come from interpolated times.

**N12. LOW | `row_marks` still uses `or 0` (lines 1351, 1356).**
- Presentational only (eligibility re-judges), but a missing time can mark a row `+` that eligibility then refuses.
- **Fix:** Mirror `_time`.

**N13. OPEN DECISION | D-b: the headline is the claim sentence.**
- Eligibility does not require the claim to be in the line-up. It allows a claim from an evidence-only (chyron) channel, whose words may never be heard on screen.
- **Fix:** Require the claim's channel to be layout-eligible, which is a cheap stricter rule, or make `headline_numbers_said` an explicit gate.

## 4. Revised scores

My Cycle 1 numbers are not visible, so that column is blank rather than invented.

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| Reply contract (parse, ids, ranges) | n/a | 92 | I found no fail-open path. |
| Eligibility predicate | n/a | 78 | Inner-sentence hole and missing-time fixes verified. Runtime constant and NaN remain. |
| Independent model checks | n/a | 58 | Claim-only verification leaves G1 self-attested (N1). |
| Wiring / GPU / infrastructure | n/a | 55 | N2, N3, N7 and N10 are unverified or open. |
| Verbatim guarantee | n/a | 90 | No path from model text to the output. N8 is only a prompt-side channel. |
| Tests (not in this chunk) | n/a | not scored | The test files are not in this chunk. |

## 5. Final priority list (diff line numbers)

**P0 (blocks ship)**
1. **N1.** Verify every non-claim story sentence against the claim: `ModelChecks.story`, lines 1657-1666, wired in `choose_story`, lines 1815-1816.
2. **N2.** Prove the LLM is running at the line-up call after `story_words` (lines 241-324; `OllamaModel.complete`, line 1566).
3. **N3.** Do not hard-code `file_head=True` for `words_fn` records (lines 234-239), or apply R4 within R1.

**P1**
4. **N4.** Calibrate `TAIL_S` per segment (lines 554-556).
5. **N5.** Define selection order within a pool (lines 2004-2018, 2107-2110), or disclose it.
6. **N7.** Distinguish an outage from an editorial HOLD (patch lines 365-370).
7. **N13 / D-b.** Decide the claim-on-screen rule.
8. **N6.** Widen the transport exception tuple (lines 1567-1568).

**P2**
9. **N8.** Sanitize the re-ask reason (lines 1685-1687, 1771).
10. **N9.** Give evaluated wire candidates a gate.
11. **N10.** Pass `max_story_calls` or remove the dead text.
12. **N11 / N12.** `isfinite` in `_time`; `near()` with unknown times; `or 0` in `row_marks`.
13. **Recorder docs.** The Recorder caches raw replies before validation (lines 1589-1606). Reword L-f(e) accordingly.
14. **Unverifiable.** Confirm `registry` and `os` are in scope in `_select_story`.

## 6. Highest-leverage change

Make the "two channels state the same event" condition independently verified for every story sentence (N1), because it is the only core editorial guarantee that now rests entirely on the model's own word.

## 7. Production ready?

**No. Yes with conditions** once these hold:
1. P0 items 1-3 are done, each with a test that fails first.
2. A non-scripted smoke run against the real `LocalLLM` completes a full story call, GPU0 swap and line-up call.
3. N4 is calibrated on at least three real finals.
4. The unverifiable items (`registry`, `os`, `_post` return type and restart behaviour, `verify_support` and `verify_reaction` signatures with the stub query dict) are confirmed by running the code.

The reply contract and the verbatim guarantee are in good shape. The remaining risk is in what the model is trusted to assert, and in a production path that has been exercised only with a scripted model.