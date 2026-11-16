# pp-ingest: requests for the integrator (files pp-ingest does not own)

Each: file, function, the change, the evidence. pp-ingest has not edited any of these files.

## R1 pipeline/transcript_store.py `ensure_meta` / `acquire`: never freeze a live or caption-less video (INGEST-FAIL-01)
`ensure_meta` writes `meta.json` once; `acquire` then returns `skipped_live` forever for a video first seen live (46 in
the main store on 2026-11-12, some skipped 113 times over three days; Scott Melker, Bitcoin Magazine, Simply Bitcoin,
BTC Sessions, Digital Asset News daily shows among them) and never sees auto captions that appeared after the first
look. Change: in `acquire`, when the stored meta has `live_status` in (`is_live`, `is_upcoming`, `post_live`) or no
English captions listed, re-probe (`yt-dlp -J`) and append the new probe to a `meta_history` list in a NEW file
(`meta.<UTC-time>.json`, write-once) that `ensure_meta` prefers when newer; keep `meta.json` immutable. Proof that it
works: pipeline/ingest/fetch.py re-probes on a schedule and transcribed three of the frozen Scott Melker streams
(tB85PzNA99I, pW6IT6Jnljw, 4g14stSOpjg) from captions on the first try (docs STATE 03:31).

## R2 pipeline/scan.py `fetch_uploads_ytdlp`: list the uploads playlist, not the /videos tab (INGEST-FAIL-02)
`https://www.youtube.com/channel/<id>/videos` has no livestreams and no Shorts. Change the URL to
`https://www.youtube.com/playlist?list=UU<channel_id[2:]>` (same flags). pipeline/ingest/watch.py `playlist_list`
does this and reads `live_status` and `duration` from the same listing.

## R3 pipeline/transcript_store.py `ensure_meta`: date a livestream VOD by its stream start (INGEST-FAIL-03)
`published_at` falls back to yt-dlp `timestamp`, which for a `was_live` video is the VOD processing time (12.5 h after
the stream for tB85PzNA99I). Change: for `live_status` in (`was_live`, `post_live`) use `release_timestamp`, with
`published_at_source = "yt-dlp release_timestamp (stream start)"`.

## R4 pp-selectid (pipeline/trend_brief.py TAXONOMY; the risk enum)
- Publish TAXONOMY: the miner then fills `topics` (today `[]`, `source.topics_status` says why). A prompt change; old
  lines keep `[]`.
- The contract's `risk` enum has no "altcoin" / "not about Bitcoin" value; the miner carries them in
  `flags_ext.altcoin` / `flags_ext.about_bitcoin` (fields may be added) and the adapter
  (`pipeline.ingest.ledger.best_unused_moments`) excludes both before returning a moment. If the packager reads the
  ledger directly instead of through the adapter, it must apply the same two exclusions.
- Measured on the 03:20 smoke (112 moments, three Scott Melker streams): `eligibility` (role clip, at mining time)
  returned `no_bitcoin` for 59 (the moment is about Bitcoin by the model's flag but does not say the word; T11 needs
  the word) and `too_many_sentences` for 8 (T9: at most 3 sentences; the miner allows 5). Both are the packager's
  rules to keep or bend (law L-o); the miner records them, never relaxes them.

## R5 pipeline/optout.json (PBX 02:35: an opt-out registry the selector honours)
The miner honours it when present: a JSON list of channel ids, or `{"channel_ids": [...]}`. Absent = nobody opted
out. Unreadable or another shape = fetching and mining pause (fail closed) and the reason is logged; listing continues.

## R6 Wiring (the integrator's act; docs/audits/INGEST_DESIGN.md section 10)
1. Merge `pipeline/ingest/`, `tools/ingest_watch.py`, `tests/ingest/`. The contract modules (pp-selectid's
   `pipeline/eligibility.py`, `pipeline/select_by_id.py`) are imported from `pipeline/` once merged; pre-merge they
   are read from the pp-selectid worktree (`PP_SELECTID_PIPELINE`).
2. Transcripts: `tools/ingest_watch.py handoff --main /home/ultron/protocol_pulse/data/editorial` (dry run lists
   absent files with verified hashes; `--apply` copies, never overwrites).
3. To run inside the main tree: `PP_INGEST_ALLOW_MAIN_STORE=1 python3 tools/ingest_watch.py run` in its own tmux
   (the store guard refuses the main tree without it). The main tree's own cron ingest
   (`pipeline/transcript_ingest.py`, every 30 min, captions + Whisper on GPU0) is unchanged by this branch.
