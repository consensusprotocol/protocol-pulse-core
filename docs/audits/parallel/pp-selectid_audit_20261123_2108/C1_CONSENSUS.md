# C1 CONSENSUS (written by the pp-selectid session, ruling 118: Heimdall seats only)
Seats answered: 2 of 2 (qwen3.8-27b; gpt-oss-20b at effort low). gemma's breaker was open (the first start refused).
- gpt-oss P1 ("content_flags can count more than 3 kinds and still pass"): DISPROVED. The rule IS kinds (ruling 155
  (1)); review_problems refuses n > cap with n the kinds: test_the_cap_counts_kinds asserts '4 kinds of review flag,
  over 3' for four kinds, and mutation K1 (counting every flag) fails it.
- qwen P1 (kind_sentences raises KeyError for a code with no plural wording on 2+ clips): UNREACHABLE today (the
  context_a row flags only when every code is in STEP_A_SOFT, all four worded in STEP_A_SOFT_MANY; soft_edges yields only
  EDGE_IN / EDGE_OUT, both in EDGE_WORDS_MANY), HARDENED anyway: the merged sentence falls back to the one-clip wording,
  then the code itself.
- qwen P2 (a 6-clip merged sentence is not stripped by _CLIP_REF): a medley has at most 5 segments (hook + 2-4 clips);
  within one package each code is ONE sentence, so the count is right either way. No change.
- qwen P2 (content_flags filters FLAGGED rows): review_flags_of reads only FLAGGED rows too. DISPROVED.
- gpt-oss P2 (identical sentences of one gate collapse): intended (one kind). P3s: no change.
Cycle 2 cross-examines the hardened diff.
