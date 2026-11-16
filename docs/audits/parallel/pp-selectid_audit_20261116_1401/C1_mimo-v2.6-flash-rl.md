# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 276 s finish=stop usage in 8644 / out 17135 usd_reported=0.001862 usd~0.283 (upper-bound price)

# CODE AUDIT — pp-selectid (RULING 123 (1): Grok reserve at 25 % with tripwire)

Reviewer pass on the four requested checks, plus a general sweep. Findings are tagged by severity.

---

## CHECK (1): The tripwire's comparison, and that it cannot be missed

**What is correct:**
- The comparison `float(usage["usd_reported"]) > float(f) * usd` matches the order's operative threshold — "bills above 25 % of the **list** price of what it used" — where `usd` is the list cost of the call's usage (confirmed by the test asserting `trip["list"] == 0.055`, the true list cost of 1 000 × $5/M + 2 000 × $25/M, not the reserved 0.095 625). The order's looser phrase "compare what was billed with what was reserved" is correctly resolved in favour of the explicit "above 25 % of list" rule.
- `usage = usage or {}` executes before `usage.get(...)`, so a `None` usage cannot crash the settle path.
- The `and` chain short-circuits safely: no fraction → no trip attempt; non-numeric billed → no trip attempt; already tripped → no duplicate record.
- The trip record is written into the same ledger dict `d` that `_reserve_fraction` reads, under the same `self._lock()`, and is persisted (the test reads it back from the file). `held` is captured from `d["reserved"].pop` before use, so `reserved` in the record is the actual amount held for the offending call.
- The trip fires during the settle of the offending call itself, so the offending call is the accepted "one call's overshoot"; every subsequent `_reserve_fraction` read sees the trip.

**Vectors by which a trip could be missed:**

- **[P3]** An abandoned / `unreported` call (no numeric `usd_reported` in usage) that in fact bills above 25 % of list never trips the wire. The order says "after every outside call"; unreported calls are outside calls whose billing we simply do not know, and the ledger carries a `usd_unreported_estimate` that the tripwire ignores. Evidence base is 127/127 reported calls, so likelihood is low, but the gap is real and the failure direction is the unsafe one (reserve stays at 25 % → a later, larger overshoot).
- **[P3]** `_settle(key, backend=None, ...)` skips the tripwire block entirely (`if backend is not None:`). If any settle path for an xAI call passes `backend=None`, that call's trip is silently missed. This is pre-existing structure (the `by_backend` accounting has the same gate), but the order's "after every outside call" makes it worth confirming that all xAI settle paths pass the backend.
- **[P3]** Race window: `_reserve_fraction(b)` (lock acquired and released) and `self._reserve(...)` (separate lock acquisition) are not atomic with respect to a concurrent `_settle` trip write. A trip landing between the two leaves one in-flight call reserved at 25 % after the trip is recorded. This is within the order's explicitly accepted "one call's overshoot" tail, but it is not literally "at once"; closing it would mean re-checking the trip inside `_reserve` under the same lock.
- **[P3]** If `_settle`'s ledger persistence fails after the in-memory trip write, the trip may be lost for the day. This inherits the ledger's existing write-failure behaviour (which raises, fail-closed), so it is consistent with M12, but the trip specifically is a fail-open artifact.

No P0/P1 here: the comparison itself is right, and every miss vector either matches the spec's wording or fails in the conservative direction.

---

## CHECK (2): That the trip holds for the day

**Correct.**
- `_reserve_fraction` reads the ledger under `self._lock()` and returns `None` (list reserve) whenever `reserve_tripped[b.name]` is present — so from the moment of the trip, every subsequent reserve for that backend in that ledger's day is at list.
- The trip is persisted in the ledger file, so it survives across `Router` instances pointed at the same day's ledger.
- Day rollover: `proof_ly.day_ledger` gives one ledger per day (21:10 ET → 21:10 ET); a new day's ledger has no `reserve_tripped` key, and `(d.get("reserve_tripped") or {}).get(...)` handles the absent key gracefully (backward compatible with pre-change ledgers). The test's day-2 leg proves the fraction re-applies on a fresh ledger.
- The trip is recorded once (guarded by `not ... .get(backend.name)`), matching "the first call that bills above 25 %".

**[P3]** Test nit: the day-2 leg does not assert day-2's ledger state. With the mutated `g._usage` (`usd_reported=0.02`), day 2's single call actually trips day-2's ledger too during settle — the test neither expects nor checks this. The claim under test ("a new day's ledger: 25 % again") is still proven by the call running, but the unasserted side effect is worth a line of assertion for clarity.

No P0/P1.

---

