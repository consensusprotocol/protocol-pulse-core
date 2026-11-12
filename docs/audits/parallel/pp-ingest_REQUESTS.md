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
4. Local model (law L-x, ULTRON FIRST): set `"enabled": true` for the local back-end in
   `pipeline/ingest/providers.json` only where the GPU0 lease is held: `Service(lease=<gpu0 lease predicate>)`; the
   back-end refuses every call while the predicate is false. A/B on the same 30 videos:
   `PP_INGEST_GPU0_LEASE_HELD=1 python3 tools/ingest_watch.py ab --video-list <AB dir>/videos.json --backends
   local_gemma,heimdall_qwen27b --enable local_gemma` under the lease (the judge is chosen automatically: the first
   judge-role back-end whose model is none of the generators).

## R7 The 3 h VOD ceiling
`transcript_store.MAX_DURATION_S` (3 h) excludes long partner livestreams from the selector's universe. pp-ingest
captions VODs up to 6 h (no Whisper cost on this path) and records longer ones as `too_long`. Whether the selector
keeps 3 h is the integrator's call; the ledger carries the moments either way.
