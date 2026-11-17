# Heimdall audit

**Question:** Review this diff to pipeline/lock_precheck.py (the integrator's lock pre-check: it answers, before a paid build, what the render's lock will say about a span). Each answer has an outcome: "hold" is a FINAL verdict the builder never re-asks for that span; "error" is NO verdict (never a pass) and is asked again. The defect fixed: a YouTube video still "post_live" (DASH segments only) downloads a window section with seconds of picture, no audio and a 0 s container; pinned.validate_range then raised PinError "range outside the source file (file covers 0-0.000 s ...)" and the pre-check answered "hold" on words it never heard. The diff: on a PinError, when the acquired window has no media (pinned._duration < 0.5 s, or unreadable), the outcome is "error" and the window's work directory is removed (select_passages._download_window treats any existing file over 100 KB as a cache hit, so the 750 KB broken file would otherwise be served forever). Any other PinError (a real range fault on a file with media, a lock that cannot be made) still "hold".
FACTS (unchanged code): pinned._duration(path) runs ffprobe and returns the container duration or raises PinError when it cannot read one; wd = work_dir(vid, lo, hi, sha) is this video's window directory for this request (shared by the request's spans of that video); a span whose latest entry is "error" is answered again on the next request (_cached).
Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.
CHECKS:
H1. Can a span whose window HAS media and whose words differ now come back "error" instead of "hold" (a hold lost)?
H2. Can an empty or unreadable window still come back "hold", or a "pass"?
H3. Can removing wd break another span of the same request or video (a crash, a wrong verdict), or remove anything but this window's own cache?
H4. Can _empty_source raise, or anything else change behaviour?

**Panel:** gptoss  |  **Cost:** $0.0012
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
