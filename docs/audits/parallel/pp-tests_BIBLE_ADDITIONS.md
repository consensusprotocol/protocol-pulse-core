# pp-tests BIBLE ADDITIONS — failure patterns found by the adversarial wall (for the integrator to fold into docs/QWEN_CONTEXT_BIBLE.md)

Session pipeline_pp_tests, 2026-11-12. Each pattern names its evidence (a test in tests/adversarial that fails on it
today, strict xfail) and the request in docs/audits/parallel/pp-tests_REQUESTS.md. Numbered PP-E* so they cannot
collide with the integrator's E-FAIL numbers.

### PP-E1: A fuzzy anchor is a meaning changer
**Evidence:** `editorial_select.align_quote` and `sentence_law.anchor` accepted every one of the generated meaning
mutants (measured 2026-11-12: 233 mutants of the 120 anchor cases, 20 per kind, 233 / 233 accepted by each; the pins
fail while any one is accepted, they do not assert "every one"): '$81,000' vs '$18,000', '16%' vs '60%', 'has' vs "hasn't", the Fed vs the Treasury, '-5%' vs
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
other caller). G20 fails closed: the shape to copy. G12 / G15 with no shout-out return `(True, {"skip": True})`, and
production writes that as a PASS row, not SKIPPED (corrected 2026-11-12, integrator merge audit: the first version of
this entry said "recorded SKIPPED", from the test's own model of stage_gates; run_all_gates nests the skip under
"data" and stage_gates reads only a top-level skip; R-28).
**Rule:** every gate ends `if not measured: return False, ...`; a skip is a verdict the row writer reads, never a
True with a flag beside it.
**Detection:** test_f4 test_a_required_gate_never_passes_on_nothing (R-13, R-14, R-15).

### PP-E6: A canonical form must be a fixpoint
**Evidence:** canon('about two, three hundred dollars') reads 2 and 300; canon of that canonical text reads 2300
(the spaced-thousands rule joins two numbers the first pass kept apart). Real transcripts measured so far are fixpoints
(2,197 sentences, a one-off measurement; the shipped test covers the 200 sentences of tests/fixtures/canon_20261111);
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
**Evidence:** an EDL edited between the gates and the attestation (another credited channel) was attested ALL_PASS
(the pin stops at the attestation; delivery of that run was not exercised): only the finals and manifests are compared
with the digests the gates measured.
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
**Correction (integrator merge audit, 2026-11-12):** this wall broke its own rule three times, all fixed: the F2
template had one clip, which the wall's own R-23 makes illegal (every lock test would have errored once R-23 landed);
the R-04 control read the very field R-04's fix changes; the R-22 probe kept a transcript of other bytes, which R-10's
fix rejects. Added rules: a fixture must satisfy every contract the wall itself requests; a control may only read
what no requested fix changes; a request may never loosen what a check accepts (R-19, withdrawn), and a rewrite of a
check keeps its existing guards (R-02 / R-03: the 5-token minimum; an empty token run occurs in every text).

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

## Integrator merge audit of phase 1 (pipeline_pp_dod, 2026-11-12 04:47 ET): patterns found while answering it

