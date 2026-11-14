<!-- z-ai/glm-5.3-flash, 86 s, finish stop, $0.0006 (vendor usage.cost) -->

# PROTOCOL PULSE — CYCLE 2 AUDIT
**Reviewer:** Claude (session reviewer, second pass)
**Target:** `pp-tests_b78c2` — tests/adversarial/test_f0_cpu_guard.py + BIBLE_ADDITIONS (UPDATED diff, 161 lines)
**Status:** **PASS** — one P2, one P3, no P0/P1.

---

## SECTION 1: WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the three Cycle 1 reviews:

1. **glm's P1 (vacuous bytecode check under `-B` / `PYTHONDONTWRITEBYTECODE`) — I missed it.** I praised the `dont_write_bytecode` handling in Cycle 1 without noticing that if the *environment* already sets the flag, the "no `__pycache__` beside the loader" assertion (L141) passes even if `_key` never touches the flag. The fix in the updated diff (L120–122: force `sys.dont_write_bytecode = False` for the calls, restore the environment's value in the `finally` at L133, then assert `flag_after is False` at L140) is exactly right and makes the check non-vacuous. This was the strongest finding of Cycle 1 and it was not mine.

2. **glm's P2 (record-module leak if a statement before the `try` raises) — I missed it.** In the Cycle 1 code, `sys.modules[rec.__name__] = rec` sat outside the `try`. In the updated diff it is inside (L119), and the `finally` pops it (L134). Correct.

3. **glm's P3 / qwen's P3 (comment the double patch and the `io.open_code` dependency) — I missed the documentation gap.** Now covered at L123 and L149–150. The `io.open_code` assumption is the load-bearing trick of the whole test; it deserved a comment, and it has one.

4. **qwen's P2 (pop `_pp_fb_under_test` from `sys.modules`) — I also would have raised this.** The consensus refutation is measured and I agree: `module_from_spec` + `exec_module` without a `sys.modules` insertion registers nothing, so there is nothing to pop. Verified reasoning, not just assertion.

5. **Gemini's P2 (also deny `os.environ` / `subprocess`) — I agree with the refutation.** The behaviour under test is "the *value* comes from the loader": a `_key` that bypasses via environ returns something that is not the sentinel and fails at L136. Denying environ would also forbid what the production `relay.get_key` legitimately does (reads the environment first). The consensus is right; the check as scoped is tighter, not looser.

What nobody caught, including me, in Cycle 1: see Section 3.

## SECTION 2: WHERE DO I AGREE OR DISAGREE?

| # | Finding (reviewer) | Verdict | Why |
|---|---|---|---|
| 1 | glm P1: bytecode check vacuous under `-B` (glm) | **AGREE — accepted, fixed** | L120–122, L133, L140. Measured: mutations fail under both regimes now. |
| 2 | glm P2: record-module leak (glm) | **AGREE — accepted, fixed** | Insertion moved inside `try` (L119), popped in `finally` (L134). |
| 3 | glm P2: document the fresh-copy assumptions (glm) | **AGREE — accepted, fixed** | Docstring L92–94 states them: top level only sets constants, no self-lookup, not registered. |
| 4 | glm P3: `path` parameter dead (glm) | **AGREE with refutation** | It is the mutation seam; now documented as such (L94). |
| 5 | glm/qwen P3: comment the double patch + `io.open_code` (both) | **AGREE — accepted, fixed** | L123, L149–150. |
| 6 | glm P3: show `len(got)` (glm) | **AGREE with not-acted-on** | L137 already shows one type per call, which implies the length. |
| 7 | qwen P2: pop `_pp_fb_under_test` (qwen) | **AGREE with refutation** | Measured: nothing registers in `sys.modules`. No leak exists. |
| 8 | Gemini P2: deny environ/subprocess too (Gemini) | **AGREE with refutation** | The value-comes-from-loader assertion (L136) already catches bypasses; denying environ would forbid the production loader's legitimate behaviour. |

No disagreements with the Cycle 1 consensus. All eight dispositions are either correctly accepted-and-fixed or correctly refuted with evidence.

## SECTION 3: NEW FINDINGS FROM THIS REVIEW

**N1 (P2). The `finally` at L131–134 can mask the *original* failure.** If the code under test raises something that is neither `_FileOpened` nor caught by the loop (e.g., a `KeyboardInterrupt` mid-`_key`, or an unexpected `AttributeError` from a mutated `_key`), the `try` block aborts, the `finally` runs — and if a *restoration* statement in the `finally` itself raises (e.g., `builtins.open, io.open = real_open, real_io_open` cannot realistically fail, but `sys.dont_write_bytecode = flag_env` cannot either; the realistic one is... none), the original traceback is replaced. In practice, all three restoration statements are simple assignments that cannot raise, so this is theoretical. Downgrade: this is a **P3** — note it, don't fix it. Actually, on reflection: the more interesting variant is that if `_key` raises a non-`_FileOpened` exception, the loop at L125–129 catches only `_FileOpened`, so the exception propagates, the `finally` restores state, and the *test* fails with that exception — which is correct fail-closed behaviour. So N1 is genuinely P3, informational.

