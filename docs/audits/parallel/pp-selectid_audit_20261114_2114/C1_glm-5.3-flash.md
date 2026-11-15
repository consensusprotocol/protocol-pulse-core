# glm-5.3-flash (z-ai/glm-5.3-flash) 76 s finish=stop usage in 5901 / out 2002 usd_reported=0.000431 usd~0.048 (upper-bound price)

# Audit: C1_STEP — RULING 108 ledger/stop/limit change

**Scope reviewed:** the 60-line diff only (proof_ly.py, test_ruling_102.py), plus the stated unchanged guards. I am one of three independent reviewers; findings below.

---

## Answers to the three questions

**Q1 — Can any build path still write the closed SPEND_LY.json?**

Within the diff, no. `SPEND` is rebound to `SPEND_B3.json` at module level, and the unchanged guard `proof_ledger.build_router(..., spend_path=PL.SPEND, ...)` means every router built through that call writes the new ledger. The test additionally pins `PLG.PL.SPEND.endswith("SPEND_B3.json")`, so a regression to the old path fails the suite. Two residual risks worth noting (not defects in this diff):

- [P2] Any *other* module that references `SPEND_LY.json` by its own literal (not via `PL.SPEND`) is invisible to this diff and unpinned by the test. The test only pins the module attribute, not the filesystem. A cheap strengthening: after a run, assert `SPEND_LY.json`'s mtime is unchanged, or assert the new file exists after one router construction. As written, if some second call site hardcodes the old path, the test still passes.
- [P3] The comment "SPEND_LY.json is the closed $20 order's" is the only documentation of the closed ledger; nothing in code marks it read-only. If a future ruling reopens it, nothing fails. Acceptable for a 24 h batch.

**Q2 — Are stop and limit consistent with "never start a build that would end over the cap"?**

Yes, with one caveat about the *invariant* vs the *mechanism*.

The invariant: builds cost $0.15–$0.50, stop at $4.00, so a started build ends at ≤ $4.50 = the limit. The reservation mechanism ("each paid call RESERVES its upper bound while in flight") is what actually guarantees the limit is never passed — the stop is only an efficiency/STATE-line rule, not the cap. That's consistent, and the diff's comments state it correctly.

- [P2] The reasoning "a build runs $0.15–0.50, so none ends over $4.50" is a comment, not an enforced invariant. If a single build's upper bound ever exceeds $0.50 (price-table change, model price hike), the stop-at-$4.00 + limit-$4.50 pairing silently loses its 1×-build headroom. The test pins the *numbers* (4.00/4.50) but not the *relationship* `LY_LIMIT_USD - LY_STOP_USD >= max_build_upper_bound`. One extra assertion (`self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)`) would pin the headroom, not just the constants. As written, a future ruling that moves the stop to $4.40 keeps the test green while breaking the documented reasoning.
- [P3] `LY_STOP_USD = 4.00` with the refusal condition `spent0 >= LY_STOP_USD` means at exactly $4.00 no build starts — the test checks `start_refused(4.0)` is truthy and `start_refused(3.99)` is None, which correctly pins the inclusive-at-the-stop boundary. Good. Note the comment says "No build starts at or over $4.00" — consistent. No finding.
- [P3] The limit basis stays `"reported"` (unchanged), so the $4.50 cap is enforced on vendor-reported dollars only, with the price-table estimate counted only where a vendor reports none. That matches ruling 48's semantics carried forward; the ruling-108 text says "VENDOR-REPORTED" explicitly. Consistent; no finding.

**Q3 — Does the test pin the behaviour?**

Mostly yes, with one gap.

