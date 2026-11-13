# glm-5.3-flash (z-ai/glm-5.3-flash) 76 s finish=stop usage in 14850 / out 2103 usd~0.076 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-1810, ruling 76)

## 1. WHAT THE OTHERS CAUGHT THAT I MISSED

- **grok's P0 (REPOST_ALIGN_MIN not in the diff):** I treated the 0.80 as present because the expression resolves at call time; grok's point that the *diff alone* doesn't show it was fair, and the consensus note (ruling 53's constant, package.py:877, test passes) settles it. I under-weighted "verifiable from the diff" discipline.
- **grok's P1 (can a later seed revive an expired candidate?):** I assumed `seed()`'s key-not-present guard made this trivially safe. The consensus's pinned test (seed a later passing record, stays closed, never due) is exactly the durability proof I didn't demand.
- **glm's P1-1 (why-attribution order):** I noted the elif ordering but didn't flag that the *reported* reason can disagree with the ruling-76(d) `inside_12h` count.glm's P1-3 (transient inputs.json read error → permanent expiry, fail-closed but lossy) — I missed the "permanently lost to a transient OSError" framing entirely.

## 2. AGREE / DISAGREE

- **grok P0 (REPOST_ALIGN_MIN):** agree it was a legitimate diff-visibility concern; resolved by the consensus note (ruling 53's constant, test passes). Not a defect.
- **grok P1 (seed revival):** agree, and the new test at diff lines 278–283 closes it. Disagree with residual doubt: `seed()` only adds when the key is absent, and the test proves a later passing record neither reopens nor re-dues the expired line-up.
- **qwen P0-1 (difflib fuzzy vs L-k):** partially agree. The consensus refutation is right that L-k governs lock-text fidelity, not exclusion, and that strict equality would miss every re-post cut differently. But qwen's underlying instinct — that 80 %/run-3 can merge genuinely different speeches — survives as a residual utility risk, not a compliance bug. Downgrade to P2.
- **qwen P0-2 (ctx.now vs pin-stage clock):** agree with the consensus refutation — ruling 76 (c) says "at the moment they would render," so the later, tighter clock is correct, not a bug.
- **glm P1-1 (why-order):** agree it's a reporting-accuracy issue, not a leak; the ruling's *effect* holds on every path. P2.
- **glm P1-3 (transient read error → permanent expiry):** agree, P1. Fail-closed is ruling-compliant, but a transient OSError at 18:10 permanently kills a 2 h-old candidate with no recovery path, since expiry is for good by design.
- **glm P1-4 (build clock vs pin clock):** agree, and it's *by design* — the pin clock is later, so it only tightens. Not a defect.

## 3. NEW FINDINGS (nobody caught these in Cycle 1)

**N-1 (P1) — proof_ledger.py:207–215: the publish-time harvest reads only the record that *seeded* the candidate (`e["source"]`), not the record that *found* each moment.** If a candidate's line-up was extended or re-dered by a later record (the 16:30 Nov 13 build's search re-forms line-ups — the diff's own comment at candidates.py:52–54), a moment found by a different record's inputs.json is invisible to the harvest. It gets no publish time → "no known publish time" → the whole candidate expires. Fail-closed, ruling-compliant, but a *silent* wrong-expiry that the ruling-76(d) counts won't explain. Concrete scenario: candidate seeded from record A (moments a,b,c), a later record B re-punctuates and finds a,b,c,d; the registry's `lineup` now includes d (if the search re-formed it), but the harvest reads only A's inputs.json → d has no publish time → candidate expires despite d being 1 h old. *Uncertain whether the search actually extends line-ups in the registry; the diff's comment says the search "re-wrote" a resting candidate, so it's plausible. Flag, don't assert.*

**N-2 (P2) — proof_ledger.py:244: `inside_12h` counts `not PK.expired(m, now)` over ALL moments, not just the ones the build actually considered.** The ruling-76(d) STATE line 1 count "moments inside 12 h" is computed over the full moment list, including moments already excluded by delivered-overlap, opt-out, or hard exclusion. The count is therefore an upper bound, not "moments inside 12 h *and available*". Whether the owner's "moments inside 12 h" means the pool or the universe is not determinable from the diff. Flag as ambiguity, not a defect.

**N-3 (P2) — package.py:112–115: the same-speech elif runs a full O(spans × moments) `same_speech` twice per moment (once in `any(...)`, once in `next(...)`).** Purely a performance note; the `next()` re-evaluates the same predicate. No correctness impact.

**N-4 (P2) — package.py:88–93: `expired()` imports package_pin inside the function, and package_pin imports... (uncertain: the diff doesn't show package_pin's imports).** If package_pin imports package at module level, there's a potential circular-import risk that only works today because `expired()` defers its import to call time. Works, but fragile. *Uncertain — the diff doesn't show package_pin's import block.*

**N-5 (P2) — proof_ledger.py:197–199: the --hours refusal prints to stderr and returns 2, but the test at 303–310 asserts the 12/6 runs *raise* AssertionError ("went on to write a proof dir") rather than return cleanly.** The test's guard mechanism (refused_only / the proof-dir guard) is not shown in the diff, so the assertion that the run "went on" is verified only by the test's own guard, not by anything in the diff. *Uncertain; the guard is presumably pre-existing test infrastructure.*

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** none.

**P1 HIGH:**
1. **proof_ledger.py:207–215 (N-1):** publish-time harvest reads only the seeding record's inputs.json; a moment found by a different record silently expires the candidate. Fix: harvest from every record that contributed to the line-up, or at minimum log which record's inputs.json was consulted per candidate so a wrong-expiry is diagnosable.
2. **proof_ledger hedged by design (glm P1-3):** a transient OSError on inputs.json permanently expires the candidate. Fix: distinguish "file unreadable" (retryable) from "no publish time" (expired), or log the read failure into the expiry `why` so the loss is attributable.

**P2 MEDIUM:**
3. **package.py:112–117 (glm P1-1):** why-attribution order — a stale same-video-overlap moment reports "delivered (or overlaps...)" not "ruling 76 (a)"; the ruling-76(d) count and the why reasons can disagree about why a moment is out. Reporting only.
4. **package.py:85 (qwen residual):** same_speech's 80 %/run-3 heuristic can merge genuinely different speeches sharing a long common phrase; fail-closed, utility-only.
5. **proof_ledger.py:244 (N-2):** `inside_12h` counts the full moment universe, not the available pool; ambiguous vs the ruling's intent.
6. **package.py:112–115 (N-3):** same_speech predicate evaluated twice per moment (any + next); performance only.
7. **package.py:91 (N-4):** deferred import of package_pin inside expired() — works, fragile if package_pin ever imports package at module level. Uncertain from diff.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Log, into each expiry's `why`, *which record's inputs.json was consulted and whether the read succeeded* — it converts both P1s (silent wrong-expiry from the wrong record, silent loss from a transient read error) into diagnosable, attributable failures without changing any ruling-76 behavior.

## 7. PRODUCTION READY?

**Yes with conditions.** No P0s; every ruling-76 path excludes correctly and fail-closed, the registry expiry is provably durable (the pinned revival test), the window cannot be widened past 12, and the pin-stage re-check uses the later, tighter render clock. Conditions:

1. **proof_ledger.py:207–215:** the expiry `why` must record the source of each publish time (which record's inputs.json) and whether the read succeeded, so a wrong-expiry or transient-read loss is attributable after the fact.
2. **package.py:112–117:** either reorder the elif arms so `expired` precedes the delivered/same-speech checks, or add a note to the ruling-76(d) counts that `why` attribution is order-dependent — the STATE line's counts and the why reasons must not be the only record of *why* a moment died.

Both conditions are reporting/observability fixes; neither changes what the ruling excludes. Ship.