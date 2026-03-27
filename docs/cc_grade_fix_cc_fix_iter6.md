Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter6.md

# PIPELINE FIX NEEDED - ITERATION 6 - GRADE F (31/100)
VERDICT: The episode is unpublishable due to a cascade of critical technical failures, from a fatal script error and severe A/V defects to an extreme runtime overrun.
CRITICAL FAILURES: - duration=63.0min (target 7-15)
- loudness=-70.0 LUFS (target -16 to -14)
- true_peak=0.4dBTP (max -1.0)
- freeze_frames=214 (max 0)
- no_artifacts (due to freezes)
- audio_quality (due to loudness/peak/sync issues)
- pacing (due to extreme duration)
- file_integrity (render script crashed with UnboundLocalError)
FAILING DIMS (<7/10): - duration_check: 0/10 - Critical failure. Episode is 63.0 minutes, massively exceeding the 7-15 minute t
- loudness_check: 0/10 - Critical failure. -70.0 LUFS is unlistenably quiet and completely misses the -16
- true_peak_check: 0/10 - Critical failure. Preflight log shows a true peak of 0.4dBTP, which exceeds the 
- freeze_check: 0/10 - Critical failure. 214 freeze frames make the video unwatchable. The automated pr
- file_integrity_check: 0/10 - Critical failure. The render pipeline crashed with an 'UnboundLocalError' traceb
- no_filler: 0/10 - Critical failure. The episode is 4-9x its target length, which strongly implies 
- no_artifacts: 0/10 - Critical failure. The 214 freeze frames are extreme visual artifacts that make t
- audio_quality: 0/10 - Critical failure. Unusable loudness, clipping peaks, and evidence of significant
FIX INSTRUCTIONS: 1. **PIPELINE SCRIPT:** Fix the fatal `UnboundLocalError` in `daily_producer.py` at or before line 1305. The `clips` variable is used before it is guaranteed to be assigned. Initialize `clips = []` at the beginning of the `run_pipeline` function scope.
2. **CONTENT EDITING:** This is a pre-pipeline issue. The source material must be edited down to the 7-15 minute target runtime *before* being processed. The current 63-minute input is the root cause of the duration, pacing, and freeze-fix timeout failures.
3. **AUDIO PIPELINE:** Investigate the entire audio chain. The `Loudnorm` and peak limiting steps are failing. Verify ffmpeg filter complex for audio processing. The source clips have severe A/V sync issues that must be addressed at the recording stage.
4. **VIDEO ASSEMBLY:** The root cause of the 214 freeze frames and 13 black frames must be found. Inspect the `[assemble]` process and the source `part_*.mp4` files for corruption or encoding errors.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter6 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.