## CHECK (3): That nothing but the named back-end changes

**Correct.**
- `model_providers.json`: exactly one key added, to the xAI reasoning back-end only; comma placement valid.
- `_reserve_fraction` returns `None` (→ list, unchanged behaviour) when the spec has no numeric `reserve_list_fraction` **or** when `self.spend_path` is absent — so no-spend-path runs are untouched, and every other backend takes the `frac is None` branch in `Router.call` (`round(upper * frac, 6) if frac is not None else upper` → `upper`).
- The `_settle` tripwire is gated on `_num(f)` from the backend's own spec, so it cannot fire for a backend that does not name the fraction.
- Ruling 121's fit test is explicitly pinned back to list via `frac=False`, preserving its original semantics now that the JSON carries the key — correct and minimal.
- Heimdall, the $1.00 cap, and the take-settle-release cycle are untouched.

**[P3]** The `xai()` test helper now defaults to `frac=True` (keeping the JSON's 0.25). Only one call site in the diff was updated to `frac=False`. Any **other** `self.xai()` call site in the file (or any test elsewhere that builds this backend from `model_providers.json`) now silently reserves at 25 % instead of list. From the shown hunks I cannot see whether such call sites exist. The failure mode is loud rather than silent — a test asserting a list-reserve refusal would see the call fit and fail its `assertRaises`, and a test asserting a reserve amount would mismatch — so CI should catch it; but it should be confirmed before merge rather than discovered in CI.

**[P3]** New structural assumption: `b.spec` must exist on **every** backend object, because `_reserve_fraction` runs `b.spec.get(...)` for each backend in the `Router.call` loop and the tripwire line runs for every `_settle` with a non-None backend. All evidence suggests every backend is constructed from `model_providers.json` spec dicts (the Heimdall entry is right there in the JSON, and the test `Fake` carries a `spec`), but the base class is not shown; if any backend lacks `.spec`, `Router.call` raises `AttributeError` for it — fail-closed, but a regression for non-Grok traffic.

**[P3]** No range validation on `reserve_list_fraction`: a misconfigured `0` (if `_num(0)` is truthy → reserve 0), a negative value, or a value > 1 would misbehave. `_num` presumably checks numeric-ness only. The value is committed and reviewed, so risk is low.

No P0/P1: the blast radius is genuinely limited to the named backend.

---

## CHECK (4): The tests

**Strengths:**
- `test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day` is a well-constructed end-to-end: it proves the list reserve would not fit (0.69 + 0.3825 > 1.00) while the 25 % reserve does (0.69 + 0.095 625 < 1.00), asserts `upper_usd` numerically, runs two sub-threshold calls (no trip), trips on the third with all five record fields asserted, asserts the notice, asserts the next call is refused at list with `g.calls` unchanged (the refusal happens before the backend is invoked), and proves day-2 reset with a fresh ledger. Arithmetic checks out throughout (0.3825 = 1.25 × 0.306; 0.013 75 = 0.25 × 0.055; 0.73 = 0.69 + 0.01 + 0.01 + 0.02).
- `test_only_a_back_end_that_names_the_fraction_is_reserved_below_list` correctly isolates the opt-in: no key → list → refused.
- The ruling-121 adjustment (`frac=False`) is the right way to keep an older gate testing what it always tested.

**Gaps:**

- **[P3]** The exact boundary is untested: no case with `billed == f * list` exactly. The `>` operator is correct per "above" (equal must not trip), but a mutation flipping `>` to `>=` would survive every shown test. One line (`usd_reported = 0.01375`, assert no trip) would close it.
- **[P3]** "Mutations Q1-Q4 after a control" are referenced in the summary but not present in the diff — cannot be verified from this package. If they live in a separate file, fine; if they were promised and not written, that is a gate gap.
- **[P3]** Day-2 ledger state unasserted (see check 2).

No P0/P1: the tests exercise the trip, the hold, the reset, and the opt-in, and their arithmetic is sound.

---

## SUMMARY

The implementation matches RULING 123 (1) on every point I could verify: the threshold is 25 % of **list** (not of the reserve), the trip is first-only, persisted in the day's ledger, read under lock by every subsequent reserve, reset by a new day's ledger, and scoped to backends that name the fraction. All findings are hardening / coverage items in the P3 band — none is a wrong result, a missed gate, or a defect that must block merge.

Findings: 6 × [P3] (unreported-call trip gap; backend=None settle path skips the tripwire; reserve/trip race window; unverified `self.xai()` call sites now inheriting the fraction; `b.spec` assumption on all backends + no range validation on the fraction; boundary case and day-2 ledger untested, mutations unshown).

P1_OR_WORSE: 0