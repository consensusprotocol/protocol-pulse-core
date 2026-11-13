# glm-5.3-flash (z-ai/glm-5.3-flash) 113 s finish=stop usage in 7701 / out 2623 usd~0.062 (upper-bound price)

# Audit: pp-selectid-1635 — cost basis reporting fix (RULING 70)

## Scope of what I verified
Static review of the 141-line diff only. I did not run the tests; I take the stated results (test_visual_pin 11, test_medley 138 OK) as reported, not verified.

## Findings

### P1-1 — `usd_basis` leaks into the cached record's `usage`-adjacent fields? No — but the cache-exclusion list is the load-bearing line
`pipeline/visual_pin.py:76` (diff line 76): `cache[k] = {x: y for x, y in rec.items() if x not in ("cached", "usd", "usd_basis")}`.

This is correct and is the key invariant: neither `usd` nor `usd_basis` enters the cache, so a later read cannot mistake a stored basis for fresh evidence. Verified consistent with the two cache-hit return paths (diff lines 56–57, 61–63) which re-add `usd=0.0, usd_basis="cached"` on the way out. No path stores a basis. Good.

### P1-2 — `cost()` bool guard is correct, but only on the reported branch
`pipeline/visual_pin.py:44` (diff line 44): `isinstance(rep, (int, float)) and not isinstance(rep, bool)`.

In Python, `True`/`False` are instances of `int`, so without the `not isinstance(rep, bool)` clause a literal `True` in `usage["usd_reported"]` would round to `1.0` and be labelled "reported" — $1.00, not $0.04. The guard is present and correct. Note the asymmetry: the **estimate** branch (diff line 46) has no bool guard — `float(getattr(r, "usd", 0.0) or 0.0)`. If a Reply ever carried `usd=True`, it would become `1.0` labelled "estimate". That's a latent, not active, defect: the background states Reply.usd is a price-table float, so I cannot show a concrete scenario today. P2.

### P2-1 — Estimate branch: `or 0.0` silently converts a legitimate 0.0 the same as a missing one
`pipeline/visual_pin.py:46` (diff line 46): `float(getattr(r, "usd", 0.0) or 0.0)`.

`0.0 or 0.0` → `0.0`, so this is behaviourally identical for the zero case; the `or` only matters for `None`/missing. No defect, noted for completeness. The `usd_basis` is still "estimate" either way, so the label is honest. No action.

### P2-2 — `estimated_calls` counts only the estimate branch, by design — confirm the log's conditional matches
`pipeline/package.py:24` (diff line 24): `out_visual["estimated_calls"] += 1` sits inside the `elif rec.get("usd_basis") == "estimate":` branch. The driver (diff lines 90–93) prints the "+ $Y ... for N call(s)" clause only `if vis.get("estimated_calls")`. So a run that is all-reported prints no estimate clause, and a run that is all-estimate prints no "vendor-reported" clause — wait, it does: the "$X vendor-reported" clause is unconditional (diff line 90) and prints `$0.0000 vendor-reported` when everything was estimated. That's cosmetic, not a mislabel: the figure printed is genuinely the reported-basis sum, which is legitimately $0.0000. Not a defect; the label stays truthful.

### P1-3 — Cached replies: the `usd=0.0` in the record vs. the ledger's "cached" counter — no double-count, verified
Cache-hit paths (diff lines 56–57, 62–63) return `usd=0.0, usd_basis="cached"`. In `package.build` (diff lines 20–24), a record with `usd_basis == "cached"` matches **neither** the `if` nor the `elif` — it adds to neither `usd_reported` nor `usd_estimate`, and not to `estimated_calls`. It only increments the `cached` counter (diff line 18). So a cached reply contributes $0.00 to both sums and is counted once, in `cached`. Correct: a reply served from its recording costs nothing, and it is not silently counted as a "reported" $0.00. Good.

### P1-4 — The `rec.get("usd_basis")` read in package.build vs. records that predate this change
`pipeline/package.py:20` (diff line 20): `if rec.get("usd_basis") == "reported":`.

Scenario: a visual record produced by the **old** code (pre-branch, e.g. replayed from a persisted package or a cache written before this change) has `usd` but no `usd_basis` key. Then:
- `usd_reported` += 0, `usd_estimate` += 0, `estimated_calls` += 0 — the cost silently vanishes from both sums.

But: the cache-exclusion change (diff line 76) means a cache written by the *new* code never holds `usd` either, so the only stale-`usd`-without-basis records are those persisted by the old code. Whether such records survive into a fresh build depends on whether `visual_cache` is persisted across builds — the diff shows `VP.load_cache(visual_cache)` (diff line 8), which implies yes. If the 2026-11-13 first-build's cache (the $0.3646 run) is reused, its records carry `usd` but no `usd_basis`, and the new build's ledger would print $0.0000 for calls that actually cost $0.0890.

