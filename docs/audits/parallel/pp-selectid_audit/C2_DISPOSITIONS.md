# pp-selectid — audit cycle 2: dispositions (FINAL)

Cycle 2 ran on the FIXED diff (the cycle-1 consensus and law L-o implemented), 02:00-02:06 ET Nov 12. The repo tool
(utils/cross_llm_audit.py) silently drops a file >= 220,000 bytes, and the fixed diff was 247,891 bytes, so it was
audited in two chunks, each < 220,000 bytes:
- A_contract_predicate_wiring: eligibility.py, select_by_id.py and REQUESTS (the R1 patch).
- B_tests_proof_docs: tests, proof driver, stand-ins, smoke test, design doc and bible.

Each chunk went through the tool's own `build_audit_package` and `build_cycle2_prompt`, with the cycle-1 outputs and
C1_CONSENSUS.md. That is five reviewers per chunk on three vendors, each named in its file:
- claude-fable-5-2, claude-opus-5-5, claude-sonnet-5-5 (effort high);
- the tool's own gpt-4o leg, `call_gpt4o`, with OpenAI credit restored about 02:07 ET;
- grok-4.20-0309-reasoning on XAI_API_KEY_MEDLEY. This is the judge role the orchestrator authorised at 02:00. It was
  told it has no tools and must answer in one message.

Runner: scratchpad audit_c2.py. Outputs: `<chunk>/C2_<model>.md`. Prompts: `<chunk>/C2_PROMPT.md`.

Two limits of the tool, recorded rather than worked around:
- `build_cycle2_prompt` truncates each cycle-1 output to 5,000 characters and the consensus to 3,000. The three
  Claude reviewers each said they could not find their own cycle-1 text. It was under "WHAT THE OTHER MODELS SAID".
- Every reviewer saw only its own chunk.

Verdicts (production ready?):

| Reviewer | Chunk A | Chunk B |
|---|---|---|
| fable | No (70) | No for R1; modules mergeable unwired (71) |
| opus | No (68) | No (63) |
| sonnet | No, yes with conditions | Yes with conditions for the contract; No for R1 |
| gpt-4o | No | No |
| grok | Yes with conditions (95) | Yes with conditions (95) |

No reviewer found a P0: no path accepts a non-id reply or model-written text, and every output text is `Span.text`.

Consensus rule, as in cycle 1:
- A finding counts when two or more reviewers raised it.
- A single-reviewer finding is implemented only when I verified it in the code as a fail-open or a breach of a law.
  Each of these is marked "(single, verified)".
- Refutations carry evidence.

## IMPLEMENTED

Each item names the reviewers who raised it, the fix, and the test that fails on the pre-fix code. The proof of
discrimination is scratchpad old_code_check.py, which ran the new eligibility tests against a rebuilt pre-fix
eligibility.py:
- FAIL on the pre-fix code: inner-sentence D4; non-finite time / near; conjunction then pronoun; claim under L-o.
- Pass on both, as expected, because they pin behaviour that already held: cap vs anchor; runtime upper bound; tier
  bounds; `enabled` pinned.

