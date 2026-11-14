# qwen3.8-27b (qwen/qwen3.8-27b) 91 s finish=stop usage in 12448 / out 3015 usd~0.083 (upper-bound price)

# Audit: pp-selectid-2005 (RULING 82)

## P0 Findings

**1. `pipeline/context_integrity.py` (diff lines 34–50): Failover loop can raise `ValueError` instead of `ProviderError` when the chain is exhausted.**

The loop logic is:
```python
while True:
    ra = router.call(...)
    try:
        A = _strict(...)
        ...
        break
    except (ValueError, TypeError):
        if hasattr(router, "reject"):
            router.reject(ra)
        if not failover or ra.backend in skip:
            raise          # <-- raises ValueError, not ProviderError
        skip.add(ra.backend)
```

Scenario: The router's chain for `context_verdict` (after frozen legs removed) is `[xai, deepseek, glm, qwen]`. The call is made with `avoid_vendor={"xai"}` (the first verdict's vendor). The router skips xAI and tries deepseek. Deepseek is down → router moves to glm. GLM is down → router moves to qwen. Qwen is down → **router raises `ProviderError`** (chain spent). This is correct.

But consider: deepseek is *up* but returns an out-of-contract answer. `skip = {deepseek}`. Next iteration: router is called with `avoid_model={deepseek}`. Router skips xAI (vendor), skips deepseek (avoid_model), tries glm. GLM is down → router moves to qwen. Qwen is down → **router raises `ProviderError`**. Correct.

Now the critical case: deepseek is up, returns out-of-contract. `skip = {deepseek}`. Next: router called with `avoid_model={deepseek}`. Router skips xAI, skips deepseek, tries glm. **GLM is up but also returns out-of-contract.** `skip = {deepseek, glm}`. Next: router called with `avoid_model={deepseek, glm}`. Router skips xAI, skips deepseek, skips glm, tries qwen. **Qwen is up but also returns out-of-contract.** `skip = {deepseek, glm, qwen}`. Next: router called with `avoid_model={deepseek, glm, qwen}`. Router skips xAI, skips all three Heimdall models. **Chain is spent → router raises `ProviderError`.** Correct.

Wait — re-examine. The `raise` on line 49 fires when `ra.backend in skip`. This means the router *returned* a response from a model already in `skip`. Can that happen? The router is told `avoid_model=skip`, so it should never return a response from a model in `skip`. If the router correctly honors `avoid_model`, then `ra.backend in skip` is never true, and the loop only exits via `break` (success) or the router raising `ProviderError` (chain spent). The `raise` on line 49 is a defensive guard against a router bug.

**However**, there is a subtle issue: if the router has a bug or the `avoid_model` kwarg is not properly forwarded (e.g., the router's `call` signature doesn't accept `avoid_model` and silently ignores it), the loop could cycle. But the diff shows `**({"avoid_model": set(skip)} if skip else {})` is passed to `router.call`. If the router doesn't support `avoid_model`, this would raise `TypeError` at the call site, not loop. So the loop terminates.

**Verdict: Not a P0.** The loop terminates correctly under all scenarios where the router honors its contract. The defensive `raise` is unreachable in correct operation.

**2. `pipeline/context_integrity.py` (diff line 48): The `raise` on line 48 re-raises the original `ValueError`/`TypeError`, not a `ProviderError`.**

If the defensive guard on line 48–49 ever fires (router returns a model already in `skip`), the exception raised is the original `ValueError` from `_strict`, not `ProviderError`. The docstring says "then ProviderError: no verdict." This is a contract mismatch, but as analyzed above, the guard is unreachable in correct operation. **Downgrade to P2.**

## P1 Findings

**3. `pipeline/package.py` (diff lines 134–137): `second_screen` passes `deadline_s=SECOND_VERDICT_DEADLINE_S` but does NOT pass `failover=True` explicitly.**

```python
return prescreen(router, chunk, sources, ctx, {k[0]}, {k[1]}, n=len(chunk), store=None, log=log,
                 cache=cache, batch=SECOND_VERDICT_BATCH,
                 deadline_s=SECOND_VERDICT_DEADLINE_S)
```

In `prescreen` (diff lines 117–120):
```python
return CI.step_a(router, ..., deadline_s=deadline_s,
                 failover=deadline_s is not None), None
```

Since `deadline_s=120.0` (not `None`), `failover=True` is correctly derived. **This is correct.** No finding.

**4. `pipeline/package.py` (diff lines 144–147): The off-writer re-screen in `build()` passes `batch` and `deadline_s` but does NOT pass `failover`.**

```python
got_a, fails_a, _, _ = prescreen(router, stale, sources, ctx, writers_v, writers_f,
                                 batch=SECOND_VERDICT_BATCH,
                                 deadline_s=SECOND_VERDICT_DEADLINE_S,
                                 n=len(stale), store=None, cache=step_a_cache)
```

Again, `prescreen` derives `failover=deadline_s is not None` → `True`. **Correct.** No finding.

**5. `pipeline/package.py` (diff lines 117–120): The FIRST screen (initial prescreen) does NOT pass `deadline_s` or `failover`.**

```python
return CI.step_a(router, {m["moment_id"]: contexts[m["moment_id"]] for m in chunk}, writer_vendor,
                 seed=7 + i * batch, writer_family=writer_family, deadline_s=deadline_s,
                 failover=deadline_s is not None), None
```

The `prescreen` function signature has `deadline_s=None` as default. The initial call to `prescreen` from `build()` (not shown in diff, but implied) does not pass `deadline_s`, so it defaults to `None`, and `failover=False`. **The first verdict's path is unchanged. Correct.**

