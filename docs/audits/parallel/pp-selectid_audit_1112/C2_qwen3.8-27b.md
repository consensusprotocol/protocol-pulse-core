# qwen3.8-27b (qwen/qwen3.8-27b) 89 s finish=stop usage in 33979 / out 2984 usd~0.147 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1112
# Reviewer: [Your AI Model]

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the logic of `can_open` and the fail-closed paths, which were correct. However, I missed two subtle but significant issues that the other models (specifically GLM-5.3-FLASH and GROK-4.20) highlighted or hinted at:

1.  **The Ledger Provenance Shift (GLM P1-1):** I noted that `prescreen` writes the ledger even when serving from cache, but I did not fully articulate the *semantic* change. The ledger (`store`) is no longer just "what this build paid for." It now contains verdicts sourced from the shared cache (`cache`). If any downstream tooling or audit logic assumes `store` represents *new* spend or *new* computation for this specific build instance, it is now incorrect. It represents "the state of knowledge for this build," which includes cached history. This is a behavior change that requires documentation or downstream verification.
2.  **The "Same Vendor" Second Screen Risk (GLM P1-2 / GROK P2):** I verified that `second_screen` avoids the *writer's* vendor. I did not sufficiently stress-test the scenario where the *first* screen and *second* screen both resolve to the *same* non-writer vendor from the cache. The ruling implies a "second opinion" from a *different* vendor (Order 06:22 item 45). If the cache contains a verdict from Vendor X for the first screen, and Vendor X is the only non-writer vendor available in the cache for the second screen, the "second screen" is effectively a re-read of the same verdict, not a new independent check. The code *allows* this because it only filters out the *writer's* vendor/family. This weakens the "two-vendor" guarantee if the cache is sparse or if the writer's vendor is the only other option.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GROK-4.20 (SHIP: Yes):** I **AGREE** with the final verdict but **DISAGREE** with the severity of the cache vendor issue. Grok called it P2. I believe the "same vendor" second screen risk is **P1** because it undermines the core intent of Order 06:22 item 45 (independent verification). If the "second" screen is just the first screen's cached result, the build has not actually received a second opinion.
*   **GLM-5.3-FLASH (No P0, P1s on Ledger/Cache):** I **AGREE** with the P1-1 (Ledger provenance) and P1-2 (Cache vendor selection) findings. GLM correctly identified that the ledger now mixes cached and new data. I also agree with the concern about `sorted()` picking the alphabetically first eligible backend, which is arbitrary and not "best."
*   **QWEN3.8-27B (SHIP: No, P0 on Cache Poisoning):** I **DISAGREE** with the P0. Qwen's P0 was based on a misreading of the `new` dict initialization in `hook_ratings`. As Qwen itself noted in its own text ("Wait, let's look closer... This is actually safe"), the logic is correct. The `new` dict is local to the success path and only written to the cache if the contract is met. There is no poisoning. The "P0" was refuted by the consensus and by my own re-verification.
*   **CLAUDE CONSENSUS (SHIP: Yes, No P0/P1):** I **PARTIALLY AGREE**. I accept there are no P0s. However, I disagree that there are no P1s. The "same vendor" second screen issue is a P1 because it violates the *spirit* of the ruling (independent verification) even if it doesn't crash the build. The ledger provenance shift is a P1 because it changes the meaning of a data artifact.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `second_screen` may not provide an independent second opinion (pipeline/package.py:218-222)**
The `second_screen` function calls `prescreen` with `writer_vendor` and `writer_family` set to the *current* writer's identity. It then relies on `prescreen`'s cache lookup logic.
*   **Scenario:**
    1.  Build 1: Writer is Heimdall. First screen uses XAI (cached). Second screen avoids Heimdall, finds XAI in cache. Both screens are XAI.
    2.  Build 2: Writer is XAI. First screen avoids XAI, finds Heimdall in cache. Second screen avoids XAI, finds Heimdall in cache. Both screens are Heimdall.
    3.  **The Problem:** The "second screen" is supposed to be a *different* vendor's verdict. If the cache only has one non-writer vendor, the second screen is just a re-confirmation of the first screen's vendor. This does not satisfy the "step A from a SECOND vendor" requirement of Order 06:22 item 45 if "second" implies "different from the first."
    *   *Verification:* The code at line 218 passes `cache=cache`. The `prescreen` function at line 143-144 picks the first eligible backend from the cache. It does *not* exclude the backend used in the *first* screen of the *current* build. It only excludes the *writer's* backend.
    *   *Impact:* If the first screen and second screen come from the same vendor, the "two-vendor" check is effectively a "one-vendor" check. This is a logic gap in the implementation of the ruling.

