# pp-selectid audit 0352 (the exclusion screen's deterministic part before step A; why_none named): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers moments.py, package.py and test_medley.py. No P0. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- qwen: no P0, no P1, "SHIP: yes";
- glm: "yes with conditions" (no P0; its P1s are mostly coverage notes about contracts outside the diff).

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | Prove, not assert, that ad_read_out refuses exactly what the package stage refuses (glm condition 1, P1-1, P1-8) | IMPLEMENTED: a differential test runs package.exclusion_for, the package stage's own screen, on the same moment and the same stubbed context, with a router that fails if called. It gets the same verdict ("exclude"), the same reason and the deterministic backend. |
| K2 | The contracts outside the diff (glm condition 2) | VERIFIED in the code. (a) exclusion_for passes context_around's raw before-string to exclusion_verdict (package.py: `before, after = CI.context_around(...)`, then `M.exclusion_verdict(router, m["text"], before, after, ...)`); ad_read_out reads the same call on the same fields. (b) src_of is context_integrity.source_for, which raises KeyError for a missing Source (audit 0208, K1), the same lookup exclusion_for uses. (c) A moment's "sentences" is always [k0, k1] (moments.record), the same fields exclusion_for indexes. |
| K3 | why_none could read "angle N: None"; the whole message was truncated at 900 (glm P2-1, P2-3) | IMPLEMENTED: each angle's reason is its why, else its result, else "no reason recorded", truncated at 250 characters per angle. |
| K4 | A KeyError from any field is skipped, not only a missing Source; out["ad_read"] is a census after no_role (glm P1-4, P1-5) | DOCUMENTED in ad_read_out's docstring. Both fail closed: a skipped moment still meets the package stage's screen. |
| K5 | The AD_MARKERS search ran twice (glm P2-2) | IMPLEMENTED: one search. |

## Kept

- **glm P1-2 (why_none ordering):** verified correct by the reviewer itself. The fallback runs only when there is no package and nothing else set a reason.
- **glm P1-12 (step A's "screened" count changes):** documented. Step A no longer sees moments that the package stage refuses on the same rule.

## Verification

- test_medley 54 OK and test_moments OK; the other suites are run before the commit.
