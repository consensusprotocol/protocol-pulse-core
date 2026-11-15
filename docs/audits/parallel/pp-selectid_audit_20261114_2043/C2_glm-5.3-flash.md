# glm-5.3-flash (z-ai/glm-5.3-flash) 141 s finish=stop usage in 13043 / out 3997 usd_reported=0.000900 usd~0.099 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid (RULING 107 Q1, fixed diff)

Second pass. I have the fixed diff (355 lines), the C1 outputs from glm-5.3-flash and Grok, and the consensus record. I re-traced the abandon path, both carry-over sites, the lock discipline, the ledger arithmetic, and the new tests line by line against the ruling text.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **glm F1 (unreadable-ledger blast radius in `reported_rate`).** The strongest finding of the cycle. I had treated the `except SpendLimit` catch as complete because the stated guard says `_ledger` raises `SpendLimit` on unreadable. glm correctly pushed past the stated guard: `_save`'s atomicity is not in the diff, so a concurrent reader can see a half-written file and raise `JSONDecodeError` (a `ValueError`, not `SpendLimit`), and a ledger missing `by_backend` raises `KeyError`. Since `reported_rate` runs inside the `abandon` closure and the `DeadlineExceeded` handler, an unexpected exception there converts a routine deadline miss into a call failure — the wrong failure direction for a cost-estimate helper. I under-weighted that the *stated* guard only covers one failure mode while the *code* must survive all of them. The fix (catch `SpendLimit, OSError, TypeError, ValueError`, fall back to list) is now in the diff at lines 32–33 and is the right shape: list price is the higher booking, so the fallback is conservative.
- **glm F3 (read-rate / write-booking gap).** I did not flag the benign TOCTOU between `reported_rate`'s read and `_settle`'s write. glm's analysis is exactly right and the docstring now states it (lines 46–48): a reported call landing between the two moves the rate by one call, and the ledger stays balanced because `_replace_booking` removes the booking *as stored* (`on_cap`, line 85/118), never a recomputed one. That last point is the subtle part — if the late answer removed a *recomputed* booking, the gap would not be benign. It removes the stored one. Correct.
- **glm F14 (rate applies only while abandoned).** I missed that a late answer *without* a vendor figure must be accounted at its own token counts' estimate (ruling 83 (a)), not keep the reported-rate booking. The new test at lines 313–324 pins it: `usd_unreported_estimate` ends at `slow.usd({in:1000, out:100})`, and the row's `in_reported` stays 3000 while `in` goes to 4000. Correct reading of the ruling.
- **Grok's confirmation of (4) via the two legacy-ledger tests.** I had verified the `_settle` site; Grok's framing made explicit that both sites (`_settle` line 72 and `_replace_booking` line 124) use identical logic and that the legacy tests exercise both. That symmetry check is worth having.

What nobody caught that I also missed in C1 — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**glm F1 (downgraded to P2 by glm, then fixed) — AGREE, and the fix is correct.** One refinement: the new catch at line 32 also covers the `isinstance` guards' failure modes, but note the guards at lines 30–31 run *inside* the `try`? No — they run after the `with` block, but lines 30–31 are inside the `try` (the `with` at 28–29 closes, then 30–31 execute, still within the `try` begun at 27). So `int(b.get("reported_calls") or 0)` raising `TypeError`/`ValueError` on a non-numeric `reported_calls` is caught. Good. The test at lines 326–341 exercises all four corrupt bodies plus no-spend-path plus no-row. This is now airtight. One residual: `_num(b.get("usd_reported"))` at line 34 and the division at line 39 are *outside* the `try`. If `usd_reported` were, say, a string, `_num` returns falsy → `None` (line 35) — fine. If it's a numeric string, `_num` presumably accepts it and `float()` at 39 succeeds — fine. If `toks` is a bool, `_num` passes and `float(True)` = 1.0 — harmless. No defect; noting the reasoning.

**glm F3 (read/write gap) — AGREE.** The docstring's justification is sound: the only inconsistency window is one call's worth of rate drift, and the removal-by-stored-booking property keeps the ledger balanced. I verified the removal: `_replace_booking` line 118 subtracts `booked_unreported` (the stored `on_cap`), not a recomputation. Balanced.

**glm F14 — AGREE.** The ruling's "the $20 cap is on that basis from now" governs the *abandoned* booking; ruling 83 (a) governs the late answer's own accounting. The implementation separates the two correctly: `usd` (list figure) stays on the estimate basis, `unreported` (the reported-rate booking) goes to the cap's basis, and a figureless late answer swaps the booking for its own estimate (line 127: `d["usd_unreported_estimate"] + usd`).

