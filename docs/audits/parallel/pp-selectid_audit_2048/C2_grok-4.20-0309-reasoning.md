# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 29 s finish=stop usage in 18139 / out 1164 usd~0.120 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok caught the original on_abandon() exception ordering (providers.py:296 in Cycle 1) where a SpendLimit would skip the missed_deadline log and alter Router.call failover; the diff now logs first (line 295) then settles, with a new test exercising corrupt-ledger-at-deadline. I missed this interleaving. Qwen caught the on_late exception swallowing and ledger-write fragility; the new _replace_booking (lines 259-281) plus explicit catch-and-log (lines 252-254) addresses it. I also under-weighted the exact usd_unreported_estimate subtract-then-add path that Qwen flagged as dependent on abandon().

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Grok P2 (providers.py:296): fully agree; the fix and test (lines 550-568) verify missed_deadline is written even on SpendLimit, ledger stays untouched, and next backend is skipped (fail-closed).  
- Qwen P0-1 (race in _within): partially agree on the scenario but the consensus is correct—the new lock + "if not done.is_set()" guard (lines 208-209) plus box["abandoned"] set under lock makes the race verifiable and intended (on-time answer wins; abandoned path only taken when still running). The ordering test (lines 588-613) confirms ["booked", "answered", "booked done", ("late", ...)].  
- Qwen P0-2 / ledger arithmetic: agree the original was fragile; new _late/_replace_booking makes the subtract-book-then-delta logic explicit and test-covered (lines 499-516, 531-542) with no double-count.  
- Both on class_84: agree. The implementation (attest.py:44-61) matches the five integrator rules in the ruling and docstring; tests (test_attest.py:354-376, test_lock_precheck.py:409-431) cover fillers-spoken-only, one-function-word (and the second holding), criticals, 2-for-2, approved-side filler, and carry_class unchanged. The 20:12 span now adopts.  
- Qwen P1 on_late swallowing: agree it was real; now isolated, caught, and logged with "replaced: false".

**3. NEW FINDINGS FROM THIS REVIEW**  
None at P0/P1. Verifiable from diff only: prompt_tokens_upper is conservative (char count + 200 + images, never under-books per ruling 83(a) comment); reservation is released at deadline (no residual "reserved" entry, test line 502/517); _replace_booking is atomic under self._lock() with os.replace semantics implied by prior ledger code; late thread never uses the answer text (verifiable: value only unpacked for usage, never stored). The round(..., 8) on usd_reported (line 275/277) is the sole inconsistency vs. 6-decimal paths but only affects the reported basis and is test-covered. No deadlock (lock released before on_late call). Nothing the integrator held can adopt here (any None class => hold, line 119).

**4. REVISED SCORES**  
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| providers ledger & deadline | P2     | clean  | Fixes for ordering, atomic _replace_booking, exception logging, and new racing/ledger-corrupt tests resolve all arithmetic and fail-closed concerns verifiable in diff. |
| attest / lock_precheck | P2     | clean  | class_84 now explicitly matches all 5 integrator rules; comprehensive tests cover the exact held span and all must-hold cases; RULES string updated. |
| Overall                | SHIP with 2×P2 | SHIP yes | All Cycle 1 items implemented or refuted by the diff and tests. |

**5. FINAL PRIORITY LIST**  
**P2: pipeline/providers.py:273** (usd_unreported_estimate subtracts booked then conditionally adds usd; arithmetic is correct per tests at 499-516 and 535-542 but assumes abandon() and _late() always see identical booked value—verifiable they do, yet any future drift in prompt_usd would be silent).  
No P0 or P1 verifiable from diff. All design choices (late estimate > prompt booking, reservation release, char-based prompt count, exact match to integrator's 5 rules) are explicitly documented and test-covered.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The lock in _within (lines 196-209) plus logging-before-booking in abandon() guarantees the prompt-token booking and missed_deadline line are written before any late replacement or exception, making accounting fail-closed even on corrupt ledger.

**7. PRODUCTION READY?**  
Yes. All ledger arithmetic produces exact on-time numbers with no double-count (tests 490-517, 531-542); booking always precedes late logic (test 588-613); class_84 implements the five integrator rules exactly (docstring + tests 354-376, 409-431); nothing integrator-held adopts here; cap/stop updated per 83(b); no violation of M12, L-j, L-k, or smallest-diff constraints visible in diff.

**P0: none verifiable from diff**  
**P1: none verifiable from diff**  
**P2: providers.py:273** (see #5; minor rounding inconsistency but tests pass and math holds)  

SHIP: yes