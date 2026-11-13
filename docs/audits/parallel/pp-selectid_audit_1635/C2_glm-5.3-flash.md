# glm-5.3-flash (z-ai/glm-5.3-flash) 97 s finish=stop usage in 7883 / out 2756 usd~0.065 (upper-bound price)

# pp-selectid-1635 — CYCLE 2 FINAL REVIEW

## 1. WHAT DID THEY CATCH THAT I MISSED?

Being honest about my Cycle 1 output (which I'm reconstructing from the consensus record, since my prior findings were folded into it):

- **glm's P1-4 (stale-`usd`-without-basis records from a pre-change cache)** — this was the deepest finding of Cycle 1 and the one I most likely underweighted. The scenario: `VP.load_cache(visual_cache)` (diff line 8) implies the cache persists across builds. A record written by the *old* code carries `usd` but no `usd_basis`. In `package.build` (diff lines 20–24) such a record matches neither the `if` nor the `elif` — its cost vanishes from both sums. glm traced this correctly and the consensus answered it (A3): every record `build()` can *see* now carries a basis, because `visual_for`'s fresh path stamps it via `cost()` and both cache-hit paths (diff lines 56–57, 62–63) overwrite with `usd=0.0, usd_basis="cached"` — and they serve *old* cache records too, since the hit path reads `hit` and re-stamps. So the stale-`usd` record never reaches `see()`'s accumulation. I should have traced that read path myself; the key insight is that the cache-hit return *re-stamps* the record, which neutralizes the stale-`usd` concern entirely.
- **glm's P2-2 (the unconditional "vendor-reported" clause)** — the cosmetic observation that an all-estimate run prints `$0.0000 vendor-reported`. I agree it's truthful (the reported-basis sum genuinely is $0.0000) and not a defect. This is the kind of cosmetic-vs-defect distinction that's easy to overcall.

What nobody missed, collectively: the three core invariants (basis routing, bool guard, cache/seal exclusion) were each independently verified by at least two models.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| glm P1-1 (cache-exclusion list is the load-bearing line, diff line 76) | **Agree** | It's the invariant that makes the whole fix coherent: neither `usd` nor `usd_basis` enters the cache, so no reader can mistake a stored basis for fresh evidence. Verified consistent with both cache-hit return paths. |
| glm P1-2 (estimate branch lacks the bool guard, diff line 46) | **Agree, correctly graded P2** | `float(getattr(r, "usd", 0.0) or 0.0)` would turn a hypothetical `Reply.usd = True` into `1.0` labelled "estimate". But the background states `Reply.usd` is a price-table float (`Backend.usd`), so it's latent, not active. glm's own hedge ("latent, not active") is the right grading. |
| glm P2-1 (`or 0.0` conflates 0.0 and missing) | **Agree, no action** | `0.0 or 0.0 → 0.0`; behaviourally identical. The label stays "estimate" either way, which is honest. |
| glm P2-2 (unconditional "vendor-reported" clause) | **Agree, cosmetic** | The printed figure is genuinely the reported-basis sum; $0.0000 is a truthful value. Not a mislabel. |
| glm P1-3 (no double-count of cached replies) | **Agree** | A `usd_basis == "cached"` record matches neither accumulation branch; it's counted once, in `cached`. Correct. |
| glm P1-4 (stale-`usd`-without-basis) | **Agree with the consensus resolution** | The concern is real for *persisted* records, but the cache-hit paths re-stamp `usd=0.0, usd_basis="cached"`, so no stale-`usd` record reaches `see()`'s sums. Resolved. |
| grok's "no findings, SHIP: yes" | **Agree** | Nothing to dispute; its verification of the bool guard and the exact-string-match routing matches mine. |
| qwen's P2 #1–#10 | **Agree, all correctly graded** | Its check table (no estimate→reported mislabel; bool/missing → estimate; no gate/seal/cache-key change) matches my reading. Its note that `sealed()` is an *inclusion* list (consensus A2) is the strongest form of the seal argument: `usd`/`usd_basis`/`usage`/`cached` can never reach the seal regardless of what the record carries. |

No disagreements. The Cycle 1 outputs were unusually consistent — no finding was contradicted by another model.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2, new): the `usage` key survives into the cache, and it's the only carrier of the reported figure — but it's excluded from the *seal*, not the cache.**
Diff line 73: the fresh-path record includes `"usage": getattr(r, "usage", None)`. Diff line 76 excludes only `("cached", "usd", "usd_basis")` from the cache write — so `usage` (containing `usd_reported`) **is** persisted in the cache. This is actually *correct and necessary*: it's what lets a later `cost()`-style reader recover the vendor figure if the record is ever re-processed. But nobody in Cycle 1 (including me) explicitly noted that the cache deliberately keeps `usage` while dropping the derived `usd`/`usd_basis`. That's the right design — the *derived* fields are per-invocation, the *raw* vendor evidence is durable — but it's an unstated invariant. If someone later "simplifies" the exclusion list to also drop `usage`, the reported basis becomes unrecoverable on replay. Worth a one-line comment, not a code change.