**Grok P2 (no test for unreadable ledger *during* the abandon closure's `booking_usd` call) — PARTIALLY AGREE, now resolved.** The new test at 326–341 calls `booking_usd` directly on each corrupt ledger (line 338) and asserts `(LIST, "list")`. That covers the abandon-closure's computation; what it does not cover is the *full* abandon path (the closure → `_settle` → `_save`) with a corrupt ledger, where `_settle` still raises by design ("an unreadable ledger raises here", line 139/143). That's the documented, unchanged behavior — `_settle` raising is pre-existing, not a regression. Grok's P2 is therefore satisfied in substance; the residual (corrupt ledger + abandon → `_settle` raises) is the documented status quo. No change required.

**Grok P3s (type hints, harness coupling, duplicated constant) — AGREE, all cosmetic.** No behavior impact. Note the constant duplication (glm/Grok) is now *worse* in one sense: the ruling text appears in the module docstring, the test docstring, and the consensus record — but the test's copy is a quotation, which is the right kind of duplication.

**glm's self-correction inside F1/F2 (the "Wait — re-reading" passage).** Its final conclusion — the catch is complete *given* the guard, but the guard may not hold because `_save`'s atomicity is unseen — is the correct epistemic state, and the implemented fix (widen the catch) makes the question moot. The widened catch covers `JSONDecodeError` (a `ValueError`) regardless of `_save`'s atomicity. That's the right way to close an uncertainty you cannot see: defend at the catch, not at the write.

**qwen's contribution (via the consensus record).** Its "[P1]"-tagged questions were, per the driver's reading, questions answered "correct" in its own text. I agree with the driver's reading: the substance (rate formula, carry-over, caller compatibility) was confirmations, not defects. The consensus's IMPLEMENTED/NOTED split is faithful to what the diff now shows.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] N1 — `reported_rate`'s `rows`/`b`/`n` computation: the `isinstance` guards are inside the `try`, but the *second* read of the ledger row happens after the lock is released.** Lines 28–31: the `with self._lock():` block covers only `rows = self._ledger()["by_backend"]`; then `b = rows.get(name) ...` and `n = int(...)` run *outside* the lock, on the already-extracted dict. This is fine — the dict is a private in-memory copy, no shared state. But note the asymmetry with the docstring's claim (line 46–47, "The rate is read under the ledger lock"): the *row* is read under the lock; the arithmetic on it is not, which is correct because the dict is detached. No defect — this is a confirmation, not a finding. Recording it because Grok's answer to (3) ("acquires the flock, reads, and releases") is precisely right and I want it on the record that I verified the detachment.

**[P2] N2 — `booking_usd`'s rounding: `round(rate * prompt_tokens_upper, 8)` vs. `_settle`'s 6-place rounding of the day totals.** The booking is stored at 8 places (line 54), then added into `usd_unreported_estimate` which is rounded to 6 (line 76–77), and the late-answer removal subtracts the 8-place stored value from a 6-place-rounded accumulator (line 117–118). Because the subtraction uses the *stored* 8-place value against an accumulator that was rounded to 6 after the addition, the final residue can differ from zero by up to ~1e-6 per abandoned-then-answered call. glm's C1 F5 (rounding residue of 1e-6, NOTED NOT CHANGED) covers exactly this; my addition is only the observation that the *removal* side uses the unrounded stored value, so the residue is bounded by the 6-place rounding of the accumulator, not by the 8-place booking. Still cosmetic: the cap compares against $20 with 6-place tolerance in practice. No change required; it stays NOTED.

**[P2] N3 — the `tried` message at lines 157–159: the f-string's conditional `{'its own reported rate' if basis == 'reported_rate' else 'list price'}` duplicates the basis→phrase mapping that the deadline log already records as `booked_basis`.** Two encodings of the same fact, in the same hunk. If a third basis ever exists, both must change. Cosmetic; the test at 230/242 pins both phrases. No change required.

**[P3] N4 — `test_the_rate_is_none_whenever_the_ledger_cannot_give_one` (lines 326–341) writes the corrupt bodies with `open(spend, "w").write(body)` without closing.** CPython's refcounting closes it promptly, so the subsequent read in `reported_rate` sees the full body; under PyPy or a future refactor this could flake. One-line fix: `with open(spend, "w") as f: f.write(body)`. Nit.

**[P3] N5 — the test at line 330 asserts `reported_rate` returns None with no `spend_path`, but the router fixture's default `limit_usd`/basis are unspecified there; the assertion holds because `spend_path` is falsy (line 25–26), which is the intended branch.** Fine as written; noting that the test's *first* case exercises the no-spend-path guard, which Grok's C1 P2 said was untested — it is now tested, at line 330.

