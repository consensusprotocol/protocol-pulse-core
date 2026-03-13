Read PIPELINE_LAWS.md first. This is a SURGICAL fix session — do NOT touch anything except what's listed below.

## DIAGNOSIS FROM V9 LOGS
The TTS IS generating (28 cache files exist). The failures are in the ASSEMBLER:

1. **True peak: 2.6 dBTP** (limit -1.5) — loudnorm is not controlling peaks. The assembler is applying loudnorm but it's not working. Fix: in assembler.py, find all `loudnorm=I=-14:TP=` calls and change TP value to `-2.0` (more headroom). Also add `dynaudnorm=f=150:g=15` as a second-pass limiter after loudnorm.

2. **4 silent gaps >2s** — Eryn lines exist in TTS cache but are being dropped during assembly. Find where host segments are assembled and add a file-size check: if any TTS file is <5KB, log a WARNING and substitute 0.5s silence pad rather than leaving a gap. The gap itself causes black frames downstream.

3. **Duration 681s vs 400-600s target** — 5 clips at ~130s avg is too long. In manifest_builder.py or daily_producer.py, find the clip duration target and reduce max clip duration from whatever it is now to 90s max per clip (target 5 clips × 90s = 450s + narration ≈ 540s total).

4. **Bitrate 2.8Mbps** — find the ffmpeg encoding parameters and increase CRF slightly or add `-b:v 3.5M` floor to guarantee minimum bitrate.

## WHAT TO DO
1. Read video_pipeline_v3/assembler.py — find loudnorm calls, fix TP and add dynaudnorm limiter
2. Read video_pipeline_v3/assembler.py — find where TTS audio files are concatenated, add size check
3. Read video_pipeline_v3/manifest_builder.py OR daily_producer.py — find clip duration cap, set to 90s
4. Read video_pipeline_v3/assembler.py — find output encoding params, add bitrate floor

Run regression_test.sh after — must show zero FAILs.
Commit: git add -A && git commit -m "fix(assembler): true peak limiter, silent gap guard, clip duration cap, bitrate floor" && git push