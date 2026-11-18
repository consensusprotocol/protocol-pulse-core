# r125: a stream last seen live takes the pipeline's record within the sweep, not at its 20-min re-probe (Nov 18)

## Why (found by r119's own measure)
The orchestrator's 13:05 ET ruling of Nov 16: "Mine each video within 10 minutes of its transcript". On Nov 18 the
measure (transcript_lag_s) showed Fox Business J0UvqtdsBmc at 462 s: a scheduled live show, probed is_live at 09:20
ET; the pipeline's transcript ingest Whispered it at 09:32 (acquired_at 14:32:43Z: it transcribes a stream only once its
own probe sees it over: transcript_store.acquire skips is_live / is_upcoming); fetch.pipeline_sweep (every 60 s)
looked at transcript waits and, since r120, at post_live rows, but never at a row whose last probe said is_live
(r120's invariant: "the sweep never touches an is_live row"), so the record waited for the 09:40 re-probe
(config.LIVE_REPROBE_S = 1200). Inside the bound this time; by design this path could wait up to ~20 min. Of 229
videos with a measured lag, 4 took over 300 s, 2 were LATE: both live rows, on the paths r120 and r122 fixed.

## The change (pipeline/ingest/fetch.py)
- pipeline_sweep also selects a row in live_waiting whose stored live_status is is_live, and makes it due ONCE: only
  when its pipeline record's acquired_at is LATER than the row's state_at (the time of its last probe). Every probe
  of a live row ends in Queue.set_state, which rewrites state_at (queue.py:166 `state_at=config.iso()`), so after the
  probe the same record is no longer newer: no loop of probes. fetch.process is unchanged: a probe that still says
  is_live sets it LIVE again (never taken, no caption download, no meta); post_live takes the record (r120); was_live /
  not_live take it before captions (r118).
- _zoned(s): a time with its zone ('Z' read as UTC), else None (as service.transcript_lag reads acquired_at); a time
  without its zone never makes a live row due (it waits for its re-probe as before).
- Every other wait keeps its rule (any record makes it due): probe_retry, captions_pending, post_live (r120), and an
  unavailable "no metadata" stub (r122).
- tests/ingest/test_r120.py: its sweep test's still-live row now has a record OLDER than its probe (so r125 leaves it,
  as r120 did); the case r125 adds is test_r125's.

## Unchanged code the change relies on (not in the diff)
- queue.py:162-169 Queue.set_state: `f = dict(f, state=state, state_at=config.iso(), next_at=...)` on every call;
  queue.py:171-177 claim() also sets state_at.
- fetch.py process(): `found = pipeline_transcript(vid, ...) if live == "post_live" else None` and `if live ==
  "is_live" or (live == "post_live" and found is None): q.set_state(vid, Q.LIVE, next_at=now_ts + LIVE_REPROBE_S, ...)`
  (a stream still live is never taken).
- The pipeline's records carry acquired_at as ISO 8601 with its zone (e.g. "2026-11-18T14:32:43.041518+00:00").

## What to check
- A stream YouTube still calls live can never be taken, nor probed more than once per new record.
- The other waits' rule is unchanged.
- A missing or zoneless time fails closed (no extra probe).

Suite: tests/ingest 449 passed (5 new in test_r125.py). Mutations M69-M73: 5 of 5 killed; test_r125 passes unmutated
under the mutation runs' guarded environment.
