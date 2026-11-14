# qwen3.8-27b (qwen/qwen3.8-27b) 96 s finish=stop usage in 42034 / out 2482 usd~0.163 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0108B

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (GLM-5.3-FLASH) identified the `kind` kwarg merge risk (B1), the behavioral change in `hook_ratings` attempt count (B2), the replay's legacy contract tolerance (B3), and the `step_a` comparison masking (B4).

**What I missed or under-weighted:**
*   **The `would_seal` logic flaw (Qwen P1-2 / GLM C1 fix):** I did not explicitly flag that `would_seal_under_grok` could evaluate to `True` (or be misleadingly calculated) when *all* shadow answers were missing. The Cycle 1 consensus correctly identified that `None` is the only safe state when verification is impossible. The fix in the diff (`would_seal = None if not texts or (missing and not on_pin) ...`) addresses this, but I should have flagged the original logic's potential for a false positive "seal" in Cycle 1.
*   **The `router.reject` removal:** I noted the change in `hook_ratings` but did not explicitly verify that *all* other call sites (fidelity, exclusion, speaker, coherence, medley, context_integrity) correctly removed the manual `router.reject` calls. Since `P.call_parsed` handles rejection internally, leaving manual rejects would cause double-rejection or state corruption. The diff shows they are all removed. I should have explicitly confirmed this "no double-reject" invariant.
*   **The `gateway` change in `package.build`:** I did not scrutinize the change from `router.backends[n].vendor` to `P.gateway(router.backends[n])` in the `writer_avoid` calculation. This is a subtle but critical change for `heimdall_first` routing where a "family" is its own maker. If `P.gateway` returns the wrong identifier, the "avoid writer" logic fails, potentially allowing a judge to be the same model as the writer.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok-4.20 (SHIP yes, no findings):** I **disagree** with the "no findings" stance. While there are no P0s, the `would_seal` logic and the `gateway` change are significant enough to warrant P1/P2 attention. Grok's audit was too superficial on the shadow/replay logic.
*   **Qwen3.8-27B (P1-1: 429 handling):** I **agree** with the Cycle 1 consensus that this is **refuted**. The replay is a measurement tool, not a gate. The `router.down.pop` is a deliberate design choice to allow re-tries after a pause, and the `SpendLimit` cap in the Router prevents runaway spend. It is not a defect.
*   **Qwen3.8-27B (P1-2: `would_seal` semantics):** I **agree**. The original logic was dangerous. The fix in the diff is correct.
*   **GLM-5.3-FLASH (B1: `kind` kwarg):** I **stand by** this. It is a merge risk. If Package A's `Router.call` does not accept `kind`, the `TypeError` is caught and treated as a step failure. This is fail-closed, so it is safe, but it will silently disable the new routing if the versions are skewed. It is a P2 (operational risk, not a logic bug).
*   **GLM-5.3-FLASH (B3: Replay legacy tolerance):** I **stand by** this. The replay uses a more permissive parser for `clips_alone`/`coherence` than production. This is disclosed and intentional for reading old recordings. It does not affect the `hook` decision (which uses strict parsing). P2.

## 3. NEW FINDINGS FROM THIS REVIEW

**P1: `package.build` — `writer_avoid` logic change requires `P.gateway` to be robust.**
`pipeline/package.py:376-378`:
```python
ab = router.backends.get(angle_reply.backend)
writer_avoid = {P.gateway(router.backends[n]) for n in router.chain("angle_write") if n in router.backends} - \
    {P.gateway(ab) if ab is not None else angle_reply.vendor}
```
**Scenario:** If `P.gateway` returns `None` or an empty string for a backend that is not a "gateway" (e.g., a direct model), the set difference might not correctly exclude the writer's family. Under `heimdall_first`, if `P.gateway` does not correctly map `heimdall:qwen` to its "maker" identifier, the `avoid_vendor`/`avoid_family` logic in subsequent verdict calls might fail to exclude the writer, violating the "judge is never the writer" law.
**Verification:** I cannot see `P.gateway` in this diff (Package A). I must assume it is correct. If it is not, this is a P0. **Condition:** Verify `P.gateway` returns a stable identifier for all backends.

