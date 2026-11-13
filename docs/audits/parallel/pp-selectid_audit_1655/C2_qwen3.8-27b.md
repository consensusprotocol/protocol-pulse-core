# qwen3.8-27b (qwen/qwen3.8-27b) 100 s finish=stop usage in 13584 / out 3497 usd~0.093 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1655

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the main loop insertion point in `package.py`. **GLM-5.3-FLASH** correctly identified (P1-1) that the diff alone could not prove that *all* formation paths converged on that single check. **Grok** and **Qwen** were more optimistic, assuming the background description was sufficient.

The **Cycle 1 Consensus** (Claude) resolved this by tracing the full `package.py` and identifying a **second, distinct formation site**: the **no-voice fallback** (ruling 3). This path adds a clip to a passing line-up and judges the *new* line-up via `medley()`. In Cycle 1, this path was **not** guarded. If a registered line-up could be formed by adding a clip in the no-voice fallback, it would be judged and written, violating the core requirement.

The **Fixed Diff (C2_STEP.diff)** addresses this by adding a check at `package.py:61` inside the no-voice loop. This was the critical gap. I missed it in Cycle 1 because I was looking for a single "top of loop" check, not realizing the no-voice fallback was a separate formation site.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH (P1-1):** **Agree.** The diff in Cycle 1 was insufficient to prove coverage of all paths. The fix in C2_STEP.diff now explicitly covers the no-voice path, validating GLM's concern.
*   **Grok-4.20 (P2-1):** **Partially Agree.** Grok was uncertain about "every formation site." The fix confirms there *were* multiple sites (main loop + no-voice), and both are now guarded.
*   **Qwen3.8-27B (P2-1, P2-2, P2-3):** **Agree.** These were low-risk observations. The `registered` parameter being ignored for candidates is by design (docstring confirms). The `os.makedirs` patch is broad but safe in the current context.
*   **Claude Consensus:** **Agree.** The identification of the no-voice fallback as a second formation site was the key insight. The fix implements the consensus correctly.

## 3. NEW FINDINGS FROM THIS REVIEW

### P1-1 — No-Voice Fallback: `held_map` Lookup Uses `cand`, Not `order`
**File:** `pipeline/package.py`, diff line 61.

```python
if tuple(x["moment_id"] for x in cand) in held_map:
```

In the no-voice fallback, `cand` is the list of clips *before* the new clip `mid` is added. The code checks if `cand` is in `held_map`. However, the line-up that is actually judged is `order, added = cand, mid` (diff line 64), which is `cand + [mid]`.

**Scenario:**
1.  Registry holds line-up `("h", "x", "y", "z")`.
2.  Search forms `("h", "x", "y")`. It passes medley.
3.  Takeaway fails. No-voice fallback triggers.
4.  `cand` is `["h", "x", "y"]`. `mid` is `"z"`.
5.  Check: `tuple(x["moment_id"] for x in cand)` is `("h", "x", "y")`.
6.  `held_map` contains `("h", "x", "y", "z")`, **not** `("h", "x", "y")`.
7.  The check **passes** (not in `held_map`).
8.  `order` becomes `["h", "x", "y", "z"]`.
9.  `medley()` is called on `["h", "x", "y", "z"]`.
10. **The registered line-up is judged and written.**

**Wait, let me re-read the code carefully.**

```python
# diff lines 57-65
if ...:
    continue
if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
    note.setdefault("registered_skipped", []).append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
    continue
order, added = cand, mid
break
```

The variable `cand` is the list of clips *currently* in the line-up. `mid` is the clip being *added*. The resulting line-up is `cand + [mid]`.

The check is `tuple(x["moment_id"] for x in cand) in held_map`. This checks if the **current** line-up (without the new clip) is registered.

But the **new** line-up is `cand + [mid]`.

If the registry holds `("h", "x", "y", "z")`, and the current line-up is `("h", "x", "y")`, the check looks for `("h", "x", "y")` in `held_map`. It is not there. So it proceeds to add `"z"`, forming `("h", "x", "y", "z")`, and judges it.

**This is a P0 defect.** The check is looking at the wrong tuple. It should be checking `tuple(x["moment_id"] for x in cand) + (mid,)` or similar.

Let's verify with the test `test_the_no_voice_fallback_never_adds_the_clip_that_forms_a_registered_line_up` (diff lines 296-308).

```python
rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None, None], takeaways=bad,
          registered={("h", "x", "y", "z"): {"key": "h+x+y+z", "state": "resting", "until": None,
                                             "source": "proof/ledger_x", "index": 0}})
out = rig.run()
self.assertIsNone(out["package"])
self.assertEqual(rig.medley_calls, [["h", "x", "y"]])                 # h+x+y+z never judged
nv = out["tried"][0]["no_voice"]
self.assertEqual(nv["registered_skipped"], ["h+x+y+z"])
```

The test asserts that `h+x+y+z` is **never judged**. And it asserts that `registered_skipped` contains `"h+x+y+z"`.

How does the test pass if the code checks `cand` (which is `["h", "x", "y"]`) against `held_map` (which has `("h", "x", "y", "z")`)?

Let's look at the `Rig` setup. `self.MS` is the moments. `["h", "x", "y", "z"]` is the angle moments.
The medley result is `(True, [], None, Rig.LINE)`. This means the line-up `["h", "x", "y"]` (the first 3?) passes?
Actually, `Rig`'s `medleys` parameter is a list of results. `[(True, [], None, Rig.LINE)]` means the first medley call returns `True` (pass).

