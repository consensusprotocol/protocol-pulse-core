# Audit 20261114_1441 (ruling 104), cycle 2: consensus

Reviewers:
- grok-4.20: yes with conditions. No P0 or P1.
- qwen3.8-27b: yes with conditions. One finding it tags <critical> and lists as P1 (the "doomed variant").
- glm-5.3-flash: yes with conditions. No P0 or P1; five P2 conditions.

All three agree the cycle-1 <high> (medley ordering) is resolved by the rework: a held parent is REPLACED in the pool, so
the two never compete. grok's ALONE <medium> is resolved by the text_sha256 argument, which glm adopts.

## Taken (a one-line fix; cycle 3 reviews it)

- **qwen P1, "the doomed variant".** A parent with a CURRENT hold whose held word cannot be left out:
  - the word cannot be placed, or it sits in the first sentence;
  - the parent is ALSO over the ceiling;
  - so the ceiling trigger still made a variant, and that variant kept the held word. It would fail its own pre-check:
    gates spent, no pin, and never a wrong pin.
  - Now: when a current hold cannot be relieved, for_pool makes NO variant at all, not even the ceiling's, and the
    parent is not replaced.
  - Test: the first-sentence hold over the ceiling gives no variant and replaces nothing. The mutation that puts the
    old behaviour back (P6) is killed.

## Documented, no change

- **grok (1): lock_precheck.answer reads only the current decoder's file under the current rules.** This is unchanged
  code: result_file(seg, results_dir, decoder=DECODER) and _matches (rules == RULES). test_ruling_104 checks it through
  holds(): an older decoder's and older rules' holds are not read.
- **grok (2): read the first production build's ruling-104 notes.** That will be done on STATE line 1 after the build.
- **glm P2-1, an insert anywhere suppresses the variant.** This is the chosen, conservative semantics. held_word places
  only an approved-side token. A spoken-side insert's position is not placed, so no variant is proposed. It errs toward
  no variant, never toward a variant that keeps a held difference.
- **glm P2-2, a held parent with no variant.** It stays in the pool and holds again at its pre-check, exactly as before
  this change. The notes name it on the build's RULING 104 line.
- **glm P2-3, the cut hold does not also try held_word.** A ruling-73 hold is about the cut, not a token, so its
  as_spoken text need not differ. The tail goes, as the ruling says ("a tail the cut cannot make").
- **glm P2-4, a variant whose span is already a pool moment.** That moment keeps its own record. The note records the
  collision ("its variant X is already in the pool").
- **glm P2-5, the two roles' answers are compared by their "at" strings.** Both are the integrator's ISO 8601 UTC
  stamps in one format, written by one service, so the string order is the time order. lock_precheck.answer itself
  picks each role's newest.
- The cycle-1 note said test_ruling_104 holds 15 tests. It holds 14 at cycle 2, and 14 with the fix's assertion added
  to an existing test.

Verification: 20 of 20 mutations killed with P6. test_ruling_104, test_spotlight and test_ledger_build pass in dev10.
