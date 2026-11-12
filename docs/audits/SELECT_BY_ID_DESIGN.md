# SELECT BY ID + ONE ELIGIBILITY PREDICATE — design (pp-selectid, 2026-11-12)

Order: orchestrator 00:32 ET Nov 12 (session pipeline_pp_selectid); addendum '22:15' item 3 (constrained selection)
and red-team batch D (one eligibility predicate). New modules only: `pipeline/eligibility.py`,
`pipeline/select_by_id.py`. The wiring into the existing pipeline is a patch for the integrator
(`docs/audits/parallel/pp-selectid_REQUESTS.md`); no existing pipeline file is edited here.

## 1. Why

Four fully automatic runs held on selection defects with one root: the editorial model WRITES text (a cluster
headline, an event description, an evidence quote) and the pipeline then tries to prove its rewrite exists in the
sources. E-FAIL-036 (caption entities: a correct quote failed), E-FAIL-037 (split Whisper tokens: a correct quote
failed), E-FAIL-038 (the claim re-read as another event, with an invented date), and the ledger pattern of
fresh_20261112_001448 / _013452: clusters that by construction hold statements from >= 2 channels ended
"coverage 1 < 2" or "currentness missing" after each channel was re-judged against the model's own rewrite. The
second root: what may be used (Bitcoin screen, freshness, partner channel, layout, stand-alone, whole sentences) is
decided in several places that disagree (section 4).

## 2. The contract (pipeline/select_by_id.py)

The model sees numbered, source-backed sentences and may answer with ids only.

| call | the model sees | it may answer |
|---|---|---|
| story | the sentences of one candidate group (a DEC-13 channel cluster), each `id \| mm:ss \| text`, under a header per video (channel, age) | `{"story": [ids], "claim": id}`: the ids of every sentence that states ONE current development, from >= 2 channels; `claim` is one of them |
| line-up | the word-timed sentences of the story's on-screen-eligible videos within 30 s of each story statement, each `id \| mm:ss \| seconds \| mark \| start \| text`, and the claim sentence | `{"hook": [a, b], "clips": [[a, b], ...]}`: ranges of consecutive whole sentences of one video each; the hook, then 2-3 clips, in play order |

Row facts shown to the line-up call (presentation only; eligibility judges every reply): mark `*` = states the story;
`+` = may join the `*` sentence next to it under D4 (within 8 s, at most two a side, refers back to it or is only an
interjection), judged against that ONE sentence so that it holds for every range keeping its `*` neighbour (D4 (a)
only gains matches as the anchor grows; test_every_plus_mark_holds_for_a_range_with_its_star_neighbour); start `H` /
`C` = the sentence may begin the hook / a clip (T7, T8). The story call marks channels that can never be on screen
("evidence only", DEC-12d). A wire group's headline is shown as a hint, never as the claim.

Rejected, never repaired (laws L-l, L-j): a reply that is not exactly one JSON object (prose, code fences, two
objects); a duplicate, missing or unknown key (a key that restates the claim in words, e.g. `headline`); an id that is
not a JSON integer (`"12"`, `12.0`, `true`) or not in the input; a range that is not `[first, last]` of consecutive
sentences of ONE video (a cross-source range, a range over a gap in the numbering, `last < first`); a story or a
line-up from one channel; an empty reply (`""`, `{}`, `{"story": []}`). A schema-valid reply must then pass
`eligibility.eligible()` on the whole selection. An invalid reply is asked again with the reason (3 attempts, as
LocalLLM.chat_json), told in the model's own ids which range broke which rule (`explain`); a decline is final
(`{"story": [], "claim": null}` / `{"hook": null, "clips": []}`: asking again would invite an invented story or
line-up); empty ranges are not a decline. Every attempt is recorded (prompt sha256, raw reply, verdict,
eligibility reasons).

Production entry: `run_pools(model, ctx, pools, words_fn, *, checks, max_story_calls)` runs the DEC-13 pools in order
(channel_clusters_48h -> channel_clusters_72h -> wire_headlines, each only when every earlier one produced nothing).
- `cluster_groups` turns the recorded cluster entries into groups, widest first (most channels; ties in clustering
  order: decision D-f).
