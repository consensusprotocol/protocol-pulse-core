# pp-ingest: a second caption source, and what the 429s correlate with (DESIGN ONLY, nothing built)

The orchestrator's ruling of 13:05 ET Nov 16: "Longer term, design (do not build yet) a second caption source that does
not depend on this machine's YouTube quota, and say what the 429s correlate with (request rate, the six sessions sharing
one IP, the hook pass re-fetching)."

## 1. What the 429s correlate with (measured from the records; Nov 15 00:00 to Nov 16 13:30 ET)

Sources: the watcher's queue (every listing cycle, every fetch state change), the attempts logs of both transcript
stores (this watcher's and the pipeline's), the pipeline ingest's run log (ingest_runs.jsonl), service.log, and the other
services' logs on this machine. Script: the session scratchpad's caps/traffic.py.

| hour ET (Nov 16) | watcher listing | listing time a cycle | watcher probes | watcher captions | pipeline captions | pipeline Whisper (YouTube audio) |
|---|---|---|---|---|---|---|
| 05 | 384 yt-dlp playlists | ~85 s | 5 | 3 ok | 3 ok | 0 |
| 06 | 384 | 85 s, then 168 / 176 s | 7 | 5 ok | 5 ok | 0 |
| 07 | 320 + 64 RSS | 166 / 225 s, then ~91 s | 5 | 1 ok, 1 refused (07:47) | 1 ok | 0 |
| 08 | 179 + 205 RSS | (gate) | 12 | 3 refused | 2 refused | 2 ok |
| 09-12 | mixed (gate) | | 8-14 | 4-23 refused | 3-12 refused | 2-12 ok |

- REQUEST RATE, THIS WATCHER: steady, and not new. 384 yt-dlp uploads-playlist listings an hour (64 channels every
  10 min, since playlist-first went live at 11:56 ET Nov 14), 4-12 probes and 1-8 caption downloads an hour. The same
  rate ran 44 hours with no 429. It was not the trigger alone. It is the largest steady source measured, and the
  cheapest to cut (section 3).
- THE ENDPOINT: only the caption endpoint (timedtext) refused. The playlist listing and the probes (the player API) were
  answered all day, and the pipeline's audio downloads for Whisper (googlevideo) kept working: 2-12 an hour from 08:00.
