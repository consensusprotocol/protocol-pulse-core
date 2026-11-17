# r121: a probe answered with yt-dlp's stub is "no metadata", never "waiting" (Nov 16, 19:4x ET)

## Why
The self-check (r118, the orchestrator's 10:50 order (4)) fired at 19:31 ET with 6 videos waiting. 2 of them, Yahoo
Finance nlRpMRMq2bc ("The Daily Wolf with Scott Melker (12:00...") and QSHyMFr-i04, had sat in probe_retry since 12:05
ET as "no publish time measured". One `yt-dlp -J --skip-download --ignore-no-formats-error` read of nlRpMRMq2bc at 19:3x
ET returned the stub yt-dlp emits for a page with no player data: title "youtube video #nlRpMRMq2bc", live_status,
duration, timestamp, release_timestamp, upload_date all None, no captions: a video removed, private or not public
yet. fetch.probe returned it as a probe (its id matches); fetch.process then retried it as "no publish time measured"
every hour forever (PROBE_RETRY_S caps at 3600 s), and stall.check counted it as waiting: it would have raised the
stall line every 30 minutes without mining overnight until the video left the 12 h window.

## The change (pipeline/ingest/fetch.py only)
- fetch.probe: a JSON whose id matches but which carries none of FACT_KEYS (live_status, duration, timestamp,
  release_timestamp, upload_date) is ("no_metadata", ...), not a probe.
- fetch.process: "no_metadata" is UNAVAILABLE (reason "no metadata: ..."), tried again every NO_METADATA_RETRY_S
  (3600 s: as often as before, so a video that turns public is still seen within the hour) and given up after
  NO_METADATA_MAX_TRIES (6). UNAVAILABLE is in Q.FETCH_DUE (retried at its next_at) and not in stall.WAITING
  (unchanged code), so a stub never raises the stall line.
- Any probe with one fact keeps its old path (an upcoming stream: is_upcoming with its start; a VOD missing its
  timestamp: "no publish time measured" as before).

## What to check
- No real video can be read as a stub (each kind of real answer carries at least one of FACT_KEYS).
- A stub is never waiting, never mined, retried no more often than before, and given up.

Suite: tests/ingest 434 passed (3 new in test_r121.py). Mutations M44-M47: 4 of 4 killed.
