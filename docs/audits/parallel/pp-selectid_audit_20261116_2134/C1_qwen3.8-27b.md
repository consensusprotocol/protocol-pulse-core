# qwen3.8-27b (qwen/qwen3.8-27b) 305 s finish=stop usage in 9660 / out 11967 usd_reported=0.010502 usd~0.208 (upper-bound price)



# Code Audit — RULING 127 (2): Local Judge Verdicts Are Provisional

## Scope

I reviewed the 183-line diff (C1_STEP.diff) implementing RULING 127 (2) across `pipeline/package.py` and `tests/package/test_ruling_102.py`, checking the four requested areas against the governing laws (M12 fail-closed, LAW 20 hard-stop, smallest-diff / M1).

---

## 1. Can any path still seal or cache on a local verdict?

**No.** I traced every write path:

| Path | Guard | Verdict |
|---|---|---|
| `prescreen` – after a backend call | `if str(backend).startswith(LAST_RESORT): … continue` (line 46-49) skips vendor/family tracking, `a_by` insertion, cache write, and store write | ✅ blocked |
| `prescreen` – reading shared cache | `pick` lambda now has `and not name.startswith(LAST_RESORT)` (line 27-28) | ✅ blocked |
| `prescreen` – reading build store (`db`) | `if not (… and not str(rec.get("backend")).startswith(LAST_RESORT))` (line 37-38) forces re-ask | ✅ blocked |
| `second_screen` – second verdict | `elif str(a2.get("backend") or "").startswith(LAST_RESORT): fail[mid] = [local_held(a2)]` (line 57-58) | ✅ blocked |
| `last_resort_of` / `last_resort_note` | Unchanged; now unreachable because local verdicts never enter `a_by` | ✅ inert |

The `continue` in `prescreen` is placed immediately after `items, backend = got` and before any state mutation, so no partial write is possible. The `second_screen` check is the **primary** guard for the second screen (which makes its own backend calls independently of `prescreen`), not merely defence-in-depth.

**No finding.**

## 2. Is a local verdict HELD (retried), never a refusal?

`local_held(a)` always returns a string beginning with `HELD` (`"STEP_A_HELD (ruling 102): local, provisional (ruling 127 (2)): …"`). The parenthetical reports what the local judge said (`pass` or `refuse: <reasons>`) as **informational context inside the HELD reason**, not as the verdict itself. `is_held()` checks `str(w).startswith(HELD)` for every element, and the test helper `self.local(fail)` asserts both `PK.is_held(f)` and `"local, provisional" in f[0]`.

The reason text explicitly states *"held for this build, retried next build"*, and the test `test_every_faster_leg_unavailable_…` confirms the next build re-asks DeepSeek (call count 1, verdict from DS, `fail == {}`).

**No finding.**

## 3. Did anything change for the other legs?

The new code is gated exclusively on `startswith(LAST_RESORT)` (i.e. `"local_judge:"`). For every non-local backend:

- `pick` lambda: the added `and not name.startswith(LAST_RESORT)` is `True` for all non-local names → no behavioural change.
- Store-read guard: same prefix check → no change.
- Post-call guard: `str(backend).startswith(LAST_RESORT)` is `False` → the `continue` is never reached → vendor/family tracking, `a_by`, cache, and store writes proceed exactly as before.
- `second_screen`: the new `elif` is only reached when the previous `if` (no-verdict) is `False` **and** the backend is local → no change for DS/G/GEM.

The `off` lambda, the failover chain order, the `time_sensitive` / old-key fallback, and the `STEP_A_SAME_VENDOR` check are all untouched.

**No finding.**

## 4. The tests

I walked each modified/added test against the code paths:

| Test | What it proves | Verdict |
|---|---|---|
| `test_every_faster_leg_unavailable_…_provisional_never_a_pass_never_cached` | All Heimdall legs down → LJ answers → `two == {}`, all HELD, `cached() == {}`; next build with DS back → DS answers, `fail == {}` | ✅ correct |
| `test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read` | (a) Mocked `CI.a_failures` → HELD text contains `"refuse: REFERENT_OUTSIDE"`, still HELD not REFUSE. (b) Cache poisoned with LJ verdict → `pick` skips it, DS called. (c) Store poisoned with LJ verdict → store-read guard skips it, DS called | ✅ correct |
| `test_the_order_is_deepseek_glm_gemini_the_judge` | Chain `(DS,G,GEM) all down → want=None` → `two == {}`, `self.local(fail)`; other cases unchanged | ✅ correct |
| `test_every_leg_out_of_contract_…` | All Heimdall legs out-of-contract → LJ answers → `two == {}`, `self.local(fail)` | ✅ correct |
| `test_a_second_verdict_from_the_local_judge_never_seals_a_package` | End-to-end build: `out["package"] is None`, `last_resort_87 == {}`, `second_vendor` entries all start with `HELD` and contain `"local, provisional"` | ✅ correct |

The mutation-kill claim (5/5) is consistent with the test coverage: each of the four guards (post-call `continue`, `pick` filter, store-read filter, `second_screen` elif) has at least one test that would fail if the guard were removed.

**No finding.**

---

## Findings

**[P3] `local_held` f-string is 4 lines and dense.** The reason string is correct and the tests pin its content, but a future reader will need to parse the nested conditional `('refuse: ' + '+'.join(…) if why else 'pass')` inside the f-string. A small helper or a two-line construction would aid readability. Not a defect.

**[P3] `test_a_local_refusal_is_provisional_too_and_a_cached_local_verdict_is_never_read` bundles three distinct scenarios** (local REFUSE is HELD; cached local verdict is skipped; stored local verdict is skipped) into one method. Splitting into three `test_…` methods would make a future regression easier to bisect. Not a defect.

**[P3] `str(backend).startswith(LAST_RESORT)` is called in three places** (prescreen post-call, prescreen store-read, second_screen). A tiny module-level predicate `def _is_local(name): return str(name or "").startswith(LAST_RESORT)` would DRY the check and make the intent greppable. Purely cosmetic.

---

P1_OR_WORSE: 0