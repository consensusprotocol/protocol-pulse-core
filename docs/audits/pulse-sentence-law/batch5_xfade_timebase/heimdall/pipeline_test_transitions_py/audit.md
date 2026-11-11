# Heimdall audit

**Question:** Protocol Pulse video concat with ffmpeg 4.4.2. Fix: xfade refused a dissolve whose first input was a concat filter output (timebase 1/1000000) while the second input was 1/24 (after fps=24). The fix inserts settb=1/24 on the running input before xfade. Check: can settb change any frame time or the A/V lock, could the xfade offset (computed on the timeline in seconds) now land on a different frame, is any other junction kind (dip, concat, inserted wipe) affected, and does the new test really reproduce the production failure. Only state what you can verify from the diff. (this chunk: pipeline/test_transitions.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0074
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [critical] The _seg call for clip_02 is malformed: the filename 'r.mp4' is missing and the colour/frequency/duration/onset arguments are passed inside os.path.join instead of as separate _seg arguments. os.path.join(self.tmp, "ramp", 880, 3, (0.4, 2.6)) will raise TypeError in Python 3 because 880, 3, and (0.4, 2.6) are not str or os.PathLike. The test cannot execute at all, so it does not reproduce the production xfade timebase failure. (agree: 0)
- qwen27b:F2 [high] Even ignoring the TypeError, the resulting tuple has only 2 elements ("clip_02", <seg_result>) whereas segs[0] and segs[1] are 3-element tuples (label, seg, channel). Any downstream code that unpacks or indexes segs[i][2] for the channel label will raise IndexError or pass the wrong value to TR.plan, so the test would not exercise the A/A/B channel plan it claims to reproduce. (agree: 0)

## Added in cross-examination (not voted on)
- none
