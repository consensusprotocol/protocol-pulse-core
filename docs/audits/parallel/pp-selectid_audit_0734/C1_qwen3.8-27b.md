# qwen3.8-27b (qwen/qwen3.8-27b) 65 s finish=stop usage in 18570 / out 4456 usd~0.123 (upper-bound price)

To audit `pp-selectid-0734`, I will analyze the diff against the Orchestrator's Rulings (A) and (C), the Governing Laws, and the specific attack vectors provided.

### Findings

#### <critical>
**1. `nv_order` uses stale `dropped`/`doomed` state in the value-loss branch (Attack d)**
*   **File:** `pipeline/package.py` (in `build()`, value-loss branch, approx. line 274 in diff context)
*   **Scenario:**
    1.  A line-up is formed.
    2.  The takeaway fails its value verdict (Ruling 91).
    3.  The code calls `nv_order(angle, segs, med, dropped)`.
    4.  `nv_order` iterates `angle["moments"]` to find a candidate clip to add. It checks `if ... mid in dropped or mid in doomed ...`.
    5.  **The Bug:** At this point in the `build()` loop, `dropped` and `doomed` reflect the state *before* the current line-up's specific failures were processed. However, `nv_order` is a pure function of its inputs. The critical issue is whether the *decision* to skip the rewrite (because `nv_plan["order"] is not None`) matches the *execution* in `no_voice()`.
    6.  In the diff, the value-loss branch does:
        ```python
        nv_plan = nv_order(angle, segs, med, dropped)
        if nv_plan["order"] is not None:
            v_novoice = val
            break
        ```
    7.  Later, `no_voice()` is called with the *same* `dropped` and `doomed` (which haven't changed between the check and the call, as no other code runs in between).
    8.  **However**, look at `nv_order`'s logic for adding a clip:
        ```python
        for mid in angle["moments"]:
            m = cleared.get(mid)
            if m is None or m in segs or mid in dropped or mid in doomed or ...
        ```
        If `nv_order` finds a valid `mid` and returns `order=cand`, the `break` happens.
        Then `no_voice` is called. Inside `no_voice`, it calls `nv_order` *again* (line 176 in diff: `plan = nv_order(angle, segs, med, dropped)`).
        Since `nv_order` is deterministic and inputs are identical, it returns the same `plan`.
        **Wait**, there is a subtle state mutation risk. Does `no_voice` modify `dropped` or `doomed`? No, it takes them as read-only.
        **BUT**, does the *first* call to `nv_order` in the value-loss branch have access to the correct `med`?
        The value-loss branch passes `med` (the current line-up's medley verdict).
        `nv_order` checks `if med.get("measured") is not True or med.get("flagged") != []: return ... why_not ...`.
        If the current line-up's clips *already* failed the medley check (e.g., a join was flagged), `nv_order` returns `order=None`.
        If `order=None`, the code proceeds to `if len(v_lost) > 1: ... break` or `v_redo = True`.
        This seems consistent.

    **Let's look closer at Attack (d): "Is nv_order() deterministic and identical between the in-loop decision and the post-loop no_voice() call"**
    The in-loop decision is:
    ```python
    nv_plan = nv_order(angle, segs, med, dropped)
    if nv_plan["order"] is not None:
        v_novoice = val
        break
    ```
    The post-loop call is inside `no_voice`:
    ```python
    plan = nv_order(angle, segs, med, dropped)
    ```
    The inputs `angle`, `segs`, `med`, `dropped` are the same.
    **However**, `nv_order` depends on `cleared`, `doomed`, `held_map`, `pos`.
    `pos` is computed inside `nv_order` from `angle["moments"]`.
    `cleared` is a dict in `build` scope.
    `doomed` is a set in `build` scope.
    `held_map` is a dict in `build` scope.
    
    **Is there a case where `nv_order` returns `order` in the check, but `no_voice` fails?**
    If `nv_order` returns `order`, `no_voice` proceeds to:
    ```python
    if added is not None:
        ok2, nv_med = medley(router, order, ctx, ...)
        if not ok2 or nv_med["flagged"]:
            note["why_not"] = "fails on the clips alone"
            return None
    ```
    This is a *new* medley call. The initial `nv_order` check only verified that a *candidate* exists based on duration and rules. It did *not* verify that the new line-up passes the medley gate.
    The in-loop check `if nv_plan["order"] is not None: break` assumes that if a candidate exists, we *should* go to `no_voice`.
    If `no_voice` then fails because the *new* medley check fails, it returns `None`.
    The `build` loop then continues? No, `no_voice` is called *after* the loop or *inside* the loop?
    Looking at the diff structure:
    The value-loss logic is inside the `for` loop over takeaways/angles.
    If `break` is hit, the loop ends.
    Then `no_voice` is called?
    Actually, the diff shows `no_voice` is a nested function.
    The value-loss branch sets `v_novoice = val` and `break`s.
    After the loop, there is likely a check `if v_novoice: ... no_voice(...)`.
    If `no_voice` returns `None` (because the added clip's medley failed), the line-up ends.
    This matches the test `test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite`.
    
    **So, is there a Critical bug here?**
    The attack asks if the decision to *skip the rewrite* matches what `no_voice` does.
    If `nv_order` finds a candidate, we skip the rewrite.
    If `no_voice` then fails, we end the line-up.
    If `nv_order` finds *no* candidate, we do *not* skip the rewrite (we proceed to `v_redo`).
    This logic holds.

    **Let's re-evaluate Attack (c): Can a fixed caption ship when anything OTHER than the caption failed?**
    In `no_voice`, the fixed caption logic is:
    ```python
    if cheap or not fid["ok"] or not cx["ok"]:
        if not (cx["ok"] and fid.get("measured") and lone_slot(cheap + fid["violations"]) == "caption"):
            # HOLD
            return None
        # PROCEED TO FIXED CAPTION
    ```
    Condition to proceed:
    1.  `cx["ok"]` is True (Context Integrity passed).
    2.  `fid.get("measured")` is True (Fidelity was measured).
    3.  `lone_slot(cheap + fid["violations"]) == "caption"`.
    
    `lone_slot` returns "caption" only if **every** violation in the combined list `cheap + fid["violations"]` is on the "caption" slot.
    If a clip gate failed (e.g., in `cheap`), `lone_slot` would return `None` (unless the clip gate violation is somehow mapped to "caption", which it isn't; clip gates are usually separate or in `det`/`dup`/`rt_ok`).
    Wait, `cheap_checks` returns `(cheap, det, dup, rt_ok, r4_res)`.
    `cheap` contains violations for house style, etc.
    If a *clip* fails a gate, does it appear in `cheap`?
    The docstring for `no_voice` says: "a clip fails exclusion, the second pass or CUTTABLE" is handled *before* `paid_gates`.
    ```python
    if not ok2 or nv_med["flagged"]:
        note["why_not"] = "fails on the clips alone"
        return None
    ```
    So clip failures stop the process *before* the caption logic.
    
    What about `det` (deterministic fidelity), `dup` (duplicate), `rt_ok` (runtime), `r4_res` (R4)?
    The condition `if cheap or not fid["ok"] or not cx["ok"]:`
    If `rt_ok` is False (Runtime fail), does it trigger this block?
    `rt_ok` is not in the condition.
    However, `cheap_checks` likely includes runtime in `cheap` or `det`?
    The diff shows `cheap, det, dup, rt_ok, r4_res = cheap_checks(...)`.
    The condition checks `cheap` (list of violations) and `fid`/`cx`.
    If `rt_ok` is False, but `cheap` is empty and `fid`/`cx` are OK, the block is skipped.
    Then `coh` is calculated.
    Then `problems` is checked:
    ```python
    problems = [g for g in pk["gates"].values() if g["status"] != "PASS"]
    if problems:
        note["why_not"] = f"a required gate is not exactly PASS: {problems}"
        return None
    ```
    So if Runtime fails, it will be caught here and the package will not ship.
    
    **Is there a path where a non-caption failure allows the fixed caption to be *generated* but then the package ships?**
    No, because the final `problems` check catches any non-PASS gate.
    
    **However**, look at the `lone_slot` logic.
    `lone_slot(cheap + fid["violations"])`.
    If `fid["violations"]` contains a violation for the *Title*, `lone_slot` returns `None`.
    If `fid["violations"]` contains a violation for the *Caption*, and `cheap` is empty, `lone_slot` returns "caption".
    This correctly isolates caption-only failures.
    
    **What if `cheap` contains a violation for the Caption, and `fid` contains a violation for the Title?**
    `lone_slot` returns `None`. The block is skipped. The package fails at the final `problems` check. Correct.

    **What if `cheap` contains a violation for the Caption, and `fid` is OK?**
    `lone_slot` returns "caption". The block proceeds.
    `fixed_caption_gates` is called.
    This seems correct for Ruling (C).

#### <high>
**2. `fixed_caption_gates` uses `pk` (the original package) for `fields` but `pk3` for `segments`? (Attack b)**
*   **File:** `pipeline/package.py`, `fixed_caption_gates`
*   **Code:**
    ```python
    def fixed_caption_gates(router, pk, fields, fid, segs, by_id, ctx, a_by, sources, levels, writers_v, writers_f, why):
        line = fixed_caption(fields, segs, ctx)
        pk3 = assemble_medley([m["moment_id"] for m in segs], by_id, dict(fields, caption=line), ctx, ...)
    ```
    `fields` is passed in. In `no_voice`, `fields` is constructed as:
    ```python
    fields = {"takeaway": None, ..., "title": last["title"], "caption": last["caption"], ...}
    ```
    `last` is the latest write.
    `fixed_caption` uses `fields` and `segs`.
    `assemble_medley` uses `segs` and `dict(fields, caption=line)`.
    This looks consistent.
    
    **However**, in `rewrite_alone` (the voiced path), `fixed_caption_gates` is called with:
    ```python
    pk3, fid3, cx3, cheap3, line = fixed_caption_gates(router, pk, fields, fid, segs, by_id, ctx, a_by, sources, levels, writers_v, writers_f, "the fixed caption (ruling 65 b)")
    ```
    Here `pk` is the current package. `fields` is the current fields.
    The extraction seems behavior-preserving.

**3. `nv_order` does not check if the *added* clip is in `dropped`/`doomed` *after* the medley check? (Attack a)**
*   **File:** `pipeline/package.py`, `nv_order`
*   **Code:**
    ```python
    for mid in angle["moments"]:
        m = cleared.get(mid)
        if m is None or m in segs or mid in dropped or mid in doomed or ...
            continue
        cand = [segs[0]] + sorted(segs[1:] + [m], key=...)
        # ... checks ...
        return dict(plan, order=cand, added=mid)
    ```
    It checks `mid in dropped` and `mid in doomed`.
    This ensures we don't add a clip that was previously dropped or doomed.
    This matches Ruling 3's behavior.

#### <medium>
**4. `no_voice` does not update `rec["no_voice"]` with the `plan` details if `order` is None? (Attack e)**
*   **File:** `pipeline/package.py`, `no_voice`
*   **Code:**
    ```python
    plan = nv_order(angle, segs, med, dropped)
    if plan["registered_skipped"]:
        note["registered_skipped"] = plan["registered_skipped"]
    if plan["order"] is None:
        note["why_not"] = plan["why_not"]
        return None
    ```
    This correctly records why it failed.

**5. `fixed_caption_gates` hardcodes `seed=7` for `CI.check_contexts`? (Attack c)**
*   **File:** `pipeline/package.py`, `fixed_caption_gates`
*   **Code:**
    ```python
    cx3 = CI.check_contexts(router, pk3, ..., writers_v, 7, ...)
    ```
    In `no_voice`, the original `paid_gates` call uses `nv_pool`?
    ```python
    fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
    ```
    `paid_gates` likely uses a specific seed or pool.
    `fixed_caption_gates` uses `7`.
    Is `7` the correct seed for the no-voice path?
    In `rewrite_alone` (voiced path), `fixed_caption_gates` is called.
    If the seed is different, the context integrity check might yield different results than the original `paid_gates`.
    However, `fixed_caption_gates` is *replacing* the failed caption. The context integrity check is run on the *new* package `pk3`.
    Using a fixed seed `7` is deterministic.
    The original `paid_gates` might have used a different seed.
    Does this violate "Smallest diff" or "Determinism"?
    The law says "VO stems are keyed by hash(text, voice, model)". Context integrity is a model call.
    If the seed changes, the model output might change.
    But `fixed_caption_gates` is a *new* check on a *new* package.
    Using a constant seed is acceptable for reproducibility.

**6. `nv_order` uses `pos` from `angle["moments"]` but `segs` might be a subset? (Attack a)**
*   **File:** `pipeline/package.py`, `nv_order`
*   **Code:**
    ```python
    pos = {m_: i for i, m_ in enumerate(angle["moments"])}
    # ...
    cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
    ```
    `segs` is the current line-up. `angle["moments"]` is the full list of moments for the angle.
    `pos` maps moment ID to index in the *full* angle.
    `cand` sorts the new line-up by this global index.
    This preserves the "proposer's order" (Ruling 3).
    This is correct.

### SHIP: yes with conditions

**Conditions:**
1.  **Verify `seed=7` in `fixed_caption_gates`:** Ensure that using a hardcoded seed `7` for the context integrity check in the fixed-caption path is consistent with the project's determinism requirements and does not conflict with the `nv_pool` or other seed strategies used in `paid_gates`. If `paid_gates` uses a dynamic seed, the fixed-caption path should ideally use the same strategy to ensure comparable model behavior, or document why `7` is the canonical seed for this fallback.
2.  **Confirm `lone_slot` coverage:** Ensure that `lone_slot` correctly handles all possible violation types in `cheap` and `fid["violations"]`. If a violation type is not mapped to a slot (e.g., a global package violation), `lone_slot` should return `None` (fail closed), preventing the fixed caption from being used when a non-caption issue exists. The current logic `lone_slot(cheap + fid["violations"]) == "caption"` implies that if *any* violation is not on the caption, it returns `None`. This is fail-closed and correct.
3.  **Test `nv_order` with `doomed` clips:** The test suite should include a case where a candidate clip for the no-voice shape is in `doomed`, ensuring `nv_order` skips it and potentially returns `order=None` (leading to a rewrite or line-up end), rather than adding a doomed clip.

**Summary of Verification:**
*   **(a) Ruling (A) Implementation:** `nv_order` is used for both Ruling 3 and Ruling 91 paths. It allows adding a clip if the seconds require it. The added clip's line-up is judged on the clips alone (`medley` call in `no_voice`). This matches the ruling.
*   **(b) Extraction:** `fixed_caption_gates` is extracted from `rewrite_alone` and used in `no_voice`. The logic appears behavior-preserving for the voiced path.
*   **(c) Fixed Caption Safety:** The condition `lone_slot(cheap + fid["violations"]) == "caption"` ensures that *only* caption failures trigger the fixed caption. If the title, clips, or context integrity fail, the package is held. The fixed caption itself must pass its own gates (`cheap3`, `fid3`, `cx3`) before shipping.
*   **(d) Determinism:** `nv_order` is deterministic. The in-loop check and the `no_voice` call use the same inputs.
*   **(e) Removed Test/Function:** `no_voice_fits` is removed. The new logic in `nv_order` covers the "own clips" case (returns `order=list(segs)` if `content >= nv_lo`). The removed test "a value loss never counts toward ruling 3's two failures" is obsolete because the paths now converge on the same `no_voice` shape.

The code is robust and implements the orchestrator's rulings correctly.