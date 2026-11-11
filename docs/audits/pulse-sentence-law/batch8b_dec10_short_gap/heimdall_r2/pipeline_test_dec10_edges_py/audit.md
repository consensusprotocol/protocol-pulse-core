# Heimdall audit

**Question:** Tests for DEC-10 d: TestValleyCut (abutting sin^2-enveloped words; the edge must be cut within one 10 ms hop of the junction with the 83 ms fade, unconditionally) and TestMixedEdgeAcoustics (mocked: a normal edge failing cut_accept rejects the clip; an edge at the minimum is judged by neighbour_clear, not cut_accept). Are any assertions vacuous, or would the tests pass on the pre-change code? Report only real defects you can quote.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0153
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [high] Test is vacuous: it passes on pre-change code because the mocked check_cut_acoustics returns False for both edges, so the clip is rejected regardless of whether the valley edge is correctly exempted from cut_accept. (agree: 1)
- deepseek:F2 [critical] Test is broken: it expects accepted_cut to return a non-None result, but the mocked check_cut_acoustics returns (False, det) for in_pass=False, out_pass=True. If accepted_cut uses the first return value as the pass/fail for the normal edge, it will reject the clip, so assertIsNotNone fails. (agree: 0)

## Added in cross-examination (not voted on)
- none
