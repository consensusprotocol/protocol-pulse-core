Read ~/protocol_pulse/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/video_pipeline_v3/daily_producer.py — specifically the assembly and post-render sections.
Read ~/protocol_pulse/video_pipeline_v3/assembler.py — specifically the final encode section.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: PRE-FLIGHT QC LOOP — GRADE A GUARANTEE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

THE PROBLEM:
Right now the pipeline renders → sends to Gemini → gets F → starts over
from scratch. This wastes 45-90 minutes per failed render. The grader
consistently fails on 3 things:
  1. Freeze frames (>1 = instant critical failure, score 0/10)
  2. Silence gaps (>1 gap >0.8s = critical failure)
  3. Audio loudness (wrong LUFS = fail)

All 3 are detectable by ffprobe/ffmpeg BEFORE Gemini sees the video.
The fix: run a pre-flight QC check after assembly, fix the specific
issues, then send to Gemini. Gemini never sees a broken video.

THE ARCHITECTURE:
After assembler.py produces the final video, before gemini_grade.py runs:

  assemble → PRE_FLIGHT_QC → [fix if needed] → gemini_grade

PRE_FLIGHT_QC is a blocking gate. If it fails, fix and retry assembly
of only the broken segments. Max 3 pre-flight attempts before escalating.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY: CROSS-LLM AUDIT FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Register in utils/cross_llm_audit.py:
  FEATURE_MAP["preflight-qc"] = ("PIPELINE_LAWS.md", "main")
  EXPLICIT_FILES["preflight-qc"] = [
      "video_pipeline_v3/daily_producer.py",
      "video_pipeline_v3/assembler.py",
      "video_pipeline_v3/gemini_grade.py",
  ]

python3 utils/cross_llm_audit.py --feature preflight-qc
[save C1]
python3 utils/cross_llm_audit.py --feature preflight-qc --cycle 2 --cycle1-results [C1]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENT: run_preflight_qc(video_path) in daily_producer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_preflight_qc(video_path: str) -> dict:
    """
    Run pre-flight QC checks on assembled video before Gemini grading.
    Returns {passed: bool, issues: list, metrics: dict}
    
    Checks (all via ffprobe/ffmpeg, no LLM needed):
    1. FREEZE FRAMES — ffmpeg freezedetect n=0.003:d=1.5
       Threshold: 0 freeze frames allowed (grader fails at >1)
    2. SILENCE GAPS — ffmpeg silencedetect n=-50dB:d=0.8
       Threshold: 0 gaps >0.8s in middle 80% of video
    3. LOUDNESS — ffmpeg ebur128
       Threshold: integrated LUFS between -17 and -12
       True peak: <= -1.0 dBTP
    4. DURATION — ffprobe
       Threshold: between 7 and 15 minutes
    5. RESOLUTION — ffprobe
       Threshold: exactly 1920x1080
    """

If preflight FAILS, for each issue type apply a targeted fix:

FREEZE FRAME FIX:
  Run ffprobe to get timestamp of each freeze frame.
  For each freeze location, extract 10s surrounding segment.
  Re-render that segment with explicit -r 30 -vsync cfr flags.
  Splice back into final video using concat demuxer.
  Maximum 3 freeze frame fix attempts.

SILENCE GAP FIX:
  Run silencedetect to get exact timestamps of gaps.
  For each gap >0.8s, extract surrounding audio segment.
  Apply atrim + apad to fill gap with minimal fade.
  Re-mux audio track into video without re-encoding video stream.
  (audio fix is fast — no video re-encode needed)

LOUDNESS FIX:
  If LUFS outside target range, apply loudnorm filter to final output.
  ffmpeg -i input.mp4 -af loudnorm=I=-14:TP=-2.0:LRA=7:linear=true output.mp4
  Single pass — fast, no re-encode of video stream needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WIRE INTO PIPELINE (daily_producer.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
After Step 12 (assembly complete), BEFORE gemini_grade:

MAX_PREFLIGHT_ATTEMPTS = 3
for attempt in range(1, MAX_PREFLIGHT_ATTEMPTS + 1):
    logger.info(f"[PREFLIGHT] Attempt {attempt}/{MAX_PREFLIGHT_ATTEMPTS}")
    qc = run_preflight_qc(final_video)
    
    if qc["passed"]:
        logger.info("[PREFLIGHT] PASSED — sending to Gemini")
        break
    
    logger.warning(f"[PREFLIGHT] FAILED: {qc['issues']}")
    write_render_context("preflight", "fail", error=str(qc["issues"]))
    
    if attempt == MAX_PREFLIGHT_ATTEMPTS:
        logger.error("[PREFLIGHT] Max attempts reached — sending anyway")
        send_telegram(f"⚠️ PREFLIGHT: {qc['issues']} — sending to Gemini anyway")
        break
    
    # Apply targeted fixes
    _apply_preflight_fixes(final_video, qc)

# NOW call gemini_grade — video is clean
grade_result = grade_with_gemini(final_video)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LOGGING AND BIBLE UPDATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Log every preflight check result to:
  video_pipeline_v3/logs/preflight_YYYYMMDD.log

Format:
  [PREFLIGHT] freeze_frames=0 silence_gaps=0 lufs=-14.2 duration=8m32s
  [PREFLIGHT] PASS — proceeding to Gemini

After implementing, append to QWEN_CONTEXT_BIBLE.md:
  PATTERN: Pre-flight QC loop
  PURPOSE: Ensures Gemini never sees a video with freeze frames/silence/loudness issues
  LOCATION: daily_producer.py run_preflight_qc() called after Step 12 before grading
  THRESHOLDS: 0 freeze frames, 0 silence gaps >0.8s, -17 to -12 LUFS, 7-15 min duration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRESSION + COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bash ~/protocol_pulse/regression_test.sh — 0 FAILs required
git add video_pipeline_v3/daily_producer.py
git commit -m "feat(pipeline): pre-flight QC loop — freeze/silence/loudness auto-fix before Gemini grading — Grade A guarantee"
git push

IMPORTANT: Do not ask for confirmation before committing.
Run git add, commit, and push automatically.
