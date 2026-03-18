# ASSEMBLER V2 REBUILD GOSPEL
## THE LAWS
1. render() NEVER raises. filler_result() on any failure.
2. CRF-only encoding. No -b:v/-maxrate/-bufsize alongside -crf.
3. EpisodeContext episode-scoped. No module globals.
4. ffprobe_contract: 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo.
5. Atomic writes via atomic_rename.
6. safe_text() from helpers.py is the single drawtext sanitizer.
7. PiP: eof_action=repeat. stream_loop=-1 on pre-normalized pip_preview.
8. Metrics cache scoped to ctx.workdir NOT /tmp.
9. Outro: -an strips audio before stream_loop.
10. All 29 tests pass before commit.
