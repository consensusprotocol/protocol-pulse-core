# pp-tests BIBLE ADDITIONS — failure patterns found by the adversarial wall (for the integrator to fold into docs/QWEN_CONTEXT_BIBLE.md)

Session pipeline_pp_tests, 2026-11-12. Each pattern names its evidence (a test in tests/adversarial that fails on it
today, strict xfail) and the request in docs/audits/parallel/pp-tests_REQUESTS.md. Numbered PP-E* so they cannot
collide with the integrator's E-FAIL numbers.

### PP-E1: A fuzzy anchor is a meaning changer
**Evidence:** `editorial_select.align_quote` and `sentence_law.anchor` accepted every one of the generated meaning
mutants (40 per kind): '$81,000' vs '$18,000', '16%' vs '60%', 'has' vs "hasn't", the Fed vs the Treasury, '-5%' vs
'+5%', million vs billion. A SequenceMatcher ratio >= 0.80 with pinned first / last tokens cannot see one changed token
in a sentence of six or more.
**Rule:** an approximate match may absorb ASR spelling, never a number, sign, unit, negation or name; compare those
tokens exactly after the fuzzy span is chosen. **Detection:** test_f1 TestSelectionAnchors (R-05).

### PP-E2: A character substring on canonical text matches inside words and numbers
**Evidence:** `story_semantics.quote_in` verified '$81,000 by the weekend' inside '$181,000 by the weekend', 'coin fell
below ...' inside 'Bitcoin fell below ...', 'trading at 74' inside 'trading at 74,500 dollars', and a quote straddling
two unrelated excerpts. The same shape in G3b: 'week' matched 'weekend'.
**Rule:** compare canonical TOKENS as runs (or whole tokens), inside one excerpt; never `in` on strings.
**Detection:** test_f1 TestQuoteVerification, TestG3b (R-02, R-03, R-07).

### PP-E3: A cache keyed by a name is not a cache of these bytes
**Evidence:** select_passages relabelled an old download of the window at 285 s as the new request's 45 s; reused a
transcript made from bytes that are no longer under the name; accepted a leftover partial file after yt-dlp exited 1;
the selection lock binds the transcript's digest but not the media's, so G16 passes a source replaced after the lock.
**Rule:** every cached artefact carries the identity of what it was made from (section, sha256 of the input) and is
used only when that identity is re-checked; a failed producer never leaves its output name holding older bytes.
**Detection:** test_f2 TestDirtyCache, TestLockBinding (R-09, R-10, R-22).

### PP-E4: A failed extraction leaves the previous output to be measured
**Evidence:** qa_gates.extract_frame writes to a fixed name and never deletes it; when ffmpeg writes nothing, G8 read
the frame an earlier render left there: a black current final passed G8 on four sharp frames of the previous render.
G8 also passes on one of its five samples.
**Rule:** delete a fixed-name output before producing it; a gate that asks for N samples fails on fewer.
**Detection:** test_f4 test_g8_never_measures_a_frame_of_an_earlier_render, test_g8_never_passes_on_one_of_five_samples
(R-20, R-21).

### PP-E5: A gate that loops over nothing returns its initial True
**Evidence:** G3b, G3c, G8, G4s, G14 (both forms), G17a, G18 and G19 return PASS for empty segments / plans / manifests
(release_auth's evidence rule blocks them at release with 0 samples; the gate verdict itself is still PASS for any
other caller). G12 / G15 return an explicit skip (recorded SKIPPED) and G20 fails closed: the shapes to copy.
**Rule:** every gate ends `if not measured: return False, ...`; skip is explicit, never a True.
**Detection:** test_f4 test_a_required_gate_never_passes_on_nothing (R-13, R-14, R-15).

### PP-E6: A canonical form must be a fixpoint
**Evidence:** canon('about two, three hundred dollars') reads 2 and 300; canon of that canonical text reads 2300
(the spaced-thousands rule joins two numbers the first pass kept apart). Real transcripts measured so far are fixpoints;
spoken ranges are not.
**Rule:** canon(canon(x)) == canon(x) is a property test of the canonical form. **Detection:** test_f1
TestCanonicalForm (R-01).

### PP-E7: Name matching by containment hears a different channel
**Evidence:** G20 counted 'Bitcoin Magazine' as said when the sign-off says 'Bitcoin Magazine Pro' (and the reverse
fuzzily), Coffeezilla / Coffeezilla Extras, CNBC / CNBC Television: the registry has such families.
**Rule:** match all registry names longest-first, each claiming its span; a credited name never matches inside a
longer registry name. **Detection:** test_f1 TestSignoffNames (R-06).

