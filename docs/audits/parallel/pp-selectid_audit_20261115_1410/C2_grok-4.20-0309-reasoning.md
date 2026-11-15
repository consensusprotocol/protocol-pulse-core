# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 21 s finish=stop usage in 44384 / out 1206 usd_reported=0.061746 usd~0.252 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid-20261115_1410 (RULING 115 (1)+(2) — Calibrated Hook Bar, post-fix)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   In Cycle 1 I fully traced the per-candidate loop, the new HOOK_VERSION, the outside-seal mark, and the exclusion of the hook from COHERENCE_MIN, but I missed the subtle cached-rater mismatch (a stale Grok rating would block re-ask after a routing change) and the naive-datetime TypeError path that lived outside the try in bar(). I also under-weighted how the global _LIVE dict + mtime+minute key interacts with test fixtures that clear it. Grok and the consensus caught both; qwen caught the future-measured_at stretching the 24 h window. Those three items were genuine oversights on my part.

2. WHERE DO YOU AGREE OR DISAGREE?
   - Grok [P1] on verdict/min change: agree it was a real semantic expansion beyond the literal “nothing else changes” sentence, but the consensus reading (hook slot = bar, clips keep COHERENCE_MIN) is the only reading that makes a scroll=3 floor usable. Not a defect after the explicit orchestrator note on STATE line 1.  
   - qwen [P1] on future measured_at + naive time: fully agree; both are now fixed with clear refusal messages and a new test (B10/B11 mutations killed).  
   - Consensus fixes for cache-key seed, listed-rater-only cache lookup, and spotlight pin carriage: agree all were necessary and correctly implemented.  
   - Grok [P2] on rater=None asymmetry in bar()/passes(): partially agree — the code now documents it, but the contract remains subtle; a caller supplying a mismatched non-None rater would still produce a confusing failure.

3. NEW FINDINGS FROM THIS REVIEW
   [P2] hook_bar.bar() constructs fl = {p: int(cal["floors"][p]) for p in PARTS} after the KeyError/TypeError catch block has already returned “no readable measured_at or floors”. A calibration missing the “floors” key entirely (or containing a non-numeric value that int() rejects) therefore produces the generic message instead of the more precise “a floor under 3” or “missing floors” text that the builder log and Telegram note expect. The test suite never hits this exact shape because load() + write() always produces a well-formed dict. (pipeline/hook_bar.py:82 and :92)
   [P3] providers._shadow_ask builds rec["kind"] only for the shadow record; the deciding reply’s cached/replayed flags are still copied verbatim into the shadow log even when the shadow chain is the dedicated “shadow86:coherence_verdict:hook”. Minor log noise, not behavioral. (providers.py:671)
   [P3] conftest.py rigs only package._live_bar(); test_hook_bar.py (real_hook_bar=True) still exercises the live file, but a future change to hook_live_bar() that touches os.stat() timing could silently break the once-per-minute cache test. Not a defect today.

4. REVISED SCORES
   | Subsystem          | Cycle 1 | Cycle 2 | Why changed |
   |--------------------|---------|---------|-------------|
   | hook_bar.py        | 9.2     | 9.7     | Future-time + naive-datetime fixes + explicit SKEW_MIN test |
   | package hook path  | 8.1     | 9.4     | Cache-rater fix, per-candidate loop, clear “passes” propagation |
   | verdict integration| 7.8     | 9.0     | Explicit exclusion of hook from COHERENCE_MIN now documented |
   | shadow & routing   | 9.0     | 9.5     | Dedicated kind chain prevents cross-talk |
   | tests & mutation   | 9.5     | 9.8     | 31/31 mutations killed, new live-cache test |
   | seal / law surface | 9.3     | 9.6     | Mark explicitly outside pin_seal, all L-* laws re-checked |

5. FINAL PRIORITY LIST
   [P2] pipeline/hook_bar.py:82 — give missing “floors” key its own refusal message before the generic except block (improves builder log and matches “every part >= its floor” contract).  
   [P2] pipeline/package.py:458 — add explicit comment that hook_own() calls _live_bar() on every hook_own() invocation (currently hidden behind the once-per-minute cache); makes the mtime dependency obvious for future readers.  
   [P3] pipeline/providers.py:666 — rename “own” variable to “shadow_chain_key” for clarity.  
   No P0 or P1 items remain.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   The explicit per-candidate asking + HOOK_VERSION that includes both asking mode and seed 7, combined with the listed-rater-only cache filter, ensures the calibration’s measured bytes are the only bytes that can ever produce a passing hook.

7. PRODUCTION READY?
   Yes with conditions: (a) the [P2] missing-floors refusal message must be added (one-line change), (b) orchestrator must confirm the “hook slot = calibrated bar, clips keep COHERENCE_MIN” reading is acceptable, and (c) a final production calibration run must be performed with the new HOOK_VERSION bytes to re-seal hook_calibration.json. After those three items the diff satisfies every governing law, fail-closed rule, and test mutation.

P1_OR_WORSE: 0