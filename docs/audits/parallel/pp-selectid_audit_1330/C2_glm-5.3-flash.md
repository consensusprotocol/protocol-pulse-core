# glm-5.3-flash (z-ai/glm-5.3-flash) 89 s finish=stop usage in 15217 / out 2567 usd~0.084 (upper-bound price)

# pp-selectid-1330 — CYCLE 2 REVIEW (final)

## 1. What the others caught that I missed

- **GLM's P1-1 (malformed entry → wrong exception type).** I had noted the `index=None` scan accepts any truthy `t.get("lineup")` but did not trace it to the contract: `load_candidate`'s docstring says "Raises ValueError", yet a string lineup (`"hx"`) yields `t["lineup"][0] == "h"` (silently wrong hook comparison) or `TypeError` at `list(t["lineup"])` — and the proof_ledger wrapper catches `TypeError` (diff line 212) so the CLI still refuses, but a direct caller of the public function gets the wrong exception. Honest miss: I stopped at "the wrapper catches it" without checking the documented contract.
- **GLM's P1-3 (seeds after a ruling-41 swap).** I verified the counter arithmetic (see R1 below) but did not check whether a *swapped* line-up produces its own `tried[]` entry with the same `angle` field. GLM's scenario — a swap recorded such that `n = sum(...)` counts 1 where the loop's counter said 2 — would silently serve the wrong seed. I flagged the mechanism, not the scenario.
- **QWEN's P1 (n_lineup 0-based).** I had this right in Cycle 1; the consensus's R1 refutation (the loop increments *before* the verdict call, so starting at n−1 gives exactly the recorded seed) is correct, and the test at diff line 335 asserts (8, 108) / (19, 218) as the Rig receives them. I agree with the refutation.

## 2. Agree / disagree

- **GLM P1-1 — agree, P1.** The `try/except` in proof_ledger makes it fail-closed at the CLI, so it is not P0, but the contract breach on a public build-path function is real. Fix is one line: `isinstance(t.get("lineup"), list)` in the scan, or validate shape before the scan.
- **GLM P1-2 (stale `supply_exception`) — partially agree, downgrade to P2.** The order says "as it was judged", so replaying the recorded flag is defensible; and the failure mode is benign in both directions: `repeat_ok=True` when the current pool would not grant it only widens the search (the exact-ids check at line 60 still closes it if the result differs), and `repeat_ok=False` when the pool would grant it only risks closing a candidate the standing rule would keep — which is the conservative direction for a "keep" ruling. I cannot verify from the diff whether `lineup_for` re-derives the exception; GLM also could not, and said so.
- **GLM P1-3 (seeds after a swap) — agree it is the right question, but the evidence answers it.** The consensus's offline dry run is the strongest evidence in this review: every recorded call was SERVED, which proves the reconstructed (ai, n_lineup) equalled the recorded ones for the 12:22 record *including whatever swaps/None entries precede tried[0] — tried[0] is the first entry, so no swap precedes it; the (19, 218) test covers the across-angles/after-None case. What remains unproven is only the general case "a swap before the passing entry in the same angle", which no test covers and the dry run does not exercise. P2, not P1: the mechanism is verified, one path is not.
- **QWEN's long P0-1 → self-retracted — agree.** Its own analysis concludes the `!= ids` check at line 60 catches every divergence (subset, reorder, different clips), and the test at diff lines 369-377 proves the `clips=(n, n)` pin defeats the subset search. No finding survives.
- **GROK's "no findings, SHIP: yes" — agree, with the note that it reviewed only changed lines and verified the rest by the added tests.** That is a legitimate scope, but it means the swap-before-passing-entry case was verified by nobody.

## 3. New findings (this cycle)

