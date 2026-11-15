# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 23 s finish=stop usage in 13090 / out 1079 usd~0.092 (upper-bound price)

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Grok caught the exact `continue` after `if v is None` in `tail_variant.py:96` (pre-fix) that dropped the parent entirely on a non-matching `ends` (no fallback to normal hold/ceiling triggers, violating “the rules stand”). I had only flagged the duplicate-parent dict-comprehension loss.  
Qwen caught the pre-canon `E.spoken` + manual slice + implicit “...” strip in the original `directive_variant` (lines 62-67 pre-fix), a potential L-k violation. I had reviewed the canon call but missed that the strip was outside the single canonical form.  
GLM caught the non-list `{"directives": 5}` TypeError outside the try (proof_ledger.py:155 pre-fix) and the one-sentence parent silent-ignore. These were outside my Cycle-1 scope.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- Grok’s medium on bad-ends parent drop: fully agree; the fixed `if v is None: notes…` (no `continue`) + later `notes[mid] = (notes.get… + "; " …)` merge now lets normal triggers run and keeps both notes. Mutation D11 killed.  
- Qwen’s L-k critical on ad-hoc normalization: agree on the original risk; disagree it was still critical post-fix—the strip is gone, `C.canon_tokens(E.spoken(...))` is now the sole path, and test_ruling_104.py:245-246 confirms canon drops “...” idempotently.  
- GLM H1/H4 (silent drops, alternative_to=""): agree these were consistency warts; the new strict `directives()` regex + type + non-blank checks (lines 162-165) plus test with malformed rows (lines 284-294) close them.  
- GLM H5 (ceiling bypass): partially agree—the `continue` after adding directive variant still skips *for_pool’s* local ceiling check, but background + test with 35 s ceiling + later `pool.usable` on every returned moment (including variants) makes it non-breaking.  
- GLM H6 (IndexError on empty segments): agree it exists but is unchanged by this diff; not introduced here.

**3. NEW FINDINGS FROM THIS REVIEW**  
<medium> pipeline/tail_variant.py:174 (spot_place call site) + proof_ledger.py:174: `pk["segments"][0]["channel_id"]` remains; a package with `"segments": []` (possible from upstream malformation) raises IndexError inside the ledger `try` but is *not* in the `except (PinRefused, ValueError, OSError)` tuple, crashing the build instead of recording a refusal note. Concrete sequence: malformed package reaches `main()`, `spot_place` line 174 → uncaught IndexError → ledger build aborts. (Not new to this diff, but surfaced by the added `spot_place` extraction.)  
No other breaks verifiable from diff + background. All 14 mutations remain killed; directive path cannot reach pin without a validated builder-written row; variant still faces every gate; ruling 90 one-per-day rule is identical for non-alternatives.

**4. REVISED SCORES**  
| Subsystem              | Cycle 1     | Cycle 2     | Why changed |
|------------------------|-------------|-------------|-------------|
| directive_variant path | <medium>    | none        | Bad-ends `continue` removed; canon path cleaned; one-sentence note added |
| directives() reader    | <medium>    | none        | Strict 20-hex, story-id regex, non-blank, non-list handling per GLM/Qwen |
| day_taken / spot_place | <medium>    | none        | Unified rule, explicit alt return, tests for second-alternative and unreadable record |
| ceiling / gate bypass  | <medium>    | <medium>    | Still skips local ceiling but downstream gates confirmed by background + test |
| segments[0] indexing   | not scored  | <medium>    | Newly visible after extraction to spot_place |

**5. FINAL PRIORITY LIST**  
P2 MEDIUM — pipeline/tail_variant.py:174 (and proof_ledger.py:174): add explicit check `if not pk.get("segments"):` before `[0]`, return refusal note (kill the IndexError path).  
No P0 or P1.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Unifying ruling-90 into `day_taken(..., alternative_to)` and having both pool and pin call it, so the single exception for a named alternative is explicit, testable, and cannot be bypassed without a validated directive row.

**7. PRODUCTION READY?**  
Yes with conditions: (1) address the remaining `pk["segments"][0]` IndexError with an explicit guard and test (P2 above); (2) add one test case passing a >35 s directive variant to confirm `pool.usable(seg_max=35)` still refuses it downstream. Once those two lines/tests land, the feature is ship-ready. All Cycle-1 findings are resolved.