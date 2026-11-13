# pp-selectid audit of the batch + speakers diff (00:05 ET Nov 13 order): cycle 1 consensus (synthesis by the pp-selectid session, 00:14 ET Nov 13)

**Run.** C1_STEP.diff is 44,699 bytes; the prompt is 68,620 bytes. No reviewer raised a P0.
- grok-4.20-0309-reasoning (xAI): no P0/P1; three P2s. SHIP yes with conditions.
- qwen/qwen3.8-27b (Heimdall, effort none): two P1s and three P2s. SHIP yes with conditions.
- z-ai/glm-5.3-flash (Heimdall, effort none): five P1s (it downgrades one itself) and twelve P2s. SHIP yes with
  conditions.

**One change outside the reviewed diff, made while cycle 1 ran.** The integrator's check_pin_only recomputes seal()
from this worktree's package_pin.py. Since ruling 1 (88397a53) put time_sensitive and source_published_at in the seal
body ALWAYS (None when absent), all 6 earlier pins in tests/package/proof recomputed to a different digest, including
the delivered 37c5b5f5 and 41f29b1f. The speaker edit would have added a third such field.
- Fix: SEALED_LATER = (time_sensitive, source_published_at, speaker). Each enters the body only when the segment
  carries its key, so all 6 earlier pins recompute again (0 of 6 under HEAD 0453f171).
- A new pin always carries all three, because to_pin refuses one without; dropping any of them changes the digest.
- Test: test_every_earlier_pin_still_recomputes_and_a_dropped_later_field_is_caught. Cycle 2 reviews this change.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | to_pin checks the speaker record's shape only, so a record check() would never produce can be sealed: a named speaker absent from people, or a line that is not that person's (qwen P1, glm P1-3) | IMPLEMENTED: speaker_problems now requires what check() produces. Every person has a name, a source line and a role in host / guest / other. A named speaker is one of the people, with that person's line and role, plus a non-empty basis. to_pin cannot re-read the source or the transcript; that verification is check()'s, at attribution, and the evidence is sealed for the reader. Test: 4 new must-fail shapes in test_the_pin_refuses_... |
| K2 | an unmeasured speaker record reaches the pin (grok P2, which wants it tightened; glm P2-3, which says it is not a defect: "unknown" claims nothing) | IMPLEMENTED in part. A failed attribution is tried once more with a new seed (seed 8). A second failure stays "unknown" with measured false and its why, and it still pins: it claims no name. The order's rule is "Unknown speaker = say unknown, never guess", and L-m governs gates; this record is not one. STATE marks every unmeasured speaker. Test: test_an_unmeasured_attribution_is_tried_once_more_with_a_new_seed |
| K3 | people and roles are verified only as far as the name in the line (qwen P2: a memorial mention; glm P2-1: the role is never checked) | DOCUMENTED, kept. "people" means named in the source's own lines. Code checks the name is in the line it cites; the role is the verdict's reading of that line, shown beside it. No text test can prove participation |

## Unique findings, implemented (each verified first)

- **glm P1-1:** verified that Router.call re-raises a back-end's own error (`except BaseException: ... raise`), so one
  segment could abort the whole seal. attribute() now turns any exception into "unknown", measured false, with the
  exception type in why. Test: a router that raises RuntimeError.
- **glm P1-2:** a ```json fence is read (_json). Test: a fenced reply names the speaker.
- **glm P1-5:** the seal step refuses a malformed package file with KeyError / TypeError named, never a traceback.

## Refuted or kept, with the reason

- **qwen P1** (normalised matching lets a non-contiguous basis pass): KEPT.
  - Its example is the same words in the same order, differing only in punctuation and case.
  - The transcript's punctuation is the recognizer's own, so word-level verbatim is the standard. glm P2-2 checked
    the same matching and agrees.
- **qwen P2** (a delivered span from another universe may not exclude): REFUTED. package.usable matches by video_id
  and time overlap, independent of the universe (package.py:96-97). A span on a video the universe lacks matches
  nothing.
- **grok P2** (people still lists a person the speaker logic rejected): KEPT by design. people is for tagging the
  people the source names; the speaker is a separate claim.
- **grok P2** (package_batch_<tag>.json is written before the speakers): KEPT. build and seal are separate steps, and
  the pin is the authority. Nobody reads an unsealed package file as a pin.
- **glm P1-4** (usable's overlap is unverifiable): REFUTED with the code and test cited above (test_ledger_build K7).
- **glm P2-4** (the seal holds the record's why and backend text): KEPT by design. The seal covers the bytes that ship.
- **glm P2-10** (no test drives the real Router): ANSWERED by the live seal of the batch pins, recorded in STATE.

## Verification

- 10 offline suites, 215 tests OK. test_speakers.py has 15 tests.
- regression_test.sh in the worktree: 26 PASS | 0 FAIL | 5 WARN.
