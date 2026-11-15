# C1 CONSENSUS — pp-selectid audit 20261115_0910 (the medley's ruling-109 channel gate)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0), glm-5.3-flash (P1_OR_WORSE: 0). Grok not asked (they agree). $0.0033
vendor-reported.

AGREED BY BOTH: the subset argument holds (`cleared` at :2562 is a filter of the gate's `ms`, so the rule at :2587
refuses every pool the gate refuses); nothing paid runs before the gate; the candidate exclusion is right; the
pre-existing candidate KeyError (proof_ledger.py:484) need not be fixed in this change.

EACH FINDING AND WHAT WAS DONE:

1. glm [P2] "the record's shape is tested against one late-failure mode only". NO CHANGE: the shape is not mode-dependent.
   The :2587 return is the `out` of ONE dict literal (pipeline/package.py:2563-2572 in the base), and its "prescreen" is
   a literal too (screened, cleared, failed, parallel_101, held_102, last_resort_87). Between :2563 and :2587 only log
   lines run (:2573-2586); nothing is added to `out`. Every failure mode that reaches :2587 returns the same keys.

2. glm [P2] "open_work may subscript the missing 'visual' key: verify". VERIFIED, AND NOW TESTED.
   tests/package/proof_ledger.py:150-154 reads `(res or {}).get("prescreen") or {}`, `pre.get("held_102") or {}` and
   `(res or {}).get("visual") or {}`: all tolerant. A NEW TEST,
   test_the_guard_finds_no_open_work_and_the_registry_no_line_up, runs the real proof_ledger.open_work on the gate's
   record (0: nothing asked or undone) and the real candidates.seed (no key added, no candidate).

3. glm [P2] "usable 5 vs pool 4 in the log line". NO CHANGE: intended. "usable" is package.usable's count (n_usable,
   :2528), which includes the moments the no-role rule later removes, as the base's own log line does
   (:2573 "{n_usable} usable, ... {len(no_role)} left out by the render's STAND_ALONE"); "pool" is what would reach step A.

4. glm [P3] "mark the gate so no paid call is inserted above it". Already there: the comment says "It ends here, before
   any paid verdict", and the test asserts no call of any kind (screens, events, hook, visual and medley calls empty);
   mutation C10 (the gate after a paid step A) is killed.

5. qwen [P3] "is n_usable defined?" Yes: pipeline/package.py:2528 `n_usable = len(ms)`, before the gate.

6. Both [P3] the pre-existing candidate KeyError (proof_ledger.py:484 reads o["candidate"] outside its try; the early
   returns before :2703 set none). TRACKED as an open item in the handoff, for its own change and audit. This change adds
   no exposure: candidate builds skip the gate.

THE CODE NOW: the same gate; test_medley.py gains the open_work / seed test (6 tests in TestRuling109Channels). Suites:
tests/package 553 pass. Mutations: 10 of 10 killed.
