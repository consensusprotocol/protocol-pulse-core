# pp-selectid audit of the ledger build path, ROUND 2: cycle 3 consensus (synthesis by the pp-selectid session, 23:47 ET Nov 12)

**Run.** Cycle 3 is a fresh review of the final diff after cycles 1 and 2 (C3_STEP.diff, 38,967 bytes; prompt 62,400
bytes; the question is QUESTION_R2.txt). No reviewer raised a P0.
- grok-4.20-0309-reasoning (xAI), 198 s: two P2s. SHIP yes with conditions.
- qwen/qwen3.8-27b (Heimdall, effort none), 57 s: P2s only. "SHIP: no", on a missing video_id crashing the build.
- z-ai/glm-5.3-flash (Heimdall, effort none), 335 s: four P1s and six P2s, plus one open question: does the sha cover
  the words? SHIP yes with conditions.

**Spend:** about $0.42 at the config's upper-bound prices.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K7 | the adapter's delivered_ids stay empty, so L-p rests on package.usable (grok P2, glm P1-1; condition: pass ids, or state that usable's any-overlap check alone carries L-p) | ANSWERED with evidence, and now stated and tested. usable drops ANY moment that overlaps a delivered span of the same video (package.py:96-97: d.start < m.end and m.start < d.end), whatever the pin's age; the driver passes every delivered pin's spans. The live run dropped 2 moments this way. The adapter's delivered_ids are ledger moment ids for the previous 24 h; tonight's pins carry no ledger id, and an overlap check is stricter than an id check. The driver's docstring says so. Test: test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age (a pin from Oct 1; two overlapping spans out, two touching spans in) |
| K8 | a row without video_id crashes build_inputs, and two rows without moment_id share one report key (qwen P2 x2, glm P1-4) | IMPLEMENTED: a row whose moment_id or video_id is not a non-empty string (or that is not an object) is counted in report.malformed. It is keyed by its moment_id, or by "row <i>" when that id is missing or already taken, and it never crashes the build. Test: test_a_row_without_an_id_is_counted_never_a_crash |

## Unique findings, implemented (each verified first)

- **glm (a): the sha does not cover the words.** CONFIRMED: segments_sha256 hashes each segment's [start, end, text]
  only (transcript_store.py:86-89), and S.tokens_from_record reads the clip's words from rec["words"]. The store's
  own reader checks the same thing (transcript_records). Fix in word_source: words_off_segments requires the word
  list to spell the sha-checked segments exactly, in order, with each segment's start and end equal to its first and
  last word's times (1 ms). Measured on the store:
  - all 66 word records (35,697 segments) agree to the ms;
  - word_source over all 57 videos refuses none for this reason (28 are read; 29 are verbatim records that are not
    sentence-ready).
  Test: test_a_record_whose_words_do_not_spell_its_segments_is_never_read (an edited word, a shifted boundary time, an
  added word). Word times inside a segment stay outside the sha; including the words in the hash is the store's fix,
  flagged to the integrator.
- **glm P1-2:** the record order was the glob's within a tie. Fixed: the store's two slots are read by name, in a
  fixed order: WORD_RECORDS = transcript.whisper_words_punct.json, then transcript.whisper_words.json. Those are the
  only two names in the store (9 and 57 files). Test: test_only_the_stores_two_word_record_slots_are_read_in_a_fixed_order.
- **qwen P2:** the near-negations "hardly", "scarcely", "barely", "rarely" and "seldom" were added to SNAP_GUARD. Test:
  test_a_snap_never_adds_a_near_negation.
- **glm P1-3:** SL.anchor takes the earliest longest match inside the window (sentence_law.py:336), so a phrase said
  twice inside it is not told apart. The hit's offset from the row's own caption times is now recorded
  (info.offset_s). This is a measure, not a gate. Test: test_the_hit_is_measured_against_the_rows_own_caption_times.
- **glm P2-1:** the proof dir is stamped to the second, and a run never writes into an existing dir (exit 2).
- **glm P2-2:** report.no_word_record_videos names which videos wait, with how many rows and why.
- **glm P2-3:** a pin's error names the pin file. Tested.
- **glm P2-4:** the driver test's no-write check looks only at ledger_* dirs.

## Refuted or kept, with the reason

- **grok P2** (an int channel_id and a str one count as a conflict): REFUTED. str(123) == "123", so they merge into
  one channel.
- **qwen P2** (a record of another method may pass): REFUTED. E.sentence_ready requires timing == "word"
  (eligibility.py:297), and only the two word slots are read.
- **qwen P1 -> P2 and glm (c)** (since = approved_at may read too few lines): KEPT. A pin's approved_at is earlier than
  its delivery, so the lines read are a superset of those mined since the delivery. A line mined between approval and
  delivery cannot be in the sealed package. glm finds no defect; qwen's own walk-through finds no failure.
- **qwen P2** ("1st" is refused by the digit rule): KEPT. It is fail-closed and the cost is one dropped row.
- **qwen P2** (the malformed test does not check the moments): REFUTED. The test asserts exactly one moment, L1.
- **qwen P2** (a pin with no story_id): KEPT. The run is refused, now naming the pin.
- **glm P2-5** (the same id with a different channel_name): KEPT. The registry's display_name is used first
  (ctx.channel); the row's name is only a fallback.
- **glm P2-6** (file_head and vod are hard-coded): KEPT. They are correct for the full-video slot, the only one read.
  They must be revisited when window records are wired.

## Verification

- tests/package/test_ledger_build.py has 18 tests. The 6 new in cycle 3 all fail on the cycle-3 code (3 FAIL, 3
  ERROR), which was rebuilt from C3_STEP.diff. The K7 test passes on both, as expected: it records evidence for
  existing behaviour.
- All 9 offline suites pass: 199 tests OK.
- regression_test.sh in the worktree: 26 PASS | 0 FAIL | 5 WARN.
