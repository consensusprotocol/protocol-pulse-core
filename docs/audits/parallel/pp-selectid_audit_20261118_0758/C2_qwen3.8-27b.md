# qwen3.8-27b (qwen/qwen3.8-27b) 183 s finish=stop usage in 9999 / out 9247 usd_reported=0.007058 usd~0.169 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261118_0758 — RULING 146 (1) + (2)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Qwen's P2 — `ONSET_QUIET` regex coupled to prose:** I missed this in Cycle 1. The regex `r"ms of genuine quiet before the hook's first onset <"` is a substring match against a human-readable `why` string produced by the onset-measurement code. If that code's wording shifts (e.g., "is below" instead of "<", or a different unit format), the soft pass silently never triggers. The failure mode is fail-closed (safe), but the RULING 146 (2) feature degrades with no log, no error, no test failure. I should have flagged the coupling.

**Qwen's P2 — mutation inside a filter predicate:** I also missed this. `soft_graphics(m)` reassigns `m["visual"]` to a new dict as a side effect of being called in the `if` clause of a dict comprehension. A reader scanning the filter sees what looks like a pure predicate. The mutation is intentional and idempotent, but it's discoverable only by reading `soft_graphics`'s body. I should have noted the readability/maintainability concern.

**Gemma:** No unique findings beyond what I already had. Her analysis was thorough and correct.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My position |
|---|---|
| Gemma: all four checks compliant, P1_OR_WORSE: 0 | **Agree.** The logic is sound. |
| Qwen: Check 1 — no 9:16 version can carry burned graphics | **Agree.** `formats=["16x9"]` on the visual record + `formats_of` sealing the whole package + `RENDER_16X9_ONLY` as a second gate. Airtight. |
| Qwen: Check 2 — third person / unmeasured / mid-word all stay HARD | **Agree.** `hook_block` → None from `graphics_only`; `measured is True` required; `ONSET_QUIET` doesn't match mid-word `why`. |
| Qwen: Check 3 — clean pass unchanged | **Agree.** Every new path is gated by `soft`. Test asserts `clean["package"] is None`. |
| Qwen: Check 4 — tests adequate | **Agree.** Four tests cover unit + end-to-end + negative cases. |
| Qwen P2: regex coupling | **Agree.** Valid. Fail-closed but silent degradation. |
| Qwen P2: side effect in filter | **Agree.** Valid. Idempotent but obscures intent. |
| Claude consensus: "No change from cycle 1 to cycle 2" | **Agree.** The diff is the same code; no new defects were introduced. |

**No disagreements.** All three Cycle 1 outputs are consistent and correct.

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] `ONSET_QUIET` regex is a prose-substring match with no structural anchor
`pipeline/package.py` line 10:
```python
ONSET_QUIET = re.compile(r"ms of genuine quiet before the hook's first onset <")
```
This matches a *sentence fragment* in the `why` field. The test at line 157 hard-codes the exact string `"70 ms of genuine quiet before the hook's first onset < 90 ms (G17a's 80 ms + one 10 ms frame)"`, so the test and the regex are in lockstep *today*. But neither the test nor the regex is coupled to the *producer* of the `why` string (the onset-measurement code in `sentence_law.edge_plan` / `head_tail`). If that code rewords the message, both the regex and the test break silently (the test would fail, which is good, but the regex would fail-closed in production with no test coverage of the *actual* produced string).

**Recommendation:** Have the onset-measurement code set a structured field (e.g., `h["failure_kind"] = "quiet_shortfall"`) and match on that. Alternatively, add a test that calls the actual onset-measurement function and asserts its `why` output matches `ONSET_QUIET`.

### [P2] `soft_graphics` mutates `m["visual"]` inside a dict-comprehension filter
`pipeline/package.py` lines 66–69 and 4174–4179:
```python
vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order
        if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))
        and not (soft and soft_graphics(m))}
```
`soft_graphics(m)` reassigns `m["visual"] = dict(v, formats=["16x9"], graphics_16x9=kinds)`. This is a **write** inside what reads as a **read-only filter**. The mutation is idempotent (second call reads the cached `graphics_16x9`), and the two call sites (main line-up, no-voice order) are safe because the second sees the already-mutated record. But:
- A future refactor that reorders the `and` clauses or adds a third call site could change semantics.
- A reader scanning the comprehension cannot tell that `m["visual"]` is being rewritten.

