# PROTOCOL PULSE — MASTER HANDOFF FOR CLAUDE FABLE 5
**Prepared:** 2026-07-01 (ET) · **For:** the incoming Fable 5 continuous-execution agent
**Operator:** PBX (Paul) · **Repo HEAD at handoff:** `d90f2412`

---

## 0. HOW TO USE THIS DOCUMENT

You are inheriting a large, mostly-built autonomous Bitcoin-intelligence platform running on a single server (Ultron). Much of it works. Several high-value features are **built but not fully autonomous**, and a few share one root blocker. Your job is to take each item in the **Work Queue (Section 6)** to 100% completion, live-tested, committed, and then move to the next without waiting for hand-holding.

Read in this order before touching anything:
1. This document, end to end.
2. On Ultron: `~/protocol_pulse/CLAUDE.md` (the coding constitution).
3. `~/protocol_pulse/PIPELINE_LAWS.md` + `PIPELINE_LAWS_ADDENDUM.md` + `CROSS_LLM_AUDIT_LAW.md` (gospel for any video-pipeline work).
4. `~/protocol_pulse/LOCKED_FIXES.md` and `PRODUCTION_DESIGN_LAWS.md` before any render change.

There are dozens of legacy `.md` docs in the repo root (many overlapping "COMPLETE_CODEBASE" / "HANDOFF" files). **This document supersedes them as the entry point.** Treat the files named above as the authoritative laws; treat the rest as historical.

---

## 1. THE GOAL PROMPT (continuous autonomous execution)

> Paste this as your standing objective. It is written for continuous, self-driving execution.

```
GOAL: Drive every project in the Protocol Pulse Work Queue (Section 6 of
FABLE5_MASTER_HANDOFF.md) to 100% completion — built, wired, live on Ultron,
autonomous on a schedule, and verified with real evidence — then move to the
next without stopping for permission.

OPERATING CONTRACT:
1. Work the queue in priority order: P0 first (it unblocks the rest), then P1,
   then P2. Finish one item to its acceptance criteria before starting the next,
   unless an item is blocked, in which case park it (Section 6 "Blocked" list)
   and continue.
2. For every code change follow AUDIT-FIRST: read the real files → cross-LLM
   audit (utils/cross_llm_audit.py, 2 cycles) for pipeline code → implement only
   the consensus fix → behind a feature flag when new → regression_test.sh shows
   0 FAILs → git add + commit + push in one step. No uncommitted .py left on disk.
3. "Done" means the acceptance criteria in Section 6 are met AND proven with a
   live test — a real render, a real posted item, a real HTTP 200 from the
   deployed endpoint via headless browser or the relay — NOT a curl to localhost
   you assume worked, and NOT "should work." Triple-verify. Log the evidence in
   the commit message.
4. Everything runs through the Ultron relay (Section 3). All times ET. Never
   print .env contents or API keys. Never assign PBX a manual task; attempt it
   yourself first. The only legitimate escalations are: external billing (paying
   X for API credits), account actions inside a third-party dashboard (Buffer key
   regen, X developer portal), and anything needing root/sudo (the relay runs as
   `ultron` without passwordless sudo). For those, do everything you can up to the
   wall, then surface the exact one-line command or action PBX must take.
5. Respect the brand and voice laws (Section 8) on anything customer-facing.
   PBX is never positioned publicly as founder/builder/CEO.
6. When a project reaches its acceptance criteria, post a one-line status
   ("<project>: DONE — <evidence>, commit <hash>") and immediately begin the next.
   Do not stop to ask "what's next" — the queue is what's next.
7. Update Section 6 status markers and append a dated line to
   ~/protocol_pulse/HANDOFF_LATEST.md as you complete each item, so the next
   session inherits accurate state.

STOP CONDITION: every P0/P1/P2 item is DONE and verified, or every remaining item
is genuinely Blocked with the blocker documented. Then produce a final report.
```

**FIRST ACTIONS ON BOOT (do these in order):**
1. Verify GPU health per the Section 3 alert — `nvidia-smi` must list both RTX 4090s cleanly before any render/TTS/lip-sync work. If it errors, stop and confirm with PBX that the reset/reboot is done.
2. Build **P0 6.1 (`x_reader` on Grok `x_search`)** immediately — it needs no decision and unblocks four downstream features.
3. Then proceed down the Work Queue by priority. The comedy decision (6.4) is already resolved — no need to ask.