**[P2] N6 — `booking_usd`'s signature takes `b` (the backend) and re-derives `b.name`, but `reported_rate` re-reads the ledger row by name; the abandon closure already holds `b` and could pass the row.** Not a defect — the re-read is the *point* (freshness under the lock). Recording it because it explains why the two-lock-sequence design is correct: the closure's `b` object is not the ledger row; it's the Backend. No stale-row hazard. Confirmation, not a finding.

**[P2] N7 — one genuinely new behavioral observation: the `DeadlineExceeded` handler (lines 156–160) computes `booked, basis = self.booking_usd(b, prompt, system)` a *second* time, independently of the `abandon` closure's computation at line 134.** Are they guaranteed to agree? The closure runs inside `_within`'s `on_abandon` (in the caller's thread, before the raise); the handler's computation runs after the raise. Between the two, another process could add a reported call, flipping `basis` from `list` to `reported_rate` (or changing the rate). Consequences: (a) the `tried` message's dollar figure may differ from the one actually booked by the closure — a cosmetic inconsistency in the message only, since the closure's booking is what enters the ledger; (b) `basis` in the message may disagree with the ledger's actual booking. The deadline log's `booked_usd`/`booked_basis` come from the closure (lines 135–142), so the *evidence* record is the authoritative one; only the `tried` message can drift. Cosmetic. But note the *double computation* also means the rate could be read twice under two separate locks — harmless, no deadlock (sequential, same thread).glm's F3 docstring covers the closure-side gap; this is the handler-side twin, which nobody named. It is the same benign class: message-only drift, ledger balanced. No change required; if the team wants one-line insurance, compute `booked, basis` once in the closure and have the handler read it from the abandonment record — but the closure's locals aren't in scope at the handler, so the current duplication is the simplest correct shape.

**[P3] N8 — `seed()` (test, line 190–196) uses `open(path, "w")` without a context manager, same class as N4.** Nit.

Nothing here rises to P1. The C1 fixes closed the only real defects.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Rate formula & threshold (Q1) | 9.5 | 9.5 | Unchanged; formula, 3-call threshold, and None-conditions all verified again, incl. the outside-`try` guards (§2). |
| Cap under-booking (Q2) | 9.5 | 9.5 | Unchanged; `prompt_tokens_upper` + all-in rate + 8-place rounding, conservatively high. |
| Locks/threads (Q3) | 9 | 9.5 | +0.5: verified the row dict is detached before the lock releases (N1) and the handler-side double-read (N7) is sequential, same-thread, deadlock-free. |
| in_reported carry-over (Q4) | 10 | 10 | Both sites, both legacy tests, both late-answer variants — unchanged. |
| Backward compat (Q5) | 10 | 10 | Defaults `None` restore prior arithmetic; unchanged. |
| Tests (Q6) | 9 | 9.5 | +0.5: the corrupt-ledger test now covers `booking_usd` directly (Grok's P2 resolved); residual nits N4/N8. |
| Ledger balance (late-answer removal) | 9.5 | 9.5 | Removal-by-stored-booking verified; 6/8-place rounding residue noted (N2), cosmetic. |

No score dropped. The C1 fixes raised the two subsystems they touched.

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM:**
  - **N7** — providers.py, lines 156–159 (diff) / the `except DeadlineExceeded` handler: `booking_usd` is computed a second time, independently of the closure's; the `tried` message's `$` and `basis` can drift from the actually-booked values under concurrent reported-call additions. Message-only; ledger stays balanced. Should fix (or accept and note) — the deadline log remains authoritative.
  - **N2** — providers.py, lines 54 vs 76–77 vs 117–118: 8-place booking vs 6-place accumulator rounding; residue ≤ ~1e-6 per abandoned-then-answered call, removal side uses the stored 8-place value. Should fix only if the cap's comparison needs better than 1e-6; otherwise NOTED, as in C1.
  - **N3** — providers.py, lines 157–159: the basis→phrase conditional duplicates `booked_basis`'s encoding. Should fix if a third basis is ever added.
- **P3 (nits):** N4 (test, line 336: unclosed `open().write()`), N8 (test, line 196: same), N5 (line 330, documentation of coverage), N6 (design note, no action).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Nothing must change: the C1 fixes (the widened catch in `reported_rate` and the removal-by-stored-booking property) closed the only defects, and the highest-remaining leverage is documenting — in `booking_usd`'s docstring, one clause — that the `DeadlineExceeded` handler's second `booking_usd` computation is message-only and the deadline log's closure-side record is authoritative (N7).

## 7. PRODUCTION READY?

**Yes.** Conditions (all already satisfied or cosmetic): (a) the widened catch at lines 32–33 stays — it is the load-bearing fix; (b) the 11 ruling-107 tests plus the 75 existing provider tests pass, which the consensus record states; (c) the P2s (N7, N2, N3) are acknowledged, not necessarily fixed — none affects the ruling's contract, the cap's correctness, or the ledger's balance.

P1_OR_WORSE: 0