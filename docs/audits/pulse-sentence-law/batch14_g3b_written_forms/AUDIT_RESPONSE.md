# Batch 14 (law L-g: G3b reads ASR symbols as the spoken words): dispositions

Audit on the actual diff (STEP.diff): cross-LLM, all three models both cycles (Grok's daily budget had reset);
Heimdall deepseek + qwen27b + glm (heimdall/).

## Implemented
- Cross-LLM UNIQUE-1 (Gemini; the consensus tiebreaker upheld it against GPT-4o and Grok): the EDL's next source
  word can read as several words ('50%' -> '50 percent', '$5' -> '5 dollars'), and the leak check used only the
  first. It now counts a leak when ANY of those words is heard after the expected last word in a majority of the
  readings (fail closed; the old rule matched the whole '50%' token). Must-fail test with stubbed readings
  ('the market rose. percent' with next word '50%' -> FAIL; 'the market rose.' -> PASS).

- Heimdall (deepseek + qwen27b, cycle 1): commas are removed only between digits (thousands separators), other
  commas split words as before ('well,known' = 'well known'); abbreviated scales after a number are spelled out
  ('$40M' = '40 million dollars', '74k' = '74 thousand'); a 'dollars' the ASR also wrote is not doubled
  ('$40 trillion dollars' = '40 trillion dollars'); '$50%' reads '50 percent' with no 'dollars'; the
  next-word check (also deepseek's high finding) uses every word. Tests added for each, plus a gate-level
  must-fail ('rally' expected, 'above $40 trillion' heard -> FAIL) and the EDL's own symbol ('$40.' -> 'dollars').

## Rejected, with evidence
- Heimdall qwen27b F3 "the '$' expansion can invent a 'dollars' never spoken (false accept)": the EDL's last word
  comes from the verbatim decode, which heard 'dollars' as a word; a clip cut before it still fails G17c (every
  edge word's frames against the source within 1 dB) and G18; the selection lock fixes the word inside the cut.
- Heimdall qwen27b F6 "'U.S.' now stays one token 'u.s'": the old rule never matched a 'U.S.' last word at all
  (expected 'u.s' vs heard 'u', 's'); identical written forms now match.

## Agreed as correct (no change)
- Unanimous: the deferred 'dollars' after scale words ('$40 trillion' -> '40 trillion dollars'); the last-word
  normalisation; fail-closed behaviour; the v2f must-pass and the preserved must-fails.
- GPT-4o's P2 "add a test for '$40 trillion'": already asserted in test_symbols_are_read_as_the_spoken_words
  (Grok and Gemini said so).

## Verified
- CUDA_VISIBLE_DEVICES=0: test_g3b_majority 7 passed (with the added cases), test_round2_mustfail 15 passed.
