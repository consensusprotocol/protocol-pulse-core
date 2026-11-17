# gemma-4-31b-it (google/gemma-4-31b-it) 152 s finish=stop usage in 10434 / out 3201 usd_reported=0.000720 usd~0.079 (upper-bound price)

The code implements RULING 126 (1) as requested. It correctly shifts the "show date" from UTC to ET and modifies the Step-A cache key to be date-agnostic for non-time-sensitive moments, while providing a migration path for existing cached verdicts.

### Analysis

**1. ET Date Conversion**
- `context_integrity.show_date(now)` uses `zoneinfo.ZoneInfo("America/New_York")`. This is the correct way to handle the ET calendar date, including DST transitions.
- The change is applied to both `contexts_from_sources` (used in context checks) and `package.prescreen` (used in Step-A), ensuring consistency across the pipeline.

**2. Cache Key Logic (`step_a_key`)**
- The logic `kc = context if time_sensitive(m) else {k: v for k, v in context.items() if k != "show_date"}` ensures that for moments without time-sensitive flags/words, the `show_date` is excluded from the SHA256 hash.
- This prevents "re-paying" for the same verdict when the calendar date rolls over, satisfying the ruling.

**3. Migration Path (`step_a_old_keys` & `prescreen`)**
- The `step_a_old_keys` function reconstructs the keys used by the previous version of the code (which used UTC dates).
- The window `k in (0, 1)` (today and yesterday UTC) is sufficient to cover the ~12-hour offset between UTC and ET.
- In `prescreen`, the recovery logic is correctly gated: `if rec is None and not time_sensitive(m)`. This ensures that time-sensitive moments are **never** recovered from old keys and must be re-evaluated for the new date.
- Recovered verdicts are stored in the `moved` dictionary and merged into the cache via `_cache_put`, ensuring they are found via the new key in subsequent runs.

**4. Test Coverage**
- `test_ruling_126_the_show_date_is_the_et_date` verifies the UTC $\rightarrow$ ET conversion (e.g., 00:30 UTC Nov 11 is Nov 10 ET).
- `test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved` comprehensively tests:
    - Recovery of non-time-sensitive verdicts from old UTC keys.
    - Rejection of time-sensitive verdicts from old keys.
    - Successful migration (writing under the new key).
    - Correctness of the date window.

### Findings

No [P0], [P1], or [P2] defects found. The implementation is precise and the tests are robust.

P1_OR_WORSE: 0