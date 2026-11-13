# pp-selectid audit of the ledger build path (ruling 2, 22:40): cycle 2 dispositions (synthesis by the pp-selectid session, 23:34 ET Nov 12)

**Run.** Cycle 2 cross-reviews the fixed diff (C2_STEP.diff, 27,420 bytes; prompt 51,306 bytes) with the cycle-1
reviews and C1_CONSENSUS.md. Every reviewer: SHIP yes with conditions; no P0.
- grok-4.20-0309-reasoning (xAI), 30 s: P1, the drop reason; P2, only the last failure is kept; condition 3, the
  hard-coded delivered pins.
- qwen/qwen3.8-27b (Heimdall, effort none), 70 s: P1, SNAP_GUARD is a blacklist; P1, the first row's channel; P1,
  the fallback is not counted. P2: SEARCH_PAD_S; the hard-coded pins.
- z-ai/glm-5.3-flash (Heimdall, effort none), 159 s: P1 N-1, only the last failure is kept; P1, the first row's
  channel. P2: N-3 typographic apostrophes, N-4 the pin read, N-5 the exception type, N-2, N-6, a missing-sha test,
  SEARCH_PAD_S.

**Spend:** about $0.31 at the config's upper-bound prices.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K4 | a video's drop reason is only the LAST failure, and a punctuated record passed over before a verbatim one is used leaves no trace (grok P1 + P2-2, qwen P1-3, glm N-1 P1) | IMPLEMENTED: word_source returns (Source, path, passed_over). passed_over names every record read and not used, in reading order, each with why ("<file>: <why>"). A dropped video's reason is all of them, joined. A Source read after a passed-over record is listed in report.fallbacks. Test: test_every_record_passed_over_is_named_and_a_fallback_shows (punctuated sha broken and verbatim not sentence-ready: both named, punctuated first; verbatim ready: it is used and the fallback is listed) |
| K5 | the Source takes the first row's channel for every row of its video (qwen P1-2, glm P1-2; grok: latent) | IMPLEMENTED, checked not assumed: a video whose rows name more than one channel_id is dropped whole and counted (report.channel_conflict). The live ledger has none (0 of 77 videos, 2,069 lines). Test: test_a_video_whose_rows_name_two_channels_is_dropped_whole |
| K6 | the delivered pins are hard-coded in the driver (grok condition 3: they go stale after the next delivery; qwen P2; glm N-4: a missing pin raises a traceback after the proof dir is made) | IMPLEMENTED: --delivered PIN [PIN ...] is required and has no default. The pins are read BEFORE anything is written. A pin that cannot be read, has no clip, or has no zoned approved_at refuses the run: exit 2, why on stderr, no proof dir. Test: test_the_driver_reads_the_delivered_pins_before_writing_and_refuses_a_bad_one |

## Found by the builder while answering K6 (not a reviewer finding; audit round 2 reviews it)

- **"since".** Ruling 2's words are "best_unused_moments since the last delivered video", and `since` is that
  parameter of the adapter (pp-selectid contract v0: "lines mined at or after `since` or published inside the 72 h
  window"). The driver passed now - 72 h.
  - It now defaults to the newest delivered pin's approved_at: tonight that is 2026-11-13T03:01:09Z, the 41f29b1f
    medley. --since overrides it, and --hours is now the publish window only.
  - Effect: a line is no longer read if its video was published before the window AND it was mined before the last
    delivered package was sealed.
  - A since later than now, or one without a time zone, refuses the run.

## Unique findings, implemented (each verified first)

- **glm N-5:** a timeout, or an answer that cannot be read, raised something other than RuntimeError, which is
  outside the documented contract. Unreadable means empty, not JSON, or not {rows: list, report: object}. Both now
  raise RuntimeError. Tested with 5 such answers and a timeout.
- **glm N-3:** a typographic apostrophe hides a negation from SNAP_GUARD ("Don’t", U+2019). The added words are now
  read with ’ ‘ ʼ as '. None of the store's 66 word records holds one today, but the window records will come from a
  new writer. Test: test_a_typographic_apostrophe_does_not_hide_a_negation.
- **glm residual:** a record with no transcript_sha256 is never read. This is now tested; segments_sha256([]) is a
  hex digest, never None.
- **qwen P2 / glm:** the reason for SEARCH_PAD_S is now in its comment.
- **Hygiene:** the record reads and the tests' writes close their files (ResourceWarning).

## Refuted or kept, with the reason

- **grok P2-1** (report keys mix paths and messages): REFUTED. On a failure, word_source's second element was always
  a reason; a path came only with a Source. The new return shape makes this explicit (passed_over).
- **qwen P1-NEW-1** (SNAP_GUARD is a blacklist; use a whitelist, or anchor_ratio >= 0.9): KEPT.
  - In the live run, 8 of 162 re-anchored rows snapped. The words they added were "um", "Yeah," (2), "And", "You
    know, as", "right?" and "does quite well" (2): fillers, and the head of the row's own sentence. A whitelist of
    articles and prepositions would refuse them.
  - Every gate judges the snapped text, not the ledger row: step A, L-v 2, CUTTABLE, fidelity, context and
    coherence. The pin locks that text too. The ledger's scores only rank.
  - anchor_ratio measures how well the row's text matched, not how big the snap was.
  - names_person is not a gate in the packager: grep finds it only where moments.py validates and records it.
- **glm N-2** (a malformed row frees its span for a later duplicate): KEPT. This is correct: a malformed row made no
  moment.
- **glm N-6** (word_records lists records read, not records used): KEPT, and commented. moments and videos count
  what was used.

## Verification

- tests/package/test_ledger_build.py has 12 tests.
  - 5 are new or changed in cycle 2, and all 5 fail on the cycle-1 ledger_build.py (3 FAIL, 2 ERROR). The cycle-1
    file was rebuilt from C2_STEP.diff.
  - The driver test is new; the cycle-1 driver has no delivered_pins.
- All 9 offline suites pass: 193 tests OK.
- regression_test.sh in the worktree: 26 PASS | 0 FAIL | 5 WARN.
