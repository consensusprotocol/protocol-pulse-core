# pp-selectid — STATE (session pipeline_pp_selectid, branch pp-selectid, worktree ~/worktrees/pp-selectid)

## MOMENTS / PACKAGE INPUT CONTRACT v0 (published 02:36 ET Nov 12 for pipeline_pp_ingest; fields may be ADDED, never renamed or removed)

The moment ledger is append-only JSONL, one moment per line. Proposed path: `data/editorial/moments/moment_ledger.jsonl`
(the ingest session owns the path; the packager takes it as an argument). A moment is whole sentences of ONE source
record, by id; its text is never rewritten.

```
{"schema": "pp.moment/1",
 "moment_id": "<sha256('video_id|transcript_sha256|w0|w1')[:20]>",   # stable identity: same record + same words
 "video_id": "...", "channel_id": "...", "channel_name": "<registry display_name>",
 "published_at": "<aware ISO-8601 of the ORIGINAL upload>", "title": "<exact video title>",
 "transcript_sha256": "<transcript_store segments sha>", "transcript_method": "...",
 "timing": "word" | "segment",                    # word = sentence-ready word record (law L-e); else captions / segments
 "words": [w0, w1],                               # token indices into select_by_id.tokens_from_record(record)
 "sentences": [k0, k1],                           # into eligibility.split_sentences(tokens): WHOLE sentences only
 "text": "<eligibility.spoken(tokens[w0..w1]): verbatim as spoken, law L-h>",
 "start": s, "end": s,                            # the record's own times (seconds from the file start)
 "duration_s": s | null,                          # word timing only; else null and:
 "duration_estimate_s": s | null,                 # caption / segment timing: a FLAGGED estimate, never used for runtime
 "speaker": {"turn_change_inside": bool | null, "label": str | null, "confidence": float | null,
             "named": str | null, "named_source": "metadata" | "diarisation" | null},   # law L-v (1); null = not measured
 "scores": {"hook_first_2s": 0-5, "quotable": 0-5, "surprising_fact": 0-5, "stance": 0-5, "stakes": 0-5,
            "stands_alone": 0-5, "contempt_outrage": 0-5},   # integers; contempt_outrage is a PENALTY (law L-u)
 "names_person": bool,                            # a fact, never a positive axis on its own (L-u)
 "risk": ["accusation" | "partner_attack" | "imperative" | "guaranteed_return" | "single_source_breaking" |
          "ad_read" | "third_party_media" | "price_prediction" | "doom" | "politics_non_btc" | "time_sensitive"],
 "topics": ["<closed Bitcoin taxonomy id>", ...],  # pipeline/trend_brief.py TAXONOMY (published with phase 2)
 "reason": "<= 160 chars, model text: FORENSIC ONLY, never enters a prompt or anything audience-facing",
 "eligibility": {"role": "clip" | "hook", "ok": bool, "reasons": [...], "targets_missed": [...]},  # eligibility.eligible
 "mined": {"by": "<model name@digest>", "prompt_sha256": "...", "reply_sha256": "...", "at": "<ISO>", "cycle": "..."}}
```

Rules the packager applies on reading; the ingest session may pre-apply them, never relax them:
- The packager reads "best unused moments since T": lines with `mined.at >= T` or `published_at >= now - 72 h`, de-duplicated by
  `moment_id` (the latest line wins), minus moments delivered in the previous 24 h (DEC-9 / L-p novelty, delivered
  moment ids).
- A moment the packager can use must have:
  - `eligibility.ok`, re-judged by the packager with its own clock;
  - no hard-exclusion risk flag (L-u): accusation, partner_attack, imperative, guaranteed_return,
    single_source_breaking, ad_read, third_party_media;
  - `speaker.turn_change_inside == false` (L-v 1; null = not measured = not usable on screen, law L-m);
  - word timing for anything heard (L-e).
- Down-weighted, not excluded: price_prediction (at most one per video), doom, politics_non_btc. Ranking is deterministic
  (scores minus penalties, ties by moment_id).
- Fairness (L-u): at most ONE clip per channel per video and at most 20 s per source video. The opt-out registry
  `pipeline/optout.json` (channel ids; PBX 02:35) is honoured by the miner AND the packager.
- Package output `pp.package/1`: type story | moments; ordered segments (moment ids, verbatim text, times); the PBX MAX VO
  (intro, bridges, sign-off); ONE title, ONE caption (L-t); checks (VO fidelity, context integrity L-s, exclusions,
  runtime); the model per artefact; dollars. Detailed with phase 2 in docs/audits/MOMENTS_FIRST_DESIGN.md.