---

## 2. WHO YOU'RE WORKING WITH

PBX (Paul) operates Consensus Protocol LLC out of Naples, FL and is the technical/creative driver of Protocol Pulse. Communication style: **terse, decisive, feedback by version/commit number, expects autonomous execution without permission loops.** He signs copy as "Paul" (no title).

**Brand positioning rule (non-negotiable):** On any customer-facing surface, PBX is **never** positioned as solo-founder / builder / CEO. No "one person built this" narrative. The public brand (Protocol Pulse) is intelligent, edgy, confident — **not tribal**. PBX is personally a Bitcoin maximalist; the brand has broader appeal. Internal tooling docs like this one may describe his operational role plainly; public materials may not. Consensus Protocol LLC is the parent entity and should not appear in partner-facing/SLS materials.

Properties in the ecosystem: **Protocol Pulse** (terminal, newsletter, Pulse Check video, @ProtocolPulseHQ), **Bitcoin Boomers** (podcast/YouTube), **Cypherpunk'd** (clip channel), plus separate ventures (SLS, Brick Lantern) that are **out of scope** for this handoff unless PBX says otherwise.

---

## 3. INFRASTRUCTURE & ACCESS

**Ultron** — AMD EPYC 9R14 (96 physical / 192 logical cores), **2× RTX 4090** (GPU0 + GPU1; the "4× 4090" in old docs is stale), ~93–128 GB RAM, Ubuntu 24.04. Runs hot (100°F closet); read temps from `/sys/class/hwmon` directly (lm-sensors not installed): k10temp→hwmon1, nvme→hwmon0. NVMe is the tightest thermal margin.

> ⚠️ **LIVE INFRA ALERT (check first):** at handoff `nvidia-smi` returned
> `Unable to determine the device handle for GPU0000:01:00.0: Unknown Error`.
> That typically means a GPU fell off the PCIe bus (driver/thermal/power). The
> entire video pipeline and all CUDA TTS/lip-sync depends on the 4090s, so
> **diagnose this before any render work** (check `dmesg | grep -i nvrm`,
> consider `nvidia-smi -r` GPU reset which needs root, or a reboot). Track GPU
> isolation law: pipeline on cuda:0, avatar server on cuda:1.

**The Relay (all remote execution goes through this):**
- Endpoint: `https://relay.protocolpulse.io/exec`, POST, `Content-Type: application/json`
- Auth: token passed **in the JSON body** `{"token":"<value>","cmd":"<command>"}`, NOT an Authorization header. Token is provisioned in your project instructions / `.env`; do not paste it into files.
- Use **Python3 urllib** (not curl), User-Agent `Mozilla/5.0`, 90s timeout for long commands.
- Service: `ultron-relay.service` (also self-healed by a `*/2` cron running gunicorn on port 8201, 4 workers, 120s timeout). Root path returns 404; only `/exec` is live.
- Relay quirks that will bite you:
  - **Shell eats `$`.** Any `$` in a command (Python vars, GraphQL `$input`, awk) gets interpolated by the relay's shell. **Always deliver scripts via base64:** write the script locally, `base64 -w0`, then `echo <B64> | base64 -d > /tmp/x.py && python3 /tmp/x.py`. This is the single most important relay habit.
  - Multi-line git commits: write a shell script with a `git commit -F - <<'MSG'` heredoc, base64 it, run it. Inline multi-line commit messages 500 at the relay layer even when the commit succeeds server-side.
  - `pkill -f <pattern>` can kill the relay itself if the pattern matches its own cmd string. Use `pkill -x <exact_name>`.
  - Daemon detachment: `setsid ... &` is insufficient. Use Python double-fork + `os.closerange(3, maxfd)` before `execv`, redirect to a logfile, poll separately.
  - HTTP 500 from the relay can occur even when the server-side command succeeded (it did for a git push this week). Verify state before retrying.
  - No passwordless sudo. Anything needing root must be escalated to PBX.

