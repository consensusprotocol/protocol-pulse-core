# C1 CONSENSUS — pp-selectid audit 20261115_1129 (ruling 112's diagnosis driver, tests/package/hook112.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 1) and glm-5.3-flash (P1_OR_WORSE: 1). Both raise a P1, so they agree on the
count and Grok was not asked. Cycle 1: $0.0082 vendor-reported.

THE TWO P1s:
1. qwen [P1] "a moment that passed G17a but was not rated (no error) should be stage 4, 'may open'". NOT A DEFECT: "may
   open" is package.can_open (pipeline/package.py:1417), which is hook eligibility AND G17a AND the render's opener
   rule. A moment that passes G17a but fails another of them never reaches "may open"; it stops before it, where the
   driver puts it, with "cannot open (hook eligibility or the render's opener rule)". The test already covers this
   case (moment "x" in test_each_moment_stops_where_its_record_says: stage 3, "cannot open"). The STAGES comment now
   says what "may open" means.
2. glm [P1] "medley_trace reads the rating before the second-pass / trim-cut / G17a failures; the order rests on
   undocumented record semantics". FIXED: every failure is now checked before the rating. A rated moment passed all of
   them (package.build rates ONLY its openers, :2643-2645), so it still reaches the rating. A record holding both a
   failure and a rating for one id would now stop at the failure. A new test builds that inconsistent record (stage 2,
   "L-v 2 FAIL"); mutation H16 (the rating first) is killed.

THE P2 / P3s:
3. glm [P2] "the hook pass's 'a model was called' is a heuristic (cost > 0 or >= 1 s)". FIXED with pp-ingest's own
   record: its `calls` table logs every hook-pass call (role hook / spotlight; kinds ok, invalid, cache). An event
   counts as called when such a call exists for its video since that video's previous event. The heuristic stays only
   for a database without `calls`. New test; mutation H17 killed. On the real data the classes move by one event
   (261 / 43 / 13).
4. glm [P2] "cache keys split on ':'". FIXED: rsplit(":", 2) on "<moment id>:<text sha>:<version>".
5. glm [P2] "a missing reference kills the whole run". FIXED: ref_moments records an unreadable reference with its error;
   the others are calibrated and parts (1), (3) and (4) still run. New test; mutation H18 killed.
6. glm [P3] "a ledger row without a moment id". FIXED: skipped (tested: a row with moment_id null).
7. glm [P2] "the stop is checked before each seed, so the last call could pass the cap". The cap still holds: the router's
   own limit is the order's $0.30 (providers.Router reserves each call's list-price upper bound and refuses one that
   would pass it). The $0.25 stop is ours, below it.
8. glm [P2] "spotlight step-A detection matches the text of `out`". The text is code-written: spotlight.build writes
   "step A: ..." or "no verdict (law L-m)" for exactly that stop (pipeline/spotlight.py, the `stop(...)` after the
   prescreen). It is the record's only encoding of the stage. No change.
9. glm [P2] "held-back counts: a moment held by both scroll and alone counts for each; setup uses <= 3". Intended. The
   question is which PART holds a 3 back, so both parts count. A rating-3 moment has scroll and alone >= 3 by
   definition (the rating is their lower one), so == 3 is exact for them; setup is outside the rating, so <= 3 is the
   only meaningful test. Shown apart.
10. qwen [P2] "Heimdall only for every call of the calibration?". Yes: hook_ratings makes ONE kind of call,
    call_parsed(router, "coherence_verdict", ..., kind="hook") (pipeline/package.py:900-902). Its chain is the one
    heimdall_hook_chain replaces. package._writers only reads the angle_write chain; it calls nothing.
11. qwen [P3] "open() without a context manager". FIXED in build_records, ref_moments and main.
12. ALSO NEW: `--since` (ISO, with a zone) pins the window's start, so the run reports the order's own 48 h (from
    16:15 UTC Nov 13). The hook pass's window uses the same start.

THE CODE NOW: tests 15 (was 12); 18 of 18 mutations killed after a control run; suites 700 pass.