4. Local model (law L-x, ULTRON FIRST; integrator B3, 06:xx ET): no environment string stands in for custody any more.
   The local back-end is available only while the process holds the GPU0 lease (`gpu0.held()`, a check, never an
   acquisition) and `"enabled": true` is set for it in `pipeline/ingest/providers.json`; `story_semantics.LocalLLM`
   (main 4867a74a) takes `gpu0.require` + `swap_to` on every request, and `Router.release()` unloads the model when a
   cycle ends (the watcher: whenever its mine loop is idle; the A/B: at the end of the run). Without pipeline/gpu0.py
   (this worktree before the merge) the back-end is never available. A/B on the same 30 videos, inside the lease's
   custody: `python3 tools/ingest_watch.py ab --video-list <AB dir>/videos.json --backends local_gemma,heimdall_qwen27b
   --enable local_gemma`. Under the spend freeze (orchestrator 05:30) the judge role's back-ends (xAI, Google,
   Anthropic) are frozen: pass `--judge <a back-end of another model family>` or `--no-judge` (see R9).
5. Spend freeze (orchestrator 05:30 ET): `providers.json` `spend_freeze.vendors` = openai, anthropic, xai, google; the
   mine chain is heimdall_qwen27b -> local_gemma. Lifting it: remove the vendor(s) from `spend_freeze` and restore the
   mine chain's frontier tail (it was local_gemma -> heimdall_qwen27b -> anthropic_frontier -> xai_frontier), then
   restart the watcher.

## R7 The 3 h VOD ceiling
`transcript_store.MAX_DURATION_S` (3 h) excludes long partner livestreams from the selector's universe. pp-ingest
captions VODs up to 6 h (no Whisper cost on this path) and records longer ones as `too_long`. Whether the selector
keeps 3 h is the integrator's call; the ledger carries the moments either way.

## R8 transcript_store: make the five private functions this branch calls public (integrator, non-blocking)
pp-ingest writes the SAME record format by calling the store's own writer, which today means private names:
`ts._ytdlp`, `ts._vdir`, `ts._write_once`, `ts._store`, `ts._log_attempt` (and `LocalLLM._post` for the local
back-end). Proposed: public aliases in `pipeline/transcript_store.py` (`ytdlp`, `video_dir`, `write_once`,
`store_record`, `log_attempt`) and `LocalLLM.post`, then this branch switches to them. Until then a rename in those
files breaks pp-ingest's fetch and local mining (tests/ingest/test_store_contract.py and test_watch_fetch.py fail
first, by design).

## R9 A judge under the spend freeze (law L-x: generator and judge are different models)
The `judge` role's chain (xai_frontier, gemini_frontier, anthropic_frontier) is entirely frozen, so a blind A/B can
run only with `--no-judge` or a judge of another model family that is not frozen. Heimdall serves other families at
gateway prices (GET /models, 2026-11-12: z-ai glm-5.3-flash, minimax-m3.1-flash, meta-models muse-spark-open,
nvidia nemotron-3.5-super-vl, openai gpt-oss-20b, ...). Proposed: after a measured check (the audit of this change used
three of them as reviewers: results in docs/audits/parallel/pp-ingest_audit/freeze/), add the most coherent one to
`providers.json` as a judge back-end (vendor heimdall), first in the judge chain while the freeze lasts. Not done here:
a judge back-end is the integrator's call (it decides what the A/B measures).

