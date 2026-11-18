# qwen3.8-27b (qwen/qwen3.8-27b) 1456 s finish=stop usage in 18643 / out 25445 usd_reported=0.019009 usd~0.438 (upper-bound price)



# Code Audit — pp-selectid (RULING 147)

## Findings

### [P1] SOFT_GATES does not contain EXCEPTION_GATE — existing test will fail

The diff context for `pipeline/package_pin.py` (hunk `@@ -49,6 +49,8 @@`) shows the current state of `SOFT_GATES`:

```python
SOFT_GATES = frozenset({"context_a",
                         "graphics"})
```

Two elements only. Yet the **existing** (unchanged, space-prefixed) test in `tests/package/test_ruling_137.py`, class `TestRuling144TheOneException`, asserts:

```python
self.assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)
```

`EXCEPTION_GATE = "pbx_exception"` is not in that frozenset. This test will raise `AssertionError` on every run. Either a hunk that adds `"pbx_exception"` to `SOFT_GATES` is missing from this diff, or the constant was never actually added when RULING 144 was implemented. The description claims "its two audit cycles PASS" for the integrator's file, so verify the integrator's `package_pin.py` at `r146-g17a 7c1bed55` — if `SOFT_GATES` there includes the exception gate, this diff's context is stale or incomplete.

**Action:** Confirm the full `SOFT_GATES` definition in the target branch. If `"pbx_exception"` is missing, add it (it must be SOFT so the exception row is FLAGGED, not a hard gate failure). Re-run the test suite.

---

### [P2] ONSET/TAIL law text vs. RULING 146 (2) soft enforcement

The governing ONSET/TAIL law states:

> "the hook, need ≥ 80 ms of genuine sub-speech audio before the first onset or a declared room-tone lead-in pad"

RULING 146 (2) (orchestrator 2026-11-18 07:55) changes enforcement to **SOFT**: `lock_cut` marks the record `"short"` and the render flags *"The opening clip may start abruptly"* but never refuses. The code implements the ruling correctly (`hook_lead` → `refused` → `short` in `lock_cut`), but the law text as written in this audit package still reads as a hard requirement. Since the orchestrator is the law-making authority, the ruling supersedes, but the law section should be amended to read "…need ≥ 80 ms …; if unmet, the cut is flagged (SOFT, RULING 146 (2)) and never refused." Without the amendment, a future auditor reading only the law section will flag this as a violation.

---

### [P2] `gate_g16` now passes `trimmed=lock.get("trimmed_leading")` — new hard-stop path

The old `gate_g16` called `edge_plan(sa, words, lock["i0"], lock["i1"])` without `trimmed`. The new code adds `trimmed=lock.get("trimmed_leading")` and a new `trimmed_onset` check that appends errors (→ `row["pass"] = False`). This is a **stricter** gate: renders that previously passed with a trimmed leading word can now fail if the onset is not clean. This is correct per RULING 33 part 2 and LAW 20 (adding checks is allowed), but it is a behavioural change that will affect any in-flight or replayed run whose lock carries `trimmed_leading`. Ensure the three-clean-videos verification (the release criterion) includes at least one segment with a trimmed leading word so the new path is exercised.

---

### [P3] `to_pin` calls `content_flags` and `flags_cap` twice

```python
problems += [f"{content_flags(pk.get('gates'))} review flags, over {flags_cap(pk.get('gates'))} (ruling 136 (2) / "
             f"147)"] if content_flags(pk.get('gates')) > flags_cap(pk.get('gates')) else []
```

Four calls where two suffice. Bind to locals for clarity and to avoid any (theoretical) non-determinism if `pk` were mutated between calls:

```python
n, cap = content_flags(pk.get("gates")), flags_cap(pk.get("gates"))
problems += [f"{n} review flags, over {cap} (ruling 136 (2) / 147)"] if n > cap else []
```

---

### [P3] `hook_lead` refusal message when `tried` is empty

If `cut_candidates(src, plan)["in"]` returns an empty list (no legal candidates in the pause), the refusal reads:

> "…and no legal cut has genuine quiet from the cut to the word for a D1 pad to join (digital zeros lie between)"

The actual cause is "no candidates exist," not "digital zeros." In practice this is unreachable (if the pause has no candidates, `accepted_cut` would have returned `None` and `lock_cut` would have errored before calling `hook_lead`), but the message is misleading in the edge case. Consider a distinct branch: `if not tried: "no legal cut candidates in the pause"`.

---

### [P3] Timeline inconsistency in the audit header

The package header reads `Generated: 2026-11-18 08:21 UTC` (= 03:21 EST). RULING 147 is timestamped `orchestrator 08:20 ET Nov 18` (= 13:20 UTC). The package was generated ~5 hours **before** the ruling it implements. This is likely a timezone-labeling error in the header (the "08:21" was probably meant to be ET, not UTC), but it should be corrected so the audit trail is internally consistent.

---

### [P3] RULES comment formatting (line 10)

```
"ruling 142 + ruling 146")             # RULING 146 (2): …                         # RULING 142 (orchestrator 14:32 ET Nov 17): …
```

Two `#` comments on one line. The second is the tail of the RULING 142 comment that was on the previous line. It's valid Python (everything after the first `#` is a comment) but confusing. Split onto two lines.

---

## Answers to the three requested checks

**(1) Can any pin other than the excepted one get the cap of 5?**
No. `flags_cap` returns `PBX_EXCEPTION_CAP` only when `isinstance(gates, dict) and EXCEPTION_GATE in gates`. The key `"pbx_exception"` is written exclusively by the driver under `--pbx-exception` and sealed with the gates. The test at line 475–476 confirms: a gates dict with the exception key removed refuses 4 flags (cap 3). The only residual risk is the [P1] above (if `SOFT_GATES` doesn't actually contain the key, the exception row might be treated as a hard gate failure upstream, but the cap logic itself is sound).

**(2) Is the mirror byte-identical and does nothing else on this side change behaviour?**
The `sentence_law.py` changes are a wholesale copy (the diff shows the full set of integrator changes: `IN_LEAD_MAX_S`, `_ruling73`, `hook_lead`, `padded_lead_ms`, `lock_cut`, `span_fidelity`, `EDGE_WORD_FLOOR_DBFS`, the `tail` parameter, the `clamp` in `accepted_cut`, the `gpu0` import, the `gate_g16` trimmed-onset addition). The "this side" changes are limited to:
- `lock_precheck.py`: `DECODER` sha + `RULES` string + comment (no logic change; the new `hook_lead_short` field in pre-check output is explicitly "never read" on this side).
- `package_pin.py`: `PBX_EXCEPTION_CAP` constant + `flags_cap()` + two call-site updates.

The `gate_g16` trimmed-onset addition is in `sentence_law.py` (the mirror), so it's part of the byte-identical copy, not a "this side" change. No other behavioural change on this side.

**(3) The tests.**
- Decoder sha: updated in both `test_lock_precheck.py` and `test_ruling_105.py`. Consistent with the code.
- RULES string: updated in `test_lock_precheck.py`. Matches the code.
- RULING 147 cap: `test_ruling_137.py` covers 4-pass, 5-pass, 6-refuse on the excepted pin, and 4-refuse on a non-exception pin. Boundary conditions are correct.
- **However**, the existing `self.assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)` assertion will fail given the `SOFT_GATES` definition shown in the diff (see [P1]).
- Mutation coverage claim ("4 of 4 killed"): cap both ways (2), decoder (1), rules (1) = 4. Consistent with the test changes shown.

---

P1_OR_WORSE: 2