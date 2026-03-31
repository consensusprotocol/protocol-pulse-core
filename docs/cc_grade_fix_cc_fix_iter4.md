Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter4.md

# PIPELINE FIX NEEDED - ITERATION 4 - GRADE C (74/100)
VERDICT: A technically sophisticated production pipeline is severely undermined by poor source material quality, resulting in critical audio failures that make the episode unfit for broadcast.
CRITICAL FAILURES: - Loudness: Final QC failed with -16.3 LUFS, below the minimum broadcast standard.
- Source Integrity: Multiple source clips show severe A/V sync drift (>300ms), compromising the final edit.
FAILING DIMS (<7/10): - no_artifacts: 1/10 - CRITICAL: Multiple source clips had severe A/V sync drift (>300ms) requiring aut
- loudness_check: 2/10 - QC FAILED: Integrated loudness is -16.3 LUFS, which is too quiet and outside the
- audio_quality: 2/10 - Poor. Fails loudness QC, required fixes for silence gaps, and source material ha
FIX INSTRUCTIONS: 1. **Loudness:** In the audio normalization stage, adjust the integrated loudness target from -16 LUFS to -14 LUFS to meet broadcast standards. Re-run the final loudness scan to verify.
2. **A/V Sync:** Investigate the source clip ingestion process. The A/V drift on `pulse_check_20260329.mp4.norm26` through `norm32` is consistently ~300ms. This points to a systemic issue in the source recording or pre-processing stage that must be fixed to prevent artifacts.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter4 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.