### PP-E8: A law's statement and its check can disagree on the reference
**Evidence:** L-b says no fade overlaps an edge word; its check G17c aligns within +-2 hops and passes v2f edges whose
recorded fade reaches 10-20 ms into the word's decay by the law's own word-bounds measure, while failing another 10 ms
one; the protected preview has four such edges besides the documented Natalie tail (pp-tests_REQUESTS.md PP-04).
**Rule:** when a law is written as a property ("never overlaps"), measure the property directly on the references,
not only the check that implements it. **Detection:** test_f5 test_l_b_* (pinned table, no xfail: a decision).

### PP-E9: The bytes the drop describes must be the bytes the gates read
**Evidence:** an EDL edited between the gates and the attestation (another credited channel) was attested ALL_PASS and
delivered: only the finals and manifests are compared with the digests the gates measured.
**Rule:** every input a gate reads is in GATE_REPORT.measured_files and re-checked at attestation.
**Detection:** test_f3 test_an_edl_changed_after_the_gates_ran_holds (R-12).

### PP-E10: A test that patches a module attribute patches the whole process
**Evidence (this session, test-side):** replacing `select_passages.subprocess.run` replaced `subprocess.run` for
sentence_law too (the attribute is the shared module object); a strict xfail also "passes" on an unrelated crash of
the test's own setup (two of mine did until re-run with `--runxfail`: a 4-token control quote under quote_in's
5-token minimum, a "partial" file 3 KB over the cache size).
**Rule:** patch a stand-in module object on the caller (`monkeypatch.setattr(mod, "subprocess", Proxy())`), and read
every strict xfail's failure with `--runxfail` before trusting it.

