# qwen3.8-27b (qwen/qwen3.8-27b) 100 s finish=stop usage in 16906 / out 3513 usd~0.103 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1300
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (as the "you" in the prompt) apparently produced no output — the "YOUR CYCLE 1 OUTPUT" section is empty. So I have no prior findings to reconcile. I will treat this as a fresh, fully-informed review, using the other models' Cycle 1 outputs as a checklist to verify or refute.

**GLM-5.3-FLASH** raised P1-1 (merge_fid `ok` computation ignoring non-violation failure markers), P1-2 (title-hold returns a literal cx record), and P1-3 (rewrite success path with non-empty cheap). The consensus refuted P1-3 (R3: `rewrite_alone` raises on cheap failure before returning, so a "passed" rewrite always has empty cheap). P1-2 was recorded as G1 (the hold breaks before any inventory is built). P1-1 was recorded as G2 (every VF.check record carries a "verdict" key).

**GROK-4.20** found no P0/P1 and said SHIP: yes.

**QWEN3.8-27B** raised a P0 (fixed caption path doesn't check cheap3 before sealing) and a P1 (hardcoded `ok: True` in the fixed caption verdict). The consensus refuted the P0 (R1: the caller checks `cheap` after `rewrite_alone` returns and breaks before sealing). The P1 was partially addressed: the hardcoded `verdict.ok: True` is intentional (K3: no model verdict on a code-written line), and the deterministic layer is still checked via `merge_fid`.

**What I would have missed without their input:** The subtle interaction between `att["violations"]` being updated at line 194 to include `cheap` (a change from the old code which only had `fid["violations"] + cx["violations"]`), and the downstream sealing logic. The consensus (R2) clarifies that `att` is a record, not a gate — sealing is decided by the inventory built from the final `fid`, `cx`, `cheap`, etc. This is a critical distinction that is easy to miss.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My Verdict | Reasoning |
|---|---|---|
| **QWEN P0: fixed caption seals with failing gates** | **DISAGREE (refuted)** | The caller at line 213 checks `if not (fid["ok"] and cx["ok"]) or cheap:` after `rewrite_alone` returns. If `cheap3` has violations, `cheap` is truthy, the loop breaks, and no inventory is built. The package is never sealed. QWEN's own text acknowledges this: "This is not a P0 for sealing a bad package, because fid3['ok'] becomes False, triggering the break." |
| **QWEN P1: hardcoded `verdict.ok: True` in fixed caption** | **PARTIALLY AGREE (by design)** | The hardcoded `ok: True` in the verdict is intentional per K3: "code-written, no model" means no model verdict. The deterministic layer is still run and merged via `merge_fid`. If the deterministic layer fails, `fid3["ok"]` becomes `False` (line 100: `ok=det["ok"] and ver["ok"]`), and the caller breaks. The only risk is if the deterministic layer passes but the fixed caption's *text* is somehow invalid in a way the deterministic layer doesn't catch — but the house style lint (part of `cheap_checks`) and context integrity still run. This is a P2 at most. |
| **GLM P1-1: merge_fid `ok` ignores non-violation failure markers** | **DISAGREE (refuted)** | The consensus (G2) notes that every record `VF.check` returns carries a `"verdict"` key. The `ok` field in the verdict is computed as `measured and not ver["violations"]` (line 99). If a record failed for a reason outside `violations` (e.g., `price_now_measured: False`), that would be a bug in `VF.check` itself, not in `merge_fid`. The test fixture at line 300 shows `price_now_measured` as a separate key in the deterministic layer, not the verdict. The deterministic layer's `ok` is computed as `not det["violations"]` (line 93), which is correct for the deterministic layer. |
| **GLM P1-2: title-hold returns literal cx record** | **AGREE (P2, by design)** | The title-hold path (line 152) returns `{"ok": True, "violations": []}` as the cx record. This is a shape-deficient record, but the hold breaks the line-up before any inventory is built (line 213-218: `if not (fid["ok"] and cx["ok"]) or cheap:` — with `fid["ok"]` set to `False` at line 152, the condition is true, and the loop breaks). The record is never sealed or gated. This is the ruling's intent ("then hold"). P2: the record's provenance is thin, but it is never used for sealing. |
| **GLM P1-3: rewrite success path with non-empty cheap** | **DISAGREE (refuted)** | The consensus (R3) correctly notes that `rewrite_alone` runs `cheap_checks` on the new package *before* any verdict, and raises on a failure (line 133-134: `if cheap2[0]: raise ValueError(...)`). A raise takes the caption to the fixed line, or the title to a hold. A "passed" rewrite therefore always returns empty cheap results. The state "passed rewrite with non-empty cheap" cannot occur. |
| **GROK: SHIP: yes, no P0/P1** | **AGREE** | GROK's analysis is thorough and correct. The diff introduces no new renderer/compositor/selector, changes no gate thresholds, keeps every required gate on the final bytes, and complies with every concrete clause of ruling 65. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1: `att["violations"]` now includes `cheap` (line 194), a change from the old code.**
The old code was `att["violations"] = fid["violations"] + cx["violations"]`. The new code is `att["violations"] = cheap + fid["violations"] + cx["violations"]`. This is a behavioral change: `att` now records cheap-check violations in addition to fidelity and context violations. This is correct (the cheap checks are part of the gate path), but it means that any downstream logic that reads `att["violations"]` will now see cheap violations that were previously not recorded there. The consensus (R2) clarifies that `att` is a record, not a gate — nothing decides sealing from it. However, if any logging, reporting, or debugging tool reads `att["violations"]` and assumes it only contains fidelity/context violations, it will now see cheap violations. This is a P2: a record-keeping change that could confuse downstream consumers, but does not affect sealing.

**P2-2: The `lone_slot` check at line 185 (`if cheap and lone_slot(cheap) is None`) changes the old redo path.**
The old code was `if cheap:` — any cheap failure triggered a redo. The new code is `if cheap and lone_slot(cheap) is None:` — a cheap failure that is *only* on the caption or title no longer triggers a redo; it goes on to the paid gates. This is the intended behavior per ruling 65, but it means that a cheap failure on the caption (e.g., house style) will now be evaluated by the paid gates (fidelity verdict, context integrity) before the ruling 65 path is taken. If the paid gates also fail, the old redo path is taken (line 219-230), and the cheap violations are included in the redo instructions (line 227: `extra = _redo(cheap + fid["violations"] + ...)`). This is correct, but it means that a caption that fails house style *and* fidelity will now go through the paid gates before being redone, which is a slight change in the order of operations. This is a P2: a change in the order of gate evaluation that could affect performance (the paid gates are more expensive than the cheap checks), but does not affect correctness.

**P2-3: The `fixed_caption` function (line 78-83) does not validate that `fields["title"]` exists.**
If `fields["title"]` is `None` or missing, `fields["title"]["text"]` will raise a `KeyError` or `AttributeError`. However, the `fixed_caption` function is only called in the `except` block of `rewrite_alone` (line 153), which is only reached if the caption's write failed. The caption's write is only attempted if `lone_slot` returned `"caption"`, which means the caption was the only failing line. The title is therefore guaranteed to have passed the gates and to exist in `fields`. This is a P2: a potential `KeyError`/`AttributeError` that is guarded by the control flow, but would be a hard crash if the guard were ever removed.

**P2-4: The `merge_fid` function (line 86-102) does not handle the case where `one` has no `"deterministic"` key.**
Line 91: `d0, d1 = fid["deterministic"], one["deterministic"]`. If `one` does not have a `"deterministic"` key, this will raise a `KeyError`. However, `one` is always constructed with a `"deterministic"` key: either from `VF.check` (line 136, which always returns a `"deterministic"` key) or from the fixed caption path (line 158, which explicitly includes `"deterministic"`). This is a P2: a potential `KeyError` that is guarded by the construction of `one`, but would be a hard crash if the guard were ever removed.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| **Gate path correctness** | N/A (no Cycle 1 output) | **PASS** | No path seals a caption or title that was not gated. The merged record, the fallback, and the title hold all preserve the gate path. The caller checks `fid["ok"]`, `cx["ok"]`, and `cheap` before sealing. |
| **Fixed line format** | N/A | **PASS** | The fixed caption matches the ruling: gated title in lowercase, line break, channel names in play order separated by `' / '`, lowercase. It cites every clip. |
| **L-x (line writer independence)** | N/A | **PASS** | The line writer's vendor and family are added to `writers_v` and `writers_f` (lines 129-130) before the fidelity verdict is run (line 136). The verdict never comes from the line's writer. |
| **Takeaway failure exclusion** | N/A | **PASS** | `lone_slot` returns `None` if any violation is on the takeaway (line 75: `slots <= {"caption", "title"}`). The test at line 381-384 confirms that a takeaway failure does not take the ruling 65 path. |
| **Title hold** | N/A | **PASS** | A title that fails again is held (line 150-152): the fidelity record is set to `ok=False`, and the line-up stops. No fixed title is generated. |
| **Old redo path** | N/A | **PASS** | The old redo path is preserved for non-lone failures. The cheap violations are now included in the redo instructions (line 227), which is correct. |
| **Budget fix** | N/A | **PASS** | The budget now counts only JUDGED line-ups: `total += 0 if med.get("replayed") or med.get("cached") else 1` (line 176). The test at line 399-403 confirms that a cached verdict is free. |
| **Record-keeping** | N/A | **PASS (with P2s)** | `att["violations"]` now includes cheap violations (P2-1). The title-hold returns a shape-deficient cx record (P2, by design). The fixed caption's verdict is hardcoded to `ok: True` (P2, by design). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **P2-1** (`pipeline/package.py:194`): `att["violations"]` now includes `cheap` violations, a change from the old code. Downstream consumers that read `att["violations"]` and assume it only contains fidelity/context violations will now see cheap violations. No change needed; document the change.
2. **P2-2** (`pipeline/package.py:185`): The `lone_slot` check changes the order of gate evaluation for caption/title cheap failures. A caption that fails house style will now go through the paid gates before the ruling 65 path is taken. No change needed; this is the intended behavior.
3. **P2-3** (`pipeline/package.py:82`): `fixed_caption` does not validate that `fields["title"]` exists. Guarded by control flow, but would be a hard crash if the guard were removed. No change needed; the guard is sufficient.
4. **P2-4** (`pipeline/package.py:91`): `merge_fid` does not handle the case where `one` has no `"deterministic"` key. Guarded by the construction of `one`, but would be a hard crash if the guard were removed. No change needed; the guard is sufficient.
5. **P2-5** (`pipeline/package.py:152`): The title-hold path returns a shape-deficient cx record (`{"ok": True, "violations": []}`). The record is never sealed or gated, but its provenance is thin. No change needed; the hold breaks the line-up before any inventory is built.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The highest-leverage change is the **caller's gate check at line 213** (`if not (fid["ok"] and cx["ok"]) or cheap:`), which ensures that no package is sealed unless the fidelity, context integrity, and cheap checks all pass. This single check is the linchpin of the entire ruling 65 implementation: it guarantees that the fixed caption, the rewritten caption, and the title hold all respect the gate path, and that no ungated line is ever sealed.

## 7. PRODUCTION READY?

**Yes.**

The diff is correct, complete, and compliant with ruling 65. No P0 or P1 findings. The P2 findings are record-keeping and defensive-coding concerns that do not affect correctness or sealing. The tests are thorough and pass. The budget fix is correct. The gate path is preserved. The fixed line format matches the ruling. L-x is satisfied. The takeaway failure exclusion is correct. The title hold is correct. The old redo path is preserved.

**Conditions:** None. The code is ready to ship.