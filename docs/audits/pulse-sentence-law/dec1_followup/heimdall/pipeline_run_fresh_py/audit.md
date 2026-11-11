# Heimdall audit

**Question:** DEC-1 follow-up to late Heimdall findings. (1) The G9 row is split: G9_tail is now the calibrated gate result alone; a new row outro_locked is FAIL on an outro conform fallback. Before, the same condition was hidden inside G9 as (identical or not fallback), and identical already contained 'and not fallback', so the term was 'not fallback'. Verify there is no acceptance change: the run must still HOLD on a conform fallback and on a luma failure (verdict_for holds on any FAIL row), and nothing else changed. (2) Tests: TestTailRows; the G9 must-fail assertion checks the boolean strictly and the measured luma against the floor constant; sys.path gains the pipeline dir (no module name is shared with segment_v1). Find any way this loosens acceptance or any test that passes vacuously. Only state what you can verify from the diff; if uncertain, say so. (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0046
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
