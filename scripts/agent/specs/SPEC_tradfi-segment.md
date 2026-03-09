# FEATURE SPEC — tradfi-segment
## IDENTITY
- **FEATURE:**       Suits & Sats — TradFi segment renderer
- **BRANCH:**        agent/tradfi-segment
- **WORKTREE_DIR:**  ~/worktrees/tradfi-segment
- **SESSION:**       agent_tradfi-segment
- **PRIORITY:**      🔴 High

## SCOPE
Wire the Suits & Sats segment into the Pulse Check pipeline. On Monday and Friday,
the daily_run.py pipeline injects a `tradfi_weekly` segment type that reads from
tradfi_weekly.json, generates a 60-90s Eryn+Brian exchange via TTS, assembles it
with the SUITS & SATS eyebrow overlay, and inserts it after the data segment.
Does NOT build the frontend dashboard or Grok integration — pipeline only.

## SUCCESS CRITERIA
1. `tradfi_weekly` segment type handled in assembler.py without error
2. On Monday/Friday: script_writer.py includes suits_and_sats block in dialogue
3. TTS generated: Eryn reads TradFi signal, Brian delivers Bitcoin lens translation
4. Visual: data_segment scene with "SUITS & SATS // BITCOIN LENS" eyebrow text
5. Segment duration 60-90s (verified via ffprobe on test render)
6. Non Monday/Friday: segment skipped cleanly, no error
7. Test render completes without FAIL or traceback
8. Regression passes zero FAILs

## FILES_TO_TOUCH
- `video_pipeline_v3/daily_run.py` — inject tradfi_weekly segment on Mon/Fri
- `video_pipeline_v3/script_writer.py` — add suits_and_sats dialogue generator
- `video_pipeline_v3/assembler.py` — add tradfi_weekly segment type handler
- `video_pipeline_v3/utils/tradfi_monitor.py` — ensure weekly json write path correct

## FILES_NEVER_TOUCH
- `video_pipeline_v3/PIPELINE_LAWS.md`
- `regression_test.sh`
- `video_pipeline_v3/tts_engine.py` — read only
- Any file in ~/protocol_pulse/ (production)

## SHARED_DEPS
- `video_pipeline_v3/tts_engine.py` — use existing TTS, do not modify
- `video_pipeline_v3/assembler.py` data_segment scene — extend, do not replace
- `video_pipeline_v3/data/intelligence/tradfi_weekly.json` — read only

## BOOT SEQUENCE
1. Read this spec fully
2. Read PIPELINE_LAWS.md
3. Read AGENT_CONTEXT.md
4. cat ~/protocol_pulse/video_pipeline_v3/utils/tradfi_monitor.py | head -80
5. cat ~/protocol_pulse/video_pipeline_v3/assembler.py | grep -n 'x_spaces\|data_segment\|segment_type' | head -20
6. Begin implementation

## TEST COMMAND
```bash
cd ~/worktrees/tradfi-segment/video_pipeline_v3
TEST_MODE=true python3 -c "
from script_writer import generate_suits_and_sats_block
result = generate_suits_and_sats_block({'signals':[],'macro_tone':'BULLISH FOR BITCOIN','macro_summary':'Test','avg_btc_lens_sentiment':65})
assert result is not None, 'suits_and_sats block returned None'
assert 'dialogue' in result or 'text' in result, 'no dialogue in result'
print('PASS: suits_and_sats block generated')
"
```

## LAWS TO LOAD
- [x] PIPELINE_LAWS.md
- [ ] ARTICLE_PAGE_LAWS.md
- [ ] LIVE_INTELLIGENCE_LAWS.md

## GPU USAGE
- Requires GPU render: YES (test render only)
- Acquire: ~/protocol_pulse/scripts/agent/gpu_lock.sh acquire agent_tradfi-segment
- Use --cached-only flag first to avoid full channel scan

## PR FORMAT
- **Title:** `feat(tradfi-segment): Suits & Sats pipeline integration — Mon/Fri TradFi segment`

## STATUS
- [x] Spec written
- [ ] Agent launched
- [ ] Build complete
- [ ] Tests passing
- [ ] PR opened
