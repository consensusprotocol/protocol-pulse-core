# C2 CONSENSUS — pp-selectid audit 20261115_1700 (RULING 117 (2)'s set: join_moments)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and glm-5.3-flash (0; its breaker had closed): they agree, Grok was not
asked. Cycle 2: $0.0025; the audit $0.0297 vendor-reported. No P1 in either cycle; no third cycle. Both read cycle
1's one change (the K9 test) and call it production ready.

P2 noted, NOT changed (the landed code is the audited code):
- qwen, again, "can() repeats lineup_ok's checks; a shared helper or a comment": C1's answer stands (every line-up
  still passes lineup_ok at pipeline/package.py:2057, so a drift can only narrow the table, never loosen a line-up);
  glm's cycle 2 agrees and asks only that the argument be recorded, which C1_CONSENSUS does.

P3s noted:
- glm "the exclusion of the hook's own video holds only without repeat_ok; under L-y 4 a same-video moment could
  stand beside the hook": REFUTED by the code: lineup_ok's repeat_ok branch also requires every segment its own video
  (`len({m["video_id"] for m in segs}) == len(segs)`, pipeline/package.py:1605-1606), and the search's second pass
  runs with repeat_ok=True under that same rule.
- glm "the `x in cleared and can(x)` order is load-bearing": correct as written (left to right); noted.
- glm: the K9 test also pins that the exclusion gate dooms (not only drops) a moment; qwen: the cap truncates the
  pool first when the writer's picks fill it (the order's own priority: the hook, the writer's picks, then the pool).
- The docstring's length and the long test names (both reviewers): left as they are.

Suites: all 40 files, 813 tests (810 before; the fill test, join_moments' own test, the K9 test). Mutations: 23 of 23
killed after a control run. FINAL DIFF: FINAL.diff (written at landing).
