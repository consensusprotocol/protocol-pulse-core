# claude-fable-5-2 (effort high) 283 s stop_reason=end_turn usage=in 64690 / out 26540

# pp-selectid, cycle 2 final review (chunk A: contract, predicate, wiring)

**Verdict: not ready.** The cycle-1 fix for the inner-sentence D4 hole (U1) does not work as written, and the new independent check never tests whether the second channel states the same event.

Three limits on this review:
- I ran nothing; every finding is from reading the diff.
- My own cycle-1 text was not included in the prompt (the placeholder is empty), so I cannot compare against it or quote my earlier scores.
- The tests are not in this chunk, so I cannot confirm any test-related fix (U4).

## 1. What the others caught

Since I cannot see my own cycle-1 output, I checked each cycle-1 finding against the fixed code instead.

| Cycle-1 finding | Status in the fixed code |
|---|---|
| U1 inner sentence skips D4 | **Not fixed in effect** (new finding N1) |
| U2 missing time read as 0 | Fixed in `_span` and `_anchor`; two remnants (N6) |
| U3 gates, `why`, infrastructure HOLD | Fixed (lines 339-368); evaluated wire candidates still get no `decision` (356-359) |
| M1 model gates dropped | Partly fixed; `verify_support` is aimed at the wrong sentence (N2) |
| M2 transport errors, `finally` | Fixed for `OllamaModel`; two gaps (N7) |
| Recorder caches before validation, key omits seed (Fable 2) | Seed added and empty replies are not saved; rejected replies are still saved (N8) |
| `file_head` default (Sonnet 3) | Default is now False; `word_source` still asserts True for backtest records (N5) |
| Ledger rule routed around by retry (Fable 4) | The retry path is closed (1810-1811); the identity gap remains (N9) |

## 2. Agree or disagree

- **U1, U2, U3, M2:** agree with all four. The U1 fix needs redoing.
- **M1 floors superseded by L-o:** agree, given the law. The `verify_reaction` wiring is correct: it uses a core-only anchor (line 1676).
- **M1 `verify_support`:** partially agree. It was wired, but only against the claim itself.
- **Opus on `registry` and `os` being undefined in the hunk:** still unverifiable here. Only the smoke test output can settle it.
- **No path for a non-id reply to be accepted; no model text in claim, segments, passages or ledger evidence:** still agree after re-reading `parse_reply`, `check_story`, `check_lineup`, `Table.span` and `to_passages`.

## 3. New findings

**N1. HIGH | eligibility.py 1031, 1043, 1059: the inner-sentence check matches the sentence against itself.**
- `anchor` is the token range from the first to the last story sentence, so it contains the inner sentence being judged.
- `_anchor_entities` then returns that sentence's own capitalised words, and `numbers(anchor)` its own numbers.
- Opus's cycle-1 scenario still passes: in `[*, "Anyway, Solana looks great.", *]`, "Anyway" and "Solana" are anchor entities and are found in the text.
- The outer loop inherits the same anchor, so a neighbour can also match on a name that only an inner sentence said.
- Fix: build the anchor from the core sentences only, `" ".join(stext(c) for c in core)`, as `ModelChecks.lineup` already does. Add a test with a capitalised off-topic inner sentence.

**N2. HIGH | select_by_id.py 1654-1666: no check that the other channels state the same event.**
- `verify_support` is called with the claim as both the event and the text. `same_actor_action_object` is then true by construction; only `presented_as` carries information.
- No other story member is checked. The old flow adjudicated every video (`counted_as_same_event`).
- Scenario: channel A says "Bitcoin ETFs took in $1B"; channel B says "Bitcoin fell to 60k today". One model reply joins them and every deterministic rule passes. B's sentence becomes a starred anchor and a clip under A's headline.
- Fix: run `verify_support(query(claim.text), member.text)` for each non-claim member, and require at least two layout-eligible channels to pass.
- Unverified: whether `verify_support` needs a `today` argument, which is not passed.

**N3. HIGH (unverified) | patch 392-419, `to_passages` 1950-1969: nothing downstream of `select_story` is proven.**
- `passages.json` `story` loses `short_label`, `action`, `entities` and the rest of the old query keys.
- `score`, `clip_score` and `relevance` are None.
- The returned label is a full sentence where it used to be `short_label`.
- The smoke test stops at `select_story`. A sort or format on None, or a `story[...]` key read in `select_and_build_edl`, the VO step or Telegram, would fail only in production.

**N4. HIGH (unverified) | patch 252-272 with `OllamaModel.complete` 1566: the production swap sequence is never exercised.**
- The path is: release GPU0, run Whisper, then call `L._post` directly for the line-up.
- The claim that the placement guard is "kept" depends on the guard living in `_post` and not in `chat_json` or `start`. The scripted fake cannot show this.
- There is now one swap per accepted story where there was one per pool, and `max_story_calls` is None in production.

**N5. MEDIUM | patch 234-249: backtest records are asserted as full-video.**
- `word_source` sets `file_head=True` for `words_fn` records and discards the status string.
- Without R4, a run-window transcript (E-FAIL-PS1) is accepted with window-offset times.
- Fix: make R4 part of R1.