- `wire_groups` retrieves a wire headline's chunks by the headline's own embedding (no derived query).
- Inside a pool, every group gets its story call first, up to the story-call budget. Then ONE `words_fn` brings the
  on-screen videos of all its accepted stories to sentence-ready word records. That is the existing GPU0 word pass:
  one swap per pool, as today's E5 (law L-r). Then the line-up calls run in group order, and the first accepted
  line-up wins.
- `checks` (ModelChecks) is required, so the production entry never runs without today's independent judgements.
- `to_passages` and `evidence_record` give select_passages and the story ledger their inputs.
- The wiring patch (REQUESTS R1) calls it from editorial_select._select_story.

Since the orchestrator's 02:30 order (law L-w 3), story-first is kept as a preferred package TYPE when >= 2 channels
cover one development. This contract is that type's selector, and the moments-first packager (phase 2) chooses
between types.

What leaves select_by_id is source text only: the claim is the claim sentence verbatim; every hook / clip text is its
sentences verbatim (transcript_store.read_text of the record's own words, law L-h); every time is the record's own
word timestamp. Nothing the model writes is ever matched back to a transcript, so the class behind E-FAIL-036 /
037 / 038 cannot occur (proof table: section 6).

Text the model sees: "as spoken" = `transcript_store.read_text` (law L-h: entities decoded, split Whisper tokens
read whole), neutralised by `story_semantics.quote_data` inside an untrusted-text block. Every comparison
(same-statement identity, ledger, backward references, openers, numbers) is `pipeline/canon.py` (law L-k).

Model access: `Model.complete(prompt, max_tokens, seed) -> raw text`.

`OllamaModel(story_semantics.LocalLLM)` is the production adapter:
- gemma3:27b on the GPU0 Ollama, in JSON mode at temperature 0 (story_semantics.py:190-195);
- LocalLLM's GPU0 placement guard and digest are kept; its lenient JSON repair is deliberately NOT used;
- every transport failure is a ModelError: OSError, http.client.HTTPException, or an unreadable envelope;
- a prompt whose estimate exceeds LLM_CTX minus the reply is never sent, because Ollama would drop its head, the
  instructions. Both tables also cap their rows by a character budget inside the context (`row_budget`).

`Recorder` keys every exchange by sha256(model, prompt, max_tokens, seed):
- production (`validated_only=True`, DEC-13 e / law L-l) writes a reply only after it was accepted or declined with
  every check passed;
- the proof (`validated_only=False`) keeps every reply, because the order says "record every reply for offline
  replay".

`Replay` serves recorded replies only, and tests never call out.

The proof's stand-ins (tests/select_by_id/standins.py) are recorded in every proof file:
- gpt-6.1-sol was the first; its account was out of credit 01:20-02:07 ET;
- claude-opus-5-5 was the 01:44 substitute;
- claude-fable-5-2 was the generator under the orchestrator's 02:00 note;
- the judge for ModelChecks is grok-4.20-0309-reasoning, from another vendor than the generator.

Two calls, not one. The story call needs no word timing: any transcript method works, and captions are punctuated
(median ~17 words per sentence mark on fresh_20261112_001448, none unpunctuated). The line-up call needs a
sentence-ready word record (L-e) for every on-screen sentence, so production runs its existing word pass between the
two calls, once per pool.

Independent model checks (`ModelChecks`, today's prompts and validators; audit M1 / C2) run on verbatim text only:
- `verify_support` on EVERY story sentence, with the claim as the event: SUPPORTS = same actor / action / object
  AND presented as current. The two-channel coverage therefore rests on an independent verdict per sentence, never
  on the selecting reply alone.
- `verify_reaction` (D4 c) on every non-statement sentence of a chosen range.

A negative verdict rejects the reply, which is asked again naming ids and labels only (no model or transcript text
enters a re-ask). A verdict that cannot be read is a ModelError, and nothing is selected.

## 3. The predicate (pipeline/eligibility.py)

`eligible(item, ctx) -> Result` is the one question every selection step asks. Pure: no model, no file, no network,
no clock (ctx.now is handed in). A rule it cannot measure on what it is handed fails closed (L-j); nothing
measured is never a pass (L-m).

- item: `Source` (one video), `Span` (whole sentences k0..k1 of one Source, in a role: `evidence` = a statement a
  story rests on; `hook` / `clip` = heard on screen), `Lineup` (story spans + claim, and when chosen the hook and
  clips).
- ctx: `Context(now, registry, role, story, ledger, scorer)`: the run clock (aware UTC), pipeline/channels.json,
  the role, the story statements an on-screen span must carry, the delivered-story ledger, and clip-scorer verdicts
  (only for stand_alone's one exception, below).
- Result: `ok`, `reasons` (every named blocking reason with its detail, never only the first), `facts` (measured
  either way: `layout_eligible`, `age_h`, `tier`, `duration_s`, `n_sentences`, ...), `parts` (a Lineup's per-span
  results).

Layout eligibility is measured for every item and reported as the fact `layout_eligible`; for an on-screen role it
is also the blocking reason `layout_ineligible`, so the supply DEC-12d removes can be counted.

## 4. Every eligibility rule in today's selection path

Line numbers are HEAD c1451047. "Choice" names the reason in eligibility.py; where two places disagree the stricter
is taken and the disagreement is written next to it.

### 4.1 Source

| # | rule | where today | disagreement | choice (reason) |
|---|---|---|---|---|
| S1 | partner channel: registry entry by channel_id, enabled | transcript_ingest.py:40 (`enabled` default True); editorial_select.py:614-616; run_fresh.py:257 (chosen channel must be a registry name); DEC-6 | backtest.py:122 builds a stub channel for a channel_id the registry lacks and editorial_select.py:103 then calls it layout-eligible; run_fresh.py:257 HOLDs it only after selection. A missing `enabled` reads as enabled | registry entry by channel_id AND `enabled is True` (absent = not enabled); names come from the registry (`not_partner_channel`) |
| S2 | channel identity on the text | transcript_store.py:512 (E-FAIL-030); story_semantics.py:803 | - | channel_id and channel_name both present (`no_channel_identity`) |
| S3 | no v2f material | editorial_select.py:60, :624; run_fresh.py:260, :394 | - | (`v2f_material`) |
| S4 | uploads only | transcript_ingest.py:52 (no Shorts); transcript_store.py:446-451 (live / upcoming skipped) | - | `Source.vod` (`not_vod`) |
| S5 | freshness | transcript_ingest.py:55 (`0 <= age <= 72 h`); editorial_select.py:41, :57 (48 h tier, then 72 h); :71-74 `_recency` (missing age 0.4, a future age 1.0 = freshest); :77-83 (naive time read as UTC); story_semantics.py:498-539 + :52 (stale only before now - 72 h - 7 d) | 72 h vs 72 h + 7 d grace; missing / future / timezone-less upload times admitted downstream (GPT-select F35, Grok47-select F15) | the source's own upload time, `0 <= age_h <= 72`; missing, future or timezone-less = `not_current`; fact `tier` 48h / 72h. NOTE (not changed): CONSTITUTION section 9 states a 48 h Freshness Law for the video_pipeline_v3 5-clip format; DEC-13 sets 72 h max for Pulse Check. Recorded for the integrator / PBX |
| S6 | layout | editorial_select.py:95-103 (channel_id and not has_chyron, DEC-12d); :1152 (has_chyron evidence never a clip); run_fresh.py:376-392 | - | fact `layout_eligible` always; on screen `layout_ineligible` |
| S7 | word record the sentence law can read (L-e) | transcript_store.py:404-411; editorial_select.py:865, :882; punctuation.py:33 | - | on screen: word timestamps AND (`whisper_words_punct` or no stretch needs restoration) (`not_sentence_ready`) |
| S8 | transcript identity | editorial_select.py:647-648 (sha recorded per universe video) | - | `transcript_sha256` present (`no_transcript_identity`); no tokens (`no_transcript`) |

### 4.2 Span (whole sentences of one source)

| # | rule | where today | disagreement | choice (reason) |
|---|---|---|---|---|
| T1 | whole sentences: split after a terminal mark that is not an abbreviation / '...' | sentence_law.py:96-104; editorial_select.py:151-161; transcript_store.py:359-371 (splits on any '.', abbreviations included) | transcript_store's sentence segments split 'U.S.'; the other two do not | sentence_law.is_terminal everywhere |
| T2 | starts a sentence | editorial_select.py:197-198; sentence_law.py:251-262 (a file head is a start) | select_passages windows (and frozen 5-min windows) begin mid-file, where the first word is no evidence of a sentence start | previous word terminal, or the record's first word AND `Source.file_head` (`fragment`) |
| T3 | ends a sentence | editorial_select.py:138-140, :243, :341, :554 | - | last word terminal (`fragment`) |
| T4 | a statement, not a question | editorial_select.py:138-140 (windows); edl_rules.py:88 (R1, hook only) | R1 checks the hook only | every span, evidence included (a question states no development) (`not_statement`) |
| T5 | punctuated stretch | sentence_law.py:107-111, :281-283; E-FAIL-013 | - | both boundaries in a punctuated stretch (`unpunctuated`) |
| T6 | instruction-shaped text | story_semantics.py:337-356; editorial_select.py:353, :428 | - | (`injection_markers`) |
| T7 | first word capital or digit | editorial_select.py:199-201 | - | on screen (`start_case`) |
| T8 | opener | editorial_select.py:127, :202-204 (selection: any window opening on a continuation word is rejected); :208-218 (selection: the hook opener only); stand_alone.py:40-57 + run_fresh.py:342-370 (validate: hook pronoun / conjunction / reply word; a clip's conjunction or reply word passes if the clip scorer affirms) | a clip opening on a conjunction: rejected at selection, accepted at validate with the scorer; a clip opening on a reply word: passes selection, needs the scorer at validate | LAW L-o (01:50): a conjunction opener is a TARGET (fact `targets_missed`, never a reason); the rules that stay hard apply to the first word AFTER any leading conjunctions (audit C2: 'And it ...' is a pronoun hook): the hook's pronoun / reply word rejected; a clip's reply word only with a scorer verdict in ctx.scorer (score >= 3.5, fault != starts_mid_thought), else fail closed (`opener`). R1 runs no scorer, so every reply-word clip opener fails closed (section 7). Downstream stand_alone at validate is not yet aligned with L-o (REQUESTS R6) |
| T9 | 1-3 sentences, interjection-only sentences transparent | editorial_select.py:52, :143-148, :237 | - | on screen (`too_many_sentences`, `no_content`) |
| T10 | duration of the span's own words | editorial_select.py:49-50 (hook 8-12 s, clip 12-20 s); select_passages.py:333 (E-FAIL-012); edl_rules.py:229-232 (R5 8-25 s) | R5 8-25 s vs 12-20 s | LAW L-o: hook 8-12 s / clip 12-20 s are TARGETS measured on word timestamps (fact `duration_s`, a miss in `targets_missed`); only an unmeasured duration fails (`duration`: the runtime needs it, L-m). The one hard length rule is the line-up's runtime (L6). edl_rules R5 / select_passages:333 still apply windows downstream until wired (REQUESTS R6) |
| T11 | names the subject (Bitcoin) | stand_alone.py:64-96 (hook must; a clip may instead complete the previous claim at validate); editorial_select.py:208-218 (selection: a clip must name it); editorial_select.py:59 (`bitcoins?\|btcs?` regex) vs stand_alone.py:27 + canon tokens | validate vs selection on clips; the regex and the token test differ on written forms ('bitcoin.com': regex yes, tokens no) | every on-screen span names Bitcoin by BOTH tests (`no_bitcoin`) |
| T12 | the hook's lead-in | sentence_law.py:57 (HEAD_LEAD_MIN_S 80 ms: file head and the hook), :300 (file-head pad); DEC-10 in-file lead 0 ms | selection can choose a hook G17a must fail (GPT-cut F12) | a hook needs >= 80 ms of transcript gap before its first word, or the file head (where the D1 pad applies) (`hook_lead`) |
| T14 | a statement has words enough to be one | story_semantics.py:370-372 (quote_in: a verbatim quote counts only with >= 5 canonical tokens) | - | every span, evidence included (`too_short`); and a sentence STATES a story statement only with a run of 5 consecutive canonical tokens of it (or all of a shorter one): `eligibility.states`, asymmetric, because the symmetric same-statement rule lets 'Right.' match any statement holding 'right' (found by the stand-in on fresh_20261112_013452) |
| T13 | anchored on the story + D4 adjacency | editorial_select.py:221-246 (window = the sentences holding the verified quote); :249-344; :366-456 (D4: (a) backward reference / shared entity / shared number or interjection-only, (b) within 8 s, cap 2 per direction, (c) model verify_reaction) | (a) reads the derived query's entity names and action / object nouns, which the id contract does not have | on screen: the span holds >= 1 story statement (same video, >= 5 shared consecutive canon tokens, within 30 s of the statement's own time; an unknown time never matches: L-m, audit C2) (`no_story_statement`); every other sentence, BETWEEN two statements included (audit U1), passes (a), (b), cap (`adjacent_not_admissible`). (a)'s anchor is the STATEMENT sentences only, never the sentence being judged (audit C2: with the whole window as anchor an inner sentence matched its own names); its entity names: the claim sentence's proper names, said in the anchor (parity-tested against today's function given those names); the 'event nouns' half is dropped (stricter). (c) is ModelChecks.lineup (section 2) |

### 4.3 Story (Lineup.story + claim)

| # | rule | where today | choice (reason) |
|---|---|---|---|
| G1 | >= 2 independent channels | editorial_select.py:47, :1036; DEC-13 | (`story_one_channel`) |
| G2 | Bitcoin screen: >= 2 channels with a Bitcoin statement in the tier | editorial_select.py:59, :989-992 (chunk granularity) | sentence granularity, both Bitcoin tests (`story_bitcoin_screen`); fact `tier` |
| G3 | >= 2 layout-eligible channels | editorial_select.py:48, :1038-1040 | (`story_layout_channels`) |
| G4 | each member a valid statement | the evidence quote checks: story_semantics.py:370-372, :748-767 | every member eligible as `evidence` (`story_member`) |
| G5 | the claim | label_cluster headline (model text, story_semantics.py:772-862) / derive_story_query (:466-480) | the claim is one story sentence verbatim (`claim_not_in_story`), names Bitcoin (`claim_no_bitcoin`; this replaces BTC_RELEVANCE_MIN, editorial_select.py:44, :763, a model rating of the model's own text) and stands on its own like a hook, because it is read alone downstream as the headline: lower-case start, or a pronoun / reply word (after any leading conjunction) = `claim_not_standalone` (found on fresh_20261106_213852: "But that said, like I think ..." fails on 'that'); a leading conjunction alone is a target under L-o (`targets_missed`; audit C2) |
| G6 | not already delivered (DEC-9) | editorial_select.py:845-854; story_ledger.py:24-32 | a member that is the same statement (same video, >= 5 shared consecutive canon tokens) as delivered evidence (`already_delivered`) |

### 4.4 Line-up

| # | rule | where today | disagreement | choice (reason) |
|---|---|---|---|---|
| L1 | shape | editorial_select.py:54 (3 clips max), :1302, :1307; select_passages.py:159, :183, :200, :360 (success with a hook + 1 clip: GPT-select F08); edl_rules.py:220 (R5 >= 2 clips) | 1 clip passes select_passages | hook + 2-3 clips (`lineup_shape`) |
| L2 | channels | editorial_select.py:1302, :1307 (>= 2 counting the hook); edl_rules.py:237 (R5: >= 2 among the clips) | hook counted or not | >= 2 among the clips (`lineup_channels`) |
| L3 | no overlap | editorial_select.py:1290 (any); select_passages.py:287 (any); edl_rules.py:110 (> 1.0 s) | 1.0 s tolerance in R2 | any overlap in one video (`overlap`) |
| L4 | <= 2 ranges per video | editorial_select.py:55, :1292; select_passages.py:289 | - | (`per_video`) |
| L5 | <= 2 clips per channel | editorial_select.py:1291; select_passages.py:291 | - | (`per_channel`) |
| L6 | runtime | LAW L-o (01:50): "the only hard duration rule is the format: total runtime 60-70 s"; checked before render where the line-up is chosen | - | estimate = the line-up's word spans + `TAIL_S` 14.30 s (the approved preview's final 71.08 s minus its four word spans 56.78 s; L-o's own figure, 12.91 s of non-passage time, is the same measurement on the final's passage time), inside 60-70 s; an unmeasured span fails (`runtime`). One calibration: REQUESTS R6 asks the final to be measured too |
| L7 | (pending law L-u, orchestrator 02:30) | - | - | ONE clip per channel per video and <= 20 s per source video, for every package type. Not applied in this audited predicate (L5 = today's 2); the integrator writes L-u and phase 2's packager applies it to the story-first type too |

## 5. Model judgements that are not in the pure predicate

Listed so nothing is lost; none of them writes text that becomes a claim any more.

| judgement | today | under select_by_id |
|---|---|---|
| the same current development across channels | adjudicate (CURRENT_EVENT + verbatim quote + chunk id) + verify_support (SUPPORTS) per video against the model-written event | ModelChecks.story: today's verify_support on EVERY story sentence with the CLAIM (verbatim, L-i) as the event; any non-SUPPORTS rejects the reply (asked again, ids only); unreadable = ModelError (audit C2) |
| currentness | transcript_currentness over adjudicated verdicts | the same verify_support (`presented_as` exactly 'current'); source age is deterministic (S5) |
| Bitcoin relevance / importance | derive_story_query ratings (BTC_RELEVANCE_MIN 3) | the claim must name Bitcoin (G5); groups are offered widest first (D-f) |
| clip quality floors | rate_passages: hook >= 4.0, clip >= 3.5 | superseded by law L-o (score floors are targets that rank); not run |
| D4 (c) reaction / consequence | verify_reaction per added sentence | ModelChecks.lineup: verify_reaction on every non-statement, non-interjection sentence of each chosen range |
| editorial review / gate, stand-alone at validate | editorial_review + editorial_gate; stand_alone.check_edl | unchanged (downstream of the EDL) |
| context integrity (law L-s, orchestrator 02:30) | none | not in this contract: a verbatim whole sentence can still misrepresent its speaker once lifted; the L-s gate (phase 2) covers every package type, story-first included |

## 6. Holding runs: would the defect have been possible under this contract?

The per-defect answers and the proof's results are in docs/audits/parallel/pp-selectid_PROOF.md. The generated table
is in pp-selectid_PROOF_TABLE.md, copied to STATE.

In short: E-FAIL-030 (missing identity), 033 (unpunctuated decode), 034 (headline-shaped candidates), 036 / 037
(entities, split tokens) and 038 (the claim re-read as another event) are not possible under this contract.

The layout hold of fresh_20261112_013452 becomes a named deterministic refusal.

E-FAIL-043's class, a strict same-event judgement and a line-up recall miss, is still possible and is made visible:
- The column of record (judge at temperature 0, production parity) accepted the preview's story.
- The generator then declined the line-up, although a line-up that passes our rules exists in the same rows.
- Most other clusters stop at the per-sentence check.

## 7. Known limits (reported, not hidden)

- A wrong grouping is still a model judgement: the story call can put two sentences about different events in one
  story. The contract makes such an error visible (every member is a verbatim source sentence, the claim is one of
  them), never laundered through a rewrite; it does not make it impossible.
- The hook lead (T12) reads the transcript gap; Whisper starts words inside pauses (E-FAIL-005), so G17a on the audio
  stays the authority; T12 only stops selection from choosing a hook the gate must fail.
- The line-up needs word timing. In a CPU-only replay, a story whose layout-eligible videos have no sentence-ready
  word record cannot get a line-up (production would run its word pass); the proof reports those rows as such.
- The proof never ran gemma3:27b (GPU0 is leased to the live run; this session uses no GPU). Its replies came from
  frontier stand-ins in JSON mode. A gemma3:27b shadow run over the saved universes is the integrator's prerequisite
  before R1 is enabled (REQUESTS R6): the strict parser (no repair) could hold every run if gemma's JSON mode emits
  anything but one object.
- `TAIL_S` is one calibration from a four-segment final. A hook + 2 clips line-up has fewer transitions, so its real
  non-passage time may be smaller than 14.30 s, and the estimate could fail open at the low edge. REQUESTS R6 asks for
  the final's runtime to be measured as well.
- The approved preview against L-o: its trio without Bitcoin Magazine estimates ~54.4 s (< 60 s), and its four
  segments ran 71.08 s on the final (> 70 s). L-o leaves a tolerance to PBX. The must-pass test accepts a
  four-segment line-up that passes our rules, from the same sources, and says so.
- DEC-9 identity is per statement (parity with story_ledger.delivered_match). A neighbouring sentence of a delivered
  event in another video is not caught. Novelty under L-p / L-q is the orchestrator's open question.
- `states()` maps a story statement from the story call's record onto the word record's sentence that repeats its
  5-token run within 30 s. A word-record sentence that repeats the run AND adds more words counts as core, so it is
  exempt from D4 (c).
- A reply-word clip opener needs a clip-scorer verdict that R1 never runs (L-o retired the floors), so every
  reply-word clip opener fails closed.
- Law L-u (orchestrator 02:30: one clip per channel, <= 20 s per source video) and L-s (context integrity) postdate
  this audited contract. They apply to the story-first package type through the phase-2 packager and gates.
