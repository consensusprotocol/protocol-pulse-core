# pp-selectid — BIBLE ADDITIONS (for docs/QWEN_CONTEXT_BIBLE.md; the integrator numbers and folds them)

### E-FAIL-PS1: A replay read a WINDOW transcript as full-video word timing
**Evidence:** pipeline/backtest.py `_run_transcript` (offline_words' second source) returns the first
`runs/*/transcripts/<video>.json` it finds as a full-video word record. Those files are select_passages' transcripts
of a DOWNLOADED WINDOW (`_download_window`, dl_start = round(start - 15 s)): runs/pinned_20261110_103950 has Yahoo
Finance 36HPi9UZPOc as a 49 s window at offset 23.38 s, Natalie Brunell lusJ1m-J0Mc 41 s at 58.63 s, Bitcoin Magazine
jbDqdLytkNM 43 s at 123.19 s (each EDL's `source_window_offset_s`). Anchoring a full-video quote time in window time
misses the quote ("verified quote not found in word timestamps") or anchors in the wrong place, so the backtest can
understate selector recall or report a window the live run would not cut.
**Fix:** REQUESTS R4 (a word record for a replay is a full-video store record; a run transcript only with its EDL
offset added, else none). **Detection:** a run transcript's duration vs the video's; the EDL offset of that video.

### E-FAIL-PS2: Porting a rule that read a model-derived field changes the rule unless the field is replaced
**Evidence:** D4 (a) (editorial_select.backward_reference) takes the event's entity names from the derived query
(`q["entities"]`). The id contract has no derived query; the first port dropped those names, which made (a) stricter
than today's and refused the approved preview's Natalie Brunell clip on the stand-in's first real reply.
**Fix:** the event's names come from the claim sentence (the event stated in its source's own words), said in the
anchor, as today's names had to be (eligibility.event_names / _anchor_entities); the 'event nouns' half (the query's
action / object phrases) stays dropped (stricter). **Detection:** tests/eligibility TestParity
test_d4_entity_half_with_the_claims_names_answers_as_today_with_those_names (today's function given those names
answers exactly as the port).

### E-FAIL-PS3: A retry reason must speak the model's own ids
**Evidence:** the first stand-in line-up retries were told "prev sentence 13 starts 9.62 s from the statement": 13 is
an internal sentence index; the model sees row ids. It repeated the same reply (attempts 1 and 3 identical).
**Fix:** select_by_id.explain(): every rejected part named by the model's own range ([12, 14]) and a rule it can act
on. **Detection:** test_select_by_id test_with_one_marked_sentence_the_unreferenced_neighbours_fail_d4 (the message
names `clip_01 [a, b]`).