## LIVE STATE (newest first; ET; times corrected 01:46 from file times: four entries had been stamped
## from an elapsed-time estimate, 30-110 min late)

- 02:53 Nov 12 PHASE 1 DONE: d809a1f8, pushed. Was: COMPLETE, COMMITTING. Audit cycle 2 dispositions: pp-selectid_audit/C2_DISPOSITIONS.md (23
  fixes implemented, each with a test that fails on the pre-fix code; 6 refuted with evidence; 8 limits for PBX or the
  integrator). Checks: 123 tests passed (10 GPU-skipped), SMOKE PASS, regression_test.sh 26 PASS / 0 FAIL.
  - Proof column of record: judge at temperature 0, production parity. The proof table is below; the per-defect
    answers are in pp-selectid_PROOF.md.
  - No saved universe produced an accepted line-up. The preview's story was accepted, and its line-up call declined
    although a line-up that passes our rules exists (a generator recall miss, recorded). Most clusters stop at the
    per-sentence check, today's strict same-event judgement.
  - Three old universes (Nov 6-7) are still running in this column and follow in the next commit.
  - Stand-in spend for phase 1: $23.33 estimated (upper-bound prices), plus the audits (cycle 1 and cycle 2 reviewer
    calls, ~$11 estimated), against a $40 guard on stand-in spend.

## PHASE 1 PROOF TABLE (generated: tests/select_by_id/proof_table.py)

### Column of record
| run | written (ET) | judge | groups screened 48h / 72h | story calls | outcomes per group | line-up | every id resolves | line-up passes eligibility (re-check) | claim (verbatim source sentence) |
|---|---|---|---|---|---|---|---|---|---|
| fresh_20261112_050611 | 02:43 | grok-4.20-0309-reasoning@t0 | 42 / 18 | 8 | 5 declined, 3 rejected, 1 no model call | no | - | - | - |
| fresh_20261111_190259 | 02:45 | grok-4.20-0309-reasoning@t0 | 41 / 12 | 8 | 4 declined, 3 rejected, 1 story; line-up not asked (no word record) | no | - | - | Bitcoin touched its 200 day moving average today. |
| fresh_20261111_213954 | 02:46 | grok-4.20-0309-reasoning@t0 | 38 / 19 | 8 | 6 declined, 2 rejected | no | - | - | - |
| fresh_20261112_001448 | 02:40 | grok-4.20-0309-reasoning@t0 | 38 / 19 | 8 | 6 declined, 2 rejected | no | - | - | - |
| fresh_20261112_013452 | 02:42 | grok-4.20-0309-reasoning@t0 | 39 / 21 | 8 | 4 rejected, 4 declined | no | - | - | - |
| fresh_20261110_093150 | 02:45 | grok-4.20-0309-reasoning@t0 | 24 / 14 | 8 | 6 declined, 2 rejected | no | - | - | - |
| fresh_20261111_192645 | 02:42 | grok-4.20-0309-reasoning@t0 | 41 / 15 | 8 | 5 declined, 3 rejected | no | - | - | - |
| fresh_20261107_080503 | - | - | - | - | not run yet in this column | - | - | - | - |
| fresh_20261107_065702 | - | - | - | - | not run yet in this column | - | - | - | - |
| fresh_20261106_213852 | - | - | - | - | not run yet in this column | - | - | - | - |
| pinned_20261111_172202 | 02:37 | grok-4.20-0309-reasoning@t0 | - / - | 1 | 1 story; line-up declined | no | - | - | Bitcoin has now seen a 16 % decline from the overall high from $88,000, touching down towards about $73,400, $ |

Models per run file (generator / judge): {"generator": "anthropic:claude-fable-5-2@medium", "judge (ModelChecks)": "xai:grok-4.20-0309-reasoning@t0", "openai_probe": "ok"}

Stand-in spend estimate, all proof runs of this session: $23.3678 over 437 calls (1272680 prompt / 464904 completion tokens); per model, at the upper-bound USD prices per 1M tokens [input, output] each stand-in declares:
- anthropic:claude-fable-5-2@medium: 159 calls, $9.5512 at [8.0, 40.0]
- anthropic:claude-opus-5-5@medium: 49 calls, $1.2753 at [4.0, 20.0]
- xai:grok-4.20-0309-reasoning: 106 calls, $5.3511 at [5.0, 25.0]
- xai:grok-4.20-0309-reasoning@t0: 81 calls, $4.2236 at [5.0, 25.0]