**P2: `replay85.py` — `anchor_units` for `clips_alone`/`coherence` may over-attribute.**
`tests/package/replay85.py:872-874`:
```python
if k in ("clips_alone", "coherence", "fidelity"):
    whole = [n for n, ts in anchors if ts and all(t in npr for t in ts if t)]
    return {u: whole for u in (row.get("grok") or {})} if whole else {}
```
**Scenario:** If a prompt contains the text of *all* clips from an anchor pin, *every* unit in that row is attributed to that anchor. If the prompt is a large batch containing clips from multiple pins, this might incorrectly attribute units to an anchor if the text match is too loose (e.g., common phrases). The `_norm` function strips non-alphanumeric, which might cause false positives.
**Impact:** Low. This only affects the "Anchors" section of the table, not the routing decision.

**P2: `shadow86.py` — `pin_texts` uses `res["package"]` for medley, but `res["spotlight"]["package"]` for spotlight.**
`tests/package/shadow86.py:1180-1181`:
```python
pks = ([res.get("package") or {}] if res.get("pin") else []) + \
    ([(res.get("spotlight") or {}).get("package") or {}] if res.get("spotlight_pin") else [])
```
**Scenario:** If a build has *both* a medley pin and a spotlight pin, `pin_texts` returns the union of both. This is correct for the "would_seal" check (the pin is the union of sealed clips). However, if the `res["pin"]` is a medley pin and `res["spotlight_pin"]` is a spotlight pin, the `on_pin` check in `compare_lines` will mark a unit as `on_pin` if it matches *either* pin's text. This is correct behavior for the "would_seal" logic (if Grok fails *any* part of the sealed pin, it would have stopped it).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Verdict Call Sites** | P1 (B1, B2) | P2 | The `kind` kwarg is a merge risk, not a logic bug. The `hook_ratings` change is correct. The `gateway` change is a new P1 (unverified). |
| **Replay85** | P1 (B3, B4) | P2 | The legacy tolerance is disclosed. The `step_a` comparison is acceptable. The `anchor_units` over-attribution is a P2. |
| **Shadow86** | P1 (would_seal) | P2 | The `would_seal` fix is correct. The `pin_texts` logic is sound. |
| **Tests** | P2 | P2 | The tests cover the new behavior. The `chained` helper is a good addition. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None.

**P1 HIGH**
1.  **`pipeline/package.py:376-378` — `P.gateway` robustness.** Verify that `P.gateway` returns a correct, non-empty identifier for all backends, especially under `heimdall_first`. If it returns `None` or an incorrect identifier, the "avoid writer" logic fails, potentially allowing a judge to be the writer. **Condition:** Confirm `P.gateway` behavior in Package A.

**P2 MEDIUM**
1.  **`pipeline/context_integrity.py:20` — `kind` kwarg merge risk.** If Package A's `Router.call` does not accept `kind`, the `TypeError` is caught and treated as a step failure. This is fail-closed, but it will silently disable the new routing if the versions are skewed. **Condition:** Verify Package A's `call` signature includes `kind`.
2.  **`tests/package/replay85.py:872-874` — `anchor_units` over-attribution.** The text match for anchors might be too loose, causing false positives in the "Anchors" section of the table. **Condition:** Review the `_norm` function and the anchor text matching logic.
3.  **`tests/package/replay85.py:564-595` — Legacy contract tolerance.** The replay uses a more permissive parser for `clips_alone`/`coherence` than production. This is disclosed and intentional, but it means the replay's agreement percentages are not directly comparable to production's. **Condition:** Accept the disclosed tolerance.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Verify that `P.gateway` in Package A correctly maps all backends to their "maker" identifiers, especially under `heimdall_first` routing, to ensure the "avoid writer" logic in `package.build` is robust.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Verify `P.gateway` behavior:** Confirm that `P.gateway` returns a correct, non-empty identifier for all backends, especially under `heimdall_first` routing. If it does not, the "avoid writer" logic in `package.build` is broken.
2.  **Verify Package A's `Router.call` signature:** Confirm that `Router.call` accepts the `kind` kwarg. If it does not, the new routing will silently fail (fail-closed) due to `TypeError`.
3.  **Accept the replay's legacy tolerance:** The replay's `clips_alone`/`coherence` parsers are more permissive than production's. This is disclosed and intentional, but it means the replay's agreement percentages are not directly comparable to production's. Accept this for the purpose of the replay.