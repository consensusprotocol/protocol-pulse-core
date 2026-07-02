# HANDOFF_LATEST — running progress log

Append one dated line per completed Work Queue item (see FABLE5_MASTER_HANDOFF.md Section 6).

- 2026-07-01: Tweet posting moved to Buffer GraphQL (commit a507dcd8); tweet voice model Haiku->Sonnet 4.6 (d90f2412); X read-credit blocker diagnosed + x_search validated as free read layer (x_reader = P0, not yet built).
2026-07-01 (ET): 6.1 x_reader DONE — services/x_reader.py live on Grok x_search (grok-4.3 /v1/responses). Live test: 5 real posts (saylor/Breedlove22/MartyBent) w/ status IDs + get_reactions (8 radar-shaped replies, sentiment+themes). 12/12 unit tests. Degraded/uncited responses rejected. Cache data/x_reader_cache/ (30m posts / 60m reactions TTL), cost logged (~$0.018/call). Flag config/x_reader_config.json enabled=true. Next: 6.2 comment_radar repoint.
2026-07-01 (ET): 6.2 comment_radar REVIVED — fetch_candidates + extract_comments repointed at x_reader (x_search), dual-path imports, X API kept as fallback. Live cycle: 10 candidates, 5 posts processed, 5 on-voice drafts (scores 86-89) in radar_drafts.json from real reply sentiment. Note: mode=live but posting still dead (402 X API) -> drafts land as post_failed; posting revival is 6.3/6.5. Next: 6.3 quote_rt_engine.

## 2026-07-01 — P1 6.3 quote_rt_engine ✅ DONE (Fable 5)
- Rewired anchor discovery to x_reader (x_search): THOUGHT_LEADERS primary, WIDE_KOLS fallback when <2 anchors clear min_anchor_engagement floor.
- identify_anchors now requires real status IDs (isdigit, len>=15) — killed the legacy bug where DB row ids produced broken quote URLs. Cleaned 137 invalid legacy pending entries in quote_rt_schedule.json.
- Hooks: claude-sonnet-4-6 (voice law), capped hooks_per_anchor=3, 24h spacing.
- Posting: config/quote_rt_config.json flag (posting_enabled=true after live proof), hard 2 posts/day cap, routes through services/buffer_poster.post_to_buffer (shareNow). Fixed success-check to accept post_id (buffer_poster returns success/post_id, not id).
- LIVE EVIDENCE: quote-tweet posted to @ProtocolPulseHQ 2026-07-01 18:35 ET, Buffer post 6a459648f2b098d070548fc6 status=sent, anchor x.com/i/status/2072354952182141253 (River, 1,722 engagement), X gate allowed 3/8.

## 2026-07-01 — P1 6.4 comedy_machine ✅ DONE (Fable 5, resumed session)
- services/comedy_machine.py live: Sonnet satire on real material (narratives + perception + x_reader + channel titles), hard voice-law filter, LLM gate w/ believability kill-switch, floor 88, theme dedup, 3-5 day cadence, Buffer posting to main account (PBX decision locked).
- Cron: daily 13:00 ET, self-gating. posting_enabled=true.
- 21/21 tests. Two live cycles gated correctly (best 71-74 -> SKIP; skip-over-force is the feature). First post lands autonomously when material clears 88.
- Fixed inner-array JSON extraction bug (same class as x_reader parse_json_block).
- Next: 6.5 social_daemon revival (confirmed down, log dead since Apr 24, self-heal cron not effective).

