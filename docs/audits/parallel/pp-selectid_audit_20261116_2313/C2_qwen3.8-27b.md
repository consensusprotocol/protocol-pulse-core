# qwen3.8-27b (qwen/qwen3.8-27b) 98 s finish=stop usage in 10158 / out 8309 usd_reported=0.006397 usd~0.155 (upper-bound price)



# CYCLE 2 — FINAL REVIEW: pp-selectid-20261116_2313 (RULING 130 (2))

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma's [P0] (no-voice path hold falls through to `see(order)`):** I initially flagged this as a concern in my own reading of the diff excerpt, but upon tracing the full control flow (as Claude's consensus did), the outer guard `if nv_pre is not None and not nv_pre.get("ok"):` (existing code, not shown in the diff because it's unchanged context) catches **both** holds and no-verdicts, and `return None` fires before `see(order)`. Gemma's excerpt omitted this outer guard, making the inner `if nv_pre.get("error") or not nv_pre.get("segments"):` look like the sole gate. **Gemma is wrong here.** I should have caught this in Cycle 1 by noting the diff hunk header `@@ -3465,6 +3459,12 @@` implies surrounding context lines that include the outer guard.

**Qwen's [P2] (bg orphan-future invariant):** Valid observation. When `vbad` triggers a re-line after `bg` is populated, the pool futures are submitted but never collected. This is pre-existing behavior (the original code had the same pattern), but the new code makes `bg = {}` the explicit "empty" sentinel, making the invariant slightly more load-bearing. Not a regression, but worth a comment.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Reasoning |
|---------|---------|-----------|
| Gemma [P0]: no-voice hold reaches `see(order)` | **DISAGREE** | The outer `if nv_pre is not None and not nv_pre.get("ok"):` guard (existing, unchanged) returns `None` for any not-ok response (hold or no-verdict) before `see(order)` is reached. The test `test_the_no_voice_line_up_asks_the_lock_too` (line 220: `assertNotIn("z", rig.visual_calls)`) and mutation K2 confirm this. |
| Gemma: tests miss the no-voice branch | **DISAGREE** | The no-voice test at line 220 explicitly asserts the held clip is never in `visual_calls`. |
| Qwen [P2]: bg orphan-future is comment-only | **AGREE** | Pre-existing pattern; the writes loop's `w_used == writes` break guarantees `bg = {}` is never read. A future refactor could break this silently. |
| Qwen [P3]: lock_for iterator per-call | **AGREE** | Cosmetic; single-shot build per process. |
| Qwen [P3]: no isinstance guard on pre | **AGREE** | Pre-existing; contract guarantees dict. |
| Qwen: all 5 checks PASS | **AGREE** | Confirmed independently below. |

## 3. NEW FINDINGS FROM THIS REVIEW

**[P3] The `lock_off` function ignores its `segs` parameter.**
`proof_ledger.py` line 101: `def lock_off(segs):` — the parameter is accepted but never used. This is intentional (it's a stub that always returns the same no-verdict shape), but a linter or future reader might flag it. A `_segs` or a docstring note would clarify. Not a defect.

**[P3] No explicit test that `lock_check=None` (no lock at all) still populates `bg` and calls `see`.**
The diff doesn't add a test for the "lock_check is None" path in the main loop. However, this path is exercised by every existing test that doesn't pass a `lock_check` argument (the default in `Rig` is presumably `None`), and the behavior is unchanged from the original. Not a gap in practice.

**No new P0, P1, or P2 findings.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| Main loop ordering (lock before bg/see) | PASS | PASS | Confirmed: `bg = {}` + `if not relined and not no_verdict:` gate is correct. |
| No-voice path ordering | PASS (with doubt) | PASS | Resolved: outer guard `not nv_pre.get("ok")` catches holds. Gemma's P0 was a misread of the diff excerpt. |
| lock_off / lock_for driver | PASS | PASS | Shape correct, never a pass, numbered requests, bad value refused. |
| bg invariant (orphan futures) | N/A | [P2] | Pre-existing; new code makes it slightly more load-bearing. Comment recommended. |
| Test coverage | PASS | PASS | 3 new/modified tests in test_medley, 3 in test_ledger_build. 6/6 mutations killed. |
| Law compliance (M12, L-m, L-d) | PASS | PASS | Fail-closed on lock_off and exceptions. No gate thresholds modified. |

## 5. FINAL PRIORITY LIST

| Severity | Finding | Location |
|----------|---------|----------|
| [P2] | `bg = {}` orphan-future invariant is comment-only; a future refactor of the writes loop could silently discard submitted pool futures. Add a one-line `# INVARIANT:` comment at the `bg = {}` site (package.py diff line 75) noting that `w_used = writes` guarantees the writes loop never reads `bg` when it's empty. | `pipeline/package.py` (diff line 75) |
| [P3] | `lock_off(segs)` ignores its parameter; rename to `_segs` or add a docstring note. | `tests/package/proof_ledger.py` line 101 |
| [P3] | No defensive `isinstance(pre, dict)` guard after `lock_check(segs)`; if the contract is ever violated, `.get()` raises `AttributeError` outside the try/except. Pre-existing. | `pipeline/package.py` (diff lines 60-62) |

**No P0 or P1 findings.**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The reordering itself (lock check before `bg`/`see`) is the entire value of this diff — it prevents the exact $0.129 waste that motivated RULING 130 (2) — and it is correctly implemented in both the main loop and the no-voice path; the only remaining risk is a future refactor that breaks the `bg = {}` / `w_used = writes` invariant, which a single comment would mitigate.

## 7. PRODUCTION READY?

**Yes.**

Conditions (all satisfied by the current diff):
1. Lock pre-check runs before any paid vision/exclusion/truth check in both the main line-up loop and the no-voice line-up. ✓
2. A held or no-verdict line-up never triggers `see()`, `exclusion_for`, or `truth_for`. ✓
3. A passing line-up is byte-identical in its downstream behavior (bg population, see, vbad, writes loop). ✓
4. `lock_off` returns `{"ok": False, "segments": [], "error": ...}` — structurally incapable of being a pass. ✓
5. `--lock-precheck` defaults to `"on"`; `"off"` is a safe no-op that preserves the line-up as a budget candidate. ✓
6. Tests: 6/6 mutations killed; 854 tests across 40 suite files pass by exit code. ✓

The [P2] comment is a nice-to-have for maintainability, not a merge blocker.

---

P1_OR_WORSE: 0