# Batch 98, cycle 2 (adversarial, the same diff): ONE FINDING, FIXED

The question is QUESTION.txt: five goals, X1-X5.

| Seat | Effort | Result | Cost |
|---|---|---|---|
| qwen27b | medium / 32768 | PASS, confidence 0.92, 88.5 s, 30,681 characters of reasoning | $0.0059 |
| gptoss | medium / 24576 | FAIL, one finding (high), confidence 1.0, 11.9 s, 7,465 characters of reasoning | $0.0003 |

**F2 (gpt-oss), checked against the code: REAL. Its severity is overstated, since the next re-read heals it, but the fix is simple.**
- _newest_meta took the LAST line of meta_history.jsonl.
- Two re-reads at once (the cron ingest and editorial_select, say) can append the OLDER read last.
- A stale is_live snapshot would then win until the next re-read, 20 minutes later.

**Fixed in d8b0b9b0:** the newest snapshot is the one READ last, by metadata_fetched_at; on a tie the later line wins, and an undated snapshot never wins over a dated one. Tested in test_the_newest_snapshot_is_the_latest_read_not_the_last_line, which fails before the fix; mutation R11 is killed.

The fix delta (306ab688..9ecccc26) gets its own two cycles in ../fix_delta/.
