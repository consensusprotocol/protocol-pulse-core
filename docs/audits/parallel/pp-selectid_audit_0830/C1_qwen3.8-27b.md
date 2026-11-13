# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 8762 / out 1502 usd~0.049 (upper-bound price)

I have reviewed the diff for `pipeline/package.py` and `tests/package/test_medley.py` against the governing laws and the specific instructions for Ruling 54 / Proposal 1.

### Findings

**P0: None**
No critical violations of the Governing Laws or the specific Ruling 54 constraints were found. The implementation correctly fails closed (returns `None`) if a line-up cannot be formed, and it does not bypass any existing gate logic.

**P1: None**
The logic for `pool_fill` and `placement` appears sound.
1.  **Line-up Rules:** `pool_fill` calls `lineup_for` with the extended list. Since `lineup_for` is the single source of truth for rules (one per channel, short clip last, seconds range, etc.), and it is called unchanged, all rules apply to the pool-filled line-up.
2.  **Ordering:** The code constructs `ext = dict(angle, moments=own + rest)`. `own` preserves the angle's original order. `rest` is appended. `lineup_for` prefers the proposer's earliest moments (lowest sum of play positions). This ensures the angle's own clips are prioritized and kept in their relative order, with pool clips filling the remaining slots (typically at the end, or swapped in if necessary to satisfy rules like "short clip last").
3.  **Scope:** The fill is triggered only when `n_lineup == 0` (the angle's own moments formed *no* line-up). It does not run for re-lines after a drop (which are handled by the existing Ruling 41 swap logic later in the loop).
4.  **Dropped/Doomed:** `pool_fill` accepts a `dropped` parameter and passes it to `lineup_for`. The `rest` list is built from `pool.values()`. It is critical that `pool` (the `cleared` dict passed to `build`) does *not* contain dropped or doomed moments. Looking at `build`, `cleared` is the set of moments that passed the second pass. `dropped` and `doomed` are separate sets used to filter *within* the lineup logic or for subsequent swaps. The `pool_fill` call passes `frozenset(dropped | doomed)` to `lineup_for`. However, `pool_fill` itself iterates over `pool.values()` to build `rest`. If `pool` contains moments that are in `dropped` or `doomed`, they would be added to `rest` and then passed to `lineup_for`. `lineup_for` will reject them if they are in the `dropped` set. This is safe (fail-closed), but slightly inefficient. More importantly, does `cleared` contain `doomed` moments? `doomed` usually refers to moments that failed a specific check *after* being cleared, or are marked for exclusion. If `cleared` is the input to `build`, and `doomed` is a subset of it, then `pool_fill` might offer doomed moments to the model or lineup. However, `lineup_for` will reject them. The prompt generation (`clips = ...`) iterates over `cleared`. If `doomed` moments are in `cleared`, they are shown to the model. This is existing behavior, not changed by this diff. The diff only adds `pool_fill` logic. `pool_fill` uses `cleared` as the pool. If `cleared` contains doomed moments, they are in the pool. `lineup_for` filters them out. This is consistent with existing behavior.

**P2: Minor Observation on `placement` Logic**
In `placement(m)`:
```python
if not ((m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True):
    lim.append("cannot open (never the hook)")
```
This logic states that a clip *cannot open* if it does NOT have (hook eligibility OK AND hook onset pass).
Conversely, a clip *can open* if it HAS (hook eligibility OK AND hook onset pass).
This matches the rule: "the hook can open (hook eligibility + the G17a onset measure)".
The prompt tells the model: "a clip marked 'cannot open' is never the hook".
This is consistent.

**P2: Test Coverage**
The tests cover:
1.  An angle that forms no line-up is completed from the pool.
2.  The proposer is told placement limits.
3.  The build records `pool_filled` and judges the line-up.
4.  Nothing to add gives `None`.
These are good. One edge case not explicitly tested: what if the pool is empty? `rest` would be empty, `pool_fill` returns `(None, None)`. This is handled.

**P2: "First Line-up Only" Constraint**
The Ruling says: "complete it from the whole cleared pool... first line-up only."
The code:
```python
if segs is None and n_lineup == 0:    # PROPOSAL 1: the angle's own moments form not even its
    segs, filled = pool_fill(angle, cleared, frozenset(dropped | doomed))   # FIRST line-up: the
```
`n_lineup` is the count of line-ups formed for this angle so far. If `n_lineup == 0`, it means no line-up has been formed yet from the angle's own moments. This is the "first line-up" attempt. If a line-up *was* formed (`n_lineup > 0`), this block is skipped. This correctly implements "first line-up only".

**P2: "Angle's Play Order Kept"**
`pool_fill` appends `rest` to `own`. `lineup_for` prefers the proposer's earliest moments. This keeps the angle's own moments in their relative order and prioritizes them. The added clips are placed after them (or swapped in if rules require, e.g., short clip last). This is consistent with "the angle's play order kept".

**P2: "Every Line-up Rule Unchanged"**
`lineup_for` is called with the same parameters (except the extended `moments` list). The rules inside `lineup_for` are unchanged. This is consistent.

**P2: "Proposer is Told Each Clip's Seconds and Placement Limits"**
The `clips` string in `build` now includes `placement(m)`. This tells the model the limits. This is consistent.

### SHIP: yes

The diff correctly implements Ruling 54 / Proposal 1. It fails closed, respects the "first line-up only" constraint, keeps the angle's play order, applies all line-up rules via `lineup_for`, and informs the proposer of placement limits. The tests verify the key scenarios. No P0 or P1 issues found.