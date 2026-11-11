# CURRENT STATE — 2026-11-11 14:27 ET (Pulse Check mission; CC session in tmux pipeline_pp_dod)

Read docs/audits/DEFINITION_OF_DONE_PULSE_CHECK.md first (LIVE STATE newest first; DEC-1..DEC-11; OD-1..OD-7),
then docs/RUNBOOK_PULSE_CHECK.md. Branch `combo-letterbox-quoteonly-v2` (HEAD: see git log; batch 11 on top of 36e769d0). Nothing is
published; Telegram (the approval chat) gets a run ONLY when every gate passed (orchestrator 08:30).

## What exists (all audited, committed, pushed)
- One command: `scripts/pulse_check_run.sh` (auto) / `--pinned PIN.json`; flock, logs/pulse_check/, tmux-safe,
  NOT in cron; delivers only on a clean pass; DEC-9 story ledger for auto runs.
- Stages: env, editorial (auto) or pinned, review, validate (edl_rules, editorial laws, stand-alone + topic
  rule), cut (sentence law), sentence_law (G16), voice, prepare (fade retry, shot snap), layout, render
  (16:9 + 9:16, transitions), gates (G1..G19, G4s), verify (contact sheets, V1 vision checks).
- `pipeline/replay.py RUN_DIR --from prepare|layout|render|gates` re-runs the tail on a copy.
- DEC-10 sentence law (ae965c95, 29299ea5, 9b459ec6): edge timing calibrated to v2f's measured worst (0 ms;
  D1 head rule 80 ms unchanged); the legal range is the heard gap; a short gap is cut at the envelope minimum
  (searched inside the transcript gap +- one hop) with a 2-frame (83 ms) fade; neighbour_clear (no audible
  neighbour word) in the cutter and G16; stage_cut defers a minimum-cut edge to G16 instead of M19.
- DEC-11 credits gates (af5447c6): G12 / G15 measure the brand-red rings the renderer draws (count, layout
  position, aspect >= 0.95 unchanged) and G15 checks each disc is the credited channel's registered avatar;
  fails closed without the channel list.
- 9:16 safe frame keeps its input's colour matrix (36e769d0; the recut's vertical was color_space=unknown).

## Phase 4a (Nov 10 story): NOT passing; time box over; nothing sent
- Recut #2 runs/pinned_20261111_172202 (DataDash hook, Natalie Brunell, Yahoo Finance, Bitcoin Magazine;
  71.17 s; orchestrator 13:15: "the right video"). G16 / G17 / G18 / G19 PASS both formats.
