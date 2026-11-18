# qwen3.8-27b (qwen/qwen3.8-27b) 171 s finish=stop usage in 8460 / out 6726 usd_reported=0.006288 usd~0.126 (upper-bound price)



# Code Audit — pp-selectid / RULING 150 (1) BY HAND

## Scope Reviewed
`pipeline/package.py`, `pipeline/package_pin.py`, `tests/package/proof_ledger.py`, `tests/package/test_ruling_137.py` (the C1_STEP.diff, 138 lines).

---

## Findings

### [P3] Module-level mutable pin (`VALUE_SOFT_LINE`) is process-global

`package.VALUE_SOFT_LINE` is a bare module attribute mutated by the driver (`PK.VALUE_SOFT_LINE = a.value_soft_line`). If a future refactor ever runs two builds in one process (e.g., a batch driver), the second build would inherit the first build's pin. Today each build is a separate `proof_ledger.py` invocation, so this is safe. Worth a one-line comment at the declaration site stating "process-local; set once by the driver, never by library code" so a future reader doesn't treat it as a configurable knob.

### [P3] No test for the "pin set but verdict passes" path

`TestRuling150ValueByHand` covers: named line + LOST → FLAGGED; clean pass → no package; wrong line / no line / unmeasured → no package. The one untested branch is: `VALUE_SOFT_LINE` is set, the never-empty pass is active, but the value verdict is **ok** (all four "yes"). In that case `not val["ok"]` is False, the soft override is skipped, and the row should carry **no** `status`/`flags` keys (the `**({} if … else {})` adds nothing). The code is correct by inspection, but a one-line test (`values=[{"adds":"yes","no_restate":"yes","missed":"no","short":"no"} …]` with the pin set, assert no `FLAGGED` in the row) would close the matrix and guard against a future refactor that inverts the condition.

### [P3] Exact-string identity check bypasses `canon.py` (L-k)

`fields["takeaway"]["text"] == VALUE_SOFT_LINE` is a raw `==`. L-k mandates `canon.py` for "every text comparison in the pipeline." This is an **identity** check ("is this the exact line the operator typed?"), not a semantic/speech comparison, so `canon` would be wrong here (it would normalise `$40M` → `40 million dollars` and let a different line match). The code is correct; a brief inline comment (`# identity, not canon: the operator must name the exact string`) would pre-empt a future "L-k compliance" sweep from "fixing" it.

### [P3] `VALUE_FLAG` embeds the line in double-quotes without escaping

`VALUE_FLAG = 'The closing line may mostly restate the clips: "{line}"'` — if the closing line itself contains a `"` character, the flag string becomes ambiguous to a human reader. Not a functional bug (the flag is display-only, never parsed), but a `json.dumps(line)` or `repr(line)` would be more robust.

### [P3] `rec["value_by_hand"]["answers"]` copies only four keys

The record stores `adds`, `no_restate`, `missed`, `short` but not `why`, `words`, or `backend`. The log line and the `v_lost` path (for non-soft failures) do include `why`. For a "BY HAND" audit trail, including `why` in the record would make the build log self-contained without cross-referencing the log stream.

---

## Answers to the Three Requested Checks

**(1) Can any line other than the named one, or the clean pass, or an unmeasured verdict get through?**

No. The guard is a five-clause conjunction:

```python
soft                          # never-empty pass only
and not val["ok"]             # verdict must have failed
and val.get("measured") is True  # must be a measured (not INCONCLUSIVE) verdict
and VALUE_SOFT_LINE is not None  # pin must be set
and fields["takeaway"]["text"] == VALUE_SOFT_LINE  # exact string identity
```

- **Different line:** last clause is `False` → no override → `v_lost` append → no package. ✓ (tested: `test_any_other_line_or_no_verdict_stays_hard`)
- **Clean pass:** `soft` is `False` → no override → unchanged. ✓ (tested: `test_the_clean_pass_never_takes_it`)
- **Unmeasured verdict:** `val.get("measured") is True` is `False` → no override → unchanged. ✓ (tested: `run_rig(…, measured=False)`)

**(2) Does fidelity / context / length / banned words stay HARD for the named line?**

Yes. The soft override only mutates the **value** verdict dict (`dict(val, soft=True)`). The subsequent paid gates (fidelity via COMMENTARY/NEEDS_SOURCE, context, length ≤ `LY_TAKEAWAY_MAX_WORDS`, banned words) are independent checks that run unconditionally after the value block. If any of them fails, the build still refuses. The code comment and the log line both state this explicitly. The `SOFT_GATES` addition in `package_pin.py` names only `"takeaway_value"`, not fidelity/context/length/banned-words. ✓

**(3) The row the render reads.**

In `inventory()`, when `value.get("soft")` is `True` and `value.get("ok") is not True`, the row gains:

```python
"status": "FLAGGED",
"flags": ['The closing line may mostly restate the clips: "<line>"']
```

The row's `text` field is `value.get("text")` (the judged line, which equals `VALUE_SOFT_LINE` by the guard). Because `"takeaway_value"` is in `SOFT_GATES`, `gate_problems()` does not treat `FLAGGED` as a blocker (confirmed by the test: `gate_problems(…) == []`). The render reads the sealed row: status `FLAGGED`, plain flags list, `replayed` false (set by existing inventory logic outside this diff), text equal to the shipped line. ✓

---

## LAW / GOVERNING-COMPLIANCE CHECK

| Law | Status |
|-----|--------|
| LAW 20 / M2 (hard stop, no reclassification) | Compliant. The ruling explicitly makes this gate SOFT; the code adds it to `SOFT_GATES` and flags rather than passes. No threshold is changed. |
| M12 FAIL CLOSED | Compliant. Unmeasured verdict, missing pin, wrong line → all fall through to the existing HARD refusal. |
| L-k (canon for text comparison) | See P3 above. Identity check, not a speech comparison. Acceptable. |
| Smallest diff / no new renderer | Compliant. 4 files, ~40 lines of logic, no new modules. |
| GPU0 / no publishing | Not touched by this diff. |

No P0 or P1 violations found.

---

P1_OR_WORSE: 0