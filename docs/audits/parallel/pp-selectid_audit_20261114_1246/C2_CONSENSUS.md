# Audit 20261114_1246 (rulings 100 and 101), cycle 2: consensus

Cycle 2 reviewed the diff as it stands after cycle 1's fixes (QUESTION.txt, "CHANGED AFTER CYCLE 1": items 2' and 3').

Reviewers:
- grok-4.20: SHIP yes with conditions. No <critical>, no <high>, two <medium> (documentation).
- qwen3.8-27b: SHIP yes. No P0/P1. Its three P2s are verified safe in its own text.
- glm-5.3-flash: SHIP yes with conditions. No P0. One P1 (H1) and four P2s.

All three confirm that cycle 1's real finding is resolved: every first-screen leg keeps a bound (glm 60 s, deepseek
300 s, Grok 118.1 s), and the second screen's Grok stays as ruling 88 (c) set it.

## Carried into ruling 102's change (audited there; no code change after this cycle)

- **glm H1:** "the confirm-ahead idles when Grok is the writer". The build's writer list is deepseek -> qwen -> Grok
  (proof_ly.WRITERS). The writer at plan time is the first not down (package._writers, :2270), so Grok writes only when
  deepseek and qwen are both down in this run before step A.
  - Then confirm_ahead has no leg off the writers and off Heimdall. It asks nothing and spends nothing, and the build
    line reads "0 verdicts, $0.0000".
  - No wrong pin and no spend: only the word "parallel" misleads.
  - Ruling 102 rewrites step A's second family list (Grok -> deepseek -> glm -> Gemini -> the local judge), which
    changes the confirm's possible legs anyway. The confirm-leg existence check goes there, with its own two cycles.
- **glm M2:** pin with a test that a shadow86:/probe87: role takes no row.
  - They are not verdict roles. The role string carries its prefix at call time; Router._breaker_live (unchanged)
    tests the same prefix.
  - The test goes into ruling 102's change set.

## Documented, no change

- **grok:** "par['used'] stays 0 when the first screen raises". The build then raises (the confirm-ahead is joined in
  `finally`), and no ruling-101 line is printed for a build that did not finish.
- **grok:** "a computed_at in the future recomputes". This fails safe, and exactly 24 h recomputes, per "recomputed
  from the records daily".
- **glm M1 (with its C1 M4 / M33):** est_wait_s and the leg are PLAN-TIME values.
  - A breaker that opens mid-build, or a failover inside a round, makes the real wait longer, so the plan errs only
    toward sequential.
  - The line says "would have held the build about N min": an estimate, labelled as one.
- **glm M3:** with exactly 3 answers, p90 interpolates between the top two. That is a legitimate p90 (ruling 100's
  letter). The table prints n, p50 and p90 beside every deadline, so the basis is visible on STATE.

SHIP: yes. The two carried items are scheduled into ruling 102's change. The diff committed is exactly the one
cycle 2 reviewed (C2_STEP.diff).
