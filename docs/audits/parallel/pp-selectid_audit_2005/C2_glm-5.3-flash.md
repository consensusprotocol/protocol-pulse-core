# glm-5.3-flash (z-ai/glm-5.3-flash) 75 s finish=stop usage in 12369 / out 1924 usd~0.066 (upper-bound price)

# pp-selectid-2005 — CYCLE 2 AUDIT (final)

## 1. What the others caught that I missed

Honest accounting against my Cycle 1 output:

- **Grok's P2 on the defensive-branch error type** (context_integrity.py:48-52): I traced the loop but did not note that when the defensive `ra.backend in skip` guard fires, the raised exception was the original `ValueError`, not the documented `ProviderError`. Qwen independently found the same thing and the consensus implemented the fix (lines 50-52 now raise `providers.ProviderError` with `from e`). I missed the contract-mismatch angle; the fix is in the diff and is correct — `raise ... from e` preserves the cause, and the first-verdict path (failover=False) still raises the original at line 49, unchanged. Good catch, correctly fixed.
- **GLM's P1-2 (implicit deadline↔failover coupling)**: I noted the coupling in passing but did not flag that the invariant "first-verdict path passes neither" is enforced only by convention. The consensus's mitigation — the `screen_deadlines` recording in the Rig (test_medley.py:195, 236) — pins `[None, 120.0, 120.0, 120.0, 120.0]`, which is exactly the test GLM asked for. I under-credited this; it's now test-enforced, not convention-enforced.
- **GLM's P1-3 (all-three-failing test exercises the router's spent path, not the loop's)**: I did not check which termination branch the test hits. GLM is right: in the all-three test the router raises `ProviderError` before returning, so the loop's own `ra.backend in skip` guard (line 50) is only exercised via the non-failover short-circuit. However, the consensus's "recorded, no change" note is also right that each failure mode is exercised alone, and the guard is now a 3-line defensive branch raising a documented error. I agree with recording it, not blocking.

## 2. Agree / disagree

- **GLM P1-1 (skip-set keyed by `ra.backend` vs router's `avoid_model` contract)** — **agree, and the consensus resolved it**: the router walks the chain by name, `_skip` refuses `name in am`, and `Reply(text, name, ...)` carries that same name as `.backend`. The failover test runs the real Router with fake back-ends, so the keying is exercised, not assumed. Disagree only with residual doubt: the test's back-end ids (`heimdall:glm`) differ from production (`heimdall:z-ai/glm-5.3-flash`), but since the invariant is "the name the router skips == the name it returns", and that holds for any id, the residual risk is nil. Resolved.
- **Qwen's withdrawn P0s** — agree with the withdrawal; its own trace shows the loop terminates whenever the router honors `avoid_model`, and a non-honoring router raises `TypeError` at the call site rather than looping. Correct.
- **Grok's "SHIP: yes"** — agree; nothing it called P2 is wrong, and both of its substantive P2s were addressed.

## 3. New findings (Cycle 2)

**P2 — test_medley.py:282: the deadline-asked wrapper records `k.get("deadline_s")` but the assertion `set(asked) == {120.0}` (line 285) cannot distinguish "the deadline was forwarded" from "the wrapper saw the kwarg".** It does verify forwarding (the wrapper reads the kwargs actually passed to `router.call`), so this is sound — but note the wrapper is installed on the router *instance* after construction and the second/third `step_a` calls in the test (lines 287-291) reuse it, so `asked` accumulates across all three runs; `set(asked)` still passes because the later calls also pass 120.0. Fragile but correct. Nobody flagged the accumulation; it's harmless here.

**P2 — context_integrity.py:38: `**({"deadline_s": deadline_s} if deadline_s else {})` treats `deadline_s=0` as "no deadline".** Nobody caught this. With the constant at 120.0 it's unreachable, but the same truthiness idiom is used for `skip` (line 37), where it's correct. If a future caller passes 0 meaning "immediate", the call silently runs unbounded. Cosmetic; note it.

**P2 — package.py:133-134: `second_screen`'s grouping key `(b.vendor, b.family)` uses the FIRST verdict's backend, but the new chain adds two more Heimdall families (glm, qwen) — a first verdict from `heimdall:deepseek` (family deepseek) now groups clips whose second verdict may come from glm/qwen, which is correct per the ruling (only the FIRST verdict's vendor/family is avoided), but the ruling's second constraint ("different from the writer's, for a clip it quotes") is enforced by the off-writer re-screen, not here.** Verified consistent: `second_screen` passes `avoid={k[0]}`/`{k[1]}` (vendor, family of the first verdict) and the re-screen at package.py:2817-2820 avoids the writers'. No defect — recorded because the ruling's two constraints land in two different code paths, and no test pins that a second verdict from the *writer's* family (when writer ≠ first-verdict vendor) triggers the re-screen. The existing swap test (test_medley.py:227-237) covers the re-screen; adequate.

**P2 — test_medley.py:284: `x.calls == 0` is asserted, which pins that xAI is avoided by BOTH vendor and family — but the test passes `writer_family={"grok"}` while production's second_screen passes only the first verdict's vendor and family, which for an xAI first verdict is `({"xai"}, {"grok"})`.** Consistent. No defect.

Nothing new rises above P2.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| context_integrity.step_a failover loop | sound, one noted gap (loop-termination branch untested) | sound; defensive branch now raises documented ProviderError; gap recorded, not blocking | consensus fix landed in diff |
| package.py wiring (batch/deadline) | sound | sound; now test-pinned via `screen_deadlines` | GLM's condition implemented |
| model_providers.json chain | sound | sound; pinned by test_ledger_build.py:161-171 (chain + glm family) | — |
| Tests | adequate | adequate; noted fragility (asked-accumulation, deadline_s=0) | closer reading |
| Cost/ledger | accepted as stated | accepted; consensus confirmed abandoned-call booking and no-cached-failure | — |

## 5. Final priority list

**P0 CRITICAL** — none.

**P1 HIGH** — none.

**P2 MEDIUM**
1. context_integrity.py:38 — `deadline_s=0` silently means unbounded (truthiness guard). Use `is not None` if 0 should ever be meaningful.
2. test_medley.py:282,285 — `asked` accumulates across the test's three `step_a` runs; the assertion passes for the right reason today but would not detect a later call losing the deadline. Reset `asked` per run or assert per-run.
3. test_medley.py:263-291 — the loop's own `ra.backend in skip` termination branch (context_integrity.py:50-52) is exercised only via the non-failover short-circuit, never as a genuine "router returned an already-skipped backend" (recorded by consensus; a unit test of the guard would close it).

## 6. The single highest-leverage change

Add one test that forces the router to return a back-end already in `skip` — it is the only branch of the failover loop no test executes, and it is the branch that guarantees termination.

## 7. Production ready?

**Yes.** Conditions (all P2, none blocking): (a) the defensive-branch unit test above, (b) `is not None` for the deadline guard, (c) reset `asked` between the failover test's three runs. All 15 suites pass, the ruling's family rule, no-cached-failure, unchanged first-verdict path, and batch/deadline wiring are each pinned by a test, and the two Cycle 1 conditions (ProviderError on the defensive branch; the deadline-pinning test) are implemented in this diff.