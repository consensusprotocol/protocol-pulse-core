# claude-opus-5-5 (effort high) 177 s stop_reason=end_turn usage=in 64690 / out 17349

# Protocol Pulse, Cycle 2 audit: pp-selectid, chunk A (contract, predicate, wiring)

**Note on my Cycle 1 output.** The package says "[See below — you wrote this]", but my own Cycle 1 text is not included. I cannot quote my earlier findings or scores. Below, I review the fixed diff on its own and against the three peer reviews and the consensus. Where I would be guessing about my own Cycle 1 position, I say so rather than invent it.

---

## 1. What they caught that I cannot claim credit for

All three peers converged on five things. Each is a real defect in the Cycle 1 code, and I credit them to the peers:

- **Inner-sentence D4 hole.** A non-statement sentence between two story statements skipped D4 (Fable 3, Opus 1, Sonnet 1).
- **Missing time read as 0.** A missing word time counted as a pass (Sonnet 2, Fable 7, Opus 6).
- **Recorder keyed without the seed.** It also cached before validation (Fable 2).
- **Transport errors escaping.** Errors from `OllamaModel` escaped `_ask`, with no `finally` around `L.stop()` / `E.close()` (Opus 3, Sonnet 4).
- **`file_head` defaulting to True.** Combined with backtest window transcripts, this asserted a sentence start that does not exist (Sonnet 3).

Fable 4 is the subtlest of these: the retry loop let a delivered story be re-asked around the ledger.

---

## 2. Agreement and disagreement, checked against the fixed code

| Finding | Verdict | Evidence in the fixed diff |
|---|---|---|
| U1 inner sentences skip D4 | **Agree, fixed.** | `_anchor` lines 1033–1044 now judge every inner non-statement sentence for (a) and (b). Inner sentences are not counted toward the per-direction cap. That is acceptable because T9 caps a range at 3 sentences. |
| U2 missing time = 0 | **Agree, mostly fixed.** | `_time()` (822–825) is used in T10, T12, T13 and `statement_entry`. Two leftovers: `row_marks` still uses `.get("start") or 0` (1351, 1356), and `near()` passes when a time is missing (1008). NaN still slips through `_time` (new finding N4). |
| Fable 2 Recorder | **Partially agree, partially fixed.** | The seed is now in the key (1583) and empty replies are not saved (1598). The reply is still written **before** `check()` runs (1600–1605). Fable's citation says L-f(e) caches only validated replies, so this still conflicts. In practice, a rerun replays the whole rejected chain deterministically and never asks the model. |
| Fable 1 / Opus 2: model gates dropped | **Partially agree.** | Floors are superseded by L-o (accepted, if L-o is PBX law as stated). `verify_support` and `verify_reaction` are now wired (332, 1641–1688). **But** REQUESTS R3 D-a (452–455) still says "R1 does not run them". The doc now contradicts the patch. Also see N1 and N2: the replacement checks are weaker than what they replace. |
| Opus 3 / Sonnet 4: transport errors | **Agree, fixed for one path only.** | `OllamaModel.complete` maps transport errors (1564–1568), and the patch has a `finally` (333–337). The **ModelChecks** path calls `LocalLLM.chat_json` directly. If that raises `URLError` or `TimeoutError` rather than `LLMParseError`, the exception passes through `check()` (not a `Declined`/`ModelError`/`Rejected`), escapes `_ask` and `run_pools`, and crashes the run (N5). |
| Sonnet 3: `file_head` / R4 | **Agree, only half fixed.** | The default is now False (598). But `word_source` hard-codes `file_head=True` (239) **including on the `words_fn` path** (247–248). Without R4, a backtest window transcript is still asserted as full-video, and its times go straight into `to_passages` start/end. R4 is not stated as a prerequisite of R1. |
| Fable 4: ledger re-ask | **Agree, fixed.** | `choose_story` turns `already_delivered` into a final `Declined` (1810–1811). The result is stricter than before: one matching sentence declines the whole group. That is fail-closed, so acceptable. Ledger identity still requires the same `video_id` (1070). A next-day rerun of the same event from new uploads is not caught. Today's `delivered_match` is unverifiable here. |
| Opus: `registry` and `os` undefined | **Still unverifiable.** | Line 225 uses `registry` and line 330 uses `os.path`. Neither is defined in the hunk. The smoke test output is not in the package. |
| U3 gates on every cluster | **Agree, fixed for clusters.** | Lines 339–359 cover clusters. Wire candidates get a `decision` only when the wire pool was **not** evaluated. Evaluated wire items get none. Minor. |
| Peer Q1 / Q3: no fail-open on ids, no model text in outputs | **Agree.** | Re-checked `parse_reply`, `_keys`, `_id`, `Table.span`, `check_story`, `check_lineup`, `to_passages` and `evidence_record`. Every emitted text is `Span.text`. |

