# Heimdall audit

**Question:** Protocol Pulse sentence law for cutting video clips at sentence edges (DEC-10). Change: the timing minimums (pause, lead, tail, guard) are calibrated to the approved reference's measured worst (0 ms: one approved edge has abutting words); a boundary's legal cut range is now the HEARD gap (the previous word's last offset to the next word's first onset at speech - 6 dB) and the neighbour side ends at the envelope minimum between the two words; abutting words get a zero-length pause at that minimum; a short gap is cut at the minimum with a 2-frame audio fade instead of being rejected; a new check neighbour_clear fails any cut that keeps frames of the neighbouring word above the valley threshold (speech - 12 dB) after the fade; a separate file-head rule (80 ms or a room-tone pad) is unchanged; prerender passes per-cut fade lengths (the frozen reference declares 20/30 ms, identical to the old defaults). Find real bugs: a cut that can now include part of another word or sentence and pass, a clipped first/last word that passes, ranges that are empty or inverted, the frozen reference's output changing, must-fail cases that now pass. Only state what you can verify from the diff. (this chunk: pipeline/test_pulse_20261110_mustfail.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0035
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
