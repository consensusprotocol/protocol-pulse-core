# pp-ingest: failure patterns for the Qwen bible (the integrator folds them in; numbering is the integrator's)

Session pipeline_pp_ingest, branch pp-ingest. Each entry: evidence (measured), root cause, fix or request, detection.

### INGEST-FAIL-01: A write-once metadata record froze every livestream first seen while live (46 videos skipped for days)
**Evidence (02:40 ET Nov 12, read-only on /home/ultron/protocol_pulse/data/editorial):** 46 `meta.json` records carry
`live_status: is_live` and are skipped on every 30-minute ingest (`attempts.jsonl`: "skip: live_status is_live"), some for
three days: Scott Melker 4g14stSOpjg (first seen 2026-11-09 14:30 UTC, 106 skip attempts to 2026-11-12 05:30), Bitcoin
Magazine nKt44oQb840 (113), Simply Bitcoin 1QSjaOtZl4g (82), BTC Sessions gSo8S5riS5Q (85), Digital Asset News
c8Me61Vk7P0 (88). yt-dlp now reports these streams as `was_live` VODs with English auto captions (checked on
tB85PzNA99I: `was_live`, 1,787 s, `en-orig` + `en`).
**Root cause:** `transcript_store.ensure_meta` writes `meta.json` once ("refreshed only by appending to meta_history",
which no code does); `acquire()` reads the frozen `live_status` and returns `skipped_live` forever. The same freeze hits
captions: a video whose auto captions did not exist yet at first sight is recorded with `captions_auto_en: []` and
never re-checked (it goes to Whisper on the main path, never to captions).
**Fix / request:** pp-ingest never writes `meta.json` while a video is live, upcoming, post-live or without captions;
it re-probes on a schedule (docs/audits/INGEST_DESIGN.md section 3). For the main path: REQUESTS R1.
**Detection:** tests/ingest/test_fetch.py `test_a_live_stream_is_reprobed_never_frozen`; the daily coverage report lists
every partner video still waiting, with its live status.

### INGEST-FAIL-02: The yt-dlp listing fallback reads the /videos tab, which has no livestreams and no Shorts
**Evidence (02:45 ET Nov 12):** YouTube RSS (`feeds/videos.xml`) answers HTTP 404 for every registered channel (as on
2026-11-07). The fallback `scan.fetch_uploads_ytdlp` lists `/channel/<id>/videos`: for Scott Melker its newest entry is
2026-11-08, while his uploads playlist (`UU` + id) shows three `was_live` daily shows since (tB85PzNA99I, pW6IT6Jnljw,
4g14stSOpjg) and five Shorts. With RSS down, the selector's universe silently loses every partner livestream.
**Root cause:** YouTube splits a channel into tabs (/videos, /streams, /shorts); only the uploads playlist lists all.
**Fix / request:** pp-ingest lists `https://www.youtube.com/playlist?list=UU<id[2:]>` (one request, every upload with
`live_status` and duration). For `scan.fetch_uploads_ytdlp`: REQUESTS R2.
**Detection:** tests/ingest/test_watch.py `test_uploads_playlist_url_and_parse` (a `was_live` entry is discovered);
the coverage report's per-channel listing.

### INGEST-FAIL-03: A livestream VOD's yt-dlp `timestamp` is its processing time, not when it was said
**Evidence:** tB85PzNA99I (Scott Melker): `release_timestamp` 2026-11-11T14:00:43Z (the stream), `timestamp`
2026-11-12T02:31:38Z (12.5 h later). `ensure_meta` takes `timestamp` when there is no RSS time, so a stream's
time-sensitive language ('today', price levels) would be dated 12 h late (law L-v 3).
**Fix:** pp-ingest's `published_at` for a livestream VOD is `release_timestamp` (source named in
`published_at_source`); both times are kept in the meta record.
**Detection:** tests/ingest/test_fetch.py `test_live_vod_is_dated_by_its_stream_start`.

### INGEST-FAIL-04: "reasoning effort low" let qwen3.8-27b spend the whole reply budget thinking on a long prompt
**Evidence (03:05 ET Nov 12, Heimdall staging, one mining window of Yahoo Finance 36HPi9UZPOc, 2,169 prompt tokens):**
effort `low`, max_tokens 4,000: HTTP 200 after 100.7 s with EMPTY content, `finish_reason: length` (every token went to
hidden reasoning). Effort `none`: 19.9-20.1 s, 718-727 completion tokens, valid JSON, $0.0007-0.0008. The replay v3
report's "batch 2, effort low, 0 % failures" was measured on short extraction prompts; it does not carry over to a
longer instruction prompt.
**Rule:** an HTTP 200 is not an answer: an empty content or `finish_reason: length` is a failed call (providers.py
raises `empty`), and a reasoning effort is chosen per prompt by measurement, recorded in providers.json with its
evidence.
**Detection:** tests/ingest/test_providers.py `test_empty_content_with_length_is_a_failed_call`.

### INGEST-FAIL-05: A circuit breaker that re-read the outage's failures re-opened the moment the back-end recovered
**Evidence (03:55 ET Nov 12, tests/ingest/test_service.py `test_every_back_end_dead_videos_wait_then_complete`):** after
every back-end failed (the outage) and then answered again, the videos stayed waiting: "circuit open (7/10 failures)".
`Health.record` judged the failure-fraction rule on EVERY event, successes included, over a window still full of the
outage's failures, so the first successes re-opened the breaker for another 5 min per recovery (a flapping fallback).
**Fix:** failure rules are judged only on a failure, the latency rule only on a success, and a success that closes the
circuit starts a fresh window.
**Detection:** tests/ingest/test_providers.py `test_a_recovered_back_end_is_not_reopened_by_the_outages_old_failures`,
`test_a_success_never_trips_the_failure_rules` (both fail on the old code: verified by swapping the old `record` back in).

### INGEST-FAIL-06: A prefix fingerprint calls different videos with the same long intro "the same video"
**Evidence (audit cycle 2, 2026-11-12):** `text_fingerprint` hashed the first 400 canonical tokens (about 2-3 min of
speech). A channel opening every episode with the same sponsor read or standard intro would have each new episode
marked a re-upload of its first one and never mined: silent, permanent loss of the channel. Measured before the fix:
no collision yet (600 main-store and 113 staging caption records).
**Rule:** an identity fingerprint covers the whole object it identifies, never a prefix chosen for speed.
**Detection:** tests/ingest/test_watch_fetch.py `test_a_shared_long_intro_is_not_a_reupload_but_the_same_speech_is`
(fails on the prefix version).

### INGEST-FAIL-07: YouTube's RSS is a 15-minute cache: a 10-minute poll still discovers an upload up to ~25 min late
**Evidence (08:51 UTC Nov 12):** feeds answer `Cache-Control: public, max-age=900` with `Age` up to 240 s and no
ETag / Last-Modified (so conditional GETs never apply). Two uploads published 08:30 were absent from the 08:36 and 08:45
reads and present at 08:54 (discovered 24 min after publish).
**Rule:** the coverage check reports a not-yet-listed upload younger than poll + cache as "inside the discovery
window", never as a watcher miss and never as covered; "time from publish to mined" includes this delay.
**Detection:** tests/ingest/test_ledger_coverage.py TestCoverage (a 10-minute-old unlisted upload is reported inside
the discovery window).
