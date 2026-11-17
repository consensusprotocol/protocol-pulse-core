# qwen3.8-27b (qwen/qwen3.8-27b) 179 s finish=stop usage in 13235 / out 9709 usd_reported=0.007538 usd~0.185 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-selectid-20261117_1217
# Reviewer: Claude (Cycle 2)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GPT-OSS-20B:** All ten findings were refuted by the Cycle 1 consensus, and I confirm each refutation. I did not miss any valid issue. The model confused the `cuttable` row's expression with `context_a`'s, and assumed `a_by` was keyed by moment ID when both call sites build it as `a_lab` (keyed by clip label). Its P0/P1 count of 6 was entirely spurious.

**QWEN3.8-27B:** Three P3 nits, all valid and all confirmed below. I had not flagged the redundant `soft_codes` call or the structural asymmetry in the cuttable override in my own Cycle 1 pass. These are real readability concerns, not correctness bugs.

**Consensus:** Correct on every point. No disagreement.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | Verdict | Reasoning |
|---|---|---|---|
| `soft_second` doesn't mutate `cleared` | GPT-OSS #1 | **Disagree** | `add_flags(m, c)` at line 51 mutates `m` in place; `m` is the same dict object held in `cleared`. Test at line 266 asserts `cleared["b"]["step_a_flags"]`. Confirmed. |
| `context_a` uses the cuttable expression | GPT-OSS #2 | **Disagree** | The quoted expression belongs to the `"cuttable"` row (line 203). `context_a`'s status is `row(bool(a_rows) and (not a_codes or soft_a), …)` (line 188). Confirmed. |
| `a_by` keyed by moment ID | GPT-OSS #3–6 | **Disagree** | Both call sites (lines 114, 136) build `a_by` as `a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}`. Keyed by label, matching `who` and `seg_flags`. Confirmed. |
| `soft_step_a` is dead code | GPT-OSS #7 | **Disagree** | Called by `cleared_pool` (line 556 in the full file), which `_build` calls at line 3227. Stage 1, live. Confirmed. |
| `fails` may be `None` | GPT-OSS #8 | **Disagree** | `prescreen` always returns a dict. `fails.get(mid)` on a dict is safe. Confirmed. |
| `soft_step_a` drops moment keys | GPT-OSS #9 | **Disagree** | `dict(m, step_a_flags=c)` copies every key of `m` and adds/overwrites `step_a_flags`. Confirmed. |
| `soft_edges` requires `ok is True` | GPT-OSS #10 | **Disagree (by design)** | A missing `ok` means the word check was unmeasured. Law L-m: unmeasured is never a pass. Stays hard. Confirmed. |
| Redundant `soft_codes` call in re-screen | QWEN #1 | **Agree [P3]** | Line 130–131: `soft_codes(fails_a.get(mid))` in the guard, `soft_codes(fails_a[mid])` in the body. Pure function, same input, same result. Storing in a local would clarify intent. |
| Cuttable override omits `soft and` | QWEN #2 | **Agree [P3]** | Line 209: the override condition uses `soft_edges(t)` without the `soft and` prefix that the base row (line 203) has. Safe today because `edge_fl` is empty when `soft` is False, so the FLAGGED dict is never added. But the asymmetry is a latent trap. |
| `soft_second` mutates in place | QWEN #3 | **Agree [P3]** | Consistent with the re-screen's `add_flags` pattern and `cut_soft`'s `cleared[mid]["edge_flags"] = e`. Not a bug. A one-line comment at the `add_flags` call site would help the next auditor. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P3] `edge_fl` comprehension: `cuttable` field check is redundant with `soft_edges`

Line 175–176:
```python
edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c)
           for mid, t in (truth or {}).items()
           if soft and (t.get("edges") or {}).get("cuttable") is not True
           for c in (soft_edges(t) or [])]
```

The `cuttable is not True` guard is redundant: `soft_edges` already returns `None` when there are no bad edges (line 33: `if not bad … return None`), and a moment with `cuttable: True` has no bad edges by construction. The guard is harmless but adds a second source of truth for "is this moment cuttable?" that could drift from `soft_edges`'s internal logic. Not a bug; a maintenance note.

### [P3] `soft_record` in the `build` wrapper captures `tried` but not `soft_edges` / `soft_second`

Line 156:
```python
"soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}
```

