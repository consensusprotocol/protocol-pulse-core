# THE PER-CYCLE LINE WRITTEN BY THE WATCHER (the orchestrator's 08:15 standing order and its 09:02 note), cycle 1

Reviewers (Heimdall): glm-5.3-flash (327 s, $0.006): "Close, not there" (two P0s, three P1s); muse-spark-open (396 s,
$0.032): "ready for production after two P1 fixes" (no P0); qwen3.8-27b (351 s, $0.027): "ready for production" (the
N+1 lookup acceptable). minimax-m3.1-flash: no review (an empty reply at its output limit; not re-run). Cycle 1:
$0.065. Diff reviewed: 47c7939b against 81f46b3c.

## Fixed (each with a test that fails without it: six mutations, each caught)
- C1-1 (glm P0 "the vanish"): cycles that found nothing new returned NO line when a mined upload of the window had a
  Bitcoin term (one the cycles did not list), so the old line stayed or vanished. Now any window with a cycle says
  what its cycles found ("none of its N cycle(s) found a new upload"); only a window with no cycle at all (the watcher
  stopped) has no line.
- C1-2 (glm P0): a reason can carry yt-dlp's multi-line stderr; one newline made write_cycles_notice refuse the line
  on every pass (logged once, never written). Every field is folded to one physical line (_one), and the whole line.
- C1-3 (glm P1): the note's "newest with one" could be days old without saying so: now "the newest upload with one,
  before this window: <video> <channel> "<title>", seen HH:MM ET <date>".
- C1-4 (glm P1): each video's title, shortened to 40 characters, beside its id ("video" read as something a reader
  recognizes).
- C1-5 (glm P1): a ceiling: 12,000 characters, the window's oldest cycles beyond it counted ("N older cycle(s) of the
  window not shown"), the newest always kept.
- C1-6 (muse P1): a cycle whose count its events do not match says both ("4 new (3 found in its events)").
- C1-7 (muse P1, glm BUG 5): the video rows are read in one query (per 500 ids), not one per video.
- C1-8 (glm BUG 9): uploads recorded at a channel's first listing (older than 72 h, never mined) are counted, not listed
  one by one (a new channel would list 30 lines of "mined no (seen_old)").
- C1-9 (glm BUG 2): the note's "N upload(s) seen" adds up: duplicates, no captions, too long and opt-outs counted as
  "not minable" beside the Shorts and the not-yet-mined.

## Recorded, not changed
- glm BUG 3: a partially mined video re-mined every 6 h moves the line's time (a real change; a rewrite every 6 h).
- glm BUG 4: the queries are not one snapshot; the next pass (60 s) re-reads everything (benign).
- glm BUG 7: the +-2 s around a cycle's discoveries: the discoveries are recorded inside the cycle; verified.

Suite: tests/ingest 354 passed.
