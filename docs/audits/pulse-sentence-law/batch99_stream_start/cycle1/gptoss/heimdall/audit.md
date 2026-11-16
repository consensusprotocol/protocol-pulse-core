# Heimdall audit

**Question:** Review this diff (pp-ingest R14, INGEST-FAIL-03).
- The problem it fixes: the transcript ingest's universe() keeps only YouTube RSS entries whose RSS "published" time is within the window (72 h). For a scheduled live stream, that time is when it was SCHEDULED, days before it airs, so the stream dropped out of the window just as it aired. Bitcoin Magazine KRvh4AcSofA was scheduled Nov 13 and aired Nov 16.
- The fix:
  - Each metadata snapshot now keeps yt-dlp's release_timestamp, the stream's start.
  - transcript_store.stream_start(video_id) gives when a stored stream aired.
  - universe() re-dates an entry outside the window by that start.

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

FACTS (unchanged code, not in the diff):
- _newest_meta(video_id) returns the newest snapshot dict. It raises OSError / ValueError when meta.json is missing or unreadable, and ValueError from _vdir for an invalid id.
- LIVE_STATES = ("is_live", "is_upcoming", "post_live").
- universe() runs one() per channel in a ThreadPoolExecutor and collects every list; an exception in one() propagates.
- Inside the window the RSS time is used, as before.

CHECKS:
S1. Is only an entry OUTSIDE the window by its RSS time re-dated? Is it re-dated only when the store holds it as a stream (is_live / is_upcoming / post_live / was_live)? Does an ordinary upload keep its RSS time?
S2. Does stream_start use release_timestamp, and the time of the read only for a snapshot read while not yet finished that names no start? Does a finished stream with no start keep its RSS time?
S3. Can a missing, unreadable or odd record (bad JSON, a bad time string, an invalid id, a bool or string release_timestamp) raise out of universe() or acquire()?
S4. Is a start in the future, or older than the window, still outside it?
S5. Does anything else change?

**Panel:** gptoss  |  **Cost:** $0.0006
## Consensus findings (majority of panel agrees)
- **[high] pipeline/transcript_store.py:183** stream_start returns None for finished streams with no release_timestamp, causing universe() to drop them even though they should keep their RSS time.
  - evidence: ````
    if not isinstance(m, dict) or m.get("live_status") not in LIVE_STATES + ("was_live",):
        return None
    for field in ("release_timestamp",) + (("metadata_fetched_at",) if m.get("live_st`
  - fix: Modify stream_start to consider metadata_fetched_at for finished streams as well, e.g.:
```
    if not isinstance(m, dict) or m.get("live_status") not in LIVE_STATES + ("was_live",):
        return None
    for field in ("release_timestamp",) + (("metadata_fetched_at",) if m.get("live_status") in LIVE_STATES + ("was_live",) else ()):
        try:
            return datetime.fromisoformat(m.get(field))
        except (TypeError, ValueError):
            continue
    return None
```
This ensures that finished streams with no start keep their RSS time by using the fetch time.
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
