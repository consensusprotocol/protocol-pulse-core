# A19 ONE COPY PER DELIVERY (the orchestrator's 08:15 ruling 3), cycle 1: consensus

Reviewers (Heimdall): qwen3.8-27b (391 s, $0.011): "safe and fail-closed", one P1 (refuted below); glm-5.3-flash
(412 s, $0.006): "P0 none: the diff is production-ready as written; the fail-closed paths hold", one P1 on the diff
(a test: added); muse-spark-open (574 s, $0.033): "This code is ready for production" (P0 / P1 none). Cycle 1:
$0.050. Diff reviewed: 016965a4 against d64b24ba.

## Agreed by all three (verified)
- Fail closed everywhere: a delivered video whose attested copy cannot be identified (no sha256 named, no copy with
  it, a candidate that cannot be read) keeps EVERY copy; an unreadable PROVENANCE.json stops the pass in unit_videos
  before kept_copies runs.
- A replay's identical copy and a recut are other copies and go only under the usual rules (expired, unit idle 2 h,
  not open in a process, inside its unit, not a protected path, not a symlink).
- The sha256 cache key (real path, size, mtime_ns) re-hashes a replaced file; a read cut short gives a hash that
  matches nothing, so the file is not taken for the attested copy (kept, never a wrong keep).

## Fixed (with a test, each mutation-checked: the test fails without the fix)
- C1-1 (glm P1): a test with the attested copy in a reference's run/sources/ (the delivery's own second path) and a
  PROVENANCE naming a plain file name: it is found and kept, the runs' copies of the video go, the video is resolved.
  Parametrized over "<id>.mp4" and "section_1.mp4". Dropping run/sources/ from the own paths fails both cases.
- C1-2 (muse's note on kept_of; glm C3): deleted.jsonl's `kept_copies` was derived from the kept file's NAME
  (`_vid_of(basename)`), so a PROVENANCE `file` not named by its video id would have logged `kept_copies: []` beside a
  deletion (none today: all 152 source entries of the real PROVENANCE files are named "<id>.<ext>"). kept_copies() now records the video id each copy was
  kept for ({real path: (video id, why)}), and kept_of is computed only for another copy. The "section_1.mp4" case
  fails with the name-based version.
- C1-3 (glm C5): the module-level sha256 cache grew for the watcher's lifetime; it is emptied at SHA_CACHE_MAX = 4,096
  entries (a test: 5 files with a bound of 3, every hash still right).
- C1-4 (glm C15): the omitted-video test's last assertion passed for either reason (the video's publish time was
  unknown); it now has an expired publish time, so only the unresolved rule keeps it, and the keep reason is asserted.

## Refuted or recorded
- qwen P1 "run/sources/ is not collected into copies, so attested copies there are unresolved": refuted. `copies`
  lists target files only (the files the purge may delete); no target names run/sources/ (runs/*/sources/*,
  lock_precheck/work/*/sources/*), so a file there is never deleted. kept_copies checks the delivery's OWN
  sources/<file> AND run/sources/<file> before the copies (so qwen's refined case, own sources/ mismatched and own
  run/sources/ matched, is found too). The one case not looked for: the attested copy only in ANOTHER unit's
  non-target directory; that video is unresolved and every copy is kept (fail closed). On the real tree the only
  run/sources/ is the v2f reference's own, and the 09:2x ET dry run had 0 unresolved. Design 12 now says this.
- glm C13 "summary() prints the A19 line for a refused pass": refuted; summary returns "purge: <refused>" first.
- muse "if / continue vs elif": both branches continue; equivalent; no change.
- glm C12: a video unresolved for delivery A and resolved for B keeps every copy (A's fail-closed rule);
  `other_copies` counts 0 for it and `unresolved` names it. Recorded (reporting only).
- glm C10 / qwen #3: PROVENANCE.json is read twice (unit_videos, kept_copies); either order of a concurrent rewrite
  is fail-closed (verified by glm). Recorded (P3).
- glm C4 / muse TOCTOU: a copy created after the snapshot is either the attested one (then the video was unresolved:
  every copy kept) or another copy (deleted under the usual rules). Verified: no lost copy.
- qwen #2 (_SHA without a lock): one purge thread per process, and purge.lock (a blocking flock) serialises passes
  across processes; the worst case is a redundant hash. Recorded.
- Outside this diff (recorded for their own change): glm P1 "the second-model check loop parses a 13-day ledger tail
  every 30 s while mining" (service.check_once, ledger): to be measured before any change; glm P2 newest_mtime walks
  each unit every pass; glm P3 the router's retry recording, check_seen, COVERAGE_HOUR_UTC across DST; observability
  notes (muse, glm).

Suite: tests/ingest 320 passed.
