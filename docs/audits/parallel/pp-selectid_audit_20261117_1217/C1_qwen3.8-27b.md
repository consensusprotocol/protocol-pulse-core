# qwen3.8-27b (qwen/qwen3.8-27b) 333 s finish=stop usage in 13950 / out 12393 usd_reported=0.011378 usd~0.228 (upper-bound price)



# Code Audit: pp-selectid-20261117_1217 (RULING 137 Stage 2a)

## Scope Reviewed
`pipeline/package.py`, `pipeline/package_pin.py`, `tests/package/test_ruling_137.py` — the soft/soft gate switch for the never-empty pass (second-family step-A refusals + CUTTABLE sentence-edge run-on).

---

## Findings

### [P3] Redundant `soft_codes` evaluation in the re-screen branch (package.py, diff line 130–132)

```python
elif soft and got_a.get(mid) is not None and soft_codes(fails_a.get(mid)):
    add_flags(m, soft_codes(fails_a[mid]))       # second call, same input
    a_by[mid] = got_a[mid]
```

`soft_codes` is a pure function; the second call recomputes the same sorted set. Not a correctness issue, but a reader (or a future mutation) could be confused about whether the two calls could diverge. Storing the result in a local before the `elif` body would make the intent explicit.

### [P3] `cuttable` row override condition omits the `soft and` guard (package.py, diff line 209)

```python
# base row:
all((t.get("edges") or {}).get("cuttable") is True or (soft and soft_edges(t)) for t in truth.values())
# override condition:
all((t.get("edges") or {}).get("cuttable") is True or soft_edges(t) for t in truth.values())
```

Harmless in practice: the override is gated on `edge_fl` being non-empty, which itself requires `soft` to be True (the `edge_fl` comprehension has `if soft and …`). But the asymmetry is a latent trap if someone later restructures the `edge_fl` computation. Adding `soft and` to the override condition would make the two expressions structurally identical and self-documenting.

### [P3] `soft_second` mutates `cleared`'s moment dicts in place via `add_flags` before the filter re-binds `cleared` (package.py, diff lines 55–64, 110)

```python
def soft_second(cleared, a_two, off_fail):
    ...
    add_flags(m, c)          # mutates m in place
    ...
cleared = {mid: m for mid, m in cleared.items() if mid in a_two or mid in soft_two}
```

The filter creates a new dict but the values are the same (now-mutated) dicts. This is consistent with the re-screen's `add_flags(m, …)` pattern and with how `cut_soft` sets `cleared[mid]["edge_flags"]`. No bug, but a reader scanning for "where does `step_a_flags` get set?" must follow the mutation rather than a return value. A brief comment at the `add_flags` call site noting "mutates the moment so the flag is visible to inventory" would help the next auditor.

---

## Verification of the Five Requested Checks

### (1) Nothing HARD can pass

| Hard condition | Where it's enforced | Verdict |
|---|---|---|
| Word mismatch (`ok` is not True) | `soft_edges` line 29: `t.get("ok") is not True` → return None | ✓ stays hard |
| Error / missing edges | `soft_edges` line 29: `t.get("error")` / `not isinstance(t.get("edges"), dict)` → None | ✓ |
| Non-run-on edge reason | `soft_edges` line 33: `startswith(EDGE_SOFT[k])` must match for **every** bad edge | ✓ |
| Window-edge edge ("no word before/after it") | Test line 274–282: `soft_edges` returns None | ✓ |
| Trimmed word | Test line 276: "the recogniser does not hear the trimmed word…" → None | ✓ |
| Hard step-A code (STALE_TIME, SPEAKER_CHANGE, RETRACTION) | `soft_codes` line 46: `all(str(c) in STEP_A_SOFT)` → False → None | ✓ |
| Held moment | `soft_codes` line 46: `not is_held(f)` → False → None | ✓ |
| No verdict (re-screen) | Line 130: `got_a.get(mid) is not None` required | ✓ |
| FLAGGED `second_pass` at the pin | `SOFT_GATES` does not include `"second_pass"`; test line 315–317 raises `PinRefused` | ✓ |
| `L-v 2` word check (`second_pass` row) | Never in `SOFT_GATES`; inventory row unchanged | ✓ |

**No hard path can be converted to soft.** Fail-closed (M12) is maintained: missing data, errors, and unmeasured edges all return None from the soft helpers, keeping the moment out.

### (2) Clean pass is unchanged

