# Heimdall audit

**Question:** Protocol Pulse news-video pipeline. Changes: (1) pipeline/transitions.py renamed pulse_transitions.py because render16 puts a legacy folder with its own transitions.py first on sys.path (import shadowing); (2) a contact sheet of the finished video plus a 6-line visual checklist answered by two vision models, any no/missing/unparseable answer = HOLD, added on top of existing gates, never replacing one; (3) fade-out retry made transactional (a moved cut is kept only if the re-prepared clip passes the whole contract, else original cut and clip restored); (4) one function decides whether cuts are machine-placed; (5) Telegram delivery attaches the sheets. Find real bugs: wrong pass/fail decisions, a gate that can pass when it should hold, crashes, lost files, state left inconsistent after a failure. Only state what you can verify from the diff. (this chunk: pipeline/pulse_transitions.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0255
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [medium] Temp directory created by tempfile.mkdtemp is never cleaned up. If render_wipe is called repeatedly (e.g., across multiple runs or retries), orphaned directories accumulate on disk, each containing PNG frames and a WAV file. (agree: 1)
- qwen27b:F2 [medium] The xfade offset can be negative when the first segment's frame count equals the dissolve frame count (e.g. a 6-frame talking-head clip with a 6-frame dissolve). In that case t == dd, so offset = t - dd - 1/FPS = -1/FPS ≈ -0.0417. ffmpeg's xfade filter does not accept a negative offset and will either error out or produce a corrupt first frame, failing the entire concat. (agree: 1)
- qwen27b:F3 [low] jmap is built with segs.index(segments[j["after"]]), which returns the first positional match. If two segments in the manifest share an identical (label, path, type) tuple, the junction is silently attached to the wrong segment, producing a transition at the wrong point in the timeline (or no transition at all for the intended pair). (agree: 1)

## Added in cross-examination (not voted on)
- qwen27b: [low] render_wipe passes -t 0.3333 (4-decimal truncation of 8/24=0.33333…) to ffmpeg. The 8th frame spans [7/24, 8/24) = [0.29167, 0.33333). Because 0.3333 < 0.33333, ffmpeg may treat the output as ending before the 8th frame's nominal end, potentially producing a 7-frame clip instead of 8. Downstream, _frames() would return 7, and the concat timeline would be off by one frame at every C-junction.
