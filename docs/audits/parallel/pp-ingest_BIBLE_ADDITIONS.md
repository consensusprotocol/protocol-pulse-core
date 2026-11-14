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

### INGEST-FAIL-08: A spend tripwire wired as an availability check halts the leg it was meant to watch
**Evidence (integrator merge audit B1, 05:02 ET Nov 12; reproduced on 753dec1d):** `Router.available` returned "not
available" while the meter was not 'ok', so at 90 % of the cap, and whenever the spend was merely unmeasured (a failed
or stale /credits read), the metered gateway was skipped. With it alone in the chain (the spend freeze leaves exactly
that) the chain halted with 0 calls; the 90 % state never clears, so it would have stayed halted.
**Rule:** a NOTIFY is a notice plus a preference, never a removal: the metered back-ends move to the end of the chain
(others first where any are callable) and keep mining. "Nothing measured is never a pass" means the notice is written,
not that the work stops.
**Detection:** tests/ingest/test_providers.py `test_the_tripwire_notifies_and_moves_the_metered_back_end_last_never_out`,
`test_an_unmeasured_spend_is_never_read_as_below_the_tripwire_and_never_halts`; the old-code reproduction:
docs/audits/parallel/pp-ingest_audit/integrator_c1/mustfail_old_753dec1d.json.

### INGEST-FAIL-09: A retry limit that counts outages turns a long outage into permanent, silent loss
**Evidence (integrator B2; reproduced on 753dec1d):** 8 passes x 10 min: a pure outage of 80 minutes (every back-end
refusing, no reply at all) moved a video to `mined_partial` with `next_at` 32 years ahead and 0 ledger lines, and the
coverage check counted it as mined (1/1).
**Rule:** tell an OUTAGE (nothing answered: skipped, down, overloaded, refusing access) from a REJECTION (a back-end
answered and the reply was refused). An outage waits as long as it lasts and uses no try; only rejections count, and
even then the video stays retryable and is never counted as covered.
**Detection:** tests/ingest/test_service.py
`test_every_back_end_down_for_any_number_of_passes_waits_without_a_try_then_completes` (13 passes),
`test_rejected_windows_become_partial_retryable_and_never_counted_as_mined`,
`test_coverage_never_counts_a_partial_or_waiting_video_as_mined`; the live-component drill under the spend freeze:
docs/audits/parallel/pp-ingest_audit/drill_freeze_20261112.json.

### INGEST-FAIL-10: A rate-limit marker that is a prefix of a per-video refusal stalls every channel
**Evidence (integrator B4; reproduced on 753dec1d):** the bot-check marker "Sign in to confirm you" is a prefix of the
age gate's "Sign in to confirm your age". One age-gated video tripped the global yt-dlp breaker (600 s), was requeued
as a rate limit forever, and since nothing called `calm()` each later trip escalated to the 60-minute pause.
**Rule:** match the specific per-video refusal (age gate) first and make it terminal for that video; match the
generic marker on its distinctive words ("not a bot"); every answer that is not a rate limit calms the breaker.
**Detection:** tests/ingest/test_watch_fetch.py TestYouTubeGateAgeGate.

