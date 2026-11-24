# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 119 (Protocol Pulse, Python): pipeline/post_live_prefetch.py and its two callers (run_fresh.prefetch_post_live before pinned.prepare; lock_precheck.prefetch). Same diff as cycle 1. Only state what you can verify from the diff and the cited lines. If uncertain, say so. Do not guess.

CYCLE 1: qwen27b F1 (the live_status probe's 90 s timeout -> 30 s) and F2 (a segment without a source is YouTube: documented as pinned.acquire's model) were applied; gpt-oss PASS. SINCE THEN, LIVE: U7X6kReXets (post_live, 7134 s) was cut from the cached whole stream at 20:27 ET Nov 23 and the HARD clock guard (pinned.post_live_offset) passed; the independent verifier's drill confirmed the same window (41.2 s) and that the guard refuses a window shifted 1 s or 2.5 s.

TRACE AND ANSWER:
T1. A yt-dlp section download that TIMES OUT is killed by subprocess.run's timeout; can a process it started keep writing the same out path after _post_live_window has written it (a race that replaces the cut window), and does anything here prevent or detect that?
T2. If the whole-stream download is partial (a truncated video.mp4 above 100 KB left by an earlier failed run in POST_LIVE_DIR), what does this route produce, and which check (if any) refuses it before a render uses it?
T3. Any other defect.

OUTPUT: for each finding, severity, file:line, the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff and the cited lines show; say when uncertain.

**Panel:** gptoss  |  **Cost:** $0.0003
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
