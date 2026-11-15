# glm-5.3-flash (z-ai/glm-5.3-flash) 101 s finish=stop usage in 13897 / out 2925 usd_reported=0.000794 usd~0.086 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid, RULING 105 builder side (lock_precheck / package_pin)

Scope: the 399-line C2 diff, judged against the ruling text, the integrator's field shape, and the C1 findings from qwen3.8-27b and glm-5.3-flash. I traced `ruling_105_fails` clause by clause, the decide/apply flow, the seal path, and the new test file.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting:

- **The canon gap (both reviewers, C1).** The C1 code compared raw strings; the ruling's own must-fail list uses `'68,000' / '86,000'` with commas, so the record may legitimately carry formatted tokens, and law L-k says every text comparison goes through canon. I under-weighted this in C1 — I treated it as a formatting nit when it was the single most likely divergence between the integrator's pass and this side's hold. Both reviewers independently converged on it; that convergence was the tell I should have acted on.
- **The adopt_spoken hole (glm).** `decide()` ran the re-check only for `out in PASS`, so an adoption resting on a bad record sailed through unchecked. I missed it. The fix (run the re-check for `PASS` and `adopt_spoken` alike) is correct and the new test `test_an_adoption_that_rests_on_the_record_is_checked_too` pins both directions (bad record → hold, good record → adopt). This was the best catch of Cycle 1 and it was not mine.
- **glm's self-downgrades.** Its two other "P1"s (non-string readings, the record's own tests) were, as its own text concluded, fail-closed paths — P2s at most. I agree with the downgrades; the consensus correctly did not act on them.

What they missed that I had: the seal-compatibility question (glm's (3) — the key enters the seal only when a segment carries it, and the frozen 3f481f5a pin is tested to recompute) and the "hold never becomes a pass" question. Both are now confirmed by test, so they're settled, not open.

## 2. WHERE DO I AGREE OR DISAGREE?

**Qwen's P1 (canon) — AGREE, and the fix is right.** `_canon` now wraps every token: the record's token, every decoder reading, every second reading. Non-string → `None` → no match, no truncation → fail closed. The new test covers `'401K'`/`'401(k)'`/`'401'`-of-`'401k'` passing, `'86,000'` vs `'68,000'` still holding as (3), and `None`/`""`/`"  "` tokens holding. One subtlety worth noting: `_canon` returns `None` for a *blank* string via `C.canon(x) or None`, so `"  "` → `None` → "is not a number" — correct, and the test pins it. This is the right shape: canon at the boundary, raw values only in the error messages (`u.get('token')!r` — good, the why-string shows the record's own spelling, which aids debugging without weakening the check).

**Qwen's P2 (the truncation helper's suffix logic) — AGREE, no change needed.** `_truncation` requires the dropped suffix to be digit-free, which is exactly the ruling's "the token minus a NON-DIGIT suffix only". `'4015'`/`'401'` (a digit cut) correctly holds; `'401k'`/`'401'` correctly passes. The heuristic matches the ruling's words; nothing more is required.

**glm's P2 (shape validation) — PARTIALLY AGREE, still open.** The C2 code still reads only `token` from each reading and never validates `at`/`source` presence, and still trusts the record's `tests` booleans as *booleans* while separately re-deriving the substance. But note the consensus's own counter: "the record's own tests are re-derived anyway" — (1)/(2)/(3) are computed from the readings, so the `tests` dict is a redundant consistency check, not a trust point. That's defence in depth, not a gap. What *remains* genuinely unvalidated: a reading dict with a *missing* `token` key yields `None` → fails closed (good); a reading that is not a dict yields `None` → fails closed (good). So the residual exposure is only "this side's hold-why strings may cite a shape problem as a substance problem" — a diagnostic-quality issue, not a correctness one. **P2, fix or document; not a ship-blocker.**

**glm's (2)/(3) confirms — AGREE.** A hold outcome reaches the unchanged hold branch; the re-check can only turn pass→hold. The seal: `SEALED_LATER` and `to_pin`'s carry both gained the key, `package_pin.seal()` adds SEALED_LATER keys only when the segment carries them, and `test_the_record_is_sealed_and_a_pin_without_one_seals_as_before` proves both directions — a pin without the record seals byte-identically to before, a pin with it seals, the frozen 3f481f5a spotlight pin still recomputes, and a tampered reading changes the seal. That is the complete compatibility matrix. No finding.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] (NEW) `ruling_105_fails`'s "many-token" edge-form check is a key-presence test, not a verdict test — and the two are conflated.** Line 84: `if "tokens" in u or u.get("verdict") != "pass":`. The integrator's edge form is `{"tokens": [...], "verdict": "hold", "why": ...}` — a *hold* record. But a hypothetical `{"tokens": [...], "verdict": "pass"}` (a pass carrying the plural key) also holds here, which is fine, yet the *error message* for the plural form reads `the record's verdict is 'hold' (more than one disputed token)` — it reports the verdict, not the plural-ness, as the reason. Meanwhile the test `test_the_records_own_tests_and_verdict_must_agree` exercises the plural form only via its verdict="hold", so the plural-key-with-pass-verdict path is unpinned. Diagnostic clarity, not correctness: the record is held either way. Fix: mention the plural key in the why-string when present, or add the one-line test.

