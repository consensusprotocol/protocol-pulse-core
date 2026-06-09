# Protocol Pulse Video Pipeline — AutoResearch Program

## Goal
Make the Protocol Pulse video pipeline render successfully every time. The pipeline generates a daily Bitcoin video briefing from partner channel clips, TTS narration, charts, and social posts.

## Current State
- Pipeline location: ~/protocol_pulse/video_pipeline_v3/
- Entry point: `python3 daily_producer.py --test --no-resume --skip-scan`
- Last successful render: V56b (May 25, 2026) — 124MB, 4.2 min
- Current failure: Assembly stage crashes due to complex ffmpeg filtergraphs timing out

## The Problem
`run_ffmpeg_filtergraph()` in `assembler_common.py` times out at 900s for simple video segments. The filtergraphs in `render_social.py` and `render_narrator.py` are too complex for CPU processing. NVENC GPU encoding was tried but only speeds up the encode step, not the filter processing.

## Success Metric
A test render completes with:
1. Output file > 50MB
2. Duration > 180 seconds
3. No assembly crash
4. ffprobe validates 1920x1080, h264, aac

## Experiment Loop
1. Read the crash traceback from the latest render log
2. Identify which filtergraph function crashed
3. SIMPLIFY that filtergraph (fewer overlays, simpler compositing)
4. Run a test render: `cd ~/protocol_pulse/video_pipeline_v3 && CUDA_VISIBLE_DEVICES=0 python3 daily_producer.py --test --no-resume --skip-scan 2>&1 | tee /tmp/render_test.log`
5. Check result: did it complete? Check output file size and duration
6. If success: commit with "PASS: [description]"
7. If fail: revert, try a different simplification, repeat

## Constraints
- Do NOT change clip_extractor.py and assembler.py in the same commit
- Do NOT remove the timeout=900 force in run_ffmpeg
- Do NOT change fps=30 anywhere without measuring AV sync before/after
- TTS uses Kokoro (tts_kokoro function in tts_engine.py) — do NOT call tts_chatterbox (undefined)
- All presets should be "fast" or "ultrafast" for intermediates
- The music mix step in assembler.py must use -c:v copy (stream copy video)

## Key Files
- assembler_common.py — run_ffmpeg, run_ffmpeg_filtergraph (core encode functions)
- render_social.py — make_social_card_visual (CRASHES — needs simplification)
- render_narrator.py — make_host_visual (CRASHES — needs simplification)
- render_clip.py — make_clip_visual
- render_intro_outro.py — intro/outro rendering
- assembler.py — orchestrator, do NOT add logic here

## Simplification Strategy
The filtergraphs have too many overlay layers, drawtext calls, and compositing operations. Simplify by:
1. Reducing overlay count (remove decorative elements, keep essential text)
2. Using pre-rendered static backgrounds instead of generating them via filtergraph
3. Breaking complex filtergraphs into multiple simple passes instead of one massive filter_complex
4. Using -preset ultrafast for all intermediate renders
5. Pre-rendering backgrounds as simple PNG + overlaying text in a second pass
