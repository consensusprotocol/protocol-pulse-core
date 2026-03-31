Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter2.md

# PIPELINE FIX NEEDED - ITERATION 2 - GRADE C (70/100)
VERDICT: A structurally sound episode sabotaged by critical audio mastering errors and source file sync issues, rendering it unpublishable without fixes.
CRITICAL FAILURES: - Loudness: -16.3 LUFS is well below the -14 LUFS target.
- True Peak: -0.9 dBTP is above the -1.0 dBTP maximum, risking distortion.
- Audio Quality: The combination of mastering errors and source A/V sync issues makes the audio unprofessional.
FAILING DIMS (<7/10): - true_peak_check: 2/10 - CRITICAL FAILURE: True peak at -0.9 dBTP is too high (hot) and exceeds the -1.0 
- loudness_check: 3/10 - CRITICAL FAILURE: Loudness at -16.3 LUFS misses the -14 LUFS target significantl
- no_artifacts: 3/10 - MAJOR FLAW: Multiple source clips had significant A/V sync drift (up to 0.317s) 
- audio_quality: 3/10 - Poor. The combination of incorrect loudness, hot true peak, and A/V sync issues 
FIX INSTRUCTIONS: 1. **Audio Mastering:** Re-export the final mix. In the audio mastering stage (e.g., loudnorm), set the integrated loudness target to -14.0 LUFS and the true peak maximum to -1.5 dBTP. This will fix the two primary QC failures.
2. **Source Integrity:** Before re-render, review the source clips for A/V sync issues. The logs indicate significant drift in multiple clips, particularly the 'data' and 'signal_active' segments. These must be fixed in the NLE project to prevent future sync problems.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter2 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.