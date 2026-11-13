# Batch 47 cycle 1: no consensus findings

Implemented from single votes (qwen F1 and glm F1, phonetic false positives on short codes): a ONE-word name never
matches phonetically. The case is measured: doublemetaphone('Casa') = doublemetaphone('case') = KS. Such a name keeps
the exact and 0.85-ratio routes. This is stricter than the ruling's literal text; it does not loosen anything, and it
is reported in the DoD. Test: test_a_one_word_name_is_never_heard_phonetically.

Kept, with reasons:
- glm F1, "any shared code, not the same primary". For a name of two or more words EVERY token must match, consecutive
  and in order. That is the ruling's own discriminator: 'Steven Lubka' shares STFN with 'Stephan', but LPK does not
  share LFR with 'Livera'.
- qwen F2, the review drop's script check allows a 0.85 ratio. It is the same strict reading law L-a uses before
  render (run_fresh stage_voice, never phonetic). The amendment says "the SCRIPT names every credited channel", which
  is that check.
- glm, cross-examination (low), the quoted stretch can carry a neighbour's letter ('dstefanlavera'). It is exactly the
  same-length window the ratio was computed on, so it is quoted as measured.
