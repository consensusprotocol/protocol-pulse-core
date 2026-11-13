# pp-selectid audit 0728 (one canonical token for a trimmed word): cycle 1 consensus

- grok, qwen and glm: no P0 or P1, all three "SHIP: yes". The predicates now match the render's validate_schema
  exactly. The only behaviour change is the intended one: a multi-token trimmed word ("But so", "and/or") is refused
  here instead of at the render's prepare.
- glm's P2s are recorded, with no change.
  - P2-1: an empty token list is refused before and after.
  - P2-2: the reason's text is not part of the seal; only segment fields are sealed.
  - P2-3: the pin-side "and/or" case is covered by the bad-value loop, which now includes it.
- Verification: test_medley 81 OK; every other suite OK.
