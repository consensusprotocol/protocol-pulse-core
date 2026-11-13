# pp-selectid audit 0335 (ruling 35: too_many_sentences retired): cycle 1 consensus

Synthesis by the pp-selectid session, 03:18 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers eligibility.py and test_eligibility.py. No P0. Verdicts:
- grok: no P0 and no P1, "SHIP: yes";
- qwen: "yes with conditions" (verify that `targets` is in scope);
- glm: "SHIP: yes", conditional on a grep for other consumers.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | Is `targets` bound where the retired rule appends to it (qwen P1)? | VERIFIED. eligibility.py:425 binds `targets = facts.setdefault("targets_missed", [])` in the same on-screen branch, before T7/T8 and T9. The test that reads the recorded target passes, which proves the append ran. |
| K2 | Does any other consumer of the reason string "too_many_sentences" exist (glm P2-4)? | VERIFIED by grep over every .py in the worktree, including pipeline/test_*.py. The only other hit is select_by_id.PLAIN:591, a reason-to-plain-words table for the older selector's model feedback. With the reason never raised, that entry is never read. KEPT, flagged (K2 law: not silently deleted). No gate, count or report reads the string. |
| K3 | The test is brittle on the literal "3", and the cap boundary is untested (glm P1-1 regraded to P2, glm P2-2) | IMPLEMENTED: the expected string is built from E.MAX_WINDOW_SENTENCES. A 3-sentence span (at the cap) records no T9 target. |

## Kept

- **glm P2-1 (retired and live targets share targets_missed):** KEPT. The recorded string names itself retired ("T9, retired by ruling 35"), and nothing ranks on the list.
- **qwen P2 (string formatting):** cosmetic, no change.

## Verification

- test_eligibility 29 OK, plus the boundary assertion.
- test_moments, test_select_by_id and test_ledger_build OK.
