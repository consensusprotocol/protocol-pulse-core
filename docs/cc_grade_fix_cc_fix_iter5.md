Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter5.md

# PIPELINE FIX NEEDED - ITERATION 5 - GRADE B (82/100)
VERDICT: This episode is structurally sound but fails its final quality control check due to incorrect audio loudness and is marred by significant A/V sync issues in its source material that required heavy automated correction.
CRITICAL FAILURES: - Loudness: Final QC failed with -16.2 LUFS, outside the target of -14 LUFS.
FAILING DIMS (<7/10): - no_artifacts: 3/10 - Significant audio/video sync drift (up to 0.317s) was detected and corrected acr
- loudness_check: 5/10 - Final loudness of -16.2 LUFS missed the target range (-16 to -14 LUFS) and cause
- audio_quality: 5/10 - The combination of loudness failure, initial true peak failure, and severe A/V s
FIX INSTRUCTIONS: 1. **Loudness:** Re-run the final loudness normalization pass. Target an integrated loudness of -14 LUFS with a tolerance of +/- 1 LU, and a true peak of -1.5 dBTP. The current -16.2 LUFS is too quiet and fails QC.
2. **AV Sync:** Investigate the source of the A/V drift in the `pulse_check_20260329.mp4.norm*` parts. The drift is consistently around 300ms. Check the recording or initial ingest process for variable framerate issues or sample rate mismatches.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter5 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.