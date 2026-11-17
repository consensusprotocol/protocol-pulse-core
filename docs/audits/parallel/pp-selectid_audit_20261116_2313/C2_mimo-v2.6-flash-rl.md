# mimo-v2.6-flash-rl (xiaomi/mimo-v2.6-flash-rl) 157 s finish=stop usage in 9938 / out 13230 usd_reported=0.001580 usd~0.228 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid-20261116_2313 (RULING 130 (2))

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma's [P0] was wrong, and I would have been right to reject it in Cycle 1.** Gemma's excerpt of the no-voice path omitted the outer guard `if nv_pre is not None and not nv_pre.get("ok"):` (package.py ~3457). A HOLD has `ok=False`, so that guard fires and `return None` executes before `see(order)` is ever reached. Gemma's logic chain (error is None → segments populated → if fails → proceeds to see) is correct *for the inner `if`* but irrelevant because the outer guard already returned. Claude's C1 consensus correctly identified this. Gemma's secondary claim — that tests miss the no-voice branch — is also wrong: `test_the_no_voice_line_up_asks_the_lock_too` drives the no-voice line-up with a holding lock and asserts `z` is never in `rig.visual_calls`; mutation K2 was killed by it.

**Qwen's [P2] on the `bg = {}` orphan-future invariant** is a legitimate observation I would have flagged as P3 in Cycle 1. Qwen correctly notes that the invariant ("`bg` is read only inside the writes loop, which a re-lined/no-verdict line-up never enters because `w_used = writes`") is enforced only by control flow, not by an assertion or structural guard. A future refactor of the writes loop that moves the `w_used` check later would silently read an empty `bg`. This is pre-existing (the original code had the same pattern), but the new code makes `bg = {}` a *new* default state that didn't exist before, so the invariant is now more load-bearing. I agree this is P2, not a merge-blocker.

**Qwen's [P3] on `lock_for`'s per-call iterator** and **[P3] on missing `isinstance` guard** are both correct and both correctly deprioritized. No disagreement.

---

## 2. WHERE I AGREE / DISAGREE

| Finding | Model | Verdict | Why |
|---|---|---|---|
| [P0] No-voice path proceeds to `see(order)` on HOLD | Gemma | **Disagree — refuted.** | Outer guard `if nv_pre is not None and not nv_pre.get("ok")` catches holds (`ok=False`) and returns `None` before `see(order)`. Gemma's excerpt omitted this line. |
| Tests miss the no-voice branch | Gemma | **Disagree — refuted.** | `test_the_no_voice_line_up_asks_the_lock_too` covers it; mutation K2 killed. |
| [P2] `bg = {}` orphan-future invariant is comment-only | Qwen | **Agree.** | Valid structural fragility. Pre-existing pattern, but `bg = {}` is a new default. P2. |
| [P3] `lock_for` iterator is per-call | Qwen | **Agree.** | Cosmetic; build is single-shot. No action. |
| [P3] No `isinstance(pre, dict)` guard | Qwen | **Agree.** | Contract violation exposure, not a regression. P3. |
| All 5 requested checks PASS | Qwen | **Agree.** | I independently verified each. See §3 below. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] Behavioral change: lock no-verdict now pre-empts a `vbad` re-line that would have masked it

**File:** `pipeline/package.py`, main line-up loop (diff lines 56–89).

In the **original** code, the order was: `see(segs)` → `vbad` → (if `vbad`, re-line, skip lock) → lock check. So if a line-up would fail the vision check (`vbad` truthy) **and** the lock would give no-verdict, the original code re-lined the line-up (search continued) and **never observed the lock's no-verdict**. The lock was only asked about the *next* line-up (the re-lined one).

In the **new** code, the lock runs first. If it gives no-verdict on line-up A, `no_verdict = True`, the search stops — even though A would have failed the vision check anyway and been re-lined.

**Is this a defect?** No — it is the *intended* behavior per RULING 130 (2) ("run the lock pre-check on every line-up candidate BEFORE any paid vision check") and per Law M12 (fail closed: a no-verdict is never a pass, the search stops). The original code's behavior was arguably a latent bug: it masked a lock no-verdict behind a `vbad` re-line, paying for a vision check on a line-up whose lock answer was never recorded. The new code is strictly more conservative and saves money.

**However**, this is a real behavioral delta that the PR description does not call out. A reviewer comparing old vs. new behavior on a line-up that would both fail `vbad` **and** get a lock no-verdict would see: old → re-line (search continues), new → stop (search halts). This should be documented in the PR description or a code comment. Severity: **P2** (should document; not a code change).

