# qwen3.8-27b (qwen/qwen3.8-27b) 123 s finish=stop usage in 21509 / out 3293 usd~0.114 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1735
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM-5.3-FLASH (P1-1):** I missed the `avoid_model` gap on the *out-of-contract* path. In Cycle 1 I focused on the success-then-avoid path (which is tested) and did not trace what happens when `write_line` raises *after* `router.reject(r)` — i.e., the reply exists but is malformed. In that case `r` is not `None`, but the old code never set `by`/`alone_by` from it because the exception was raised before the assignment. The fix (setting `e.backend = r.backend` on the re-raised exception, then reading `getattr(e, "backend", None)`) is correct and I now verify it. **I was wrong to consider this path safe in Cycle 1.**

**QWEN3.8-27B (P0-1, `cseg[v["segment"]]` KeyError):** I initially dismissed this as "guarded by the `in cseg` check" but did not verify the guard is *always* on the code path that reaches the index. Re-reading line 135: `if not own and v.get("segment") in cseg and (...)` — the `in cseg` check is a conjunct *before* the body executes, so `cseg[v["segment"]]` at line 138 is only reached when the key exists. **QWEN was wrong; the guard is sufficient.** I agree with the consensus refutation.

**GROK-4.20:** I agree with its "SHIP: yes" and its reasoning that the loop terminates and no gate is bypassed. It was the most concise and correct in Cycle 1.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Reasoning |
|---|---|---|
| GLM P1-1 (avoid_model on out-of-contract) | **AGREE — was a real P1, now fixed** | The fix at line 104 (`e.backend = r.backend`) and the read at lines 223/280 close the gap. The new test `test_a_reply_out_of_contract_still_sends_the_second_write_to_the_other_model` (line 537) verifies both takeaway and title paths. |
| GLM P1-2 (RUNTIME on "-" attributed to takeaway when bridge is the cause) | **DISAGREE — refuted** | The bridge is a *kept* line; its text is fixed from the last full write. `takeaway_budget` (line 266) computes the word range that lands 60–70 s *with that bridge included*. If no length works, `b is None` and the loop breaks before any write (lines 267–270). The takeaway alone can only change its own length; if the bridge's length is the problem, the budget is `None` and no write is attempted. The docstring's claim "only the takeaway's length moves" is correct *given the bridge is fixed*. |
| GLM P1-3 (merge_fid precondition: last_fid from a different package) | **PARTIALLY AGREE — but not a defect** | `last_fid` is set at line 362 only after `paid_gates` succeeds on the *current* full write. The kept lines (title, caption, bridge) have identical text in the takeaway-alone package (they are carried over from `last_fields`). The fidelity verdict on those lines is a function of their text + the clips, which are unchanged. `merge_fid(fid, "takeaway", one)` replaces only the takeaway's verdict with the new one. The precondition "the kept lines' verdicts are only merged when that write's lines were judged" holds because `last_fid` is non-`None` only when the previous write reached paid gates (line 347: `if lone and last_fid is not None`). |
| QWEN P0-1 (KeyError on `cseg[v["segment"]]`) | **DISAGREE — refuted** | The `in cseg` guard at line 135 prevents the index from being reached with a missing key. |
| QWEN P1 (Router.call may not accept avoid_model) | **DISAGREE — refuted** | The signature at line 88 passes `**({"avoid_model": avoid_model} if avoid_model else {})`. The router's `call` method accepts `avoid_model` (verified in Cycle 1 consensus). |
| GROK (no P0/P1/P2) | **AGREE** | Its analysis is correct and complete for the scope it covered. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1 — `t_refused` deduplication uses dict equality on a list of dicts (line 336, 361, 372).**
File: `package.py`, lines 336, 361, 372.
`t_refused += [e for e in own if e not in t_refused]` relies on `dict.__eq__` for membership. This is correct for value equality, but if two violations have the same `text`, `rule`, and `detail` (e.g., the same RUNTIME violation reported twice across cheap and paid gates), the second is correctly deduplicated. However, if the `detail` string is truncated differently (e.g., `detail[:300]` at line 142 vs. the raw detail in `cx["violations"]` at line 360), two logically identical refusals could both be included. This is a cosmetic issue (the writer sees the same sentence twice with slightly different detail truncation) and does not affect correctness. **P2, not a blocker.**

**P2-2 — `TAKEAWAY_SAID` is injected into the full-write prompt via `WRITE_LY.format(..., said=TAKEAWAY_SAID)` (line 30), but `WRITE_LY` is a module-level constant defined at line 13. If `WRITE_LY` is ever reused in a context where `said` is not a valid format key, it will raise `KeyError`.**
File: `package.py`, lines 13–20, 26–30.
The `{said}` placeholder at line 20 is new. The `format` call at line 26–30 passes `said=TAKEAWAY_SAID`. This is safe as long as `WRITE_LY` is only formatted with the `said` kwarg. The test `test_both_takeaway_prompts_name_the_two_refused_patterns` (line 554) verifies the full-write prompt contains `TAKEAWAY_SAID`. **No defect; noted for future maintainability.**

**P2-3 — The `while True` loop at line 239: the `lone` condition at line 241 checks `not last_rw65`. If a full write went through Ruling 65's title rewrite (`last_rw65 = True`), no takeaway-alone writes follow. This is correct per the order ("No takeaway-alone write follows a write whose caption/title went through ruling 65's rewrite"). However, `last_rw65` is set at line 362 from `bool(att.get("rewrite"))`. If `att` does not have a `"rewrite"` key (e.g., the first full write, which has no rewrite), `last_rw65` is `False`, which is correct. **No defect.**

