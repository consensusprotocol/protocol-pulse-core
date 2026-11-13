# qwen3.8-27b (qwen/qwen3.8-27b) 120 s finish=stop usage in 15937 / out 2764 usd~0.089 (upper-bound price)

# Audit: pp-selectid-1300 (Ruling 65)

## P0 Findings

**1. `pipeline/package.py` (approx. line 213-218 in diff): The "Fixed Caption" fallback can be sealed with failing gates.**
In `rewrite_alone`, if the model write for the caption fails (raising an exception or returning a failing verdict), the code falls through to the `fixed_caption` logic (lines 153-165). It constructs `pk3` with the fixed caption and runs `cheap3 = cheap_checks(...)`. However, it **does not check the result of `cheap3`** before returning `pk3`.
*   **Scenario:** The model write fails. The code generates the fixed caption. `cheap_checks` on this new package fails (e.g., due to a house style violation in the channel names, or a deterministic fidelity rule triggered by the specific title text). The code returns `pk3` (the package with the fixed caption) and `cheap3` (which contains violations).
*   **Consequence:** Back in the main loop (line 213), the check is `if not (fid["ok"] and cx["ok"]) or cheap:`. If `cheap3` has violations, `cheap` is truthy, so the loop breaks with `rec["why"]` set. **However**, look closely at the return value of `rewrite_alone` in the fallback path: it returns `pk3, fid3, cx3, cheap3, rec`.
    *   Wait, let's re-read the main loop logic at line 213:
        ```python
        if not (fid["ok"] and cx["ok"]) or cheap:
            rec["why"] = ...
            w_used = writes
            break
        ```
    *   If `cheap3` has violations, `cheap` is truthy. The loop breaks. The package `pk` is updated to `pk3` (line 204: `pk, fid, cx, cheap_t, rw = rewrite_alone(...)`).
    *   Does the loop *seal* the package? The `break` exits the `while` loop. The code after the loop (not shown in diff, but implied by "sealed inventory") likely checks `att["violations"]` or `rec["why"]`.
    *   **Crucial Check:** Does `att["violations"]` get updated with `cheap3`?
        *   Line 194: `att["violations"] = cheap + fid["violations"] + cx["violations"]` happens *before* `rewrite_alone`.
        *   Inside `rewrite_alone`, `att` is not modified.
        *   After `rewrite_alone` returns, `cheap` is updated to `cheap_t` (which is `cheap3`).
        *   But `att["violations"]` is **not** updated to include `cheap3`'s violations.
        *   If the downstream sealing logic relies on `att["violations"]` being empty to seal, it might seal a package where `cheap_checks` failed on the fixed caption, because `att["violations"]` still holds the *old* violations (which were only on the caption, and thus `lone_slot` was triggered).
        *   **Correction:** The `break` sets `rec["why"]`. If the sealing logic checks `rec["why"]` or `att["ok"]`, it might stop. But if it checks `att["violations"]` specifically, it sees the *old* violations.
        *   **More Critical:** Look at line 213 again. `if not (fid["ok"] and cx["ok"]) or cheap:`. If `cheap3` fails, we break. The package `pk` is now `pk3`. The `att` dict still has the *old* `violations`. If the final seal check is `if not att["violations"]: seal()`, it will seal `pk3` even though `cheap3` failed.
        *   **Verdict:** This is a **P0**. The fixed caption path does not update `att["violations"]` with the results of the gates run on the fixed caption. If the fixed caption fails `cheap_checks` (e.g., house style), the package may be sealed with a failing gate, violating Law 20/M2 (failed gate is a hard stop) and L-j (gates on bytes sent).

**2. `pipeline/package.py` (approx. line 158-160 in diff): The "Fixed Caption" verdict is hardcoded to `ok: True`.**
In the fallback path of `rewrite_alone`:
```python
one = {"deterministic": VF.check_deterministic(...),
       "verdict": {"ok": True, "violations": [], ...},
       ...}
```
The `verdict` is hardcoded to `ok: True`. The `deterministic` check is run, but its result is **not** checked for violations before merging.
*   **Scenario:** The fixed caption (title + channel names) triggers a deterministic fidelity violation (e.g., a number mismatch or a forbidden word in the channel name). `VF.check_deterministic` returns `ok: False`.
*   **Consequence:** `merge_fid` is called with `one` where `verdict.ok` is `True`. The merged `fid3` will have `verdict.ok` as `True` (assuming the other lines passed). The `deterministic` violations from `one` are merged into `det["violations"]`.
*   **Check:** `merge_fid` line 93: `det["ok"] = not det["violations"]`. So `fid3["deterministic"]["ok"]` will be `False`.
*   **Check:** `merge_fid` line 99: `ver["ok"] = measured and not ver["violations"]`. `ver["violations"]` comes from `v0` (old) and `v1` (new). `v1` is hardcoded to `[]`. So `ver["ok"]` remains `True`.
*   **Check:** `merge_fid` line 102: `ok=det["ok"] and ver["ok"]`. So `fid3["ok"]` will be `False`.
*   **Back to Main Loop (Line 213):** `if not (fid["ok"] and cx["ok"]) or cheap:`. `fid` is now `fid3`. `fid3["ok"]` is `False`. So the condition `not (fid["ok"] ...)` is `True`. The loop breaks.
*   **Result:** The package is **not** sealed. It is held.
*   **Re-evaluation:** This is **not** a P0 for sealing a bad package, because `fid3["ok"]` becomes `False`, triggering the break. However, it is a **P1** because the `verdict` is hardcoded to `ok: True` despite the deterministic layer failing. This creates a confusing state where `fid3["verdict"]["ok"]` is `True` but `fid3["ok"]` is `False`. It relies on the `deterministic` layer to catch the failure. If the deterministic layer is bypassed or has a bug, the verdict would incorrectly pass. But given the current code, it fails closed.

