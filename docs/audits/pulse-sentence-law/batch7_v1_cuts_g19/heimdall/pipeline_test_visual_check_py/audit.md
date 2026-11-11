# Heimdall audit

**Question:** Protocol Pulse news-video pipeline verification (no publishing). Changes on top of an audited batch: (1) the visual checklist's credits question now gets the channel list from the edit decision list (a 9:16 crop can hide a show's branding); (2) the 'next shot visible before a cut' line is answered one cut at a time: the frame 3 frames before and 3 frames after each cut, side by side, asked of two vision models; any 'yes', missing answer or error fails; the whole-sheet answer for that line is kept only as advisory; (3) a vision reply missing up to 3 final closing braces is closed before parsing (nothing else repaired); (4) a new deterministic gate G19: on each finished video, no hard shot change (ffmpeg scene score >= 0.3) inside a talking-head segment's clean span before its first word or after its last word, with speech times from the prepare stage's record, failing closed without a record; (5) batch-6 audit fixes (stand-alone subject terms, replay catch-all, shot-snap test strengthening, a reason string). Find real bugs: a check that can pass when it should fail, wrong frame/time arithmetic, a repair that accepts a reply the model did not give, a gate that ignores a segment. Only state what you can verify from the diff. (this chunk: pipeline/test_visual_check.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0110
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [high] The test asserts that a reply missing exactly 3 final closing braces returns None, but the spec states 'a vision reply missing up to 3 final closing braces is closed before parsing'. The string '{"answers": {"credits_round_and_match": {"answer": "yes", "why": "cut off"' has 3 opening braces and 0 closing braces; appending 3 '}' yields valid JSON. The test will pass if the implementation only repairs 1 or 2 missing braces (a real bug), masking the defect. It should assert a successful parse (a dict with one key) instead of None. (agree: 1)

## Added in cross-examination (not voted on)
- none