## R10 The reply cache's key omits the request's reasoning setting (integrator's call; found during ruling 40)
`providers.Router._key` hashes the back-end id, its model, the prompt, the schema and max_tokens, but not the
back-end's `extra_body` (where Heimdall's reasoning effort and provider routing live). So after a back-end's reasoning
setting changes in providers.json, the replies stored under the old setting are reused as if they came from the new
one. Ruling 40's checker changed glm-5.3-flash from effort none (calibration 21/24) to its default (24/24); its six
stored effort-none replies were deleted by hand before the measured run. Adding `extra_body` (and the anthropic
back-ends' `effort`) to the key fixes it, but every stored reply then stops matching, including the frozen vendors'
replies an A/B re-reads (R6.4, R9), which can no longer be asked again under the freeze. Proposed: add it to the key
when the freeze is lifted, or now with a one-time key migration of the stored replies (a back-end whose config did
not change keeps its replies). Not changed here.

## R11 Ruling 77 item 4: the word-pass worker's tiers become "last 6 h, then 6-12 h", nothing older (the integrator owns the worker)
Orchestrator 18:09 ET Nov 13 (ruling 77, with the builder's ruling 76: a moment is usable only within 12 h of its
video's publish time, then never again). In `pipeline/word_pass_worker.py` today: `FRESH_H, DAY_H = 10, 24` ("the last
10 h first, then the last 24 h, then older") and `HORIZON_H = 72` (the `since` it asks the adapter for). Asked:
`FRESH_H, DAY_H = 6, 12`, no tier after 12 h, and `HORIZON_H = 12`.
What pp-ingest has done meanwhile: the adapter the worker reads (`ledger.best_unused_moments`, run from this worktree)
now refuses every moment 12 h or more after its video's publish time (`expired (rulings 76 + 77 ...)`, the first
exclusion, whatever `since` or horizon the caller passes). So the worker already receives nothing older than 12 h; its
24 h and "older" tiers are simply empty until the constants change. Its temporary audio and window WAVs (deleted by
the worker at the end of each cycle) are also covered by the watcher's purge when a cycle dies and leaves them
(`/tmp/word_pass_*` untouched for 12 h; never a directory a process holds open).

## R12 pp-selectid `pipeline/heimdall_health.py` (ruling 87; the builder's module, non-blocking)
1. Two probers, one streak: `probe_due` reads `last_probe_utc` but does not claim the probe, and `probe_result` stamps
   it only when the probe has answered (up to 60 s per family later). While both the builder's probe thread and this
   watcher's probe run during an outage, both can see a probe due in the same 2-minute slot and both report: "3 answers
   in a row" can then come from 2 rounds (back to Heimdall-first after ~2-4 min instead of ~4-6), and one prober's
   failure resets the other's streak. Proposed: `probe_due` stamps `last_probe_utc` when it answers True (a claim), so
   one probe per slot fleet-wide; `probe_result` keeps the streak rule.
2. `_prepend(state_md, ...)` takes its lock as `state_md + ".lock"`, a file beside the caller's STATE.md (untracked in
   the caller's repo; and a lock the caller's own STATE writers do not take). This watcher therefore passes no
   `state_md` and writes every switch to its own STATE line 1 under its notices' lock (INGEST_DESIGN section 14).
   Proposed: a lock path outside the caller's tree, or a documented `state_lock` parameter.
   THE BUILDER'S ANSWER (Nov 14, after the watcher's restart): (1) AGREED: `probe_due(path, now, who="")` will CLAIM the slot when it returns
   True (stamps `last_probe_utc` = now and `last_probe_by` = who under the same flock; a second prober in the slot
   gets False; a claimer that never reports spends one slot); in its 2-cycle audit, sha to follow. This watcher loads
   the module once at start: it takes the claim up at a restart after that commit, passing who="pp-ingest probe" only
   where the signature takes it (today's version would raise on the keyword). (2) Noted; this watcher passes no
   state_md, so the lock never touches this tree.
   DONE: the builder committed the claim (pp-selectid 11ed255f, audited 2 cycles); this watcher took it up at its
   02:57 ET restart (pp-ingest 4f805fcf, audited 2 cycles in pp-ingest_audit/r87claim/): its probes claim as
   "pp-ingest probe".


## R13 The pipeline's Whisper waits on an idle GPU0 lease (the integrator's; non-blocking; Nov 16 12:43 ET)
Since 07:47 ET Nov 16 YouTube refuses caption downloads from this machine (HTTP 429), so the only transcript path for a
new upload is the main tree's `pipeline/transcript_ingest.py` (cron */30, Whisper on GPU0), whose records pp-ingest
now takes (r118). Its 12:30 ET run deferred every Whisper: "GPU0 lease busy ... held by pin-stage clip scorer
(integrator, GPU0) (pid 136857)". That process is `pipeline/stand_alone_scorer.py serve` (up since ~10:00 ET, 0.1 %
CPU); at 12:43 ET GPU0 showed 18 MiB used and 0 % utilization. GPU1's lease was held by `local_watchdog`. So 5 uploads
waited with no transcript, 2 of them Bitcoin (Bitcoin Magazine uAvmynMSVhM, 19 min; Scott Melker f0NnJM63Ffc, 61 min).
Proposed (the integrator's call): the scorer server takes GPU0's lease only around its GPU work, or the transcript
ingest's Whisper uses GPU1 under its lease when GPU0's is held (transcript_store.whisper accepts
CUDA_VISIBLE_DEVICES=1 under law L-r). Until then pp-ingest takes each Whisper record within 10 minutes of it landing.
   THE ORCHESTRATOR'S RULING (13:05 ET Nov 16): YES. The integrator is ordered to release the GPU0 lease between
   scoring calls, or to let the pipeline's ingest use GPU1 when GPU0 is leased (builds first). pp-ingest: mine each
   video within 10 minutes of its transcript, Bitcoin channels first; design (not build) a second caption source that
   does not depend on this machine's YouTube quota, and say what the 429s correlate with.
   DONE BY THE INTEGRATOR (13:4x ET Nov 16; main tree e2b3fa65 and a2dc8ec9): the transcript ingest's Whisper now
   WAITS for GPU0 (polls every 5 s holding nothing, at most 1500 s a run) instead of deferring at once; renders (their
   yield flag) and builds (pipeline/gpu0_want: the scorer and the pre-check raise it while work waits) come first;
   each run record carries "waited_for_gpu0_s". CORRECTION of this request's reading: the lease file records its LAST
   owner; the scorer never holds GPU0 idle (no process held the lease at 12:56); the 12:30 run's one no-wait attempt met
   a 73-candidate scorer burst (12:28-12:34). pp-ingest read the file's record as a current holder without checking the
   flock: wrong. Bitcoin Magazine uAvmynMSVhM was transcribed by the 13:00 run.
   STILL OPEN (the integrator's, found 13:45 ET): Scott Melker f0NnJM63Ffc is skipped every run as "live_status
   is_live" from the pipeline's meta.json written at 09:30 ET while the stream was live (is_live, no duration, captions
   only live_chat) and never refreshed; this watcher's own probe at 13:25 ET sees it was_live, 3,679 s, with English
   automatic captions listed (its downloads refused by the 429s). INGEST-FAIL-01's pattern (a meta written while live
   freezes the video); proposed: re-read the metadata of a video whose stored live_status is is_live / is_upcoming /
   post_live before skipping it (transcript_store's meta_history is its refresh path).
   THE INTEGRATOR'S ANSWER (13:5x ET): confirmed ("my 'live, skipped by policy' was wrong"). The cause is
   transcript_store.ensure_meta: it returns a stored meta.json whenever one exists, never refreshed (no meta_history is
   ever written), so acquire() skips on a stored is_live / is_upcoming forever. The fix, audit-first, in the 14:30 or
   15:00 cron run: before skipping a video whose stored live_status is is_live / is_upcoming / post_live, its metadata
   is re-read at most once per run; the fresh snapshot is appended to meta_history.jsonl (meta.json stays
   write-once); ensure_meta returns the newest snapshot. pp-ingest reads only the pipeline's transcript records (never
   its meta.json), so nothing changes here; the r119 sweep takes f0NnJM63Ffc's record within a minute of it landing.
   FIXED BY THE INTEGRATOR (batch 98, main tree 8f8bccf1, 13:55 ET): before a skip, transcript_store re-reads a record
   stored as is_live / is_upcoming / post_live (at most once per 20 min a video); the snapshot goes to
   meta_history.jsonl (meta.json stays write-once); ensure_meta returns the newest snapshot; a hung or missing yt-dlp is
   a logged failure and the stored state stands for that run. The 14:00 run re-read 14 such records: 9 was_live, 3
   post_live, 2 still live. Scott Melker f0NnJM63Ffc read again at 14:01:46 ET: was_live, 3,679 s, captions refused
   (429), due for Whisper, deferred by that run's 4-hour audio budget (--max-whisper-hours 4, a cron setting) behind
   Bitcoin Magazine oqB8dx7VgOQ (111 min), BTC Sessions nvEftLDdab4 (76) and Digital Asset News Sps9le2Z5RI (48), in the
   ingest's own priority order. pp-ingest asks no cron change: the ingest orders by tier (Melker is tier 2, the other
   deferred are mostly tier 3), so the 14:30 run takes it early; each run's budget (about 8 h of audio an hour) is well
   above the day's upload volume; the watcher mines it within a minute of its record (r119).
   CORRECTION (14:5x ET): pp-ingest expected the 14:30 run to take Melker "early (tier 2 before tier 3)"; wrong: the
   pipeline's priority key is (approved layout first, then tier, then age), and Melker's layout is pending, so the
   14:30 budget went to Bitcoin Magazine (approved, tier 1, 29 min), Simply Bitcoin (approved, tier 2, 86 min) and
   CoinDesk (approved, 125 min). The integrator (14:5x ET): Melker is now second for the 15:00 run, behind TFTC
   ZtnhDQODni8 (83.5 min), 2.41 h cumulative inside the 4 h budget; 15 more videos (11.83 h of audio) after it. No cron
   change asked: the approved-layout channels are the ones the builder can cut first; the watcher takes Melker's record
   within a minute of it landing (r119's sweep covers captions_pending).