### pinned_20261111_172202 (the approved preview): overlap with its four passages
| approved | channel | chosen by select_by_id | same words | overlap s | eligible with the model's own story | why not |
|---|---|---|---|---|---|---|
| hook | DataDash | - | False | - | True |  |
| clip_01 | Natalie Brunell | - | False | - | False | no_story_statement: holds no sentence that states the story (editorial_select anchored_window) |
| clip_02 | Yahoo Finance | - | False | - | True |  |
| clip_03 | Bitcoin Magazine | - | False | - | False | layout_ineligible: Bitcoin Magazine: burned-in chyron (has_chyron, DEC-12d); not_sentence_ready: no sentence-ready word record (law L-e): a stretch reads unpunctuated; no_story_statement: holds no sentence that states th |

- 02:40 Nov 12 (this machine's clock; the note is stamped 02:45) NOTE RECEIVED: L-x NO SINGLE MODEL, ULTRON FIRST.
  - Phase 2 puts every model role behind ONE provider interface, with a config naming at least two interchangeable
    back-ends per role, in this order: local gemma3:27b on Ultron first, then frontier (OpenAI / Anthropic / xAI) or
    Heimdall (OpenAI-compatible, HEIMDALL_API_KEY). The roles are mining, scoring, angle / packaging, VO / title
    writing, the fidelity verdict, the context verdict and the trend brief.
  - The run continues when a vendor fails: out of credit, 429, 5xx or transport errors. Generator and judge are always
    different models. No vendor or model name appears outside the config.
  - A blind A/B harness per role, with its prompts, is provided. The integrator runs the local leg under the GPU0
    lease; this session runs the frontier and Heimdall legs.
  - Heimdall spend: the 90% tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of this file) and a fallback,
    never a halt.
  - For phase 1, R1's patch builds `OllamaModel(L)` directly. Under L-x it will take the role's provider chain from the
    phase-2 config; recorded in REQUESTS R6.

- 02:36 Nov 12 ORDERS 02:30 (strategy audit: laws L-s..L-w) AND 02:35 (PBX decisions) RECEIVED.
  - All four strategy reviews were read before continuing (heimdall_probe/pp_redteam/strategy: claude.md, gpt.md,
    grok47.md, grok420r.md). Phase 2 is built to L-s..L-w, and none of its output is called DONE without them.
  - Consequences for phase 1: L-w 3 keeps story-first as a package type, so R1 is that type's selector (not superseded).
    L-u (one clip per channel, <= 20 s per source video) is recorded in REQUESTS R6 and applied by the phase-2
    packager; the audited predicate is unchanged.
  - 02:35: the moments/package input contract for pipeline_pp_ingest is published at the top of this file. The
    opt-out registry file replaces partner outreach. Frontier models write and check (angle, VO, title, fidelity,
    context), with dollars per video reported. The launch cadence is 2 videos a day. Vocabulary: "a line-up that
    passes our rules", never "legal".
  - Phase 1 is nearly finished. Audit cycle 2 dispositions are in pp-selectid_audit/C2_DISPOSITIONS.md, and 23 fixes are
    implemented with tests that fail on the pre-fix code. Smoke pass; 123 tests passed (10 GPU-skipped);
    regression_test.sh 26 PASS / 0 FAIL. The proof is re-running on the final code with the same generator for the
    whole column. Commit and push follow.
  - CORRECTION: the OpenAI probe's HTTP 400 from 01:44 to 02:30 was the probe's own wording. json_object mode needs the
    word "JSON" in the messages. It was not the account: from 02:07 OpenAI answered every correctly worded call.
    Fixed; the probe returns ok.

