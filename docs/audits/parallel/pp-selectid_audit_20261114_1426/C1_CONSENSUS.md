# Audit 20261114_1426 (the ruling-103 landing: DECODER / RULES, the relisten record sealed, canon-401k), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes. No finding.
- qwen3.8-27b: SHIP yes. No <critical>, <high> or <medium>.
- glm-5.3-flash (342 s): no <critical> or <high>. Its <medium> notes are fragility and consistency notes, each ending
  "not a break". One is taken.

## Taken

- **glm (b), the record is shared by reference.** apply() put the parsed entry's own dict on the segment. A later
  in-place edit of either would then move the sealed bytes without the entry file changing. apply() now seals a COPY,
  as it stands (a JSON round trip, so the record's types are kept). The test asserts that the copy is equal and is not
  the same object.

## Documented, no change

- **glm (c), canon's plan-name rules** ("401b", an "owed" number before a plan, the split form). canon.py and
  test_canon.py are the integrator's audited code (batches 79 and 80), taken byte-identical so that both sides keep one
  canonical form. Questions on its rules go to its owner; this change neither adds nor removes a rule.
- **glm (b), the edge form {token, against, verdict "hold", why}.** It rides only on a HOLD entry. A held segment never
  reaches apply() (pre-check ok is False), so the edge form is never sealed. A sealed record is always a passing
  re-listen's full form, as it stands.
- **glm (d), the landing order.** Builds are this side's own: no build runs between READY and the integrator's push,
  and this side pushes only after it, as agreed.
- **glm (a)/(e), the test literals, the history comment, attested()'s default rule text.**
  - The literal file-name assertion pins the integrator's contract (the 12-hex decoder in the file name).
  - The plumbing assertion uses LP.DECODER.
  - attested() records an ADOPTED text (ruling 84's class), which ruling 103 does not change.

Verification: 8 of 8 mutations killed. test_ruling_103 and test_lock_precheck pass. The copy is checked by a new
assertion.
