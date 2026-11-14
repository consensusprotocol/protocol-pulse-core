# THE PER-CYCLE LINE WRITTEN BY THE WATCHER, cycle 2: consensus

Reviewers (Heimdall): glm-5.3-flash (552 s, $0.007): "Yes, with conditions ... small" (P0 / P1 none); muse-spark-open
(409 s, $0.030): every cycle 1 fix agreed; minimax-m3.1-flash (528 s, $0.010, cut at its output limit after its
findings): two P1s, two P2s (taken, below); qwen3.8-27b (367 s, $0.010): "No" on two P0s, both refuted below.
Cycle 2: $0.057 (both cycles $0.122). Diff reviewed: the working tree at 890f2a56 against 81f46b3c.

## Agreed (verified)
- The cycle 1 fixes (the vanish, the multi-line reason, the counts, the backfill, the titles, the ceiling, one query)
  are real and pinned; the switch-line-first and changed-only rewrite guarantees hold.

## Taken (each with a test that fails without it: four mutations, each caught)
- C2-1 (minimax N1, P1): "NOTHING BITCOIN IN THE LAST 3 H" over-claimed while uploads of the window were not mined yet
  (normal for live streams waiting for hours). The head now says what is known: "NOTHING BITCOIN AMONG THE K MINED IN
  THE LAST 3 H (Q NOT MINED YET)"; the bare claim only when every upload of the window is accounted for.
- C2-2 (minimax N2, P1): one row the renderer could not handle (a mined row without its mined time) raised and lost
  the whole line. A row without its time is rendered "(its time not recorded)"; a row whose rendering raises is named
  "its row could not be read (<error>)"; the line is written either way.
- C2-3 (minimax N3, glm N22 / N6): the ceiling was soft (one cycle longer than it shipped whole; the slack ignored the
  note's length): the whole line is now cut at max_chars as a last step (never over).
- C2-4 (minimax N4, P2): the cycles line could sit under another notice (whoever wrote last went first);
  spend._rewrite_top now keeps it right under ruling 87's switch line, above the other notices.

## Refuted
- qwen P0 "_quiet's logic is inverted (use windows_screened > 0)": refuted. Here a SCREENED window is one dropped
  before any model call for having no Bitcoin term; windows > windows_screened means some window had a term and was
  asked, so the note is (rightly) withheld. The tests pin both cases (a Bitcoin video withholds it; all-screened says
  it). qwen's proposed condition would withhold the note for every screened video, the opposite of the order.
- qwen P0 "compose returns None when cycles ran but found nothing": the cycle 1 code; fixed in C1-1 (its own c2 text
  notes the newline P0 is likewise already handled).

## Recorded
- glm N28: the writer's guard can only fire on a caller bypassing compose (defense in depth). muse: the `start`
  heuristic's fragility is made visible by the count-mismatch note.

Suite: tests/ingest 359 passed.