**N-1 — `out["candidate"]["result"]` can report a stale or wrong outcome when the candidate's tried entry is not the last one, or when `why_none` leaks.** `package.py` diff lines 167-169: `t_ = next((t for t in out["tried"] if t.get("candidate") is not None), {})` — in candidate mode there is exactly one such entry, so `next(..., {})` is fine; but if the candidate *closes before the loop* (line 93-96), the function returns early and this finaliser never runs, so `out["candidate"]["result"]` is never set — the record then has `closed: why` but no `result` key at all. The test at diff line 353-357 asserts `why_none` and `closed` but never `result` for the early-return path. Minor, P2: the information is present in `closed`, but the shape is inconsistent between the two closure paths (early return: no `result`; loop closure: `result` = the tried entry's `why`). A consumer keying on `result` (the next change, K3's registry) will see a missing key.

**N-2 — the early-return path skips `out.pop("why_none", None)` symmetry, harmless, but also skips the `search`/spend finaliser.** Diff line 96: `return out` happens before `out["search"] = {...}` (line 171) and before the spend delta is computed. A closed-candidate run therefore reports no `search` block and no `usd_reported`/`usd_estimate` — the proof_ledger then does `res.update(..., usd_estimate=round(own["est"], 4), ...)` from its own accounting, so the ledger's totals are still written, but `out["search"]`'s absence is a shape difference any downstream consumer of the returned dict must handle. P2; verify the orchestrator/proof_ledger does not read `res["search"]` unconditionally — I cannot see that code.

**N-3 — `angle_tried` is replayed into `SimpleNamespace.tried` (diff line 101) but nothing verifies the recorded `angle_tried` entries correspond to THIS angle.** `load_candidate` copies `record.get("angle_tried")` wholesale (line 39). If the earlier record's `angle_tried` accumulated across angles (the name suggests per-build, not per-angle), the replayed `tried` list would misattribute. I cannot verify from the diff whether `angle_tried` is per-angle or per-build; if per-build, the replayed value is wrong for angle 2 candidates. P2-uncertain, same caveat GLM gave for `supply_exception`.

**N-4 — the `for seed in ((7, 8) if candidate is None else ())` loop (diff line 102) means a candidate build has no retry if... nothing — there is no angle call at all, so this is correct.** Verified, not a finding; noted because the consensus's "glm's P1-4 is answered by grep" presumably refers to this: the angle-reply attributes come from the recorded back-end, not from a call.

## 4. Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why |
|---|---|---|---|
| load_candidate | pass (missed the exception-type contract) | P1 (GLM's) | the wrapper hides it at the CLI, not for direct callers |
| candidate_lineup | pass | pass | the `!= ids` check + the subset test close every divergence I can construct |
| seed reproduction | pass | pass, one P2 | mechanism proven (R1 + the (19,218) test + the dry run); the swap-before-pass case untested |
| candidate-mode loop guards | pass | pass | the `n_lineup >= candidate["n_lineup"]` guard + the failing-verdict break close both exits; the tests assert one call, no swap |
| proof_ledger refusal | pass | pass | read-before-write, exit 2, catches the loader's exceptions |
| out-shape consistency | not examined | P2 (N-1, N-2) | the early-return path skips the finaliser; `result` missing on one closure path |

No P0 in either cycle. Nothing changed my ship verdict.

## 5. Final priority list

**P0 CRITICAL** — none.

**P1 HIGH**
1. `package.py:16-33` (diff) — `load_candidate`'s documented `ValueError` is not what a malformed entry raises: a truthy non-list `lineup` (e.g. `"hx"`) passes the `index=None` scan, then `t["lineup"][0]` indexes a character and `list(t["lineup"])` explodes it; the caller sees `TypeError`/silent wrongness, not `ValueError`. Fix: `isinstance(t.get("lineup"), list)` in the scan, or shape-validate the entry once before it. (GLM P1-1, adopted.)

**P2 MEDIUM**
2. `package.py:37` — the reconstructed `n_lineup` is unproven for one case: a ruling-41 swap recorded before the passing entry in the same angle. The mechanism is verified (R1) and the 12:22 record is proven by the dry run, but no test covers swap-then-pass. Fix: one test, or assert the reconstructed seed against a recorded one if the record carries it.
3. `package.py:57` — `repeat_ok` from the recorded `supply_exception` may be stale relative to this pool; both directions are conservative or caught by the exact-ids check, but the closure reason conflates "the exception no longer applies" with "a line-up rule fails".
4. `package.py:167-169` + the early return at 96 — `out["candidate"]["result"]` is never set when the candidate closes before the loop, and the early return skips the `search`/spend finaliser; the returned dict's shape differs between the two closure paths.
5. `package.py:39,101` — `angle_tried` is replayed wholesale; if it is per-build rather than per-angle, a non-first-angle candidate replays the wrong list. Unverifiable from the diff.

## 6. The single highest-leverage change

Add the `isinstance(t.get("lineup"), list)` guard in `load_candidate`'s scan — it is one line, restores the documented contract on a public build-path function, and is the only finding that a future caller (K3's standing-registry change, which will call `load_candidate` directly) will hit.

## 7. Production ready?

**Yes with conditions** — both conditions are small and neither blocks the 12:22 seal:

1. The P1-1 shape guard in `load_candidate` (one line) before the K3 registry change makes it a hot path.
2. One test for the swap-before-passing-entry seed case (P2-2), or a recorded-seed assertion, before "as judged" is relied on for any record other than 12:22's.

For the RIGHT NOW seal of the 12:22 candidate specifically: the offline dry run served every recorded call (proving the seeds, the bytes and the L-x routing for exactly this record), the closure paths are fail-closed, and the replay-only ReplayMiss stop is not a live path. Ship it.