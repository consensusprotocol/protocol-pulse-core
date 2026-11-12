# Heimdall audit

**Question:** Batch 31 = RULING 13 (orchestrator 2026-11-12 '10:02') + RULING 11 ('08:55') in gate G14 (audio-visual alignment of each talking-head segment of a rendered video against its source; pipeline/gates.gate_g14). The requirement is unchanged: a segment passes with >= 3 conclusive matching samples (G14_MIN_CONCLUSIVE) and zero conclusive mismatches; fewer than 3 = HOLD; the xcorr bar and the 40 ms tolerance are unchanged. RULING 13: a 0.5 s sample window counts only if >= 60 % of it (G14_MIN_SPEECH) lies inside the LOCKED words' speech = the selection lock's words i0..i1 (word timestamps) minus the cut's measured pauses (cuts_final pause_in / pause_out); run_fresh now passes exactly that (gates.g14_run_speech) instead of every transcript word; a window below 60 % is not a sample; a retake (an inconclusive sample re-taken at the nearest spoken word) must qualify the same way. RULING 11: a segment whose clear region (outside VO segments and dissolve overlaps) is shorter than G14_EVEN_BELOW_S = 6.75 s gets its windows spread evenly over that region at a stride >= G14_MIN_STRIDE_S = 0.75 s inside G14's own margins (0.05 s after the start, window + 0.1 s before the end; g14_even_offsets); a region that cannot hold 3 windows at that stride gets none (HOLD). Longer segments keep the fixed layout. Measured (old vs new, per-segment verdicts): tonight's render clip_02 (4.666 s) FAIL 3/4 -> PASS 4/4 on 4 speech windows; the same with clip_02's audio 200 ms late FAIL 0/4; the Nov 11 preview and the corrected Nov 10 cut and the frozen v2f keep every per-segment verdict.
FIND: any way a segment now passes on fewer than 3 real speech samples or with a conclusive out-of-sync sample; boundary errors in the 60 % coverage (double counting, the pause subtraction) or in the even layout (stride, margins, the clear region at dissolves); any input on which the change crashes or passes when nothing was measured; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0101
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
