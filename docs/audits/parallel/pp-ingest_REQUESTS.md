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

