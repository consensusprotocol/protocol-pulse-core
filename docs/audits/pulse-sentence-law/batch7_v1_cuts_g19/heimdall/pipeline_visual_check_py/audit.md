# Heimdall audit

**Question:** Protocol Pulse news-video pipeline verification (no publishing). Changes on top of an audited batch: (1) the visual checklist's credits question now gets the channel list from the edit decision list (a 9:16 crop can hide a show's branding); (2) the 'next shot visible before a cut' line is answered one cut at a time: the frame 3 frames before and 3 frames after each cut, side by side, asked of two vision models; any 'yes', missing answer or error fails; the whole-sheet answer for that line is kept only as advisory; (3) a vision reply missing up to 3 final closing braces is closed before parsing (nothing else repaired); (4) a new deterministic gate G19: on each finished video, no hard shot change (ffmpeg scene score >= 0.3) inside a talking-head segment's clean span before its first word or after its last word, with speech times from the prepare stage's record, failing closed without a record; (5) batch-6 audit fixes (stand-alone subject terms, replay catch-all, shot-snap test strengthening, a reason string). Find real bugs: a check that can pass when it should fail, wrong frame/time arithmetic, a repair that accepts a reply the model did not give, a gate that ignores a segment. Only state what you can verify from the diff. (this chunk: pipeline/visual_check.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0225
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [medium] The brace-repair loop appends closing braces to the entire reply and then scans all '{' positions, so it can complete and return a later incomplete JSON object even when the reply already contains a complete object without the key. This violates the stated rule that only a reply whose only fault is up to 3 missing closing braces at its very end is closed, and it can accept an answer the model did not give. (agree: 0)
- deepseek:F2 [high] Swapped frame/time arithmetic in boundary_pairs: the before frame should be taken from the end of the previous segment (a['end'] - BOUNDARY_FRAMES / FPS) and the after frame from the start of the next segment (b['start'] + BOUNDARY_FRAMES / FPS). The code uses b['start'] - ... and a['end'] + ..., which grabs frames from the wrong segments when there is a gap or dissolve, so the boundary check can look at frames that are not actually before/after the cut. (agree: 0)

## Added in cross-examination (not voted on)
- none