## P1 Findings

**3. `pipeline/package.py` (approx. line 194 in diff): `att["violations"]` is not updated after `rewrite_alone`.**
As noted in P0, `att["violations"]` is set *before* `rewrite_alone`. If `rewrite_alone` succeeds (caption passes), `att["violations"]` still contains the *old* caption violations.
*   **Scenario:** Caption fails. `rewrite_alone` succeeds. `pk` is updated to the new package. `fid` is updated to the merged fidelity. `cheap` is updated to the new cheap checks (which pass).
*   **Consequence:** `att["violations"]` still lists the old caption violation. If the sealing logic checks `att["violations]` to determine if the package is clean, it will see a violation and **reject** a valid package.
*   **Verdict:** This is a **P1** (Functional Bug). The package will likely be rejected even when the fix succeeded, because the audit trail (`att`) is stale.

**4. `pipeline/package.py` (approx. line 202 in diff): `lone_slot` logic on `cheap + fid["violations"]`.**
```python
slot = lone_slot(cheap + fid["violations"]) if cx["ok"] and fid.get("measured") else None
```
If `cheap` has a violation on the caption, and `fid` has a violation on the *takeaway*, `lone_slot` returns `None` (because slots are `{"caption", "takeaway"}`). The code proceeds to the old redo path. This is correct.
However, if `cheap` has a violation on the caption, and `fid` has *no* violations (but `fid["ok"]` is `False` for some other reason, e.g., `measured` is `False`), `lone_slot` is not called because `fid.get("measured")` is `False`. The code proceeds to the old redo path. This is correct (fail closed).

**5. `pipeline/package.py` (approx. line 150-152 in diff): Title Hold Logic.**
```python
if slot != "caption":
    rec["why"] = ...
    return pk, dict(fid, ok=False), ...
```
If the title fails the rewrite, it returns `pk` (the *original* package, not the one with the new title) and `fid` with `ok=False`.
*   **Consequence:** The main loop breaks. The package is held. This is correct per Ruling 65(c).

## P2 Findings

**6. `pipeline/package.py` (approx. line 176 in diff): Budget Fix.**
```python
total += 0 if med.get("replayed") or med.get("cached") else 1
```
This correctly implements the 12:00 budget rule.

**7. `pipeline/package.py` (approx. line 185 in diff): Cheap Check Bypass.**
```python
if cheap and lone_slot(cheap) is None:
    # redo
```
If `cheap` has violations, but they are all on the caption (`lone_slot` returns `"caption"`), the code does **not** redo immediately. It proceeds to paid gates.
*   **Risk:** If the paid gates (fidelity/context) also fail, the code will check `lone_slot(cheap + fid["violations"])`. If the paid gates fail on the *takeaway*, `lone_slot` returns `None`, and the old redo path runs. This is correct.
*   **Risk:** If the paid gates pass, but `cheap` failed on the caption, `lone_slot(cheap + [])` returns `"caption"`. `rewrite_alone` runs. This is correct.

## SHIP: No

**Reasons:**
1.  **P0:** The fixed caption path does not update `att["violations"]` with the results of the gates run on the fixed caption. If the fixed caption fails `cheap_checks`, the package may be sealed with a failing gate (if the sealing logic relies on `att["violations"]` being empty) or, more likely, the `break` condition `if not (fid["ok"] and cx["ok"]) or cheap:` will trigger, but `att` remains stale.
2.  **P1:** `att["violations"]` is not updated after a successful `rewrite_alone`. This will cause valid packages to be rejected because the audit trail still contains the old violations.

**Required Fixes:**
1.  In `rewrite_alone`, after determining the final `pk`, `fid`, `cx`, and `cheap`, update `att["violations"]` to reflect the new state.
2.  Ensure that if the fixed caption fails `cheap_checks`, the package is explicitly held and not sealed. The current `break` logic might handle this, but the stale `att` is a risk.
3.  Consider updating `att["violations"]` in the main loop after `rewrite_alone` returns, regardless of success/failure, to ensure the audit trail matches the final package state.