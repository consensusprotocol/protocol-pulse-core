# glm-5.3-flash (z-ai/glm-5.3-flash) 97 s finish=stop usage in 8907 / out 2970 usd~0.071 (upper-bound price)

# glm-5.3-flash — CYCLE 2 AUDIT (pp-selectid-0707, spend guard)

## 1. What the others caught that I missed

**Grok's P2 on `_settle` not being in the diff** — I flagged the same thing but buried it as a caveat inside P1-2. Grok stated it cleanly as its own finding: the diff proves `_basis_total` reads the three keys, but not that `_settle` writes them correctly on every vendor reply path (xAI `cost_in_usd_ticks`, Heimdall `usage.cost`, STT, deadline-abandoned calls). That's the right emphasis; the ruling's correctness ultimately rests on code we both only saw described. I should have made it a standalone finding.

**Qwen's P2-1 on the floating-point assertion** — I missed this entirely. `3.46 + 1.81` in IEEE 754 is `5.2700000000000005`, and the test at `test_providers.py:161` uses `places=6` (tolerance 5e-7). It passes today, but the margin is ~3e-8 of headroom against the rounding error of the *sum itself*; any future change to the seeded decimals could flip it. Qwen's suggested fix (compare against the explicit sum `3.46 + 1.81`, or loosen to `places=4`) is strictly better. Legit catch, correctly graded P2.

**Qwen's P2-2 on `spent()` returning 0.0 when `spend_path` is unset** — I noted the `0.0` return in my Cycle 1 verification but didn't assess it as API surface. Qwen's point stands: a Router built without `spend_path` silently reports $0.00 and never raises `SpendLimit`. It's pre-existing behavior, unchanged by this diff, so P2/noted is the right grade. I agree.

**Qwen's P2-3 / Grok's P2 on the `>=` stop-gate reading** — I verified the `>=` comparison in Cycle 1 but didn't articulate the "start gate, not mid-build abort" interpretation as a finding. Both models did, and both concluded it satisfies the ruling's "At $10 reported stop and tell me." I agree with their reading: the ruling's own numbers support it ($10 stop, $12 cap — if "stop" meant abort at $10, the $12 cap would be unreachable except within a single build's reservations, which the ruling's "from where you stand" framing doesn't suggest). No disagreement.

## 2. Agree / disagree on their key findings

| Finding | My verdict | Why |
|---|---|---|
| glm P1-1 (`res` might not be a dict) | **Partially agree — correctly refuted by the implementer** | My Cycle 1 scenario was conditional ("if `PK.build` can return `None`"). The consensus shows the implementer verified `res` is a dict on every path (the line above already calls `res.update(...)`), and a build that *raises* never reaches either line. I accept the refutation; my "unverifiable-from-diff" hedge was the honest part, and the fix (`res = res or {}`) is still harmless belt-and-braces. |
| glm P1-2 (legacy ledger reads as $0.00) | **Agree — and the fix is good** | The C2 diff implements exactly the right fail-closed: `_basis_total` (providers.py:31-33) raises `SpendLimit` when the ledger has `calls` but neither reported key, and the test at lines 173-176 exercises it. One nuance: the guard triggers only when **both** keys are absent. A legacy ledger with `usd_reported` but no `usd_unreported_estimate` (or vice versa) still reads the missing one as 0.0 — fail-open for that half. Given the background says `_settle` maintains all three, this is a theoretical residue, not a practical one. P2. |
| Grok: `_settle` unverifiable from diff | **Agree** | Correct scope discipline. The diff's test seeds the ledger directly (lines 152-153), so `_settle`'s key-population behavior is asserted by background, not by this diff. |
| Qwen: float-fragile assertion | **Agree** | P2, correctly graded. |
| Qwen: `spent()` == 0.0 when unconfigured | **Agree (pre-existing, noted)** | Not introduced by this diff; the new `spent()` docstring (providers.py:38) even documents it. |
| Qwen/Grok: `>=` start-gate reading of "at $10 stop" | **Agree** | See §1. |

## 3. New findings from this review

**N1 (P2) — `proof_ledger.py:91-92`: `res["spend_ruling_48"] = ...` still assumes `res` is a dict, and the C2 fix doesn't add the one-line guard.** The implementer's refutation (R1) is that `PK.build` returns a dict on every path — but that's verified from code outside this diff, exactly the category of claim the audit brief says to treat carefully. The cost of `res = res or {}` (or a `try/except` around the assignment) is one line; the cost of being wrong is losing the ruling-48 record entirely, which is the very accounting the ruling demands. Nobody in Cycle 1 *disputed* this — the implementer just asserted the invariant. I'd ship either way, but the guard is cheaper than the trust.

**N2 (P2) — `providers.py:31-34`: the fail-closed guard fires only when *both* reported keys are missing.** A ledger with `calls: 400`, `usd_reported: 3.46`, and no `usd_unreported_estimate` key reads the latter as 0.0 — a silent under-count of the STT/abandoned-call dollars, the same fail-open direction my Cycle 1 P1-2 described, now surviving the fix for the both-keys-missing case. Scenario: any code path (or hand-edit, or a future `_settle` regression) that writes `usd_reported` but skips `usd_unreported_estimate` when its value would be 0.0. Not verifiable from the diff whether `_settle` ever omits a zero-valued key. If it does, the guard never fires and the reported basis under-counts. Fix: require both keys when `calls > 0`, or have `_settle`'s contract (unverifiable here) guarantee both.

