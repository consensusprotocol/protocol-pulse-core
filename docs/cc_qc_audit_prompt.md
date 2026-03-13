Read PIPELINE_LAWS.md first. Then read video_pipeline_v3/quality_gate.py (or wherever the QC score is calculated that produces the "QUALITY SCORE: 94/100 PASS" output seen in logs).

PROBLEM: The internal pipeline QC is reporting 94/100 PASS on renders that Gemini grades F (29-38/100). The QC system is blind to:
1. Eryn TTS complete silence (all her lines generate zero audio / empty files)
2. Mid-video black frames (30+ second segments)  
3. Freeze frames (21 instances)
4. Audio true peak clipping (+0.4 dBFS, exceeds -1.0 dBFS limit)

TASK: Audit and fix the QC system so it catches these failures BEFORE reporting a score.

Specifically:
1. Find where QUALITY SCORE is calculated — likely quality_gate.py, daily_producer.py step 12/12b, or assembler.py
2. Add real ffprobe checks:
   - Silence detection: ffmpeg silencedetect — if any host has >5s total silence, score=0, FAIL
   - Black frame detection: ffmpeg blackdetect — if any mid-video black segment >2s, score=0, FAIL  
   - True peak check: ffmpeg ebur128 — if true peak > -1.0 dBFS, deduct 20 points
   - TTS file validation: after each TTS call, check file size > 10KB — if any host file is <10KB, FAIL immediately before render starts
3. The TTS pre-check is most critical — add it to tts_engine.py so that if ElevenLabs returns empty/tiny audio for ANY line, it raises RuntimeError immediately instead of silently writing a 0-byte file that causes black frames downstream
4. Fix the score calculation to reflect actual failures — a render with silent hosts should never score above 30

After fixing, run regression_test.sh — must show zero FAILs before committing.

Commit: git add -A && git commit -m "fix(qc): add real ffprobe silence/black/peak checks, TTS pre-validation" && git push
