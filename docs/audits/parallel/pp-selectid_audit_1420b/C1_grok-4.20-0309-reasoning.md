# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 147 s finish=stop usage in 7420 / out 699 usd~0.055 (upper-bound price)

**P2: pipeline/candidates.py:11** (F1)  
Concrete scenario: due() now builds sort key with `_at(x[1]["found_at"])` (or `datetime.min` UTC for missing). The added test (test_candidates.py:106-109) confirms ordering for valid ISO-with-offset, same-time, and missing-key cases (newest-first, missing treated as oldest). Cannot verify from diff alone that a malformed `found_at` (e.g. non-ISO string or int) raises inside due() *and* that the driver's pre-write refusal block (exit 2, no package.json/registry update) still fires, because no caller changes or top-level try around `due(reg, now)` appear in the diff.

**P2: pipeline/candidates.py:22** (F2)  
Concrete scenario: run_due passes current `lineups` to try_one, then clamps any returned `judged` to `[0, lineups]` (updating `why` when out-of-range) before subtracting. The new test (test_candidates.py:118-120) confirms a try_one returning 99 when 8 left results in judged=8, left=0 and "all are charged" in why. Verifiable that candidates cannot push total judged > initial 8; the for-loop structure + `if cls == "package"` return + initial lineups=0 test (unchanged) together prevent over-charge. Matches "recorded verdicts free" ruling.

**P1: tests/package/proof_ledger.py:58** (F3)  
Concrete scenario: nested try around `PK.build(..., candidate=c)` catches any Exception, logs, returns `(None, "budget", msg, left)` *without* setting `last["out"]`. run_due still calls `outcome(..., "budget", ...)`, charges remaining lineups, and continues. The later `last.get("out") or {minimal dict}` (line 70) and guarded registry block (lines 82-92) after `package.json` write are present. Verifiable that driver no longer crashes on build raise, package.json is never lost, and candidate is not forcibly closed/rested. The `--from-candidate` path now also populates `candidate_tries` (line 44). However, the diff does not show the outer exception context for the whole `main()`, so cannot verify *all* new paths are non-crashing.

**P2: tests/package/test_candidates.py:104** (test coverage)  
New `test_due_sorts_by_time_not_by_text` and out-of-range test match the F1/F2 claims that are visible in the diff. No test for malformed `found_at`, for a candidate build that raises, or for multiple due candidates when a prior one clamps lineups to 0. All 13 suites pass per header, but coverage of the exact F3 exception/guard paths is not visible.

No P0s. All four stated fixes (F1-F4) are implemented in the visible code; the registry-write guard, candidate_tries shape for --from-candidate, and lineups clamping are exactly as described. Uncertain on malformed-time refusal path and full outer exception surface because they live outside the diff.

**SHIP: yes with conditions** (add malformed-found_at test + confirm due()-raise path still hits exit-2 before any write)