- Blockers (exact numbers in the DoD 13:32 / 14:03): G9 = OD-4 residual (same locked outro re-encoded ~0.03
  darker than v2f: 16:9 14.3021 vs 14.33; 9:16 14.7418 vs 14.77 once tagged); G10 16:9 = Bitcoin Magazine's
  real burned-in lower third (no 16:9 chyron framing exists for has_chyron channels); G14 = one sample in a
  0.6 s pause of Yahoo's speech under the music bed (xcorr 0.154; not a transition / VO freeze); G3c = hook
  tail only after 8d (DataDash's room tone 10.4 dB under his speech, limit 11.63).

## Phase 4b (three fresh stories in a row at one HEAD): RESTARTING
- Run 1 at 36e769d0 (14:03, runs/fresh_20261111_190259) HELD in editorial on a pipeline defect (hand-made
  transcript records without channel identity crashed clustering; bible E-FAIL-030); fixed in batch 11, the
  count restarts at the batch-11 HEAD with a Law 22 re-proof there. Do not commit between the three runs
  (identical HEAD). Every run is expected to hit G9 (OD-4) until the orchestrator decides it.

## Open decisions for the orchestrator
OD-4 G9 on a black-ending locked outro (blocks every render by encoder state); G10 16:9 framing for
has_chyron channels; G14 sampling in source pauses under the bed (OD-7 class); G3c on a quiet source's room
tone (OD-5 class); OD-1 superseded by DEC-11; OD-2 / OD-3 / OD-6 as written.

---

# CURRENT STATE addendum 2026-11-05 09:15 ET (read before the 2026-11-04 handoff below)

- Overnight segment_v2 run (ba125e19) was REJECTED by PBX: agent rewrote the pipeline, used a question as hook, repeated a passage, 5 VOs, wrong avatars, overrode failed gates, sent Telegram. Full rebuild done 02:00-09:10 ET.
- NEW CANONICAL CHAIN: ~/protocol_pulse/pipeline/ (run.py, render16.py, gates.py, shoutout.py, edl_rules.py, channels.json, test_edl_rules.py) + vertical/render_vertical.py. REPRO PROOF: pipeline reproduces segment_v1/out/segment_v12.mp4 byte-identical (segment_v1/repro/REPRO_PROOF.md). 26 unit tests; last night's bad EDL is a must-fail fixture.
- Editorial rules are CODE gates (R1-R8): statement hook only, no passage reuse, VO after answer only, VO <= 25% runtime, credits == EDL channels with unique avatars, every (channel, tile_count) needs a hand layout table, G10 chyron runs on any channel with has_chyron. Laws 23a, 24, 25, 26 in PIPELINE_LAWS.md.
- v2c outputs (Dollar Hegemony topic): segment_v2/out/segment_v2.mp4 (64.96 s) and segment_v2_vertical.mp4 (65.00 s), inspected frame by frame by the orchestrator; Telegram 67202/67203 (replace 67199/67200). Awaiting PBX verdict. Open judgment item: letterbox bars on BMTV solo shot and Bitcoin Layer chart in 9:16.
- Method that worked: orchestrator pulls frame grids after EVERY render and corrects the agent with explicit rects; the agent's own report was wrong 3 times (gate override, "false positive" G4, text-only "vision review"). Never trust a report line without the picture. Vision review now grok-4.3 with image_url.
- YouTube: v12 is live on Protocol Pulse (RLTgcj6dxN4); pulse_check.json has video_id + x_url. Cypherpunk'd mis-upload wayq6CtR0V4 stays private.
- Uncommitted: static/data/pulse_check.json, segment_v1/edl*.json, topic.json, youtube_description.txt (publisher/repro side effects) - review and commit.
- pp_vert pane idle with inert suggestion "Start segment_v3 with a new topic": NEVER bare Enter.

# CURRENT STATE — Protocol Pulse medley engine (handoff 2026-11-04 22:05 ET)

Read this first in every new session. It supersedes everything below the "PREVIOUS HANDOFF" marker.
PBX's Fable (Claude) usage is near its cap until 2026-11-07 18:00 ET; whichever model continues must follow the OPERATING PRINCIPLES section exactly. They are what made 2026-11-04 work.

## 1. What is published / where things are

| Item | State |
|---|---|
| First Pulse Check (Binance $6.4B hack) 16:9 | `~/protocol_pulse/segment_v1/out/segment_v12.mp4` (100.5 s). Approved FLAWLESS by PBX. Posted to X by PBX manually: https://x.com/protocolpulsehq/status/2118125593695072641 — retweeted by @BTCsessions (145k). |
| 9:16 vertical | `segment_v1/out/segment_v17_vertical.mp4` (102.9 s). PBX: "A+". Telegram msg 67184. NOT yet posted anywhere. |
| YouTube | NOT on Protocol Pulse yet. `wayq6CtR0V4` was uploaded by mistake to the **Cypherpunk'd** channel (token in `.env` belongs to it); it is now PRIVATE. Needs a token for the Protocol Pulse channel — see §4. |
| Thumbnail | `segment_v1/publish/thumbnail_v12.jpg` = thumbs_v12/thumb_v12_2.jpg (Ben + Nico frame, headline "$6.4B BINANCE HACK", transparent pulse mark top-right). Approved style: real frames, third-party logos blurred, no black box behind the mark. |
| X headline (analysis register) | `segment_v1/publish/captions_v12.json` (freshness=analysis). Reply credits @SimplyBitcoin @BTCsessions @CoinDesk. |
| Homepage Pulse Check | `templates/index.html` reads `/static/data/pulse_check.json` {video_id,url,title,x_url,published_at}; falls back to playlist embed when video_id is null. The publisher must write this file after every YouTube upload (TODO, pp_thumb). |
| Grok (xAI) | NEW key in `~/protocol_pulse/.env` as `XAI_API_KEY_MEDLEY` (new account; old account has ~$247 of failed invoices, no Ultron usage anymore). All Grok callers read that one var. |
| X API (posting) | Old X developer account: 402 "credits depleted" on create_tweet. PBX created a new X developer account (logged in as Cypherpunk'd). To post as @ProtocolPulse: get the new app's API key + secret (app set to Read and Write), run the OAuth 1.0a PIN flow (tweepy OAuth1UserHandler, callback "oob") while PBX is logged in as @ProtocolPulse, store the 4 values in `.env` (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET). Then: `cd ~/pp_publisher && python3 publish.py --segment ~/protocol_pulse/segment_v1 --version 12 --skip-youtube --no-gate --at now --freshness analysis --reply-delay 10` (dry-run first with --dry-run). |

## 2. Code that is now law (do not re-litigate)

- **Vertical renderer (canonical):** `~/protocol_pulse/vertical/render_vertical.py` (v1.0 locked 2026-11-04) = `segment_v1/render_v17_vertical.py`. Layout tables in `vertical/layout_tables/`. The old "intelligent" module (`vertical/reframe.py`, `compositor.py`, `shotmap.py`) is DEAD. Do not resurrect it.
- **Three layouts only:** `single` (fixed face crop, chyron-safe = exclude bottom 200 px of source for CoinDesk), `stack2` (two source rects, speaker on TOP, each 1080x960 or 1080x911 with black bars), `grid` (BTC Sessions 5-tile screen-share: screen on top, enlarged column below; PBX-approved). Layout per shot comes from a hand table keyed by source channel + tile count. Unknown → `single` + WARN. Never a detector-chosen layout.
- **Parity:** the 9:16 mirrors the 16:9 shot-for-shot, same order, and muxes the horizontal's finished audio (identical by construction). G11 fails if duration differs > 0.25 s or segment count differs.
- **Gates (qa_gates.py), thresholds are constants (Law 20):** G2 watermark probe; G8 sharpness (Laplacian var on composited faces, floor per-shot); G9 tail (last 1 s not black, audio not silent); G10 chyron IMAGE-BASED (Canny edge density + white fraction on bottom 12% band of CoinDesk frames); G11 parity; G12 credits (count red-ring avatars == number of partner handles). Telegram send only on all-pass. Every gate measures the OUTPUT PICTURE, never input metadata (the old G10 read crop rects and passed a sliced chyron — that is the failure to remember).
- **EDL:** `segment_v1/cuts_final.json` is the single source of truth (Law 22). CoinDesk 7QIB in=230.58. Renderers never patch cut points.
- **Speaker attribution in copy:** manifest knows channel, not speaker. Headline credits a real name ONLY when `publish/partner_handles.json` has a verified `speaker` for that channel AND the clip is the host speaking. Clip_04's "if our entire hot wallet was drained" is Adam O'Brien (guest), not Ben Perrin. V2 gap: per-clip speaker ID.
- **Publisher (`~/pp_publisher`):** `--freshness breaking|developing|analysis` (hook register by story age; validator rejects time markers outside breaking), channel-name validator (no Simply/Sessions/CoinDesk/@ in headline), `$` required on money figures, caption REUSE of a passing `captions_vN.json` (same freshness) so the reviewed copy is the posted copy; `--regen-captions` forces new; `--reply-delay` default 10 s. captions.py/publish.py changes are UNCOMMITTED in ~/pp_publisher (commit them).
- **Laws added:** 20 (gate thresholds never lowered), 21 (time budgets, GPU path), 22 (EDL truth), 23 (vertical parity) in `~/boomers_pipeline/PIPELINE_LAWS.md`.

## 3. Operating principles (the method — apply to every task)

1. **Look at the picture.** Every claim about a render is verified by pulling a frame grid (`ffmpeg -vf fps=1/3,scale=192:-1,tile=10xN`) through the relay in 40 KB base64 chunks and reading it. Gates passing is not evidence; the image is.
2. **Rebuild from the last approved version.** A regression is fixed by returning to the version PBX approved and changing the one thing he flagged. Never fix a regression by adding intelligence (detectors, critics, layouts). Tonight's spiral (v13–v14) came from doing the opposite; the recovery (v15–v17) came from this rule.
3. **Hand tables beat detectors** for anything editorial (which face, which layout). Detection may measure; it may not decide.
4. **Honest ETAs, no padding.** State the budget, stop when it's exceeded, report. "Tomorrow evening" pacing is rejected by PBX; so is pretending 4 h is 1 h.
5. **One CC session per repo**: `pp_vert` = ~/protocol_pulse (vertical + site), `pp_thumb` = ~/pp_publisher. Prompts via base64 → /tmp/cc_prompt.txt → `tmux load-buffer` + `paste-buffer` + `send-keys Enter`. **Trap:** text pasted while CC is busy sits unsubmitted; after it goes idle, check the pane with `tmux capture-pane -p` (NO character filtering, keep the arrow) and press Enter ONLY if your own prompt text is in the input box. An idle CC pane shows a dim PROMPT SUGGESTION (e.g. 'pick thumb 2 and do a real publish for v12'); a bare Enter on an empty input ACCEPTS it and runs it. Never send a bare Enter. Check the pane tail before assuming a prompt ran. Compaction can also drop a queued prompt — re-send after compaction.
6. **Relay** (`https://relay.protocolpulse.io/exec`, urllib, UA Mozilla/5.0): ~50 KB stdout cap (500 error above it); background processes die when the call returns — start daemons with `setsid nohup … < /dev/null &`. Never print .env values.
7. **Copy voice:** lowercase social copy, no hashtags, no em dashes, credit people never channels in the headline, equal credit to all partners in the 🧡 reply.
8. **Never clip reactions to other people's clips; never show a partner's video "unavailable"; red/black brand, orange only as subject accent.**
9. **Bible law:** every new failure pattern → `~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md` immediately.

## 4. Open items, in priority order

1. **YouTube channel token.** Find which Google account owns the Protocol Pulse channel (consensusprotocolhq@gmail.com only offered Cypherpunk'd). Auth link = Google OAuth with `redirect_uri=https://protocolpulse.io/oauth/youtube/callback`, scopes youtube + youtube.upload + youtube.force-ssl, `prompt=consent select_account`; the site callback writes `YOUTUBE_REFRESH_TOKEN` into `~/protocol_pulse/.env`. The site process must have the main `.env` exported (it loads `core/.env` only — permanent fix: add `load_dotenv(parent/.env)` in `core/app.py`; until then restart waitress with `set -a; . ~/protocol_pulse/.env; set +a`). After auth: verify `channels().list(mine=True)` == "Protocol Pulse", add a channel-identity assert in `youtube.py` (refuse upload unless channel title == config YOUTUBE_EXPECTED_CHANNEL), then publish v12 (`--skip-x --no-gate --at now --freshness analysis`), write `static/data/pulse_check.json` with video_id + x_url, verify homepage on phone width.
2. **X posting as @ProtocolPulse** — §1 last row.
3. **Publisher writes pulse_check.json** after each YouTube upload and adds x_url after X post (pp_thumb task). Commit pp_publisher.
4. **Fresh-topic end-to-end run** (the real test): topic_rank → sources → EDL (cuts_final) → VO (PBX MAX voice, Law 15 1.0 s pad) → 16:9 render → `vertical/render_vertical.py` → gates → Telegram gate → publisher. Run unattended; Telegram is the only stop. Daily format: one program, 60–120 s, two aspect ratios from one EDL. 5–10 min weekly roundup is a later product.
5. Hardware: GPU1 (Xid 79) pinned Gen1/quarantined pending physical reseat; `CUDA_VISIBLE_DEVICES=0`. Remove `/etc/sudoers.d/90-ultron-temp` when done.
6. OpenAI + Gemini balances empty (trifecta audits run Grok + Claude until topped up).

## 5. Fast commands

```
# frame grid of any render (then pull /tmp/g.jpg in 40 KB base64 chunks)
ffmpeg -v error -y -i FILE -vf 'fps=1/3,scale=192:-1,tile=10x4' -frames:v 1 -q:v 6 /tmp/g.jpg
# publisher dry run
cd ~/pp_publisher && python3 publish.py --segment ~/protocol_pulse/segment_v1 --version 12 --dry-run --no-gate --at now --freshness analysis
# site restart (CLAUDE.md)
cd ~/protocol_pulse/core && pkill -f 'waitress --port=5000'; set -a; . ~/protocol_pulse/.env; set +a; setsid nohup python3 -m waitress --port=5000 --threads=4 --channel-timeout=300 app:app >> ~/protocol_pulse/logs/waitress.log 2>&1 < /dev/null &
```

---
# PREVIOUS HANDOFF (kept for history)
# Protocol Pulse — Current State
**Generated:** 2026-03-27 12:33:37  
**Git:** `8e1935c1` on `main`  
**Repo:** https://github.com/consensusprotocol/protocol-pulse-core

---

## 🚦 SERVICE STATUS
| Service | Status |
|---------|--------|
| Flask (protocolpulse.io) | HTTP 200 |
| Avatar server (port 8200) | HTTP 200 — avg latency 12.54s |
| CF Tunnel | Active |
| Watchdog cron | Every 5 min |

---

## 🎬 VIDEO PIPELINE — CURRENT
- **V8:** GRADE_F_FAIL|29|/home/ultron/protocol_pulse/video_pipeline_v3/output/2026-03-12/pulse_check_20260312.mp4|This episode is a catastrophic technical failure, rendered unwatchable by a complete TTS failure that cascaded into massive audio and video errors.
- **V9:** Rendering —   Output: /home/ultron/protocol_pulse/video_pipeline_v3/output/2026-03-12
======================================================================
[STEP 13] QUALITY GATE...
  QUALITY SCORE: 69/100 [#############-------] HOLD (threshold: 85)
- **V9 grade:** GRADE_F_FAIL|38|/home/ultron/protocol_pulse/video_pipeline_v3/output/2026-03-12/pulse_check_20260312.mp4|This episode is a catastrophic and unpublishable failure due to a complete breakdown of the text-to-speech pipeline, resulting in a silent co-host, unwatchable dead air, and clipped audio.
- **V9 file:** 
- **Root cause of V7/V8 F:** Eryn voice ID `uxKr2vlA4hYgXZR1oPRT` (Natasha) was wiped by git reset. Fixed in commit `7667c3d6` — correct ID `kdnRe2koJdOK4Ovxn2DI`
- **QC false positive bug:** Internal scorer reports 94/100 PASS on Grade F renders — CC session `qc_audit` fixing now

---

## 🔊 TTS — VOICE DECISIONS (2026-03-12)
| Provider | Host 1 (Female) | Host 2 (Male) |
|----------|----------------|---------------|
| **ElevenLabs** (current default) | Eryn `kdnRe2koJdOK4Ovxn2DI` | Mark `1SM7GgM6IMuvQlz2BwM3` |
| **Inworld** (pending, set TTS_PROVIDER=inworld) | Lauren | Nate |

Inworld voices selected 2026-03-12 via A/B test. CC session `tts_patch` adding Inworld support to tts_engine.py now.  
Quality notes: Inworld = better audio quality, ElevenLabs = better cadence. FFmpeg atempo=1.2 applied post-gen on Inworld.

---

## 🌐 SITE CSS — ALL FIXED ✅
All CSS files 200 BYPASS on Cloudflare via `/v3/css/` Flask route with `no-store` headers:
  pp-core.css: 404 BYPASS
  pp-style.css: 404 BYPASS
  pp-coindesk.css: 404 BYPASS
  pp-fix.css: 404 BYPASS
  pp-homepage.css: 404 BYPASS

---

## 🤖 AVATAR SERVER — BROKEN (CC audit running)
- **Port:** 8200 | **Route:** avatar.protocolpulse.io
- **Engine:** Wav2Lip-GAN FP16, GFPGAN face restore, BATCH_SIZE=64
- **Known issues being fixed:**
  - avg_latency 48.92s (target <10s)
  - apply_blink() creates black oval artifacts
  - /status returns 404 (frontend expects it)
  - blinks_enabled: false
- **CC session:** `avatar_audit` running now

---

## 🔄 ACTIVE CC SESSIONS
| Session | Task | Status |
|---------|------|--------|
| `v9_render` | V9 video render | Running |
| `qc_audit` | Fix QC false positives | Running |
| `tts_patch` | Add Inworld Lauren+Nate | Running |
| `avatar_audit` | Fix avatar latency/artifacts | Running |

---

## 📋 PENDING — NEEDS ATTENTION
1. **V9 grade** — fire `python3 gemini_grade.py` in `video_pipeline_v3/` once render completes
2. **TTS_PROVIDER=inworld** — set in .env after tts_patch CC commits, V10 will use Inworld
3. **Google Cloud billing** — console.cloud.google.com → enable billing for Tier 1 Gemini (150 RPM vs 25 RPD)
4. **Render.com** — disconnect GitHub repo (stop deploy failure emails)
5. **gunicorn.pid** — add to .gitignore (keeps getting committed)
6. **ADMIN_TOKEN** — add to .env for /sponsor-agent dashboard
7. **Overnight loop** — `overnight_render_loop.py` ready, launch after first Grade A
8. **RNS.ID affiliate** — $300/referral, add to Oracle Briefings + newsletter (parked)

---

## 🔑 KEY FILES
- `~/protocol_pulse/PIPELINE_LAWS.md` — gospel, load into every CC session
- `~/protocol_pulse/.env` — all API keys
- `~/protocol_pulse/app.py` — ROOT Flask app (gunicorn loads this via wsgi.py)
- `~/protocol_pulse/video_pipeline_v3/tts_engine.py` — dual-provider TTS
- `~/protocol_pulse/oracle/avatar_server.py` — 984-line avatar engine
- `~/protocol_pulse/overnight_render_loop.py` — autonomous grade-A loop
- `~/protocol_pulse/docs/handoff/CURRENT_STATE.md` — this file

---

## ⚡ CC LAUNCH LAW (PERMANENT)
```bash
tmux new-session -s NAME \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
```

---

## 📜 GIT LOG (last 8)
```
8e1935c1 feat(signals): live signal data engine — CoinGecko/mempool.space/Deribit/alternative.me
4a999aa9 feat(dashboard): Commander subscriber terminal — signals, feed, Oracle, API keys
82d63288 feat(social): auto-publish articles+episodes to Nostr + X on every new content
b1eaefaf feat(article): cinematic redesign — hero image overlay, two-column layout, signal brief sidebar
a8710484 feat(intelligence): live Chart.js halving cycle chart, wire Grade A Pulse Check episode L_XrlNO-nv4
b913a40c fix(panopticon): wire signal data so counters show live values; fix(hero): stats strip no-wrap symmetrical layout
df569b09 fix(hero): left-align stats strip inside hero container
a06113cd fix(hero): align stats strip and New Here row to left hero container
```

---

## 2026-11-04 — Site Rescue Session
**Branch:** site-fix-20261104
**What broke:** LLM credit exhaustion killed article generation since Oct 22. 152 articles had title "```html", 147 had "TL;DR:" titles, 304 had placeholder sources.
**Fixes applied:**
- Provider chain: Ollama (qwen3-coder:30b, free) -> Gemini -> Anthropic -> OpenAI for all article generation
- Centralized sanitize_article_output() strips fences, placeholder sources, empty elements
- Title extraction: TITLE: > h1 > h2.article-header > Ollama-generated headline
- 348 botched articles repaired via scripts/repair_botched_articles.py
- Oracle/Satomi/Avatar removed from nav, homepage, routes (302 redirects)
- Homepage dead data (UPDATING, Loading, N/A, recently) replaced with real data or hidden when unavailable
- FTS index rebuilt