### [P3] `vbad` is not computed when the lock holds or gives no-verdict — `rec["why"]` attribution changes

**File:** `pipeline/package.py`, main line-up loop (diff lines 75–89).

In the original, if both `vbad` and a lock hold were true, `rec["why"]` was set by the `vbad` branch (it ran first). In the new code, the lock branch runs first, so `rec["why"]` is set by the lock branch (`"ruling 72: the render's lock holds ..."`). The `vbad` branch never runs. This is *more accurate* (the lock is the first reason for rejection) but is a subtle change in the recorded reason string. Not a defect. **P3**.

### [P3] No-voice path: `lock_stop` is not set on a HOLD (only on no-verdict)

**File:** `pipeline/package.py`, no-voice path (consensus excerpt, ~3457–3461).

When the lock holds a clip in the no-voice path, `out["lock_stop"]` is **not** set (only `note["why_not"]` is). When the lock gives no-verdict, `out["lock_stop"]` **is** set. This is correct: a hold rejects the specific no-voice line-up (the caller can try another), while a no-verdict stops the search entirely. Consistent with the main loop's behavior. Not a defect. **P3** (noting for completeness).

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 (est.) | Cycle 2 | Why changed |
|---|---|---|---|
| Main line-up loop reorder | PASS | PASS | Independently verified: lock runs first; `bg`/`see`/`vbad` gated by `not relined and not no_verdict`; writes loop invariant holds. |
| No-voice path reorder | PASS | PASS | Outer guard `if nv_pre is not None and not nv_pre.get("ok")` correctly catches holds and no-verdicts before `see(order)`. |
| `lock_off` / `lock_for` driver | PASS | PASS | `lock_off` returns `ok=False, segments=[], error=...` → no-verdict path in both loops → never a pass (Law L-m). |
| `bg = {}` invariant | PASS | PASS (P2) | Correct today; structurally fragile. Pre-existing pattern, new default state. |
| Tests | PASS | PASS | 6 new/modified tests cover main loop (hold, no-verdict), no-voice (hold), lock_off, lock_for, bad flag. 6/6 mutations killed. |
| Behavioral delta (lock no-verdict pre-empts `vbad` re-line) | not flagged | **P2 (document)** | Intended per ruling; should be called out in PR description. |

**No P0 or P1 findings.** Gemma's P0 was refuted. Qwen's P2 is valid but not a blocker. My new P2 is a documentation gap, not a code defect.

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **`pipeline/package.py` main loop (diff lines 56–89):** Document the behavioral change where a lock no-verdict now pre-empts a `vbad` re-line that would have masked it in the original code. Add a comment or PR description note. (New finding, this review.)
2. **`pipeline/package.py` line ~3729 (diff line 75):** The `bg = {}` default relies on the writes loop's `w_used = writes` early-break to never read it. Add a one-line assertion or invariant comment at the `bg = {}` site. (Qwen's [P2], agreed.)

**P3 NIT:**
3. **`tests/package/proof_ledger.py` `lock_for` (diff line 116):** Per-call iterator restarts numbering if `lock_for` is called twice. Cosmetic; no action needed. (Qwen's [P3].)
4. **`pipeline/package.py` main loop (diff lines 60–62):** No `isinstance(pre, dict)` guard after `lock_check(segs)` returns. Contract guarantees a dict; not a regression. (Qwen's [P3].)
5. **`pipeline/package.py` main loop:** `rec["why"]` attribution changes when both `vbad` and lock-hold are true (lock branch now wins). More accurate; no action needed. (New finding, this review.)

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add a one-line invariant comment or assertion at `pipeline/package.py` diff line 75 (`bg = {}`) stating that the writes loop's `w_used = writes` early-break guarantees `bg` is never read when empty — this is the only structural fragility in an otherwise correct reorder.

---

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. Address P2 #1: add a comment or PR description note documenting that a lock no-verdict now pre-empts a `vbad` re-line (behavioral change from original, intended per RULING 130 (2)).
2. Address P2 #2: add an invariant comment at `bg = {}` (one line, no code change).
3. Re-run the full suite (40 files, 854 tests) and confirm 6/6 mutation kills after any comment-only edits (sanity check).

No code logic changes required. The reorder is correct, the guards are correct, the tests are adequate, and the driver flag is safe.

---

P1_OR_WORSE: 0