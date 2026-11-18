# qwen3.8-27b (qwen/qwen3.8-27b) 326 s finish=stop usage in 9032 / out 10277 usd_reported=0.007747 usd~0.181 (upper-bound price)



# Code Audit — RULING 144 (PBX Exception, pp-selectid)

## Scope Reviewed
Three files: `pipeline/package_pin.py`, `tests/package/proof_ledger.py`, `tests/package/test_ruling_137.py`. The change introduces a named, logged, one-process exception that extends the 12-hour window to at most 30 hours for a single build, places the exception's plain words as the first review flag, and excludes them from the 3-flag content cap.

---

## Findings

### [P2] Global mutation of `package_pin.WINDOW_H` is a process-wide side effect

```python
if a.pbx_exception:
    package_pin.WINDOW_H = float(a.hours)
```

This rewrites a module-level constant that `package.expired`, `window_problems`, and the candidate registry all read. The design contract is "one build = one process," and the test confirms the value is restored in the test's `finally`. However, if this driver is ever invoked more than once in a long-lived process (a test harness, a supervisor that re-enters `main`), the second invocation inherits the first's widened window with no exception flag. A parameter-passing approach (threading `window_h` into the checks that need it) would eliminate the class of bug entirely.

*Why not P1:* The stated architecture is strictly one-process-per-build, the refusal path (exit 2) occurs before the mutation, and the test pins the invariant. It is a latent fragility, not a live defect.

---

### [P2] Exception gate is injected after `SP.attribute_package` (the seal)

```python
SP.attribute_package(router, res["package"], sources, log=say)   # seal
try:
    if a.pbx_exception:
        res["package"]["gates"][package_pin.EXCEPTION_GATE] = {…}
    lock = LP.pin_problems(res["package"]) + \
        package_pin.window_problems(res["package"]["segments"])
```

The ruling's narrative says "after the package seals and before its pin is written," which matches the code. But if `pin_problems` (or any downstream validator) re-hashes the gate set against the seal produced by `attribute_package`, the added row would break that hash and the pin would be refused. The diff does not show `pin_problems`'s body, so I cannot confirm it is seal-agnostic with respect to gates.

*Action:* Verify that `LP.pin_problems` does not compare the gate inventory to the seal. If it does, the exception row must be added *before* `attribute_package`, or the seal must be recomputed after insertion.

---

### [P2] `content_flags` will raise `AttributeError` if the exception gate's value is a non-dict truthy

```python
exc = ((gates or {}).get(EXCEPTION_GATE) or {}).get("flags") or [] if isinstance(gates, dict) else []
```

If `gates["pbx_exception"]` were ever a string, number, or list (data corruption, a hand-edited JSON), `(value or {})` evaluates to `value` (truthy non-dict), and `.get("flags")` raises. `review_flags_of` guards with `isinstance(row, dict)`, but `content_flags` does not.

*Fix:*
```python
row = (gates or {}).get(EXCEPTION_GATE) if isinstance(gates, dict) else None
exc = (row.get("flags") or []) if isinstance(row, dict) else []
```

---

### [P3] `--pbx-exception` accepts the bare prefix with no description

The validation is:
```python
a.pbx_exception.startswith("PBX exception") and a.pbx_exception.strip()
```

The string `"PBX exception"` (14 characters, no trailing text) passes. The ruling requires the exception to be "named and logged"; a bare prefix is technically a name but carries no context for the reviewer reading the flag. Consider requiring a minimum length or a non-empty remainder after the prefix:
```python
a.pbx_exception[len("PBX exception"):].strip()
```

---

### [P3] `content_flags` called twice in `to_pin`

```python
problems += [f"{content_flags(pk.get('gates'))} review flags, over …"] \
    if content_flags(pk.get("gates")) > REVIEW_FLAGS_MAX else []
```

The function is evaluated once for the f-string and once for the condition. Harmless (pure function, small input) but a local variable would read cleaner and guard against a future refactor that makes it impure.

---

### [P3] Redundant `isinstance` check on an argparse string

```python
isinstance(a.pbx_exception, str) and a.pbx_exception.startswith("PBX exception")
```

`argparse` with `metavar="TEXT"` (no `type=`) always yields a `str` or `None`. The `isinstance` guard is dead code. Not wrong, just noise.

---

## Answers to the Reviewer's Four Questions

1. **Can the exception leak to a later build or another pin?**
   No. The mutation is process-local (one build = one process, exit after). The gate row and `res["pbx_exception"]` are embedded in this package's JSON only. A later process starts with `WINDOW_H = 12` and must pass `--pbx-exception` again to widen it. The never-reused check reads delivered pins and is unaffected.

2. **Can it carry more than one flag past the cap, or hide a doubt?**
   The exception gate is always populated with exactly one flag (`[a.pbx_exception]`). `content_flags` excludes only that exact string via list membership. A content doubt with different text still counts toward the cap of 3. A 4th content doubt is refused (test line 138–139 confirms). The only way to "hide" a doubt is to make its text byte-identical to the exception string, which would require the operator to deliberately craft a doubt that reads as the exception—defeating the purpose of the doubt.

3. **Anything else the 12 h rule guards that this bypasses?**
   The 12 h rule guards segment freshness (no stale content). The exception extends it to 30 h for one build. It does **not** bypass: never-reused, sentence law, selection lock, snap limit, any content gate, the sign-off name check, or the release authorisation. The integrator's only age gate (L-v 3's 24 h for time-sensitive segments) is noted in the ruling as unaffected. `PBX_EXCEPTION_MAX_H = 30.0` is a hard ceiling; `--hours 31` is refused.

4. **The tests.**
   Two new tests cover: (a) ordering and cap exclusion (3 doubts + exception seals; 4 doubts + exception refuses; exception is in `SOFT_GATES`); (b) driver validation (refusal without exception, refusal with unnamed text, refusal above 30 h, no mutation on refusal, mutation on success). 7/7 mutations killed. The tests are correct and well-scoped. One gap: no test exercises `content_flags` with a malformed (non-dict) exception gate value (see P2 above).

---

## Governing-Law Compliance

| Law | Status |
|-----|--------|
| SENTENCE LAW | Untouched |
| SELECTION LOCK | Untouched |
| SNAP LIMIT / NEIGHBOUR / ONSET-TAIL | Untouched |
| CREDITS / L-a / L-b / L-c / L-d | Untouched |
| L-e / L-f / L-g / L-h / L-i | Untouched |
| L-j (release on these bytes) | Untouched; exception gate is part of the sealed package |
| L-k (canonical form) | Untouched |
| L-l (model reply whole) | Untouched |
| LAW 20 / M2 | Compliant: threshold is a named constant (`PBX_EXCEPTION_MAX_H`); the exception is a ruling-authorised waiver, not a gate reclassification |
| M12 FAIL CLOSED | Compliant: invalid text → exit 2; hours over cap → exit 2; no exception → 12 h as ever |
| LAW 22 (v2f byte-identical) | Untouched |
| Smallest diff / M1 / GPU0 / no publishing | Compliant: 3 files, no new renderer/compositor/selector |

---

P1_OR_WORSE: 0