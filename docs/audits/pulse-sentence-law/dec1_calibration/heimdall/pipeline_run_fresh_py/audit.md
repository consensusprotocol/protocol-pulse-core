# Heimdall audit

**Question:** DEC-1 commit: per-format named constants calibrated to the approved v2f reference's measured worst value for exactly the four gates it failed (G3c valley depth, G5 9:16 true peak, G8 sharpness floor, G9 tail luma), with tests that the reference passes and a fixture just beyond fails; G8 now receives its source clips in production (it never did and always failed no_source); DEC-3: a source already below the floor is judged by the render/source ratio >= 0.85 alone; G8/G9 waiver rows removed. Find: any threshold changed beyond the stated values, any gate other than these four changed, a comparison that lets the reference fail its own value, a test that passes vacuously, a wiring error in source_clips. (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0126
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/run_fresh.py:589** src16 is wired to per-clip final renders (`final_*.mp4`) instead of the source camera clips, so G8 compares the render against itself, yielding a render/source ratio of 1 and passing vacuously. The comment explicitly says 16:9 sources should be the prepared source camera clips.
  - evidence: `src16 = {c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4") for c in cuts}`
  - fix: Build src16 from the actual source camera clip paths (e.g., from cuts or the source directory), not from `final_*.mp4`.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[high] pipeline/run_fresh.py:688** The G9 row adds an extra `(identical or not fallback)` condition beyond the calibrated luma floor. If the approved reference's conform used fallback and its outro is not hash-identical, the reference would fail this row even though it passes the calibrated G9_tail gate.
  - evidence: `rows[fmt]["G9_tail"] = _status(res["G9_tail"]["pass"] and (identical or not fallback))`
  - fix: Remove the extra `(identical or not fallback)` condition so the row reflects only the calibrated G9_tail gate result, or align the condition with the approved reference behavior.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[high] pipeline/run_fresh.py:589** Wiring error in source_clips for 16:9: the comment states the source should be 'the prepared clips (source camera, 1920x1080)', but the code points to files named 'final_{clip_id}.mp4'. The 'final_' prefix is the same convention used for the pipeline OUTPUT (cf. the variable 'final16' which is the gated 16:9 final). Feeding the pipeline's own per-clip output as the 'source' makes G8's render/source sharpness ratio ≈ 1.0 by construction, rendering the gate meaningless — it can never detect a real sharpness regression against the camera original.
  - evidence: `src16 = {c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4") for c in cuts}`
  - fix: Point src16 at the actual source-camera clips (e.g. f"src_{c['clip_id']}.mp4" or f"camera_{c['clip_id']}.mp4" — whatever the pipeline stores the pre-processing 1920x1080 camera footage as in the qa directory), not the per-clip final outputs.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] pipeline/run_fresh.py:688** G9 status adds a conjunctive condition beyond the stated 'calibrate the luma floor' change: the row is PASS only when the gate passes AND (outro is hash-identical to the locked master OR no conform fallback was used). A video whose tail luma is above the calibrated floor but whose outro is not byte-identical to the locked master (e.g. a re-encoded or slightly re-timed outro) and which did use a conform fallback will be marked FAIL even though the luma gate itself passed. This is a new pass/fail criterion not described in the DEC-1/DEC-3 scope (which only mentions calibrating the luma floor and removing the waiver row).
  - evidence: `rows[fmt]["G9_tail"] = _status(res["G9_tail"]["pass"] and (identical or not fallback))`
  - fix: If the only intended change is the calibrated luma floor, the status should be simply _status(res["G9_tail"]["pass"]). If the (identical or not fallback) guard is intentional, document it as a separate decision and add a test where luma passes but identical=False and fallback=True to confirm the expected outcome.
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