| # | Finding (reviewers) | Fix | Test |
|---|---|---|---|
| C2-1 | Two-channel coverage rested on the selecting reply alone; only the claim was checked, against itself (fable A N2, opus A N1, sonnet A N1, fable B N1, sonnet B N2) | `ModelChecks.story(claim, members)`: today's `verify_support` on EVERY story sentence with the claim as the event (SUPPORTS = same actor / action / object AND presented as current; L-l). Any other verdict rejects the reply, naming the ids; the model is asked again. The query's key entities are the claim's own names, so the entity list is never empty (opus A N2). | `test_model_checks_keep_todays_judgements_on_verbatim_text`: a TOPIC_ONLY member is rejected by id; one verdict per sentence. Smoke: >= 1 verify per story sentence. |
| C2-2 | The D4 anchor for an inner sentence was the whole window, so the sentence matched its own names and numbers (fable A N1). U1 regression tests were missing (fable B N4, opus B, sonnet B N1). | `eligibility._anchor`: the anchor is the statement sentences only. | `test_an_inner_sentence_between_two_statements_meets_d4` covers a capitalised off-topic inner sentence, an inner sentence with its own number, a back-reference, an interjection, and > 8 s from both statements. `test_the_outer_cap_and_the_anchor_hold_apart`. |
| C2-3 | Unmeasured times passed: `near()` returned True on a missing time (fable N6, opus, sonnet N11); `row_marks` read `or 0` (fable, opus, sonnet N12); NaN passed `_time` (opus N4, sonnet N11) | `_time` keeps finite numbers only; `near()` is False on any unknown time (L-m); `row_marks` shows no '+' without times. | `test_a_non_finite_time_is_no_measurement_and_never_near`. The '+'-mark test now uses timed statements and asserts it is never vacuous. |
| C2-4 | The Recorder cached replies before validation (fable A N8, opus A, sonnet A, grok A, fable B N5, opus B, sonnet B) | `Recorder(validated_only=True)` holds a reply until `_ask` settles it: written only when accepted or declined after every check. Production uses it (DEC-13 e, L-l); the R1 patch passes it. The proof keeps `validated_only=False` because the order says "record every reply for offline replay". | `test_the_production_cache_keeps_only_validated_replies`: a prose reply is not cached and is asked again; an accepted reply and a valid decline are cached; an undecidable check is not cached; proof mode keeps everything. |
| C2-5 | The adapter's exception tuple was too narrow (fable A N7, sonnet A N6, grok A/B, sonnet B P1-4) | `OllamaModel` maps OSError, `http.client.HTTPException`, ValueError, KeyError and TypeError to ModelError. The GPU0 RuntimeError still stops the run. | Nine transport forms → model_error; the GPU0 guard propagates. |
| C2-6 | A conjunction opener skipped the opener rules that stay hard (fable A N10, opus A N8) | `leading_conjunctions()`: the conjunctions become a target (L-o), and the pronoun / reply rules apply to the first word after them. | `test_the_word_after_a_conjunction_meets_the_opener_rules` |
| C2-7 | The claim's opener rule contradicted L-o (fable A N10, fable B N9, opus B N7, sonnet B N3) | L-o applied to the claim too: a conjunction is recorded in `targets_missed`; a pronoun or reply word, including one after a conjunction, still rejects. Design doc G5 updated. | `test_the_claim_must_stand_on_its_own` |
| C2-8 | `word_source` asserted `file_head` for backtest records; R4 is a prerequisite (fable A N5, opus A, sonnet A N3) | R1 patch: on the backtest `words_fn` path only a full-video STORE record counts (status 'store ...'). A run's window transcript is refused, with or without R4, because its times are window offsets (E-FAIL-PS1). The path now writes `arb["results"]` (opus A N9). | Smoke runs the live path. The backtest path is covered by the `words_fn` status contract of R4's diff. |
| C2-9 | Evaluated wire candidates got no decision (fable A, opus A, sonnet A N9) | R1 patch: one `gate(g)` for clusters and wire candidates. A story accepted whose line-up was never asked says so ("another group of the pool was selected first"). | Smoke: two clusters; the second's gate is asserted. |
| C2-10 | `max_story_calls` was never passed (fable A N4, opus A N7, sonnet A N10) | R1 patch: `SB_MAX_STORY_CALLS = 12` per run. It is a budget to tune with measured gemma latency (L-p); the pool records "stopped". | `test_checks_are_required_and_one_word_pass_serves_a_pool` (budget branch) |
| C2-11 | One GPU0 swap per accepted story (fable A N4, opus A N7) | `run_pools`: every story call of a pool first, then ONE `words_fn` for the union of their on-screen videos, then the line-up calls in group order (today's E5; law L-r). | Same test (one call for two stories). Smoke: `word_pass == {videos: 3, sentence_ready: 3}`. |
| C2-12 | Selection order was clustering order; importance ranking was lost (fable A N13, sonnet A N5) | `cluster_groups`: widest first (most channels), ties in clustering order. Decision D-f in REQUESTS R3. | `test_clusters_are_offered_widest_first` |
| C2-13 | Model and transcript free text entered the re-ask prompt (fable A N12, sonnet A N8) | Rejections from ModelChecks name ids and enum labels only. The model's reasons stay in the attempt record (forensic), never in a prompt. | Asserted in the model-checks test (no MODEL-WRITTEN-REASON, no transcript words in the re-ask). |
| C2-14 | Prompt size was never measured against LLM_CTX (fable A N11, grok A) | `row_budget()` caps the rows of both tables by characters inside LLM_CTX minus reply and instructions, at a conservative 2.5 chars/token (gemma's tokenizer is unmeasured here). `OllamaModel` never sends a prompt over the context: Ollama drops the head, which holds the instructions. | `test_a_prompt_over_the_context_is_never_sent` |
| C2-15 | `checks` was optional on the production entry (opus B N4) (single, verified: a gate lost by omission) | `run_pools(..., *, checks)` is keyword-only and required; tests pass `checks=None` explicitly. | `TypeError` asserted |
| C2-16 | An outage looked like an editorial HOLD (sonnet A N7) (single, verified: L-n counts editorial holds as selector misses) | R1 patch: when every evaluated group ended in a model error → "HOLD (infrastructure)". | Smoke: scripted outage → HOLD (infrastructure); stop() ran once. |
| C2-17 | The row cap could hide a gap behind consecutive ids (opus A N9) | `_blocks` prints "... (sentences not shown here: a range never crosses this line)". | `test_a_hidden_gap_is_shown_and_the_content_range_is_the_rules` |
| C2-18 | The prompt rounded the content range, and the runtime re-ask had no numbers (fable A N14) | One decimal in the prompt; the re-ask states the ranges' measured seconds and the allowed seconds. | Same test |
| C2-19 | Smoke gaps: one cluster, `finally` unproven, INFRA_HOLD unexercised (opus B, fable B) | Two clusters; `stop()` counted on accepted, fabricated-id and outage paths; outage → infrastructure hold. | `smoke_wiring_patch.py`: SMOKE PASS |
| C2-20 | Missing tests: range shapes, bool/float ids in ranges, replay miss on an unrecorded seed, tier boundaries, `enabled` pinned for every registry channel, runtime upper bound, hard-coded row id, escape behaviour (fable B N9, opus B N9, sonnet B N7) | All added. | `test_range_shapes_are_rejected_never_repaired`, the replay test, `test_the_tier_boundaries`, `test_every_registry_partner_states_enabled_as_a_boolean`, the runtime test, the neutralisation test |
| C2-21 | Proof driver gaps: no ledger, the words used were unhashed, the timezone was unchecked, the main path was hard-wired, the re-check was unlabelled (fable B N6, opus B N9, sonnet B N5 / N8) | Done, except the gemma run (see R-7). The ledger is read read-only; none exists (data/pulse_check/story_ledger.jsonl is absent: nothing was delivered). The words actually used are hashed and re-read in `resolve()`. A run start without a timezone is refused. `PP_MAIN_TREE` sets the main path. The re-check is labelled as the same predicate; `ids_resolve` is the independent angle. | Proof re-run on the final code (see PROOF) |
| C2-22 | The spend guard read without the lock; stale docstrings; proof_table bugs (sonnet B N6, fable B N7 / N8) | `guard()` takes the writers' lock. Docstrings name the real stand-ins. `proof_table` prints models and per-model spend, survives a missing SPEND.json, and names its output file correctly. | — |
| C2-23 | Stale docs (fable B N7, opus B N2, sonnet B N9) | Design doc: L-o in T8 / T10, runtime row, ModelChecks, seed key, section 6 proof, section 7 limits. REQUESTS: R1 prose, R3 D-a / D-f / D-g, R4 status, R6. | — |

## REFUTED (evidence)

- **R-1. "After the GPU0 release, `_post` cannot reach a running Ollama" (sonnet A N2, fable A N4).**
  `release_gpu0_for_whisper` only unloads models with keep_alive 0 (story_semantics.py:299-319; `_unload` at
  :261-268). The Ollama listener keeps running, and `/api/chat` loads the model on the next call. Today's E5 depends
  on the same sequence: a word pass between pools, then gemma calls again.
  The gap that remains is that `placement_checked` stays True after a reload. That is today's LocalLLM behaviour, and
  law L-r's `swap_to(model)` (the integrator's gpu0.py) is the fix. REQUESTS R6 names it.
- **R-2. "ModelChecks transport errors escape `_ask`" (opus A N5).** `LocalLLM.chat_json` catches every exception
  per attempt except the GPU0 guard and raises LLMParseError (story_semantics.py:236-246). ModelChecks maps that to
  ModelError. The stand-in path (`ChatJSON`) maps ModelError and ValueError the same way.
- **R-3. "`registry` and `os` undefined in the hunk" (fable A, opus A, sonnet A: unverifiable to them).**
  editorial_select.py:23 imports os at module level, and `_select_story` defines `registry` at :613, before the
  patched block. The smoke test applies the patch and runs the patched `_select_story` end to end (SMOKE PASS).
- **R-4. grok A: "the diff correctly hard-codes file_head=True only for full-video store records".** Wrong for the
  `words_fn` path, as the other three found; fixed in C2-8.
- **R-5. "`states()` makes a sentence core that the model never chose" (sonnet B N10, unverified to it).**
  The story call and the line-up call read different records of one video, with two segmentations: a caption or
  segment record, then a word record. `states()` maps a story statement onto the word-record sentence that repeats
  >= min(5, len) of its consecutive canonical tokens. `near()` bounds the match to +-30 s of the statement's own
  time, and since C2-3 an unknown time never matches.
  Since C2-1, the statement itself carries its own `verify_support` verdict.
  Limit recorded in the design doc: a word-record sentence that repeats a statement's 5-token run AND adds more words
  counts as core, so it is exempt from D4 (c).
- **R-6. "Run gemma3:27b before merge" (opus B P0).** Not possible in this session: the order leases GPU0
  exclusively to the live run and forbids any GPU use here. It is accepted as the integrator's prerequisite for
  enabling R1: a gemma3:27b shadow run over the saved universes, with the per-attempt validity rate and rejection
  reasons (REQUESTS R6).
  Verified meanwhile: `LocalLLM._post` sets Ollama `"format": "json"`, temperature 0 and `num_ctx` LLM_CTX
  (story_semantics.py:190-195), so a fenced reply is not expected from JSON mode. That is unmeasured on gemma here.

## ACCEPTED AS LIMITS, OR DECISIONS FOR PBX / THE INTEGRATOR

- **L-1. `TAIL_S` is one calibration (all reviewers).** L-o's own proposal uses the same single measurement: 12.91 s of
  non-passage time on the final, which is 14.30 s on word spans. Every approved final so far (preview, v2f) has four
  segments. The predicate's figure is the pre-render check L-o asks for. REQUESTS R6 asks that 60-70 s also be
  measured on the final, in gates or edl_rules, and that `TAIL_S` be refit once three-segment finals exist.
- **L-2. The approved preview against L-o's 60-70 s (fable B N3, opus B N3, sonnet B).**
  - The approved trio without Bitcoin Magazine estimates 54.4 s; Bitcoin Magazine is excluded by DEC-12d.
  - The approved four segments run 71.08 s on the final.
  - L-o says: "the approved preview itself ran 71.08 s; whether the format is checked on the final's runtime with a
    tolerance is PBX's call". The fable strategy review proposes 58-72 s with elastic VO.
  - The must-pass test therefore asserts a four-segment line-up that passes our rules, from the preview's own sources. It does not
    claim this is the approved line-up, and the test docstring says so.
  - PBX decision.
- **L-3. L-o is not yet wired downstream (fable B N2, opus B N1).** edl_rules R5 (8-25 s), stand_alone at validate and
  select_passages:333 still apply the windows as hard filters. L-o's own CHECK says: "Until wired, the existing code
  still applies the windows and floors as hard filters." A line-up outside the windows can therefore HOLD at validate.
  That fails closed and is recorded. REQUESTS R6 names the three sites.
- **L-4. DEC-9 identity is per statement, not per event (fable A N9, opus A, sonnet A, opus B, sonnet B N4).** This
  is parity with today's `story_ledger.delivered_match`. Novelty under L-p / L-q is open for the orchestrator.
  Design doc section 7.
- **L-5. The claim may come from an evidence-only channel (sonnet A N13).** Decision D-b stays open.
- **L-6. The reply-word clip exception needs a scorer verdict that R1 never runs (opus B N8).** It fails closed:
  every reply-word clip opener is refused. Design doc section 7.
- **L-7. Targets do not rank across candidates (fable B N2, sonnet B).**
  - The line-up prompt states the targets as preferences.
  - Every deviation is recorded in `facts.targets_missed`, which is what L-o asks to be recorded.
  - Deterministic ranking belongs to the moments-first miner and packager (phase 2), where the packager chooses the
    package type; story-first is one type (order 02:30, L-w 3).
- **L-8. Downstream consumers of passages.json with null scores (fable A N3, grok A).** The smoke test stops at
  `select_story`. The moments-first wiring (phase 2) will be smoke-tested through select_passages' PIN path and the
  EDL. R1's consumers are the same.
