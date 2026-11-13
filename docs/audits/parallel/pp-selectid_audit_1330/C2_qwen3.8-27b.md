# qwen3.8-27b (qwen/qwen3.8-27b) 50 s finish=stop usage in 16482 / out 3414 usd~0.101 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1330
# Reviewer: GLM-5.3-FLASH (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Grok-4.20-0309-REASONING** caught nothing I missed; it found nothing at all. Its "SHIP: yes, no findings" is a non-audit. It did not engage with the seed reconstruction, the `lineup_for` contract, or the `filled` initialization. It is not a useful counterweight.

**Qwen3.8-27B** raised a P0 on `candidate_lineup` / `lineup_for` that I did not raise in Cycle 1. Its *conclusion* (no P0) is correct, but its *reasoning* is muddled: it oscillates between "lineup_for might return a different set" and "the check on line 60 catches this." The check **does** catch it. I missed explicitly stating that the `!= ids` guard at `package.py:60` is the load-bearing line that makes Qwen's P0 a non-issue. I should have said so in Cycle 1.

**Claude's consensus** refuted Qwen's P1 (n_lineup off-by-one) with the strongest possible evidence: an offline dry run on the real 12:22 record where every recorded call was served from its recording, proving the seeds match. I did not have access to that dry run in Cycle 1. I now accept the refutation. My P1-3 (seeds after a ruling-41 swap) is **subsumed** by this evidence: the dry run exercised the exact path, and the seeds were correct.