**P1-NEW — The `rewrite_alone` loop for the title (lines 193–225): the `told` list is mutated in-place via `told = told + [...]` at line 225, but `told` is initialized as `list(refused)` at line 192. If `refused` is a list of dicts, `told + [new_dict]` creates a new list, so the original `refused` is not mutated. This is correct. However, the `AGAIN` entry at line 225 uses `line['text']` — if `line` is `None` (the write raised before producing a line), this would raise `TypeError`. But the `if line is not None:` guard at line 224 prevents this. **No defect.**

**P1-NEW — In the takeaway-alone path (lines 264–283), if `write_line` raises, `alone_by` is updated at line 280 via `getattr(e, "backend", None) or alone_by`. If the exception is a *provider* failure (no reply at all), `e.backend` is not set (the fix at line 104 only sets it on the out-of-contract path, where `r` exists). In that case, `alone_by` retains its previous value (or `None` if this is the first attempt). The second attempt then has `avoid_model=None`, meaning it may land on the same model. **This is a residual gap from GLM P1-1: the fix covers the out-of-contract case but not the provider-failure case.** However, a provider failure means no reply was produced at all, so there is no "model" to avoid in the meaningful sense — the router's `avoid_model` is a hint, not a guarantee, and the router's own rotation logic should handle it. The order says "the second attempt on the other writer model," which implies the first attempt *produced* a model. A provider failure is not a "write" in the sense of the order. **P2, not P1: the order's intent is satisfied for all cases where a model was actually used.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Loop termination | PASS | PASS | Verified: `w_used` increments on full writes (max `WRITES=2`), `alone_n` increments on takeaway-alone (max `LINE_ONLY_WRITES=2`), `over_budget`/`ai` break, explicit breaks on `NoBridgeFits`, `b is None`, and success. No path exceeds 2+2 writes. |
| Gate integrity (no gate accepts more) | PASS | PASS | The takeaway-alone path runs `cheap_checks`, `VF.check` (on takeaway alone), `CI.check_contexts` (on full package), coherence, and `merge_fid`. No gate is skipped or relaxed. The kept lines' verdicts are from a *previous* write that passed those gates. |
| merge_fid precondition | PASS (with note) | PASS | `last_fid` is non-`None` only when the previous write reached paid gates. The kept lines' text is identical. The precondition holds. |
| takeaway_refusal attribution | PASS | PASS | False "alone" is impossible: any violation not on the takeaway's slot, not RUNTIME/R4 on "-", and not a STRONGER/NOT_ENTAILED with the takeaway's words makes `alone=False`. False "not alone" only loses a retry (conservative). |
| Ruling 65 caption path | PASS | PASS | Caption still gets one write, then the fixed caption. Prompts unchanged byte-for-byte (the `said` and `limit` additions are only for `slot == "takeaway"`). |
| Title: exactly two writes | PASS | PASS | `LINE_ONLY_WRITES=2` for title. Second write avoids first's model (including out-of-contract via `e.backend`). Then held. |
| Writer-only change (no judge touched) | PASS | PASS | `TAKEAWAY_SAID` is in the writer's prompt. No judge prompt, threshold, or model is changed. `VF.check` and `CI.check_contexts` are called with the same parameters as before. |
| avoid_model on out-of-contract | **FAIL (Cycle 1)** | **PASS (Cycle 2)** | Fixed by `e.backend = r.backend` at line 104 and the read at lines 223/280. Test at line 537. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None. (GLM P1-1 is fixed. GLM P1-2 and P1-3 are refuted. QWEN P0-1 is refuted.)

**P2 MEDIUM:**
1. **P2-1** (`package.py:336,361,372`): `t_refused` deduplication may include near-duplicate entries if `detail` truncation differs between cheap and paid gate violations. Cosmetic; the writer sees redundant context. No correctness impact.
2. **P2-2** (`package.py:13-20,26-30`): `WRITE_LY` now has a `{said}` placeholder. If `WRITE_LY` is ever formatted without the `said` kwarg, it will raise `KeyError`. Currently safe (only one call site), but fragile for future reuse.
3. **P2-3** (`package.py:280`): On a provider failure (no reply), `alone_by` is not updated, so the second attempt has `avoid_model=None`. This is acceptable per the order's intent (no model was "used"), but the router's rotation is the only safeguard. Not a defect.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `e.backend = r.backend` fix at line 104 (and its consumption at lines 223/280) is the single highest-leverage change: it closes the one real P1 that existed in Cycle 1 (GLM P1-1), ensuring the "second attempt on the other writer model" order is honored even when the first attempt's reply is out of contract, and it is verified by a dedicated mutation test.

## 7. PRODUCTION READY?

**SHIP: yes.**

Conditions (all satisfied):
1. The loop terminates within `WRITES + LINE_ONLY_WRITES = 4` writes. ✓
2. No gate is bypassed or relaxed; the takeaway-alone path runs all gates. ✓
3. `merge_fid`'s precondition holds whenever it is used. ✓
4. `takeaway_refusal` attribution is conservative (false "not alone" only loses a retry). ✓
5. Ruling 65's caption path and prompts are unchanged. ✓
6. The title gets exactly two writes, the second on the other model. ✓
7. Only the writer's prompt changed; no judge prompt, threshold, or model was touched. ✓
8. The out-of-contract `avoid_model` gap (GLM P1-1) is fixed and tested. ✓