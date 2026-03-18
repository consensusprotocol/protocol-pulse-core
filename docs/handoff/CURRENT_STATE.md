# PROTOCOL PULSE V2 ASSEMBLER REBUILD -- HANDOFF DOC
Generated: 2026-03-18 05:15 UTC -- UPDATED CORRECT VERSION
HEAD: afae87d0 | Repo: consensusprotocol/protocol-pulse-core
Raw: https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/docs/handoff/CURRENT_STATE.md

## STATUS: DAYS 1-4 COMPLETE 29/29 TESTS PASSING -- NEXT: DAY 5
## NOTE: Older doc (d2dd725a, Mar 12) is STALE. This is current.

## WHAT WAS BUILT (2026-03-18)
assembler_v2 modular rebuild at video_pipeline_v3/assembler_v2/
Tests: 29/29 PASS (test_day1 6/6, test_day2 6/6, test_day3 8/8, test_day4 7/7)

## FILES
video_pipeline_v3/assembler_v2/
  constants.py  manifest.py  state.py  helpers.py  preflight.py
  ffmpeg_core/filters.py  ffmpeg_core/encode.py  ffmpeg_core/probe.py
  segments/base.py  segments/transition.py  segments/wrap.py
  segments/cold_open.py  segments/narration.py
  segments/partner_clip.py  segments/data_segment.py
  test_day1.py 6/6  test_day2.py 6/6  test_day3.py 8/8  test_day4.py 7/7

## THE 10 LAWS
1. render() NEVER raises. filler_result() on failure.
2. CRF-only. ZERO -b:v -maxrate -bufsize.
3. EpisodeContext episode-scoped. Zero module globals.
4. ffprobe_contract: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.
5. Atomic writes via atomic_rename.
6. safe_text() from helpers.py is THE ONLY drawtext sanitizer.
7. PiP eof_action=REPEAT. stream_loop=-1 on pre-normalized pip_preview.
8. Metrics cache: ctx.workdir/metrics_cache.json. Never /tmp.
9. Outro: -an on OUTRO_BRANDED before stream_loop.
10. 29 tests pass before commit.

## TEST RUNNER
python3 -c "import sys; sys.path.insert(0,'/home/ultron/protocol_pulse/video_pipeline_v3'); exec(open('/home/ultron/protocol_pulse/video_pipeline_v3/assembler_v2/test_dayN.py').read())"

## INVARIANT CHECKS
grep -r VIDEO_BITRATE assembler_v2/ | grep -v .pyc  (expect 0)
grep -c _safe_text assembler_v2/segments/narration.py  (expect 0)
grep workdir assembler_v2/state.py | grep episode_id  (must exist)
grep -c maxrate assembler_v2/ffmpeg_core/encode.py  (expect 0)

## DAY 5 NEXT -- BUILD FROM SCRATCH
social.py: assembler_v2/segments/social.py
  3 X posts on branded bg. spec.social_posts list. Fallback dark panel.
signal_active.py: assembler_v2/segments/signal_active.py
  Top: Nostr signal. Bottom: ALWAYS Curated Mining sponsor.
  Sponsor: Curated Mining white-glove Bitcoin mining Section 179 LLC
  Audio TTS. Brand red/black/white JetBrainsMono.

## INFRA
Relay token: <REDACTED-stored-in-env>
CC: tmux new-session -s NAME ; unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions
