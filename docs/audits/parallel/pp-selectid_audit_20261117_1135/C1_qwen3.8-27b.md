# qwen3.8-27b (qwen/qwen3.8-27b) 384 s finish=stop usage in 16379 / out 14289 usd_reported=0.013156 usd~0.263 (upper-bound price)



# Code Audit: pp-selectid — RULINGS 136/137, Stage 1 (NEVER EMPTY for Step A)

## Verdict on the five requested checks

**(1) No HARD gate can be passed by this change.**
Confirmed. Three independent layers enforce this:
- `soft_step_a` requires `all(str(c) in STEP_A_SOFT for c in f)` — a single hard code (STALE_TIME, SPEAKER_CHANGE, RETRACTION) excludes the moment from the soft pool entirely.
- `inventory` computes `soft_a = bool(soft and a_codes and all(c in STEP_A_SOFT for c in a_codes))`; if any code is hard, `soft_a` is False and the `context_a` row remains `FAIL`.
- `gate_problems` accepts `FLAGGED` only when `flagged_ok(g, row)` is true, which requires `g in SOFT_GATES` (currently `{"context_a"}` only). A `FLAGGED` row on any other required gate (e.g. `exclusion`, `medley`, `stand_alone`) is rejected.

**(2) Clean package always first; soft pass only after empty clean, within day limit.**
Confirmed. The `build` wrapper calls `_build` (clean) first, returns immediately if a package exists, `never_empty` is False, or `flagged_today >= FLAGGED_DAY_MAX`. The soft pass runs only in the remaining case. The test `TestTheTwoPasses` verifies all four paths (clean seals, soft seals, both empty, day-limit hit) and that `never_empty=False` short-circuits.

**(3) Pin's flags are bound by the seal; live check accepts exactly this.**
Confirmed. `to_pin` derives `rf = review_flags_of(pk["gates"])` and inserts it into `moments_package` before `pin_seal` hashes the dict. The test asserts `mp["package_sha256"] == PP.pin_seal(pin)` and that a clean pin has a different hash. The live path (`check_pin_only` → `gate_problems`) accepts `FLAGGED` on `context_a` with valid flags and `replayed is False`; `review_problems` re-derives the flags from the sealed gates and rejects any mismatch.

**(4) Every pin sealed before this change recomputes.**
Confirmed. Old pins have no `FLAGGED` rows. `review_flags_of` returns `[]`; `gate_problems` sees all-`PASS` rows and accepts them; `to_pin` adds no `review_flags` key (the `if rf else {}` guard). The `flagged_ok` path is never reached. Byte-identical recomputation.

**(5) Tests.**
The six test classes cover: pool membership (soft back, hard excluded, held excluded, no-answer excluded, clean unchanged, copy semantics); the step-A row (PASS/FAIL/FLAGGED transitions, hard code still FAILs in soft pass); pin sealing (flags sealed, bound, absent when clean, six refusal cases); two-pass ordering (clean-first, soft-after-empty, day-limit, never_empty off); day count (per-ledger, reset). The mutation note (13/14 killed, P2 equivalent) is consistent with the code.

---

## Findings

**[P2] `build(*args, **kw)` allows `soft` to leak into the first (clean) pass**
`pipeline/package.py`, new `build` wrapper (line ~4204).

The public `build` captures all extra keywords in `**kw` and forwards them to `_build`. If a caller ever passes `soft=True` (e.g. a future refactor, a test helper, or a copy-paste from `_build`'s signature), it lands in `**kw` and the *first* `_build(*args, **kw)` call already runs with `soft=True` — the "clean" pass is silently a soft pass, and the clean-first guarantee is void. Worse, the second call `_build(*args, soft=True, **kw)` would raise `TypeError: got multiple values for keyword argument 'soft'`.

The intended callers (`proof_ledger.py`) do not pass `soft`, so this is latent, not active. But the signature gives no compile-time or call-time protection.

*Fix:* add `soft` to the wrapper's keyword-only parameters and assert it is False (or simply don't forward it):
```python
def build(*args, never_empty=False, flagged_today=0, soft=None, **kw):
    if soft is not None:
        raise TypeError("soft is internal to _build; use never_empty on build()")
    ...
```
Or, more simply, pop it: `kw.pop("soft", None)` before the first `_build` call.

---

**[P3] `record_flagged` opens the file without a context manager and without atomic write**
`tests/package/proof_ledger.py`, `record_flagged`.

```python
json.dump(d, open(path, "w"), indent=1)
```
If the process is killed between `open` and `json.dump` completing, `FLAGGED_DAY.json` is truncated. A crash in the read path (`json.load(open(path))`) also leaks the handle. This is a test/proof script, not a production send path, so the blast radius is a lost day-count (the next run reads 0 and allows up to 2 flagged pins again). Low risk, but a `with` block and a temp-file + `os.replace` would be trivial.

---

**[P3] `build(*args, **kw)` loses parameter-name safety for all callers**
The original `build` had 20+ named parameters. The new wrapper hides them behind `*args, **kw`. A typo in a keyword (e.g. `scorer_exra=`) is no longer caught at the `build` call site; it surfaces as a `TypeError` deep inside `_build`, with a stack trace that doesn't name the original call. IDE autocomplete and `inspect.signature` are also degraded. Functionally correct, but a regression in developer ergonomics for a module with ~4000 lines of call sites.

---

**[P3] `step_a_flags` key is injected into moment dicts that flow through the rest of the pipeline**
`soft_step_a` returns `dict(m, step_a_flags=...)`. These augmented moments enter `cleared` and are later passed to `stand_alone_check`, `candidate_lineup`, the pin's `segments`, and any JSON serialisation. The extra key is harmless for all current consumers (they access specific fields), but it is unannounced metadata on a struct that is also hashed and compared in a few places. If a future gate or comparison does a full-dict equality on moments, the flagged and unflagged copies of the same moment would differ. Not a bug today; a note for stage 2.

---

**[P3] `FLAGGED_DAY.json` directory is assumed to exist**
`FLAGGED_DAY = os.path.join(HERE, "proof", "FLAGGED_DAY.json")`. The `proof/` directory is created by other proof scripts, but `record_flagged` does not `os.makedirs(..., exist_ok=True)`. If the directory is absent (fresh checkout, cleaned workspace), the write raises `FileNotFoundError` and the proof ledger crashes after the pin is already written. The read path (`flagged_today`) handles this gracefully (returns 0), but the write path does not.

---

## Compliance with Governing Laws

| Law | Status |
|---|---|
| LAW 20 / M2 (thresholds are constants; failed gate = hard stop; never reclassify) | Compliant. No threshold changed. `FLAGGED` is a new, explicitly authorised status for one gate under one condition; it is not a reclassification of a FAIL. Hard codes still FAIL. |
| M12 FAIL CLOSED | Compliant. Missing step-A answer → moment excluded. Held → excluded. Exception in `_build` → propagates, no fallback. Soft pass also empty → clean (empty) result returned, not a fabricated pass. |
| LAW 22 (v2f byte-identical) | Not affected. This change is in the package/pin layer, not the render layer. |
| Smallest diff / M1 (no new renderer, compositor, selector) | Compliant. No new rendering or selection code. |
| L-j (release authorised on these bytes) | Not directly touched, but the `gate_problems` change is the one the live `check_pin_only` calls. A `FLAGGED` row on a soft gate with `replayed is not False` is still rejected, preserving L-j. |

No law violations found.

---

P1_OR_WORSE: 0