# pp-selectid audit 0640 (ORDER 06:22 items 45 and 44): final consensus after cycle 2

**Cycle 2 verdicts:**
- grok: "Production ready: Yes", no P0 / P1;
- qwen: "Production ready: Yes", no P0 / P1 left (its cycle-1 P1-1 fixed, its P1-2 agreed a non-defect);
- glm: "Yes with conditions": one P1 (N1, spend visibility), refuted below with the code.

All three agree that:
- the cycle-1 fix (a raising chunk fails its clips closed) closes the only crash path;
- K1 (no KeyError) and K2 (no cap truncation) are non-defects;
- K3 (both vendors writing) cannot arise with the configured chains and is bounded anyway;
- no clip reaches the angle prompt or a line-up without a passing step-A verdict from each vendor, and the gates use
  the verdict off every writer.

## Cycle 2: IMPLEMENTED (no behaviour change)

| # | finding | change |
|---|---|---|
| D1 | grok P2 and glm N5 (consensus): the test's fake prescreen has a ternary with two identical branches | one assignment, with the comment saying why z's second verdict is the same vendor (STEP_A_SAME_VENDOR). |
| D2 | glm N3: the STEP_A_UNKNOWN_BACKEND reason should name the back-end | it names it (tested: 'nowhere:model'). |
| D3 | grok P2: say that Executor.map keeps the jobs' order (the zip relies on it) | comment. |
| D4 | glm P2-3: say that off_writers returns the FIRST qualifying verdict on purpose | docstring. |

## Refuted (verified from the code)

| # | claim | the code |
|---|---|---|
| R1 | glm N1 / P1-1: with store=None the second screen's calls may be invisible to the spend trail | `store` is prescreen's STEP-A VERDICT store (`_load_store(store)` / `db[...] = a`), never spend. Spend is booked by providers.Router.call on EVERY paid call: `_reserve(b, upper)` before it, then `_settle(key, b, usage, usd, role)` into the order's ledger (SPEND_LY.json). build()'s budgets read that ledger through `spend` (proof_ledger: `spend=lambda: (own["est"], own["best"])`, PL.meter(router)). So the second screen's calls count toward the per-build search budget (ruling 41) and the ledger, like every other call. The old post-write re-screen used store=None in the same way. |
| R2 | qwen P1-5 (cycle 2): one() catches Exception, not BaseException | intended: KeyboardInterrupt and SystemExit must stop the build (glm agrees). |
| R3 | qwen P2-1 / glm N2: a_two can hold more than two verdicts | bounded by clips x writes; off_writers re-checks every verdict against the current writers each time (now documented, D4). |

## Recorded, not changed

- glm N6 / P2-5: when the second vendor disagrees with the first, that clip leaves BEFORE the angle step. So the
  angle model sees fewer clips, and a Heimdall step-A outage at that moment ends the build. This is order 45's own
  design, recorded in STATE.

## Verification

- test_medley: 80 tests OK. The other ten suites OK; regression_test.sh is run on the worktree before the commit.
