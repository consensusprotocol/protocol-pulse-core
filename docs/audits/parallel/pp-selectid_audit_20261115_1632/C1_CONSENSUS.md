# C1 CONSENSUS — pp-selectid audit 20261115_1632 (RULING 117 (2)+(3): the join table and the search)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of tokens (finish=length, no answer), so Grok
was asked (P1_OR_WORSE: 3, one finding tagged P1, two P2 it calls blocking). Cycle 1: $0.0490 vendor-reported.

GROK'S BLOCKING POINTS, each checked against the code:
1. [P1] "A new selector, against M1 (no new renderer / compositor / selector)". NOT A DEFECT: the search is the
   orchestrator's own order (ruling 117 (2): "choose the order BY SEARCH over the table ... No model call in the
   search"). It lives INSIDE the existing line-up stage of package.build, beside lineup_for, reorder (ruling 63) and
   swap_lineup (ruling 41), and replaces the trial-and-error reordering ruling 63 did with paid verdicts; it adds no
   pipeline stage, no module, no render path, and the clips-alone and coherence verdicts still decide every line-up.
2. [P2, "blocking"] "itertools.permutations without an import". REFUTED: pipeline/package.py:54 `import itertools`
   (module top; reorder() has used itertools.permutations since ruling 63).
3. [P2] "300-400 model calls per package". REFUTED by arithmetic: at most 8 moments an angle = 49 ordered pairs (the
   hook never second), 25 pairs a call = 2 calls an angle, MAX_ANGLES 3 = at most 6 calls a build, and every answer is
   cached by the two texts for every later build. "Not charged": every call goes through the build's own router,
   whose spend ledger is the batch ledger (tests/package/proof_ledger.py:217-221, spend_path=PL.SPEND), read by the
   build's budget guards (over_budget, ruling 41's per-build cap).

P3s noted: the cache key carries the two texts and the question's version, not the on-screen names (the hook cache's
rule too; a channel renamed would need a new key); the docstrings; a coherence-only failure does not prune the search
(the ruling names the clips-alone verdict's joins; coherence has no joins).

CHANGED AFTER CYCLE 1 (in this cycle 2's diff): the order's set for the table is "the hook and the clips that passed
step A from both vendors, the second pass and CUTTABLE; cap 8 moments an angle", which is the CLEARED POOL, not only
the writer's own 3-4 picks. build() now asks the table of the angle's hook, its writer's other moments, then the rest
of the cleared pool by rank score, at most 8 (ext = the angle with those moments; the search keeps the writer's order
first by its fewest-moves rule). New test: the table's moments are the hook, the writer's picks, then the pool, capped
at 8. 13 tests in TestRuling117JoinSearch; all 40 suite files pass.
