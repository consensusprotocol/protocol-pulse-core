# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 21 s finish=stop usage in 14011 / out 1036 usd~0.096 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0640**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
Qwen caught the unhandled exception propagation out of `f.result()` / parallel orchestration (its P1-1) and the direct `a_by[mid]` lookup (P1-2); GLM caught the PRESCREEN_N vs. len(chunk) coupling and the transient stale-verdict window between angle_write and the first write. I had rated the parallel path and re-screen block as P2-only in Cycle 1 and did not explicitly trace the exception path or the None-group handling for unknown back-ends. The C2 diff + new tests close exactly those gaps.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- Fully agree with Qwen P1-1, GLM condition 4, and the consensus fix: `one()` + `ex.map` + per-chunk `STEP_A_UNAVAILABLE` makes the parallel second_screen fail-closed (verified by the new test at test_medley.py:297-312).  
- Agree with GLM P1-1 on the cap/truncation concern but accept the consensus mitigation (K2): `cleared` is built only from moments present in `a_by` after the first prescreen, so the UNKNOWN_BACKEND path cannot mask a truncation.  
- Disagree with Qwen P1-2 (KeyError): the new code uses `a_by.get(mid)` everywhere and the build-site filter guarantees every cleared moment has a first verdict; the added test at 314-336 exercises the unknown-backend case safely.  
- Agree with Grok on threading safety, off_writers selection after writes, and that no clip reaches angle/line-up without two passing verdicts (tests 226-239, 249-260).  
- Agree with consensus that the K2 stale-verdict fail-open is fixed, item-44 swap-only behavior is now correct and tested (including “no swap fits → re-lined”), and that Heimdall-in-time behavior is unchanged (still zero re-screens).

3. **NEW FINDINGS FROM THIS REVIEW**  
None at P0/P1. The combined Cycle-1 feedback plus the C2 diff revealed no new violation of L-m, L-x, L-j, item 44, or item 45.  
P2 (minor): pipeline/package.py:32 — `ex.map` does preserve order (per stdlib docs), but a one-line comment would make the zip reliance explicit for future readers.  
P2 (test): test_medley.py:325 — the fake prescreen’s ternary is duplicated and could be a dict lookup for clarity, but it does not affect correctness.

4. **REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| second_screen (parallel, groups, fail-closed) | P1 (orchestration) | none | Exception wrapper, .get() usage, None-group handling and dedicated test eliminate the crash and KeyError vectors. |
| re-screen / item 44 (stale, bad, swap) | P1 (K2 stale verdict) | none | Explicit `bad` dict, “no verdict off writers is never a pass”, doomed tracking, and swap_lineup call now match the law and the 05:48 failure mode exactly. |
| off_writers + writers_v/f after angle/write | P2 | none | Post-angle and post-write calls, a_two accumulation, and rig’s third-vendor tests cover all vendor-family growth cases. |
| Overall correctness & test coverage | SHIP with conditions | SHIP yes | All Cycle-1 P1 items are implemented and regression-tested in the provided C2 diff. |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL:** none  
**P1 HIGH:** none  
**P2 MEDIUM:**  
- pipeline/package.py:32 — add comment “# ThreadPoolExecutor.map preserves submission order” before the zip.  
- tests/package/test_medley.py:325 — clarify the duplicated ternary in the fake prescreen (non-functional).

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Second_screen (item 45) run on every cuttable clip *before* angle_write, paired with the strict “no verdict off writers is never a pass” re-screen path (item 44), eliminates the entire 05:48 failure class while preserving every prior safety law.

7. **PRODUCTION READY?**  
**Yes.** All Cycle-1 P1 findings are addressed, the new tests exercise every branch (including exception, unknown backend, same-vendor, no-swap re-line, and both-vendor write via the rig’s third backend), no clip can reach angle or lineup without two passing verdicts, off-writer selection is maintained after writes, and the single-clip swap behavior matches the orchestrator order. The two P2 comments are documentation-only and can be added post-ship.