**What I missed that matters:**
- I did not verify that `filled` initialization (diff line 134: `filled = None`) is correct for the candidate path. In the candidate's first iteration, `swapped` is preset to `cand_segs`, so the code takes the `if swapped is not None` branch (diff line 142). In that branch, `filled` is **never assigned** before the `rec` dict is built (diff line 145–149). The `**({"pool_filled": filled} if filled else {})` guard means `filled=None` → no key added. This is correct: the candidate's line-up was not "filled" by the pool search; it was preset. But I should have stated this explicitly.
- I did not check whether `out["candidate"]["result"]` (diff line 169) can be `None` in a way that misleads the operator. If the candidate is closed before any `tried` entry is appended (e.g., `candidate_lineup` returns `why_c`), `out["tried"]` is empty, `t_` is `{}`, and `result` falls through to `out.get("why_none")`. This is correct. If the candidate is judged and fails, `t_` has `"why"`. If it passes and seals, `t_` has `"result": "PACKAGE"`. All paths are covered.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My position |
|---|---|---|
| P1-1: `load_candidate` trusts `t["lineup"]` as a list; a string would cause `TypeError` not `ValueError` | GLM (me, C1) | **AGREE, but downgrade to P2.** The `proof_ledger.py` wrapper catches `TypeError` (diff line 212: `except (OSError, ValueError, KeyError, TypeError)`), so the CLI refuses with exit 2. The contract says "Raises ValueError," but the only production caller is `proof_ledger.py`, which handles `TypeError`. A future caller without that wrapper would get a confusing error, but the fail-closed property (M12) is preserved. Not a P1. |
| P1-2: `supply_exception` may be stale relative to THIS pool | GLM (me, C1) | **AGREE, P2.** The order says "as it was judged." Replaying the recorded `repeat_ok` flag is the intended behavior. If the current pool would not grant the exception, `lineup_for` will return `None` or a different set, and the `!= ids` check closes the candidate. The closure reason ("its clips no longer form its line-up under the line-up rules") is slightly imprecise but not misleading. The candidate is closed, which is the correct outcome. |
| P1-3: `n_lineup` reconstruction can disagree after a ruling-41 swap | GLM (me, C1) | **RETRACT.** The offline dry run proves the seeds are correct for the 12:22 record. The test at diff lines 323–335 covers "after a None line-up and across angles." A ruling-41 swap produces a `tried[]` entry with the same `angle` number (the swap is judged within the same angle's while-iteration, and the counter `n_lineup` is incremented per judged line-up). The reconstruction `sum(1 for u in tried[:index+1] if u.get("angle") == t["angle"] and u.get("lineup"))` counts every line-up entry for that angle up to and including the candidate. This matches the loop's counter. The dry run is dispositive. |
| P0: `lineup_for` might return a different set | Qwen (C1) | **DISAGREE (no P0).** The check at `package.py:60` (`[m["moment_id"] for m in segs] != ids`) ensures the returned segments are exactly the candidate's clips in order. If `lineup_for` returns anything else, the candidate is closed. This is correct and fail-closed. |
| P1: n_lineup is 0-based, seeds are one less | Qwen (C1) | **DISAGREE (refuted by Claude).** The loop increments `n_lineup` **before** the verdict call. Starting at `candidate["n_lineup"] - 1`, the first iteration judges with `n_lineup = candidate["n_lineup"]`, which is the recorded seed. The tests assert (8, 108) for angle 1 line-up 1 and (19, 218) for angle 2 line-up 2. The dry run confirms. |
| No findings | Grok (C1) | **DISAGREE with the method, not the conclusion.** Grok found nothing because it did not audit. The conclusion (SHIP: yes) happens to be correct. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1 — `load_candidate` does not validate that `t["lineup"]` is a list of strings.**
`package.py:33` (diff line 33): `a["hook"] != t["lineup"][0]`. If `t["lineup"]` is a string (e.g., `"hx"`), `t["lineup"][0]` is `"h"`, and the comparison may pass or fail silently. Then `list(t["lineup"])` at diff line 40 explodes it into characters. The `proof_ledger.py` wrapper catches `TypeError` from `int(t["angle"])` if `angle` is also malformed, but if `angle` is valid and `lineup` is a string, the `TypeError` comes from `list(t["lineup"])` only if `t["lineup"]` is not iterable — a string **is** iterable, so no `TypeError` is raised. The candidate would be loaded with `lineup = ["h", "x"]` (characters), and `candidate_lineup` would check `mid not in cleared` for each character, which would fail (characters are not moment IDs), closing the candidate with "no longer cleared in this pool." This is fail-closed but produces a confusing error message. **Severity: P2.** Fix: add `if not isinstance(t.get("lineup"), list) or not all(isinstance(x, str) for x in t["lineup"]): raise ValueError(...)` at the top of the validation block.

**P2-2 — `out["candidate"]["result"]` can be the string `"not tried"` in a way that is ambiguous with a legitimate closure reason.**
`package.py:169` (diff line 169): `t_.get("result") or t_.get("why") or out.get("why_none") or "not tried"`. If the candidate is closed by `candidate_lineup` (e.g., "its angle's back-end is not in the router"), `out["why_none"]` is set and `out["tried"]` is empty, so `result = out["why_none"]`. This is correct. If the candidate is judged and fails, `result = t_["why"]`. If it passes, `result = t_["result"]` (which is `"PACKAGE"` or similar). The `"not tried"` fallback is only reached if `out["tried"]` is empty AND `out["why_none"]` is not set, which cannot happen in candidate mode (either `candidate_lineup` closes it and sets `why_none`, or it is judged and appended to `tried`). So `"not tried"` is dead code. **Severity: P2 (cosmetic).** No fix needed, but the dead branch is a minor code smell.

**P2-3 — The `filled` variable is initialized to `None` per angle (diff line 134), but in the candidate's first iteration, the `swapped` branch is taken and `filled` is never assigned. This is correct, but the code does not document why.**
In the normal path, `filled` is set when `lineup_for` returns a "pool filled" result. In the candidate path, `swapped` is preset to `cand_segs`, so the `if swapped is not None` branch is taken, and `filled` remains `None`. The `rec` dict uses `**({"pool_filled": filled} if filled else {})`, so `None` → no key. This is correct: the candidate's line-up was not filled by the pool search. But a reader might wonder why `filled` is initialized at all in the candidate path. **Severity: P2 (documentation).** Fix: add a comment at diff line 134: `# filled: None in candidate mode (swapped is preset); set by lineup_for in normal mode`.

**No new P0 or P1 findings.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `load_candidate` validation | P1 (P1-1) | P2 | The `proof_ledger.py` wrapper catches `TypeError`; fail-closed is preserved. The contract violation is minor. |
| `candidate_lineup` / `lineup_for` contract | Not flagged | P2 (Qwen's P0 refuted) | The `!= ids` check at line 60 is load-bearing and correct. |
| Seed reconstruction (`n_lineup`, `ai`) | P1 (P1-3) | No finding | The offline dry run proves the seeds are correct. The test covers the None-line-up and cross-angle cases. |
| `filled` initialization | Not flagged | P2 (documentation) | Correct behavior, but the candidate path's use of `swapped` bypasses `filled` assignment without a comment. |
| `proof_ledger.py` refusal path | No finding | No finding | The `except (OSError, ValueError, KeyError, TypeError)` at diff line 212 covers all failure modes. Read-before-write is enforced. |
| L-x (writers' vendor/family) | No finding | No finding | `angle_reply` is a `SimpleNamespace` with `vendor` and `family` from the recorded back-end (diff lines 100–101). The writers use `angle_reply.vendor` via the unchanged code. |
| Guard against re-lining/swapping | No finding | No finding | The `if candidate is not None and n_lineup >= candidate["n_lineup"]: break` at diff lines 138–139 ensures the loop runs exactly once. The `swapped` preset ensures the first iteration judges the candidate's clips. |
| Closure paths | No finding | No finding | `candidate_lineup` returns `(None, why)` for every closure reason. The `if why_c is not None: return out` at diff lines 93–96 exits before any further call. The `if candidate is not None and not ok_m: break` at diff lines 157–159 closes on a failing verdict. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. `package.py:33` (diff line 33): `load_candidate` does not validate that `t["lineup"]` is a list of strings. A string `lineup` would be exploded into characters, producing a confusing "no longer cleared" closure. Fix: add `isinstance` checks.
2. `package.py:134` (diff line 134): `filled` initialization in the candidate path is correct but undocumented. Add a comment explaining why `filled` remains `None` when `swapped` is preset.
3. `package.py:169` (diff line 169): The `"not tried"` fallback in `out["candidate"]["result"]` is dead code. Remove it or add a comment explaining it is unreachable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `!= ids` check at `package.py:60` (diff line 60) is the single most important line in this diff: it ensures that the candidate's clips are judged **exactly as recorded**, and if the pool has changed such that `lineup_for` would return a different set, the candidate is closed rather than re-judged on different content. Without this check, the entire "as it was judged" property of Ruling 66 would be silently violated.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. The P2-1 fix (validate `t["lineup"]` is a list of strings in `load_candidate`) should be applied before the next build that uses `--from-candidate` with a record that might have malformed entries. This is low-risk but the current behavior produces confusing error messages.
2. The offline dry run evidence (Claude's consensus) should be attached to the audit record as the primary proof that the seeds are correct. The tests cover the common cases, but the dry run on the real 12:22 record is the strongest evidence.
3. The standing registry ("Every build first tries the open candidates, newest first") is explicitly out of scope for this change (K3). This diff is the `--from-candidate` path for RIGHT NOW. The next change must build on `load_candidate` / `build(candidate=)` and add the registry.

**SHIP: yes with conditions** (the two P2 fixes above; the conditions are minor and do not block the immediate use of `--from-candidate` on the 12:22 record, which is the stated goal of Ruling 66).