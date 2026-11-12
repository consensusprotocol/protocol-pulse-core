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
