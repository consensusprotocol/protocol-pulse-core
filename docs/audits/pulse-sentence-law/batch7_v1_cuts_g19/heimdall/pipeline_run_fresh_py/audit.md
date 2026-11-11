# Heimdall audit

**Question:** Protocol Pulse news-video pipeline verification (no publishing). Changes on top of an audited batch: (1) the visual checklist's credits question now gets the channel list from the edit decision list (a 9:16 crop can hide a show's branding); (2) the 'next shot visible before a cut' line is answered one cut at a time: the frame 3 frames before and 3 frames after each cut, side by side, asked of two vision models; any 'yes', missing answer or error fails; the whole-sheet answer for that line is kept only as advisory; (3) a vision reply missing up to 3 final closing braces is closed before parsing (nothing else repaired); (4) a new deterministic gate G19: on each finished video, no hard shot change (ffmpeg scene score >= 0.3) inside a talking-head segment's clean span before its first word or after its last word, with speech times from the prepare stage's record, failing closed without a record; (5) batch-6 audit fixes (stand-alone subject terms, replay catch-all, shot-snap test strengthening, a reason string). Find real bugs: a check that can pass when it should fail, wrong frame/time arithmetic, a repair that accepts a reply the model did not give, a gate that ignores a segment. Only state what you can verify from the diff. (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0086
## Consensus findings (majority of panel agrees)
- **[high] pipeline/run_fresh.py:961** G19 result is written to rows but never incorporated into ok16/ok9, so run_gates_overall ignores G19 failures. A video can fail G19 and still be reported as overall PASS.
  - evidence: `rows[fmt]["G19_edge_shots"] = _status(ok)
...
"run_gates_overall": {"16x9": ok16, "9x16": ok9}}`
  - fix: Update ok16/ok9 after G19 (e.g., ok16 = ok16 and g19['16x9']['ok'], ok9 = ok9 and g19['9x16']['ok']) or compute run_gates_overall from rows after all gates have been added.
  - raised by deepseek:F1; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F2 [medium] G19 is fed shot_snap from CLIP_CONTRACT.json, not the prepare stage's speech-time record. If shot_snap lacks speech times, the gate cannot enforce the clean-span rule and may ignore segments or fail incorrectly. (agree: 0)
- qwen27b:F1 [low] The snap_rec construction uses `r.get("shot_snap") or {}`, which maps a null/missing shot_snap to an empty dict. The spec requires the gate to fail closed 'without a record.' If edge_shots.gate_g19 distinguishes between a key being absent from snap_rec (true 'no record') and a key being present with an empty dict (record exists but empty), a clip whose shot_snap is explicitly null in CLIP_CONTRACT.json will have an entry in snap_rec and may not trigger the fail-closed path. This is unverifiable without the gate_g19 source, but the `or {}` collapses two semantically different states (missing field vs. null value) into one. (agree: 1)

## Added in cross-examination (not voted on)
- none