**N2 (P3). `H.control` at L155–156 evaluates `os.path.isfile` on a hardcoded absolute path.** `/home/ultron/...` — this is the documented, intentional configuration pin (the docstring at L152–153 says so, and the consensus blessed it as a "labelled control"). But it makes the suite non-portable to any machine where the tree lives elsewhere. Nobody flagged portability in Cycle 1; the consensus explicitly blessed the pin, so this is a note, not a defect. P3.

**N3 (P3). The stub's `import sys` inside `_KEY_STUB` (L80) is executed by the import machinery with `builtins.open`/`io.open` patched.** Verified: `sys` is a builtin, already in `sys.modules` in any pytest process, so the import resolves from the cache with no I/O. But if a future refactor of the stub ever imports a *non-builtin* module (e.g., `import json`), the import machinery's `SourceFileLoader.get_data` uses `io.open_code` — still fine — but `importlib`'s frozen/`sys.path`-based import of `json` would... also use `io.open_code` for the source. So the assumption holds for any module import; the only thing that would break it is a stub that calls `open()` directly at module level. Worth one sentence in the comment at L123, not a code change. P3.

**N4 (P3). `assert flag_after is False` (L140) uses `is` on a bool.** Fine in CPython (bools are singletons), but `flag_after` was assigned at L130 from `sys.dont_write_bytecode` — if a mutated `_key` *restores* the flag to its environment's value (True under `-B`), the assertion correctly fails. Correct as written; noting only that `is False` vs `== False` is a style point, and `is` is actually the stricter, better choice here. No action.

**N5 (P3, the one worth reading). The `opened == []` assertion (L135) is the *only* thing standing between the suite and a `_key` that reads the key file through `pathlib`/`os`-level I/O.** `pathlib.Path.read_text` calls `io.open` → patched, caught. `os.open` (the *os-module* call) is **not** patched — `os.open` returns a file descriptor, not a file object, and does not go through `builtins.open`/`io.open`. A mutated `_key` that uses `os.open`/`os.read`/`os.close` would **pass** the `opened == []` check. The BIBLE_ADDITIONS text (L20) says "deny the forbidden effect during the call (open / io.open patched...)" — the rule as written is accurate to what the test does, so the documentation is not wrong, but the *rule* could be read as "no file I/O at all" when the test actually enforces "no I/O through `open`/`io.open`". Nobody caught this. It is a genuine, if narrow, gap between the rule's wording and the check's enforcement. Fix: one clause in the BIBLE_ADDITIONS rule (L20): "open / io.open patched (os-level fds are not denied)". P3, documentation-only.

N1–N4 are informational; **N5 is the only new finding with any teeth**, and it is documentation-only.

## SECTION 4: REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---| Production-ready? |
| Correctness | 96 | 97 | The glm-P1 fix (forced flag, restored in `finally`, asserted) closes the only real correctness gap; the record-module leak is closed. |
| Law compliance | 100 | 100 | No change; all laws still hold, and items 1–2 of the consensus made the check *stricter*. |
| Security (secrets) | 98 | 98 | No change; the type-only failure message (L137) remains exemplary. N5 (os-level fds) is a documentation nuance, not a leak. |
| Backend/test quality | 95 | 97 | Cleanup, isolation, and documentation gaps from Cycle 1 all closed; remaining findings are P3. |
| Documentation (BIBLE_ADDITIONS) | 93 | 96 | PP-E32 is well-written; N5's wording nuance is the only gap. |

**Overall: 96 → 97.** The updated diff resolves every accepted Cycle 1 finding; nothing regressed.

## SECTION 5: FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM:**
  - **P2-1 (N1, informational):** the `finally` at L131–134 — restoration statements are all non-raiseing assignments, so no masking risk today; if a future restoration statement *can* raise, the original failure would be masked. No action required now; flag for the next time the `finally` is edited. (tests/adversarial/test_f0_cpu_guard.py L131–134)
- **P3 (must not block):**
  - **P3-1 (N5):** BIBLE_ADDITIONS L20 — add "(os-level fds are not denied)" to the PP-E32 rule so the rule's wording matches what the check enforces. (docs/audits/parallel/pp-tests_BIBLE_ADDITIONS.md, the "Rule" bullet, second dash)
  - P3-2 (N2): the hardcoded `/home/ultron/...` pin (L155) is a documented, consensus-blessed control; note for portability, no action.
  - P3-3 (N3): if the stub ever imports a non-builtin, the `io.open_code` comment (L123) still holds; no action.
  - P3-4 (N4): `is False` vs `== False` — no action; `is` is the better choice.

## SECTION  Cycle 2 verdict

**The single highest-leverage change:** the Cycle 1 fixes already shipped — the forced-`dont_write_bytecode`-False fix (glm's P1) is the one that turned a potentially vacuous check into a real one, and it is the reason this diff is now ship-ready; the only remaining work is one clause of documentation (P3-1).

**Production ready?** **Yes.** Conditions (none blocking, all documentation-level):
1. Add the P3-1 clause to PP-E32's rule (BIBLE_ADDITIONS, the "deny the forbidden effect" bullet): note that only `open`/`io.open` are denied, not os-level fds — so the rule's wording matches the check's enforcement.
2. Optionally note the P2-1 caveat next to the `finally` (restoration statements must stay non-raiseing, or the original failure gets masked).

Both are one-line documentation edits; the code itself ships as-is.

---

*Cycle 2, final. 97/100. Ship it.*

**Reviewer: Claude — second review, final.**