## 2026-07-01 — P1 6.5 social_daemon ✅ DONE (Fable 5)
- Daemon up + stable (self-heal cron works now that the April XAI_API_KEY crash cause is gone via 6.1/6.2). All 4 tasks ran with real output: radar drafts, nostr event published (2/3 relays), reply_engine on x_reader mentions path.
- Radar posting REVIVED through Buffer: LIVE quote posted 18:55 ET (Buffer 6a459af4f2b098d07054c305, saylor anchor, score 94.5). Replies convert to quotes (Buffer can't in-reply-to; X writes still 402/billing). QRT-engine dedup guard added. Daily cap 6->3 for brand safety.
- Note: transient x_reader "could not parse JSON array" at 18:57 (xAI response variance); radar degraded gracefully. Watch frequency; harden x_reader parse if recurring.
- Next: 6.6 pipeline 10-consecutive-Grade-A convergence (the flagship grind). Also open: 6.7 Satomi, 6.8 Cypherpunkd retries, 6.9 data-resilience.

## 2026-07-01 — P2 6.7 Satomi Oracle ✅ DONE (Fable 5) — verification, no code change
- All 5 mandatory oracle tests PASS live: health ok; speak+intent -> 200 with real MP4; chat -> 200 job_id; job poll -> pending then 200 with video; immediate second speak -> 200 (no 503, semaphore clean).
- voice_ops blueprint open loop CLOSED: registered in current Waitress ("Voice ops blueprint registered" in logs), routes live at /api/voice/* (health returns 302->login = auth-gated, not missing). The May "No module named" errors predate the file deployment; current process imports fine.
- GPU isolation verified correct: avatar reports cuda:0 post-CUDA_VISIBLE_DEVICES remap; physically on GPU1 (VRAM match), pipeline on GPU0.

## 2026-07-01 — P2 6.8 Cypherpunk'd clips ✅ DONE (Fable 5) — retry already completed 2026-06-10
- rerender_v2_progress.json: 415 moments, 263 rendered, 103 failed, done=true (2026-06-07). Retry driver (rerender_v2 retry mode) completed 2026-06-10 13:12: ok=99 fail=4 of 103. Clip inventory now 363 mp4s in static/cypherpunkd_clips_v2/.
- 4 permanent failures (e.g. retry066 LcIT9Tgbkm8 @1600s "no output") — source-side, not worth further GPU time.
- FLAGS (unresolved by design, not ignored): background music not implemented in boomers_pipeline (phase 2); Content-ID risk persists on partner clips regardless of overlays.

## 2026-07-01 — Relay operational learning (Fable 5)
- Relay returns HTTP 500 when command stdout contains non-UTF8 binary (breaks its JSON encoding). E.g. catting avatar MP4 response bytes. Sanitize with: cmd | tr -cd '[:print:]\n'. This, plus the $-interpolation trap, explains all 500s this session.

## 2026-07-01 — P2 6.6 status (Fable 5): loop died silently, RESTARTED 20:07 ET — MONITOR
- Boot-started loop (18:06) died between ~18:40 and ~19:50 with no exception logged: render_main tmux vanished, no OOM evidence readable, no output produced. Heartbeat had consecutive_failures=3 pre-cycle. Possible GPU0 instability (Xid 79 earlier today) — if it dies silently again, investigate GPU0 first.
- The crontab "Overnight render loop failsafe" is a COMMENT ONLY — no actual auto-restart line exists. Consider adding one (next session).
- Restarted 20:07:30 ET in tmux render_main after full preflight (avatar :8200 ok, GPUs idle, no competing procs): overnight_render_loop.py --daemon, iteration 1 running, daily_producer spawned. Latest prior grade: 85 (iter4), broadcast_ready False, counter 0. Convergence continues next session.
- 6.9 data-resilience NOT started — next session's first item, along with 6.6 monitoring.

## 2026-07-02 — Satomi user input FIXED (Fable5) + clip-ending verification
- SATOMI: two frontend bugs killed months of "does not accept user input": (1) _audioFinished ReferenceError broke greeting chain on every load; (2) stageTextSubmit silently dropped input while busy (greeting holds busy 8-30s). Plus UI timeouts (45s/30s) shorter than avatar latency (51-100s) — retuned 120s/90s. Headless-browser proof: typed question -> /oracle/chat 200 -> 12.08s lip-synced answer video played. Backups: templates/oracle_live.html.bak_satomi_input_* and .bak_timing_*.
- REMAINING Satomi item: audio-first path dead (job /audio 202 until video done) — avatar_server side; latency polish, not input blocker.
- LEARNING CORRECTION: template edits NOT always live-immediate — Jinja caches compiled templates in running Waitress; bounce required. Waitress self-heal cron did NOT restart it (manual setsid start needed) — verify/repair that cron next session.
- CLIP ENDINGS: Cypherpunk'd v2 FIXED — word-level find_optimal_end_words, 0 boundary-error fallbacks in full run, 3/3 sampled tails end on complete resolved sentences. PP partner clips (Pulse Check) have V58 sentence-boundary+2.5s-tail logic in clip_extractor. Boomers: NO v3 rerender found on disk — old library likely still has abrupt cuts; rerender with the v2 engine is the queued fix.

## 2026-07-02 — Boomers clipping LIVE + Satomi near-instant + cron repair (Fable5)
- BOOMERS CLIPPER: scripts/boomers_clip.py (runs from ~/boomers_pipeline/channels/bitcoin_boomers/). Fixed word-boundary engine now applied to Bitcoin Boomers. EP6 clip001 verified: ends "...my kids, grandkids." — clean sentence, no mid-cut. nvenc encode. Supervisor processing all 3 downloaded episodes (EP6_JOE_KELLY, EPoV69sfxWM, irzDcWaRRNs) detached -> ~/protocol_pulse/static/boomers_clips_v2/. Log: /tmp/boomers_all.log.
  - GOTCHA: don't launch transcribe under CUDA_VISIBLE_DEVICES=0 (word_transcribe pins device_index=1 -> invalid ordinal -> CPU fallback, 267s+). Use WHISPER_GPU=1, no CVD mask. Ollama must be up for Qwen moments.
- SATOMI NEAR-INSTANT: dedicated Kokoro TTS daemon (services/kokoro_tts_daemon.py, localhost:8250, GPU1, warm). In-process Kokoro was 20-32s/call (pathology); daemon does 0.6-1.2s. avatar_server routes to daemon first. Time-to-audio 31s->1.8s, full video 52s->34s. Commit 5d2901a0.
- GPU ISOLATION: avatar_server was silently on GPU0; pinned to GPU1 via site_health.sh (CUDA_VISIBLE_DEVICES=1).
- CRON REPAIR: waitress self-heal pattern self-matched pgrep (never restarted -> why manual bounce was needed); fixed to bracket "[w]aitress.*5000". Added */2 bracket-safe self-heal for kokoro_tts_daemon.
- All 5 oracle mandatory tests PASS. Browser test: typed question -> chat 200 -> answer video played.
