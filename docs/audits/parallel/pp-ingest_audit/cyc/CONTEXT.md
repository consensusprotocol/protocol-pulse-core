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
