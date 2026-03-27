Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter5.md

# PIPELINE FIX NEEDED - ITERATION 5 - GRADE C (72/100)
VERDICT: A highly automated but technically flawed production that is not broadcast-ready due to a critical audio peak failure and severe underlying video artifact issues.
CRITICAL FAILURES: - true_peak_check
- no_artifacts
FAILING DIMS (<7/10): - true_peak_check: 0/10 - CRITICAL FAILURE: Final QC reported a true peak of -1.4 dBTP, failing the check 
- host_authenticity: 2/10 - The use of a 'Wav2Lip' AI avatar is a significant drawback. It creates a sense o
- no_artifacts: 2/10 - CRITICAL FAILURE: The render process is fundamentally flawed, generating severe 
- freeze_check: 5/10 - The preflight process detected and fixed a high number of freeze frames (19, the
- episode_title: 5/10 - The title 'pulse_check_20260325' is a functional filename, not a compelling, cli
- visual_polish: 6/10 - While transitions and branded elements are good, the use of an AI avatar and the
FIX INSTRUCTIONS: 1. **True Peak:** In the audio mastering stage, adjust the FFmpeg `loudnorm` filter's limiter to enforce a true peak ceiling of -1.5 dBTP. The current configuration allowed a peak of -1.4 dBTP. 
2. **Artifacts:** The root cause of the freeze frames must be identified. The `PREFLIGHT FIX` is a temporary patch. Investigate the source clips and the `[assemble]` concatenation process for codec, timestamp, or container mismatches that are causing the initial render to fail.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter5 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.