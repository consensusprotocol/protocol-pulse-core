# Heimdall audit

**Question:** Protocol Pulse news-video pipeline, auto mode story selection and verification. Changes: (1) candidates whose COUNTED evidence includes the same statement (same video, shared supporting chunk, >=5 consecutive shared words in the evidence quotes) are merged into one event: one derived query, verdicts pooled one per video, not-counted verdicts re-judged against the merged query within a budget, same coverage decision; (2) a story ledger: an auto run delivered HOLD FOR APPROVAL in both formats records its counted evidence; later runs exclude any candidate resting on the same statement; (3) the 9:16 letterbox check asks two vision models about ONE frame per shot of every talking-head segment; a non-screen shot called letterboxed or unanswered fails. Find real bugs: false merges of different events, a delivered story selected again, a story wrongly excluded, a letterbox that can pass, crashes, state left inconsistent. Only state what you can verify from the diff. (this chunk: pipeline/editorial_select.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0151
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
