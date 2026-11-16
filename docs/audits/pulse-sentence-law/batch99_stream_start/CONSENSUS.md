# Batch 99 (pp-ingest R14, 1b6bc0cb..fbcf0986): two cycles, PASS; one single-seat finding judged not a defect

The cycles:
- Cycle 1 (S1-S5): only entries outside the window are re-dated; only streams; release_timestamp first; malformed records are safe; future and old starts stay out; nothing else changes.
- Cycle 2 (Z1-Z4, break it).

| Cycle | qwen27b (medium) | gpt-oss (medium) |
|---|---|---|
| 1 | PASS 0.92, 38.2 s, 11,774 characters of reasoning, $0.0023 | FAIL, one finding (high), 17.3 s, 11,350 characters, $0.0004 |
| 2 | PASS 0.72, 176.4 s, 27,236 characters, $0.0058 | PASS, 14.4 s, 10,161 characters, $0.0003 |

**gpt-oss's cycle-1 finding: "stream_start returns None for finished streams with no release_timestamp, causing universe() to drop them even though they should keep their RSS time." NOT A DEFECT; no change.**
- The finding contradicts itself. stream_start returning None IS what keeps the RSS time: universe() re-dates only when a start is known. So a finished stream that names no start keeps its RSS date, which is the design (S2).
- Its proposed fix uses the read time for was_live too. That would date a finished stream by when it was last READ, possibly days after it aired, and keep an old stream in the window. That is exactly mutation W3, which test_a_finished_stream_with_no_start_recorded_keeps_its_rss_time kills.

Consensus: no defect. No change. 9 of 9 mutations killed (MUTATIONS.log); must-fail on the old code: 3 of 9 tests fail (MUST_FAIL_OLD_CODE.log).