### PP-E11: A pinned defect must be the only way its test can fail, and its fixtures must already speak the fix's contract
**Evidence (frontier review of this wall, verified):** pytest counts ANY exception of an xfail-marked test as the
expected failure, a failing fixture `assert` included (even with `raises=AssertionError`, since that is an
AssertionError too); and the first fixtures wrote no download record, no `media_sha256` and no measured EDL digest, so
the very fixes R-09 / R-10 / R-12 request would have broken the controls and left other xfails "failing" for the
wrong reason, or flipping because a fixture stopped working.
**Rule:** a strict xfail is `raises=AssertionError`; every precondition (fixture, control) is `pytest.fail`, so a
broken setup is FAILED / ERROR, never the defect; fixtures write the records the requested fix will read (extra data
today's code ignores), and the request names them; a probe that must flip only on fix X keeps every other fix's
record consistent (the byte-replacement probe rewrites the download record for the new bytes so only the transcript
binding can tell).

## Phase 2 (moments-first exam, 2026-11-12 from 03:00 ET)

### PP-E12: A clean-looking clip can be the set-up the speaker knocks down next
**Evidence:** Bitcoin Magazine (MJzWDJf4thg k1227-1229) 'So every Bitcoin bear market has been shallower than the
last ... And now our most recent of just minus 53%.' reads as a stand-alone thesis; the next 20 s say 'The consensus
view is that this bear market's drawdown was mild. But maybe there's a more nuanced view owed' and re-measure it in
sigma. I first labelled it MUST-PASS from a 2-sentence look; both frontier baseline models rejected it with the reason.
**Rule:** a moment is judged on its whole after-window, never on its first neighbours; 'the consensus view', 'but maybe',
'a more nuanced view' after a clip are reversals. **Detection:** context_integrity__later_retraction__04.

### PP-E13: A correction can land after the 60 s window
**Evidence:** Yahoo Finance (F6YuzU0C8ho) says the Trump-Xi summit is 'next month, I believe' (k123) and corrects it 74 s
after the clip ends ('Also, I misspoke. The Shenzhen summit is next week.', k155-156). A gate that reads a fixed 60 s
after-window passes the retracted claim. **Rule:** besides the window, search the whole record for explicit
corrections ('I misspoke', 'I should say', 'sorry, it was', 'actually, no') and test them against the moment.
**Detection:** context_integrity__later_retraction__01 (window widened to 80 s and marked so); request R-24.

### PP-E14: Whisper records carry no speaker turns; captions do
**Evidence:** manual captions mark turns ('>>' and 'NAME:' labels: CNBC, Bloomberg, Fox), so a host's paraphrase ('>> SO
YOU'RE SAYING ...', 9iyI2LddOoE k49) is visibly another turn; the Whisper records of the same kind of exchange (Kai-Fu
Lee, 4cfjpf_IDwU k173-174 'So you're telling me ... There is a fear ...') carry none. L-v (1) 'a moment may not span a
speaker change' cannot be checked on a record that does not know turns. **Rule:** a Whisper-only moment has an UNKNOWN
speaker until diarised; a gate must not treat 'no label' as 'same speaker'. **Detection:** context_integrity__wrong_speaker__01..03.

### PP-E15: Ad copy recurs across episodes and carries no marker in its first sentences
**Evidence:** the same Trezor read opens 'Bitcoin is not a set and forget asset. Hodling is an active process.' in two
BTC Sessions episodes (Irt0jKj7ISw k201, jTuJ8PXhRV4 k675); Square's 'Bitcoin can help diversify how you spend, save,
and invest ...' runs in three Bitcoin Magazine episodes; Ledn's 'Selling Bitcoin to cover a big expense is the move
most holders end up regretting' reads as editorial advice (lusJ1m-J0Mc k60). None of these sentences contains 'sponsor',
'code' or a URL; the marker comes 10-40 s later. **Rule:** detect ad reads on the window (and on repetition of the same
sentence across a channel's episodes), never on the moment's own words. **Detection:** exclusions__ad_read__01..05,
context_integrity__reading_aloud__03.

### PP-E16: A channel's upload can be another show's production
**Evidence:** 'Saifedean Ammous' (vgsSZ4mAHfQ) is a Doha Debates debate republished on the channel (its description says
so); Simply Bitcoin plays Darius Dale from Natalie Brunell's Coin Stories (l987bgGZjS0 k32-40) and Jordi Visser from
Anthony Pompliano's show (qo8rDU3bbMo k60-64) inside its own episodes. The channel name says nothing about whose audio
it is. **Rule:** third-party media is decided from the description and the window ('sat down with', 'told <host>',
'hosts ... to debate'), per moment. **Detection:** exclusions__third_party_media__01..02.

### PP-E17: A VO line can add a topic, and a name the case cannot verify
**Evidence:** my first VO corpus opened every case with 'Two voices on Bitcoin.' even where neither clip says Bitcoin,
and named speakers ('Mark Moss', 'Kai-Fu Lee') whose names appear in no clip and in no field of the VO case; both
frontier models rejected four MUST-PASS cases for exactly this. **Rule:** manifest language may name channels, the show,
the date and the count of voices; a topic or a person needs a clip or verified metadata (L-v (1)).
**Detection:** vo_fidelity__faithful_paraphrase__03/04/06 and manifest_language__04 (corrected).

### PP-E18: An exam's packaging can carry the answer
**Evidence:** in the first corpus every must-pass case had the VO bridge "Also on the record:" and no must-fail case
did; the stale-time cases alone had undated captions; one case alone had an 80 s window; the INDEX listed every
must-fail case first. A one-line gate keyed on the bridge met every threshold (frontier review, chunk A).
**Rule:** an exam's stimulus format is drawn from one pool for both labels, the order is shuffled per run, the ids
are salted per run, and a test proves that no single format field lets a lookup gate pass.
**Detection:** test_no_package_field_separates_the_verdicts, test_a_gate_that_answers_by_position_fails.

### PP-E19: A channel named after a person turns a guest's words into the host's
**Evidence:** a must-pass package opened "Stephan Livera first." over Joe Burnett's sentence (and "Natalie Brunell"
over Jeff Booth's); both frontier baseline models failed it as a wrong-speaker package. The channel name is the host's
name, so crediting the channel names the host.
**Rule:** a person-named channel is credited as "<name>'s show" in VO, captions and titles unless that person is the
speaker. **Detection:** the must-pass packages of context_integrity (clean_assertion 03 / 08 / 09,
clean_conjunction_opener 06 / 07).

### PP-E20: Narration right after "X posted / X pointed out" may still be X's
**Evidence:** Simply Bitcoin (l987bgGZjS0) k128 'Jameson Lopp posted about exactly that this week.' k129 'Red team, then
blue team ...' k130 'And the whole time, the debt keeps climbing ...'; k132 'Michael Saylor pointed out that ...'
k133 'The case for holding Bitcoin crosses party lines.' Whether k130 / k133 are the narrator's or the paraphrase's is
not decidable from the words. **Rule:** a moment that follows a reported-speech lead-in without a clear boundary is
'uncertain' (a FAIL under L-s); never a must-pass. **Detection:** both clips were removed from the must-pass set.

### PP-E21: A spend guard that keeps refused calls' reservations starves its own run
**Evidence:** OpenAI's credits ran out mid-baseline (HTTP 429 insufficient_quota); the guard kept each refused call's
worst-case reservation ($0.49), the ledger read $14.68 against $9.26 billed, and every later call was refused by the
guard. **Rule:** a call the vendor refuses before processing it (4xx other than 408 / 409) releases its reservation; a
call with an unknown outcome keeps it. **Detection:** baselines/frontier_blind._call; SPEND.jsonl `release_refused`.