**N2 (P2, new): `estimated_calls` counts *calls*, but the estimate clause prints "call(s) with no vendor figure" — the count and the sum can disagree in one edge.**
Diff lines 22–24: `estimated_calls` increments only when `usd_basis == "estimate"`. But a record with `usd_basis == "reported"` and `usd == 0.0` (vendor reported a genuine $0.00, e.g. a free-tier or promo call) contributes $0.00 to `usd_reported` and *doesn't* increment `estimated_calls`. That's correct. However, the *reverse* edge: a record with `usd_basis == "estimate"` and `usd == 0.0` (price-table upper bound happens to be $0.00, e.g. a zero-priced model) increments `estimated_calls` but adds $0.00 to `usd_estimate`. The log then prints "+ $0.0000 price-table estimate for 1 call(s) with no vendor figure" — which is truthful, just visually redundant. No defect; noting for completeness since nobody flagged the zero-estimate-print case.

**N3 (P2, new): the round-to-6-places happens at *two different layers* with different inputs.**
`cost()` (diff line 45–46) rounds the *per-reply* figure to 6 places. `package.build` (diff lines 21, 23) rounds the *running sum* to 6 places. For the reported branch, the per-reply rounding happens *before* the sum, so the build's sum is a sum of already-rounded values, then rounded again. With 3 sheets at $0.041144 each, the sum of rounded values ($0.123432) vs. the rounded sum of unrounded values could differ in the 6th decimal if the vendor reported more precision. This is a sub-microdollar discrepancy — far below any reporting threshold — but it's a *double-rounding* pattern nobody mentioned. Not a defect; noting it because the fix's stated goal is "the vendor's figure, exactly", and the 6th decimal is where the vendor's precision (xAI's `cost_in_usd_ticks / 1e10` → 10 decimal places) gets truncated. If the project ever cares about the 10th decimal, this is where it's lost. Today: no action.

**N4 (observation, new): the test at diff lines 127–136 never exercises a *bool* `usd_reported`.**
The test covers: reported (float), missing (no key → estimate), cached. It does *not* cover `r.usage = {"usd_reported": True}` → should be "estimate" (per the bool guard at diff line 44). The guard is correct by inspection, but the test doesn't pin it. This is the cheapest possible test to add — one line — and it's the only invariant in the fix that's verified by reading, not by execution.glm flagged the guard; qwen verified it; nobody asked for the test.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `visual_pin.cost()` basis routing | 9/10 | 9/10 | Unchanged. All three bases route correctly; the bool guard is right; the only gap (no bool test) is N4. |
| Cache exclusion / seal integrity | 9/10 | 9.5/10 | Raised. The consensus A2 (seal is an *inclusion* list) closes the last theoretical leak; N1 confirms the cache keeps the *right* things. |
| `package.build` split accounting | 9/10 | 9/10 | Unchanged. Exact-string-match routing, no cross-contamination; glm's stale-record concern resolved by the re-stamp on cache hit. |
| Driver log line | 8.5/10 | 8.5/10 | Unchanged. Truthful in all cases; the cosmetic edges (all-estimate, zero-estimate) are noted, not defects. |
| Test coverage | 8/10 | 8/10 | Unchanged. Good coverage of the three bases; the missing bool-`usd_reported` case (N4) is the one cheap gap. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM:**
1. **N4** — `tests/package/test_visual_pin.py` (new test, diff lines 127–136): add one assertion, `r.usage = {"usd_reported": True}` → expect `{"usd": 0.37, "usd_basis": "estimate"}`. Pins the bool guard, the only invariant verified by reading rather than execution.
2. **N1** — `pipeline/visual_pin.py:76` (diff line 76): add a one-line comment noting that `usage` is *deliberately* kept in the cache (it's the durable vendor evidence) while `usd`/`usd_basis` are per-invocation derivations. Protects the invariant against future "simplification".
3. **N3** — `pipeline/visual_pin.py:45–46` + `pipeline/package.py:21,23`: note the double-rounding (per-reply then per-sum) truncates vendor precision beyond 6 decimals; harmless today, relevant if the project ever reports beyond the 6th decimal.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add the one-line bool-`usd_reported` test (N4) — it's the only invariant in this fix that currently rests on code-reading rather than an executed assertion, and it costs one line to pin.

## 7. PRODUCTION READY?

**Yes with conditions** — and the conditions are cheap:

1. Add the bool-`usd_reported` test case (N4) — one assertion, pins the guard at `visual_pin.py:44`.
2. Add the one-line comment at `visual_pin.py:76` documenting that `usage` is intentionally cache-persisted (N1).

Both are documentation/test-only; neither touches the shipped logic. Everything else — the basis routing, the split accounting, the seal and cache-key integrity, the log line's truthfulness — is verified correct from the diff, and the Cycle 1 consensus (all three models: no P0, no P1) holds under this second review.