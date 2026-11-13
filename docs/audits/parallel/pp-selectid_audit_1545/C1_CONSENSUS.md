# pp-selectid audit 1545 (RULING 69: the speaker attribution reads the caption turn): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes with conditions": P1, a malformed caption record could crash the package.
  - glm: "SHIP: yes with conditions": P1-1 chained merges, P1-2, P1-3.
  - qwen: "SHIP: No", on P1-1 to P1-3.
- No P0. Three consensus items are applied before cycle 2.

## Applied

| # | finding | the change |
|---|---|---|
| C1 | The backchannel merge is too loose: any <= 3 words between markers was skipped, so a SHORT FLOOR-TAKING line by the other speaker ("Mark, why?"), or a marker misfire, could join two speakers (qwen P1-1, P2-3; glm P1-1) | An interjection now continues a turn only when it is <= 3 words AND every word is a backchannel token (BACKCHANNEL: yeah, yes, right, okay, sure, mm, mhm, uh-huh, exactly, wow...). Anything else ends the turn. Test: test_only_a_backchannel_continues_a_turn_and_a_bad_record_is_skipped. The real 945.28 case still reads: the turn is 696.24-953.52 across "Yeah.", and holds the address. |
| C2 | A malformed caption record (a segment without "start", a non-numeric time, times out of order) raised outside any guard and could abort the whole package (grok P1, P2; qwen P1-2) | captions() parses inside a guard: a missing or non-numeric start, a NaN, or a time earlier than the one before skips that store, which is the same as having no markers. attribute() reads the turn inside a guard ("the caption turn could not be read: ...", still measured). attribute_package guards captions_for. Tests: an out-of-order store and a store without "start" are skipped; a bad clip time gives a recorded why, no crash. |
| C3 | The cut of a turn longer than TURN_MAX_CHARS could split words (grok P2, qwen P2-1; glm asks for a test) | The cut moves to word boundaries on both sides. Test: test_a_long_turn_is_cut_on_word_boundaries_around_the_clip (the clip's words kept, no word split, within the limit). |

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P1-3: a quote from a backchannel could be attributed to the turn's speaker | turn_of builds the turn text from `spans` only. Each skipped interjection [b, nxt(b)) is appended to `backchannels` and never to `spans`, so its words are not in turn["text"]. check_turn keeps a quote only if _within(quote, turn_text). The test asserts "Tell that to his wife" is not in the turn text. |
| R2 | glm P1-2: decide() could accept an address to a person not among the people | check_turn keeps an address only when `who` (the person, by _norm equality) is in people. decide() then names the other of exactly two; with any other count it names no one. The invariant is enforced where the evidence is admitted. |

## Recorded (single-model, no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-3: the first store with any marker wins over a fuller copy | That fails closed: a copy without the clip's turn markers gives "no marker before the clip", or a longer turn cut by TURN_MAX_CHARS. Single-model. |
| G2 | qwen P2-2: MARKER_TOL_S 0.5 s | Caption lines carry their display time, about 2 s per line in auto-captions, so a tighter tolerance would miss real edges. Single-model. |
| G3 | glm P2-2: the name-word length thresholds (> 1 in check_turn, > 2 for the lower third) | The lower third is noisier OCR text, so short tokens there are ignored. Single-model. |

## Verification

- test_speakers 23 OK on dev25 (2 new).