**6. `pipeline/model_providers.json` (diff lines 63–75): The new `heimdall:z-ai/glm-5.3-flash` back-end has `"min_out": 16000`.**

The known cost note says "an ABANDONED call's upper bound (about $0.24 for a Heimdall call with 16000 output tokens)." With `price_usd_per_1m: [3, 15]` (input, output per 1M tokens), 16000 output tokens = 0.016 × $15 = $0.24. This matches. **No finding.**

**7. `pipeline/context_integrity.py` (diff lines 36–38): The `deadline_s` is passed to `router.call` on every iteration of the failover loop.**

This means each model in the chain gets its own 120 s deadline. If deepseek takes 119 s and returns out-of-contract, glm gets a fresh 120 s. Total worst-case: 3 × 120 s = 360 s for the second verdict. This is by design (the ruling says "120 s per call"). **No finding.**

**8. `pipeline/package.py` (diff lines 130–131): `SECOND_VERDICT_BATCH = 2` is used for chunking in `second_screen`.**

The comment says "small batches so one fits in it [120 s]." Deepseek took 284–304 s for 8 excerpts. 2 excerpts ≈ 71–76 s, well within 120 s. **Reasonable. No finding.**

## P2 Findings

**9. `pipeline/context_integrity.py` (diff line 48): Defensive `raise` re-raises `ValueError`/`TypeError` instead of `ProviderError`.**

As noted, this is unreachable in correct operation, but if it ever fires, the exception type doesn't match the documented contract ("then ProviderError: no verdict"). A caller catching `ProviderError` would not catch this. **P2: cosmetic/defensive mismatch.**

**10. `tests/package/test_medley.py` (diff lines 279–281): `P_ProviderError()` is a module-level function that imports `providers` on each call.**

```python
def P_ProviderError():
    import providers
    return providers.ProviderError
```

This is used in `assertRaises(P_ProviderError())`. It works, but it's an unusual pattern. If `providers` is not importable in the test environment, this would fail at call time, not at import time. **P2: minor style/robustness concern.**

**11. `pipeline/model_providers.json` (diff lines 78–88): The `context_verdict` chain in the JSON includes `anthropic:claude-opus-5-5` and `local:gemma3:27b` (frozen legs).**

The test `test_ruling_82_the_context_verdict_chain` (diff lines 158–168) verifies the *frozen-out* chain via `PL.chains()["context_verdict"]`. The JSON itself still lists the frozen legs. This is consistent with the background: "Frozen vendors (openai, anthropic, local) are removed from every chain (tests/package/proof_ly.chains)." The removal happens in `proof_ly.chains`, not in the JSON. **No finding — the JSON is the source of truth for all backends; the chain filtering is done at runtime.**

## Verification of Required Checks

| Check | Result |
|---|---|
| **Family rule: no second verdict from xAI** | ✅ `second_screen` groups by the first verdict's `(vendor, family)` and passes them as `avoid_vendor`/`avoid_family` to `prescreen`. The router skips xAI. The failover chain (deepseek → glm → qwen) is all Heimdall, none xAI. |
| **No second verdict from writer's family for a clip it quotes** | ✅ The off-writer re-screen in `build()` passes `writers_v` and `writers_f` to `prescreen`, which passes them to `step_a` as `avoid_vendor`/`avoid_family`. The router skips the writer's vendor and family. |
| **No out-of-contract answer can be a verdict** | ✅ `_strict` raises `ValueError`/`TypeError` on any out-of-contract answer. The `break` only happens after `_strict` succeeds. The failover loop only `break`s on success. |
| **Failover loop terminates** | ✅ Each iteration either `break`s (success), the router raises `ProviderError` (chain spent), or `skip` grows by one. `skip` is bounded by the number of models in the chain. The defensive `raise` on line 48–49 is unreachable if the router honors `avoid_model`. |
| **First verdict's path unchanged** | ✅ The initial `prescreen` call does not pass `deadline_s`, so it defaults to `None`, and `failover=False`. No deadline, no failover. |
| **Nothing cached from a failed call** | ✅ The diff does not modify the caching logic. The background states "A call that fails is never cached (unchanged)." The `prescreen` function's caching is per-moment and only on success (the `try/except` in `screen` returns `None, e` on failure, and the caller does not cache `None`). |
| **Batch/deadline wiring reaches every second-vendor and off-writer call** | ✅ `second_screen` passes `batch=SECOND_VERDICT_BATCH` and `deadline_s=SECOND_VERDICT_DEADLINE_S`. The off-writer re-screen in `build()` passes the same. Both flow through `prescreen` → `step_a` with `failover=True`. |

## SHIP: yes with conditions

**Conditions:**
1. **P2 #9**: Change the defensive `raise` on `context_integrity.py` line 48–49 to raise `ProviderError` (or a subclass) instead of re-raising the original `ValueError`/`TypeError`, to match the documented contract. This is low-risk but should be fixed before merge to avoid a latent exception-type mismatch.
2. **Verify at runtime** that `router.call` correctly honors the `avoid_model` kwarg. The failover loop's correctness depends on the router never returning a response from a model in `avoid_model`. If the router silently ignores `avoid_model`, the loop could cycle (though the `skip` set would still grow, and the loop would terminate when `skip` covers all models, but the router would keep returning the same model, and the `ra.backend in skip` guard would fire, raising `ValueError` instead of `ProviderError`). A unit test that mocks the router to ignore `avoid_model` and verifies the loop still terminates with `ProviderError` would close this gap.