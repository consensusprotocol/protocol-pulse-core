# Heimdall audit

**Question:** Batch 30 = RULING 14 (orchestrator 2026-11-12 '10:02'): gate G20 (the rendered sign-off must name every credited channel) failed because Whisper wrote 'seifedean amos' for 'Saifedean Ammous' (fuzzy ratio 0.800 against the unchanged G20_NAME_RATIO 0.85). The change: spoken-form aliases in the channel registry entry for Saifedean Ammous ('seifedean amos', 'saifedean amos', 'safedean ammous', 'saifedean ammus'); G20's matcher (gates.spoken_channels) already tries every registry alias at the unchanged 0.85, exact substring first. NO code change and NO ratio change. Must-fail tests: the transcript of tonight's render now names all three credited channels; the same transcript with his aliases removed does not name him (0.800); a sign-off that omits him does not name him; a sign-off naming a different person does not name him; the ratio is still 0.85.
FIND: any way the new aliases make G20 hear him when he is not spoken (a short or generic alias matching other words, or overlapping another credited name); tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0063
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