**However** — the cache-hit paths (diff lines 56–57) return `usd=0.0, usd_basis="cached"` regardless, because a cache hit is by definition not a new call. The stale-`usd`-in-cache scenario only matters if `package.build`'s `see()` sums over records that came from the cache *miss* path of a *previous* build. I cannot determine from the diff whether `see()` ever sees such records; the `todo` list is filtered to `not (m.get("visual") or {}).get("measured")`, so a previously-measured moment is skipped entirely. **Uncertain — flagging, not asserting.** If stale records can reach `see()`, the cost vanishes from the printed total (fail-quiet, not fail-closed, but this is reporting, not a gate — M12's fail-closed applies to gates, and no gate reads these fields per the diff).

### P2-3 — Nothing here touches a gate, the seal, or the cache key — verified
- Seal: `VP.sealed` (diff lines 138–141 context) already excluded `usd`/`cached` before this change; the diff adds `usd_basis` to the *cache* exclusion (line 76) but the seal's exclusion list is untouched. The test at diff lines 138–141 asserts the seal never holds a cost; `usd_basis` is a cost-adjacent field, and the test's fixture (line 140) does not include `usd_basis`, so the test does not *prove* `usd_basis` stays out of the seal — but the seal code is unchanged, so if it excluded `usd` by name, `usd_basis` (a different key) would only enter if the seal were inclusive. **Uncertain**: I cannot see `sealed()`'s implementation; the diff shows only its tail (lines 32–33). If `sealed()` copies the whole record, `usd_basis` now rides into the seal where it didn't before. That would change the seal's contents — not its *key* — and the test wouldn't catch it. P2, conditional on `sealed()`'s implementation.
- Cache key: the cache key `k` is computed before this diff's hunk; no change visible. Untouched.
- Gates: `MEDLEY_GATES` referenced only in an existing assertion (diff line 116); no gate logic modified. Untouched.

### P2-4 — test_medley's fixture now carries `usd_basis: "reported"` (diff lines 106–107) — the build's split-total assertion (line 115) asserts `(0.006, 0.0)`
Three moments, each `usd=0.002, usd_basis="reported"` → `usd_reported = 0.006`, `usd_estimate = 0.0`. Arithmetic checks out. But the fixture's third-moment override mechanism (`self.visuals.get(...)`) means the test as diffed exercises only the "reported" basis through the build path; the "estimate" basis through `package.build`'s elif branch is exercised only in `test_visual_pin` at the `cost()` unit level. The elif branch in `package.build` (diff lines 22–24) — the `estimated_calls` increment — has no build-level test coverage shown in this diff. P2, coverage gap, not a defect.

## What I could NOT verify (stated, not guessed)
1. Whether `VP.sealed()` copies the whole record (→ would `usd_basis` enter the seal?) — implementation not in the diff.
2. Whether stale pre-branch cache records can reach `see()` — depends on `visual_cache` persistence and the `measured` filter, which I've reasoned about but not traced.
3. Whether any *other* consumer of `out["visual"]["usd"]` exists outside this diff (e.g. the pin builder, `package_pin.to_pin` referenced at diff line 117) — if the pin's seal or a downstream report read `usd` and it's now absent from `out_visual`'s top-level (renamed to `usd_reported`/`usd_estimate`), that consumer would silently read `None`/0. The diff shows the driver (proof_ledger.py) updated, but I cannot confirm it's the only reader. **This is the highest-uncertainty item**: the key `usd` is *removed* from `out_visual`'s schema (diff lines 9–11: old had `"usd": 0.0`, new has `usd_reported`/`usd_estimate`), and any reader of `out["visual"]["usd"]` not shown in this diff now gets a missing key. The diff's `.get("usd", 0)`-style readers would survive; direct `["usd"]` readers would KeyError.

## SHIP: yes with conditions

Conditions:
1. **Confirm no other reader of `out["visual"]["usd"]` exists** (the renamed key). Grep for `visual"]["usd` / `visual.get("usd")` across the repo; the diff updates proof_ledger.py but I cannot see the whole call graph. If a reader exists, it silently reads 0/None — a reporting regression, not a gate failure.
2. **Confirm `VP.sealed()`'s exclusion list** covers `usd_basis` (or that the seal is intentionally allowed to carry it — but then the "seal never holds a cost" test's premise shifts, since the test fixture lacks `usd_basis` and wouldn't catch the drift).
3. (Optional, P2) Add a build-level test where one call is `usd_basis: "estimate"` to exercise `package.build`'s elif + `estimated_calls` increment, which currently has no shown coverage.

No P0. The core invariant — reported vs. estimate never summed under one label, bools never counted as reported, cached costs $0.00 — holds on every path I could trace.