# r118: the stalled miner (the orchestrator's 10:50 ET order of Nov 16), rulings 118 and 119 (3)

## The order (verbatim, the parts this change answers)

"(1) NOW: find why those 14 are not mined (transcripts not fetched or not transcribed? the miner waiting on a route? a
job that only runs on a timer? the GPU0 lease? the false Plan B switches leaving it between routes?) and mine them,
newest conversations first, ON HEIMDALL. Say the cause in one line on line 1 of your STATE as soon as you know it, then
fix it properly, audit-first on Heimdall only.
(2) THE TERMS HAVE CHANGED (ruling 118, PBX 05:25 ET today): outside vendors are capped at $1.00 A DAY for the whole
pipeline and $0.58 is already spent, so the miner's PAID ROUTE IS CLOSED: Plan B for mining is no longer Grok or Gemini.
It is the next Heimdall model (qwen, then deepseek 4.1, minimax, gemma, gpt-oss, mimo; never glm or muse), then the
local model on a free card under the lease. Heimdall is free and effectively unlimited for us; a video may wait
minutes, never hours. glm is out of every chain (ruling 119 (3)).
(3) NO MORE FALSE OUTAGES: the outage clock is fed only by YOUR OWN mining and probe calls, never by another session's
deadline misses, and any answered call or probe resets it (ruling 87 as amended). Land that with (1).
(4) SELF-CHECK: if videos are waiting and nothing has been mined for 30 minutes, write it on line 1 and act; do not sit
idle at the prompt."

## The cause (measured, Nov 16)

- From 07:47 ET YouTube answered HTTP 429 ("Unable to download video subtitles ... Too Many Requests") to EVERY caption
  download from this machine: 12 tries 07:47-10:37 ET, none ok (the last ok 07:18 ET). The main tree's own transcript
  ingest (cron */30, pipeline/transcript_ingest.py: captions, else Whisper on GPU0) got the same 429s (its breaker file
  data/editorial/state/caption_circuit.json: "HTTP 429 on lcYYuefFMQA" at 10:00 ET) and transcribed most of the same
  videos with Whisper.
- The watcher has no transcript path but captions (no Whisper, no GPU), and fetch._store_captions TRIPPED THE WHOLE
  yt-dlp GATE (watch.YouTubeGate, 10 / 20 / 40 / 60 min) on every caption refusal, even a refusal made by
  transcript_store's own 30-minute caption breaker with NO request (fetch_captions returns "throttled" at once while
  caption_circuit_open(), pipeline/transcript_store.py:208 and :249-261). So the probes, which YouTube still answered
  (the uploads-playlist listing too: 59-64 channels listed in the same cycles), stopped as well: 9 videos sat in
  probe_retry ("rate_limited: yt-dlp breaker open for 389 s") and 5 in captions_pending. Nothing reached the miner from
  07:18 ET. Not the miner (Heimdall qwen answered at 06:37 ET), not its route, not the GPU lease, not a switch (none since
  Nov 14).
