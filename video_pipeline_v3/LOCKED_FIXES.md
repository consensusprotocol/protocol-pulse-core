# LOCKED FIXES — Protocol Pulse Video Pipeline

Every fix below is verified and protected by `regression_test.sh`.
**DO NOT revert or modify these without updating the regression test.**

---

## FIX-001: No aresample=async=1 in assembler.py
- **Broken:** Lip sync drift in final output — audio drifts 0.1-0.5s from video
- **Root cause:** `aresample=async=1` in assembler's normalization/concat/mastering
  silently resamples audio to "fill gaps", shifting audio relative to video
- **Fix:** Replaced all `aresample=async=1` with `aresample=48000` (simple resample,
  no async correction). `async=1` only exists in clip_extractor.py's `fix_av_sync()`
  where it's needed to fix broken source clips BEFORE they enter the pipeline.
- **Regression test:** `! grep -q 'async=1' assembler.py`
- **Locked:** 2026-04-03

## FIX-002: No aresample=async=1 in render modules
- **Broken:** Same lip sync issue propagated through render_clip, render_narrator,
  render_intro_outro, assembler_common, daily_producer
- **Fix:** Same as FIX-001 — replaced with `aresample=48000` in all render modules
- **Regression test:** Separate checks for each file (FIX-002a through FIX-002e)
- **Locked:** 2026-04-03

## FIX-003: async=1 MUST remain in clip_extractor.py
- **Purpose:** Source clips from YouTube may have broken AV sync from yt-dlp muxing.
  `fix_av_sync()` applies the nuclear fix with `aresample=async=1:min_hard_comp=0.1`
  to realign audio. This is the ONLY place async correction belongs.
- **Regression test:** `grep -q 'async=1' clip_extractor.py`
- **Locked:** 2026-04-03

## FIX-004: Episode-level whoosh mastering disabled
- **Broken:** Double/triple whoosh SFX at every transition
- **Root cause:** `make_transition_visual()` bakes whoosh into transition segments,
  then episode-level mastering in `concatenate_parts()` added ANOTHER whoosh at
  every part boundary. 2-3 whooshes overlapping at each transition.
- **Fix:** Set `has_whoosh = False` in episode mastering (assembler.py ~line 547).
  Per-segment whoosh from `make_transition_visual()` is sufficient.
- **Regression test:** `grep -q 'has_whoosh = False' assembler.py`
- **Locked:** 2026-04-03

## FIX-005: PiP retry at 40% for dark-intro channels
- **Broken:** Simply Bitcoin and other channels in FORCE_SKIP_CHANNELS show blank PiP
- **Root cause:** 15s forced intro skip + PiP extraction at 15% = dark logo frames.
  `_verify_pip()` rejects (YAVG < 12). No retry → blank PiP.
- **Fix:** After 15% fails, retry at 40% (clip_a) and 80% (clip_b)
- **Regression test:** `grep -q 'position_pct=0.40' assembler.py`
- **Locked:** 2026-04-03

## FIX-006: Music locked to confident_02.mp3
- **Broken:** Random music track selection sometimes picked inappropriate tracks
- **Fix:** Hardcoded confident_02.mp3 as signature soundtrack
- **Regression test:** `grep -q 'confident_02' daily_producer.py`
- **Locked:** 2026-03-31

## FIX-007: No gunicorn on port 5000
- **Broken:** Gunicorn and Waitress fighting for port 5000
- **Fix:** Waitress is the ONLY web server. Gunicorn is RETIRED.
- **Regression test:** `! grep -rq 'gunicorn.*5000' ../scripts/*.sh`
- **Locked:** 2026-03-04

## FIX-008: Avatar server blocked by hook
- **Broken:** Avatar server consuming 6GB RAM despite being disabled
- **Fix:** pre_bash_gate.sh blocks any command referencing avatar_server.
  Cron watchdog disabled 2026-04-03.
- **Regression test:** `grep -qi 'avatar' ../scripts/hooks/pre_bash_gate.sh`
- **Locked:** 2026-04-03

## FIX-009: CLAUDE.md constitution
- **Purpose:** Inviolable rules that CC sessions must follow
- **Regression test:** `test -f ../CLAUDE.md`
- **Locked:** 2026-03-04

## FIX-010: CC hooks configured
- **Purpose:** Pre-commit audit gate, pre-bash gate, stop audit
- **Regression test:** `test -f ../.claude/settings.json`
- **Locked:** 2026-03-04

## FIX-011: No Kokoro/dual-host
- **Broken:** Kokoro TTS caused crashes, dual-host caused inconsistent voice
- **Fix:** Single PBX host (Mark) for all narration. Kokoro removed.
- **Regression test:** `! grep -qi 'kokoro' tts_engine.py`
- **Locked:** 2026-03-09

## FIX-012: PiP fallback in assembler
- **Broken:** Narration segments with >5s bare background (no PiP)
- **Fix:** `_any_pip` fallback uses nearest available clip for any segment
- **Regression test:** `grep -q '_any_pip' assembler.py`
- **Locked:** 2026-03-20

## FIX-013: Stay sovereign signoff
- **Purpose:** Brand consistency — every episode ends with "Stay sovereign"
- **Regression test:** Check script_writer.py or daily_producer.py
- **Locked:** 2026-03-09

## FIX-014: ElevenLabs pronunciation dictionary
- **Broken:** Fragile regex PRONUNCIATION_MAP mutated text before caching
- **Fix:** Server-side dictionary (id=LK24Dt58S40g429DUG9C) applied by ElevenLabs
  before synthesis. Regex map commented out.
- **Regression test:** `grep -q 'pronunciation_dictionary_locators' tts_engine.py`
- **Locked:** 2026-04-03

## FIX-015: X posts in Signal Active
- **Broken:** Signal Active segment only showed Nostr posts, no X data
- **Fix:** Added `_read_x_posts()` to signal_intelligence.py, X posts render in
  left column when X Spaces unavailable
- **Regression test:** `grep -q 'x_posts' signal_intelligence.py`
- **Locked:** 2026-04-03
