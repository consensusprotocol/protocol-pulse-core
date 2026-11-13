# qwen3.8-27b (qwen/qwen3.8-27b) 91 s finish=stop usage in 19499 / out 3011 usd~0.104 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0710

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the *logic* of the trim cut (the `trim_onset` margin, the `edge_plan` routing). We largely missed the **integration surface** in `package.py` and the **test rig fidelity** in `test_medley.py`.

Specifically:
*   **GLM-5.3-FLASH** correctly identified that the `trim` record synthesis in `hook_onset.measure` (lines 55-56) relies on the `why` string from the *hook-lead* failure path when the plan fails. While I noted this was "cosmetic," GLM correctly flagged that this `why` string propagates to the `trim_cut` report in `package.py`, potentially misleading a human auditor into thinking the *trim* logic failed when it was actually a *planning* failure.
*   **GROK-4.20** correctly verified that the `Rig.onset` stub in `test_medley.py` now correctly simulates the *new* behavior where `pass` is the conjunction of the hook lead AND the trim cut. In Cycle 1, I did not explicitly verify that the test rig's `onset` method (lines 450-459) correctly implements `r["pass"] = r["pass"] and ok` for trimmed moments. This is critical because if the rig didn't enforce this conjunction, the test `TestRuling33TrimAtThePinStage` would pass even if the production code in `hook_onset.py` (lines 94-96) failed to enforce it.
*   **QWEN3.8-27B** raised a "P0" about `_cut_head` not being verbatim. The Consensus (K1) correctly debunked this, but Qwen's underlying concern—that the pin stage measures on a *window* file rather than the *source* file—was valid. I missed explicitly confirming in Cycle 1 that `trim_onset` (line 31) passes `sa.path` (the window) to `SL.accepted_cut`, which is the correct behavior for the pin stage (measuring what *will* be cut from the window), whereas the render measures from the source. The margin (line 38) compensates for this.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM P1-1 (Margin Direction):** **Agree.** The margin makes the pin stage stricter. This is compliant with L-m/L-j. No action required.
*   **GLM P1-2 (Synthesized `why`):** **Agree.** It is a P1 because the `trim_cut` report in `package.py` (line 129) uses `t.get("why")`. If the plan fails (e.g., "no cut plan"), the `trim` record gets the *plan* failure's `why`. The report will say "FAIL: no cut plan..." under the `trim_cut` section. This is technically correct (the trim cut *is* not measured because the plan failed), but it conflates the *reason* (planning) with the *gate* (trim). It is not a logic error, but it is a reporting clarity issue.
*   **GROK P2 (Verbatim Copy):** **Agree.** The AST comparison confirms the functions are identical. The usage in `hook_onset.py` matches the render's usage pattern (`edge_plan` -> `accepted_cut` -> `trimmed_onset`).
*   **QWEN P0-1 (Provenance):** **Disagree.** The Consensus (K1) proves these functions *are* from the render. Qwen was wrong.
*   **QWEN P0-2 (Uncut Source):** **Disagree.** The pin stage *should* measure on the window. The margin accounts for the decode difference. This is by design.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `package.py` line 131: The `trim_cut` comprehension uses `m["hook_onset"].get("trim") or {...}`.**
If `hook_onset_for` (line 102-111) catches an exception from `HO.measure`, it returns `{"pass": False, "measured": False, "why": ...}`. This dict does **not** have a `"trim"` key.
In `build()` (line 131), `m["hook_onset"].get("trim")` returns `None`. The `or` clause fires: `{"measured": False, "why": "no trimmed-cut record"}`.
The moment is excluded from `cleared` (line 133).
**Scenario:** A trimmed moment where `HO.measure` throws an exception (e.g., file I/O error). The moment is excluded. The `trim_cut` report says "no trimmed-cut record". This is **fail-closed** and correct. However, the `why` string "no trimmed-cut record" is generic. It does not tell the auditor *why* the record is missing (exception vs. logic). This is a P2 for observability, not a P1 for correctness.

**P1-NEW-2: `hook_onset.py` line 94-96: The `pass` override logic.**
```python
if rec["trim"]["pass"] is not True:
    rec.update(passed_lead=ok, why=f"the trimmed cut: {rec['trim']['why']}")
    rec["pass"] = False
```
This correctly enforces that `pass` (can open medley) requires *both* the hook lead (`ok`) and the trim cut (`rec["trim"]["pass"]`).
However, note that `rec["pass"]` was already set to `ok` (line 89). If `ok` is `False` (hook lead fails) but `rec["trim"]["pass"]` is `True` (trim cut passes), the `if` block is **not** entered. `rec["pass"]` remains `False`. This is correct.
If `ok` is `True` but `rec["trim"]["pass"]` is `False`, the `if` block **is** entered. `rec["pass"]` becomes `False`. This is correct.
**Verdict:** The logic is sound. No finding.

**P1-NEW-3: `test_medley.py` line 458: `r["pass"] = r["pass"] and ok`.**
The rig's `onset` method correctly simulates the production logic.
**Verdict:** No finding.