---

## 3. New findings from the combined review

### N1 (HIGH): cross-channel coverage now rests on one model reply

Today, G1 required independent per-video verdicts:

- `sm.adjudicate` set `counted_as_same_event` per video (removed lines 160–178).
- `_decide_coverage` then required at least 2 independent channels.

In the fixed code:

- `check_story` and `_lineup` count only distinct `channel_id`s (1514, 1097) and Bitcoin naming (1100).
- `ModelChecks.story` verifies **only the claim** (1657–1666).

**Scenario.** The model returns two unrelated Bitcoin sentences from two channels as one story. Both pass every gate. This loosens the coverage law, is not disclosed, and was flagged by none of the three peers.

**Fix.** Run `verify_support` (or `adjudicate`) on at least one story member from each counted channel, against the claim. Require at least `MIN_COVERAGE_CHANNELS` channels with `SUPPORTS`, of which at least `MIN_LAYOUT_CHANNELS` are layout-eligible.

### N2 (HIGH, behavioural risk, unverified against gemma): `verify_support` is now self-referential

`ModelChecks.query` (1655) builds `{"underlying_event": claim, "action": "-", "affected_object": "-", "entities": []}` and asks whether the claim supports itself.

- `same_actor_action_object` is close to tautological, so the only informative output left is `presented_as`.
- With `"-"` placeholders, gemma may answer `same_actor_action_object: false`. That gives systematic `Rejected` results for every claim: fail-closed, but every run becomes a HOLD.
- The same placeholder query feeds `verify_reaction`.

Only stand-ins exercise this path.

**Fix:**
1. Pass a query built from the claim's verbatim names, e.g. `entities = sorted(event_names(claim))`.
2. Before merge, run 10 or more recorded real claims through `verify_support` and `verify_reaction` with gemma3:27b and record the verdict distribution.

### N3 (HIGH): the runtime law is an estimate calibrated on one 4-segment line-up, and that line-up itself breaks the law

`TAIL_S = 14.30` (554) is a constant derived from the approved preview: 71.08 s final minus 56.78 s of spans.

**Problem 1: the reference fails.** 56.78 + 14.30 = 71.08 s, which is greater than 70. The approved preview's own line-up is rejected by `runtime` (1160). Either the smoke test does not use that line-up, or it would HOLD. Confirm which.

**Problem 2: the tail scales with segment count.** Leads, tails and pads are per segment. A hook + 2 clips line-up gets a smaller real tail than the estimate assumes.

**Scenario.** Estimate 60.4 s, actual about 58.8 s: the hard 60–70 s rule fails open at the low edge.

**Fix:**
- Model the tail as `fixed + per_segment × n_segments`, calibrated on at least two finals.
- Make edl_rules (or the final render gate) enforce the measured 60–70 s on the final.
- Treat the predicate's figure as a pre-filter, not the law.

### N4 (MEDIUM): NaN timestamps pass `_time` and fail open

