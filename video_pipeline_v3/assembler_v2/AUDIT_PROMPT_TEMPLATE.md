# Protocol Pulse V2 - Production Readiness Audit Prompt
# Load into every LLM audit. No artificial limits.

AUDIT INSTRUCTIONS:
Find EVERY real issue. Do NOT artificially limit or pad findings.
- If solid in an area: say so explicitly.
- 10 problems: list all 10. 1 problem: list 1. 0 problems: say 0.
- Focus on what unit tests miss: integration, concurrency, resource leaks, silent failures
- FFmpeg filtergraphs: stream indexes, label collisions, eof_action, codec conflicts
- Anything causing 3am outages on an unattended server

SEVERITY:
[CRITICAL] -- causes failures or data corruption in production
[MAJOR]    -- causes quality issues or intermittent failures
[MINOR]    -- suboptimal, production intact
[NITPICK]  -- style/readability only

FORMAT each finding:
[SEVERITY] filename:line -- Issue -- Production impact -- Fix

AFTER ALL FINDINGS:
- Overall score /10
- What is working well
- Minimum changes before safe unattended operation

DO NOT:
- Produce exactly 3 findings to seem balanced
- Pad findings to seem thorough
- Mark things CRITICAL just to seem rigorous
- Skip findings because they seem minor