`soft_edges` and `soft_second` are recorded under `soft["prescreen"]` (lines 92, 107), so they are captured transitively. This is fine, but the test at line 240 only checks `soft_record["prescreen"] == {"soft_back": {}}` — it doesn't verify that `soft_edges` or `soft_second` keys appear when they should. A future refactor that moves them out of `prescreen` would silently break the record without a test catching it.

### [P3] `flag_sentence` fallback for unknown codes

Line 22:
```python
f"{STEP_A_SOFT.get(code) or EDGE_WORDS[code]}."
```

If `code` is in neither `STEP_A_SOFT` nor `EDGE_WORDS`, this raises `KeyError`. In practice, `flag_sentence` is only called with codes from `soft_codes` (which validates against `STEP_A_SOFT`) or from `soft_edges` (which returns `"EDGE_IN"` / `"EDGE_OUT"`, both in `EDGE_WORDS`). So the `KeyError` is unreachable. But a defensive `EDGE_WORDS.get(code, code)` would make the function total.

**No P0, P1, or P2 issues found.**

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `soft_codes` / `add_flags` / `soft_second` | 9/10 | 9/10 | Unchanged. Mutation pattern is correct and consistent. |
| `soft_edges` | 9/10 | 9/10 | Unchanged. Fail-closed on every hard path. |
| `_build` CUTTABLE filter | 9/10 | 9/10 | Unchanged. Correctly gated on `soft`. |
| `_build` second-family filter | 9/10 | 9/10 | Unchanged. `soft_second` + filter is correct. |
| `_build` re-screen | 8/10 | 8/10 | Redundant `soft_codes` call (P3). Logic is correct. |
| `inventory` (context_a, cuttable) | 9/10 | 9/10 | `lab`/`mids` mapping is correct. Override asymmetry (P3) is safe. |
| `package_pin` SOFT_GATES | 10/10 | 10/10 | `"cuttable"` added, `"second_pass"` excluded. Correct. |
| `build` wrapper / soft_record | 9/10 | 9/10 | Record is complete. Test coverage of the record is thin (P3). |
| Tests | 9/10 | 9/10 | 11 tests, 23/23 mutations killed. Good coverage of the soft/hard boundary. |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 NITS (should fix, not blocking):**

| # | File | Line(s) | Issue |
|---|---|---|---|
| 1 | `package.py` | 130–131 | Redundant `soft_codes(fails_a.get(mid))` / `soft_codes(fails_a[mid])` — store in a local. |
| 2 | `package.py` | 209 | Cuttable override condition omits `soft and` before `soft_edges(t)` — add for structural symmetry with line 203. |
| 3 | `package.py` | 63 | `add_flags(m, c)` in `soft_second` — add a one-line comment: "mutates the moment so the flag is visible to inventory." |
| 4 | `package.py` | 175–176 | `cuttable is not True` guard in `edge_fl` is redundant with `soft_edges`'s internal check — consider removing or adding a comment explaining the belt-and-suspenders intent. |
| 5 | `package.py` | 22 | `flag_sentence`: `EDGE_WORDS[code]` → `EDGE_WORDS.get(code, code)` to make the function total. |
| 6 | `test_ruling_137.py` | 240 | Test checks `soft_record["prescreen"]` but not that `soft_edges`/`soft_second` keys appear when the soft pass produces them. |

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The code is correct as-is; the highest-leverage change is **adding `soft and` to the cuttable override condition on line 209** — it costs one token, eliminates the only structural asymmetry between the base row and the FLAGGED override, and removes the one line a future refactorer is most likely to get wrong.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all P3, none blocking):
1. The six P3 nits above should be addressed in a follow-up commit but do not gate this merge.
2. The three `_build` call sites (CUTTABLE filter, second-family filter, re-screen) are not unit-tested directly; they are covered by the helper tests and the integration test `test_the_rows_flag_with_the_clip_named`. If the pipeline's test suite includes an end-to-end build with `never_empty=True` and a DataDash-shaped record, that would close the gap. If not, the current coverage is sufficient because the call sites only invoke tested helpers with tested inputs.
3. The `soft_record` field is new and has no downstream consumer yet. Confirm that the orchestrator or audit log that reads `never_empty` handles the new `soft_record` key gracefully (it should, since it's additive).

P1_OR_WORSE: 0