- 02:08 Nov 12 PHASE 2 ORDER + ADDITION (01:55) AND ORCHESTRATOR NOTE (02:00) RECEIVED. Phase 1 is finished first
  (audit kept), then Phase 2 starts. Model roles, per the 02:00 note, recorded per artefact:
  - Phase 1 proof (started 02:02, three processes over the 11 saved universes): generator
    anthropic:claude-fable-5-2@medium (its OpenAI probe at 02:02 answered HTTP 400 invalid_request_error); judge
    xai:grok-4.20-0309-reasoning on XAI_API_KEY_MEDLEY (ModelChecks: verify_support on the claim, verify_reaction on
    non-statement sentences; told it has no tools and must answer in one message). One generator for the whole
    column, so the table mixes no models.
  - OpenAI re-probed at 02:07: HTTP 200 from gpt-6.1-sol (three request variants). Work after this proof goes back to
    gpt-6.1-sol as generator / stand-in. The judge stays Grok, so generator and judge are on different vendors. Next
    probe after any 429 / 5xx: in about 20 min.
  - Audit cycle 2 running on the FIXED diff, split into two chunks of < 220,000 bytes (the tool drops larger files):
    claude-fable-5-2, claude-opus-5-5, claude-sonnet-5-5, the tool's own gpt-4o leg (OpenAI credit back) and
    grok-4.20-0309-reasoning (medley key). That is three vendors.
  - Phase 1 spend estimate (upper-bound prices): $8.27 at 02:05, against a $40 guard.

- 01:44 Nov 12 RUNNING: (1) the full proof with the substitute stand-in claude-opus-5-5 (A6; preview row done: the same
  story as gpt-6.1-sol found, then the line-up call DECLINED, which is the correct answer under today's rules for that
  story marking; one call); (2) audit cycle 1 on the actual diff (docs/audits/parallel/pp-selectid_audit/STEP.diff,
  213,853 bytes, base BASE.txt). BLOCKED-PARTIAL (audit legs): utils/cross_llm_audit.py cannot run its three external
  legs here: the permitted env file defines no GEMINI_API_KEY and no XAI_API_KEY (the names the tool reads; checked
  by presence only) and the OpenAI account is out of credit. The audit therefore uses the tool's own package builder
  and cycle-2 cross-review prompt with three Anthropic reviewers named as such (claude-fable-5-2, claude-opus-5-5,
  claude-sonnet-5-5); the cross-vendor leg is the integrator's own two-cycle audit of this branch before merge.

