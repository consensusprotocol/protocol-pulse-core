# Heimdall audit

**Question:** DEC-10 d follow-up to the audited DEC-10 batch. (1) boundary() now searches the quiet run between the two words' MIDPOINTS instead of their full extents. (2) accepted_cut(): an edge is cut exactly at its envelope-minimum point with an 83 ms (2 video frames at 24 fps) audio fade when cut_accept has no candidate on that edge OR the edge's quiet run is shorter than SHORT_IN_S 80 ms (in) / SHORT_OUT_S 140 ms (out) - the old pre-DEC-10 legality minimums, which now choose only the cutting METHOD, never legality; neighbour_clear (no audible part of a neighbouring word after the fade) still decides acceptance, and the clip is rejected if it fails. (3) batch-8 Heimdall F2: cut_accept's unchanged pair checks now also run when only ONE edge is cut at a minimum, and the other (normal) edge must pass them. (4) Tests: an abutting-word fixture asserts the short-gap path; mocked tests assert F2. Find real defects only: can any change accept a cut that keeps an audible part of a neighbouring word, cut into a kept word, place the cut outside the edge's legal range [cut_lo, cut_hi], mishandle file head / file end / point None, or loosen any existing check? (this chunk: pipeline/sentence_law.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0097
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
