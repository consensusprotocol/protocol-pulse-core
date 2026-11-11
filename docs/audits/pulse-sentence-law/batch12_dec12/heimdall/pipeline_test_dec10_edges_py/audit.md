# Heimdall audit

**Question:** DEC-12 (orchestrator 2026-11-11 14:45, decided): the parked gate items as ONE batch; every gate keeps its purpose and its must-fail tests; what changes is an instrument error or the render. (a) G9 floor per format = v2f's measured tail luma minus the MEASURED re-encode spread of the same locked outro through the final-encode path (5 GOP phases, 5 real credits cards before it, the real finals; tagged bt709 like the finals): 0.0438 / 0.0335 rounded up to 0.01, at most 0.05 -> floors 14.2857 / 14.7315; outro_locked stays the hard row; tests: v2f + another encode pass, a tail 1 luma code darker and a black tail fail, a conform fallback fails outro_locked. (b) every MACHINE-cut edge gets the 2-frame (83 ms) fade in accepted_cut; human PIN tables keep 20/30 (Law 22). (d) has_chyron channels (registry) never supply a clip in auto selection (layout_eligible); coverage evidence unchanged. (e) G14 samples only where the source transcript has a word in the 0.5 s window and outside declared transition overlaps / VO segments of the timeline map; an inconclusive sample is re-taken once at the nearest word onset; a segment passes with >= 3 conclusive matching samples and zero conclusive mismatches, else FAIL (any mismatch) / HOLD; xcorr bar and tolerance unchanged; 9:16 runs audio-only (frames=False) under the same rule; tests: the corrected Nov 10 cut passes (its pause sample re-taken), a mid-segment 2-frame AV slip FAILS, a silenced segment HOLDS. (f) G3b reads each tail 3 times (window starts jittered by 0/1/2 frames) with 1.5 s of leading context; the expected last word must be among the last two words heard in a majority; the next word must not follow it in a majority; tests: the corrected cut passes, yesterday's Natalie tail fails against its locked last word, a tail cut 250 ms into its last word fails. Find real defects only: anything that loosens a must-fail, a fail-open path, wrong time mapping in G14, a G9 floor not derived from the measurement, Law 22 risk. (this chunk: pipeline/test_dec10_edges.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0035
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_dec10_edges.py:200** The test now expects a human PIN out edge (out_pass=True) to have an 83 ms fade, but DEC-12b/Law 22 requires human PIN tables keep 20/30 ms. This loosens the must-fail for human PIN fade and risks violating Law 22.
  - evidence: `c = self._accepted(in_pass=False, out_pass=True)
self.assertEqual((c["fade_in_ms"], c["fade_out_ms"]), (83, 83))   # DEC-12b: every machine edge`
  - fix: Revert the expected fade_out_ms to 30 for this human PIN edge, or split the assertion so machine edges get 83 ms and human PIN edges keep 30 ms.
  - raised by deepseek:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
