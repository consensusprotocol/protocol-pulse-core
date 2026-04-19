# Consensus Synthesis

Authority: CROSS_LLM_AUDIT_LAW.md Phase 3
Implementation: utils/cross_llm_audit.py synthesize_consensus()

## What Counts as Consensus

Consensus requires ALL THREE conditions met simultaneously:

1. **Same file** -- both Qwen and at least 1 external LLM identify the same file
2. **Same function** -- both identify the same function or code block
3. **Same root cause** -- both describe the same underlying problem

Minimum: Qwen + 1 external LLM agreeing on all three.

## What Does NOT Count as Consensus

- "This area could be improved" -- too vague, rejected
- Same file but different functions -- NOT consensus
- Same function but different root causes -- NOT consensus
- Similar-sounding descriptions that differ on specifics -- NOT consensus
- A single model's finding, no matter how confident -- NOT consensus (unless Qwen >= 0.85)

## Consensus Report Sections

Claude produces a structured report with:

| Section | Content |
|---------|---------|
| UNANIMOUS | All 3 models agree -- implement unconditionally |
| MAJORITY | 2 of 3 agree -- implement unless compelling reason not to |
| UNIQUE INSIGHTS | Only 1 model found this -- evaluate case by case |
| CONFLICTS | Models disagree -- Claude provides tiebreaker |
| VALIDATED | All agree this is excellent -- do NOT change |
| LAW COMPLIANCE | Per-law compliance status |
| SECURITY | Security issues with priority order |
| WORLD-CLASS GAP | Missing elements 2+ models identified |
| FINAL ACTION PLAN | P0/P1/P2 sorted by consensus priority |

## Scoring Consensus

Each model provides 0-100 scores across subsystems.
The consensus table shows:

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|-----------|--------|--------|------|-----------|

Consensus score = weighted average with model reliability factored in.
Large spread (>15 points between models) triggers investigation.

## Vague Agreement Rejection Protocol

When reviewing model outputs for consensus:
1. Extract the specific claim from each model
2. Compare at the file:function:cause level
3. If any of the three specifics differ, it is NOT consensus
4. Log the near-miss for reference but do not act on it
5. Only unanimous or majority findings with matching specifics proceed

## Accelerated Path

For lower-stakes features (b1-newsletter, f5-node-watch):
- Single LLM audit (Gemini only) instead of 3
- Skip Cycle 2 second pass if all scores > 85/100
- Still store the audit doc in docs/audits/

For high-stakes features (f1-avatar, v30-terminal, video pipeline):
- Full 3-model audit, mandatory
- Cycle 2 always runs
- No shortcuts

## The Golden Rule

A feature is NOT "done" when Claude Code finishes.
A feature is done when 2+ external models have reviewed the code
AND the consensus improvements have been implemented.