**Git:** `consensusprotocol/protocol-pulse-core` on GitHub, SSH keys on Ultron. Law: every change = `git add + commit + push` in one step, no uncommitted `.py`. Never force-push.

**Web:** Waitress on **:5000** (`~/protocol_pulse/core` → `app:app`), Cloudflare tunnel → protocolpulse.io. **Gunicorn is banned for the :5000 web server** (Waitress only); gunicorn IS used for the relay on :8201, which is fine. A separate Flask/Werkzeug app for **consensusprotocol.org** runs on **:4040** (`~/consensusprotocol/app.py`), Cloudflare tunnel id `b8a54333-829e-40be-8d8f-5a205ef687fb`. Both returned 200 at handoff. Waitress self-heals every `*/1` min.

**DB:** SQLite at `~/protocol_pulse/instance/protocol_pulse.db`. Migrations via `ALTER TABLE ADD COLUMN` (no Alembic). Also `data/sovereign_intel.db` (narrative/sentiment tables like `emerging_narratives`).

**Key paths:**
- Flask app: `core/app.py`; routes split across `routes_pages.py`, `routes_api.py`, `routes_admin.py`, `routes_auth.py`, `routes_social.py`.
- Services (business logic): `services/*.py` (~large fleet).
- Video pipeline: `video_pipeline_v3/` (orchestrator `daily_producer.py`, thin `assembler.py`, split `render_*.py` modules, `audio_master.py`, `utils/`).
- Templates: `~/protocol_pulse/templates/` (NOT `core/templates/`). Template edits take effect immediately; Python edits need a Waitress restart.
- Agent fleet: `agents/agent_runner.py` (self-heals every `*/10` min; boots on reboot).
- Skills/agents for CC: `.claude/skills/`, `.claude/agents/`.

---

## 4. OPERATING DISCIPLINE (INVIOLABLE)

1. **Never** assign PBX a manual task; attempt autonomously first.
2. **Never** print `.env` contents or expose API keys. Never `sed` `.env` (use nano). Reference key *names*, never values.
3. **Banned tech:** Three.js, VR, DAO, quantum auth, Sora, MuseTalk, SadTalker (kill on sight — it steals cuda:1), Creatomate, OpusClip, Suno API, Gunicorn (for the :5000 web app), genetic algorithms, CRF ≥ 20, preset "fast"/"ultrafast" for final output, blue/cyan/purple in any pipeline visual, hardcoded `pp_background.mp3`.
4. **One Claude Code session per worktree.** Parallel sessions across *different* `~/worktrees/<feature>/` are allowed; two in the same worktree = abort. Production `~/protocol_pulse/` is never directly written by a CC agent — work in a worktree and pull in.
5. **AUDIT-FIRST LAW:** read → `utils/cross_llm_audit.py` 2-cycle (Qwen local first for $0 pre-filter, then Gemini/GPT-4o/Grok on ≤120-line surgical payloads) → implement consensus only → regression 0 FAILs → commit. Consensus = same file/function/root-cause from Qwen + ≥1 external LLM.
6. **Feature flags:** new features start FALSE in `config/feature_flags.json`, flip to TRUE only after isolated proof.
7. **"Done" = evidence.** Never claim E2E tested from a localhost curl; use Playwright/headless Chromium for real browser verification of user-facing surfaces. Triple-verify (test output, test from another angle, confirm live).
8. All times **Eastern Time**. Ollama models auto-unload after 5 min idle.
9. `aresample=async=1` is banned everywhere except `clip_extractor.py::fix_av_sync()`. Never add logic to `assembler.py` (use the split render modules). Never modify `assembler.py` and `clip_extractor.py` in the same commit.

---

## 5. CURRENT SYSTEM STATE (THE MAP)

**Healthy / running:** protocolpulse.io (:5000, 200), consensusprotocol.org (:4040, 200), the relay (:8201), Waitress + relay self-heal crons, the agent fleet (`agent_runner.py`), `perception_layer.py` (every 15 min, producing sentiment signals), `channel_daemon` KOL transcript pipeline, morning/midday/evening `stage_brief_pipeline`, daily video renders (output dirs through 2026-07-01), the newsletter/brief/Substack/Nostr crons, and a very large cron fleet (tweet 2×/day, congress + bill + EDGAR trackers, montage, x_spaces, phone brief dispatcher, etc.). Also live and verified end-to-end: the **Faye** scam-check tool (`/faye`) — see 6.10.

