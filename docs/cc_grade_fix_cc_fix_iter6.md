Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter6.md

# PIPELINE FIX NEEDED - ITERATION 6 - GRADE C (75/100)
VERDICT: The episode fails broadcast-readiness due to critical loudness and A/V sync issues, despite a sophisticated assembly and repair process.
CRITICAL FAILURES: - Loudness is -16.2 LUFS, failing the -14 LUFS broadcast target.
- Multiple source clips had severe A/V sync drift (up to 0.317s), indicating a fundamental production issue that required heavy correction.
FAILING DIMS (<7/10): - loudness_check: 2/10 - CRITICAL: Final loudness is -16.2 LUFS, failing the -14 LUFS target. The episode
- no_artifacts: 3/10 - The severe A/V sync drift required significant correction. While fixed, this is 
- audio_quality: 3/10 - The failure to meet the target loudness standard is a major audio quality defect
- file_integrity_check: 5/10 - Multiple significant A/V sync drifts (up to 0.317s) were detected and corrected.
FIX INSTRUCTIONS: To fix this render for broadcast: 1. Re-run the final audio mastering stage to target -14 LUFS integrated loudness. In the pipeline's audio module, adjust the `loudnorm` filter's `I` parameter from -16 to -14. 2. Investigate the source of A/V sync drift in the ingest process for clips `part_026` through `part_029` and `part_032` to prevent recurrence.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter6 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.