**P1-NEW-4: `funnel.py` line 274: `mom` function assumption.**
`w, _, rest = (o.get("text") or "").partition(" ")` assumes the trimmed word is the *first* word.
The background states: "A clip that opens on a discourse conjunction... may have that ONE leading word trimmed".
The `TRIMMABLE_LEADING` set is `{"but", "and", "so", "well", "now", "yeah"}`.
The `trimmed_boundary` function (line 169) checks `canon.canon_tokens(words[k]["word"]) != tok` where `k = i0 - 1`. This ensures the trimmed word is the word *immediately before* the lock's first word.
If the lock's first word is the *first* word of the sentence, the trimmed word is the *first* word of the sentence.
If the lock's first word is *not* the first word of the sentence, the trimmed word is *not* the first word of the sentence.
However, the `mom` function in `funnel.py` is a **reporting** tool. It takes the *original* moment's text and marks the *first* word as trimmed.
**Scenario:** A moment with text "So Bitcoin rises." where "So" is trimmed. `mom` produces "[So trimmed] Bitcoin rises." Correct.
**Scenario:** A moment with text "And so Bitcoin rises." where "And" is trimmed? No, `TRIMMABLE_LEADING` only allows *one* word. If "And" is trimmed, the lock starts at "so". The text is "so Bitcoin rises." The `mom` function would mark "so" as trimmed. But the *actual* trimmed word was "And".
**Wait:** The `trimmed_leading` field in the moment record contains the *word* that was trimmed. The `mom` function does *not* use `m.get("trimmed_leading")`. It uses `o.get("text")` and partitions on the first space.
**Defect:** If the trimmed word is *not* the first word of the *original* moment's text, `mom` will mark the wrong word.
**Can this happen?**
The `trimmed_boundary` requires the trimmed word to be `words[i0-1]`.
The moment's text is the concatenation of `words[i0..i1]`.
The *original* moment (before trimming) would have included `words[i0-1]`.
So the original text is `words[i0-1] + " " + words[i0] + ...`.
The `mom` function takes the original text and marks the first word.
Since `words[i0-1]` is the first word of the original text, `mom` *is* correct.
**Verdict:** No finding. The assumption holds because the trimmed word is always the first word of the *original* (untrimmed) moment's text.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `sentence_law.py` | 9/10 | 10/10 | Verified verbatim copy and correct usage. |
| `hook_onset.py` | 8/10 | 9/10 | Logic is sound. The `why` string propagation is a minor reporting issue, not a logic flaw. |
| `package.py` | 8/10 | 9/10 | The `trim_cut` exclusion is correct. The `why` string in the report is slightly misleading but fail-closed. |
| `test_medley.py` | 7/10 | 9/10 | The rig correctly simulates the new `pass` conjunction. |
| `funnel.py` | 8/10 | 9/10 | The `mom` function is correct for the current data model. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None.

**P1 HIGH**
*   **P1-1:** `pipeline/package.py:129-131`. The `trim_cut` report uses the `why` from the `trim` record. If the *plan* fails (e.g., "no cut plan"), the `trim` record's `why` is the plan failure reason. The report will show "FAIL: no cut plan..." under `trim_cut`. This is technically correct (the trim cut is not measured) but conflates the *gate* (trim) with the *reason* (plan). **Recommendation:** In `hook_onset.py` line 56, when synthesizing the `trim` record for a plan failure, use a specific `why` like "trimmed cut not measured: plan failed". This improves audit clarity.

**P2 MEDIUM**
*   **P2-1:** `pipeline/hook_onset.py:56`. The synthesized `trim` record copies `rec.get("measured")`. If the plan fails, `rec["measured"]` is `False`. The `trim` record will have `measured: False`. This is correct. No change needed.
*   **P2-2:** `tests/package/funnel.py:274`. The `mom` function assumes the trimmed word is the first word. This is correct for the current data model but fragile if the data model changes. Add a comment.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Clarify the `why` string in the synthesized `trim` record when the plan fails.**
In `hook_onset.py` line 56, change:
```python
rec["trim"] = {"pass": False, "measured": rec.get("measured", False), "why": rec.get("why")}
```
to:
```python
rec["trim"] = {"pass": False, "measured": rec.get("measured", False), "why": f"trimmed cut not measured: {rec.get('why')}"}
```
This ensures that the `trim_cut` report in `package.py` clearly distinguishes between "the trim cut failed" and "the trim cut was not measured because the plan failed."

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:**
1.  Apply the P1-1 fix to `hook_onset.py` line 56 to clarify the `why` string in the synthesized `trim` record.
2.  Verify that the `trim_cut` report in `package.py` correctly displays the new `why` string.

**Rationale:**
The logic is sound, fail-closed, and compliant with Ruling 33 (a). The tests are comprehensive and correctly simulate the new behavior. The only issue is a minor reporting clarity problem that could mislead a human auditor. Fixing this is low-risk and high-value for auditability.