- 01:40 Nov 12 STAND-IN SWITCHED: the OpenAI account is out of credit (the API answers HTTP 429 type
  insufficient_quota, code credit_balance_exhausted; the key is shared by every session; this session's own estimate
  at upper-bound prices is $2.97 over 42 calls). The 01:34 re-run made no call and was stopped by me. Assumption A6
  below: the proof continues with Gemini as the stand-in. regression_test.sh 26 PASS / 0 FAIL in this worktree
  (after copying the gitignored assets outro_branded.mp4 + music/*.mp3 from the main tree, read only; never
  committed); pipeline test_canon (site test covers the new modules) / test_stand_alone / test_dec13_clusters /
  test_editorial_robust / test_backtest: 67 passed, 10 GPU-skipped.

- 01:34 Nov 12 IN PROGRESS: full proof re-running (nine saved universes + the preview; stand-in gpt-6.1-sol, every
  reply recorded under tests/select_by_id/fixtures/replies; spend estimate before this run $2.97 of the $40 guard).
  Built since 01:08: select_by_id.run_pools (the production entry: DEC-13 pools by id, word pass between the calls,
  ledger-form evidence); the R1 wiring patch (editorial_select pools -> run_pools; select_passages hook + >= 2 clips)
  in pp-selectid_REQUESTS.md, git-apply clean on c1451047 and SMOKE PASS end to end on a temp copy
  (tests/select_by_id/smoke_wiring_patch.py: the approved DataDash / Natalie / Yahoo line-up word for word; a
  fabricated id holds the run). Found and fixed by the stand-in's real replies: D4 (a) needs the event's names (the
  claim's), retry reasons must use the model's ids, row hints must never promise what the judge refuses, a one-word
  sentence starred a statement (today's 5-token statement floor + asymmetric `states`), the line-up call needs a
  final decline. 38 tests pass. Next: proof table, cross-LLM audit (2 cycles), commit, push.
  NOTE: the first full proof run got HTTP 429 on every call for five runs (shared OpenAI key); the stand-in now backs
  off (20/40/80/160 s) and records the API's error code.

- 01:08 Nov 12 IN PROGRESS: pipeline/eligibility.py + pipeline/select_by_id.py written (uncommitted);
  tests/eligibility (18) + tests/select_by_id (16) = 34 passed, all eight ordered must-fails among them. Design doc
  docs/audits/SELECT_BY_ID_DESIGN.md written (rule inventory with file:line). Next: the proof driver over the saved
  universes (stand-in model, recorded), then audit, commit, push.
  Found on the way (to BIBLE_ADDITIONS): pipeline/backtest.py _run_transcript uses a run's WINDOW transcript
  (select_passages: offset 23.38 s etc.) as full-video word timing; the protected preview's Bitcoin Magazine window
  transcript fails today's whole-record L-e readiness on one word 570 s from its clip.

- 00:52 Nov 12 IN PROGRESS: read-in done (CONSTITUTION, PIPELINE_LAWS, CROSS_LLM_AUDIT_LAW, docs/QWEN_CONTEXT_BIBLE.md,
  DEFINITION_OF_DONE_PULSE_CHECK.md, REDTEAM_2026-11-11.md; editorial_select, story_semantics, select_passages,
  sentence_law, stand_alone, run_fresh, canon, transcript_store, backtest, edl_rules). Writing the design doc
  (rule inventory with file:line), then pipeline/eligibility.py + tests, pipeline/select_by_id.py + tests, the proof
  over saved runs, the audit (2 cycles), commit + push. Nothing committed yet. Nothing blocked.

## ASSUMPTIONS (most defensible reading; the integrator may overrule)

- A1 RUN NAMES: `fresh_20261112_014204` does not exist under runs/. The integrator's own DoD (main tree, LIVE STATE
  00:06 ET Nov 12) records that the run it describes is `fresh_20261112_013452`. The named holding runs are therefore
  fresh_20261111_213954, fresh_20261112_001448, fresh_20261112_013452; fresh_20261111_190259 (the E-FAIL-030 crash,
  the fourth fully automatic run that held on a selection defect) is answered too. Every other saved universe is a row.
- A2 SAVED UNIVERSE TEXT: a saved universe (runs/<day>/TOPIC_SELECTION.json) names its transcripts by sha; their text
  lives in the shared store /home/ultron/protocol_pulse/data/editorial (not in runs/). The proof reads those records
  READ-ONLY, each hash-checked against the sha the run recorded (exactly how the repo's pipeline/backtest.py replays a
  day), plus cached embedding vectors from the same store to rebuild the DEC-13 clusters on CPU. Nothing is written
  there or anywhere in the main tree. No GPU, no Whisper, no Ollama.
- A3 "HOOK ID": read as a hook RANGE of whole sentences ([n, n] = one sentence): the existing hook budget allows 1-3
  sentences of 8-12 s (editorial_select.py:49, :52); a one-sentence-only hook would cut supply without a law saying so.
- A4 CLAIM: the model also returns `claim`, one id out of its story ids; the claim shown downstream is that sentence's
  text verbatim. Still ids only.
- A5 STAND-IN MODEL: gpt-6.1-sol (OPENAI_API_KEY read by name inside code) only for the proof; every reply recorded so
  tests replay offline. Spend guard: priced at an assumed upper bound of $15 / 1M input and $120 / 1M output tokens
  (reasoning included); model calls stop when the estimate reaches $40.

- A6 STAND-IN SUBSTITUTE: gpt-6.1-sol cannot be called (credit exhausted, the API's own error code). The order's
  intent is a stand-in for the local gemma3:27b while GPU0 is leased, so the proof uses another available frontier
  API in the same role: Gemini (GEMINI_API_KEY read by name in code; the repo's audit default model), behind the same
  Model interface, every reply recorded for offline replay, priced at an assumed upper bound of $2.50 / 1M input and
  $15 / 1M output tokens (thinking included) into the same cumulative $40 guard. The OpenAI replies already recorded
  stay as the audit trail (tests/select_by_id/fixtures/replies_superseded).
  CORRECTION (02:08): Gemini was NOT used. GEMINI_API_KEY is not defined in the permitted env file (checked by
  presence only). The substitute was claude-opus-5-5 (01:44 run), then claude-fable-5-2 from the orchestrator's 02:00
  note, with Grok on the medley key as the blind judge. gpt-6.1-sol answers again from 02:07.

## DONE (commit hashes)

- PHASE 1 DONE: d809a1f8 (pushed to origin/pp-selectid 02:53 ET Nov 12). Contents:
  - pipeline/eligibility.py and pipeline/select_by_id.py, with tests (23 + 29 + 27 cases);
  - the design doc docs/audits/SELECT_BY_ID_DESIGN.md;
  - the exact wiring patch, REQUESTS R1, `git apply --check` clean on c1451047, SMOKE PASS;
  - the proof table (above) with per-defect answers (pp-selectid_PROOF.md);
  - audit cycles 1 and 2, recorded in pp-selectid_audit/.
  The 3 Nov 6-7 rows of the column of record follow in a later commit, and do not change any answer above.

## BLOCKED

- (nothing)
