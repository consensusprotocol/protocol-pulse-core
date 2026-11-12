# pp-tests XFAIL EVIDENCE — each strict xfail fails on its own assertion (the second angle of the triple check)

Generated from `python3 -m pytest tests/adversarial -q --runxfail -rf --tb=line` (2026-11-12, this branch): with the
marks ignored, exactly the 38 strict-xfail instances fail (334 others pass), every one with an AssertionError raised at
an assertion of the test itself (file:line below), never in a fixture or a control (those are pytest.fail, which would
show as Failed). The message is the start of the assertion's own report: the defect, measured. Normal runs report all
38 as XFAIL because each mark is `xfail(strict=True, raises=AssertionError)`; when a fix lands, that test XPASSes and
strict turns it into a failure (remove the mark then).

| test | failing assertion | exception | message (start) |
|---|---|---|---|
| test_f1_text_meaning.py::TestCanonicalForm::test_idempotent_on_adjacent_spoken_numbers | test_f1_text_meaning.py:92 | AssertionError | [('It costs about two, three hundred dollars a month to run a node.', ['it', 'costs', 'about', '2', '300', 'dollars', ... before lunch.', ['the', 'dow |
| test_f1_text_meaning.py::TestG18::test_gate_g18_fails_a_number_that_differs_from_the_lock | test_f1_text_meaning.py:149 | AssertionError | [{'edges': [], 'heard': 'Bitcoin closed above $18,000 after a quiet weekend in Asia.', 'identity': [], 'lock_diff_reported': [('replace', '81000', '18 |
| test_f1_text_meaning.py::TestG18::test_gate_g18_checks_every_occurrence_of_a_label | test_f1_text_meaning.py:164 | AssertionError | [{'edges': [], 'heard': 'Bitcoin closed above $81,000 after a quiet weekend in Asia.', 'identity': [], 'lock_diff_reported': [], ...}] |
| test_f1_text_meaning.py::TestQuoteVerification::test_a_quote_never_matches_inside_a_longer_word_or_number | test_f1_text_meaning.py:184 | AssertionError | [('$81,000 by the weekend and then it fell further', 'It went from above $181,000 by the weekend and then it fell furt...74,500 dollars.'), ('1.6 bill |
| test_f1_text_meaning.py::TestQuoteVerification::test_a_compound_name_written_apart_is_the_same_quote | test_f1_text_meaning.py:191 | AssertionError | assert False |
| test_f1_text_meaning.py::TestQuoteVerification::test_a_quote_never_straddles_two_excerpts | test_f1_text_meaning.py:202 | AssertionError | assert not True |
| test_f1_text_meaning.py::TestQuoteVerification::test_adjudicate_counts_a_quote_only_with_the_chunk_that_says_it | test_f1_text_meaning.py:222 | AssertionError | {'_model': 'fake-model', '_prompt_sha': '5ab8da42e9ce0256', '_support_prompt_sha': 'a54b00548e75894d', 'confidence': 0.9, ...} |
| test_f1_text_meaning.py::TestSelectionAnchors::test_align_quote_never_moves_a_quote_onto_a_different_claim | test_f1_text_meaning.py:246 | AssertionError | (233, [('dollars', 'digits swapped', "Yesterday BlackRock's fund closed above 94,000 dollars after a quiet weekend in ...), ('percent', 'percentage po |
| test_f1_text_meaning.py::TestSelectionAnchors::test_sentence_law_anchor_never_locks_a_different_claim | test_f1_text_meaning.py:254 | AssertionError | (233, [('dollars', 'digits swapped', "Yesterday BlackRock's fund closed above 94,000 dollars after a quiet weekend in ...), ('percent', 'percentage po |
| test_f1_text_meaning.py::TestSignoffNames::test_a_different_channel_variant_is_not_the_credited_channel[Bitcoin Magazine-Bitcoin Magazine Pro] | test_f1_text_meaning.py:331 | AssertionError | {'Bitcoin Magazine'} |
| test_f1_text_meaning.py::TestSignoffNames::test_a_different_channel_variant_is_not_the_credited_channel[Bitcoin Magazine Pro-Bitcoin Magazine] | test_f1_text_meaning.py:331 | AssertionError | {'Bitcoin Magazine Pro'} |
| test_f1_text_meaning.py::TestSignoffNames::test_a_different_channel_variant_is_not_the_credited_channel[Coffeezilla-Coffeezilla Extras] | test_f1_text_meaning.py:331 | AssertionError | {'Coffeezilla'} |
| test_f1_text_meaning.py::TestSignoffNames::test_a_different_channel_variant_is_not_the_credited_channel[CNBC-CNBC Television] | test_f1_text_meaning.py:331 | AssertionError | {'CNBC'} |
| test_f1_text_meaning.py::TestG3b::test_a_longer_word_containing_the_last_word_is_a_different_word | test_f1_text_meaning.py:392 | AssertionError | [{'dissent': False, 'edl_last': 'week', 'last_found': True, 'next_leaked': False, ...}] |
| test_f1_text_meaning.py::TestG3b::test_a_next_word_equal_to_the_last_word_still_leaks | test_f1_text_meaning.py:401 | AssertionError | [{'dissent': False, 'edl_last': 'week', 'last_found': True, 'next_leaked': False, ...}] |
| test_f2_provenance.py::TestDirtyCache::test_a_cached_window_of_another_request_is_never_relabelled | test_f2_provenance.py:133 | AssertionError | {'channel': 'DataDash', 'duration': 9.84, 'first_word': 'Bitcoin', 'handle': '@x', ...} |
| test_f2_provenance.py::TestDirtyCache::test_a_transcript_of_other_bytes_is_never_used | test_f2_provenance.py:148 | AssertionError | the old transcript was used for new bytes |
| test_f2_provenance.py::TestDirtyCache::test_a_failed_download_never_supplies_a_source | test_f2_provenance.py:163 | AssertionError | a failed download supplied the hook |
| test_f2_provenance.py::TestSelectContract::test_select_with_fewer_than_two_clips_is_not_a_success | test_f2_provenance.py:178 | AssertionError | SELECT reported success with 1 clip |
| test_f2_provenance.py::TestSelectContract::test_select_with_one_channel_is_not_a_success | test_f2_provenance.py:185 | AssertionError | assert (True is False or 1 >= 2) |
| test_f2_provenance.py::TestSelectContract::test_every_segment_names_the_next_source_word_for_g3b | test_f2_provenance.py:194 | AssertionError | ['hook', 'clip_01'] |
| test_f2_provenance.py::TestLockBinding::test_a_lock_whose_words_are_not_its_transcripts_words_is_refused | test_f2_provenance.py:237 | AssertionError | assert [] != [] |
| test_f2_provenance.py::TestLockBinding::test_g16_refuses_a_source_whose_bytes_changed_after_the_lock | test_f2_provenance.py:249 | AssertionError | [{'errors': [], 'in': {'after_word': 'story.', 'before_word': 'Bitcoin', 'boundary_valid': True, 'cut': 15.0, ...}, 'l...ighbour_kept_ms': 260, 'ok':  |
| test_f3_release_auth.py::test_an_edl_changed_after_the_gates_ran_holds | test_f3_release_auth.py:273 | AssertionError | an EDL the gates never saw was attested ALL_PASS |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G3b empty segments] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G3b talking head with no expected last word] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G3c empty segments] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G4s empty plans] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G4s a clip with no shots] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G8 empty segments] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G17a no prepared clips] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G18 empty segments and clips] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G18 empty lock text, nothing heard] | test_f4_vacuity.py:192 | AssertionError | (True, [{'edges': [], 'heard': '', 'identity': [], 'lock_diff_reported': [], ...}]) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G19 empty segments] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G14 16x9 empty manifest] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_a_required_gate_never_passes_on_nothing[G14 9x16 empty manifest] | test_f4_vacuity.py:192 | AssertionError | (True, []) |
| test_f4_vacuity.py::test_g8_never_passes_on_one_of_five_samples | test_f4_vacuity.py:230 | AssertionError | [{'degradation_pass': True, 'degradation_reason': None, 'floor': 27.56, 'floor_pass': True, ...}] |
| test_f4_vacuity.py::test_g8_never_measures_a_frame_of_an_earlier_render | test_f4_vacuity.py:246 | AssertionError | [{'degradation_pass': True, 'degradation_reason': None, 'floor': 27.56, 'floor_pass': True, ...}] |
