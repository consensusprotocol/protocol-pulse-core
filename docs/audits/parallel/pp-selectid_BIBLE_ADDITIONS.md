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

### E-FAIL-PS13 (this session's own tooling, 03:22 ET): an unquoted heredoc executed the backtick spans of a document
A shell heredoc with an unquoted delimiter (`<<EOF`) performs command substitution on its body. A Markdown section
being written through it held inline code in backticks: a file path, a command line with `--pinned`, a `git apply
--check`. Bash tried to run each of them. A git command hung on its input until the session's timeout and was
stopped. Verified afterwards:
- no run_fresh process ran;
- no run directory appeared, in the worktree or in the main tree;
- no tracked file changed.

**Rule:** any heredoc that carries document text uses a quoted delimiter (`<<'EOF'`), with values passed through the
environment or argv, never interpolated.

### E-FAIL-PS14 (measured 03:20-04:05 ET, tonight's universe): a VO that makes a point collides with three gates built for VO that only introduces
The orchestrator's 03:40 review asked for angle-led packages ("the VO makes a point"). Three integrity checks, each
correct in its own terms, then refused every angle on tonight's universe.

1. **The fidelity verdict supported a claim from ONE segment only.** A point drawn from two clips ("past gains don't
   erase risk": one clip's move plus another's rates) had no single supporting segment, so it was "uncertain" or "no".
   **Fix:** a claim may cite several segments, each with words that code verifies as verbatim. The judge says yes only
   if those words together state the claim, adding nothing.
2. **Step B (viewer takeaway) read independent compatible views as "agreeing".** Three credited speakers each making
   their own point on one subject were flagged FALSE_RELATION. L-s forbids an implied relation between speakers (one
   answering, rebutting or agreeing WITH another, or one conversation), not two attributed views on one point. The
   orchestrator's own example angle (Ammous / What Bitcoin Did / Livera) is exactly that.
   **Fix:** step B asks the relation question as L-s states it.
3. **A context failure caused by the VO's framing (NOT_ENTAILED, STRONGER, FALSE_RELATION) dropped the MOMENT.** The
   angle then ran out of moments.
   **Fix:** a VO-dependent context failure goes back to the writer with its reason, within the 3-rewrite budget. Only
   a clip's own context (step A) drops it.

None of the three loosens a rule. Each now asks what the law asks, with the same strictness. The deterministic NAME
and NUMBER rules also produced false rejects on angle VO ('Past', 'Beyond', a Title Case title, 'one thing'), fixed
with evidence in MOMENTS_FIRST_DESIGN section 4b.

### E-FAIL-PS15 (audit p2 cycle 1, unanimous): a gate's verdict that the artefact asserts instead of carries
package_pin wrote `"vo_fidelity_ok": True, "context_integrity_ok": True` as literals. R7 then tested those flags for
truthiness. An ungated, hand-edited or failed package would have rendered as "gated".
**Rule:** the artefact carries a fixed GATE INVENTORY. Each row is exactly "PASS", with who measured it and "replayed":
false. The inventory is SEALED with the gated bytes (package_pin.seal), and every consumer recomputes the seal. A row
that is missing, "FAIL" or "NOT RUN" refuses the pin.

### E-FAIL-PS16 (audit p2 cycle 1, 3 of 4): a verdict that may answer with nothing passes on nothing
`{"claims": []}` passed the blind fidelity verdict, and so did a verdict covering one line of four. Step B passed with
`"relations": []`.
**Rule:** the code requires COVERAGE:
- every sentence of every line is covered by a claim whose words are the line's own;
- every pair of clips has exactly one relation;
- every segment has a second-pass result with a measured speaker. "Not measured" (None) never passes.

### E-FAIL-PS17 (tonight 05:45-06:30 ET, the orchestrator's rulings 3, 5, 6): a model verdict that names no words is a note, not a failure
Several false rejects came from a judge disagreeing with another model's paraphrase, with no word of the video or of
the context to point at:
- STRONGER: A "likely" against B "certain";
- NOT_ENTAILED: two summaries of different scope;
- RETRACTION: a consistent later elaboration;
- a package "adding" to a clip when B was the clip's own words.

**Rule:** a context failure that blames the video must quote the video's own words; one that blames the context must
quote the context's own words, outside the clip. Code checks each quote:
- `raising_words` / `added_by`: verbatim in the VO, title or caption; `added_by` must also name the speaker's show;
- `dropped_limit`: verbatim in the window, outside the selection.

Unquoted, it is a NOTE.
- An "uncertain" still fails (L-m).
- After each change, the exam's 41 must-fail context cases are re-run: 41/41 rejected.
- One intermediate encoding let two title-thesis cases through. The exemption had been written wider than the ruling's
  own words ("the clip alone reads as CERTAIN"), so encode the ruling's words exactly.

### E-FAIL-PS18 (tonight 05:40 ET): the gates judged a play order the renderer does not use
The renderers play hook -> VO intro -> clip 1 -> bridge -> ... -> shout-out (render16.py:306-334,
render_vertical.py:853-880). The intro is heard AFTER the hook. The packager's view for step B and coherence put the
intro before the hook.
**Rule:** every gate that judges "the video as a viewer meets it" builds that view from the renderer's own segment
order, and is re-checked whenever the renderer changes.

### E-FAIL-PS19 (tonight 05:45 ET, this session's own defect): a second-pass comparison over the padded window
The L-v 2 comparison took the second transcript of the whole padded audio window (selection +/- 1.5 s). It also
treated sentence-initial capitals as names. So "Your", "Um" and an extra "not" from outside the clip failed two clean
clips.
**Rule:** compare only the words whose timing lies inside the selection, in BOTH directions, with counts. A name is a
capitalised token that is not an English word.

### E-FAIL-PS20 (tonight 05:41 ET): a factory rule outside the gates (edl_rules R4) would have HELD every host-VO package
R4 (VO <= 25 % of clips + VO; one bridge per channel transition) runs on pinned runs at validate. The moments-first VO
the orchestrator wrote at 05:35 was 38 %.
**Rule:** the packager mirrors every downstream hard rule that the package's bytes can fail (runtime, R4, the R7 shape)
and checks them for free, before any paid verdict. The integrator's R4 for moments (a5ec0f17) is mirrored: VO <= 40 %
of the total runtime, one line per slot.
