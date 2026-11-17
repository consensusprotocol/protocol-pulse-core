# qwen3.8-27b (qwen/qwen3.8-27b) 421 s finish=stop usage in 14128 / out 15797 usd_reported=0.014038 usd~0.279 (upper-bound price)



# CYCLE 2 — FINAL REVIEW: pp-selectid-20261117_1135

## 1. WHAT DID THEY CATCH THAT I MISSED?

The sole Cycle 1 finding — **qwen's [P2] on `build(*args, **kw)` forwarding a caller's `soft=True` into the clean pass** — is the one I under-weighted. I saw the `kw = {k: v for k, v in kw.items() if k != "soft"}` line and read it as "fine, it's stripped," but I did not trace the *consequence*: without that strip, the clean pass would silently run with `soft=True`, meaning the clean pass's `cleared_pool` would already include soft-flagged moments, and the "clean first, soft second" invariant would be void. The fix is correct and the new test (`self.run_build(none, sealed, never_empty=True, soft=True)[0] == [False, True]`) pins it. I should have flagged the *absence* of that strip as a P1 in Cycle 1, not just noted the line existed.

No other model produced a finding (gpt-oss-20b and gemma-4-31b-it hit their token caps with no answer), so there is no additional external signal to reconcile.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Reasoning |
|---|---|---|
| qwen [P2] `soft` leak into clean pass | **Agree, and the fix is correct.** The one-line strip plus the dedicated test close it. I partially agree with the severity: in the *shipped* code the strip is present, so the P2 is already resolved. The residual risk is only if a future refactor re-introduces the leak, which the test now guards. |
| (No other Cycle 1 findings) | N/A | Only one model answered. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] `flag_sentence` will raise `KeyError` on an unknown code — `pipeline/package.py:28`**

```python
def flag_sentence(label, channel, code):
    return f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): {STEP_A_SOFT[code]}."
```

`STEP_A_SOFT[code]` is a direct subscript. The invariant that every code reaching this line is in `STEP_A_SOFT` is enforced *upstream* by `soft_a` (which requires `all(c in STEP_A_SOFT for c in a_codes)`), so in the current call graph it cannot fire. But `flag_sentence` is a public module-level function; a stage-2 caller that passes a code not yet in `STEP_A_SOFT` (e.g., a new soft code added to `context_integrity` before the dict is updated) gets an unhandled `KeyError` deep inside `inventory`, not a clean gate failure. A one-character fix — `STEP_A_SOFT.get(code, code)` — makes it degrade to the raw code string instead of crashing the build.

**[P2] The `build` wrapper's log line reads `kw.get("log")`, which misses a positionally-passed `log` — `pipeline/package.py:133`**

```python
(kw.get("log") or print)(f"  RULING 136 (2) NEVER EMPTY: ...")
```

`log` is the 7th parameter of `_build`. If a caller passes it positionally (it lands in `*args`, not `**kw`), `kw.get("log")` is `None` and the message goes to `print` instead of the caller's logger. In the current codebase every call site uses `log=` as a keyword, so this is latent, not active. But the wrapper's own docstring says "the same search again," implying it should be transparent to the caller's logging. A safer form: inspect `args` for the 7th position, or simply always use `print` (the message is diagnostic, not user-facing).

**[P3] `record_flagged` opens the JSON file without a context manager and without a lock — `tests/package/proof_ledger.py:288`**

```python
json.dump(d, open(path, "w"), indent=1)
```

If the process is killed between `json.load` and `json.dump`, the file is left truncated. Two concurrent `proof_ledger` runs (e.g., a CI retry) can interleave reads and writes. This is a proof/test artifact, not production state, so the blast radius is a lost day-count (the next run starts at 0, which is the *safe* direction — it allows more flagged pins, not fewer). Not a merge blocker.

**[P3] `soft_step_a`'s `not is_held(f)` guard is provably redundant — `pipeline/package.py:44`**

A held reason is a string starting with `HELD` (e.g., `"HELD no verdict"`). `all(str(c) in STEP_A_SOFT for c in f)` is `False` for any such string because `HELD…` is not a key in `STEP_A_SOFT`. The test suite confirms this: the P2 mutation (deleting `not is_held(f)`) is an *equivalent* mutant. Keeping it is fine as documentation of Ruling 102's intent, but a comment would be cheaper than a dead branch.

**[P3] `CLIP_PLACE` has no entry for labels beyond `clip_04` — `pipeline/package.py:22`**

