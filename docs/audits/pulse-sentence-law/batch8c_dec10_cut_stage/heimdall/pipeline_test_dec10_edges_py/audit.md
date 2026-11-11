# Heimdall audit

**Question:** DEC-10 d (orchestrator 2026-11-11: 'Where the inter-sentence gap is short, cut at the envelope minimum with a 2-frame audio fade rather than rejecting the clip. A clip is rejected for edges only if (i) 85 % edge-word duration, (ii) no audible part of the neighbouring word, or (iii) sentence-complete locked words cannot be met.') The Nov 10 recut HELD in run_fresh.stage_cut because cut_accept's M19-era timing checks (cut_out needs a genuine pause with >= 60 ms ahead; cut_in needs a boundary dip in the prior 100 ms) rejected the two edges the sentence-law cutter placed at the envelope minimum (flagged valley_in / valley_out in cuts_final.json). Change: for an edge flagged valley, stage_cut keeps the M19 reading in CUT_ACCEPTANCE.json but leaves the verdict to the very next stage, G16 (stage_sentence_law: legal range + neighbour_clear with the cut's own fades; a failure HOLDs before anything renders). Every other edge and every human-pinned table are unchanged. Find real defects only: can a valley edge now pass without the c-ii check, can a non-valley edge skip cut_accept, can the flag be set by anything other than the cutter, does any stage between stage_cut and G16 consume the cut? (this chunk: pipeline/test_dec10_edges.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0102
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [high] Test only asserts a string label for G16, never invokes G16 or asserts neighbour_clear is called, so a valley edge could pass without the c-ii check and this test would still pass. (agree: 1)
- deepseek:F2 [high] Test mocks cut_accept.check_cut_acoustics but never asserts it was called, so a non-valley edge could skip cut_accept and the test would still pass. (agree: 0)
- deepseek:F3 [medium] Test injects valley flags directly into the cut dict, so it does not verify that only the cutter can set valley_in/valley_out. (agree: 0)
- deepseek:F4 [medium] Test only calls stage_cut, so it cannot detect if an intermediate stage between stage_cut and G16 consumes the cut. (agree: 0)

## Added in cross-examination (not voted on)
- qwen27b: [medium] No test exercises the valley_out flag. All three test methods only set valley_in (or no flag). If the production code handles valley_in and valley_out through separate code paths (e.g., different M19 sub-checks: '>= 60 ms ahead' for out vs 'dip in prior 100 ms' for in), a bug in the valley_out deferral logic would go undetected.
