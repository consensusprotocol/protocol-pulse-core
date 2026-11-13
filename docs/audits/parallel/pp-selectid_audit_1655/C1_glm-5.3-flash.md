# glm-5.3-flash (z-ai/glm-5.3-flash) 102 s finish=stop usage in 10552 / out 2995 usd~0.077 (upper-bound price)

# Audit: pp-selectid — C1_STEP.diff (registered line-ups skipped by the search)

Scope note: I can only see this one diff. I have not seen the full bodies of `candidates.py`, `package.py` around the loop, `proof_ledger.py`, or the test files; statements below are limited to what the diff shows plus the stated background. Where the diff doesn't show something, I say so.

## What the diff actually shows

- `candidates.registered()` (candidates.py, new, diff lines 9–22): builds `{tuple(lineup): {...}}` from `reg["candidates"]`, validating each entry's `lineup` is a non-empty list of non-empty strings whose `key(lu)` equals the dict key; raises `ValueError` otherwise. Reads `e["state"]`, `e["source"]`, `e["index"]` directly (KeyError if missing — caught by the driver's refusal block, which lists `KeyError`/`TypeError`).
- `package.build(..., registered=None)` (package.py, diff lines 33–64): inside the per-angle loop, after `segs` is formed and the `segs is None` guard, a lookup `held = (registered or {}).get(tuple(m["moment_id"] for m in segs)) if candidate is None else None`; if `held is not None`, it records `rec["registered"]`, sets `rec["why"]`, logs, and `break`s — before `n_lineup += 1` / `spins += 1` / any verdict call.
- Driver (proof_ledger.py, diff lines 76, 86–87): `CA.registered(reg)` added to the refusal `try` (so a malformed registry exits 2 before anything is written), and the post-`run_due` search passes `registered=CA.registered(reg)`.
- Tests: `test_candidates.py` (states, malformed), `test_medley.py` (skip on first-formed and swapped line-up; candidate build still tries its own; `out["search"]["lineups"] == 1`), `test_ledger_build.py` (malformed → exit 2, registry bytes unchanged, `refused_only()` guard).

## Findings

### P1-1 — The skip point covers "all paths that form a line-up" only by assertion; the diff shows one insertion point, not the proof
package.py, diff line 56 (`held = (registered or {}).get(...)`).

The claim "first formed, swapped, reordered or pool-filled: all pass through the same point at the top of the loop" is the load-bearing assumption, and the diff cannot prove it: it shows only that the check sits after the `segs is None` guard. If any other formation path in `build` (e.g. a re-entry into the loop after a partial angle, a retry path, or a path that constructs `segs` elsewhere) reaches a verdict without passing this point, a registered line-up could still be judged. The test `test_the_search_never_re_forms_a_registered_line_up` covers exactly two formation paths (first-formed and one swap); it does not exercise reorder or pool-fill. **Verifiable from the diff: the single insertion point exists and precedes `n_lineup += 1` and any verdict.** Not verifiable: that it's the only such point. If the loop is, as the background states, the single place line-ups are formed, this is fine — but that's the background, not the diff.

### P1-2 — `rec["registered"] = dict(held)` stores the registry's `until`/`source`/`index` snapshot, not the states after this build's candidate tries — but the driver passes the *post-try* registry, so the recorded "why" can misdescribe what happened
package.py diff line 58 + proof_ledger.py diff lines 86–87.

The driver computes `CA.registered(reg)` *after* `run_due` (comment: "the states after this build's candidate tries"), so the states are current — good. But note the ordering dependency: if anyone later moves the `registered=CA.registered(reg)` call before `run_due`, or `run_due` mutates the registry after this snapshot, the search's skip decisions and the recorded `why` ("resting until 22:29") would be stale. The diff itself is consistent; this is a fragility, not a defect. Also: `held.get("until")` may be `None` for open/closed, and the f-string handles that — verified at diff lines 59–62.

### P1-3 — `registered` lookup happens before the `spins` guard increments, and the `break` skips `n_lineup += 1` — the "cannot loop" claim holds only if the angle loop itself has a separate bound
package.py, diff lines 56–65.

From the diff: on a skip, neither `n_lineup` nor `spins` increments, and the loop `break`s immediately, so the skip itself cannot loop. The angle ends. The *next* angle forms a different line-up (different moment ids, presumably, since the previous angle's moments are consumed — though the diff doesn't show moment consumption). If angles are bounded by `max_angles` (a parameter, diff line 33), the build terminates. **Verified: the skip is a `break`, not a `continue`, so no infinite-loop risk from the skip itself.** One subtlety: the test asserts `out["search"]["lineups"] == 1` when angle 1's only line-up is skipped and angle 2's is judged — consistent with the skip not counting. But if *every* angle's first-formed line-up were registered, the build would produce no package; the diff's driver path (proof_ledger.py lines 88–90) already handles `res is None` with a `why_none` — though that's the "8 judged line-ups spent" case, not the "all skipped" case. Whether `build` returns a usable result when all angles skip is not shown in the diff. Scenario: registry holds every line-up the search would form → every angle breaks at the skip → `out["package"]` presumably `None`. Is that correct behavior? Probably yes (the registry owns those line-ups), but the diff doesn't show what `out["tried"]`/`why` the caller sees, and the driver's `elif res is None` branch (diff line 88) speaks only of judged line-ups. Minor.

### P2-1 — `registered()` validation duplicates `due()`'s implied contract but is stricter in one visible way; the error message reads `lu!r` which may be `None`
candidates.py, diff lines 18–19.

