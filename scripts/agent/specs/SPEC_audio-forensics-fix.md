# FEATURE SPEC — audio-forensics-fix
## IDENTITY
- **FEATURE:**       Audio forensics correction render
- **BRANCH:**        agent/audio-forensics-fix
- **WORKTREE_DIR:**  ~/worktrees/audio-forensics-fix
- **SESSION:**       agent_audio-forensics-fix
- **PRIORITY:**      🔴 High (BLOCKED on PBX forensic notes — launch after notes received)

## SCOPE
Fix all confirmed issues from the forensic report on pulse_check_20260308_063020.mp4.
H1 (audio too quiet), H2 (black cuts at 6:55/7:05), M1-M6 fixes as confirmed by PBX
forensic notes. Produces a corrected render that passes all forensic checks.
WAIT for PBX forensic notes before launching — spec will be updated with exact fixes.

## SUCCESS CRITERIA
1. LUFS target: -12 to -14 (was -17.7)
2. True peak: -1.5 dBFS (was -5.0)
3. LRA: 6-9 LU (was 2.8)
4. Zero black cuts detected by blackdetect (threshold 0.1, duration 0.5s)
5. Zero silence gaps >0.2s at segment boundaries
6. TradingView chart renders real data (Playwright fix)
7. Micro black flashes <3 at transitions (from 12)
8. Auto-forensic post-render analysis runs and passes
9. Regression zero FAILs

## FILES_TO_TOUCH
- `video_pipeline_v3/assembler.py` — loudnorm params, fade timing, black cut fallback
- `video_pipeline_v3/chart_capture.py` — Playwright multiline string fix
- `video_pipeline_v3/daily_run.py` — silence at open fix, BGM sidechain params
- [AWAITING PBX NOTES for final list]

## FILES_NEVER_TOUCH
- `video_pipeline_v3/PIPELINE_LAWS.md`
- `regression_test.sh`
- `video_pipeline_v3/tts_engine.py`

## BOOT SEQUENCE
1. Read this spec
2. Read PIPELINE_LAWS.md
3. Read AGENT_CONTEXT.md
4. Read ~/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS_ADDENDUM.md if exists
5. Run ffprobe on latest render to confirm current baseline
6. Begin fixes in order: H1 → H2 → M4 → M5 → M1 → M2

## TEST COMMAND
```bash
# After render:
FILE=$(ls ~/worktrees/audio-forensics-fix/video_pipeline_v3/output/pulse_check_*.mp4 | tail -1)
ffprobe -v error -show_entries format=duration,size -of csv=p=0 "$FILE"
ffmpeg -i "$FILE" -af ebur128 -f null - 2>&1 | grep "Integrated loudness"
ffmpeg -i "$FILE" -vf blackdetect=d=0.5:pix_th=0.10 -an -f null - 2>&1 | grep -c blackdetect
```

## GPU USAGE
- Requires GPU render: YES
- Acquire lock before full render

## PR FORMAT
- **Title:** `fix(audio-forensics): H1/H2/M1-M6 render quality corrections`

## STATUS
- [x] Spec written
- [ ] BLOCKED: awaiting PBX forensic notes
- [ ] Agent launched
