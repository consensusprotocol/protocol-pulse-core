# Heimdall audit

**Question:** Review this DELTA to pipeline/transcript_store.py. It fixes two findings from the audit of the stored-live-record re-read:
- (C1) a hung or missing yt-dlp (subprocess.TimeoutExpired, OSError) on a metadata read now becomes a logged AcquisitionError, which acquire() already catches for a re-read;
- (C2) the newest snapshot is now the one READ last, by metadata_fetched_at, not the last line of meta_history.jsonl.

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

CHECKS:
D1. Does every yt-dlp failure (a timeout, a missing binary, a non-JSON reply) now end in a logged AcquisitionError, with nothing else raised?
D2. Does _newest_meta pick the snapshot with the latest metadata_fetched_at? On a tie, does the later line win? Is a snapshot that gives no read time never chosen over a dated one? Are torn and foreign lines skipped?
D3. Does refresh_meta's re-read interval use the same read time (_fetched_at)? Can a malformed read time make it re-read on every call, or never?
D4. Does the delta change anything else?

**Panel:** qwen27b  |  **Cost:** $0.0022
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