**Recommendation:** Extract the mutation into a pre-pass loop before the comprehension:
```python
if soft:
    for m in order:
        soft_graphics(m)  # mutate in place, no return value needed here
vbad = {m["moment_id"]: VP.layout_block(m.get("visual")) for m in order
        if VP.layout_block(m.get("visual")) and not (m is order[0] and opens_16x9(m))
        and not (m.get("visual") or {}).get("graphics_16x9")}
```
This makes the mutation explicit and the filter pure.

### [P3] `soft_graphics` is called on every moment in the vbad filter when `soft=True`, even those with no graphics
Lines 66–69 and 4174–4179: the filter calls `soft_graphics(m)` for every `m` in `order`/`segs`. For moments without `burned_in` graphics, `VP.graphics_only(v)` is called, checks `measured`/`version`/`burned_in`/`hook_block`/`RENDER_16X9_ONLY`, and returns None. This is correct but adds a function call per moment per vbad computation. In a large medley this is negligible, but it's an unnecessary cost.

**Recommendation (optional):** Pre-filter to only call `soft_graphics` on moments that have a non-empty `burned_in` list.

### [P3] The `graphics` inventory row uses `labels(len(visual))` and `who` which are defined in the enclosing `inventory` scope
Line 98: `for lb, v in zip(labels(len(visual)), visual)`. This is correct — `labels` and `who` are available in the `inventory` function's scope. But the coupling to the `visual` list (which is the package's visual records) means the row only appears when the package actually contains graphics-flagged clips. This is the intended behavior. No issue, just noting the scope dependency for future refactors.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `visual_pin.graphics_only` | Compliant | Compliant | No change. Correct guards (measured, version, hook_block, RENDER_16X9_ONLY). |
| `package.soft_graphics` | Compliant | Compliant (P2 readability) | Logic correct; mutation-in-filter is a maintainability concern, not a correctness bug. |
| `package._can_open` (G17a soft) | Compliant | Compliant | `pass is True or soft is True` is correct. Mid-word and unmeasured stay hard. |
| `package._build` (hook stage, vbad ×2) | Compliant | Compliant (P2 readability) | All paths gated by `soft`. Clean pass unchanged. |
| `package.inventory` (hook_onset + graphics rows) | Compliant | Compliant | Flag text matches ruling. `SOFT_GATES` updated. F7 mutation confirms `graphics` is optional. |
| `package_pin.SOFT_GATES` | Compliant | Compliant | Two new entries correct. |
| Tests (`TestRuling146`) | Adequate | Adequate (P2 gap) | Four tests cover the stated scope. Gap: no test asserts the *actual* onset-measurement `why` string matches `ONSET_QUIET`. |

No score changed from "compliant" to "defective." The P2s are maintainability/robustness, not correctness.

---

## 5. FINAL PRIORITY LIST

| Priority | Finding | File / Line |
|---|---|---|
| [P2] | `ONSET_QUIET` regex coupled to prose; no structural anchor or producer-side test | `pipeline/package.py:10`, `tests/package/test_ruling_137.py:157` |
| [P2] | `soft_graphics` mutates `m["visual"]` inside a dict-comprehension filter (two call sites) | `pipeline/package.py:69`, `pipeline/package.py:79` |
| [P3] | `soft_graphics` called on every moment in vbad filter when `soft=True` (unnecessary for non-graphics moments) | `pipeline/package.py:69`, `pipeline/package.py:79` |
| [P3] | `graphics` inventory row scope dependency on `labels`/`who` (note for refactors) | `pipeline/package.py:98` |

**No P0. No P1.**

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Replace the `ONSET_QUIET` prose-substring regex with a structured `failure_kind` field set by the onset-measurement code, so that RULING 146 (2) cannot silently degrade when a developer rewords a log message.

---

## 7. PRODUCTION READY?

**Yes, with conditions.**

The code is correct: all four checks pass, the clean pass is unchanged, the hard list (third person, unmeasured, mid-word, our 9:16 crop) is preserved, and the tests verify the end-to-end behavior. The two P2 findings are maintainability/robustness concerns, not correctness defects.

**Conditions before merge:**
1. Add a test that calls the actual onset-measurement function (or its `why`-string producer) and asserts the output matches `ONSET_QUIET`. This closes the silent-degradation gap. *(P2, can be a follow-up ticket if the onset-measurement code is stable.)*
2. Extract the `soft_graphics` mutation out of the dict-comprehension filter into a pre-pass loop, or add a comment at each call site explicitly noting the side effect. *(P2, readability.)*

Neither condition blocks correctness. Both reduce the risk of a future refactor introducing a subtle bug.

---

P1_OR_WORSE: 0