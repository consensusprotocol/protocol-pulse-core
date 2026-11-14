# Audit 0915 (the orchestrator's 09:03 rulings: R-29 and ruling 92 amended), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP no. One <critical>, one <high>, two <medium>. The <critical> and the <high> are refuted from the code
  (below); the two <medium> are cosmetic or by design.
- qwen3.8-27b: no SHIP line. Most of its <high> tags resolve inside its own text ("Not a bug", "No issue"). Its points
  that stand: caption_evidence's 2-tuple case (implemented: its claim that the guard catches it was wrong for this
  diff), the build's float(m["start"]) (refuted), the private E._parse_time and the sentence split (kept, measured).
- glm-5.3-flash: finish=length at 24000 tokens, no SHIP line. Its <critical> on ValueError is refuted. Its H66 is a
  real defect (implemented). It also notes that caption_evidence counts after its guard (implemented).

Upper-bound cost: about $0.75 ($0.110 + $0.220 + $0.421), outside SPEND_LY.json.

## Implemented

1. glm H66: the ruling-95 report dropped an UNMARKED episode.
   - pp-ingest writes an unmarked episode as `"turns_per_min": 0.0` and `"unmarked": true` (its episode_measure:
     `round(n / mins, 2)` and `n == 0`). next_attempt's filter dropped every numeric turns_per_min <= 0.
   - So an unmarked episode (unknown, never solo) left "the newest conversation upload". The amended rule says only a
     MARKED episode with zero turns is out.
   - Now state() carries `unmarked`: pp-ingest's flag, or episode_turns()'s on a recount. The filter keeps an unmarked
     episode and drops only a marked one at <= 0.
   - Test: the ruling-95 test adds pp-ingest's shape for an unmarked episode (0.0, unmarked true) as the newest upload.
     It is the conversation. The marked zero-turn episode stays out.
   - Mutations S9 (drop the unmarked clause) and S10 (pp-ingest's flag never read): both killed.
   - This touches the report only (next_attempt), not a gate.
2. glm and qwen: caption_evidence counted the units AFTER its guard (only the reader call was inside the try).
   - A record from another reader with a short unit, a time that is not a number, or a None unit would crash the build.
   - A NaN time compares False with both bounds. It would read as zero changes near the clip: a REFUSAL from evidence
     that cannot be read.
   - Now the counting is inside the guard. Times are float()-ed and must be finite. Any failure is measured False: no
     evidence, never a refusal, and the layout decides.
   - The build's reader (speakers.captions) already refuses NaN and out-of-order times (speakers.py:170). So this
     guards an injected reader.
   - Test: test_a_record_that_cannot_be_counted_is_no_evidence_never_a_refusal_never_a_crash covers NaN, "noon",
     1-tuples and a None unit. The same record read cleanly does refuse.
   - Mutations S11 (no finite check) and S12 (the guard narrowed to OSError): both killed.

Mutation check: 21 of 21 killed. In the scratch copy: 20 suites, 560 tests, all pass.

## Refuted, with evidence from the code

- grok <critical> and glm <critical>: "vo_fidelity raises ValueError, not GateNotMeasured, on an empty title or a
  zoneless built_at".
  - vo_fidelity is wrapped by `@_measured` (moments_gate_adapter.py:93-103). It turns KeyError, TypeError,
    ValueError, IndexError and AttributeError into GateNotMeasured("the case cannot be read: ...").
  - glm notes this itself: the hunk starts inside the function.
  - test_an_unreadable_case_is_the_harness_error_never_a_guess passes, including
    assertRaisesRegex(GateNotMeasured, "not a zoned time"). Mutation R9 is killed by it.
  - glm H1 (a headline that is a number): TypeError, so GateNotMeasured by the same decorator. The harness's ERROR,
    never a verdict.
- grok <high>: "layout_for uses hashlib with no import, so NameError".
  - spotlight.py imports hashlib at module level (line 37, unchanged). It was already used for the contact sheet's sha.
  - The layout tests call layout_for with evidence and pass.
- grok <medium> 1: "a one-unit record gives turns_per_min None, so the prompt reads 'None speaker turns a minute'".
  - True, and cosmetic. speakers.captions returns a record only when it carries a marker, and an episode's record
    spans the episode.
  - changes_near and one_turn are counted the same either way. The refusal does not read turns_per_min.
  - Not changed.
- grok <medium> 2: "next_attempt filters on the episode's turns a minute while the build refuses per clip".
  - By design. Ruling 95's report says when the next qualifying EPISODE could arrive, before any clip of it exists.
    The per-clip refusal needs a clip's span.
  - The report's rule text says so ("the layout decides per clip").
- qwen <high>: "the build's float(m['start']) crashes on a None start".
  - A moment reaches the source test (stage 8) only after earlier stages read the same fields as numbers.
  - The ledger read sets start and end from the word record's token times (ledger_build.py:383-411).
  - truth_for float()s them at stage 2 (package.py:2160, :2175).
  - This call adds no new exposure.
- qwen <medium>: "E._parse_time is private".
  - Kept. It is the parser E.age_hours uses for every item's published_at (eligibility.py:309, :327). So the clock and
    the items are read by one parser.
- qwen <medium>: "SENTENCE_SPLIT does not split on an ellipsis or a semicolon".
  - Measured against the packager's own split (E.split_sentences over the words, then E.spoken, as
    package.current_levels reads sources). On the real corpus, 0 of 52 universes give different levels.
  - Four edge sentences give the same levels: an ellipsis before another asset's price, "U.S." mid-sentence and at the
    start, and a price before an ellipsis.
  - current_level_values needs a present-tense clause before the price, so a longer "sentence" did not add a level in
    any case tried. Kept.
