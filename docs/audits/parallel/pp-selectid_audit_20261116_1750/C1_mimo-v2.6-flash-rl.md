# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 190 s finish=stop usage in 9994 / out 17682 usd_reported=0.001969 usd~0.295 (upper-bound price)

# AUDIT: pp-selectid-20261116_1750

## Review of the three requested areas

### (1) Can `--only` add a moment or skip a gate?

**No — it cannot add a moment.** `only_moments` filters with `kept = [m for m in moments if m["moment_id"] in want]`, so only moments already in the pool survive. The `missing` list correctly reports IDs that were asked for but not found.

**No — it cannot skip a gate.** The filter is applied after `inputs` are built and before `with_variants`; every downstream stage (eligibility, step A, second screen, hook bar, visual check, story-first, writer, verdicts) sees the reduced pool and runs unchanged.

**However**, if every named ID is absent from the pool, the pool becomes empty with no refusal — see P2-1 below.

### (2) The stop's ceiling and its wiring

- **Ceiling:** `STOP_CEILING_USD = 1.25` matches the order's "$1.25" day cap. Validation `0 < X <= 1.25` correctly accepts 1.25 and rejects 1.26, 0, −1, 2. ✓
- **Wiring:** `limit` and `stop` are both derived from `a.stop_usd` (lines 102–103), passed to `build_router(limit=limit)` and `start_refused(spent0, stop)` (line 113). The record's `spend_ruling_48` names `cap`, `stop`, and `order_17_50_stop`. ✓
- **Gap:** The order says "Stop outside calls at $0.80 **unless a package is one call from its seal**." The `--stop-usd` sets a hard `limit_usd` with no exception — see P1-1 below.

### (3) The tests

The three tests cover: bad `--only` files and bad `--stop-usd` values (exit 2, nothing written), `read_only` dedup/why, `only_moments` pool-order/missing, `start_refused` with and without stop, and `build_router` limit with and without. Coverage is solid for the unit-level functions. Gaps noted as P3 below.

---

## FINDINGS

**[P1] The order's "unless a package is one call from its seal" exception is not implemented.**
The order (3) verbatim: *"Stop outside calls at $0.80 unless a package is one call from its seal."* `--stop-usd` sets `Router(limit_usd=X)` which the description itself characterises as *"no paid call reserved past it"* — a hard, unconditional stop. If spend is at $0.80 and a package is one call from its seal, the call is refused and the package cannot be sealed. The description acknowledges Ruling 122(1) is not built, but the "unless" clause is part of the ORDER itself, not Ruling 122(1), and is silently dropped. Either implement the exception (e.g., a Router flag or a pre-call check) or explicitly document the deviation and get orchestrator sign-off.

**[P2] `--only` with all IDs absent from the pool yields an empty pool with no refusal.**
`only_moments` returns `kept = []` when no pool moment matches any requested ID. The log line reports `0 of N listed moments`, but the build proceeds with an empty pool. Downstream stages may complete with no output (misleading "success") or crash unpredictably. Add a refusal: if `kept == []`, exit 2 with a clear message before any stage runs.

**[P3] No boundary test for `--stop-usd 1.25`.**
The test rejects `"1.26"` but never asserts that `"1.25"` (the ceiling) is accepted. Add `self.assertEqual(PLG.main([... "--stop-usd", "1.25"]), 0)` (or equivalent) to lock the boundary.

**[P3] No test for `--only` combined with `--from-candidate`.**
Both options can be supplied together; the interaction (filtering a previous build's moments) is untested. Add a test or explicitly reject the combination.

**[P3] `read_only` error message uses Python dict syntax, not JSON.**
The message says `needs {'ids': [moment ids], 'why': text}` but the file format is JSON (`{"ids": ...}`). Cosmetic, but misleading to an operator reading the error.

**[P3] `refused_only()` context manager is used but not defined in the diff.**
Presumably a pre-existing helper, but if it is not defined the test fails with `NameError`. Cannot verify from the diff alone.

**[P3] Cannot verify `main()` catches `FileNotFoundError` for a missing `--only` file.**
`read_only` calls `open(path)` which raises `FileNotFoundError` (an `OSError`, not `ValueError`). The test expects exit 2. If `main()` only catches `ValueError`, the test fails. Likely handled by existing code, but unverifiable from this diff.

---

P1_OR_WORSE: 1