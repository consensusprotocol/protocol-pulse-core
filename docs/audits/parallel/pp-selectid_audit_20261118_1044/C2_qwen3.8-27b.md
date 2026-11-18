# qwen3.8-27b (qwen/qwen3.8-27b) 117 s finish=stop usage in 7140 / out 5952 usd_reported=0.004576 usd~0.111 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261118_1044 | RULING 150 (1) BY HAND

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1 I declared "No defects found" and stopped there. Qwen's five P3 observations are all valid and I overlooked them:

- **Process-global mutable pin** (`VALUE_SOFT_LINE` as a bare module attribute): I noted the CLI guard but didn't flag the refactoring hazard for a future batch driver.
- **Missing test for "pin set, verdict passes"**: I confirmed the code is correct by inspection but didn't call out the untested branch explicitly.
- **L-k canon.py identity-check comment**: I accepted the `==` as correct without noting that a future compliance sweep might "fix" it.
- **VALUE_FLAG double-quote embedding**: I didn't consider the display ambiguity if the line contains `"`.
- **`rec["value_by_hand"]["answers"]` omits `why`**: I noted the record exists but didn't check whether it's self-contained for audit.

None of these are functional defects, but they are legitimate P3 hardening notes that I should have listed.

## 2. WHERE DO I AGREE OR DISAGREE?

| Qwen finding | Verdict | Reasoning |
|---|---|---|
| P3: module-level mutable | **Agree** | Safe today (one process per build); a one-line comment would prevent a future foot-gun. |
| P3: no test for pin-set + verdict-ok | **Agree** | The `**({} if … else {})` adds nothing when `ok` is True. Code is correct; a one-line test closes the matrix. |
| P3: `==` bypasses L-k canon | **Agree** | This is an *identity* check (exact operator-typed string), not a semantic comparison. `canon` would be wrong here. A comment pre-empts a "fix." |
| P3: VALUE_FLAG quoting | **Agree** | Display-only, never parsed. `json.dumps(line)` would be marginally more robust. Nit. |
| P3: missing `why` in record | **Agree** | For a BY HAND audit trail, the operator's stated reason for the lost verdict makes the record self-contained without cross-referencing the log stream. |

| Gemma finding | Verdict | Reasoning |
|---|---|---|
| Five-clause conjunction is airtight | **Agree** | I re-traced all five clauses independently; no path bypasses them. |
| Hard gates remain HARD | **Agree** | `SOFT_GATES` names only `"takeaway_value"`; fidelity/context/length/banned-words are untouched. |
| CLI guard prevents accidental use | **Agree** | `--value-soft-line` requires `--pbx-exception` and a non-empty line. |
| Test coverage is sufficient | **Partially agree** | The critical paths are covered; Qwen's "pin-set + verdict-ok" branch is the one gap (P3). |

**Disagreements:** None. All three models converge on the same conclusion.

## 3. NEW FINDINGS FROM THIS REVIEW

After re-reading the diff line-by-line with the other models' notes in hand:

**[P3] `value.get("ok") is not True` in inventory is stricter than the guard's `not val["ok"]`**

The override guard (line 21) uses `not val["ok"]` (any falsy value triggers). The inventory FLAGGED condition (line 40) uses `value.get("ok") is not True` (only `True` suppresses the flag). In practice, `ok` is always a strict boolean from the verdict function, so these are equivalent. But if a future refactor introduces a truthy non-`True` sentinel (e.g., `"partial"`), the guard would *not* override (since `not "partial"` is False) while the inventory *would* flag (since `"partial" is not True` is True). The two checks are consistent today; a comment noting they must stay in lockstep would prevent drift.

**[P3] `dict(val, soft=True)` copies the entire verdict including `why`, `words`, `backend`**

The override creates a full copy of the verdict dict. The `v_lost` path (line 30) explicitly selects keys: `("text", "measured", "adds", "no_restate", "missed", "short", "why", "words", "backend")`. The `value_by_hand` record (line 25) selects only four: `("adds", "no_restate", "missed", "short")`. This is intentional (the record is a summary, not a full verdict dump), but the asymmetry between what's stored in `rec["value_by_hand"]` vs. what's in `att["value"]` (the full dict) means the build record's `value_by_hand` is a *subset* of the actual verdict. For audit, this is fine; for debugging a disputed pin, one would need to cross-reference the log stream. (Overlaps with Qwen's P3 #5.)

**No new P0/P1/P2 findings.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Guard logic (5-clause conjunction) | PASS | PASS | Re-verified; no change. |
| Hard-gate isolation | PASS | PASS | `SOFT_GATES` correctly names only `takeaway_value`. |
| CLI / driver guard | PASS | PASS | `--pbx-exception` + non-empty line required. |
| Inventory / render row | PASS | PASS | FLAGGED + flags + text correct; `value is not None` guard prevents AttributeError. |
| Test coverage | PASS (with note) | PASS (with note) | Qwen's untested branch is P3; all critical paths covered. |
| Audit trail / record | PASS | PASS (with note) | `why` omission is P3; record is sufficient for the ruling's intent. |
| Law compliance (L-k, Law 20/M2) | PASS | PASS | Identity check is correct; ruling pattern is established. |

No score changed from PASS to anything else. The P3 notes are hardening suggestions, not defects.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 (nits, non-blocking):**
1. [P3] `pipeline/package.py` line 9: add a one-line comment at `VALUE_SOFT_LINE` declaration: *"process-local; set once by the driver, never by library code."*
2. [P3] `tests/package/test_ruling_137.py`: add a one-line test for the "pin set, verdict ok" branch (assert no `FLAGGED` in the row).
3. [P3] `pipeline/package.py` line 22: add inline comment: `# identity, not canon (L-k): the operator must name the exact string`.
4. [P3] `pipeline/package.py` line 12: consider `json.dumps(line)` in `VALUE_FLAG` instead of raw `"{line}"` to avoid quote-ambiguity in display.
5. [P3] `pipeline/package.py` line 25: add `"why"` to the `value_by_hand` answers tuple for a self-contained audit record.
6. [P3] `pipeline/package.py` line 40: add a comment noting the `is not True` check must stay in lockstep with the guard's `not val["ok"]`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The five-clause guard on line 21–22 is the entire safety surface of this ruling; a one-line comment at the `VALUE_SOFT_LINE` declaration (P3 #1) stating "process-local, set once by driver" is the highest-leverage change because it prevents the single most likely future regression: a batch driver or test harness that runs two builds in one process and silently inherits the first build's pin.

## 7. PRODUCTION READY?

**Yes.**

Conditions (all already met by the code as written):
- `--value-soft-line` is only reachable with `--pbx-exception` (CLI guard, line 76).
- The override fires only in the never-empty pass (`soft`), only for a measured verdict, only for the exact named line (five-clause conjunction, line 21–22).
- Fidelity, context, length, and banned-words gates remain HARD (not in `SOFT_GATES`; run unconditionally after the value block).
- The render reads a `FLAGGED` row with the line verbatim in `flags` (inventory, line 39–40).
- The build record carries `value_by_hand` with the ruling citation, the line, and the four answer keys (line 24–26).
- Six mutations killed; control passes.

The P3 items are hardening suggestions for the next maintenance pass, not shipping blockers.

---

P1_OR_WORSE: 0