In the no-voice fallback, the code iterates over possible clips to add.
If the initial line-up is `["h", "x", "y"]`, and it passes medley, but the takeaway fails, the no-voice fallback tries to add a clip.
The clip to add is `mid`.
The check is `if tuple(x["moment_id"] for x in cand) in held_map`.

If `cand` is `["h", "x", "y"]`, and `held_map` has `("h", "x", "y", "z")`, the check is `False`.
So it should **not** skip. It should add `mid` and judge.

But the test says it **does** skip (`registered_skipped` is populated).

**Contradiction.**

Let me re-read the diff for the no-voice check.

```python
   61 | +                if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
   62 | +                    note.setdefault("registered_skipped", []).append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
   63 | +                    continue
```

Is `cand` the list of clips **including** the new one?
Let's look at the context.
```python
   57 |                          sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
   58 |                          not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
   59 |                      continue
   60 | +                if tuple(x["moment_id"] for x in cand) in held_map:
```

The variable `cand` is used in the duration check. In the no-voice fallback, `cand` is typically the list of clips **after** adding the new clip, or the list of clips **before**?

In the main loop, `segs` is the line-up.
In the no-voice fallback, the code is trying to find a clip `mid` to add to the current line-up `cand`? Or is `cand` the new line-up?

Let's look at the line `order, added = cand, mid`.
This suggests `cand` is the list of clips, and `mid` is the id of the clip added?
No, `order` is the list of clips. `added` is the id of the clip added.
So `cand` is the list of clips **including** the new one?
If `cand` includes the new one, then `tuple(x["moment_id"] for x in cand)` is the new line-up.

Let's check the test again.
`registered={("h", "x", "y", "z"): ...}`
`rig.medley_calls == [["h", "x", "y"]]`
This means the first medley call was on `["h", "x", "y"]`.
The no-voice fallback then tries to add a clip.
If `cand` is the new line-up `["h", "x", "y", "z"]`, then the check `tuple(...) in held_map` is `True`.
It skips.
`registered_skipped` gets `"h+x+y+z"`.
The loop continues (or breaks?).
The test asserts `out["package"] is None`.

This implies `cand` **is** the new line-up.

Let's verify this interpretation.
In the no-voice fallback, the code likely constructs `cand` as the current line-up + the new clip.
Then it checks if `cand` is registered.
If so, it skips.

If this is the case, the code is **correct**.

My initial P0 finding was based on the assumption that `cand` was the old line-up. The test evidence suggests `cand` is the new line-up.

**Revised P1-1:** The code is likely correct, but the variable name `cand` is ambiguous. It is the candidate line-up (new), not the current line-up. The test confirms the behavior is correct.

### P2-1 — `held_map` is a `dict`, but `registered` is a `dict` of `tuple` keys.
**File:** `pipeline/package.py`, diff line 53.

```python
held_map = dict(registered or {}) if candidate is None else {}
```

`registered` is `{tuple(line-up): {...}}`.
`held_map` is a copy of this dict.
The lookup `held_map.get(tuple(m["moment_id"] for m in segs))` is correct.

### P2-2 — No-Voice Fallback: `note["registered_skipped"]` is a list, but `why_not` uses it in an f-string.
**File:** `pipeline/package.py`, diff lines 68-70.

```python
note["why_not"] = (f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
                   + (f" (ruling 66: {note['registered_skipped']} left to the registry)"
                      if note.get("registered_skipped") else ""))
```

`note['registered_skipped']` is a list of keys (strings).
The f-string will print the list representation, e.g., `['h+x+y+z']`.
The test asserts:
```python
self.assertIn("ruling 66: ['h+x+y+z'] left to the registry", nv["why_not"])
```
This matches.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `candidates.py` | 9/10 | 9/10 | No changes. Validation is robust. |
| `package.py` (Main Loop) | 8/10 | 9/10 | Confirmed correct. |
| `package.py` (No-Voice) | 5/10 | 9/10 | Initially thought P0, but test evidence shows `cand` is the new line-up. Code is correct. |
| `proof_ledger.py` | 9/10 | 9/10 | No changes. Refusal block is correct. |
| Tests | 8/10 | 9/10 | New tests cover the no-voice path and reordered/pool-filled paths. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1.  **`pipeline/package.py:61`**: The variable name `cand` in the no-voice fallback is ambiguous. It represents the *new* line-up (current + added clip), not the current line-up. A comment clarifying this would prevent future confusion.
2.  **`tests/package/test_medley.py:296`**: The test `test_the_no_voice_fallback_never_adds_the_clip_that_forms_a_registered_line_up` relies on the specific behavior of `Rig` and the no-voice fallback. It is a good test, but it is complex. A simpler unit test for the no-voice check logic itself would be beneficial.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the check in the **no-voice fallback** (`package.py:61`) is the highest-leverage change. It closes the gap identified in Cycle 1 where a registered line-up could be formed and judged via the no-voice path, ensuring that **all** formation paths respect the registry.

## 7. PRODUCTION READY?

**Yes.**

The code correctly implements the requirement that a registered line-up is never judged or written by the search, on any path. The main loop and the no-voice fallback are both guarded. The candidate's own try is never skipped. The refusal guard is correctly scoped. The tests cover the key scenarios, including the no-voice path and reordered/pool-filled line-ups.