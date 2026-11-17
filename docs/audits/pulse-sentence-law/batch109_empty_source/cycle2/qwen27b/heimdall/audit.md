# Heimdall audit

**Question:** Review this diff to pipeline/lock_precheck.py (the integrator's lock pre-check: it answers, before a paid build, what the render's lock will say about a span). Each answer has an outcome: "hold" is a FINAL verdict the builder never re-asks for that span; "error" is NO verdict (never a pass) and is asked again. The defect fixed: a YouTube video still "post_live" (DASH segments only) downloads a window section with seconds of picture, no audio and a 0 s container; pinned.validate_range then raised PinError "range outside the source file (file covers 0-0.000 s ...)" and the pre-check answered "hold" on words it never heard. The diff: on a PinError, when the acquired window has no media (pinned._duration < 0.5 s, or unreadable), the outcome is "error" and the window's work directory is removed (select_passages._download_window treats any existing file over 100 KB as a cache hit, so the 750 KB broken file would otherwise be served forever). Any other PinError (a real range fault on a file with media, a lock that cannot be made) still "hold".
FACTS (unchanged code): pinned._duration(path) runs ffprobe and returns the container duration or raises PinError when it cannot read one; wd = work_dir(vid, lo, hi, sha) is this video's window directory for this request (shared by the request's spans of that video); a span whose latest entry is "error" is answered again on the next request (_cached).
Cycle 2: try to BREAK it. Report ONLY a defect you can show with a CONCRETE file / request state traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.
TARGETS:
T1. A real hold (words that differ, a range past a real video's end) turned into "error", so the span is asked again and could later pass.
T2. A window with no media answered "hold" or "pass".
T3. An exception, or a deletion outside the window's own directory.

**Panel:** qwen27b  |  **Cost:** $0.0034
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
