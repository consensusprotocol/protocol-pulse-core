# Audit 20261114_1441 (ruling 104, the tail-side twin), cycle 1: consensus

Reviewers:
- grok-4.20: yes with conditions. One <high> and one <medium>.
- qwen3.8-27b: SHIP yes. One <medium> (the boundary's index convention), answered by its own reading and the test.
- glm-5.3-flash: yes with conditions. Two conditions and notes.

## Taken: a rework of the trigger (the diff as it stands now)

- **grok <high>: "parents_first only orders the spotlight's finalists; the medley could take the variant before its
  parent".** glm's condition 1 adds that the reordering ran before the 3-finalist cut, so a variant could fall out of
  the finalists behind a low-ranked parent. Both come from one design gap: the parent and its variant COMPETED.
  - The rework:
    - holds() now reads the parent's hold under the CURRENT decoder and rules only, through lock_precheck.answer: the
      newest answer on the exact span, as a hook or a clip. Under ruling 103's rules that hold is FINAL, its targeted
      re-listen included ("the hold is final and the clip may only be saved by a variant that leaves the token out").
    - A parent with such a hold (or ruling 73's cut hold) is REPLACED by its variant in the pool
      (proof_ledger.with_variants, inputs["ruling_104"]["replaced"]), so the two never compete in the medley or the
      spotlight.
    - The full clip is honoured first because the variant exists only once the current pre-check, re-listen
      included, has held the full clip.
    - A parent over the ceiling stays BESIDE its variant: it can't be a spotlight (usable's 35 s), and the medley may
      still use it.
  - parents_first() and spotlight.finalist_order() are REMOVED, and spotlight's finalists are ordered as before.
  - Consequence: an older decoder's hold no longer proposes a variant. A build first re-asks the full clip under the
    current decoder; that is the 14:12 order ("FIRST the re-listen; if it holds, the variant").
  - Tests: an older decoder's or older rules' hold is not read; a newer pass clears the hold; a hold as a clip is seen;
    the newest of the two roles wins; the held parent is replaced and the ceiling parent kept.
  - Mutations: the 19 now killed include H1-H3 (the current answer), R1-R2 (replace or keep) and L1-L2 (the build).

## Refuted

- **grok <medium>: "the variant inherits the parent's stands_alone score and can pass ALONE on it".**
  - The ALONE gate reads the integrator's CLIP SCORER verdict for the moment's own id, and only when it was given on
    its current text (package.with_verdict: the verdict's text_sha256 must equal the text's; spotlight.alone_score).
  - The variant has its own id and text, so it gets only its own verdict, or waits for one.
  - The miner's scores feed rank_score (ranking) only. M.record builds a fresh record and copies no scorer_verdict.
- **glm (b): "a repeated held token: the variant ends before the FIRST occurrence and keeps the later, held one".**
  The variant is a PREFIX ending before the first occurrence, so every later word is left out, the held occurrence
  included. It errs short, never long.

## Documented, no change

- **glm condition 2: holds() compares approved_text exactly, not through canon.** The entry's approved_text is an
  ECHO of this side's request (lock_precheck.segments_of sets it from the moment's text). lock_precheck._matches uses the
  same exact equality, and holds() now goes through it.
- **glm: a hold-triggered variant can still be over 35 s** (the held word late in a long parent). The spotlight's free
  pool keeps its ceiling, and such a variant is simply not a spotlight. The medley's own limits apply.
- **qwen <medium>, the boundary index.** src.sentences[k] is (first word, last word), inclusive (E.Span.w1). The variant
  ends at the last sentence whose last word is before the held word. The test asserts the variant's text, its left-out
  words and "401k." as the held word.

Verification:
- test_ruling_104: 15 tests.
- In dev10: test_ruling_104, test_spotlight and test_ledger_build, 93 passed, network blocked.
- 19 of 19 mutations killed.
