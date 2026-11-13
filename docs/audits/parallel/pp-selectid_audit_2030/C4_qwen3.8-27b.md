# qwen3.8-27b (qwen/qwen3.8-27b) 162 s finish=stop usage in 57948 / out 4352 usd~0.239 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## Feature: pp-selectid-2030

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the `ly_shape` slot/record bookkeeping and the `takeaway_budget` intersection logic. I missed or under-weighted the following:

1.  **The `runtime_s_estimate` KeyError (Grok P0):** I assumed `_package` or `assemble_medley` handled the runtime calculation. Grok correctly identified that `cheap_checks` reads `pk["runtime_s_estimate"]` unconditionally, but the diff provided for `_package` (lines 188-207) **does not show** the assignment `pk["runtime_s_estimate"] = runtime(...)`. While the consensus notes this was refuted by the *actual* code (which I cannot see fully, only the diff), the diff *as provided* is ambiguous. However, looking closely at `assemble_medley` (line 242), it calls `_package`. If `_package` doesn't set it, it's a P0. The consensus says it *does* set it. I will trust the consensus refutation but flag that the diff snippet for `_package` is incomplete regarding this key.
2.  **The `NoBridgeFits` Pre-Check (Grok P1 / Qwen P0-2):** I analyzed the budget intersection but missed the critical control flow change in `write_takeaway` (lines 501-506). The code now *raises* `NoBridgeFits` **before** the model call if `bridge_budget` returns `None`. This prevents the "infinite loop of rewrites" scenario I hypothesized in Cycle 1. This is a significant improvement I failed to credit in my initial read.
3.  **CUTTABLE/Second-Pass Pre-Filtering (Consensus Item 13):** I did not trace the new `ThreadPoolExecutor` block in `build()` (lines 707-717) that runs `truth_for` and checks `cuttable` *before* the angle proposer sees the moments. This is a major architectural change to prevent paying for verdicts on doomed clips. I missed this entirely in Cycle 1.
4.  **Vendor Cost Reporting (Providers.py):** I did not audit the new `_reported` and `_num` functions in `providers.py` (lines 1071-1079) or the ledger updates in `Router._settle` (lines 1111-1117). This is new code that could corrupt the spend ledger if `usd_reported` is malformed.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My Position | Reasoning |
| :--- | :--- | :--- |
| **Grok P0: `runtime_s_estimate` missing** | **Disagree (Refuted)** | The consensus states `_package` sets it. The test `test_no_intro_and_one_takeaway_after_the_last_clip` (line 1738) asserts its value. If the test passes, the key exists. The diff snippet for `_package` is likely truncated in the view I have, but the test evidence is strong. |
| **Grok P1: `None` in redo string** | **Disagree (Fixed)** | The `NoBridgeFits` exception (line 503) is raised *before* the model call. If no bridge fits, the line-up is dropped/re-lined, not rewritten. The redo path (line 856) only executes if a write *was* made and failed cheap checks. In that case, `takeaway_budget` is called with the *written* bridge text (`other=written`), so the budget is concrete, not `None`. |
| **Grok P2: Canon for text comparison** | **Disagree** | `ly_shape` and `line_problems` compare the package's *own* internal bytes (VO line vs. Record). These are not transcripts vs. locked text; they are consistency checks on the same object. `canon` is for semantic equivalence across different sources. Exact match is correct here. |
| **Qwen P0-2: Budget Intersection Empty** | **Disagree (Fixed)** | `bridge_budget` (line 112) iterates `n` from 12 down to 3. It returns the *largest* `n` where the intersection is non-empty. If no `n` works, it returns `None`, triggering `NoBridgeFits`. The "silent fallback to 12-word budget" bug is gone. |
| **GLM P0-1: `ly_shape` join mapping** | **Agree (Downgraded to P2)** | The logic in `ly_shape` (line 577) `type(a) is int and 0 < a < n_clips` correctly filters out the `intro` slot (which is not in `bridges_after_clip` for the mid-join case, or is handled via `vo["intro"]`). The "two producers, two conventions" issue is mitigated because `assemble_medley` is the *only* producer of medley packages in this codebase. The `after_clip: 0` convention is internal to `assemble_medley` and `ly_shape` agrees on it. |

## 3. NEW FINDINGS FROM THIS REVIEW

### P1: `bridge_budget` does not account for the *Takeaway* minimum in the intersection check
**File:** `pipeline/package.py`, `bridge_budget()` (lines 112-125)