`if not isinstance(lu, list) or not lu or not all(...) or key(lu) != k: raise ValueError(f"... ({lu!r})")`. If `lu` is `None`, the message prints `None` — fine. But note `key(lu)` is called only if the earlier clauses pass (short-circuit), so `key` never sees a non-list — verified by short-circuit order. However: the test at diff line 111 mutates `reg["candidates"]["a+b+c"]["lineup"]` to `["a","b"]` (wrong length → key mismatch) — good — but never tests a lineup whose key *matches* while the entry key differs, nor a duplicate line-up across two candidate entries (two keys, same line-up → the later one silently wins in the `out` dict). Scenario: registry holds the same line-up under two keys (shouldn't happen if `key()` is deterministic, but the diff doesn't prove the registry prevents it). Silent overwrite, last-wins. P2.

### P2-2 — `refused_only()` patches `os.makedirs` globally within the with-block; any code under test that legitimately calls `os.makedirs` inside the *refusal* path would now fail differently
test_ledger_build.py, diff lines 135–142.

The guard is scoped to the `with`-block (verified: it's a context manager, entered at diff lines 153 and 162 only), so no leak into other tests — that question is answered. Within the block, though, the driver's refusal path itself must not call `os.makedirs` or `urlopen` before refusing; if it did (e.g. ensuring a proof dir exists *before* validating), the test would now fail. The tests pass presumably (they're in the diff as passing assumptions), so the refusal path evidently doesn't. But this makes the tests *stricter* than before: any future legitimate "ensure dir, then refuse" change breaks them. That's the point of the hardening (the docstring says so), so it's intended. Note also: `os.makedirs` is patched, not `os.mkdir` or `pathlib` — if the driver used `pathlib.Path.mkdir` (which calls `os.makedirs`? no — `Path.mkdir` calls `os.mkdir` internally, actually it calls `os.mkdir` via `self._access`... in CPython, `Path.mkdir` calls `os.mkdir` for single-level, `os.makedirs`-like behavior via `parents=True` recursion), a `parents=True` mkdir might bypass the guard. Not verifiable from the diff whether the driver uses `pathlib`. P2, flag for the author.

Wait — correction on P2-2: in CPython, `pathlib.Path.mkdir(parents=True)` does call `os.mkdir` in a loop, not `os.makedirs`. So if the driver used `pathlib` with `parents=True`, the `os.makedirs` patch would NOT catch it, and the "cannot write a proof dir" guarantee would be weaker than stated. The docstring's claim ("fails here, before it can write a proof dir") holds only for `os.makedirs`-based writes. Flag it.

### P2-3 — The "decided, not an oversight" items (4) are consistent with the diff but one consequence is untested
Item 4 says every registered line-up is skipped, *open ones included*, and "in practice an open one reaches the search only when its own try ended on a budget." The test at diff lines 219–249 covers `resting` and `closed` states in the search, and the candidate-own-try case (`candidate=PK.load_candidate(...)` → `medley_calls == [["h","x","y"]]`, class "package"). The **open** state in the search path is not exercised in the shown test — the `held()` helper supports it, but the two search rigs use "resting" and "closed". Given the code path is state-agnostic (the lookup doesn't read `state` for the skip decision, only for the `why` string), this is almost certainly fine; the state-agnosticism is verifiable at diff line 56–57 (`held is not None` is the only condition). So: no defect, just a coverage note. The candidate-own-try exclusion is verified twice in the diff: `if candidate is None else None` (line 56) and the third rig (lines 246–249).

### P2-4 — Gates/seal untouched — verified
The diff touches `candidates.py` (new read-only function), `package.py` (one new kwarg + one lookup/record/break), `proof_ledger.py` (one extra refusal check + one kwarg), and tests. No gate, verdict, or seal logic is modified. `rec["registered"]` and `rec["why"]` are additive fields on the tried record. Consistent with "never change what a check accepts." The only behavioral change to the *output* is: fewer judged line-ups, new `registered`/`why` fields, and the angle ends where it previously would have judged. Whether downstream consumers of `out["tried"]` tolerate the new key — additive, so yes unless a strict-schema check exists (not shown).

### P2-5 — `spins > 4 * lineups` guard: the skip consumes no spin, so a pathological case where the search keeps forming registered line-ups... can't happen, because the skip breaks
Already covered in P1-3. No issue.

## Things I could NOT verify from the diff (stated, not guessed)

1. That the insertion point is the *only* path a formed line-up reaches a verdict (P1-1) — depends on unseen `package.py` loop structure.
2. Whether `build`'s return when *all* angles skip is well-formed for the driver's `res is None` handling (P1-3).
3. Whether the driver's proof-dir writes use `os.makedirs` vs `pathlib` (P2-2) — affects the strength of the `refused_only` guarantee.
4. Whether the registry can hold the same line-up under two keys (P2-1) — depends on unseen `seed()`/`key()` invariants.
5. Whether `out["search"]["lineups"]` counts judged line-ups only by construction (the test asserts 1; the diff shows `n_lineup += 1` after the skip, so yes, verified — actually this one I *can* verify: the increment is after the skip's `break`, so a skipped line-up never increments. Withdraw #5; verified.)

## Verdict

The fix is small, additive, and the skip logic as shown is correct: state-agnostic, pre-verdict, pre-count, `break`-terminated, candidate-try-exempt. The main residual risk is P1-1 (single-formation-point assumption), which the diff cannot prove but the background asserts.

**SHIP: yes** — with the note that P1-1 should be confirmed by the author (or by the existing test suite's coverage of reorder/pool-fill paths, which the diff doesn't show) before merge; it's a verification gap, not a known defect.