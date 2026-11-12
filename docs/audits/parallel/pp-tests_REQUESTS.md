# pp-tests REQUESTS — defects the adversarial wall exposed (for the integrator, tmux pipeline_pp_dod)

Session pipeline_pp_tests, branch `pp-tests`, worktree `/home/ultron/worktrees/pp-tests`. I write tests only; every
defect below is pinned by a test marked `xfail(strict=True)` that FAILS today for exactly this reason (each one was
re-run with `--runxfail` and its assertion read). When a fix lands, that test XPASSes, strict turns it into a
failure: that is the signal to remove the mark. File paths are relative to the repo root.

Priority (final audit round, three models, M1): R-09 and R-10 first: a stale download or transcript silently
supplies a clip the editor never verified (cache poisoning), and nothing downstream measures provenance.

How the pins stay honest when a fix lands (audit A, frontier review): every strict xfail is
`raises=AssertionError`, and every precondition of a test (its fixtures, a control inside it) is `pytest.fail`
(adv_helpers.control), never `assert`: a crash, a renamed field or a fixture broken by a fix shows as FAILED / ERROR,
never as the pinned defect. The fixtures already write the provenance records three fixes below propose (R-09: a
`sources/<vid>.section.json` download record; R-10: `media_sha256` in each transcript; R-12: `edl.json` in
`GATE_REPORT.measured_files`), so a fix implemented with exactly those names keeps every control valid; a fix that
stores them differently must update `adv_helpers.write_section` / `write_source` / `release_run` in the same change
(the controls then fail loudly until it does).

Note for the qa_gates.py items (R-07, R-08, R-13, R-20, R-21): LAW 24 says segment_v1 scripts are not modified and
are patched from pipeline/; qa_gates.py has nevertheless carried the DEC-1 / DEC-12 / L-g changes. Where the fix
lives (qa_gates.py itself or a wrapper in pipeline/gates.py) is the integrator's call; the tests call the public
qa_gates functions either way.

