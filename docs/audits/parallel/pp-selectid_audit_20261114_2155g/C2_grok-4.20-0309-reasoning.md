# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 36 s finish=stop usage in 12107 / out 1132 usd_reported=0.029729 usd~0.089 (upper-bound price)

**CYCLE 2 AUDIT: pp-selectid-20261114_2155g (RULING 107 (1))**

1. WHAT DID THEY CATCH THAT YOU MISSED?
In my Cycle 1 pass I focused on surface-level fingerprint coverage (moments, registry, code hash) but completely missed the fragile `json.dumps(...).count('"verdict": "error"')` string-search implementation in `open_work` (both GLM and Qwen flagged it as P1). I also did not notice that the `return None` placement inside the `nothing_new` loop (after a loaded but non-matching FINGERPRINT) deliberately limits the decision to *only the newest finished build*, nor did I surface the exact interaction between start-time vs. end-time `fingerprint(..., now, reg)` calls and how `CA.due` + `reg` mutation interact with the guard.

2. WHERE DO YOU AGREE OR DISAGREE?
- GLM F1 / Qwen P1 on `nothing_new` iteration + "newest vs any" semantics: partially agree. The original code's early return was easy to misread as a bug; after the Cycle 1 fixes and the explicit test `test_only_the_newest_finished_build_counts` (which exercises stopped/skipped builds, non-matching newest finished build, self-exclusion, and unreadable JSON), the implementation now matches the updated docstring exactly. The "newest finished build decides" rule is the correct semantics for idempotency here; checking *any* prior matching build would be incorrect.  
- GLM F2 / Qwen on time-varying `now` inside fingerprint: agree. The tests (`test_the_same_inputs_give_the_same_fingerprint`, `test_a_resting_candidate_coming_due_moves_it`, 3 h later equality) plus reuse of the *original* `now` object for the end-of-build fingerprint eliminate the concern. A due-candidate flip or ET-day rollover *is* new work.  
- GLM F3 / Qwen P1 on open_work string search: fully agree. The original was [P1]. The new recursive `_errors()` + structural walk (plus the test that a nested verdict counts but a log string quoting the phrase does not) is clean and correct.  
- GLM F4 (routing not fingerprinted): agree it was a gap; the added `"routing": routing` (and cross-test with "today" vs "heimdall_first") plus its presence inside `code_content()` for the config file closes it.  
- Consensus refutations (pool independence, integrator outputs captured at end, --from-candidate never writes FINGERPRINT, etc.): agree with all evidence provided. No disagreement on any refuted item.

3. NEW FINDINGS FROM THIS REVIEW
[P2] `fingerprint` lines 67-70 compute `precheck_results` via `(name, size, mtime)` tuples only. This detects arrival or modification of a precheck answer for the current pool but is vulnerable to non-content changes (filesystem timestamp skew, copied directories, identical content written twice). Hashing the actual JSON content (or at least including a content digest) would be more robust. The existing test only exercises presence/absence, not content identity.  
[P3] `nothing_new` line 106 sorts on the full globbed paths; combined with the `abspath` self-check this is safe but brittle if the proof directory ever moves or uses symlinks with differing lexical prefixes. Timestamp-based sort on basename only would be clearer.  
[P3] The driver-level test (`TestTheDriverAsksNoModel`) only exercises the `NOTHING_NEW` path; the end-of-build `FINGERPRINT` write path relies on the unit tests for `fingerprint`/`open_work`. Still sufficient given the mutation-killing test matrix.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Fingerprint stability  | P1      | P2      | Cycle 1 concerns on `now`, `due`, and registry mutation fully pinned by new tests and same-`now` reuse at end. |
| nothing_new logic      | P1      | P3      | Return placement is intentional per docstring + test; I misread severity in Cycle 1. |
| open_work counting     | P1      | P4      | String search eliminated; structural walk + explicit nested/string tests resolve it completely. |
| Overall guard + driver | P1      | P0      | All prior P1s addressed; router-mocking test proves $0.00 path before any model call. |

5. FINAL PRIORITY LIST
No [P0].  
[P2] Change precheck_results in `tests/package/proof_ledger.py:67` to hash file content (or size+mtime+sha) instead of metadata only.  
All Cycle 1 P1 items are resolved; no other changes required before merge.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The structural `_errors()` walk plus the driver test that makes router construction raise an exception when `nothing_new` fires, proving zero model cost with a single assertion.

7. PRODUCTION READY?
Yes with conditions: address the [P2] precheck_results metadata-only check in a follow-up patch (or accept the documented approximation); otherwise the guard, tests, and consensus fixes make it shippable.

P1_OR_WORSE: 0