### PP-E22: A source whose transcription failed crashes the slot fallback instead of stopping
**Evidence (measured 2026-11-12, worktree code):** the hook's source is cached with a valid download record but has no
transcript; transcription fails (`_whisper_transcribe` returns None: "VIDAAAAAAAA: FAILED"). select_and_build_edl drops
the hook from `valid`, refills the hook slot from the shortlist, picks the same video, and `_source_for` reads
`transcripts[vid]` for a video that IS in `sources` but not in `transcripts`: `KeyError: 'VIDAAAAAAAA'` escapes select
(its contract is True / False). With a one-clip template the earlier `len(valid) < 2` STOP hid it; the two-clip template
the integrator asked for (B2) exposed it. **Rule:** a producer that can fail leaves every map it feeds consistent ("in
sources" must imply "has a transcript", or the lookup is `.get` with a reason); a selection failure is a STOP with a
reason, never a traceback. **Detection:** test_f2 TestDirtyCache::test_a_failed_transcription_stops_select_cleanly (R-27).

### PP-E23: A lone trap line has its own position pattern
**Evidence (vo_fidelity v1.1, 2026-11-12 ~06:20 ET, caught by test_no_package_field_separates_the_verdicts before
anything was published):** the first v1.1 draft wrote each must-fail case as ONE trap line, while the must-pass host
commentary cases had a tease before clip A plus a takeaway. The play-order pattern of the lines (`after`: before A /
after A / after B) then told the verdict without reading a word: (intro, B hand-off, takeaway after B, sign-off) occurred
only in `commentary_recharacterises`; two more patterns only in must-fail cases. **Rule:** when an exam adds a field
the gate sees (here: line positions, title, universe), add it to the format-leak test in the same change, and give
must-fail packages the same honest lines (the same sentences) the must-pass packages use, so only the trap differs.
**Detection:** tests/adversarial/test_moments_gates.py `_vo_fields` (`positions`, `title_template`, `universe`).

### PP-E24: A guard installed in this process does not reach its child processes
**Evidence (repo audit tool, cycle 2 with the brief, 2026-11-12):** the scoped conftest allowed `python` children
(the moments harness starts one), and a child interpreter does not inherit the parent's socket patches: any test
starting `python -c ...` had the network. Fixed: every Python child starts with tests/adversarial/child_guard/ first
on its PYTHONPATH (its sitecustomize installs the same guard); -I / -S / -E children are refused; the moments exam's
documented opt-in (PP_MOMENTS_ALLOW_NETWORK=1) is the only way around it. **Rule:** a process-level guard (sockets,
GPU visibility, model stubs) is either re-installed in every child the code starts or the child is refused; test the
child, not only the parent. **Detection:** test_f0 test_a_python_child_refuses_the_network_too, test_a_network_tool_cannot_be_started.

### PP-E25: Pin the test's own model of production, on purpose (assumption pinning)
**Evidence (this audit):** the wall's model of stage_gates read a gate-level skip as SKIPPED; production writes PASS
(R-28). The model had nothing tying it to the code it described. **Rule:** where a test models production it cannot
run (a GPU stage) or carries a list production also carries (the REQUIRED inventory, the modules that may expose a GPU,
a test-side decoder replica), pin the assumption against production deliberately: the lines it models, the literal
inventory, a static scan, an equivalence test. Such pins are intentionally brittle: when one fails, re-derive the
model, never just the pin. **Detection:** test_f4 test_the_production_reading_is_the_code, test_f3
test_the_required_inventory_is_the_pinned_one, test_f0 test_no_module_this_suite_imports_sets_cuda_visible_devices_unreviewed,
test_f5 test_window_audio_reads_the_edges_the_whole_file_decode_reads. (The R-19 withdrawal is the matching rule for
requests: when a proposed fix would loosen what a check accepts, withdraw the proposal, never the law: PP-E11.)

## Integrator merge cycle 2 (pipeline_pp_dod, 2026-11-14 07:00 ET): the wall meets law L-r's GPU leases

### PP-E26: A static import scan that matches module NAMES against a directory blames a same-named stranger
**Evidence (integrator cycle 2, 2026-11-14):** test_f0's setter scan took every name this suite imports and looked for
`pipeline/<name>.py`. The suite's `import conftest` is its OWN conftest (tests/adversarial/conftest.py), but once law
L-r put a `pipeline/conftest.py` (the E-FAIL-053 teardown) on the release line, the scan blamed that file: `{'conftest',
'qa_gates'} != {'qa_gates'}`, a false failure on the merged tree. **Rule:** resolve an import the way the interpreter
does for THAT process (`sys.modules[name].__file__`, else `importlib.util.find_spec(name)` on the suite's sys.path),
never by a file name in a directory; and when a branch's base is older than the line it merges into, re-run its
brittle pins (PP-E25) on the merged tree before calling the branch ready. **Detection:** test_f0
test_no_module_this_suite_imports_sets_cuda_visible_devices_unreviewed (`_resolve`, with the control that `conftest` is
the suite's own).

### PP-E27: A newer, earlier guard silently takes over from the test's own guard
**Evidence (integrator cycle 2):** the wall refused Whisper with a faster_whisper stub that records every attempt, and
three tests read that record (or the stub's RuntimeError) as the proof of an attempt. Law L-r then routed every
pipeline Whisper load through gpu0 (gpu0.whisper -> Model.get -> require), which refuses a CPU session FIRST, with a
Gpu0Stop (a BaseException), and made the transcriber lazy. Result on the merged tree: 'DID NOT RAISE' (constructing the
transcriber loads nothing), R-27's pin stopped at the lease before its injected failure, and R-10's pin would have
shown its future fix as an error instead of an XPASS. **Rule:** when production adds a refusal ahead of a test's own
stub, the test names the layer it means: assert the production refusal where production refuses (here
gpu0.LeaseMissing with its message), keep the stub as the backstop for code outside it, and inject an ordinary failure
at the production seam that carries it (`_whisper_transcribe -> None`), not below a guard that now never runs.
**Detection:** test_f0 test_every_whisper_load_is_refused_and_recorded; test_f2
test_a_failed_transcription_stops_select_cleanly (R-27), test_a_transcript_of_other_bytes_is_never_used (R-10),
test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing.

### PP-E28: An exam's adapter can be older than its format
**Evidence (2026-11-14, read at origin/pp-selectid aef73873):** the builder's moments_gate_adapter.py was written
against vo_fidelity v1 and never passes v1.1's `title` or `universe` to the gate. The two stale-title cases are
must-fail only through the title, so a run would pass them whatever the gate judges: the exam would report a gate miss
that is an adapter omission. **Rule:** a format version bump names the fields an adapter must forward, and before a
paid run the adapter is checked against the current format (field by field; a case that is must-fail only through a
field the adapter drops is a guaranteed false pass). **Detection:** REQUESTS R-29; the format sections of
pp-tests_STATE.md (v1, v1.1).

## Integrator audit batch 78 (pipeline_pp_dod, 2026-11-14 ~08:20 ET): consensus of qwen27b and glm, both verified

### PP-E29: A network guard that lists forward lookups only lets reverse lookups out
**Evidence (integrator batch 78, consensus):** the exam runner's refuse_network patched getaddrinfo, gethostbyname
and gethostbyname_ex but not socket.gethostbyaddr, so a gate's reverse lookup still sent a DNS query. Checking the
class found the second reverse lookup, socket.getnameinfo (a PTR query unless numeric flags are given), missing from
ALL THREE guards: the runner's, conftest.py's and the child guard's. **Rule:** a network guard covers connect /
connect_ex / sendto / sendmsg and every name lookup, forward AND reverse (getaddrinfo, gethostbyname[_ex],
gethostbyaddr, getnameinfo). When one guard misses a call, check every guard for the same class of call; better,
keep ONE list for all of them (since batch 78: tests/adversarial/child_guard/netguard_names.py, which conftest.py,
the child guard and the runner all use). The list is shared; each guard's exception type and restore behaviour stay
its own (PP-E30: the type names the guard). **Detection:** test_f0 test_no_datagram_and_no_name_lookup_gets_out and
test_a_python_child_refuses_the_network_too; test_moments_gates test_the_network_is_refused_unless_allowed
[moments_toy_gates.network_reverse] and test_the_runner_refuses_every_call_of_the_suites_list.

### PP-E30: With layered guards, a test must name WHICH guard refused
**Evidence (the same finding):** the runner runs as a Python child of this suite, so the child guard sits under it
too, and the runner's network test asserted only `"network is disabled" in why`. Both guards' messages contain that
phrase, so the child guard's refusal hid the runner's missing patch: the test passed with the defect present.
**Rule:** where guards stack, assert the guard under test by its own exception type and message prefix (here
`NetworkRefused: moments_exam: network is disabled`), and check the must-fail line against the code from before the
fix (measured: the runner from before refused neither reverse lookup itself; only ChildNetworkBlocked came back).
**Detection:** test_moments_gates test_the_network_is_refused_unless_allowed (both parameters).

### PP-E31: Keys by NAME through the pipeline's loader, never a key-file path parsed in a test directory
**Evidence (integrator batch 78, consensus):** baselines/frontier_blind.py hard-coded the main tree's key file and
parsed it. It read one key by name and printed nothing, but it duplicated the house loader and fixed a secrets path
inside the test tree. **Rule:** read keys through video_pipeline_v3/relay.get_key (process environment first, then
the project's key files), as scripts/integrator/grok_audit.py does. Load the MAIN tree's copy, because it finds the
key file next to itself, and pin its path: a loader path taken from the environment would choose a file to EXECUTE
in a process that holds keys. In a long-lived process that imports modules by name, load it by file path without
changing sys.path and with sys.dont_write_bytecode set, so no __pycache__ lands in the main tree. **Detection:**
test_f0 test_keys_are_read_only_by_name_through_the_pipelines_loader (added in the same batch on glm's P1: no string
constant of the suite names the key file; the baseline's `_key` only calls relay.get_key).