**Tweet automation — FIXED this week (verify it holds):**
- Posting now routes through **Buffer's GraphQL API** (`services/buffer_poster.py`, endpoint `https://api.buffer.com/graphql`, auth `Authorization: Bearer <BUFFER_API_KEY>`). Reason: the direct X API returns **402 Payment Required** (the @ProtocolPulseHQ developer account, id `1971402044444692480`, has **zero API credits**). `tweet_machine.py::post_tweet()` tries Buffer first, falls back to the (dead) X API only if `POST_BACKEND=x`.
- Buffer org "Protocol Pulse" id `672bf13d36385f4ca9125c1f`. Channels: X `6a14fd85c687a22dd42796de` (@ProtocolPulseHQ), X `69e0d739031bfa423c0d867d` (@btc_boomers). Buffer keys expire 30 days after creation — if posting silently stops, regenerate at publish.buffer.com/settings/api.
- Voice model upgraded **Haiku → Sonnet 4.6** (`claude-sonnet-4-6`) for tweet generation (commit `d90f2412`). The PBX persona + 10 voice laws were always intact; Haiku just executed them flat. Confirmed live tweets going out with correct voice.

**The systemic blocker — X is credit-depleted for READS too:**
Every X-read feature (comment_radar, quote_rt_engine, reply engine, spaces/nitter scrapers) hits the same 402 CreditsDepleted wall. **The free fix is validated:** xAI's `x_search` (Agent Tools API, endpoint `https://api.x.ai/v1/responses`, model `grok-4.3`, tool `{"type":"x_search"}`, supports `allowed_x_handles`) reads X server-side and returns posts + reply sentiment + citations for ~half a cent per call. Tested live 2026-07-01 — it returned real current posts from Saylor/WClemente/etc. The old `search_parameters` Live Search is **deprecated (410 Gone)**; do not use it. Building a shared reader on `x_search` is **P0** because it unblocks four features at once.

**Video pipeline (Pulse Check):** at **V57**, NVENC GPU encoding wired into all renders (`h264_nvenc`, 10–50× speedup), Chatterbox PBX voice made primary in V56, V57 fixed a metadata leak + tweet cards + AV sync + still-image clips, social-card render filtergraph cut from 741s → 120s. **`consecutive_a_grades` = 0**, so it has NOT yet hit the 10-consecutive-Grade-A lock that defines "pipeline done." This is the single biggest convergence goal.

---

## 6. THE WORK QUEUE (build → autonomous → tested)

Status key: ☐ not started · ◐ partial/exists-but-not-autonomous · ✅ done

### P0 — the unlock
**✅ 6.1 Shared X read layer (`services/x_reader.py`) on Grok `x_search`.**
Wrap the validated Agent Tools API into reusable functions: `get_top_posts(handles, hours) -> [{author, url, text, engagement, reply_sentiment}]` and `get_reactions(post_url) -> {sentiment, top_reply_themes}`. Handle the `degraded: true` case (xAI returns unsourced training-data answers when filters match nothing — reject those). Cache to `data/x_reader_cache/` with short TTL to control cost. Acceptance: a live call returns real posts from the THOUGHT_LEADERS list with citations; cost logged; unit test passes; committed.

### P1 — social autonomy (all depend on 6.1)
**✅ 6.2 Revive `comment_radar.py`.** It runs and loads `XAI_API_KEY` fine but fetches via the dead X API → 0 candidates. Repoint its `fetch_candidates()` at `x_reader`. Note the data-shape gap: `synthesize()` expects `top_comments=[{author,likes,text}]`; `x_search` returns synthesized reply sentiment, so either adapt `synthesize()` to consume summaries or have `x_reader` structure representative replies. Acceptance: `radar_drafts.json` fills with real, on-voice draft reactions from live X data.

