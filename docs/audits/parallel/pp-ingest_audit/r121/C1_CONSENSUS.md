# r121: a stub probe is "no metadata", never waiting (Nov 16), cycle 1: consensus

Reviewers (Heimdall, diff-scoped; qwen + muse): qwen3.8-27b: "This code is ready for production. It correctly implements
the specified behavior, handles edge cases, and complies with all governing laws"; muse-spark-open: "No P0 or P1
issues in this diff ... Ready for production. Ship as-is." Cycle 1: $0.0058 of the $1.00 cap (COST.json).

## Agreed by both (verified)
- A stub (none of FACT_KEYS) is UNAVAILABLE "no metadata", retried hourly as before, given up after 6 tries, and never
  counted as waiting; any probe with one fact keeps its old path.

## Recorded (neither is a defect)
- muse: `any(j.get(k) ...)` reads a probe whose only fact were duration 0 as a stub; YouTube never sends 0 for these
  keys, and fetch.process already refuses a duration <= 0 ("no duration measured"), so the outcome (no mining) is the
  same either way.
- qwen: a log line when a stub is given up: the queue's state event records it (reason "no metadata: ...", next_at
  far ahead); recorded.

Nothing to fix. Suite: tests/ingest 434 passed; mutations M44-M47 4 of 4 killed.
