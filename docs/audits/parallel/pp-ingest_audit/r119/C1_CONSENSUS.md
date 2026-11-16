# r119: within 10 minutes of its transcript, Bitcoin channels first (13:05 ET ruling, Nov 16), cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse, glm out by ruling 119 (3)): qwen3.8-27b (59 s, $0.004 reported):
"ready for production ... The logic is sound, secure, and compliant with all governing laws", P0 none, one P1;
muse-spark-open (292 s, $0.005 reported): "P0 CRITICAL: (none) ... This code is ready for production", two P1s.
Cycle 1: $0.0093 of the $1.00 cap (253 changed lines; COST.json).

## Agreed by both (verified)
- The sweep only moves next_at for the two transcript waits inside 12 h with a record that passes every r118 check,
  never touches a video in flight, makes no YouTube request, does not run while the gate is open; every decision stays
  fetch.process's (the probe's checks first).
- With no `first`, both orders are exactly the old ones; the SQL is parameterised; tier as "Bitcoin channel" is the
  registry's own beat (muse P2 asks for tier 1 before tier 2: recorded below).

## Fixed (each with a test that fails without it)
- C1-1 (muse P1 "the 10-minute guarantee is unmonitored", its section 9): every video mined now carries
  `transcript_lag_s`, the seconds from its transcript record's own time (acquired_at: when its captions were stored or
  the pipeline's Whisper finished) to its rows: on its queue row (a new column, added at start like ruling 98's), in
  the service log ("N s from its transcript", "(LATE: past the 13:05 ruling's 10 minutes)" past 600 s) and on the
  cycles line, the orchestrator's line 2 ("N s transcript (LATE) -> rows"). A time without its zone is no time.
  Tests: test_transcript_lag_reads_only_a_time_with_its_zone, test_a_video_mined_past_10_minutes_from_its_transcript...
  (700 s: LATE in the log and on the line; 42 s: not). M32-M35 killed.

## Refuted (with the evidence)
- muse P1 "widen the sweep's except to OSError: a corrupt file or a permission error aborts the whole sweep":
  pipeline_transcript already catches OSError, ValueError, KeyError, TypeError and AttributeError per record file
  (pipeline/ingest/fetch.py, its `except` around the open / json.load / hash), and glob.glob of an unreadable directory
  returns [] (no exception); the sweep's own `except ValueError` is for transcript_store's id check, which raises
  before any path is made. A bad file costs that one video, never the sweep (test_the_sweep... w4: a broken record).
- qwen P1 "add a LIMIT to the sweep's SELECT: thousands of waiting videos": the rows are the two transcript waits inside
  12 h; the watcher sees about 60-100 uploads a day, so a few dozen at most (12 at the 12:02 stall); each costs a glob,
  and a read only when a record is there. A LIMIT without an order would starve the rest of the list. Recorded.

## Recorded
- muse P2 SQLITE_MAX_VARIABLE_NUMBER: this machine's SQLite is 3.37.2 (the limit is 32,766 since 3.32).
- muse P2 tier 1 before tier 2: the ruling says "Bitcoin channels first"; tiers 1-2 are both Bitcoin and crypto
  channels; inside them, newest first (a fresh Scott Melker stream before an hour-old TFTC). A strict tier order is one
  CASE more if the orchestrator wants it.
- muse P2 a lock on the Bitcoin-set cache: the fetch, mine and hook loops each run in one thread; a race costs one more
  registry read, never a wrong order. muse P3 a debug line when the gate stops the sweep; batched event inserts.
- qwen P2 a log of "checked vs made due": the made-due list is logged and evented; recorded.

Suite after the fix: tests/ingest 422 passed. Mutations: M22-M35, 14 of 14 killed.