**◐ 6.3 Quote-RT engine (`services/quote_rt_engine.py` — already exists, cron'd 2pm ET).** It almost certainly dies on X reads and/or posts via the dead X API. Wire candidate discovery to `x_reader`, generation to the Sonnet voice engine, and posting to `buffer_poster` — a quote-tweet is just your line **plus the quoted status URL appended**; X renders the quote card automatically (confirmed feasible via Buffer). Voice = the "bye tourists" cypherpunk reframe (see the @kinetic_finance QRT of @WClemente PBX supplied). Posts from @ProtocolPulseHQ (QRTs are sharp commentary, on-brand, unlike satire). Gate hard so it only quotes high-quality thought-leader posts, 1–2/day max, never low-value. Acceptance: a real quote-tweet with a live card posts to @ProtocolPulseHQ via Buffer, gated and deduped.

**☐ 6.4 Comedy bot (`services/comedy_machine.py` — new).** Bitcoin-Bugle-style deadpan fake-news satirist on Sonnet. Trained on: partner-channel transcripts (`video_pipeline_v3` channel_archive) + live narrative/sentiment (`emerging_narratives`, `perception_layer`) + top-comment mood via `x_reader`. HARD RULE: satire must read as **obviously absurd**, never as a believable false claim (the opposite failure of the killed "Congress passed the CLARITY Act" backlog tweet). **DECISION (resolved by PBX 2026-07-01):** posts from the main **@ProtocolPulseHQ** account — no separate handle. **Tasteful and sparse — NOT daily** (target roughly every 3–5 days, and only when the take is genuinely sharp; skip rather than force a weak one). Rationale: the brand is being built to attract Bitcoin sponsors, and edgy-but-tasteful takes signal well to that audience, but over-posting satire would jeopardize the professional credibility sponsors want. Text-first; image generation is an optional phase 2, not required for launch. Add a quality gate so a mediocre joke is dropped, not shipped.

**◐ 6.5 `social_daemon.py`.** Down; the `*/5` self-heal cron restarts it but it doesn't stay up (its jobs all need X reads, which 402). Once 6.1–6.3 land, it revives for free. Acceptance: daemon stays up, runs reply/radar/reply-back/nostr on schedule with real output.

### P2 — the big one + cleanup
**◐ 6.6 Pulse Check video pipeline → 10 consecutive Grade A.** This is the flagship. Read `PIPELINE_LAWS.md` + addendum + `CROSS_LLM_AUDIT_LAW.md` + `LOCKED_FIXES.md` + `PRODUCTION_DESIGN_LAWS.md` first, every session. Current V57, `consecutive_a = 0`. Drive `overnight_render_loop.py` / `render_improvement_loop.py` under the Content-Lock law (iterate on assembly, not content: `daily_producer.py --reuse-content`) until 10 consecutive Grade A (score ≥ 88, `broadcast_ready=True`, zero 0/10 critical dimensions). Known open issues to chase to zero: true-peak clipping, black frames at social-card boundaries, partner-clip AV sync, Gemini two-pass grading reliability, freeze-frames fixed at source (Ken Burns, never output patching). Respect GPU isolation and the NVENC substitution. Acceptance: `consecutive_a_grades.txt` reaches 10 and the loop emits "PIPELINE LOCKED."

**◐ 6.7 Satomi Oracle.** Avatar server (`oracle/avatar_server.py`, cuda:1, health on :8200) must be up 24/7; run the 5 mandatory oracle live-endpoint tests before any oracle commit (see the law in `PIPELINE_LAWS.md`). Verify `satomi_voice_ops.py` / `voice_ops_blueprint.py` blueprint registration in logs (open loop). Acceptance: all 5 oracle tests pass live; blueprint confirmed registered.

**◐ 6.8 Cypherpunk'd clips.** faster-whisper large-v3 pipeline rendered 263 clips to `cypherpunkd_clips_v2/`; ~103 failed on ffmpeg timeout for long clips — run the retry driver (libx264, extended timeout) to completion. Background music not yet implemented. Content-ID risk persists on partner clips regardless of overlays — flag, don't ignore.

**☐ 6.9 Data-resilience cleanup:** consolidate the 3 duplicate Fear & Greed fetchers into one source of truth (`signal_data_fetcher.py:229`, `routes_api.py:4385`, `routes_api.py:5612`); make `price_service.py` resilient to CoinGecko 429 (same failure mode gold had); add a `fetch_geopolitical` pre-compute cron (papers over the 39s cold call; TTL cache is only interim); add a Buffer-key weekly health-probe so posting never dies silently; add a `morning_brief` freshness check (was running ~19h stale).

**✅ 6.10 Faye scam-check tool — WORKING, keep alive + optional polish.** (`/faye`, `core/routes_faye.py`, `templates/faye.html`, blueprint registered via `routes_pages.py`.) Public fraud-detection tool built around the Karen Faye hardware-wallet impersonation case: a user submits a photo / audio / text of a suspicious message and a vision LLM (Gemini primary, Anthropic fallback, `FAYE_PROMPT`) returns an `ok`/`warn` verdict with confidence + signals. **Verified working end-to-end 2026-07-01** (image upload → HTTP 200 → structured verdict). No GPU dependency, so it's unaffected by the GPU0 fault. `/karen` and `/donate/karen` 301-redirect to `/faye`; donation address from `donation_wallets.json::karen_faye`. This is a public, named-for-a-real-person tool — treat any `/faye` outage as high priority. Optional improvement: the analysis round-trip is ~27s (vision-LLM latency); downscale the image client-side before send and/or use a faster vision model to cut it. Acceptance for "still done": monitoring shows `/faye` 200 and `/api/faye/analyze` returning a valid verdict; latency work is optional, not required.

### Blocked (need PBX / root / billing)
- **`pulse_intel.service`** crash-looped 17,405× — `ExecStart` points at a non-existent `venv/bin/python`. Fix needs root: `sudo systemctl edit`/disable, or `sudo systemctl disable --now pulse_intel.service`. It also needs the X read layer to do anything. Relay has no passwordless sudo.
- **X API native access** (if PBX ever wants native reads/QRTs instead of x_search + Buffer) requires paying X (Basic ~$200/mo). Not needed given the free path above.
- **comment_radar/comedy account decisions** and **Buffer key regen** live in third-party dashboards.

---

## 7. VIDEO PIPELINE — DEEP REFERENCE

Architecture: `daily_producer.py` orchestrates; `assembler.py` is a thin (<1,800 line) orchestrator — **do not add logic there**, use `render_narrator.py`, `render_clip.py`, `render_social.py`, `render_intro_outro.py`, `render_data.py`, `audio_master.py`, `transitions.py`, `lower_thirds.py`. Remotion components under `remotion/src/compositions/` pull brand constants from `remotion/src/brand.ts`.

Hard format lock: 1920×1080, 30fps CFR, h264 (NVENC `h264_nvenc` substituted for libx264), yuv420p, AAC 48kHz stereo, MP4. Encoding CRF 17, preset ≥ medium for finals, target 8 Mbps. Shorts 1080×1920.

Voice: Host1 Deborah (`VeCVR24o7g2y1IxLJzZs`), Host2 PBX. Note a shift toward **Chatterbox** as PBX voice primary (V56) alongside the ElevenLabs PBX clone (`HmUVvDlHsEz0m3eUGLgu`, speed 1.2×) — the ElevenLabs clone is the identity voice; do not swap it for a generic TTS without cause. Kokoro `af_heart` is a local stock voice for host1. Full voice-dynamics modes (WHISPER/CLEAR/AUTHORITY/WARM) and banned-voice list are in `PIPELINE_LAWS.md` §14B/§20.

The intelligence moat: `channel_daemon.py` (every 15 min) archives every Bitcoin-YouTube upload's transcript to `data/channel_archive/` permanently; the pipeline reads the archive, not fresh scans. 5-clip rule (5 clips, 5 distinct channels, ≤48h freshness) enforced in code, not just prompt.

Full grading/convergence law (two-pass Gemini, critical-dimension gating, 10-consecutive-A lock, content-lock iteration, render-improvement loop) is in `PIPELINE_LAWS.md` "LAWS ADDED 2026-03-24." Read it before touching the loop.

---

## 8. BRAND & VOICE

**Tweet voice** (in `tweet_machine.py`, keep intact): Theo Von × Saylor × Lyn Alden blend + 10 data-derived Voice Laws + gold-standard examples + cypherpunk identity laws. Lead with a number, ≤150 chars, no dashes, no emoji, no trailing period, original takes, one clean idea, data must be exactly correct. Bitcoin-only (no altcoins/stablecoins/ETH/"crypto"). Cut tribal copy ("stay free stay sovereign," "no chain but Bitcoin," "blood oath"). Never post regulatory clarity / ETF approvals / institutional adoption as "wins."

**Pipeline visual brand:** primary red `#CC0000`, dark `#0A0A0A`, surface `#141414`. Blue/cyan/purple permanently banned. Cypherpunk'd progress bar green `#39FF14`.

**Positioning:** never present PBX as founder/builder/CEO publicly; brand is intelligent/edgy, not maxi-tribal.

---

## 9. KEY LEARNINGS & GOTCHAS

- Model quality matters for voice: Haiku is flat, Sonnet matches the persona. Not interchangeable for voice work.
- Buffer's classic REST API (`api.bufferapp.com`) is dead ("Public API tokens not accepted"); the live one is `api.buffer.com/graphql`.
- X account 402 = credits depleted for **both reads and writes**; solve writes with Buffer, reads with `x_search`.
- xAI Live Search is deprecated (410); use the Agent Tools API (`/v1/responses`, `x_search`).
- CSS `transform` on a parent becomes the containing block for `position: fixed` children (caused the admin sidebar bug).
- Root-cause over band-aids; freeze frames fixed at source (Ken Burns), never output patching (Gemini scores output-patching 1/10).
- Relay: base64 everything with a `$` in it; `pkill -x` not `-f`; 500 can hide success.
- nitter/snscrape are unreliable now; prefer `x_search` for X reads.

---

## 10. DEFINITION OF DONE / TESTING PROTOCOL

Per project, "done" requires ALL of:
1. Acceptance criteria in Section 6 met.
2. Live evidence: a real posted item / real render passing validation / real HTTP 200 from the deployed surface via headless browser or relay — captured in the commit message.
3. Runs autonomously on its schedule (cron/daemon/agent), not just when invoked by hand.
4. Feature flag flipped on (if new), regression 0 FAILs (pipeline), committed + pushed.
5. Section 6 status marker updated and a dated line appended to `HANDOFF_LATEST.md`.

---

## 11. APPENDIX — SESSION ARTIFACTS & VALIDATED ENDPOINTS

- **`services/buffer_poster.py`** (created this week): `post_to_buffer(text, channel="x", mode="shareNow"|"addToQueue", save_to_draft=False)` and `buffer_available()`. Mutation `createPost` returns union `PostActionPayload`; select `... on PostActionSuccess { post { id status text } }` plus typed error fragments. `deletePost` returns `DeletePostPayload` (`DeletePostSuccess` / `VoidMutationError`).
- **Validated `x_search` call:** POST `https://api.x.ai/v1/responses`, body `{"model":"grok-4.3","input":[{"role":"user","content":"..."}],"tools":[{"type":"x_search"}]}`, auth `Authorization: Bearer <XAI_API_KEY>`. Optional `allowed_x_handles`, `from_date`/`to_date`. Watch `degraded:true`.
- **THOUGHT_LEADERS** (sentiment targets, in `tweet_machine.py`): PrestonPysh, LynAldenContact, Breedlove22, MartyBent, TFTC21, American_HODL, daborado (Dylan LeClair), nic__carter. comment_radar has its own broader `radar_config.json::target_accounts`.
- **LLM cascade** (tweets/briefs): Anthropic (now Sonnet 4.6 for tweets) → Gemini 2.5 Flash → Grok (`api.x.ai`, `grok-3`) → NVIDIA NIM. Ollama/Qwen local on cuda:2/3 for $0 audit pre-filtering.
- **Buffer IDs:** org `672bf13d36385f4ca9125c1f`; X channel `6a14fd85c687a22dd42796de` (@ProtocolPulseHQ); boomers `69e0d739031bfa423c0d867d`.
- **Backups left on disk:** `tweet_machine.py.bak_buffer`, `tweet_machine.py.bak_model`, `pending_tweets.json.bak_drain`.

*End of handoff. Start at Section 1 (the goal prompt), verify the GPU alert in Section 3, then execute the Work Queue.*