- THE IP, NOT A PROCESS: both caption clients on this machine were refused from the same hour (the watcher at 07:47,
  the pipeline's ingest in the 08:00 run), so the limit is per IP. The 429s are not from one session's rate.
- THE ONSET: YouTube slowed this machine before it refused. The watcher's 64-channel listing took about 85 s a cycle,
  then 168, 176, 166 and 225 s between 06:48 and 07:18 ET; it recovered by 07:25. The first caption 429 came at 07:47
  on a Monday morning, the first weekday after a quiet Sunday. That fits this IP's total YouTube traffic crossing a
  threshold. Other callers active then: a render at 06:xx (video_pipeline_v3 output; renders download clips), the
  word-pass worker's audio download for the 06:37 Bankless moments, and the morning's uploads (probes 5 to 12 an hour).
- THE SIX SESSIONS (the machine runs 18 tmux sessions): the processes found calling YouTube from this IP are
  - this watcher: listing, probes, captions;
  - the pipeline's transcript ingest (cron */30): RSS listing, yt-dlp metadata per new video, captions, audio for
    Whisper;
  - the website (waitress) and media_sync: both poll the channels' RSS feeds (the measured rate is in section 1a);
  - the word-pass worker: one audio download per mined video it word-times (it met YouTube's bot check on Nov 13
    08:02);
  - the builder's discovery, scans and runs (pp-selectid discover.py, scan.py, run_fresh.py) and the renders: clip
    downloads.
  Only this watcher and the two transcript stores log each request's time. The website, media_sync, the builder and the
  renders do not, so the IP's total rate at 06:45-07:47 cannot be rebuilt from the records. That is the one thing this
  analysis cannot prove.
- THE HOOK PASS: it never re-fetches. It reads the stored transcript; this watcher's yt-dlp gate is used only by the
  listing (service.py:235), the fetch step (service.py:257/266: probe and captions) and the daily coverage check
  (service.py:771), and no hook-pass path reaches YouTube.

## 1a. RSS polling by the other services
Measured by counting each log's feed requests over 5 minutes (13:16-13:21 ET Nov 16):
- The website (waitress.log) holds 382 feed GETs in its last 3 MB, but its DEBUG lines carry no time; media_sync logs
  feed URLs as query parameters.
- Neither logged a single feed request in that window. They poll in bursts whose times the logs do not keep, so their
  rate around 07:47 is not measurable from the records.
- The fix for the future is in section 3: one shared poller, with each request timed.

## 2. A second caption source that does not depend on this machine's YouTube quota

Requirements, from the laws and the rulings:
- the record names its video and channel and hashes to its sha (transcript_store's format, write-once);
- its times land on the video's own timeline before a clip is cut (the word pass refines words at cut time);
- no outside-vendor spend past ruling 118's $1.00 a day for the whole pipeline;
- no GPU contention with builds (R13: builds first);
- latency within minutes of publish, for the Bitcoin channels first.

| option | independent of this IP's YouTube quota? | cost | verdict |
|---|---|---|---|
| A. The pipeline's Whisper on YouTube audio (exists) | no: audio from this IP (googlevideo, a separate limit, answered all day) and a GPU lease | none | keep as the first fallback (R13) |
| B. The project's existing relay (relay.protocolpulse.io, another network) fetching the caption track | yes: another egress IP | none new; datacenter IPs are often bot-checked by YouTube | worth one test request before any build |
| C. The channels' own podcast feeds (audio from podcast CDNs) + Whisper | yes: no YouTube at all | none (local or CMP Whisper) | RECOMMENDED for the Bitcoin channels with a podcast |
| D. A paid transcript API | yes | an outside vendor: counts against ruling 118's $1/day | only if C and B fail |
| E. Signed-in requests (cookies) | no: same IP, and the account is at risk | none | no |
| F. Another machine on this LAN (CMP box, bifrost) | no: same public IP behind the same router | none | no for fetching; yes for Whisper compute |

THE RECOMMENDED DESIGN (C, with B as a cheap first test):
1. A registry field `podcast_feed` for the tier 1-2 channels that publish the same episodes as a podcast. Most of tier
   1 do: What Bitcoin Did, TFTC, Stephan Livera, Bitcoin Audible, The Investors Podcast, Preston Pysh, Natalie Brunell,
   Robert Breedlove, Saifedean Ammous, Unchained. In tier 2, Marty Bent, Scott Melker and Real Vision.
2. A poller (RSS with If-None-Match, as watch.rss_list) matches each episode to its YouTube video by the canonical title
   (canon.canon_tokens, as fetch.title_canon), the publish time within a window, and the duration within a tolerance.
   An episode that does not match one video is never used.
3. The episode's audio (podcast CDN, no YouTube) is transcribed by Whisper. Compute options: the CMP box (192.168.1.121,
   its own GPUs, outside Ultron's leases; its disk is ~95% full, so audio is streamed and deleted), or a free Ultron card
   under its lease. The record is `transcript.podcast_whisper.json` with the source URL, media_sha256 and the matched
   video id, written through transcript_store's writer into this store, ranked below a caption or Whisper record of the
   video itself.
4. TIMELINE: a podcast cut differs from the video (dynamic ad slots, intros), so its times are not the video's. Rows
   mined from it carry `timing: "podcast"` and the text. The word pass (the integrator's), which already downloads the
   video's audio at cut time, finds each moment's text in the video's own audio before a clip is cut. That needs a wider
   search window for podcast-timed rows, or one whole-video Whisper on GPU1 for videos with such rows: the contract to
   agree with the integrator. Until the word pass places a row on the video's timeline, the builder never cuts it.
5. Rollout, each step audited: (a) map the feeds; (b) measure the podcast's lag behind YouTube on a week of episodes (if
   the podcast comes out hours later, it is no help for "minutes", and B or A must carry the latency); (c) prototype the
   match and the Whisper on the CMP box; (d) agree the timeline contract with the integrator; (e) audit, then live.

## 3. Cutting this machine's YouTube footprint (complementary; not built)
- The watcher lists by activity: a channel that has uploaded in the last 48 h every 10 min; a quiet one every 30 min.
  Most of the 64 channels upload 0-3 times a day, so the 384 playlist listings an hour fall by more than half, keeping
  playlist-first's measured speed for active channels.
- One shared RSS poller for the website, media_sync, the pipeline's ingest and this watcher (all poll the same channel
  feeds), writing one cache the others read.
- The daily coverage check reads RSS instead of re-listing 64 playlists through yt-dlp.
- Any process that gets a 429 or a bot check from YouTube writes one shared breaker file per endpoint (captions, player,
  audio) that every other process reads; r118 already reads the pipeline's caption breaker.
