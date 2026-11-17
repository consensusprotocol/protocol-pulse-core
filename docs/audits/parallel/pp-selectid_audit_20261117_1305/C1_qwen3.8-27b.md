# qwen3.8-27b (qwen/qwen3.8-27b) 229 s finish=stop usage in 9111 / out 8488 usd_reported=0.007736 usd~0.155 (upper-bound price)



# Code Audit: pp-selectid — RULING 107(1) Spend-Refusal Tracking

## Scope Reviewed
- `pipeline/providers.py` — `Router.spend_refused`, `_reserve` → `_reserve_capped` refactor
- `tests/package/proof_ledger.py` — `open_work(res, sp, refused=())`, never-empty soft-pass holds, `main()` wiring
- `tests/package/test_ledger_router.py` — `TestRuling107TheBuildsRouterNamesEveryCallItRefusedForMoney`
- `tests/package/test_ruling_107_guard.py` — `test_money_refused_calls_and_the_never_empty_pass_holds_are_left_undone`

---

## Findings

### [P2] Potential unbounded build retry loop when the spend limit never resets

The fix correctly makes a money-refused build write `open_work > 0`, so the next build runs. However, if the daily spend limit is exhausted and no reset occurs (e.g., a misconfigured `limit_usd` of $0.00, or a stuck ledger), every subsequent build will:

1. Pass the "nothing new" gate (open_work > 0 from the last *finished* build).
2. Start, hit the limit on the first paid call, refuse, write `open_work > 0` again.
3. Repeat indefinitely.

The description notes that `start_refused` (:380) writes no FINGERPRINT, which stops the loop *only* if the build cannot start at all. A build that starts and then refuses mid-build (the case this fix targets) does write a fingerprint with `open_work > 0`, perpetuating the cycle.

**Mitigation already present:** the spend limit is presumably daily-reset. The `start_refused` path handles the "can't even begin" case.

**Recommendation:** Add a max-consecutive-refused-builds counter (e.g., 3) in the build driver. If the last N finished builds all have `spend_refused` non-empty and no new replies were recorded, emit a hard `HOLD` with a human-action-required message rather than silently re-running. This is a pre-existing gap in the retry philosophy, not a regression from this diff, but the fix makes the loop more likely to be hit (previously the build would silently skip; now it retries).

---

### [P2] One mutation survived (6 of 7 killed) — the untested `main()` wiring

The description explicitly flags: *"NOT UNIT-TESTED, PLEASE READ: the one wiring line in main() (open_work(res, sp, money) at :767-:773); no full-run driver harness exists."*

The surviving mutation is almost certainly in this wiring: e.g., passing `money` where `res` is expected, or omitting the `money` argument (falling back to the default `()`). A typo here would silently drop all spend-refusal counts from `open_work` without any test catching it.

**Recommendation:** Add a minimal integration test that calls `main()` (or the relevant block) with a mocked router whose `spend_refused = ["xai:g"]` and a mocked `res`/`sp` that yield `open_work == 0` without the `refused` argument. Assert the FINGERPRINT.json written contains `"open_work": 1` and `"spend_refused": ["xai:g"]`. Even a 10-line test with `unittest.mock.patch` on `json.dump` would kill this mutation.

---

### [P3] Thread-safety relies on CPython GIL for `list.append`

The justification *"list.append from the worker threads is atomic under the GIL"* is correct for CPython 3.12 (the stated runtime). However, this is an implementation detail, not a language guarantee. If the project ever moves to a free-threaded build (CPython 3.13+ `--disable-gil`, or PyPy with STM), the append is no longer atomic.

**Recommendation:** Add a one-line comment at the `spend_refused` declaration:
```python
self.spend_refused = []  # CPython GIL: list.append is atomic; revisit if free-threaded
```
No code change needed today.

---

### [P3] Deeply nested `.get()` chain for the soft-pass record is fragile to read

```python
s = ((((res or {}).get("never_empty") or {}).get("soft_record") or {}).get("prescreen") or {}).get("held_102") or {}
```

This is correct (every level defaults to `{}`), but a future reader may miscount the parentheses or miss a level. A small helper or a `try/except KeyError` with a local variable per level would be more maintainable. Not a defect.

---

### [P3] `spend_refused` records backend names, not call identities

Two different calls to the same backend (e.g., two different "judge" prompts) both append `"xai:g"`. The `open_work` count is correct (each refusal is one unit of undone work), but the FINGERPRINT.json's `"spend_refused"` list is not deduplicated and doesn't identify *which* calls were refused. For debugging, a tuple `(backend, role, prompt_hash)` would be more actionable.

This is a nit — the count is what drives the retry logic, and the count is correct.

---

## Verification of the Five Requested Checks

| # | Question | Verdict |
|---|----------|---------|
| 1 | Can any money refusal escape the count, or any non-money failure be counted? | **No.** The only path to `spend_refused.append` is `except SpendLimit` from `_reserve_capped`. Free/uncapped backends return early. Non-`SpendLimit` exceptions propagate without being recorded. The unreadable-ledger path raises `SpendLimit` (confirmed by test at line 119-122). |
| 2 | Can a build loop forever or pay twice? | **No double-payment.** Refused calls cost $0; answered calls are replayed from cache (test line 126: `x.calls == 1` after two calls). The retry loop is bounded by the daily spend reset (see P2 above for the edge case). |
| 3 | Thread safety of the append | **Correct** for CPython 3.12. `list.append` is a single C-level operation under the GIL. The `except` block is outside `_lock()`, but no lock is needed for an atomic append. |
| 4 | The soft pass's set difference | **Correct.** Verified by tracing all four test assertions. The flat-set subtraction correctly counts only items held by the soft pass but *not* by the clean pass. |
| 5 | The tests | **Adequate for the unit level.** Cover: free call (no count), answered call (no count), replayed call (no count), over-limit refusal (counted), unreadable-ledger refusal (counted), soft-pass-only holds, overlapping holds (deduplicated), `None`/empty `refused`. Gap: the `main()` wiring (see P2). |

---

## Governing-Law Compliance

- **M12 FAIL CLOSED:** `SpendLimit` is re-raised after recording; no silent pass. ✓
- **LAW 20:** A refused call is a hard stop for that call (exception propagates to the caller). ✓
- **LAW 22 / v2f:** No changes to rendering, cut points, or the v2f reference path. ✓
- **Smallest diff / M1:** No new renderer, compositor, or selector. The change is confined to the router's reservation path and the build driver's open-work accounting. ✓

---

P1_OR_WORSE: 0