### INGEST-FAIL-11: A price-table estimate overstated a vendor's cost 7x while the vendor reported the real one
**Evidence (06:10 ET Nov 12):** the A/B judge (35 xAI calls) was recorded at $3.22 from the config's upper-bound
estimate ($5 / $25 per MTok, hidden reasoning counted as output); every reply carried `usage.cost_in_usd_ticks`
(1 USD = 1e10 ticks, xAI's cost-tracking reference) totalling $0.45.
**Rule:** record the vendor's own per-call cost when it reports one (`usage.cost`, `usage.cost_in_usd_ticks`); the
price table is only the fallback for vendors that report none, and its basis is recorded with every figure.
**Detection:** tests/ingest/test_providers.py `test_a_vendor_reported_cost_in_ticks_is_the_recorded_cost`.

### INGEST-FAIL-12: Merging two observations of one moment kept the first and dropped the second's risk flags
**Evidence (integrator, non-blocking; reproduced on 753dec1d):** a range seen from two overlapping windows kept the
first window's flags; the second window's `ad_read`, `names_person` and `altcoin` were discarded, so a hard-excluded
moment (law L-u) could be served.
**Rule:** observations of the same moment merge fail closed: the union of the risk flags, names_person and altcoin,
the conjunction of about_bitcoin.
**Detection:** tests/ingest/test_mine.py `test_a_range_seen_twice_keeps_every_observations_flags`.

### INGEST-FAIL-13: A fixed window overlap re-sent text up to 3x when sentences were huge
**Evidence (freeze audit c2, glm N8; measured 07:15 ET Nov 12):** the next window started `overlap` sentences before the
end of the last one, but at least one sentence after its start; with sentences of ~250 words a 900-word window holds 3,
so each window advanced ONE sentence: 60 such sentences made 58 windows and sent each sentence 3 times (no window
ceiling in the service: cost and time grew with the redundancy, not with the content).
**Rule:** an overlap is a fraction of the window it overlaps (at most half), so every sentence is sent at most twice;
never a window cap, which would drop content. Measured on the staging store: 0 of 1,208 windows change (all hold >= 12
sentences), so no stored reply is invalidated.
**Detection:** tests/ingest/test_mine.py `test_windows_of_huge_sentences_never_walk_one_sentence_at_a_time`.
**See also INGEST-FAIL-04:** the same hidden-reasoning budget trap hit two audit reviewers served by the gateway
(glm-5.3-flash, minimax-m3.1-flash: empty, finish_reason length, on a 100k-token package); glm answered at reasoning
effort none, minimax ignored the setting (empty again). A reviewer or miner on a reasoning model is configured with
its reasoning off, and an empty answer is recorded with its cost, never as a review.

### INGEST-FAIL-14: Hard flags the miner set without meeting their definition kept good moments from the packager
**Evidence (orchestrator ruling 40, 03:13 ET Nov 13; measured 03:25-05:25 ET):** the builder's funnel showed the hard flags
removing 123 of 682 rows in 24 h; "imperative" was set on "So if you think about it, stablecoins are going to
continue growing ...", which tells the viewer nothing. A second model asked one narrow question per flag with the
ruling's definition: the miner's imperative agreed 73 % of the time (41/56), accusation 52 % (68/130), single_source_breaking 67 % (20/30). The wrong ones are predictions, the speaker's own trades and rhetorical "look / listen" (imperative); any negative mention of a named party, a hack's victim included (accusation); attributed claims and history (single_source_breaking). Putting the ruling's definitions into the miner's prompt did not raise imperative or accusation precision on the same windows (87 -> 89 %, 60 -> 59 %). The miner's prompt (mine/2) asks for 11 flags at once inside a 40-sentence
extraction and says "When unsure whether a risk flag applies, set it"; observations of one range are merged as the
union of their flags (INGEST-FAIL-12).
**Rule:** a hard flag (law L-u) is a claim about the words of the moment under a WRITTEN definition; its precision
against that definition is measured by a second model of another family (never the miner) on a sample, and the
exclusion it causes is reported with that precision. L-u stays hard; a wrong label is not L-u. Nothing is cleared
without the orchestrator's ruling.
**Detection:** `tools/ingest_watch.py flagcheck` (report: docs/audits/parallel/pp-ingest_FLAG_PRECISION.md);
tests/ingest/test_flagcheck.py. A second model's "no" is not automatically safe: on accusation it missed insinuations against identifiable parties, so its answers are read cell by cell before any rule trusts them.

### INGEST-FAIL-15: A checker with its reasoning off said "yes" to quotes that do not meet the definition
**Evidence (03:2x ET Nov 13):** on 24 quotes with a clear answer under ruling 40's definitions, glm-5.3-flash at
reasoning effort none (the setting that made it usable as a long-package reviewer, INGEST-FAIL-04) scored 21/24: three
false "yes" (a speaker's own purchase as an imperative; a historical fact and a price prediction as single-source
breaking news); at effort low 22/24; at its default reasoning 24/24 (about 300 reply tokens, median 26 s, on short
prompts). The muse model answered 20/20 of what it returned but 4 of 24 calls failed (provider 502).
**Rule:** a model that judges another model's labels is calibrated first on known cases and its score is reported
with its table; its reasoning setting is chosen by that score, per prompt length (off for 100k-token packages, where
reasoning empties the reply; default for one-question prompts).
**Detection:** `flagcheck.calibrate` runs before every check; the calibration table heads the report.

### INGEST-FAIL-16: A notice writer took any read error of the STATE file for an empty file
**Evidence (audit r87 c1, its replies at 02:10 ET Nov 14):** `spend._rewrite_top`, which puts the NOTIFY lines at the top of the
STATE file under a lock, read the file with `except OSError: text = ""`: a STATE file that EXISTS but cannot be read
(permissions, an I/O error) would have been rewritten as the notice alone, the whole file lost. It had been there
since the first notice writer; ruling 87 added two more writers to it, which is how a reviewer came to read it.
**Rule:** only a MISSING file may start empty; any other read error raises, the caller logs it and tries again later,
and nothing is ever rewritten from what could not be read (law L-j). A writer that clears a notice clears its own
record only after the notice is gone.
**Detection:** tests/ingest/test_signal.py `test_a_state_file_that_cannot_be_read_is_never_rewritten_from_nothing`
(a chmod 000 STATE file: the writers raise, every line kept).