- Done at 10:53 ET by hand (a one-off with the watcher stopped, the watcher's own fetch.process): the pipeline's 7
  Whisper records were copied in, the videos probed and mined on Heimdall qwen at once (5 moments: Strategy 2, Fox
  Business 3; the other 5 had no Bitcoin-bearing window).

## The change

1. fetch.py: THE PIPELINE'S OWN TRANSCRIPT. After the probe's checks (channel, Short, upcoming, live, publish time, age,
   duration, title duplicate) and BEFORE the caption check: pipeline_transcript() reads the main tree's store
   (config.MAIN_STORE/transcripts/<id>/transcript.*.json, READ ONLY; fetch.PIPELINE_STORE) and takes the best record by
   transcript_store.METHOD_RANK that names this video and this channel, is filed under its own method's name, has
   segments, and whose segments hash to its transcript_sha256. take_pipeline_transcript() copies it byte for byte into
   this store (tmp file, re-read and re-hashed, then os.link: write-once; a record of that method already here is kept),
   logs an attempt and a queue event; _store_captions then finds it (canonical_transcript) and marks the video
   transcribed without any download. Also when a VOD lists no English captions (BLOy6SetrUs, Yahoo Finance).
2. fetch.py: A CAPTION 429 STOPS THE CAPTIONS ALONE. No gate.trip on a caption refusal (the gate stays tripped by a
   probe's or a listing's own 429 / bot check: watch.YouTubeGate.run, pipeline/ingest/watch.py:60-71, unchanged); the
   video is tried again in CAPTION_THROTTLED_RETRY_S (600 s, was 1800), the pipeline's store looked at first. While the
   PIPELINE's caption breaker is open (its ingest was refused in the last 30 min: same machine, same IP), no download is
   tried here either (pipeline_captions_refused, its file read only). Inside the moments' life (config.EXPIRY_H, 12 h) a
   VOD without English captions is looked at every 30 min at most (_caption_retry_at), the pipeline's ingest period.
3. downsignal.py + config.py: THE OUTAGE CLOCK IS THE WATCHER'S OWN. The builder's module (pp-selectid
   pipeline/heimdall_health.py: note :141, the 15-minute rule _down_rule :176, probe_due :204, probe_result :230,
   unchanged and used through its API only) now runs on config.paths()["signal_state"]
   (data/editorial/ingest/down_signal_state.json), never its shared STATE: only this watcher's own calls are noted, only
   its own probes claim slots, only its own switches reach STATE line 1. probe_due is called without `families` (no other
   prober shares the file, so a slot left "to the prober that can ask a failed family" would never be taken: the clock
   would run to 15 min on an answering gateway). The probe role asks one back-end per family the watcher calls (as since
   10:05 Nov 14): qwen, deepseek, minimax, gemma, gpt-oss, mimo, muse; any answer resets the clock (the module, unchanged).
4. providers.json: RULING 118 / 119 (3). mine, hook and spotlight chains: qwen, deepseek 4.1, minimax, gemma, gpt-oss,
   mimo (all served by the Heimdall gateway, vendor "heimdall"), then local_gemma (still "enabled": false; available only
   while this process holds the GPU0 lease: OllamaLocalBackend.enabled, pipeline/ingest/providers.py:494, unchanged). The
   paid route (paid_route, the mine_paid role) removed: service.mine_once and downsignal._route_tick already do nothing
   without paid_route. glm's two back-ends "enabled": false and in no chain; the flag check is muse then deepseek
   (ruling 40's per-row rule, flagcheck.checkers, pipeline/ingest/flagcheck.py:244, unchanged: never the miner of the
   row's video, by back-end and by model; deepseek answers only once the watcher's live calibration passes it).
5. stall.py + spend.py + service.py: THE SELF-CHECK. A video inside its 12 h in a state that leads to mining
   (discovered, probing, probe_retry, captions_pending, transcribed, mining, mine_waiting; never upcoming or live) is
   waiting; a stall is something waiting and nothing mined for 30 min (the later of the newest mined_ts and the oldest
   waiting discovery is 30 min old). The health loop then writes "MINING STALLED SINCE HH:MM ET: n VIDEO(S) WAITING ...:
   <counts by what each waits on>; ACTED HH:MM ET: m MADE DUE NOW ..." at the front of STATE line 1 (after the batch
   spend and an alarm, before the switch line; one segment, its writer refuses '|' and newlines; text stable while the
   stall lasts) and ACTS: every waiting video in a retry state whose next try is later is made due now (never one in
   flight), when found and again every 30 min; the line goes when the stall ends.
6. tests/ingest/xllm_audit.py: this audit's reviewers are qwen + muse (glm excluded by name: ruling 119 (3)); the third
   family is mimo.

## Live check of the new chain (Nov 16 ~11:30 ET, the watcher's own mining question and validator, 1 window each of
Vu0XZSz-aj4 and DO6iIRbccIg, no stored replies): minimax 2/2 valid (57 s), mimo 2/2 valid (25 s), gpt-oss 1/2 (one
reply's reason over 160 characters: invalid, the router's next attempt), deepseek and gemma no answer within their 300 /
240 s deadlines at the time (the chain moves on; their breakers open after 5 failures).

## What to check (the laws below apply)

- The main tree is never written: the pipeline's store and its breaker file are only read (open for reading, glob,
  shutil.copyfile FROM them). A record is never taken without every check; the bytes linked in are the bytes checked.
- No video skips the probe's checks (Short, live, upcoming, too old, too long, duplicate) because a record exists.
- The gate still stops every yt-dlp call on a probe's or a listing's 429; a caption 429 can no longer stop the probes.
- The watcher's clock can no longer be started or moved by another session; its own failure still starts it and any
  answer (call or probe) resets it; a slot is never left unclaimed on its own file.
- No glm in any chain; no muse in mine / hook / spotlight; no paid route; no frozen vendor callable.
- The stall line: never on line 1 when nothing waits or something was mined in the last 30 min; never splits or folds
  the switch line; the act never touches a video in flight and acts at most every 30 min.
- Tests never read the real main-tree store (conftest points fetch.PIPELINE_STORE / PIPELINE_CIRCUIT at a temp dir).

Suite: tests/ingest 414 passed. Mutations (scratch copy, files restored from backups): 17 of 18 killed; M17 (no early
return when a record of that method is already here) is equivalent: the write-once os.link refuses it the same way.
