Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter1.md

# PIPELINE FIX NEEDED - ITERATION 1 - GRADE C (79/100)
VERDICT: An impressively automated production that is unfortunately not broadcast-ready due to a critical loudness failure and severe underlying AV sync issues.
CRITICAL FAILURES: - Loudness: Final integrated loudness of -16.3 LUFS failed the QC check against the target (-14 LUFS), making the file unsuitable for broadcast.
- AV Sync Integrity: Multiple source clips required significant AV sync correction (up to 0.317s), indicating a systemic issue in the source material or assembly process that compromises quality.
FAILING DIMS (<7/10): - no_artifacts: 3/10 - CRITICAL: The need for heavy AV sync correction indicates that the source materi
- loudness_check: 4/10 - CRITICAL: Final loudness of -16.3 LUFS missed the target range and failed the po
- audio_quality: 4/10 - The combination of a synthetic TTS voice and failing the loudness QC check resul
- file_integrity_check: 5/10 - Major concern. The assembly process required numerous, significant AV sync corre
- host_authenticity: 5/10 - The use of a TTS voice and a Wav2Lip avatar is a significant barrier to authenti
FIX INSTRUCTIONS: 1. **Loudness:** In the audio processing module, adjust the `loudnorm` filter parameters. Change the target integrated loudness (`I`) from its current setting to `-14` LUFS to meet the broadcast standard. Re-run the post-render QC to verify.
2. **AV Sync:** Investigate the source of the AV drift in the `pulse_check_*.mp4.norm*` clips. Add a pre-flight check to reject source clips with an audio-video drift greater than 100ms before they enter the main assembly pipeline. The root cause in the recording or normalization stage must be fixed.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter1 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.