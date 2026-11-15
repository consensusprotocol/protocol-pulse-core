# glm-5.3-flash (z-ai/glm-5.3-flash) 28 s finish=stop usage in 8467 / out 1691 usd_reported=0.000472 usd~0.051 (upper-bound price)

# PROTOCOL PULSE — CYCLE 3 AUDIT (final)
# Feature: pp-selectid-20261115_1129 — the C3_STEP.diff (registry() fix + end-to-end test)

Scope: the 84-line C3 diff against hook112.py/test_hook112.py, judged as the fix of the one real defect Cycle 2 missed (main() died on `import proof_saved_runs` — a module from another test folder, not on this driver's sys.path). I check the fix, the new test, and whether anything the fix touches regresses.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

- **The ModuleNotFoundError itself.** Nobody in Cycle 2 (me included) ran main() end-to-end; every test exercised the pieces, so the one import that only main() performs (`import proof_saved_runs` inside the calibration branch) was never executed. That is the lesson: the 12 tests were all *component* tests, and the defect lived exactly in the seam between them. The new `TestTheDriverEndToEnd` is the right closure of that gap, and it is the single most valuable addition of this cycle.
- **Grok's Cycle-1 P2 (rater=None spotlight path) and the consensus's "ledger-id fallback test"** — both were recorded as "for the next change," and this diff *is* that next change; neither was folded in. Fair, since the C3 diff is scoped to the crash, but the ledger is now open for the next ruling.

## 2. WHERE DO I AGREE OR DISAGREE?

- **The fix's shape (registry() reading pipeline/channels.json directly) — agree.** It is the minimal correct repair: proof_saved_runs.REG is documented as that same file, the docstring says so, and dropping the import removes the cross-folder dependency entirely rather than fixing the path. Direct-read beats import-path surgery for a diagnostic driver. One dependency assumed: that tests/select_by_id/proof_saved_runs.REG and pipeline/channels.json stay the same file. If they ever diverge, the calibration's eligibility Context silently reads a different registry than the proof runs did. [P3] — the docstring already notes the equivalence; a one-line assertion (or a test comparing the two files) would pin it. Not required.
- **The end-to-end test — agree it is the right test, with two nits.** It stubs exactly what should be stubbed (the router, the paid call, stdout) and leaves everything else real: the funnel, the traces, the four JSON outputs, the report. The assertions are the strong kind — the *call record* (`asked == [(len(REFS), None, seed, True) for s in SEEDS]`) proves no-cache (cache is None, not "unset"), every seed, and a real Context, rather than asserting output shapes. Two things it does not check:
  - [P3] It never asserts the *content* of FUNNEL.json/NEAR_MISSES.json/HOOK_PASS.json — only that the five files exist. A regression that writes empty-but-valid outputs would pass. Acceptable: the component tests cover content; this test's job is "main() runs," which it does.
  - [P3] `TestTheHookPass().db(d)` — borrowing another test class's helper rather than a fixture. Works, mildly fragile to refactoring.
- **The mutation (restoring the import) is killed — agree this is the right mutation.** It targets exactly the defect: with the import restored, main() raises ModuleNotFoundError, the test fails. That proves the test actually guards the fix, which is the whole point of C3.
- **Grok's Cycle-2 scores — agree with their direction; nothing in C3 changes them.** The fix touches the calibration's Context construction only; funnel, roll-up, near-misses, hook-pass, and read-only guarantees are untouched by this diff (verified: the diff's only production-code change is lines 23/28-29, the import→registry swap).

## 3. NEW FINDINGS FROM THIS REVIEW

- [P3] hook112.py, registry() (new lines ~401-405): no error handling if pipeline/channels.json is missing — it raises FileNotFoundError, which is *correct* for a diagnostic (fail loudly), but the traceback will point at registry() rather than "the registry moved." A one-line `raise`-with-message or a comment would help. Nit.
- [P3] test_hook112.py, new test (~line 258): `json.load(open(...))` without closing — fine in tests, CPython-finalizer-dependent. Nit.
- [P3] The test's `rate` stub returns `ctx.channel("no-such-channel") is None` — it verifies the Context is *a* Context, not that it is the *registry-backed* one. If registry() returned `{}` (empty file), the test still passes. A stronger assertion would compare one known channel. [P3] — the component tests cover the Context; this is defense-in-depth only.
- Nothing at P1 or above. The fix is correct, minimal, and guarded.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Cycle 3 | Why changed |
|---|---|---|---|---|
| Funnel / trace logic | P1:2 | P2:2 | P2:2 | Untouched by C3; prior fixes hold |
| Read-only & isolation | P1:1 | P3:1 | P3:1 | Untouched; mode=ro and no-cache still tested |
| Calibration / router | P2:2 | P3:2 | P3:2 | The import crash fixed; registry read directly; Context equivalence documented, not asserted |
| Ledger / roll-up | P2:1 | P2:1 | P2:1 | Untouched |
| Test coverage | P2:2 | P2:2 | P3:2 | The end-to-end test closes the component-test blind spot that hid the crash |
| Overall | P1:3 | P2:3 | P3:3 | Every known defect fixed; residuals are documentation/robustness nits |

## 5. FINAL PRIORITY LIST

- [P3] hook112.py:401-405 — registry(): consider asserting/verifying pipeline/channels.json matches proof_saved_runs.REG (or a comment that they must not diverge).
- [P3] test_hook112.py:~258 — the e2e test checks file existence, not output content; a known-channel assertion in the rate stub's Context would strengthen it.
- [P3] test_hook112.py:~268 — `TestTheHookPass().db(d)` borrowed helper; hoist to a fixture when next touched.
- [P3] hook112.py:401 — registry() failure mode: FileNotFoundError with no context; a message naming the registry would help the next 11:52-style diagnosis.

P0: 0, P1: 0, P2: 0, P3: 4.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Keep the end-to-end test as the permanent gate: it is the only test that executes main()'s import graph, and it is what would have caught the crash that all 12 component tests (and three reviewers) missed.

## 7. PRODUCTION READY?

**Yes.** Conditions (all satisfied by this diff, stated for the record): (a) the import of proof_saved_runs is gone and the mutation restoring it is killed — verified; (b) the calibration still runs Heimdall-only, no cache, under the $0.30 cap — untouched by C3 and still tested; (c) the four P3 nits above are recorded for the next change to this driver, none blocks.

P1_OR_WORSE: 0