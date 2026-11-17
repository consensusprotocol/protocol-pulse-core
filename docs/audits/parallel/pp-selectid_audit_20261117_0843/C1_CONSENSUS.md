# Cycle 1 consensus (pp-selectid_audit_20261117_0843)

SEATS ANSWERED: 2 of 3 (qwen3.8-27b, gemma-4-31b-it; mimo-v2.6-flash-rl spent its 32,000 tokens and returned no
answer). P0/P1: none from either seat. Both traced the seven checks against the code and passed each.

## Findings and what was done
- qwen [P2] currency_pair's docstring overstates the invariant (an empty side is vacuously satisfied): ACCEPTED,
  reworded.
- qwen [P3] the right-slide test's inline comment sits on the assertion of the slid distance: ACCEPTED, moved to its
  own line and reworded.
- qwen [P2] edge_distance re-runs SequenceMatcher per pair: DECLINED. It mirrors the render's own function exactly
  (the integrator's pinned.adjudicate_lock), on clip-scale texts; a different structure here would be a second place
  to keep in step for no measured gain.
- qwen [P3] the ruling 131 "carried" text is longer than ruling 84's: DECLINED. It is the sealed human record of
  exactly what carried over; the release caption's short form is the integrator's, from attested.rule.

## Changed since cycle 1's diff (the integrator's answer of 08:5x Nov 17, its as_spoken edges)
Cycle 1 reviewed a ruling-72 layer test that asked, at each difference between the spoken text and the merged
reading, whether the UNTRIMMED second recogniser read the spoken tokens there (attest.reads). The integrator's
pre-check builds its as_spoken text from the second recogniser's tokens with the neighbours' spill trimmed
(lock_precheck.reading + _spill: every token before the lock's first aligned token goes, unless it repeats the tokens
right after it, the speaker's own 'When, when'; the end alike). So:
- NEW attest.spill_trimmed(lock_tokens, s): that trim, as the integrator gave it.
- The ruling 72 layer is now EXACT: the spoken text's canon tokens must equal the merged reading, or the trimmed
  second reading of the span; and every difference from the merged reading must be in ruling 84's class (class_84,
  unchanged). The position-wise reads test is gone (the exact equality is stricter, and against the untrimmed reading
  it would hold a padding word at the span's edge that the render never adopts).
- NEW test test_ruling_72_on_top_is_the_second_recognisers_reading_with_its_spill_trimmed: padding at the start and the
  end is trimmed and never adopted; the speaker's own edge repeat at the start and at the end is kept and adopts.
- Mutations after a control run: 23 of 23 killed (M5 is now the exact equality; M20-M23 the trim's four branches).
  Suites: 40 files by exit code, 871 tests.

PLEASE CHECK in cycle 2: the trim (start and end, the repeat it keeps), that the exact equality cannot let a spoken
text through that is neither the merged reading nor the second recogniser's trimmed reading, and the earlier seven
checks on the changed code.
