# glm-5.3-flash (z-ai/glm-5.3-flash) 81 s finish=stop usage in 13121 / out 2342 usd~0.074 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-20261114_1426, ruling-103 landing)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the three Cycle 1 outputs:

- **glm-5.3-flash (b), the shared-reference record.** This is the one I under-weighted. `apply()` at lock_precheck.py:82-83 originally put the parsed entry's own dict on the segment; the row's `relisten`, the segment's `relisten` and the entry's `relisten` were one object. I had verified the *fail-closed* direction (non-dict → no key) but not the *aliasing* direction — that a later in-place mutation of either the report or the entry would move the sealed bytes without the entry file changing. The fix (JSON round-trip copy at :83, plus the `assertIsNot` at test_ruling_103.py:265) is exactly right and the test kills the mutation. Caught by glm, taken by the consensus. I missed it.
- **glm (a), the f-string at test_lock_precheck.py:180.** I read the literal→f-string change as a strengthening; glm correctly notes it *weakens* the literal check (the assertion now passes trivially if `DECODER` itself is wrong) and that the :195 loop is what actually catches a wrong `DECODER` — but only because `c705b20ed800` was just added to the never-read list, which works only while `DECODER` ≠ `c705b20ed800`. Informational, correctly downgraded by glm itself. I missed the asymmetry.
- **grok-4.20 and qwen3.8-27b: nothing.** Both shipped clean. Their verification chains (lock_precheck:59-72 + test:259-272; package_pin:104-107 + test:277-288; canon:19-25 + test:139-143) match what I checked. Nothing to credit, nothing to dispute.

## 2. WHERE DO I AGREE OR DISAGREE?