`_time` accepts any `float` (825), and `json.load` reads `NaN`. All comparisons with NaN are False, which plays out as follows:

| Check | Line | Effect of NaN |
|---|---|---|
| `gap < HOOK_LEAD_S` | 975 | passes the hook lead |
| `gap > ADJ_MAX_START_S` | 1053 | passes D4 (b) |
| inner-sentence `st - prev_end > ...` | 1041 | passes D4 (b) |
| runtime | 1160 | fails closed (correct) |
| `_overlap` | 1179 | fails closed (correct) |

**Fix.** `return float(v) if type(v) in (int, float) and math.isfinite(v) else None`.

### N5 (MEDIUM): ModelChecks transport exceptions escape `_ask`

Described in the table above.

**Fix.** In `ModelChecks.story` and `ModelChecks.lineup`, catch the same transport tuple as `OllamaModel.complete` (1567) and raise `ModelError`. Also confirm `LocalLLM.chat_json`'s raise behaviour, which is unverifiable here.

### N6 (MEDIUM): evidence requires punctuated records before any word pass

`story_table` judges each sentence with `role="evidence"` (1883–1890). That role still enforces:

- T2/T3 fragment;
- T5 unpunctuated (905–918).

For an unpunctuated YouTube auto-caption, `split_sentences` returns the whole record as one non-terminal "sentence", which is rejected. Such a video offers **zero rows**. Today, `adjudicate` read chunk text from caption records. The word pass now happens only **after** a story is accepted (2097), so this is circular: caption-only channels can never corroborate.

This fails closed, but it may starve every pool. The `not_offered` stats will show it.

**Fix.** Before merge, measure `select_by_id[].not_offered` on one live 72 h universe. If `unpunctuated` or `fragment` dominates, either:
- acquire word records for screened clusters' videos before the story call, or
- allow chunk-bounded evidence for segment records, with on-screen roles still requiring L-e.

### N7 (MEDIUM): the GPU0 swap is now per story, and the story calls are unbounded

- `story_words` releases GPU0 per accepted story (252–272). Old E5 did one swap per pool.
- `run_pools` is called without `max_story_calls` (332). Every screened cluster is a story call of up to 3 attempts, plus ModelChecks calls, plus possibly a swap.
- The gate text "the pool's story-call budget" (355) refers to a budget that is never set.

Whether `L` reloads cleanly on GPU0 after each Whisper release is unverifiable. The GPU0 guard `RuntimeError` deliberately crashes the run.

**Fix:**
- Pass `max_story_calls`.
- Batch the word pass: collect accepted stories within a pool, then do one swap.
- Or, at minimum, cap the number of swaps per run and record each in `arb`.

### N8 (LOW): a conjunction opener skips the whole `stand_alone.opener` check

Lines 935–941: when the first word is a conjunction, `stand_alone.opener` is not called at all. Any other rule it applies (a pronoun after "And", the reply-fragment rule) is skipped for "And it…" or "But yeah…".

**Fix.** Run `opener` on the text after removing the leading conjunction.

### N9 (LOW): leftover inconsistencies

- **Stale doc.** REQUESTS D-a (452–455) still says R1 does not run the checks; the patch does.
- **Hint drift.** `row_marks` reads missing times as 0 (1351, 1356) and can mark `+` on a row that eligibility then refuses, against its own docstring (1326).
- **Hidden gaps.** `lineup_table`'s row cap (1943–1944) can drop interior rows, leaving consecutive ids over a sentence gap. The model then gets "not contiguous" rejections it cannot see the cause of.
- **Backtest results.** The `words_fn` branch never writes `arb["results"]`, so a backtest HOLD cannot say why.

---

## 4. Revised scores