- [P2] The test pins the constants as a *tuple equality* — `assertEqual((STOP, LIMIT), (4.00, 4.50))` — which is fine, but it does not pin `LY_LIMIT_BASIS == "reported"`. The limit's meaning depends entirely on the basis (ruling 48: the estimate counts only where a vendor reports none). If someone flips the basis to `"estimate"` or `"all_in"`, the $4.50 cap changes meaning while the test stays green. One line: `self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")`. Given the ruling text says "VENDOR-REPORTED" explicitly, this is a should-fix, not a nit.
- [P2] The renamed test (`test_no_build_starts_at_the_stop_and_one_starts_below`) now asserts four things but its docstring cites the 13:02 Nov 14 ruling and ruling 108; the *old* test's docstring-cited ruling (the $16→$19 history) is dropped. That's fine — history lives in the diff comments — but the test no longer checks that STATE line 1 actually *says* the capitals message; it only checks the returned `why` string contains it. If `start_refused`'s contract includes writing STATE line 1, that side effect is unpinned. If the STATE-line writing happens in the caller (orchestrator), this is a [P3]; flagging as [P2] because the docstring claims "STATE line 1 says so in capitals" and the test verifies only the message *content*, not the *saying*.
- [P3] `assertTrue(PLG.PL.SPEND.endswith("SPEND_B3"))` — actually the test uses `.endswith("SPEND_B3.json")`, which would also match a hypothetical `SPEND_B3.json.bak` or `.../SPEND_B3.json2`; trivial. Also `assertIsNone(PLG.start_refused(3.99))` pins the below-stop case only at one point; a boundary test at 3.999… vs 4.0 is the same case. Fine.
- [P3] The test class is `TestOnThePinAndOnState` — the new assertions about ledger path and constants are arguably not "pin and state" concerns but they were before too (the old test lived there). No action.

---

## Other observations on the diff itself

- [P3] Line 10–11: the module docstring now reads "SPEND_B3.json since ruling 108; SPEND_LY.json is the closed $20 order's) holds the price-table estimate beside the" — the parenthetical spans a line break and the closing paren lands mid-sentence; the sentence still parses but the line-wrapped parenthetical makes the docstring harder to read. Cosmetic.
- [P3] Lines 26–32: the new comment block's continuation lines are column-0 `#` comments rather than aligned continuation comments (the old block aligned continuations under the assignment). Inconsistent style with the replaced block; the *content* (reservation mechanism, "none passes the limit") is preserved. Cosmetic.
- [P3] Against the governing laws: this diff touches only the proof/ledger harness, not the pipeline. No law (SENTENCE, SELECTION LOCK, SNAP LIMIT, L-a…L-l, LAW 20/M2, M12, LAW 22) is engaged. LAW 20's "gate thresholds are constants" is satisfied — the thresholds *are* module constants, and the test pins them. M12 fail-closed: a missing ledger file = empty = $0.00, which is a *pass* condition, not a missed failure; that's the correct fail-open-on-absence semantics for a fresh batch (a missing ledger at batch start is the expected state, not missing data mid-run). No violation.
- [P3] M1 "smallest diff": the diff is 60 lines, two files, no new renderer/compositor/selector, no GPU, no publishing. Compliant.

---

## Summary of findings

| # | Severity | Finding |
|---|----------|---------|
| 1 | [P2] | Test doesn't pin `LY_LIMIT_BASIS == "reported"`; basis flip changes the cap's meaning silently |
| 2 | [P2] | Headroom invariant (limit − stop ≥ max build upper bound) is commented, not asserted |
| 3 | [P2] | Test pins the module attribute, not the filesystem; a second hardcoded `SPEND_LY.json` call site would pass unnoticed |
| 4 | [P2] | Docstring claims STATE line 1 "says" the message; test verifies message content only, not the saying |
# Audit: C1_STEP — RULP1_OR_WORSE: 0

**P1_OR_WORSE: 0** — no [P0] or [P1] findings; the change is correct as written, with four [P2]s (basis not pinned, headroom invariant unasserted, filesystem not pinned, STATE-line side effect unverified) and assorted [P3]s.

**Verdict: APPROVE (with the four [P2]s recommended before or at merge).**