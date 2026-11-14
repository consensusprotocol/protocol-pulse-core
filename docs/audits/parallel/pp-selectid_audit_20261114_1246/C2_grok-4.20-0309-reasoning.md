# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 26596 / out 1496 usd~0.170 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**
- GLM's M4 (package.py:245-248 + circuit_breaker.is_open at plan time): I completely missed that the leading-leg selection + est_wait_s snapshot can be stale if a breaker opens *after* step_a_plan but *before* the first prescreen batch starts. Concrete: 37 new moments, deepseek leads (300 s row), plan parallel=True, est=1200 s; then during first batch deepseek misses twice → breaker opens → remaining rounds fall back to next leg (Grok at 118 s). The parallel confirm still ran, but printed est_wait_s is wrong.
- GLM's M5 (_Tally.call:213): non-dict truthy usage (e.g. a backend returning usage=[...]) would AttributeError inside the lock. The except in confirm_ahead catches it and returns the partial tally, but I had not spotted the getattr(rep, "usage", None) or {} pattern could still raise.
- Grok's second medium (wait=0 when Grok leads): I noted the sequential fallback but missed that effective_deadline now returns the Grok row (118.1 s) under the first_bounds 120 s caller value, so the test in test_ruling_101_the_plan... correctly shows 472.4 / 826.7 s for Grok-lead cases.
- Qwen's race description, even though ultimately refuted, highlighted that confirm_ahead passes store=None while the main prescreen passes the real store; I had not traced that the cache path (unchanged _cache_put under CACHE_LOCK) is the *only* shared mutable.

**2. WHERE DO YOU AGREE OR DISAGREE?**
- GLM M1 (percentile on n=3, interpolation): fully agree — for exactly MIN_N=3 the p90 can be < max when two are fast outliers. Not a violation of ruling 100 text ("p90 of the pair's answered calls") but the intent ("deepseek 272→300") is slightly under-weighted. Cosmetic only; table is daily recomputed.
- GLM M3/M8 (finally + par["used"]): agree with the updated code. The finally block now guarantees ahead.result() runs even on prescreen exception; par starts with "used":0 and the error-path dict from confirm_ahead leaves it 0. proof_ledger.ruling_101_line prints the error. Matches the "extra spend" reporting.
- Grok's two mediums: agree they were real in the Cycle 1 diff; both are now explicitly documented in proof_ledger.ruling_101_line and the test_ruling_101_in_a_build_grok_confirms... (which forces Grok-first and asserts used=0). No code change needed.
- Qwen critical/high: disagree. The cache lock + plan_only=True + kind="step_a_second" exclusion of Heimdall writers means the "orphaned" Grok verdict on a filter-fail moment is exactly the extra spend that ruling 101 requires reporting. No correctness failure (second_screen unchanged, clip still needs both verdicts). The self-contradiction in Qwen's own trace confirms this.
- GLM M7 (per-call import deadline_table): agree it is negligible; Python caches the module.

**3. NEW FINDINGS FROM THIS REVIEW**
<medium>
package.py:310 (the finally) + 331 (par["used"] = prewarm_used after the cleared filter): if prescreen raises *after* some moments have been processed but before cleared dict is built, the later par["used"] = line is skipped. The output JSON still contains "parallel_101" with "used":0 (from the initial dict) and the ahead's "usd". Honest for spend, but the "used" count is under-reported for partial prescreens. Concrete sequence: 40 new moments, first batch succeeds (20 verdicts written to cache), second batch raises (e.g. cache lock timeout or router limit), exception propagates after finally — ruling_101_line sees used=0.
</medium>

<medium>
deadline_table.py:121 (0 <= (now - at).total_seconds() < RECOMPUTE_S): clock skew where computed_at is 1 s in the future produces negative diff → immediate recompute. Fail-safe, but produces two identical tables 1 s apart. Also, exactly RECOMPUTE_S (86400.0) recomputes — matches the "< RECOMPUTE_S" but could be <= if daily boundary is intended.
</medium>

No criticals. The per-model effective_deadline, read-only breaker, plan_only path, _Tally lock, and prewarm_used logic all hold under the updated diff (items 2'/3' restoring first_bounds 120 s + Router override).

**4. REVISED SCORES**
| Subsystem          | Cycle 1     | Cycle 2      | Why changed |
|--------------------|-------------|--------------|-------------|
| Deadline table & effective_deadline | 2 medium   | 1 medium    | Clamping + applied() filter + test coverage eliminated the "row on writer" and "under 60" risks I flagged. |
| Parallel confirm + cache | 1 high (race) | 0 high, 1 medium | Lock + plan_only=True + final diff's _heimdall predicate resolved the race; new partial-prescreen edge surfaced. |
| Tally / spend reporting | 1 medium   | 1 medium    | _Tally non-dict usage edge remains (low probability). |
| Breaker read-only + plan | 0          | 1 medium    | Missed the mid-build staleness in Cycle 1. |
| Overall            | 4 medium, 1 high | 3 medium    | Net reduction; all P0/P1 resolved. |

**5. FINAL PRIORITY LIST**
- P2 MEDIUM (package.py:310-331): document that par["used"] can stay 0 on prescreen exception even if some ahead verdicts were written; the extra-spend math still holds.
- P2 MEDIUM (deadline_table.py:121): add comment on clock-skew recompute behavior.
- P3 (test coverage): the new test_ruling_101_in_a_build... already kills the partial-failure path; no code change required.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**
Effective_deadline + per-model p90 table (now clamped 60-300 s) prevents healthy-but-slow deepseek from permanently opening its breaker, while the parallel Grok confirm (only when Heimdall leads and >10 min est) caps the wait without changing any clip-pass logic.

**7. PRODUCTION READY?**
Yes with conditions.  
Conditions: (1) add the two P2 comments above; (2) run at least one production build with >20 new moments under heimdall_first and verify the ruling_101_line extra-spend number matches manual cache inspection; (3) confirm that after 24 h the table recomputes and deepseek step-A row stays at 300 s. These are documentation/observability items only — no behavioral bugs remain that violate rulings 100 or 101.

SHIP: yes with conditions