My Cycle 1 scores are not in the package, so the Cycle 1 column is marked unavailable rather than invented.

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| Reply contract (`parse_reply`, `check_*`, `Table`) | n/a | 90 | Strict, tested, no fail-open found by anyone. |
| Verbatim guarantee (`Span.text` → passages, ledger) | n/a | 92 | No model-text path. |
| Eligibility predicate | n/a | 74 | U1 and U2 fixed. NaN (N4), `near()` passing on missing times, the runtime estimate (N3) and N8 remain. |
| ModelChecks (D-a replacement) | n/a | 55 | Wired, but self-referential (N2), claim-only coverage (N1) and an escaping transport path (N5). |
| Recorder / replay | n/a | 70 | Seed fixed; still caches before validation. |
| R1 wiring | n/a | 62 | `finally` and gates fixed. `registry`/`os` unverified; `file_head` on `words_fn` without R4; per-story GPU swap with unbounded calls (N7); caption starvation (N6). |
| **Overall** | n/a | **68** | No accepts-model-text hole; real law gaps in coverage and runtime. |

---

## 5. Final priority list

**P0 CRITICAL**

None. No path accepts model-written text or a malformed reply.

**P1 HIGH**

1. **Coverage (N1)** in `select_by_id.ModelChecks.story` (1657–1666) and `choose_story` (1815–1816): verify one member per counted channel against the claim and require at least 2 channels with `SUPPORTS` (at least 2 of them layout-eligible). Without this, G1 is looser than today, which LAW 20 forbids.
2. **Model check query (N2)** in `ModelChecks.query` (1655): build a non-placeholder query and record a real-gemma verdict distribution before merge.
3. **Runtime (N3)** at `eligibility.TAIL_S` / runtime (554, 1156–1164): calibrate the tail per segment, enforce the measured 60–70 s on the final, and reconcile the approved preview's 71.08 s with L-o.
4. **R4 before R1, and `file_head` (Sonnet 3, still open)** at patch lines 239 and 247–248: set `file_head=True` only for store full-video records, never for `words_fn` output unless the record asserts it. Make R4 a stated prerequisite of R1.
5. **Caption starvation (N6)** in `story_table` (1879–1904): measure `not_offered` on a live universe before merge. If caption-only videos are excluded, acquire words before the story call or accept chunk evidence for segment records.

**P2 MEDIUM**

6. **N5:** map ModelChecks transport errors to `ModelError` (1659–1662, 1680–1683).
7. **N4:** `_time` rejects non-finite values (825).
8. **Recorder (Fable 2 remainder):** persist only after `check()` returns accepted or declined (1597–1605).
9. **N7:** pass `max_story_calls` (332); batch or cap GPU0 swaps (252–272).
10. **`near()` fail-open (1008)** on missing times should fail closed, consistent with L-m.
11. **N8:** opener check after a leading conjunction (935–941).
12. **N9 cleanups:** REQUESTS D-a text; `row_marks` time handling; `lineup_table` cap gaps; `arb["results"]` on the `words_fn` path; confirm `registry` and `os` in `_select_story` and attach the smoke test output.

---

## 6. Single highest-leverage change

Make the "≥ 2 independent channels state this development" rule a verified per-channel model check on verbatim member sentences (N1). Today it is only the selecting model's own claim, which removes the gate that `adjudicate` used to provide.

---

## 7. Production ready?

**No, as delivered. It becomes "yes with conditions" when all of the following hold:**

1. P1 items 1–4 are implemented, with tests that fail before the fix:
   - a two-channel story of unrelated Bitcoin sentences is rejected;
   - a 3-segment line-up with an estimate in 60–61 s is checked against the measured final;
   - a `words_fn` window record is refused or marked `file_head=False`.
2. N6 is measured on one live 72 h universe, with `not_offered` stats attached, and stories are actually reachable.
3. N2 is measured on recorded gemma3:27b replies: `verify_support` does not reject well-formed current claims wholesale.
4. The smoke test's output is attached, showing that `registry` and `os` resolve in the patched `_select_story` and that `select_passages` accepts `score: None` passages.
5. REQUESTS D-a is corrected and R4 is listed as a prerequisite of R1.