Every new code path in `_build` is gated on `soft` (a parameter defaulting to False):
- `cut_soft = {…} if soft else {}` (line 87)
- `soft_two = soft_second(…) if soft else {}` (line 105)
- Re-screen: `elif soft and …` (line 130)
- `inventory`: `if soft and …` in `edge_fl` and the `cuttable` override (lines 175, 203, 209)
- `soft_a` requires `soft` (line 183)

The clean pass calls `_build` without `soft=True`; all new branches are dead code. The `soft_step_a` refactor (lines 72–78) is behaviourally identical to the old inline check (verified by the existing stage-1 tests). **Clean pass is byte-for-byte unchanged in behaviour.** ✓

### (3) The three `_build` call sites

| Site | What it does | Correct? |
|---|---|---|
| CUTTABLE filter (lines 87–96) | Computes `cut_soft` for non-cuttable moments whose only failure is a run-on edge; sets `edge_flags` on the moment; keeps them in `cleared` | ✓ — `soft_edges` is the sole gate; `cut_ok` still applies to all other moments |
| Second-family filter (lines 105–110) | `soft_second` keeps moments the second family refused for soft-only codes; filter keeps `a_two ∪ soft_two` | ✓ — moments with hard codes or no `off_fail` entry are dropped |
| Re-screen after writes (lines 130–132) | A soft-only refusal off the writer's family keeps the clip flagged instead of dropping it | ✓ — hard code or `got_a is None` still falls through to the `else` (drop) |

All three call only the tested helpers (`soft_edges`, `soft_codes`, `add_flags`). No new logic is inlined.

### (4) Every flag names its clip in one sentence

- `edge_fl` (line 175): `flag_sentence(lab(mid), (who or {}).get(lab(mid)), c)` — `lab` maps moment_id → label via `mids`; `who` maps label → channel. Output: `"The second clip (DataDash): the checker heard the sentence run on into the clip's first word, so it may start mid-sentence."` ✓
- `context_a` flags (line 193): `flag_sentence(lb, (who or {}).get(lb), c)` — `lb` is the label directly from `a_by`. Same format. ✓
- `flag_sentence` (lines 21–22): `f"{CLIP_PLACE.get(label, 'A clip')} ({channel or 'its channel'}): {text}."` — one sentence, clip named, channel named. ✓

Test line 298–300 confirms the exact string. ✓

### (5) The tests

- `TestStage2a.test_soft_codes_and_the_second_family`: covers `soft_codes` (soft, hard, held, empty, None) and `soft_second` (keeps soft, drops hard, drops held, drops passed). ✓
- `TestStage2a.test_only_a_sentence_running_on_at_a_word_boundary_is_soft`: DataDash's real record → `["EDGE_IN"]`; both edges → `["EDGE_IN", "EDGE_OUT"]`; four non-run-on "in" reasons → None; window-edge "out" → None; `ok=False`, `error`, `edges=None` → None. ✓
- `TestStage2a.test_the_rows_flag_with_the_clip_named`: clean pass → FAIL; soft pass → FLAGGED with the exact sentence; hard edge reason → FAIL; `context_a` with soft `seg_flags` → FLAGGED; hard code in `seg_flags` → FAIL. ✓
- `TestStage2a.test_the_pin_takes_a_flagged_sentence_edge_never_a_flagged_word_check`: FLAGGED `cuttable` → pin accepts (1 review flag); FLAGGED `second_pass` → `PinRefused`. ✓
- Existing `TestTheTwoPasses` updated for the new `soft_record` key. ✓
- 23/23 mutations killed (per the description). ✓

---

## Governing-Law Compliance

| Law | Status |
|---|---|
| SENTENCE LAW | Unchanged; `soft_edges` only reclassifies the *consequence* of a run-on, not the boundary detection |
| SELECTION LOCK | Untouched |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Untouched |
| CREDITS / L-a … L-l | Untouched |
| LAW 20 / M2 | The check still identifies the same failures; the ruling changes the pipeline's response (flag vs. drop), not the check's acceptance criteria. No threshold changed. No reclassification as "false positive" — the flag is a plain-sentence description of the real concern. |
| M12 FAIL CLOSED | Missing data / error / unmeasured → `soft_edges` returns None → moment dropped. ✓ |
| LAW 22 (v2f byte-identical) | Untouched |
| Smallest diff / M1 | Three files, no new renderer/compositor/selector. ✓ |

---

## Verdict

The implementation is correct, fail-closed, and the clean pass is provably unchanged. The three `_build` call sites delegate to well-tested pure helpers. No hard gate can be converted to soft. The pin correctly refuses a FLAGGED `second_pass` while accepting a FLAGGED `cuttable`.

P1_OR_WORSE: 0