| id | finding | file : function | pinned by (tests/adversarial/...) |
|---|---|---|---|
| R-01 | PP-01 (new) | pipeline/canon.py : canon | test_f1 TestCanonicalForm::test_idempotent_on_adjacent_spoken_numbers |
| R-02 | Grok47-select F4 | pipeline/story_semantics.py : quote_in | test_f1 TestQuoteVerification::test_a_quote_never_matches_inside_a_longer_word_or_number |
| R-03 | Grok47-select F19 | pipeline/story_semantics.py : quote_in | test_f1 TestQuoteVerification::test_a_quote_never_straddles_two_excerpts |
| R-04 | GPT-select F05 | pipeline/story_semantics.py : adjudicate | test_f1 TestQuoteVerification::test_adjudicate_counts_a_quote_only_with_the_chunk_that_says_it |
| R-05 | GPT-select F04, GPT-cut F06 | pipeline/editorial_select.py : align_quote; pipeline/sentence_law.py : anchor | test_f1 TestSelectionAnchors (2 tests) |
| R-06 | GPT-gates F17 (Claude-gates T9) | pipeline/gates.py : spoken_channels | test_f1 TestSignoffNames::test_a_different_channel_variant_is_not_the_credited_channel (4) |
| R-07 | GPT-gates F15 | segment_v1/qa_gates.py : _g3b_match | test_f1 TestG3b::test_a_longer_word_containing_the_last_word_is_a_different_word |
| R-08 | GPT-gates F16, Claude-gates T2 | segment_v1/qa_gates.py : gate_g3b (_leak) | test_f1 TestG3b::test_a_next_word_equal_to_the_last_word_still_leaks |
| R-09 | GPT-select F09 | pipeline/select_passages.py : _download_window | test_f2 TestDirtyCache::test_a_cached_window_of_another_request_is_never_relabelled |
| R-10 | GPT-select F10, Grok47-select F6 | pipeline/select_passages.py : _whisper_transcribe; pipeline/sentence_law.py : make_lock / verify_lock / gate_g16 | test_f2 TestDirtyCache::test_a_transcript_of_other_bytes_is_never_used; TestLockBinding::test_g16_refuses_a_source_whose_bytes_changed_after_the_lock |
| R-11 | PP-02 (new) | pipeline/sentence_law.py : verify_lock | test_f2 TestLockBinding::test_a_lock_whose_words_are_not_its_transcripts_words_is_refused |
| R-12 | Grok47-select F8 | pipeline/run_fresh.py : stage_gates; pipeline/release_auth.py : attest | test_f3 test_an_edl_changed_after_the_gates_ran_holds |
| R-13 | GPT-gates F05, Claude-gates V4 / V5, Grok-gates 13 | segment_v1/qa_gates.py : gate_g3b, gate_g3c, gate_g8 | test_f4 test_a_required_gate_never_passes_on_nothing[G3b empty segments / G3b talking head with no expected last word / G3c empty segments / G8 empty segments] |
| R-14 | GPT-cut F23 | pipeline/word_diff.py : gate_g18; pipeline/sentence_law.py : gate_g17_prepared | test_f4 ...[G18 empty segments and clips / G18 empty lock text, nothing heard / G17a no prepared clips] |
| R-15 | PP-03 (new) | pipeline/vertical_layout.py : gate_g4s; pipeline/gates.py : gate_g14; pipeline/edge_shots.py : gate_g19 | test_f4 ...[G4s empty plans / G4s a clip with no shots / G14 16x9 empty manifest / G14 9x16 empty manifest / G19 empty segments] |
| R-16 | GPT-cut F08 | pipeline/word_diff.py : gate_g18 | test_f1 TestG18::test_gate_g18_fails_a_number_that_differs_from_the_lock |
| R-17 | GPT-cut F22 | pipeline/word_diff.py : gate_g18 | test_f1 TestG18::test_gate_g18_checks_every_occurrence_of_a_label |
| R-18 | Claude-gates T3 (named answer #3) | pipeline/select_passages.py : select_and_build_edl (_build_segment) | test_f2 TestSelectContract::test_every_segment_names_the_next_source_word_for_g3b |
| R-19 | Claude-select T1 | pipeline/canon.py : fold (or story_semantics.quote_in) | test_f1 TestQuoteVerification::test_a_compound_name_written_apart_is_the_same_quote |
| R-20 | GPT-gates F28 | segment_v1/qa_gates.py : gate_g8 | test_f4 test_g8_never_passes_on_one_of_five_samples |
| R-21 | GPT-gates F10, Claude-gates C1 | segment_v1/qa_gates.py : extract_frame, extract_audio_region | test_f4 test_g8_never_measures_a_frame_of_an_earlier_render |
| R-22 | GPT-select F23 | pipeline/select_passages.py : _download_window | test_f2 TestDirtyCache::test_a_failed_download_never_supplies_a_source |
| R-23 | GPT-select F08 | pipeline/select_passages.py : select_and_build_edl | test_f2 TestSelectContract::test_select_with_fewer_than_two_clips_is_not_a_success; ::test_select_with_one_channel_is_not_a_success |

## R-01 — PP-01 (new): the canonical form is not a fixpoint on two adjacent spoken numbers
- Defect (measured): `canon_tokens("It costs about two, three hundred dollars a month")` = `[... '2', '300', 'dollars' ...]`
  but `canon_tokens(canon(that))` = `[... '2300', 'dollars' ...]`: the canonical TEXT puts the two numbers side by side
  with one space and `_SPACED_THOUSANDS` reads '2 300' as 2300 on the second pass. Same for 'three, four hundred
  people' (3400), 'one, two hundred basis points' (1200), 'four, five hundred points' (4500), 'ten, twenty, two
  hundred wallets' (20200). Every real sentence measured is a fixpoint (2,197 sentences: tests/fixtures/canon_20261111,
  the preview's transcripts, every runs/*/transcripts record), so the exposure is speech with spoken ranges.
  Order item: "Idempotence: canon(canon(x)) == canon(x)". A site that canonicalises stored canonical text (or joins
  two canonical strings, e.g. `quote_in(" ".join(texts))` across an excerpt that ends on a number) re-merges them.
- Minimal fix: `canon()` emits a separator that `_SPACED_THOUSANDS` / `_THOUSANDS` / `_SPLIT` never join between two
  consecutive numeric tokens, e.g. `" , "` (`canon_tokens("2 , 300") == ['2', '300']`): in `canon(text)`, build the
  string token by token and insert `","` between two tokens that both match `\d+(\.\d+)?`. canon_tokens is unchanged,
  so token-based sites see no difference; quote_in canonicalises both sides alike.

## R-02 — Grok47-select F4: quote_in is a character-substring test
- Defect: `quote_in(q, texts)` = `canon(q) in canon(" ".join(texts))`, a substring of characters. Measured true for
  quotes that are NOT said: '$81,000 by the weekend ...' inside '$181,000 by the weekend ...'; 'coin fell below 74,000
  dollars on Friday night' inside 'Bitcoin fell below $74,000 on Friday night'; 'Bitcoin is now trading at 74' inside
  '... at 74,500 dollars'; '1.6 billion dollars of outflows last week' inside '$11.6 billion of outflows last week'.
- Minimal fix: compare canonical TOKEN runs: `qt = canon.canon_tokens(quote)`; true only when `qt` occurs as a
  contiguous run of `canon.canon_tokens(text)` (`any(tt[i:i + len(qt)] == qt for i in range(len(tt) - len(qt) + 1))`).

## R-03 — Grok47-select F19: a quote may straddle two excerpts
- Defect: the excerpts are joined with a space before the substring test, so 'flows turned negative. Bitcoin is up four
  percent' is "verified" across the end of one excerpt and the start of an unrelated one.
- Minimal fix: `quote_in(quote, texts)` is true when the quote is a token run of ONE text
  (`any(_run(qt, canon_tokens(t)) for t in texts)`); a caller that means adjacent excerpts joins them itself.

## R-04 — GPT-select F05: supporting chunk ids are not bound to the verified quote
- Defect (through `adjudicate` with a fake model): the reply names excerpt A as support, the quote is only in excerpt
  B: `quote_verified` True, `counted_as_same_event` True.
- Minimal fix: in `adjudicate`, `quote_ok = quote_in(quote, [c["text"] for c in excerpts if c["chunk_id"] in set(sup)])`
  (the quote must be in a SUPPORTING excerpt).

## R-05 — GPT-select F04 / GPT-cut F06: a fuzzy anchor moves a quote onto a different claim
- Defect (measured on 240 generated cases, 40 per kind): `editorial_select.align_quote` and `sentence_law.anchor`
  accept EVERY meaning mutant: '$81,000' -> '$18,000' (digits swapped, off by 1,000, x10), '16%' -> '60%', percent
  -> dollars / percentage points, 'has' -> "hasn't" / 'has not' (all seven negation pairs), the Fed -> the Treasury
  (all five actor pairs), '-5%' -> '+5%' / '5%', million / billion / trillion, a dropped decimal. The ratio
  (>= 0.80 / 0.85 with pinned edges) cannot see a one-token change in a sentence of >= 6 tokens. The lock is then
  made on words that state another number / negation / actor than the verified quote.
- Minimal fix (the "D" rule already named in the ledger): after the best span is chosen, refuse it unless the
  quote's PROTECTED tokens equal the span's, in order: numbers and ordinals (`\d+(\.\d+)?|ord\d+`), 'minus' / 'plus',
  'dollars' / 'percent', negations ('not', 'no', 'never', 'nor', any token ending "n't"), and the quote's names
  (canonical tokens of words written with a capital, first word excluded) must all be in the span. One helper in
  canon.py used by both sites.

## R-06 — GPT-gates F17: G20 hears another registry channel's name as the credited one
- Defect: credited 'Bitcoin Magazine', sign-off says 'Bitcoin Magazine Pro' -> heard {'Bitcoin Magazine'} (exact
  containment; the longer non-credited name is skipped because it overlaps the credited span). Credited 'Bitcoin
  Magazine Pro', sign-off says 'Bitcoin Magazine' -> heard (fuzzy 0.89 >= 0.85 against 'bitcoinmagazinefor').
  Same for Coffeezilla / Coffeezilla Extras and CNBC / CNBC Television. (Real Vision Finance credited, 'Real Vision'
  said: correctly not heard.)
- Minimal fix in `spoken_channels`: one exact pass over ALL registry names and aliases, LONGEST first, each claiming
  its span; a name never matches inside a span a longer name claimed; the fuzzy pass for credited names runs only on
  unclaimed text and never where a non-credited name matches exactly.

## R-07 — GPT-gates F15: G3b's last-word match is a substring test
- Defect: `_g3b_match(expected, heard)` = `heard == expected or expected in heard`; lock '... shapes up this week.',
  three readings '... this weekend' -> PASS (3/3 votes).
- Minimal fix (a TIGHTENING; it changes what the check accepts, so it needs the orchestrator's word): `heard ==
  expected or (heard.startswith(expected) and heard[len(expected):] in ("s", "es", "'s"))` (keeps 'magnitude' /
  'magnitudes', refuses 'week' / 'weekend').

## R-08 — GPT-gates F16 / Claude-gates T2: a next word equal to the last word hides the leak
- Defect: `_leak` anchors on the LAST reading word matching the expected last word; lock '... this week.', next
  source word 'Week', readings '... this week week' -> the leaked 'week' is taken as the last word: PASS.
- Minimal fix: locate the lock's last two canonical tokens (`ew[-2:]`) as a contiguous run in the reading (its LAST
  complete occurrence ending at or after the expected last word's first match); `after` = the tokens after that
  run's end; any next-word token in `after` is a leak.

## R-09 — GPT-select F09: a cached download is relabelled with the newly requested offset
- Defect (end to end through `select_and_build_edl`): `sources/<vid>.mp4` is an old download of the window at 285 s;
  the editor's passage is at 60 s (request start 45 s); the host repeats the sentence at 300 s, so it anchors, and the
  EDL records `source_window_offset_s` 45 for a file that starts at 285.
- Minimal fix: on a successful download write `sources/<vid>.section.json` `{"dl_start", "dl_end", "sha256"}`; a cache
  hit is accepted only when that record exists, its sha256 is the file's, and `[start_s - pad, end_s + pad]` lies
  inside `[dl_start, dl_end]` (inclusive); it returns the RECORDED `dl_start`; anything else is a cache miss, and a
  miss whose download fails returns `(None, 0)`, never the file already under the name (that last part is R-22: the
  R-09 pin flips only when both hold; until then it keeps failing, never a false pass). (The test fixtures write
  exactly this record, adv_helpers.write_section, with the request starting 0.25 s inside it, so the containment does
  not hinge on rounding.)

## R-10 — GPT-select F10 / Grok47-select F6: transcript and lock are not bound to the media bytes
- Defect: (a) `sources/<vid>.mp4` replaced under the same name (same speech timing, other content):
  `select_and_build_edl` reuses `transcripts/<vid>.json` of the old bytes (no transcription attempted) and succeeds;
  (b) after the lock and cut table are written, the same replacement passes `gate_g16` (the lock binds only the
  transcript's digest).
- Minimal fix: `_whisper_transcribe` stores `"media_sha256"` (sha256 of `sources/<vid>.mp4`) in the transcript and
  reuses a cached transcript only when it matches; `make_lock(..., source_sha256=...)` records it;
  `verify_lock(lock, transcript_path, source_path=None)` compares it when given; `write_lock_cut_table` and `gate_g16`
  pass `sources/<vid>.mp4`. (The fixtures write `media_sha256`; the byte-replacement probes also rewrite a CONSISTENT
  download record for the new bytes, so only this binding, not R-09's record, can flip them.)

## R-11 — PP-02 (new): verify_lock never compares the lock's words with its transcript
- Defect: a lock built from other words (first 'Ether', last 'carefully.') but carrying the sha256 of the transcript
  on disk passes `verify_lock(lock, transcript_path)` (a rewrite between hashing and reading, a concurrent attempt in
  the same run directory: GPT-select F33).
- Minimal fix: when `transcript_path` is given, load its words and require `0 <= i0 <= i1 < len(words)` and
  `first_word`, `last_word`, `text`, `n_words` equal to those derived from `words[i0:i1 + 1]`; else
  "lock words are not the transcript's words at i0..i1".

## R-12 — Grok47-select F8: an EDL changed after the gates is attested ALL_PASS
- Defect: `attest()` binds `edl.json` by its digest at attestation time but only checks the finals and manifests
  against `GATE_REPORT.measured_files`; an EDL edited between the gates and the attestation (another credited channel,
  another headline) is attested ALL_PASS and delivered.
- Minimal fix: `run_fresh.stage_gates` adds `edl.json` to `measured` (the EDL G15 / G16 / G18 / G20 read);
  `release_auth.attest` adds `"edl.json"` to the tuple it compares with `measured_files`. (adv_helpers.release_run
  already records `edl.json` there, so the family-3 control stays authorised after this fix.)

## R-13 — GPT-gates F05 / Claude-gates V4, V5 / Grok-gates 13: qa_gates REQUIRED gates pass on nothing
- Defect: `gate_g3b(final, [])`, `gate_g3b(final, [talking head with no lock text and no last_word])`,
  `gate_g3c(final, [])`, `gate_g8(final, [])` return `(True, [])`. (run_fresh's evidence rule gives them 0 samples and
  release_auth blocks the row — test_f4 test_whatever_a_gate_returns_on_nothing_release_blocks_it — but the gate
  verdict itself is PASS for any other caller, e.g. run_gates' aggregate, the Law 22 harness.)
- Minimal fix: each returns `(False, [{"error": "nothing measured"}])` when its table is empty; G3b writes a FAIL row
  (not `continue`) for a talking head with no expected last word.

## R-14 — GPT-cut F23: G18 and G17a pass on zero work
- Defect: `word_diff.gate_g18(final, [], {})` -> `(True, [])`; a clip with an EMPTY lock text whose final and source
  both read empty -> PASS with one row (stage_gates turns that case FAIL through its own `missing` list, but the gate
  does not); `sentence_law.gate_g17_prepared({})` -> `(True, [])`.
- Minimal fix: gate_g18 returns FAIL when `clips` is empty and writes a FAIL row for a clip whose `lock_text` is empty;
  gate_g17_prepared returns FAIL for an empty `clip_paths`.

## R-15 — PP-03 (new): pipeline-side REQUIRED gates pass on nothing
- Defect: `vertical_layout.gate_g4s({}, {})` and a clip with `"shots": []` -> `(True, [])`; `gates.gate_g14(final,
  manifest with no segments)` -> `(True, [])` in both the 16:9 and the 9:16 (`frames=False`) form;
  `edge_shots.gate_g19(final, [], {}, fps)` -> `(True, [])`.
- Minimal fix: each returns FAIL when it measured nothing (no shot / no talking-head sample / no talking head).

## R-16 — GPT-cut F08: a number that differs from the selection lock is report-only in G18
- Defect: lock '... above $81,000 ...'; the source span and the final both read '... above $18,000 ...': edges equal,
  identity equal, `lock_diff_reported` = `[('replace', '81000', '18000')]`, PASS.
- Minimal fix: G18 fails a row whose `diff(lock_text, heard)` contains a PROTECTED token (R-05's helper: number,
  sign, unit, negation, name); other lock differences stay reported only.

## R-17 — GPT-cut F22: G18 checks only the last occurrence of a duplicated label
- Defect: `by_label = {s["label"]: s ...}` keeps the last segment of a label; two 'hook' segments, the first reading
  other words -> PASS.
- Minimal fix: a talking-head label that occurs more than once in the manifest is a FAIL row ("duplicate segment
  label"), or every occurrence is checked.

## R-18 — Claude-gates T3 (named answer #3): the EDL never names the next source word
- Defect: `select_and_build_edl` writes no `next_source_word` on any segment, so G3b's leak check
  (`edl_entry.get("next_source_word")`) never runs in production.
- Minimal fix: in `_build_segment`, `"next_source_word": words[i1 + 1]["word"].strip() if i1 + 1 < len(words) else
  None` (pinned.build_edl likewise).

## R-19 — Claude-select T1: a compound name written apart fails the verbatim check
- Defect: `quote_in("MicroStrategy bought more bitcoin this week", ["So micro strategy bought more bitcoin this week,
  again."])` is False (the model's clean-up of the transcript's words; same spoken words).
- Proposed (a decision: it changes what the quote check accepts): compare the quote's canonical token run with the
  text's with the spaces between ALPHABETIC tokens removed on both sides, accepted only when the protected tokens of
  R-05 (numbers, signs, units, negations, names) still match one for one. NOT a CamelCase split in canon.fold: that
  would make 'MicroStrategy' read 'micro strategy' while 'MICROSTRATEGY' stays one word, breaking the all-caps surface
  variants test_f1 requires to be equal (audit A, frontier review #3), and it misses 'Microstrategy'.

## R-20 — GPT-gates F28: G8 accepts one sample as if all five were measured
- Defect: a segment claiming 10 s on a 2.5 s final: one of five frames extracted (out and source), medians of one
  value, PASS.
- Minimal fix: `ok = False` (reason "partial samples") when `len(out_variances) < 5` or, with a source,
  `len(src_variances) < 5`.

## R-21 — GPT-gates F10 / Claude-gates C1: a failed extraction measures an earlier render's frame
- Defect: `extract_frame` writes to a fixed name and never removes an existing file; when ffmpeg writes nothing (a
  sample time past the end), `gate_g8` reads the frame an EARLIER render left at that name. Measured: a black current
  final (one real sample) passes G8 on four sharp frames of the previous render.
- Minimal fix: `extract_frame` / `extract_audio_region` delete `out_png` / `out_wav` before running ffmpeg (as
  `verify_pack._frame` already does) and return False when ffmpeg failed.

## R-22 — GPT-select F23: a failed yt-dlp leaves a leftover file accepted as the download
- Defect: `sources/<vid>.mp4` holds a 10-100 KB partial file (too small for a cache hit); yt-dlp runs, exits 1, writes
  nothing; `_download_window` sees `getsize > 10_000` and returns the leftover; SELECT succeeds with it.
- Minimal fix: check `returncode`; download to `<out>.part.mp4` and `os.replace` it on success only; remove a leftover
  below the cache size before the request; a failed request returns `(None, 0)`.

## R-23 — GPT-select F08: SELECT reports success with one clip or one channel
- Defect: `select_and_build_edl` returns True with a hook and ONE clip, and with hook and clip from the same channel.
- Minimal fix (the D contract: hook + >= 2 clips + the required channels): after filling, `return False` unless
  `len(clip_segs) >= 2` and the hook + clips span >= 2 distinct channels (R5).

## R-24 — phase 2 exam (for pp-selectid, context_integrity.py): a correction 74 s after the clip
- Defect (a design gap, measured on real material; not yet a test failure because the gate is not merged):
  `context_integrity.window` reads `CONTEXT_AFTER_S = 60.0` after the moment. Yahoo Finance F6YuzU0C8ho says the
  summit is 'next month, I believe' (k123, ends 439.3 s) and corrects it at 513.3 s ('Also, I misspoke. The Shenzhen
  summit is next week.', k155-156): 74 s later, outside the window, so Step A cannot see the retraction.
- Minimal fix: besides the window, Step A also receives every sentence of the record that matches an explicit
  correction cue ('misspoke', 'I should say', 'sorry, it was', 'let me correct', 'actually, no', 'I take that back')
  within the same speaker turn region, or the after-window grows to the next correction cue within 180 s. The exam's
  case context_integrity__later_retraction__01 carries an 80 s after-window (marked in the case); a gate that
  re-derives its own 60 s window from the record fails it today.

## R-25 — phase 2 exam (for pp-selectid, context_integrity.py / eligibility): 'no speaker label' is not 'one speaker'
- Defect (design gap): Whisper records carry no speaker turns; manual captions do ('>>' and 'NAME:'). L-v (1) forbids a
  moment that spans a speaker change, and Step A must say who is speaking; on a Whisper record both are unknown, and
  an interviewer's framing reads as the guest's (Kai-Fu Lee 4cfjpf_IDwU k174: the interviewer's 'There is a fear
  amongst politicians and actually Europe is just late to the game ...' sits between Lee's own answers).
- Minimal fix: a moment from a record without turn information carries speaker = UNKNOWN into Step A, and Step A must
  return 'uncertain' (a FAIL under L-s) when it cannot attribute the selected words from the window alone; when a
  manual-caption record exists for the same video, its '>>' / 'NAME:' turns are used to label the Whisper sentences
  by time overlap. The exam's cases carry the caption turns (`window.sentences[].turn`) where the record has them.

## R-26 — phase 2 exam (for the orchestrator and pp-selectid): a temporal held-out slice
- Gap: every case and its answer is readable by the builder (same user, one machine; the published format puts
  `expected` in each case), so a gate can be tuned on the exam itself.
- Protocol (the frontier verification round's proposal, accepted): when pp-selectid freezes its gates it records the
  commit sha in its STATE; pp-tests then mines a FRESH slice (>= 15 context_integrity, >= 8 vo_fidelity, >= 6
  exclusions) from store material the corpus does not use, in the same format, and runs the frozen gates on it; the
  slice is reported apart, with the gate sha, and only then added to the corpus.
- Question for the orchestrator (from the exam's audit): does L-u's 'buy / sell / leverage imperatives' cover a
  sarcastic imperative ('Sell your Bitcoin, all of it', BTC Sessions jTuJ8PXhRV4 k179-180, mocking central bankers)?
  Two of three frontier models said no (intent), one said yes (form). The case is out of the exam until decided.

## Not code requests: measured facts and decisions for the orchestrator

### PP-04 — law L-b on the recorded EDLs of both references (measured; references frozen, nothing adjusted)
Measured with `sentence_law.edge_word_bounds` (the acoustic word extent `edge_fades` itself uses) on each source around
its cut, against the fade recorded in `cuts_final.json` (tests/fixtures/adversarial/reference_lb_edges.json, pinned
by test_f5). Overlap = how far the recorded fade reaches into the edge word (> 0 = it overlaps):

| reference | clip | IN overlap ms | OUT overlap ms | recorded disposition |
|---|---|---|---|---|
| preview | hook | -30 | **+20** | none |
| preview | clip_01 (Natalie Brunell) | -100 | **+73** (83 ms fade) | L-b must-fail (E-FAIL-032) |
| preview | clip_02 (Yahoo Finance) | **+53** (83 ms fade into 'Of') | **+20** | none |
| preview | clip_03 (Bitcoin Magazine) | **+10** | -160 | none |
| v2f | hook | -10 | -10 | passes G17c |
| v2f | clip_01 | -20 | **+20** | G17c legacy FAIL (recorded) |
| v2f | clip_02 | -130 | **+10** | passes G17c |
| v2f | clip_03 | **+10** | **+20** | IN: G17c legacy FAIL (recorded); OUT passes G17c |

Two things for a decision: (1) the protected preview carries four more fades that overlap an edge word by the law's
own measure (hook OUT, clip_02 IN / OUT, clip_03 IN) besides the documented Natalie tail; (2) G17c (the law's check)
passes v2f clip_02 OUT (+10 ms) and clip_03 OUT (+20 ms) while failing clip_03 IN (+10 ms): its best alignment within
+-2 hops can slide a fade that covers up to 20 ms of a decay out of the comparison. Whether L-b is decided by the
word-bounds geometry or by G17c's 1 dB comparison is not mine to choose; no test is xfailed on it.

### G8 9:16 on the approved reference — SETTLED by measurement (Claude-gates #5 / A4 / A5, E-FAIL-042)
Measured 2026-11-12 on the saved v2f files through `qa_gates.gate_g8` (frames to a scratch dir, reference read-only):

| format | wiring | hook | clip_01 | clip_02 | clip_03 | verdict |
|---|---|---|---|---|---|---|
| 16:9 (floor 27.56) | production (prepared clips) | 27.56 / 27.22 (1.012) | 171.87 / 178.45 (0.963) | 265.74 / 268.40 (0.990) | 89.39 / 91.18 (0.980) | PASS |
| 16:9 | no sources (Law 22 harness) | 27.56 / 0 | 171.87 / 0 | 265.74 / 0 | 89.39 / 0 | FAIL (no_source x4) |
| 9:16 (floor 10.84) | production (qa/vert_<clip>) | 19.10 / 18.07 (1.057) | 50.34 / 49.54 (1.016) | 26.25 / 25.29 (1.038) | **10.84** / 10.04 (1.080) | PASS |
| 9:16 | no sources (Law 22 harness) | 19.10 / 0 | 50.34 / 0 | 26.25 / 0 | 10.84 / 0 | FAIL (no_source x4) |

(out median / source median (ratio)). The approved reference does NOT fail 9:16 G8 through the production wiring; it
passes with zero margin on clip_03 (10.84 = the calibrated floor, Claude-gates A5). The recorded FAIL is G8 called
without source clips (the harness), which fails closed by design. Pinned: test_f5
test_g8_9x16_v2f_passes_through_the_production_wiring_at_its_floor and test_g8_9x16_v2f_fails_without_sources_the_harness_reading.

## Tooling (not a pipeline defect): utils/cross_llm_audit.py, as met by a worktree session (for the integrator)
- `BASE = Path.home() / "protocol_pulse"` fixes its inputs, its output directory (`AUDITS / feature`) and
  `AUDIT_REGISTRY.json` to the MAIN tree: a worktree session cannot run it as is without writing there (this session
  redirected the module's paths from a driver; pp-tests_AUDIT_RESPONSE.md). Proposed: a `--base` / `--out` argument.
- A file of 220,000 bytes or more is silently left out of the package (batch 16 saw an empty Grok review). Proposed:
  fail with a message instead of dropping it.
- It needs `GEMINI_API_KEY` / `XAI_API_KEY`; the project's file defines the `_MEDLEY` names (the tool exits "MISSING
  API KEYS"). Proposed: read the `_MEDLEY` names as fallbacks, as pipeline/signoff.py does.
- The xAI gateway it loads enforces `max_usd_per_day` $1.00 per budget ledger: a session that runs several rounds
  loses Grok for the day.
- A docs-only diff is reviewed without the code it describes, so it is scored as "code missing" (0/100 on a status
  update). Proposed: a package type (code / docs) and, for docs, the files they cite.
