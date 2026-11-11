# Heimdall audit

**Question:** Protocol Pulse news-video pipeline, auto mode story selection and verification. Changes: (1) candidates whose COUNTED evidence includes the same statement (same video, shared supporting chunk, >=5 consecutive shared words in the evidence quotes) are merged into one event: one derived query, verdicts pooled one per video, not-counted verdicts re-judged against the merged query within a budget, same coverage decision; (2) a story ledger: an auto run delivered HOLD FOR APPROVAL in both formats records its counted evidence; later runs exclude any candidate resting on the same statement; (3) the 9:16 letterbox check asks two vision models about ONE frame per shot of every talking-head segment; a non-screen shot called letterboxed or unanswered fails. Find real bugs: false merges of different events, a delivered story selected again, a story wrongly excluded, a letterbox that can pass, crashes, state left inconsistent. Only state what you can verify from the diff. (this chunk: pipeline/verify_pack.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0141
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [low] When a vision-route error is already recorded in v['error'], the letterbox failure appended to 'nos' is silently dropped from the diagnostic message because the 'or' short-circuits. The verdict is still correctly FAIL (v['ok'] is False), but the operator sees only the vision-route error and no mention of the letterbox failure, making debugging harder. (agree: 1)
- qwen27b:F2 [low] The letterbox check is gated on '"error" not in pack["contact_sheets"][fmt]'. The inputs to VC.shot_frames (output dir, segs, layout, shots dir) do not include the contact-sheet artefacts, so a non-fatal contact-sheet error (e.g. a missing thumbnail) causes the letterbox check to be skipped entirely. If v['ok'] is not independently forced to False by that contact-sheet error, a letterboxed 9:16 video would receive a PASS verdict. (agree: 1)

## Added in cross-examination (not voted on)
- none
