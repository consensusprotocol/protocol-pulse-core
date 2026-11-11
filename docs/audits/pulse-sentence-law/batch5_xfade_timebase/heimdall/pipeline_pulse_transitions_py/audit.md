# Heimdall audit

**Question:** Protocol Pulse video concat with ffmpeg 4.4.2. Fix: xfade refused a dissolve whose first input was a concat filter output (timebase 1/1000000) while the second input was 1/24 (after fps=24). The fix inserts settb=1/24 on the running input before xfade. Check: can settb change any frame time or the A/V lock, could the xfade offset (computed on the timeline in seconds) now land on a different frame, is any other junction kind (dip, concat, inserted wipe) affected, and does the new test really reproduce the production failure. Only state what you can verify from the diff. (this chunk: pipeline/pulse_transitions.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0069
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
