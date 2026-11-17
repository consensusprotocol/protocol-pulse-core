# Cycle 1 consensus (pp-selectid_audit_20261117_1531, batches 111 + 112's mirror)

SEATS ANSWERED: 3 of 3. qwen3.8-27b: P0/P1 none. gemma-4-31b-it: one P1 claimed. gpt-oss-20b: one P0 and one P1
claimed. All three are refuted below from the code and the passing tests.

1. gemma [P1] "test_canon_spans_reads_the_hyphen_word_by_word asserts canon_spans gives 'minus'; canon_spans only groups
   tokens, so the test fails": REFUTED. The test passes (test_lock_precheck + test_attest + test_ruling_105: 63 passed).
   canon_spans returns CANONICAL tokens with their word spans: the sign expansion is part of it ('fell' '-5%' gives
   'minus' '5' 'percent'). Mutation X4 (the new hyphen rule removed) is killed by that test.
2. gpt-oss [P0] "word_form accepts "it's" against 'it has', letting a run decode that says 'it has' pass a gate":
   REFUTED. word_form never passes anything. attest.class_131 uses it ONLY to lift law L-v 2's critical-token HOLD
   (a number, a name, a negation) from one pair. The pair then goes to ruling 131 (A)'s two of three, unchanged: the
   approved words when the second recogniser reads them, the run's reading only at an edge >= 3, all three different
   holds (test_the_contraction_is_the_same_word_form_pair covers all three). "it" is not a critical token at all, so
   such a pair reaches the same vote with or without word_form. The contraction both ways ('is' / 'has') is the ruled
   design (ruling 142 (2), feb4b72f's own case) and the integrator's shared canon.py, byte-identical.
3. gpt-oss [P1] "another module may hold the old DECODER": REFUTED. lock_precheck.DECODER is the one source. Its
   readers are lock_precheck.result_file and the tests (grep above). The lockstep moves both sides together; entries
   under another decoder are never read (unchanged rule).

## No change from cycle 1 to cycle 2.
