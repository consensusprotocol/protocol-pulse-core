# FEATURE SPEC — shorts-pipeline
## IDENTITY
- **FEATURE:**       Vertical shorts overhaul
- **BRANCH:**        agent/shorts-pipeline
- **WORKTREE_DIR:**  ~/worktrees/shorts-pipeline
- **SESSION:**       agent_shorts-pipeline
- **PRIORITY:**      🟡 Medium

## SCOPE
Overhaul shorts_cutter.py to produce 3 polished 9:16 vertical clips per episode.
Fix the existing arg-swap bug (already patched in daily_run.py). Add proper
vertical layout: talking head top half, caption lower third, Bitcoin price ticker
at bottom. Clips should be 45-75s, portrait 1080x1920, from the episode's best
quotes. Add Suits & Sats short as a 4th clip on Mon/Fri.

## SUCCESS CRITERIA
1. 3 shorts generated per episode, 4 on Mon/Fri (Suits & Sats clip)
2. Output: 1080x1920, 30fps, H264, AAC, <100MB each
3. Each clip 45-75s verified by ffprobe
4. Bitcoin price ticker visible at bottom (static from daily_signals.json)
5. Quote caption rendered as lower-third text overlay
6. No black bars, no letterboxing, correct 9:16 AR
7. generate_shorts(script, shorts_dir) signature works correctly
8. Regression zero FAILs

## FILES_TO_TOUCH
- `video_pipeline_v3/shorts_cutter.py` — full overhaul
- `video_pipeline_v3/daily_run.py` — confirm generate_shorts call signature correct

## FILES_NEVER_TOUCH
- `video_pipeline_v3/PIPELINE_LAWS.md`
- `video_pipeline_v3/assembler.py`
- `regression_test.sh`

## GPU USAGE
- Requires GPU render: YES (FFmpeg GPU encode for shorts)

## PR FORMAT
- **Title:** `feat(shorts-pipeline): vertical shorts overhaul — 9:16, captions, BTC ticker`

## STATUS
- [x] Spec written
- [ ] Agent launched
