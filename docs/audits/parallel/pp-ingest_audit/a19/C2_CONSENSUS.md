# A19 ONE COPY PER DELIVERY (the orchestrator's 08:15 ruling 3), cycle 2: consensus

Reviewers (Heimdall): qwen3.8-27b (220 s, $0.023): "Yes" (P0 / P1 none); glm-5.3-flash (224 s, $0.005): "Yes.
Conditions (none blocking)" (P0 / P1 none); muse-spark-open (360 s, $0.030): "Yes, with no conditions"; and a fourth,
minimax-m3.1-flash (392 s, $0.010, cut at its output limit in section 3): "the diff is fail-closed and safe to ship",
two P1s of its own (below). Cycle 2: $0.068 (both cycles $0.118). Diff reviewed: the working tree at 147c4884
against d64b24ba (the A19 commit 016965a4 plus the cycle 1 fixes).

## Agreed by all four (verified)
- The attested copy is protected by real path and exempt from every later rule; an unresolved video is checked before
  the other-copy branch, so it never loses a copy; an unreadable candidate is never taken for the attested copy.
- The cycle 1 fixes are present and each is mutation-checked; qwen's cycle 1 P1 stays refuted (every reviewer).

## Refuted by measurement
- minimax N-2 (P1) "the hash search reads every copy of every delivered video: 100+ GB on a fresh process's first
  pass" (it took the 3.53 GB of the v2f reference video's 3 copies for each of the 121 copies). Measured on the real
  tree, read-only, in a fresh process (10:3x ET): 39 files hashed, 0.45 GB, 0.8 s; the pass 1.3 s, the next one 0.5 s.
  A delivery's own file is hashed first and almost always matches. No size pre-filter needed. Design 12 records the
  measurement.

## Fixed (report only: no deletion decision changes; each with a test that fails without it)
- C2-1 (glm P3-1, minimax N-1's report half): an unresolved video's why named only the FIRST delivery that could not
  identify its copy; it now names every one ("pinned_dl2: ...; pinned_dl3: ..."). Test: one delivery resolved, two
  not; both named, every copy kept.
- C2-2 (found while checking qwen's c1 note 5 and minimax N-5): design 12 said "live.json and `purge` name it
  unresolved", but the watcher's stored pass (`purge_last`, live.json `purge.last_pass`) carried no A19 block at
  all. It now carries `one_copy_per_delivery` (kept_copies, other_copies, unresolved); the service test asserts it in
  live.json.
- C2-3 (minimax N-5): the `purge` command lists each unresolved video with its why (it printed only their count).
- C2-4 (glm N4, glm's condition 3): a comment that the counting lines run in a dry run too (the summary's "would
  go"); design 12 states the invariant (the deletion loop keeps exactly the paths kept_copies names plus every copy of
  an unresolved video; both sides fail closed; a fast path added to either must re-derive it).

## Recorded, not changed
- minimax N-1's semantic half (P1) "key the rule by (delivery, video): a video is unresolved only when NO delivery
  resolved it": declined. A delivery whose copy cannot be identified (a candidate that cannot be read, no hash named)
  may own any of the copies, so the rule stays per video and fail closed (design 12, the orchestrator's A19 text in
  STATE). Measured: 0 unresolved videos on the real tree; the report now names every failing delivery (C2-1).
- minimax N-3 (P2): the cache clears wholesale at 4,096 entries; a pass hashes about 40 distinct files, so the bound
  is a guard, not a working size. minimax N-6 (P2): kept_copies counts real paths, references' included (the summary
  shows the targets' share in its kept line: 30 of 46).
- minimax N-4 (P2): STATE's assumption A19 still states "kept wherever it lies": updated when A19 goes live (the old
  keep reason is grepped nowhere outside these audit files).
- glm N6 / C7 (P2): newest_mtime walks each run every pass (fine at today's 10 runs; first to fix at 10x).
- glm N7: a file replaced between the check and the hash: the next pass re-derives everything (self-healing), never a
  wrong deletion of an attested copy.

Suite: tests/ingest 327 passed. Verdict: four of four "ship"; A19 goes live at the next watcher restart.