**[P2] (NEW) `_canon`'s `or None` silently maps a canon result of `""` to `None` — correct, but undocumented.** If `C.canon("")` returns `""` (plausible for a canon that strips to nothing), `_canon` yields `None` and the token fails the "is not a number" check — the desired outcome, but the docstring says "None for a non-string or a reading with no token", not "or a token that canonifies to nothing". One clause in the docstring, or trust the test (which does pin `""` and `"  "`). Cosmetic.

**[P3] (NEW) The `dec`/`sec` guard (line 89) requires `dec` non-empty but `sec` ≥ 2 — correct per the ruling ("at least two of the second recogniser's"), yet the (2) check's `len(set(st)) < 2` would also catch a single-reading `sec`.** Redundant, harmless, and the error messages differ ("too few readings" vs "(2) ... stable"), so the earlier guard gives the better message. No action.

**[P3] (NEW) `test_the_rules_and_decoder_are_the_integrators_ruling_105_ones` asserts `LP.RULES.endswith("+ ruling 103 + ruling 105")` while `test_the_rules_string_is_the_integrators` (the older test, line 171) asserts the full literal.** Two tests, two styles, same fact. The literal in the older test is the stronger pin; the endswith in the new one would survive a future ruling 107 silently. That's arguably *desired* (the new test shouldn't need editing when 107 lands), so: nit, note it, move on.

**[P3] (NEW) `unstable_of`'s guard `(e or {}).get(...) if isinstance(e, dict) else None` — the `e or {}` is redundant with the isinstance check** (the consensus even says the redundant `(e or {})` guard is gone from `decide`, but it survives here). Harmless; `unstable_of(None)` → `None` either way. Nit.

Nothing here rises to P1. The C1 P1s are genuinely closed.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| ruling_105_fails correctness (the three tests) | 8/10 | 9.5/10 | Canon now applied to every token; the comma/case paths are implemented *and tested*; the digit-suffix rule matches the ruling's words. Residual: shape-validation diagnostics only. |
| decide/apply flow (pass→hold, adopt, hold-stays-hold) | 7/10 | 9.5/10 | The adopt_spoken hole glm found is closed and pinned both directions; hold→pass remains impossible by construction. |
| Seal compatibility (package_pin) | 9/10 | 9.5/10 | Both directions tested (with/without the record, tamper, frozen 3f481f5a recompute). Nothing left to break. |
| Test coverage | 7/10 | 9/10 | 19 ruling-105 tests; the must-fail trio, the formatting paths, the adoption, the seal, the plural edge form. Only the plural-key-with-pass-verdict micro-branch is unpinned. |
| Overall | 8/10 | 9.5/10 | Both C1 P1s closed with tests; remaining findings are P2/P3. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (Both C1 P1s — canon, adopt_spoken — are implemented and tested; I verified the fixes in the diff, not just the consensus's word: lines 59–63, 91–92, 36–41, and the two new tests at 291 and 302.)

**P2 MEDIUM**
1. `pipeline/lock_precheck.py:84–85` — the plural/hold why-string reports the verdict, not the plural key; the plural-key-with-`verdict:"pass"` path is untested. Mention `"tokens"` in the why when present; add the one-line test.
2. `pipeline/lock_precheck.py:74–104` — the agreed field shape (`at`/`source`/`token` per reading) is never validated; only `token` is read. Either validate or state in the docstring that only `token` is consumed (glm's residual, correctly downgraded).
3. `pipeline/lock_precheck.py:59–63` — document that a token canonifying to nothing (`""`, `"  "`) also yields `None` (the test pins the behaviour; the docstring lags it).

**P3 NIT**
4. `pipeline/lock_precheck.py:110` — the redundant `(e or {})` inside the isinstance-guarded expression.
5. `tests/package/test_ruling_105.py:238` — `endswith` vs the older test's full literal; intentional or not, pick one convention.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Nothing — the highest-leverage *change* was the canon fix, and it's already in; the highest-leverage *remaining* act is the one-line why-string/test for the plural-key-with-pass-verdict path, because it's the only unpinned branch in an otherwise fully-pinned check.

## 7. PRODUCTION READY?

**Yes, with conditions** — and they're small:

1. (P2) Add the plural-key mention to the why-string at `lock_precheck.py:84–85` and the one-line test for `{"tokens": [...], "verdict": "pass"}` — or explicitly accept the current diagnostic and note it.
2. (P2) Either validate the agreed reading shape (`at`/`source`/`token`) or add one docstring sentence: "only `token` is read; anything else in a reading is ignored."
3. (P3) Sweep the two nits (redundant guard, endswith-vs-literal) in the same commit or never.

All three conditions are documentation/diagnostic-grade; none changes a verdict, a seal, or a gate. The C1 P1s are closed with tests, the must-fail trio holds, the adoption path is checked, holds cannot become passes, and the seal is proven backward compatible against the frozen 3f481f5a pin.

P1_OR_WORSE: 0