`bridge_budget` calls `takeaway_budget(content_s, w(LY_BRIDGE_MIN_WORDS))` and `takeaway_budget(content_s, w(n))`.
`takeaway_budget` returns `(lo, hi)` for the *takeaway* words.
The intersection check is: `max(short[0], long_[0]) <= min(short[1], long_[1])`.
This ensures there is a *takeaway* length that works for *both* the shortest bridge and the longest allowed bridge.
**However**, the writer is asked for a bridge of *at most* `n` words. The writer might write a bridge of `n` words. The takeaway budget `long_` was calculated assuming a bridge of `n` words. The takeaway budget `short` was calculated assuming a bridge of `LY_BRIDGE_MIN_WORDS` (3) words.
If the writer writes a bridge of `n` words, the takeaway must be in `long_`.
If the writer writes a bridge of 3 words, the takeaway must be in `short`.
The intersection ensures that *some* takeaway length works for *both* extremes.
**But does it ensure that *any* bridge length between 3 and `n` works?**
`takeaway_budget` is linear in the bridge words (fixed cost increases linearly). The range of valid takeaway words shrinks linearly as bridge words increase.
If the intersection of the *extremes* (3 words and `n` words) is non-empty, is the intersection of *any* intermediate bridge length non-empty?
Yes, because the valid takeaway range is a contiguous interval that shifts left and shrinks as bridge words increase. If the interval for 3 words and the interval for `n` words overlap, all intermediate intervals (which are between them) must also overlap with at least one of them, and thus with each other?
Actually, let $T(b)$ be the valid takeaway range for bridge length $b$. $T(b)$ is $[L(b), H(b)]$.
$L(b)$ is non-decreasing in $b$. $H(b)$ is non-increasing in $b$.
We check if $T(3) \cap T(n) \neq \emptyset$.
Does this imply $T(b) \neq \emptyset$ for all $b \in [3, n]$?
Yes. If $T(3) \cap T(n) \neq \emptyset$, then there exists a takeaway length $t$ such that $t \in T(3)$ and $t \in T(n)$.
Since $L(b)$ is non-decreasing, $L(3) \le L(b) \le L(n)$.
Since $H(b)$ is non-increasing, $H(3) \ge H(b) \ge H(n)$.
If $t \in T(3)$, $t \ge L(3)$. If $t \in T(n)$, $t \le H(n)$.
So $L(3) \le t \le H(n)$.
For any $b \in [3, n]$, $L(b) \le L(n) \le t$ (wait, $L(n)$ is the max lower bound).
Actually, $L(b) \le L(n)$ is false. $L(b)$ increases with $b$. So $L(3) \le L(b) \le L(n)$.
And $H(3) \ge H(b) \ge H(n)$.
We know $L(3) \le H(n)$ (intersection non-empty).
Does $L(b) \le H(b)$ for all $b$?
$L(b) \le L(n)$. $H(b) \ge H(n)$.
We know $L(n) \le H(n)$? No, we know $L(3) \le H(n)$.
It is possible that $L(n) > H(n)$ (i.e., $T(n)$ is empty) but $T(3) \cap T(n)$ is empty?
If $T(n)$ is empty, `takeaway_budget` returns `None`. The code checks `if long_ is not None`. So if $T(n)$ is empty, it skips `n`.
The code iterates `n` from 12 down. It finds the *largest* `n` such that `takeaway_budget(content, w(n))` is not `None` AND intersects with `takeaway_budget(content, w(3))`.
If `takeaway_budget(content, w(n))` is not `None`, then $L(n) \le H(n)$.
If it intersects with $T(3)$, then $L(3) \le H(n)$ and $L(n) \le H(3)$.
Since $L(b)$ is monotonic and $H(b)$ is monotonic, for any $b \in [3, n]$, $L(b) \le L(n) \le H(3)$ and $H(b) \ge H(n) \ge L(3)$.
This does *not* guarantee $L(b) \le H(b)$.
Counter-example:
$T(3) = [10, 20]$.
$T(12) = [15, 25]$.
Intersection: $[15, 20]$. Non-empty.
$T(8) = [12, 14]$.
$L(8) = 12, H(8) = 14$. $12 \le 14$. OK.
What if $T(8) = [18, 19]$?
$L(8) = 18, H(8) = 19$. OK.
The function `takeaway_budget` returns `None` if `lo > hi`. So if `T(b)` is empty, it returns `None`.
The code only considers `n` where `long_` is not `None`.
So for the chosen `n`, $T(n)$ is non-empty.
For any $b < n$, is $T(b)$ non-empty?
$L(b) \le L(n)$. $H(b) \ge H(n)$.
Since $L(n) \le H(n)$, and $L(b) \le L(n)$ and $H(b) \ge H(n)$, it follows that $L(b) \le H(b)$.
So yes, if $T(n)$ is non-empty, all $T(b)$ for $b < n$ are non-empty.
**Conclusion:** The logic is sound. No P1 here.

### P2: `medley_content_range` does not account for the *Bridge* in the `hi` bound correctly?
**File:** `pipeline/package.py`, `medley_content_range()` (lines 103-109)

`hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)`
`extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)`
This calculates the max clip seconds such that the *minimum* takeaway (8 words) and the *maximum* bridge (12 words) fit in 70s.
This is correct for the *lineup* selection. The lineup must be short enough to allow the *worst case* VO (max bridge, min takeaway? No, min takeaway is the *shortest* VO, so it leaves the *most* room for clips).
Wait.
Runtime = Clips + VO + Tail.
We want Runtime <= 70.
Clips <= 70 - Tail - VO.
To find the *max* Clips, we need the *min* VO.
Min VO = Min Takeaway (8 words) + Min Bridge (3 words)?
No, the bridge is *optional*.
If no bridge, Min VO = 8 words.
If bridge, Min VO = 8 + 3 = 11 words.
`medley_content_range` is called with `n_bridges=0` by default in `lineup_for` (line 384: `crange or medley_content_range()`).
So it assumes *no bridge* for the lineup selection.
If a bridge is later added, the runtime increases.
Does `lineup_for` ensure the clips are short enough to accommodate a bridge?
No. `lineup_for` selects clips based on `medley_content_range(n_bridges=0)`.
If the clips are at the `hi` bound (51.5s), and a bridge is added (12 words), the runtime becomes:
$51.5 + (12/2.5 + 1.0) + (8/2.5 + 1.0) + 14.30 = 51.5 + 5.8 + 4.2 + 14.30 = 75.8s$.
This exceeds 70s.
**However**, `write_takeaway` is called *after* the lineup is fixed.
If a bridge is flagged, `write_takeaway` calls `bridge_budget`.
`bridge_budget` checks if *any* bridge length fits.
If the clips are 51.5s, `bridge_budget` will likely return `None` (as shown in the test `test_a_flagged_join_no_bridge_can_fill_drops_the_line_up_before_any_write`).
So the system *fails closed*: it drops the line-up.
This is correct behavior (fail closed), but it means that line-ups near the `hi` bound of `medley_content_range(n_bridges=0)` are *unusable* if a bridge is needed.
Is this a bug?
The law says: "The packaging estimate stays inside 60-70 s".
If a bridge is needed, the clips must be shorter.
`lineup_for` does not know if a bridge will be needed.
It picks the best clips that fit *without* a bridge.
If a bridge is needed, it re-lines.
This is acceptable. It is not a bug, but it is a potential inefficiency (wasted medley calls).
**Verdict:** P2 (Inefficiency, not correctness).

### P2: `proof_ly.py` `meter` function monkey-patches `router._settle`
**File:** `tests/package/proof_ly.py`, `meter()` (lines 1252-1267)

`router._settle = _settle`
This replaces the router's settle method.
If `Router._settle` is called from multiple threads, is the monkey-patch thread-safe?
The original `_settle` uses `self._lock()`.
The new `_settle` calls `settle(key, backend, usage, usd, role)` (the original) and then updates `tot` under `lock`.
This seems safe.
However, `router._settle` is an instance method. Replacing it on the instance is fine.
**Verdict:** P2 (Fragile, but works).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Budget Logic** | P0 | P2 | `NoBridgeFits` pre-check and `bridge_budget` intersection logic are sound. |
| **Loop Control** | P1 | P2 | Pre-filtering of CUTTABLE/Second-Pass prevents wasted calls. `NoBridgeFits` handles the bridge case. |
| **`ly_shape`** | P1 | P2 | Slot/record bookkeeping is consistent. |
| **Providers/Ledger** | N/A | P2 | New cost reporting is correct but fragile. |
| **Tests** | P1 | P2 | Tests cover the new logic well. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/package.py:103` (`medley_content_range`):** The lineup selection does not account for the potential bridge cost. Line-ups near the upper bound of clip seconds will fail `bridge_budget` if a bridge is flagged, causing a re-line. This is fail-closed but inefficient. Consider passing `n_bridges=1` to `medley_content_range` in `lineup_for` to be conservative, or accept the re-line cost.
2.  **`tests/package/proof_ly.py:1252` (`meter`):** Monkey-patching `router._settle` is fragile. If the `Router` class changes its internal structure, this will break. Consider adding a proper hook or callback to `Router` for spend tracking.
3.  **`pipeline/providers.py:1071` (`_num`):** The check `math.isfinite(x)` is good, but `x >= 0` might reject valid negative adjustments (if any). Currently, costs are positive, so this is fine.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of `NoBridgeFits` and the pre-check in `write_takeaway` (lines 501-506) is the most critical change. It prevents the system from paying for model calls that are guaranteed to fail the runtime gate, and it cleanly handles the "no bridge fits" case by re-lining the clips. This transforms a potential infinite loop or wasted spend into a deterministic, fail-closed path.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Verify that `_package` (or `assemble_medley`) indeed sets `pk["runtime_s_estimate"]`. The diff snippet is ambiguous, but the test evidence suggests it does. If it does not, this is a P0.
2.  Monitor the re-line rate. If a high percentage of line-ups are re-lined due to `NoBridgeFits`, consider adjusting `medley_content_range` to be more conservative (accounting for a bridge).
3.  Ensure the `Router` class is stable, as `proof_ly.py` monkey-patches it.