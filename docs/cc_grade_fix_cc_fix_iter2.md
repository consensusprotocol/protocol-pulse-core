Read ~/protocol_pulse/PIPELINE_LAWS.md first. Then read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md. GRADE FIX SPEC FROM: cc_fix_iter2.md

# PIPELINE FIX NEEDED - ITERATION 2 - GRADE C (75/100)
VERDICT: A deeply flawed production saved by a robust automated repair system, but critical failures in avatar generation and video integrity make it unfit for broadcast.
CRITICAL FAILURES: - Avatar/TTS Generation Failure: The core host presentation system is completely non-functional, timing out on all attempts for shorts and the stage brief.
- Severe Freeze Frames: The initial render contained over 20 freeze frames, requiring multiple corrective passes and indicating a fundamental instability in the video generation.
- File Size Verification Failure: The final output file (678.6MB) did not meet the expected size constraints.
FAILING DIMS (<7/10): - host_authenticity: 1/10 - Critical failure. The avatar/TTS generation system failed repeatedly for all sho
- visual_polish: 3/10 - Severely impacted by the complete failure of the avatar generation system, resul
- freeze_check: 4/10 - A severe number of freeze frames (20, then 5) were detected and required two aut
- episode_title: 4/10 - The title is a functional filename 'pulse_check_20260324.mp4', not a compelling,
- no_artifacts: 4/10 - The presence of severe freeze frames requiring multiple fixes indicates signific
- file_integrity_check: 5/10 - The final file size of 678.6MB failed the verification check, indicating a poten
- audio_quality: 6/10 - The final audio passed QC, but the initial render had catastrophic loudness and 
FIX INSTRUCTIONS: 1. **Avatar/TTS Service:** Debug the HTTP connection to `localhost:8200`. The service is consistently timing out after 120-300s. Check service logs for errors, resource utilization (CPU/RAM), and network configuration. File: `generate_stage_brief.py` and shorts generation module.
2. **Freeze Frames:** Isolate the source of the 20+ freeze frames. Review the source clips and the concatenation logic in the assembly stage. The `temporal noise` fix in `PREFLIGHT FIX` is a patch; the root cause must be found.
3. **File Size:** The final assembly stage produced a 678.6MB file that failed verification. Review the H.264 encoding parameters (bitrate/CRF) to ensure they align with the target file size for a ~12 minute video.


Apply ONLY the fixes listed above. Run bash ~/protocol_pulse/regression_test.sh — must show 0 FAILs. Commit: git add -A && git commit -m "fix(pipeline-auto): cc_fix_iter2 grade improvements" && git push. Echo GRADE_FIX_COMPLETE when done.