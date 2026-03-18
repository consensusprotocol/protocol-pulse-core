# X SPACES PIPELINE GOSPEL
## LAWS
1. Capture and assembler segment NEVER in same process.
2. ffmpeg capture: os.setsid() + kill(-pgid) cleanup.
3. One lock file per handle. No dual-capture.
4. Hard timeout 14400s on any recording.
5. SQLite WAL state machine is source of truth.
6. faster_whisper singleton WhisperWorker.get().
7. Clips: data/spaces/clips/date_handle_n.m4a + json.
8. Assembler segment: filler if no clips in 3-6hrs.
9. Waveform: ffmpeg showwaves on black bg.
10. Cron: monitor 5min, curator+clipper 1hr.