**N6. MEDIUM | eligibility.py 1006-1010; select_by_id.py 1351, 1356: two unmeasured-time remnants.**
- `near()` returns True when a time is missing, so an unmeasured statement position counts as near.
- `row_marks` still uses `or 0`, so a '+' hint can be shown that eligibility then refuses.

**N7. MEDIUM | select_by_id.py 1567, 1657-1688; patch 222-232: error handling gaps.**
- The caught exception list assumes urllib. If `_post` uses `requests` or raises `http.client.HTTPException`, transport errors still escape (unverified).
- `ModelChecks` calls `L.chat_json` directly and maps only `LLMParseError`.
- The setup lines (`Context`, `sources_from_universe`) run before the `try`, so an error there leaves the LLM and embedder running.

**N8. MEDIUM | select_by_id.py 1597-1605: rejected replies are still persisted.**
- A rerun replays the same rejections for all three attempts and never asks the model again.
- Fix: delete the record from `_ask` on `Rejected`, or commit only after `check` returns.

**N9. MEDIUM | eligibility.py 1065-1073: DEC-9 holds only if the model re-picks a delivered sentence.**
- Yesterday's videos are still inside the 72 h universe.
- A story built from neighbouring sentences about the same event is accepted.

**N10. MEDIUM | eligibility.py 935-941; select_by_id.py 1339: opener rules.**
- A conjunction opener now skips `stand_alone.opener` entirely, so "And it crashed…" passes the pronoun rule that is still supposed to be hard.
- `ctx.scorer` is None in production, but row marks show 'C' on pronoun openers. This is either a hint the judge refuses, or the T8 exception granted with no score (unverified which).
- Line 990 still rejects a claim that opens on a conjunction, which L-o says never rejects. This needs a ruling.

**N11. MEDIUM | select_by_id.py 1228, 1382-1384: prompt size is never measured.**
- 160 rows at up to 600 characters each can exceed `LLM_CTX`.
- If Ollama truncates the start of the prompt, the claim, the legend and the SECURITY note at the top are lost.

**N12. MEDIUM | select_by_id.py 1664-1665, 1686: unquoted text enters the re-ask prompt.**
- The `verify_support` reason (model-written) and transcript text go into the re-ask prompt outside `<sentences>` and without `_q`.
- The same text reaches the cluster `gate`.

**N13. MEDIUM | select_by_id.py 2107-2110: the winner is the first accepted cluster in clustering order.**
- Importance ranking is gone, and this is not listed in R3.

**N14. LOW | lines 554, 1427, 1449, 452-455, 1214: smaller points.**
- `TAIL_S` is one sample from a four-segment final. By the constants shown, the approved preview estimates 71.08 s, which is outside 60-70 s.
- The prompt rounds the content range to 46-56 s while the rule is 45.7-55.7 s, and the re-ask does not state the measured total.
- R3 D-a and the module docstring are stale.

## 4. Revised scores

Cycle-1 per-subsystem scores are not available to me; the panel gave 66, 66 and 72 overall.

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| Reply contract (ids only, strict parse) | n/a | 92 | No accept path found; unchanged |
| Verbatim output | n/a | 88 | Clean for claim, segments and ledger; N12 touches only the prompt and gate |
| Eligibility predicate | n/a | 68 | U2 fixed; U1 fix ineffective (N1); N6, N10 |
| Independent model checks | n/a | 55 | `verify_reaction` sound; `verify_support` misaimed (N2) |
| Wiring patch | n/a | 62 | Gates and `finally` fixed; N3, N4, N5 open |
| Recorder | n/a | 70 | Seed added; N8 open |
| Overall | 66-72 (panel) | 70 | Real progress, but two high defects in the fixes themselves |

## 5. Final priority list

No P0: I found no path that accepts a non-id reply or model-written text.

**P1 HIGH**
1. Build the D4 anchor from core sentences only (eligibility.py 1031), with a capitalised off-topic test (N1).
2. Run `verify_support` on every non-claim story member against the claim (select_by_id.py 1657-1666) (N2).
3. Prove one scripted run through `select_and_build_edl`, the VO step and the caption with the new `passages.json` and label (N3).
4. Do one live GPU run covering release, Whisper and the `_post` line-up call, with the placement guard confirmed (N4).

**P2 MEDIUM**
5. Ship R4 with R1 (N5).
6. Make `near()` and `row_marks` fail closed on missing times (N6).
7. Widen the caught transport errors, map them in `ModelChecks`, and move setup inside the `try` (N7).
8. Do not persist rejected replies (N8).
9. Strengthen the DEC-9 identity (N9).
10. Apply the pronoun and reply-word test after a conjunction; resolve the 'C' mark and scorer question; get a ruling on the claim's conjunction rule (N10).
11. Budget the prompt against `LLM_CTX` (N11).
12. Quote or drop free text in re-ask reasons (N12).
13. Disclose first-wins selection in R3, or restore a ranking (N13).

## 6. Highest-leverage change

Verify every non-claim story sentence against the claim with `verify_support`, because cross-channel same-event coverage is the one editorial guarantee that currently rests on a single unverified model reply.

## 7. Production ready?

**No.** It becomes yes when all of the following hold:
- P1 items 1 and 2 are implemented, each with a test that fails on the current code.
- P1 items 3 and 4 are shown with actual run output.
- R4 is merged together with R1.
- The smoke test output confirms `registry`, `os` and `u["_rec"]` exist at c1451047.