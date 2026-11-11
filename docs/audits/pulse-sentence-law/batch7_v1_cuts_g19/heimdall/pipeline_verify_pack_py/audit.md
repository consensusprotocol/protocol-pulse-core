# Heimdall audit

**Question:** Protocol Pulse news-video pipeline verification (no publishing). Changes on top of an audited batch: (1) the visual checklist's credits question now gets the channel list from the edit decision list (a 9:16 crop can hide a show's branding); (2) the 'next shot visible before a cut' line is answered one cut at a time: the frame 3 frames before and 3 frames after each cut, side by side, asked of two vision models; any 'yes', missing answer or error fails; the whole-sheet answer for that line is kept only as advisory; (3) a vision reply missing up to 3 final closing braces is closed before parsing (nothing else repaired); (4) a new deterministic gate G19: on each finished video, no hard shot change (ffmpeg scene score >= 0.3) inside a talking-head segment's clean span before its first word or after its last word, with speech times from the prepare stage's record, failing closed without a record; (5) batch-6 audit fixes (stand-alone subject terms, replay catch-all, shot-snap test strengthening, a reason string). Find real bugs: a check that can pass when it should fail, wrong frame/time arithmetic, a repair that accepts a reply the model did not give, a gate that ignores a segment. Only state what you can verify from the diff. (this chunk: pipeline/verify_pack.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0134
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/verify_pack.py:124** The `ok` returned by `VC.ask_panel` is discarded and recomputed solely from rows present in `per`. If `ask_panel` returns `ok=False` because a required vision model is absent from `per` (e.g., it timed out or errored before producing rows), the recomputed `all(...)` over the remaining models' rows can yield `True`, letting the panel check pass despite a missing answer. The original code trusted `ask_panel`'s `ok` which presumably accounted for model-level failures.
  - evidence: `ok = all(r["ok"] for d in per.values() for k, r in d["rows"].items() if k != NEXT_SHOT)`
  - fix: Preserve the model-level failure signal: e.g. `ok = ok and all(r["ok"] for d in per.values() for k, r in d["rows"].items() if k != NEXT_SHOT)` so that if `ask_panel` already flagged a missing/errored model, the result stays `False`.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
