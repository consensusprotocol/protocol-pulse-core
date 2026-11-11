# Heimdall audit

**Question:** Protocol Pulse news-video pipeline, auto mode story selection and verification. Changes: (1) candidates whose COUNTED evidence includes the same statement (same video, shared supporting chunk, >=5 consecutive shared words in the evidence quotes) are merged into one event: one derived query, verdicts pooled one per video, not-counted verdicts re-judged against the merged query within a budget, same coverage decision; (2) a story ledger: an auto run delivered HOLD FOR APPROVAL in both formats records its counted evidence; later runs exclude any candidate resting on the same statement; (3) the 9:16 letterbox check asks two vision models about ONE frame per shot of every talking-head segment; a non-screen shot called letterboxed or unanswered fails. Find real bugs: false merges of different events, a delivered story selected again, a story wrongly excluded, a letterbox that can pass, crashes, state left inconsistent. Only state what you can verify from the diff. (this chunk: pipeline/visual_check.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0182
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/visual_check.py:279** letterbox_check passes vacuously when VISION_MODELS is empty: the inner for-loop never executes, ans stays {}, and all(a == "no" for a in ans.values()) returns True (vacuous truth) for every non-screen frame. A letterboxed frame would therefore pass the check with no model actually inspecting it.
  - evidence: `good = all(a == "no" for a in ans.values())`
  - fix: Add a guard before the per-frame loop: if not VISION_MODELS: return False, [{"error": "no vision models configured"}]. Alternatively, treat an empty ans dict as a failure: good = bool(ans) and all(a == "no" for a in ans.values())
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[low] pipeline/visual_check.py:240** For a talking-head segment shorter than 2/FPS seconds, lo exceeds hi (lo = start+1/FPS, hi = end-1/FPS). The clamp min(max(t, lo), hi) then yields hi, which is before lo, placing the extracted frame inside the dissolve region the code is supposed to avoid. The frame is still extracted (no crash) but violates the stated invariant 'a frame inside a dissolve is moved out of it'.
  - evidence: `lo = max(s["start"], segments[i - 1]["end"] if i else s["start"]) + 1.0 / FPS
hi = min(s["end"], segments[i + 1]["start"] if i + 1 < len(segments) else s["end"]) - 1.0 / FPS
t = min(max(s["start"] + (`
  - fix: After computing lo and hi, if lo >= hi, fall back to the segment midpoint: t = (s["start"] + s["end"]) / 2, and skip the clamp. Or guard: if hi <= lo: t = (s["start"] + s["end"]) / 2 else: t = min(max(..., lo), hi)
  - raised by qwen27b:F3; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F1 [medium] shot_frames crashes with AttributeError if the caller passes layout=None. The docstring says 'A segment without a measured layout is one shot of class unknown', implying the absence of layout data should be handled, but the code only guards against a missing key inside the dict, not against the dict itself being None. (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [medium] `ask_vision` calls `_request` before the retry loop, so if `_request` raises (e.g., missing API key or unreadable sheet image), the function crashes instead of retrying and returning empty answers as the docstring promises.
