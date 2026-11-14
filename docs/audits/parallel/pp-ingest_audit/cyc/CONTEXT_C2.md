### The orders this change answers (verbatim)
- ORCHESTRATOR 08:15 ET Nov 14 (to pp-ingest): "From now on line 1 carries, after each cycle that finds something:
  video, channel, mined yes/no, moments, hooks, seconds from publish to rows."
- ORCHESTRATOR 09:02 ET Nov 14: "It is Saturday: uploads will be light; say so in the line when a cycle finds nothing
  Bitcoin in 3 hours."

### Background
- Until now pp-ingest's Claude session wrote that line by hand from the watcher's queue (a scratch script, every
  20-40 min), so between its writes the line was stale. STATE (docs/audits/parallel/pp-ingest_STATE.md) starts with a
  block of NOTICE lines (spend.NOTICE_RE: the spend notices, the outage notice, the purge notice, the signal notice,
  ruling 87's switch line, which is always first); spend._rewrite_top rewrites that block under the notices' flock,
  only when the text changes, and never rewrites a STATE file that exists and cannot be read.
- The queue records each watch cycle (events kind 'watch_cycle': new, seconds) and each discovery (kind 'discovered',
  with how it was listed), and the video rows (state, reason, published_ts, discovered_ts, mined_ts, moments, windows,
  windows_screened, hook_ts, hook_rows, spot_rows).

### The change under review (47c7939b against 81f46b3c)
- pipeline/ingest/cycles.py (new): compose(q, now_ts) -> one physical line "PP-INGEST CYCLES TO HH:MM ET (...): ..."
  with each cycle of the last 3 h that found a new upload (newest first) and each of its videos (a Short; mined no,
  queued with state and reason; mined yes with moments, hooks + spotlights or "hook pass pending", seconds publish ->
  rows, or -> mined with why 0 moments, seen-after-publish and mined-after-seen), the 09:02 note when none of the
  window's MINED uploads had a Bitcoin term (not-yet-mined ones counted apart), None when no cycle ran in the window.
  Its time: the newest cycle or change it reports (a quiet window: its newest cycle), never the clock's.
- spend.py: CYCLES_PREFIX in NOTICE_RE ("PP-INGEST CYCLES TO "); write_cycles_notice(line) (refuses a line that is not
  one physical cycles line; creates its lock's directory).
- service.py: the health loop (every 60 s) calls _cycles_notice: compose + write; a failure is logged once per cause
  and never stops the loop.
- tests/ingest/conftest.py: an autouse fixture sends every test's STATE writes to its own file (the health loop now
  writes STATE in any service test); tests/ingest/test_cycles.py (new) + a service test. Five mutations, each caught.
- design 17.

### Questions for the reviewers
1. Can the line ever be rewritten every minute (the clock leaking into its text), or carry a wrong count / time?
2. Can it ever break STATE: the switch line not first, a notice lost, a session line touched, the file rewritten from
   nothing, a test reaching the real file?
3. Does "nothing Bitcoin" ever claim it while an upload is not yet known (not mined)?

### Cycle 1 (890f2a56): what changed since 47c7939b (details in C1_CONSENSUS.md)
- cycles.compose: a window with any cycle always has a line (its cycles found nothing new: "none of its N cycle(s)
  found a new upload"); no cycle at all in the window: None. Every field and the whole line folded to one physical
  line (_one: a reason can carry yt-dlp's multi-line stderr). Each video's title (40 characters) beside its id. A
  cycle whose count its events do not match: "N new (M found in its events)". Uploads recorded at a channel's first
  listing (SEEN_OLD) counted, not listed. One query for the window's video rows (_videos, per 500 ids). A ceiling,
  MAX_CHARS 12,000: the oldest cycles beyond it dropped and counted, the newest always kept.
- cycles._quiet: "N upload(s) seen (S Shorts, Q not mined yet, O not minable)"; the newest upload with a Bitcoin term
  labelled "before this window", with its title.
- tests: six new cases (the newline reason; the no-vanish; the count mismatch and the backfill; the ceiling; the
  duplicate counted as not minable), each failing with its fix reverted.
- design 17.
