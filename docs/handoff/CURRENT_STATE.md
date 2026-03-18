# PROTOCOL PULSE V2 ASSEMBLER REBUILD -- HANDOFF DOC
Generated: 2026-03-18 | Repo: consensusprotocol/protocol-pulse-core (main)
Raw: https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/docs/handoff/CURRENT_STATE.md

## STATUS: DAYS 1-4 COMPLETE 29/29 TESTS PASSING -- NEXT: DAY 5

## MISSION
Build assembler_v2: modular rebuild of broken 5005-line assembler.py.
Target: first clean 8-12 min episode -> Gemini grade 90+/100.

## WHY REBUILDING
Old assembler (30+ patches): PiP static frame CRF+bitrate conflict outro audio bleed
/tmp race condition global state segments silently skipping.

## PACKAGE
video_pipeline_v3/assembler_v2/
  constants.py      CODEC LAW 1920x1080 h264 crf17 30fps yuv420p aac 192k 48000hz
                    FFMPEG_TIMEOUT_ENCODE=300 FILTER=120 PROBE=15 SHORT=30
  manifest.py       EpisodeManifest SegmentSpec RenderedSegment validate() on empty
  state.py          EpisodeContext episode-scoped NO globals workdir includes episode_id
  helpers.py        run_ffmpeg(-y) ffprobe_contract(h264+aac) make_filler atomic_rename
                    normalize_pip_preview get_chart_path safe_text() SINGLE sanitizer
  preflight.py      Asset disk permissions media validation
  ffmpeg_core/filters.py   overlay_pip eof_action=REPEAT
  ffmpeg_core/encode.py    encode_segment() CRF-ONLY zero bitrate flags
  ffmpeg_core/probe.py     measure_lufs(JSON) detect_black_frames detect_silence
  segments/base.py         render() NEVER raises filler_result() on failure
  segments/transition.py   0.25s black+whoosh per-output-path dedup
  segments/wrap.py         outro+TTS -an on OUTRO_BRANDED prevents audio bleed
  segments/cold_open.py    intro_tag+music(0.05)+TTS(adelay=300ms amix 0.5 3.0)+loudnorm
  segments/narration.py    bg_loop+TTS+PiP(stream_loop=-1 eof_action=REPEAT) safe_text()
  segments/partner_clip.py scale+crop HDR-tonemap silence-if-no-audio dur-logged
  segments/data_segment.py metrics(cache-first ctx.workdir NOT /tmp) keyword chart
  test_day1.py 6/6  test_day2.py 6/6  test_day3.py 8/8  test_day4.py 7/7  TOTAL 29/29
  AUDIT_PROMPT_TEMPLATE.md  Unconstrained audit find ALL issues no top-3 limit

## THE LAWS
1. render() NEVER raises. filler_result() on failure.
2. CRF-only. ZERO -b:v -maxrate -bufsize. encode.py pure CRF-17.
3. EpisodeContext episode-scoped. Zero module globals.
4. ffprobe_contract: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.
5. Atomic writes only via atomic_rename.
6. safe_text() from helpers.py is THE ONLY drawtext sanitizer.
7. PiP eof_action=REPEAT. stream_loop=-1 on pre-normalized pip_preview.
8. Metrics cache: ctx.workdir/metrics_cache.json. Never /tmp.
9. Outro: -an on OUTRO_BRANDED before stream_loop.
10. 29 tests pass before commit. Unconstrained audit prompt always.

## KEY BUGS FIXED (caused old pipeline failures)
- eof_action=pass->REPEAT: PiP was going static (old logged bug)
- CRF+bitrate conflict: encoder silently ignoring CRF-17 for months
- wrap.py -an: original outro audio was looping over TTS narration
- /tmp race: concurrent CC sessions corrupting metrics cache
- VIDEO_BITRATE purged from constants.py AND encode.py imports
- workdir includes episode_id: concurrent renders now isolated
- safe_text() centralized: inconsistent drawtext causing failures
- Manifest validate(): fast-fail instead of silent zero-content render
AUDIT CHANGE: Old top-3 prompt was suppressing 6 real bugs per audit.
New AUDIT_PROMPT_TEMPLATE.md: unconstrained. 9 findings vs 3.

## REMAINING BUILD PLAN
Day 5 (NEXT): social.py + signal_active.py
  social.py: Optional. 3 X posts drawtext on branded bg.
    Source: spec.social_posts list[{account,text,likes,retweets}]
    Fallback: dark panel. Audio: TTS+loudnorm.
  signal_active.py: Optional.
    Top half: Nostr signal (spec.signal_content{signal_type,signal_body,confidence})
    Bottom strip: ALWAYS Curated Mining sponsor (even without Nostr signal)
    Sponsor text: Curated Mining white-glove Bitcoin mining Section 179 LLC
    Audio: TTS. Brand: red/black/white JetBrainsMono.

Day 6: episode.py manifest->render->concat->QC try/except all filler on crash
Day 7: qc.py PASS/DEGRADED/HOLD min480s max900s max60sfiller max2degraded
Day 8: First full episode render
Day 9-10: Grade A (5 consecutive Gemini 90+/100)

## AUDIT PROCESS
cd ~/protocol_pulse && python3 utils/cross_llm_audit.py --feature assembler-v2-rebuild
Gemini: ROTATED 2026-03-18 confirmed working
GPT-4o: needs quota topup (429 Cycle 2)
Pre-commit gate: blocks pipeline .py without recent audit
Bypass emergencies: HOTFIX_EXEMPT=1 git commit

## INFRA
Relay: relay.protocolpulse.io/exec
Token: 581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552
Python3 urllib only. User-Agent Mozilla/5.0. 30s timeout.
Complex scripts: build locally with heredoc transfer via base64.
Long ops in tmux. CC: tmux new-session -s NAME then unset ANTHROPIC_API_KEY and claude --dangerously-skip-permissions
Git SSH keys on Ultron. yt_cookies.txt in .gitignore NEVER commit.

## CHECKLIST FOR NEW SESSION
1. Read this doc
2. git log --oneline | head -5 (confirm at 4c1a7fc6 or newer)
3. Syntax check all 16 assembler_v2 files
4. test_day1 through test_day4: confirm 29/29 PASS
5. Invariants: VIDEO_BITRATE refs=0 _safe_text-narration=0 workdir-has-episode_id maxrate-encode=0
6. Build Day 5: social.py then signal_active.py
7. After Day 5: unconstrained cross-LLM audit fix all then Day 6

## GIT LOG AT HANDOFF
4c1a7fc6 fix: Grok P0-P2 VIDEO_BITRATE purged stderr structured
a744406a fix: orphaned @staticmethod narration.py
40cd27f4 fix: CRF constants workdir UUID timeouts Law6 safe_text manifest guard
b2b64043 fix: Day 4 audit cache-first HDR tonemap KEYWORD_MAP
a453eb5d fix: remove yt_cookies.txt from git
af02e8a0 feat: Day 4 partner_clip data_segment 7/7
220caa7c fix: Day 3 audit eof_action=repeat safe_text loudnorm cold_open
69064e86 feat: Day 3 cold_open narration PiP 90 frames 8/8
65555e3a fix: Day 2 audit encode_segment probe JSON bare except
331ee70c feat: Day 2 ffmpeg_core filters encode probe base transition wrap 6/6
f5a93805 fix: Day 1 audit codec checks chart fallback preflight
0631088b feat: Day 1 constants manifest state helpers preflight 6/6
