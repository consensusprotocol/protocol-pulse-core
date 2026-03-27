Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter4.md

# PIPELINE FIX NEEDED - ITERATION 4 - GRADE C (72/100)
VERDICT: A technically sophisticated production pipeline undermined by critical, un-fixed errors in audio peak and video freeze frames, rendering the episode unfit for broadcast.
CRITICAL FAILURES: - True peak exceeds maximum (-1.3 dBTP > -1.5 dBTP)
- Render contains freeze frames (preflight check failed twice)
- Render contains audible silence gaps (preflight check failed three times)
FAILING DIMS (<7/10): - true_peak_check: 2/10 - CRITICAL FAILURE: True peak at -1.3 dBTP exceeds the -1.5 dBTP maximum, risking 
- no_artifacts: 2/10 - FAIL: The episode contains significant video (freeze frames) and potential audio
- freeze_check: 3/10 - FAIL: Preflight checks detected 12, then 6 freeze frames. The automated fix was 
- silence_check: 4/10 - FAIL: The preflight check failed three times due to a silence gap, and the autom
- visual_polish: 4/10 - Significantly degraded by the presence of un-fixed freeze frames, which directly
- audio_quality: 5/10 - Mixed. Loudness normalization and mixing are excellent, but the critical true pe
- host_authenticity: 6/10 - The host is an AI avatar. While render logs show successful generation, the pote
FIX INSTRUCTIONS: 1. **True Peak:** In the `PREFLIGHT FIX` stage, modify the `loudnorm` filter parameters. The target `true_peak` must be set to `-1.5` or lower to correct the final output from -1.3 dBTP.
2. **Freeze Frames:** The 'temporal noise' fix is insufficient. The root cause is likely in the source clips. Identify the clips corresponding to the 12 freeze frames detected in the first preflight attempt and either replace them or trim the static portions before re-running the assembly.
3. **Silence Gaps:** The 'fade bridge' fix is failing. Manually inspect the audio timeline at the part junctions where the preflight check fails. The gap needs to be closed either by extending the audio of one clip or by applying a more aggressive crossfade in the assembly stage.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter4 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.