### E-FAIL-PS4: A hint shown to the model must never be a promise the judge then breaks
**Evidence:** the line-up rows' '+' ("may join the * sentence next to it") was first computed against the whole run
of * rows; a range keeping only part of the run anchors on less text, and D4 (a) then refused the '+' rows (Natalie
Brunell: 'U.S. Bitcoin ETFs had about $1.3 billion ...' joins 'Bitcoin also wasn't spared ... It went from above
$81,000 ...' but not 'It went from above $81,000 ...' alone).
**Fix:** '+' is judged against the ONE * sentence it extends; D4 (a) only gains matches as the anchor grows, so a '+'
holds for every range that keeps its * neighbour. **Detection:** test_select_by_id
test_every_plus_mark_holds_for_a_range_with_its_star_neighbour.

### NOTE-PS5 (measured, not changed): today's whole-record L-e rule refuses a record for one stretch far from a clip
transcript_store.sentence_ready (punctuation.needs_restoration over every word) refuses the protected preview's
Bitcoin Magazine window transcript (2,159 words) for ONE word at 598.3 s that sits in an unpunctuated stretch,
570 s after the approved clip (14.68-31.34 s). The sentence law needs the clip's own boundaries punctuated
(sentence_law.is_punctuated, which eligibility checks per span, rule T5); the whole-record rule additionally removes
clean clips from supply. Kept (fail closed; it is today's law); a decision for the integrator.

### NOTE-PS6 (measured, not changed): the approved Natalie Brunell clip is out of reach of today's D4 (a)
'It went from above $81,000 after the election to below $75,000 by the weekend. U.S. Bitcoin ETFs had about $1.3
billion in net outflows just last week. And Bitcoin really hasn't participated in the Monday rally.' (PBX-approved,
L-d): with only its first sentence as the statement, the next two carry no back-reference, shared name or number
that the anchor says, so today's auto path (and select_by_id) cannot build it (today's auto window stopped at 7.15 s,
DoD 17:34). It is reachable when the story call marks all three as statements of the development. Whether a
consequence sentence must back-refer (D4 a) or may stand on naming the story's subject is a decision for the
integrator / PBX.

### E-FAIL-PS7: A D4 anchor that contains the sentence it judges admits that sentence on its own words
**Evidence:** audit cycle 2, fable A N1: eligibility._anchor's anchor for a sentence BETWEEN two story statements was
the whole token range from the first to the last statement, so it contained the inner sentence. The sentence's own
capitalised words became "anchor entities" and its own numbers "shared numbers". '[*, "Anyway, Solana looks great to me
right now honestly.", *]' passed D4 (a) on 'Anyway' / 'Solana'; a neighbour outside could match on an inner sentence's
name too.
**Fix:** the anchor is the statement sentences only (" ".join of the core), as select_by_id.ModelChecks.lineup already
built it. **Detection:** test_eligibility test_an_inner_sentence_between_two_statements_meets_d4 (fails on the pre-fix
code: scratchpad old_code_check.py).

### E-FAIL-PS8: "Two channels state one development" was attested by the reply that chose it
**Evidence:** audit cycle 2, raised by all three Claude reviewers of chunk A and by fable / sonnet on chunk B. The
id contract's story call names the story's sentences, and the predicate counted channels and Bitcoin mentions. The one
independent check ran verify_support on the claim against ITSELF, where same-actor-action-object is true by
construction. Channel B's sentence was never checked against the claim, although today's adjudicate checked every
video. Two unrelated Bitcoin sentences from two channels formed a "corroborated" story.
**Fix:** select_by_id.ModelChecks.story(claim, members): verify_support on EVERY story sentence with the claim as the
event; any non-SUPPORTS rejects the reply (asked again, naming the ids). **Detection:** test_select_by_id
test_model_checks_keep_todays_judgements_on_verbatim_text (a TOPIC_ONLY second channel is rejected by id); smoke
asserts one verdict per story sentence.

### E-FAIL-PS9: "An unknown time does not restrict" is a pass on nothing measured
**Evidence:** audit cycle 2, fable / opus / sonnet: eligibility.near() returned True when a time was missing, so a
sentence counted as a story statement (core, exempt from D4) on an unmeasured position. select_by_id.row_marks read
`start or 0`. `_time` accepted NaN, which compares False with everything, so a NaN gap passed the hook-lead and
D4 (b) rules.
**Fix:** near() is False on any unknown time; `_time` keeps finite numbers only; row_marks shows no '+' without times
(law L-m). **Detection:** test_eligibility test_a_non_finite_time_is_no_measurement_and_never_near.

### E-FAIL-PS10: An audit tool that drops large files audits nothing, silently
**Evidence:** utils/cross_llm_audit.py builds its package from the named files but skips any file >= 220,000 bytes
without an error. pp-selectid's fixed diff was 247,891 bytes, so a package naming it would have carried no code
while the reviewers still answered.
**Fix (this session):** the diff was split into chunks < 220,000 bytes, and the runner asserts that the package
contains the chunk's "### File:" section before any call. **For the integrator:** make the tool fail loudly on a
skipped file.

### NOTE-PS11 (measured): the tool's cycle-2 prompt hides each reviewer's own cycle-1 text
build_cycle2_prompt cuts each cycle-1 output to 5,000 characters and the consensus to 3,000. It lists every output
under "WHAT THE OTHER MODELS SAID" after a "YOUR CYCLE 1 OUTPUT ... [See below]" placeholder. All three Claude
reviewers of cycle 2 reported that their own cycle-1 text was missing; it was present, truncated, among the others.
Score comparisons across cycles are therefore unreliable as the tool stands.

### NOTE-PS12 (measured 03:06 ET, tonight's first package attempts): Step A read a dummy "it" and a generic "we" as referents outside the clip
The context-integrity step A (grok-4.20-0309-reasoning, temperature 0) marked two referents as outside the selection:
- What Bitcoin Did's "It's not Bitcoin that's getting hacked. It's other intermediaries.": the "It" of the cleft
  construction, "referring" to "what is getting hacked", which the clip itself says;
- Natalie Brunell's "we are going to have a new internet": "we" read as "humanity / society".

Both are false rejects of law L-s's referent rule. A cleft "it" and a generic "we" point at nothing outside the clip.
Step A's instruction now says so explicitly. A referent counts as inside when the selected words themselves identify
it. Real unresolved referents are unchanged: they still fail, and the exam (pipeline_pp_tests) measures both
directions. The same attempt CORRECTLY rejected Simply Bitcoin's "Five years after Bitcoin peaked at 69,000, Bitcoin
is up 6%. Welcome to November." as sarcastic, not an own sincere assertion.
