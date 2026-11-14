<!-- z-ai/glm-5.3-flash, 89 s, finish stop, $0.0007 (vendor usage.cost) -->

# PROTOCOL PULSE — CYCLE 2 AUDIT
**Reviewer:** Gemini 2.5 Pro · **Target:** `pp-tests_b78c3` · **Scope:** the 331-line diff (mutations record + BIBLE additions + `test_f0_cpu_guard.py`)

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **The trailing-comma record format (glm, and qwen's consensus disposition #1).** I noticed it in Cycle 1 ("Cosmetic; not worth a fix") and dismissed it. The session then *fixed* it (`f"{what}({a[0]!r})"`, line 283) and the fix is correct — `a[0]!r` of a scalar renders without the tuple comma. I under-credited this: the record string is the primary diagnostic a developer sees when the wall fails, and `subprocess.Popen('/bin/cat',)` vs `subprocess.Popen('/bin/cat')` is the difference between "is that a tuple arg or a trailing artifact?" and "the program is `/bin/cat`". Right call to fix it; I was wrong that it wasn't worth a fix.
- **The mutations record as a diff-internal artifact (glm P1).** I reviewed the test logic and called the diff "merge-ready" without noticing the *evidence* for the change (M6/M7/M8 passing the old test) lived only in the session's scratchpad — unverifiable from the diff. That's a process finding, not a code finding, which is why I missed it, but it's the single most important addition in this cycle: `pp-tests_AUDIT_B78C3_MUTATIONS.md` now makes the "nothing measured is never a pass" (L-m) claim *auditable from the repo*.
- **The `hasattr` portability nuance.** I praised it as portability; glm's framing is sharper — on the target platform (Ubuntu 24.04, CPython 3.12) all 22 names exist, so the filter is dead code *there* but insurance elsewhere. Neither of us flagged the subtle cost: a *typo'd* name in `_OS_PROCESS_STARTERS` would be silently skipped by `hasattr` and the test would lose coverage without any signal. Nobody caught that. It's my new finding (§3).

What nobody missed, credit where due: the `_io.open` boundary analysis (glm's CPython-3.12-verified trace of `io.open_code → _io.open`) is the load-bearing correctness argument, and it's right.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| glm P1: mutation evidence not in diff | **Agree, fully.** | L-m is a *repo* law, not a scratchpad law. Fixed correctly: the record gives each mutation's exact `_key`, the run harness (test's own `_load_frontier_blind` + `_check_key_behaviour`, own process, bytecode on and `-B`), and verbatim results including the three side reads *passing* the previous test a55e4dcf. This is exactly what L-m evidence should look like. |
| Consensus #1: record format | **Agree.** | Fixed at line 283. Verified: `a[0]!r` on a scalar → no trailing comma; the `f"{what}()"` no-arg branch covers `os.fork()`. Correct. |
| glm P2: flag_after / sys.path asserts "may have been dropped" | **Agree with the refutation.** | They're unchanged lines outside the hunks; the mutations record shows M3/M4 still failing on *their own* assertions, which is positive proof the asserts survived. The session's refutation is evidence-backed, not hand-waved. |
| glm P3: restore pre-existing `sys.modules['_pp_key_stub_record']` | **Agree with NOT ACTED ON.** | The name is test-private (grep the diff: only `_check_key_behaviour` touches it); `pop(..., None)` is correct. Restoring a pre-existing entry would add state-capture complexity for zero coverage. |
| qwen P2: `sys.addaudithook` would also see `io.FileIO`, pre-bound `open`, ctypes | **Agree, and agree it's correctly deferred.** | It's a real coverage boundary — a `_key` that reads via `ctypes`-level `open(2)` and returns the *stub's* value would pass. But the integrator's "nothing else changes" constraint governs, the boundary is documented in three places (code comment L273–275, BIBLE PP-E32, test docstring L326–327), and it's offered as follow-up. Deferring is the right process call. |
| qwen: "os.spawn* go through os.fork" comment (L245) | **Partially agree.** | Technically imprecise — CPython's `os.spawn*` use `posix_spawn`/`fork+exec` depending on platform and flags, not uniformly `fork`. But the test patches *both* families *and* `Popen` explicitly, so the imprecision costs nothing. Comment-accuracy nit only. |
| glm's `got.append(None)` double-failure note | **Agree, correctly judged minor.** | If a denial fires, `denied == []` (L313) fails first and names the culprit; the sentinel failure is redundant, not confusing. |

No disagreement rises to the level of "the finding is wrong."

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P3). `_OS_PROCESS_STARTERS` + `hasattr` = silent coverage loss on typo.** Lines 246–248 + 277. If a name in the tuple is misspelled (e.g. `"posix_spwan"`), `hasattr(os, n)` returns False, the name is silently skipped, and the test still passes — coverage quietly shrinks with no signal. Nobody caught this in Cycle 1; I found it by cross-reading the 22-name list against `dir(os)` on 3.12: all 22 exist, so *today* the list is fully covered, but the mechanism has no self-check. A one-line guard — `assert all(hasattr(os, n) for n in _OS_PROCESS_STARTERS), "typo in _OS_PROCESS_STARTERS"` — would fail loudly on a typo. (On non-Linux where a name legitimately doesn't exist, the assert would need the same `hasattr`-per-name logic; simplest is to keep the filter and accept the risk, or assert only the names the target platform guarantees. Either is fine; the point is the mechanism is currently silent.)

**N2 (P3, informational). The mutations record's harness claim is trust-but-verify.** Lines 13–18: "Each was loaded by test_f0's own `_load_frontier_blind(path)` and checked by its own `_check_key_behaviour`" — this is the strongest property of the evidence (the wall's exact assertions, not a re-implementation), but the record doesn't show the *harness code* itself, so a reader trusts the prose. Acceptable for an evidence doc; noting it because it's the residual gap between "recorded" and "reproducible" — the scratch copies are gone, so exact reproduction requires re-deriving the mutations from the shown `_key` bodies (which *are* shown, so it's derivable — this is why it's informational, not a finding).

**N3 (P3, informational). `deny` closures record `a[0]` only.** Line 283. For `subprocess.Popen` the first arg is the argv list — the record shows the program, which is what you want. For `os.exec*`/`os.spawn*` the first arg is the *path*, also right. No case in the denial list where `a[0]` is misleading. No action.

Nothing in the combined analysis changes the correctness verdict: the denial mechanism, restoration, the `_io.open` boundary, and the fail-closed property all hold.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Correctness | 99 | 99 | Unchanged. The consensus fixes (record format, mutations doc) are correct; my new findings are P3/informational. |
| Law compliance | 100 | 100 | L-m evidence now *in the repo* — this was the one compliance gap, and it's closed. |
| Security | 95 | 95 | Unchanged; the subprocess-denial closes the side-read exfil channel within the test's scope; the documented `ctypes`/`FileIO` boundary remains, correctly. |
| Frontend | N/A | N/A | — |
| Backend quality | 98 | 98 | The record-format fix improved diagnostics; N1's silent-`hasattr` risk is the only deduction, unchanged from Cycle 1 (I just hadn't articulated it). |
| **Overall** | **98** | **98** | The cycle-2 additions (mutations record, format fix) were exactly the right changes; nothing new was broken. |