`MAX_ANGLES = 3` and `WRITES = 2` cap the number of clips, so in practice no label past `clip_04` appears. But `flag_sentence` already handles the miss with `CLIP_PLACE.get(label, 'A clip')`, so this is purely a readability gap.

## 4. REVISED SCORES

| Subsystem | Cycle 1 (est.) | Cycle 2 | Why changed |
|---|---|---|---|
| `pipeline/package.py` (soft/never-empty logic) | 8 | **8** | The `soft`-strip fix (qwen P2) was already in the diff I reviewed; I now confirm it with the test. The `*args`/`**kw` split and the `kw.get("log")` access are the same latent fragilities I noted before. No new P0/P1. |
| `pipeline/package_pin.py` (FLAGGED / soft-gate gate) | 9 | **9** | Unchanged. `flagged_ok`, `gate_problems`, `review_flags_of`, `review_problems`, and the `to_pin` integration are clean. The `SOFT_GATES` frozenset is the right shape for stage-2 extension. |
| `tests/package/proof_ledger.py` (day count, ceiling) | 8 | **8** | `flagged_today` / `record_flagged` are correct for the single-build-per-run flow. The file-I/O nits (P3) are unchanged. `STOP_CEILING_USD` bump to 1.50 is a one-line constant with a matching test. |
| `tests/package/test_ruling_137.py` | 9 | **9** | Six test classes, 14 mutation kills (13/14, the 14th a documented equivalent mutant). The qwen-P2 regression test (`soft=True` in `**kw` → clean pass still `soft=False`) is the right guard. Coverage of the "what never seals" matrix (hard-gate FLAGGED, empty flags, non-string, replayed, 4 flags) is thorough. |

No score moved. The code I reviewed in Cycle 1 already contained the qwen fix; I simply under-weighted it.

## 5. FINAL PRIORITY LIST

| # | Sev | File : Line | Finding |
|---|---|---|---|
| 1 | **[P2]** | `pipeline/package.py:28` | `flag_sentence` uses `STEP_A_SOFT[code]` (direct subscript). Change to `STEP_A_SOFT.get(code, code)` so a future stage-2 code not yet in the dict degrades to the raw string instead of crashing the build mid-`inventory`. |
| 2 | **[P2]** | `pipeline/package.py:133` | `kw.get("log")` misses a positionally-passed `log`. Either document that `log` must be a keyword arg in the `build` wrapper's docstring, or fall back to `print` unconditionally (the message is diagnostic). |
| 3 | **[P3]** | `tests/package/proof_ledger.py:288` | `json.dump(d, open(path, "w"))` — use a `with` block; add a `# no lock: proof file, safe direction on loss` comment. |
| 4 | **[P3]** | `pipeline/package.py:44` | `not is_held(f)` is an equivalent-mutant dead branch. Replace with a comment: `# Ruling 102: held is never a soft code; kept for explicit intent (P2 equiv. mutant)`. |
| 5 | **[P3]** | `pipeline/package.py:22` | `CLIP_PLACE` stops at `clip_04`. Add a comment: `# MAX_ANGLES=3 × WRITES=2 → at most 5 clips; 'A clip' fallback covers any future shape`. |

**No P0 or P1 findings.**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Replace `STEP_A_SOFT[code]` with `STEP_A_SOFT.get(code, code)` in `flag_sentence` (line 28) — it is the one line that converts a future stage-2 integration slip from a silent `KeyError` that kills the entire build into a readable raw-code string that the gate still flags and PBX still sees.

## 7. PRODUCTION READY?

**Yes, with two conditions:**

1. **Apply the `flag_sentence` `.get()` fix** (P2, item 1 above) before the stage-2 branch is cut, so that adding a new soft code to `context_integrity.a_failures` without simultaneously updating `STEP_A_SOFT` degrades gracefully rather than crashing the build.
2. **Confirm the integrator's `check_pin_only` path** (the live caller of `PP.gate_problems`) has been smoke-tested against a pin that carries a `FLAGGED` row on `context_a` with 1–3 flags and `replayed: False`. The code path is correct by inspection, but the integrator is a separate process and the diff does not include its test suite. A single end-to-end run through `check_pin_only` with a flagged pin closes this.

Neither condition blocks the *current* stage-1 merge (the `STEP_A_SOFT` dict is complete for all four stage-1 codes, and the integrator's `gate_problems` change is backward-compatible — old pins have no `FLAGGED` rows and recompute identically). Both are pre-stage-2 hygiene.

---

P1_OR_WORSE: 0