**P1-NEW-2: `hook_ratings` cache key omits `writer_vendor` (pipeline/package.py:278)**
The hook cache key is `f"{m['moment_id']}:{text_sha(m['text'])}:{HOOK_VERSION}"`.
*   **Scenario:**
    1.  Build 1: Writer is Heimdall. Hook rated by XAI. Cached.
    2.  Build 2: Writer is XAI. Hook rating is looked up. The cache contains XAI's rating. The `off()` check in `hook_ratings` (line 280-281) filters out backends that are the writer's vendor/family. Since the writer is now XAI, the cached XAI rating is *rejected*. The system must re-ask.
    3.  **The Problem:** This is actually *correct* behavior (fail closed, re-ask if the cached vendor is now the writer). However, it means the cache is less effective when the writer rotates. More importantly, if the writer is *not* the cached vendor, the cached rating is used. This is fine.
    *   *Wait:* Let's re-read the `off` lambda in `hook_ratings` (line 276). `off = lambda name: ... b.vendor not in wv ...`. If the cached backend is the writer, it is filtered out. So the system *does* re-ask. This is safe.
    *   *Correction:* This is **NOT** a finding. The code correctly handles writer rotation by re-asking. I retract this.

**P2-NEW-1: `prescreen` parallelism and `CACHE_LOCK` (pipeline/package.py:178-179)**
The `ThreadPoolExecutor` runs `screen` in parallel. `screen` calls `CI.step_a`. The results are collected. Then `_cache_put` is called *once* at the end (line 204) with the aggregated `new` dict.
*   **Analysis:** This is safe. The lock is only held during the final merge/write. The parallel threads do not write to the cache file directly. They return results to the main thread, which aggregates them and writes under the lock. This is a correct pattern.
*   **Agreement:** I agree with Grok and Qwen that this is safe.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Fail-Closed Paths** | 9/10 | 9/10 | No change. All paths correctly fail closed. |
| **Cache Integrity** | 8/10 | 7/10 | Downgraded due to P1-NEW-1 (same vendor second screen). The cache is safe, but the *selection* logic allows a non-independent second screen. |
| **Hook Rating Logic** | 9/10 | 9/10 | No change. `hook_ratings` is robust. |
| **Ledger Semantics** | 8/10 | 7/10 | Downgraded due to GLM P1-1. The ledger now mixes cached and new data, changing its provenance. |
| **Thread Safety** | 9/10 | 9/10 | No change. Correct use of `CACHE_LOCK`. |
| **Angle Contract** | 9/10 | 9/10 | No change. `check_angles` correctly enforces the hook constraint. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None.

**P1 HIGH**
1.  **`pipeline/package.py:218-222` (second_screen independence):** The `second_screen` function does not ensure the second verdict comes from a *different* vendor than the first verdict of the current build. It only ensures it is not the *writer's* vendor. If the cache contains only one non-writer vendor, the "second screen" is a re-read of the first screen's vendor. This violates the intent of Order 06:22 item 45 ("step A from a SECOND vendor").
    *   *Fix:* `second_screen` should pass the *first screen's* backend to `prescreen` (or a new parameter) so that `prescreen` can exclude it from the cache lookup for the second screen. Or, `second_screen` should verify that the backend of the second verdict is different from the backend of the first verdict, and if not, re-ask.

2.  **`pipeline/package.py:199` (Ledger Provenance):** The build ledger (`store`) now contains verdicts sourced from the shared cache. This changes the semantic meaning of the ledger from "what this build computed" to "what this build used." Downstream consumers that assume the ledger represents *new* spend or *new* computation may be misled.
    *   *Fix:* Document this change clearly. Or, add a field to the ledger entries indicating whether the verdict was `cached` or `new`.

**P2 MEDIUM**
1.  **`pipeline/package.py:280` (Arbitrary Vendor Selection):** The `sorted()` in the cache lookup picks the alphabetically first eligible backend. This is deterministic but arbitrary. It does not prefer the "best" or "most recent" vendor.
    *   *Fix:* Consider preferring the vendor that was used in the first screen of the current build (for consistency) or the most recent vendor in the cache (for freshness).

2.  **`pipeline/package.py:278` (Hook Cache Key):** The hook cache key does not include the `writer_vendor`. This is correct (the rating is independent of the writer), but it means the cache is less effective when the writer rotates (re-asks are required). This is acceptable but worth noting.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Ensure that the `second_screen` verdict comes from a vendor *different* from the `first_screen` verdict of the current build.**

This is the highest leverage change because it directly addresses the core intent of the "two-vendor" ruling. If the second screen is just a re-read of the first screen's vendor, the build has not received an independent verification, which is the primary purpose of the second screen. This change requires modifying `second_screen` to pass the first screen's backend to `prescreen` (or a new parameter) so that `prescreen` can exclude it from the cache lookup.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Fix P1-1 (Second Screen Independence):** Modify `second_screen` to ensure the second verdict comes from a vendor different from the first verdict of the current build. This is critical for the integrity of the "two-vendor" check.
2.  **Document P1-2 (Ledger Provenance):** Clearly document that the build ledger now contains verdicts sourced from the shared cache, and that it represents "the state of knowledge for this build" rather than "what this build paid for."
3.  **Add Test for P1-1:** Add a test case where the cache contains only one non-writer vendor, and verify that the second screen re-asks (or fails) rather than using the same vendor as the first screen.

If these conditions are met, the code is production ready. The fail-closed paths are robust, the thread safety is correct, and the hook rating logic is sound. The only significant gap is the independence of the second screen, which is a P1 issue that must be addressed before shipping.