## 5. FINAL PRIORITY LIST

- **P0 CRITICAL:** none.
- **P1 HIGH:** none.
- **P2 MEDIUM:** none. (The integrator's "nothing else changes" constraint means even N1's one-line guard is a follow-up, not a ship-blocker — and it genuinely is minor: all 22 names verified present on the target platform.)
- **P3 (record, not blockers):** N1 — silent-`hasattr` typo risk, lines 246–248/277, suggest the one-line assert as follow-up; N2 — harness prose vs. reproducibility, mutations record lines 13–18; N3 — no action.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Already done: committing the mutations record into the diff (glm's P1) — it converts the test's L-m claim from "the session says the mutations fail" into repo-auditable evidence, which is the difference between a test that *is* trusted and a test that *can be checked*.

## 7. PRODUCTION READY?

**Yes, as-is.** Conditions (all follow-ups, none blocking):

1. (Follow-up) Add the one-line `hasattr` self-check for `_OS_PROCESS_STARTERS` (N1) — or accept the documented risk; all 22 names exist on the target platform, verified.
2. (Follow-up, already offered) `sys.addaudithook` to close the `io.FileIO` / pre-bound-`open` / ctypes boundary — correctly deferred under "nothing else changes", documented at code L273–275, BIBLE PP-E32, and docstring L326–327.
3. (Standing) Keep the mutations record updated if `_key`'s denial list changes — the record's results block (lines 171–195) is now part of the test's contract.

No P0/P1/P2. Merge.