# THE CALIBRATION REUSE AT A RESTART (F1 kept; after the 09:16 false outage), cycle 1: consensus

Reviewers (Heimdall): glm-5.3-flash (398 s, $0.006): "production-ready ... every reuse gate fails closed to a live
calibration" (P0 none); qwen3.8-27b (404 s, $0.011): "production-ready" (P0 none; its one P1 is outside this change);
muse-spark-open (484 s, $0.032): "ready for production" (P0 none). minimax-m3.1-flash: no review (an empty reply at
its output limit; not re-run). Cycle 1: $0.050. Diff reviewed: the working tree at 32fd1d99 against c4f733db (the
A19 cycle 2 report fixes also in it, already audited).

## Agreed by all three (verified)
- Every gate fails closed to a LIVE calibration: no record, another chain or model, no single zoned asked_at (the
  cached era), a future or day-old asked_at, nobody passed. An old record without `unmeasured` cannot pass (it has
  no asked_at either: muse).
- One look at start (`_reuse_tried`), then the live path as before; the outage retry (CHECK_RETRY_S doubling) is
  untouched: an outage calibration is never reused (nobody passed in it).

## Fixed (each with a test that fails without it: mutation-checked)
- C1-1 (glm P1): the "next calibration a day after the LIVE one, not after the restart" coupling is pinned by a
  fake-clock test: reused 6 h after the live calibration, none a minute before its day is up, a live one just after.
- C1-2 (muse P1): a refused reuse is said, with its reason ("the stored calibration is not reused (asked 25.0 h
  ago): asked live now"; none stored; another chain or model; no single zoned asked_at; nobody passed); the four
  refusal tests assert the reason. Design 16 says so.

## Recorded, not changed (outside this change)
- glm P1: a metrics surface beyond live.json (breaker states, calibration age, error rates past 24 h): observability,
  its own change.
- muse P1: watch.py's Shorts detection by URL (fetch.py's media-type check stands behind it): its own change.
- qwen P1: the purge dry run's `deleted` counts what WOULD go (audited in a19 c2, glm N4: the summary says "would
  free" / "would go"; the dry run is the CLI's default, never the watcher's).
- glm P3: the A/B tool's in-flight convention unenforced (ab.py): unchanged here.

Suite: tests/ingest 328 passed.
