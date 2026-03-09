# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# ------------------------------------------------------------

# PROTOCOL PULSE — GOSPEL: VIDEO PIPELINE AUDIO FIX
# Branch: feature/video-audio-fix | Created: 2026-03-09
# BLOCKING ON: PBX forensic notes for pulse_check_20260308_063020.mp4
# VIDEO LINK: https://video.protocolpulse.io/video_pipeline_v3/output/pulse_check_20260308_063020.mp4
---

## WHAT THIS IS
The APEX V2 pipeline (pulse_check_20260308_063020.mp4, 415MB, 8m20s) has known
audio issues that need PBX's forensic notes before the fix session can run.
Once notes are received, this gospel governs the fix session.

## THE LAWS (from PIPELINE_LAWS.md)
### Always run auto-forensic after render: ffprobe, blackdetect, silencedetect, ebur128
### Never skip regression_test.sh — zero FAILs before commit
### AV sync diagnosis first: check raw clips before touching assembler
### Audio target: -14 LUFS integrated, -1 dBTP ceiling, music at -14 LUFS with sidechain

## WHAT PBX SHOULD PROVIDE (watch the video and note):
1. **Timestamp of any audio cutoff** — where does speech get cut?
2. **AV sync observation** — do lips match? How far off?
3. **Music volume** — too loud? Too quiet? Ducking working?
4. **Any black frames** — timestamp if visible
5. **Overall quality verdict** — what's the worst thing to fix?

## CLAUDE CODE PROMPT (fire AFTER PBX provides notes)
```
Read ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md IN FULL.
Read ~/protocol_pulse/docs/gospels/VIDEO_AUDIO_FIX_GOSPEL.md.
Branch: feature/video-audio-fix.

PBX FORENSIC NOTES: [INSERT NOTES HERE]

Run auto-forensic first:
ffprobe video_pipeline_v3/output/pulse_check_20260308_063020.mp4 -v quiet -show_streams
ffmpeg -i output.mp4 -vf blackdetect=d=0.1:pix_th=0.10 -f null - 2>&1 | grep black_
ffmpeg -i output.mp4 -af silencedetect=n=-50dB:d=0.5 -f null - 2>&1 | grep silence
ffmpeg -i output.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -20

Then diagnose based on forensic output + PBX notes.
Fix root cause. Never patch symptoms.
regression_test.sh: zero FAILs → commit + push feature/video-audio-fix
```

## LLM TRIFECTA
### Claude: After PBX provides notes, run Claude gap analysis on current assembler.py
### Gemini: "Review FFmpeg sidechain ducking implementation — is it correct?"
### Grok: "ElevenLabs eleven_turbo_v2_5 — any known audio cutoff bugs with long texts?"
