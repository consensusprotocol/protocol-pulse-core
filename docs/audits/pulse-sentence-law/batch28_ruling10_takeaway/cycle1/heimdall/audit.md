# Heimdall audit

**Question:** Batch 28 = RULING 10 (orchestrator 2026-11-12 '08:40'): in EDL rule R4 for packages of type 'moments' ONLY, the VO line after the LAST clip (the TAKEAWAY, a slot that did not exist when BRIDGE_WORD_CAP = 20 was set for lines between clips) has its own word cap MOMENTS_TAKEAWAY_WORD_CAP = 30 (the intro's cap); bridges BETWEEN clips keep 20. The change: the constant, and the cap chosen per line: the takeaway cap only when after_clip is an int equal to the last clip index, else BRIDGE_WORD_CAP. Must-fail tests: 31 takeaway words rejected, exactly 30 pass, a 21-word bridge between clips rejected, the night's 24-word takeaway passes; mutations (cap 31; takeaway cap for every bridge) each fail a test. Story-type pins unchanged.
FIND: any line other than the moments takeaway that now gets the 30-word cap; any boundary error; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0071
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