**N3 (P2) — `proof_ledger.py:73` vs. the ruling's "Keep the running total on STATE line 1":** the diff logs the running total via `say(...)` (lines 74-75, 78-79, 93-94) and into `package.json` (line 91), but whether `say()` writes to STATE line 1 is not verifiable from the diff. If `say()` is a log-only function, the ruling's STATE requirement is satisfied only indirectly. Flagging as unverifiable, not a defect — same caveat I made in Cycle 1, still unresolved, still nobody else flagged it.

**N4 (P2) — `test_providers.py:167`: `r.limit_usd = r.spent() + 0.05` mutates the attribute directly rather than constructing a new Router.** This works because `_reserve` reads `self.limit_usd` at call time, but it means the test exercises the limit check with a *mid-flight* attribute mutation, not the constructor path. If a future refactor caches `limit_usd` at construction (or moves the check into a property), the test's coverage silently changes. Cosmetic; noting for completeness.

**N5 (P2) — `providers.py:34-42`: the new `spent()` acquires the lock, but `_reserve` (line 51) calls `_basis_total(d)` on a ledger dict `d` it already holds under the lock — while `proof_ledger.py:72` calls `router.spent()` (which locks) *before* the build, and `proof_ledger.py:88` calls it *after*.** No deadlock: `spent()` locks, reads, unlocks; `_reserve` locks, reads, unlocks; they're sequential, not nested. Verified — no finding, just confirming the lock discipline survives the refactor. (Stating it because the brief asks about the lock, and the C2 diff moved the basis computation *inside* the locked region in both paths — correct.)

**N6 — verification, not a finding: the reservation release path.** `test_providers.py:170` asserts `json.load(open(led))["reserved"] == {}` after the SpendLimit, confirming reservations are released on the failure path. Combined with line 61's `round(upper, 6)` booking, the reservation lifecycle is: book under lock → check → (release on settle or failure). The diff doesn't show the release code, but the test's final assertion would fail if reservations leaked. Adequate.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `_basis_total` correctness (reported = reported + unreported-estimate) | 9/10 | 9.5/10 | The fail-closed guard (F1) closes the main legacy-ledger hole; the both-keys-vs-either-key residue (N2) is theoretical. |
| Lock / reservation integrity | 9/10 | 9/10 | Unchanged; verified the basis computation sits inside the locked region in both `spent()` and `_reserve` (N5). |
| proof_ledger driver (stop gate, record) | 8.5/10 | 8.5/10 | The C2 try/except around the post-build read (F2) is good; `res`-is-a-dict still rests on out-of-diff code (N1), and the STATE-line-1 question remains unverifiable (N3). |
| proof_ly constants / wiring | 9/10 | 9/10 | 12.0 / "reported" / 10.0 consistent across both drivers; no other callers touched. |
| Test coverage | 8/10 | 8.5/10 | The ruling-48 test now covers the fail-closed path (F1) — a real improvement; the float-fragility (Qwen) and the attribute-mutation style (N4) keep it short of 9. |

## 5. Final priority list

**P0 CRITICAL** — none.

**P1 HIGH** — none. (My Cycle 1 P1-1 is refuted-with-verification; my Cycle 1 P1-2 is fixed by F1, with the residue demoted to P2.)

**P2 MEDIUM**
1. **`proof_ledger.py:91`** — add `res = res or {}` (or guard the assignment) so the ruling-48 record survives even if the out-of-diff invariant "PK.build always returns a dict" ever breaks. One line, buys the accounting the ruling demands.
2. **`providers.py:31-34`** — the fail-closed guard requires *both* reported keys to be absent; a ledger with exactly one of them still silently reads 0.0 for the other. Either require both when `calls > 0`, or confirm (out of diff) that `_settle` always writes both.
3. **`test_providers.py:161,163,165`** — replace `places=6` with comparison against the explicit sum (`3.46 + 1.81`) or `places=4`, per Qwen; the current margin against IEEE 754 drift is ~3e-8.
4. **`proof_ledger.py:74,78,93`** — confirm (out of diff) that `say()` reaches STATE line 1, or add an explicit STATE write; the ruling's "Keep the running total on STATE line 1" is currently satisfied only if `say()` does more than its name suggests.

## 6. The single highest-leverage change

Add the one-line `res = res or {}` guard at `proof_ledger.py:91` — it's the only change that protects the ruling-48 accounting record itself, which is the entire deliverable of this diff, against the one invariant nobody verified from the diff.

## 7. Production ready?

**Yes with conditions.** Conditions, precisely:
1. `proof_ledger.py:91` — guard the `res["spend_ruling_48"]` assignment (one line) so the post-build record cannot be lost to a non-dict `res`.
2. Confirm, from code outside this diff, that `_settle` writes **both** `usd_reported` and `usd_unreported_estimate` on every settled call (including zero-valued ones) — or tighten the `providers.py:31` guard to require both keys when `calls > 0`.
3. Confirm `say()` writes to STATE line 1, or add the explicit STATE write the ruling asks for.

Everything else (P2-3, the float-fragility, the attribute-mutation style) is nice-to-have and does not block. The C2 fixes (F1's fail-closed guard, F2's guarded post-build read) are correct and tested; the reported basis counts every call exactly once; the lock discipline is intact; the $10 start-gate / $12 hard-cap reading of the ruling is sound.