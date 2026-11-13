# pp-selectid audit 1810 (ruling 76: the 12 h window on the render clock, the registry expiry, the render-clock re-check, delivered speech re-posted): cycle 1 consensus

- **grok:** "SHIP: no", on one P0 and one P1. Both are refuted below with the code; the P1's durability is now pinned
  by a test.
- **qwen:** "SHIP: No", on two P0s. Both are refuted below.
- **glm:** "SHIP: yes with conditions", no P0. Its conditions are met below.

## Consensus, implemented

**C1-a (grok P1, glm P1-1): can a later seed revive an expired candidate? ("never offered again")**
- The code already holds. `seed()` adds a line-up only when its key is not in the registry
  (`if k not in reg["candidates"]`). It applies "package" only to an entry that is not closed. It seeds each record
  once.
- Durability is now PINNED: test_ruling_76_expires_a_candidate_with_a_clip_over_12_h_for_good seeds a later record
  that passes, and even packages, the expired line-up. It stays closed / expired and is never due.

**C1-b (grok P0, qwen P2-8, glm P1-2 / P2-1, all three): REPOST_ALIGN_MIN is not in the diff.**
- It is ruling 53's module constant, `REPOST_ALIGN_MIN = 0.80` (pipeline/package.py:877), resolved when
  same_speech() is called.
- TestRuling76Window calls same_speech and passes, so there is no NameError.
- The docstring now names it ("ruling 53's 0.80").

## Implemented (single reviewer, verified)

- **glm P2-1:** the bound `--hours 12` (and 6) is accepted. The run goes on past the check, and the test's refusal
  guard stops it at the proof dir.
- **glm P2-5:** same_speech's docstring said equal texts are the same speech, yet one-word texts never are. It now
  says "two texts of at least two words".
- **glm P1-5 / P2-7, and aligned:** eligibility._parse_time (behind usable's `expired`) reads a time WITHOUT a zone as
  no measurement, so expired. window_problems read it as UTC.
  - Now both refuse it (refuse more, never accept more).
  - A pin's source_published_at is utc_z()'s, which is already None for a zoneless time, so no pin changes.
  - E.age_hours never raises on a malformed time (`_parse_time` returns None).

## Refuted (evidence)

- **qwen P0-1** (same_speech is fuzzy, against L-k): L-k governs whether a LOCK's text equals the spoken words.
  same_speech decides only what is EXCLUDED as delivered speech. Its errors:
  - a wrong match loses one moment (fail closed);
  - a missed match would reuse delivered speech, the harm ruling 76 (b) forbids.
  Strict equality would miss every re-post cut differently. The guards (>= 8 words, runs of >= 3 words, 80 % of the
  shorter) keep shared common words from matching (the scattered-words test). qwen's examples are 3-word texts,
  which only an EQUAL text matches.
- **qwen P0-2** (the pin check should use the build's ctx.now): ruling 76 (c) says "re-checked against (a) at the
  moment they would render". The pin stage's real clock is that moment, and it is LATER than the build's start, so
  it only tightens. glm, answer 5: "Yes ... (c)'s the moment they would render. Later clocks only tighten."
- **glm P1-4** (three clocks): agreed they exist, and each later clock only tightens. The record's inside_12h is the
  driver's count at the build's start, labelled as such. The "why" order (b before a) only names one of two reasons
  that both exclude.
- **glm P1-3** (a transient inputs.json read error expires a candidate for good): by the ruling's letter (an
  unknown age is never assumed fresh). Every candidate comes from today's records, and a candidate's clips expire in
  12 h anyway.

## Recorded (no change)

- glm P2-2: same_speech runs twice for a matched moment (any, then next). It is build-time CPU only.
- glm P2-4: ruling 57's cross-angle preference is no longer exercised by a build test, since moments over 12 h are
  expired. Inside 12 h every clip is "fresh" (< 24 h), so the preference is moot. Its unit test still runs.
- glm P2-6: hooks_4 is None when the hook pool has no list. That is honest: never a made-up count.

## Suites (scratch copy at HEAD + this diff)

All 15 OK: medley 159, candidates 11, ledger_build 36, lock_precheck 12, ...
