# pp-selectid audit — cycle 1 consensus (synthesis by the pp-selectid session, 2026-11-12 ~02:10 ET)

Reviewers (substitutes, see STATE: no GEMINI / XAI key in the permitted env file, OpenAI out of credit):
claude-fable-5-2 66/100, claude-opus-5-5 66/100, claude-sonnet-5-5 72/100; all NOT READY. Package: the repo's
utils/cross_llm_audit.py build_audit_package on STEP.diff (213,853 bytes, base c1451047). All three found NO path by
which a non-id reply is accepted and NO path from model text to the claim / segments / passages / ledger.

A new law arrived after cycle 1 and is applied with the fixes: L-o (PBX 2026-11-12 01:50): duration windows (hook
8-12 s, clip 12-20 s), score floors and conjunction openers are TARGETS that rank, never reject; the hard length rule
is total runtime 60-70 s.

## Unanimous (3/3): implemented

| # | finding | fix |
|---|---|---|
| U1 | a non-statement sentence BETWEEN two story statements skipped D4 (a)/(b) (Fable 3, Opus 1, Sonnet 1) | eligibility._anchor judges every inner non-statement sentence: D4 (a) against the statements, (b) from either neighbouring statement; interjections transparent |
| U2 | a missing word time read as 0 passed the hook lead / D4 (b) (Fable 7, Opus 6, Sonnet 2) | `_time()`: a missing time is no measurement -> hook_lead / adjacent_not_admissible / duration "not measured" (test_a_missing_word_time_is_no_measurement) |
| U3 | R1 patch: clusters after the winner / in unevaluated pools get no `gate`; gate text read a `why` that `to_dict` lacks; INFRA_HOLD lost (Fable Q4, Opus 5, Sonnet 5) | Outcome.to_dict carries `why`; the patch writes a gate on EVERY screened cluster ("not evaluated: ..."), the cluster's claim, and the HOLD (infrastructure) decision when a GPU0 release / word pass failed |
| U4 | tests that pass vacuously (Fable 8, Opus 7, Sonnet 8) | each bad reply asserts its own rejection reason; the duplicate-key case uses valid ids; the disabled-partner assertion is unconditional; the smoke test asserts the held run's reason and runs the Recorder branch (ScriptedLLM gets a digest) |

## Majority (2/3): implemented unless superseded

| # | finding | disposition |
|---|---|---|
| M1 | R1 drops today's model gates: clip-scorer floors, verify_support (presented as current), verify_reaction (D4 c) (Fable 1, Opus 2) | FLOORS: superseded by law L-o (floors rank, never reject; select_by_id has a single model-chosen line-up, nothing to rank). verify_support on the claim and verify_reaction on every non-statement sentence of a chosen range: IMPLEMENTED as ModelChecks inside the contract (today's prompts and validators, story_semantics, on verbatim text; a negative verdict = Rejected and re-asked; an inconclusive check = model_error, nothing selected) and wired in R1 |
| M2 | OllamaModel transport errors escape; L.stop / E.close not in a finally (Opus 3, Sonnet 4) | adapter maps transport errors to ModelError (the GPU0 guard still propagates; test); the patch closes the LLM and the embedder in a finally |
| M3 | Source defaults assert what nobody checked: file_head True, vod True (Fable 7, Sonnet 3) | both default to "not established" and fail closed; sources_from_universe / the proof assert them for full-video store records of the universe (Shorts and live streams are excluded upstream: transcript_ingest.py:52, transcript_store.py:446) |
| M4 | the line-up input has no row cap (Fable 5, Sonnet 7) | LINEUP_MAX_ROWS, stars and their nearest neighbours kept first |

## Unique: evaluated one by one

| # | finding | disposition |
|---|---|---|
| F2 | Recorder caches raw replies before validation and ignores the seed: a re-ask with the same reason gets the cached invalid reply (Fable, HIGH) | IMPLEMENTED: the key includes the seed (each attempt is its own exchange); an empty reply is never cached; every served reply is validated by _ask as any reply (L-l) |
| F4 | `already_delivered` is re-asked, so a retry can pick neighbouring sentences of the same delivered event (Fable) | IMPLEMENTED: already_delivered is final for the group (Declined), as DEC-9 says the event is never selected again |
| F5 | `states` stars a sentence twenty minutes away that shares five tokens with a statement (Fable) | IMPLEMENTED: a star / core sentence must also lie within LINEUP_PAD_S (30 s) of the statement's own time when both times are known |
| F6 | `event_names` takes the claim's sentence-initial word ('As of this morning, ...' -> 'As') (Fable) | IMPLEMENTED: the first word counts only when it names Bitcoin or recurs capitalised later in the claim |
| O-BTC | BTC_RELEVANCE_MIN dropped (Opus) | NOT taken: that gate rated the MODEL-DERIVED event's relevance; the id contract has no derived event, and its claim must name Bitcoin by both deterministic tests (G5) |
| O8 | ledger tokens of entries written before canon (Opus) | IMPLEMENTED: a ledger statement is re-canonicalised from its quote |
| O-ctx | the cache key omits the context size (Opus note) | IMPLEMENTED: OllamaModel's name carries the model, its digest and LLM_CTX |
| X | `registry` / `os` undefined in the patched function (Opus, Sonnet: "cannot confirm") | REFUTED: editorial_select.py:612-613 `with open(CHANNELS_PATH) as f: registry = json.load(f)` inside _select_story; :23 `import os` |
| X2 | `u["_rec"]` must exist (Fable: unverifiable) | REFUTED: editorial_select.py:642-648 every universe entry carries `_rec` |
| X3 | the proof's re-check runs the same predicate on the same objects (Fable) | ACCEPTED as stated (it is the same predicate on fresh Context); the independent second angle is the resolution check (every id re-read from its record by sha, words compared) |
| X4 | proof stand-in is not gemma3:27b (Fable) | ACCEPTED as a limit (the order forbids Ollama on the leased GPU0); recorded in the design doc |

## Law L-o (applied with the fixes)

Hook / clip durations and conjunction openers become targets (`facts.targets_missed`, ranking only); the line-up's
estimated runtime (segments' word spans + 14.30 s measured on the approved preview: finals 71.08 s minus its four
word spans 56.78 s) must lie in 60-70 s (`runtime`, hard). Pronoun / reply-word openers are not named by L-o and stay
hard. Measured consequence: the approved preview's DataDash / Natalie Brunell / Yahoo Finance trio (40.12 s of word
spans) estimates 54.4 s and now fails `runtime`; its fourth segment (Bitcoin Magazine) is excluded by DEC-12d.