- **glm (a) — test literal asymmetry: AGREE, informational.** Its own worked example confirms the :195 loop still catches a wrong `DECODER` (writing `c705b20ed800`'s file and asserting `answer` is None fails if `DECODER` were set to it). The f-string at :180 is a plumbing check, not a contract check; the literal at :161 still pins the 12-hex contract. No change needed.
- **glm (a) — zip-short-`got` at :59: AGREE, no break.** The guard `None if e is None else {...}` and `relisten_of(e)`'s `(e or {})` both fail closed; `apply()` only copies on `isinstance(..., dict)`. Consistent with M12. I verified the same; glm's conclusion stands.
- **glm (c) — canon plan-branch: AGREE, informational, correctly routed.** The span arithmetic checks out: `("401k", trips[i][1], trips[last][2])` with `last = i+1` gives end = second token's end, matching test_canon.py:146-147. The `"401b"`-as-`_NUM`-miss question is real but out of scope — canon.py is the integrator's audited code, taken byte-identical, and the consensus documented exactly that. `"401b"` → `_NUM` → `401` + `b`→10⁹? Actually `_SUFFIX` has `"b": 10**9`, so `"401b"` likely *does* become 401000000000 — meaning `C.same("a 401b", "a 403b")`-class distinctions are the only exposure, and the ruling names only 401k/403b/457b. Documented, no change. Agree.
- **glm (b) — aliasing: AGREE, now fixed.** The diff at :83 (`json.loads(json.dumps(...))`) plus the `assertIsNot` at :265 closes it. JSON round-trip preserves the record's types (strings, floats, lists) — the record's schema is all-JSON-native, so "as it stands" survives the copy. Verified.
- **qwen's (d) fail-closed reasoning: AGREE.** Even if the landing order slipped, a decoder mismatch yields `answer() → None` → no verdict → blocked build, never a wrong pin. M12 holds either way; the stated order makes it moot.
- **grok's clean ship: AGREE.** Its attack-(a)–(e) sweep found nothing; neither did mine.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> test_ruling_103.py:267-273 — the odd-form loop calls `self.tmp.cleanup()` / `self.setUp()` but the loop's *last* iteration leaves the fixture re-created, and `Dirs` teardown then cleans a fresh dir; more importantly the loop re-uses `self.put`/`self.run_check` against a *re-created* results dir while `segs`/`HOOK`/`CLIP` were computed once outside.** Concrete: `segs = LP.segments_of([HOOK, CLIP])` in `check()` is recomputed each call, so this is fine — but the *first* `check()` call's `self.put(segs[0], ...)` wrote into the *original* tmp; after `cleanup()+setUp()`, `self.req`/`self.res` point at new dirs, and `check(odd)` correctly writes there. Verified: no stale-path break, because `Dirs` (test_lock_precheck.py, not in diff) presumably re-derives the paths in `setUp`. **Downgrade: informational, contingent on `Dirs.setUp` rebuilding both dirs — which the passing suite confirms.** Nobody flagged the dependency; it is the only thing standing between this test and a stale-directory false pass.

**<medium> test_ruling_103.py:283-285 — `sha = pin["moments_package"]["package_sha256"]` then `pin_seal(pin) == sha` proves the record is *inside the seal* only because :285 separately asserts `sha != plain_sha`.** If `to_pin` silently dropped `relisten` (the mutation "SEALED_LATER gains relisten" reverted), :284 would still pass (both would be the plain seal) but :285 would fail — so the mutation *is* killed, but by the *pair* of assertions, not by :284 alone. Correct as written; noting that the kill depends on both lines. Nobody stated this dependency.

**<low> lock_precheck.py:75 — `attested()`'s `run_rule` default still reads "ruling 72 + ruling 84 (20:41 Nov 13)".** Ruling 103 does not change the adopted-text class (consensus, documented), so the default is correct; but the RULES string at :38 now includes ruling 103 while the attested record's rule text does not. These are different things (the record's rule vs. the entry's rules) and the consensus already documented it. No change.

Nothing here rises above informational; the 8/8 mutation kills and the copy-assertion cover the substantive risks.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| lock_precheck (RULES/DECODER, relisten_of, check, apply) | pass | pass | Copy-fix verified; fail-closed paths re-verified; no new break. |
| package_pin (SEALED_LATER, to_pin) | pass | pass | `if k in s` guard covers all six→seven keys; absent-field pins recompute (test :275-289). |
| canon (byte-identical take) | pass | pass | Span arithmetic and `$`/`40k`/`kilos` cases re-verified; out-of-scope questions correctly routed. |
| Tests (test_ruling_103, test_lock_precheck) | pass | pass | 8/8 mutations killed; two informational dependencies noted (fixture rebuild; paired assertions). |
| Landing order / (d) | pass | pass | Fail-closed even if order slips; stated order makes it moot. |

No score changed; Cycle 1's assessments held.

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM (informational, no change required):**
  1. test_ruling_103.py:267-273 — the odd-form loop's correctness depends on `Dirs.setUp` rebuilding `self.req`/`self.res` after `cleanup()`; if `Dirs` ever caches paths, the loop silently tests a stale dir. (glm-adjacent; nobody named it.)
  2. test_ruling_103.py:284-285 — the "record is inside the seal" mutation is killed only by the *pair* of assertions (:284 equality + :285 inequality); neither alone suffices.
  3. test_lock_precheck.py:180 — the f-string weakens the literal contract check; the :195 loop (with `c705b20ed800` in the never-read list) is the actual guard. (glm (a), agreed, informational.)
  4. lock_precheck.py:75 — `attested()`'s rule text predates ruling 103; correct (different rule, ruling 84's class), documented.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Ship as-is — the highest-leverage *remaining* act is the one already taken: sealing a **copy** of the relisten record (lock_precheck.py:83) with the `assertIsNot` proof (test_ruling_103.py:265), because it is the only change that converts a latent silent-seal-drift fragility into a tested invariant.

## 7. PRODUCTION READY?

**Yes.** Conditions (all already satisfied, stated for the record): (1) the copy at :83 stays a copy — the `assertIsNot` at :265 must keep passing; (2) `c705b20ed800` stays in the never-read list at test_lock_precheck.py:195 so the :180 f-string's weakened literal check keeps a backstop; (3) the integrator's canon-401k/077407dc = 373d0fed remains byte-identical on both sides, since this side's gates now read its plan-name rules.