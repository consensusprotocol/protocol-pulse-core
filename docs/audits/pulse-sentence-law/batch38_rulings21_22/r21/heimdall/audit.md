# Heimdall audit

**Question:** Batch 38a = RULING 21 (orchestrator 2026-11-12 '13:06'): gate G3c (acoustic head / tail of each talking-head clip: the clip's last 120 ms must show no new onset and a valley below speech median - 11.6 dB; its first 120 ms no onset) was measured on the FINAL video, where the music bed and loudness normalisation sit under the pause and move with the VO timeline. Now, when run_fresh passes prepared_clips (label -> the prepared clip, the speech stem), gate_g3c measures each clip on its prepared clip from its start; a label without a prepared clip fails closed; every other caller (CLI, run_isolated, run.py, the calibration tests) passes nothing and still measures the final. Thresholds unchanged. Tests: the Nov 12 clip_02 tail passes on its prepared clip (it failed on the final under the bed); a prepared clip whose tail runs into the next word fails.
FIND: any way a clipped tail or head now passes; a caller whose source_clips are raw sources reaching G3c; a fail-open when the prepared clip is missing. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0091
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
