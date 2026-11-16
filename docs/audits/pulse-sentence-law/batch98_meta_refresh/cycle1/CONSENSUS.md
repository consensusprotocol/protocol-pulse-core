# Batch 98, cycle 1 (19cba368..306ab688, pipeline/transcript_store.py): ONE FINDING, FIXED

The question is QUESTION.txt: six concrete checks, M1-M6.

| Seat | Effort | Result | Cost |
|---|---|---|---|
| qwen27b | medium / 32768 | FAIL, one finding (medium), confidence 0.82, 122.8 s, 42,959 characters of reasoning | $0.0083 |
| gptoss | medium / 24576 | PASS, confidence 1.0, 18.7 s, 14,744 characters of reasoning | $0.0005 |

**F1 (qwen), checked against the code: REAL.**
- refresh_meta runs yt-dlp through subprocess.run(timeout=120).
- A hang raises subprocess.TimeoutExpired, and a missing binary raises OSError. Neither is an AcquisitionError, so acquire() would raise where it used to return a status.
- The ingest's Whisper pass does not catch it, so one hung re-read could end a whole run.
- The old code never ran yt-dlp for a stored video.

**Fixed in d8b0b9b0:** _fetch_meta turns both into a logged AcquisitionError. Tested in test_a_hung_or_missing_yt_dlp_on_a_re_read_is_a_logged_failure_never_a_crash, which fails before the fix; mutation R10 is killed.
