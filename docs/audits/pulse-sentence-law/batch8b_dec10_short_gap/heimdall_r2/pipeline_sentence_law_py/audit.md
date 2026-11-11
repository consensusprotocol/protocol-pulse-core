# Heimdall audit

**Question:** DEC-10 d follow-up in accepted_cut(): an edge whose quiet run is shorter than 80 ms (in) / 140 ms (out), or that cut_accept cannot clear, is cut at its envelope-minimum point with an 83 ms fade; neighbour_clear (no frame of the neighbouring word above speech - 12 dB after the fade) decides acceptance; cut_accept's unchanged checks run on every edge NOT cut at a minimum (also when the other edge is); default fades named; the quiet run is searched between the two words' midpoints. By construction the point lies inside the edge's heard gap [cut_lo, cut_hi]. Report only real defects you can quote.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0092
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
