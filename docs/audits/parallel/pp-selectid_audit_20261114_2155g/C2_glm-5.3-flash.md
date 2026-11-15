# glm-5.3-flash (z-ai/glm-5.3-flash) 103 s finish=stop usage in 12148 / out 2663 usd_reported=0.000707 usd~0.076 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid, RULING 107 (1) guard)

Reviewer: this audit, second pass. Inputs: the FIXED diff (C2_STEP.diff, 375 lines), the Cycle-1 outputs of qwen3.8-27b and glm-5.3-flash, and the consensus record.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

- **qwen's `return None` inside the loop (line 106).** This is the sharpest catch of Cycle 1 and I under-weighted it. Reading the FIXED code: `return None` at line 116 of the diff (source line 106) sits at loop-body level, so `nothing_new` examines exactly ONE previous directory — the newest `ledger_*` — and gives up if it lacks a readable, matching, open_work-0 FINGERPRINT.json. The docstring (lines 103–105) says "the newest earlier FINISHED build ... A build that stopped early writes none, and neither does a --from-candidate one ... so neither can stand for a full build" — which *implies* pass-over-and-continue semantics for non-finished builds. The code does pass over unreadable ones (`continue`, line 113) but not readable-but-mismatched ones. I missed the asymmetry: unreadable → continue, readable-but-different → return None.
- **glm's F4 (routing not in the fingerprint).** I did not flag that `--routing` selects which models judge yet was absent from the hashed inputs. The fix (line 76, `routing` in `parts`, and line 126 passing `a.routing`) is correct and the test at lines 243–245 pins it. Missed by me.
- **glm's F11 framing (next build's pool depends on this build's outputs).** The consensus refutation is measured and convincing (byte-identical 157 moments across two builds; outputs fingerprinted as they stand at the END of the build that read them). I had not pressed on this; their evidence settles it.

## 2. AGREE / DISAGREE, FINDING BY FINDING

- **qwen: "only the single newest previous build is checked" — AGREE, and it is the real defect.** But note the consensus record does NOT list it as implemented; it lists the string-search fix and routing. So the `return None`-in-loop bug survives into the FIXED diff. Verified against the test: `test_only_the_newest_finished_build_counts` (lines 288–311) never exercises the case "newest finished build mismatches, an older one matches" — the sequence 200000(F) → 210000(no FP) → 220000(G) → 221000(F, left=1) → 222000(F) works only because 222000 is the newest. Add 223000(G) after 222000 and the 222000 match becomes unreachable. The docstring promises pass-over; the code delivers first-match-or-None on the newest only.
- **glm F1/F2/F5/F6/F7 — AGREE with the refutations.** F2 (time-varying `now`): only `CA.due(reg, now)` reads `now`, and it changes exactly when new work appears; the 3h-equality test (lines 214–215) and the coming-due test (254–260) pin both sides. F6 (skip writes no FINGERPRINT.json): correct and *necessary* — if a skip wrote a FINGERPRINT, a chain of skips would each compare against the previous skip's (identical) inputs, which is fine, but the test at line 365 pins the chosen semantics; either is defensible, the pin is what matters.
- **glm F3 / qwen (string-search `open_work`) — AGREE, fixed correctly.** `_errors` (lines 80–87) walks dicts/lists structurally; the tests at lines 282–286 cover nested errors, a non-dict/list scalar, and a string quoting the phrase. One residual: `_errors` counts *any* dict with `verdict == "error"` anywhere in `res` or `sp`, including diagnostic/summary sub-records that merely *report* an error. If `res` ever embeds a copy of the lock's error segments under a different key, they'd be double-counted. P3 — it errs toward "work left," which sends the build to the router, the safe direction.
- **Consensus: "an older match counting" mutation — PARTIALLY AGREE.** The consensus claims mutation "an older match counting" was killed, which suggests they believe older matches *can* count. With `return None` in the loop, they cannot. Either the mutation was tested against a differently-ordered fixture, or the mutation testing missed the actual semantics. Worth one line of doubt.

## 3. NEW FINDINGS (Cycle 2)

- **[P1] N1 — `nothing_new` checks only the newest ledger directory; readable-but-mismatched builds are not passed over.** Lines 106–117. The `return None` at line 116 is inside the `for`. Consequence: any finished build whose fingerprint differs *shields* all older finished builds. Scenario: build A (fp=F, clean) → code change → build B (fp=G, clean) → code reverted → build C (fp=F). C's inputs equal A's, A left nothing undone, yet C runs the full model because B (newest) mismatches. Not a wrong result (C's judgments are still valid), but it defeats the $0.00 guarantee in exactly the revert/oscillation case the guard exists for, and it contradicts the docstring's "a build that stopped early writes none ... so neither can stand for a full build" — that clause explains why *unreadable* entries are skipped, yet readable mismatches are not. Fix: change line 116 `return None` → `continue` (one word), or add the missing test. Note the consensus's own mutation list ("an older match counting") implies the continue semantics was believed tested; it is not, for the readable-mismatch case.
- **[P2] N2 — the driver-level test's fingerprint is computed with `datetime.now(timezone.utc)` (line 324) while the previous build's FINGERPRINT was written from the same call — fine — but `PLG.CA.due` is invoked against a *patched* REGISTRY path that has no file; if `CA.due`/`new_registry` read REGISTRY lazily and the proof dir lacks CANDIDATES.json, the test passes only because the stubs return empty.** Fragile but green; P3.
- **[P3] N3 — `fingerprint`'s `precheck_results` part (lines 67–70) hashes `(name, size, mtime)` triples, not contents.** An integrator that rewrites a result file in place with identical size and same-second mtime (e.g., a re-serialization) is invisible. mtime granularity is platform-dependent; on some filesystems it's 1 s. The consensus's "byte-identical" evidence was about the *pool*, not these files. A content hash would cost one read. P2→P3: the failure direction is a missed skip (cost, not correctness).
- **[P3] N4 — `code_content` (lines 46–55) opens every file with no error handling; a dangling `__pycache__`-adjacent symlink or a concurrently-truncated pipeline/*.json raises OSError out of `fingerprint`, which now runs *before* the router — killing the $0.00 path with a traceback instead of a build.** It's the fail-closed direction (M12), so acceptable, but a `try/except` returning a sentinel would degrade to "always run" rather than "never run." Judgment call; P3.
- **[P3] N5 — test line 309–310: the one-liner `open(... if os.makedirs(...) is None else "", "w")` relies on `os.makedirs` returning None; correct but unreadable.** Nit.
- **[P3] N6 — `open_work`'s `sp.get("held_102")` (line 96) assumes `sp["held_102"]` is a list; if the render-lock record ever nests it (as `res`'s is nested under `prescreen`), the count silently drops.** The structural-`_errors` fix was applied to verdicts but not to held-102. Asymmetry; P3.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| fingerprint coverage | 9/10 | 9/10 | routing now in; precheck hashing by (name,size,mtime) is the only softness (N3) |
| nothing_new semantics | 7/10 | 6/10 | qwen's loop finding confirmed in the FIXED code; the consensus's mutation claim doesn't hold for readable mismatches |
| open_work | 8/10 | 8.5/10 | structural walk is right; held-102 asymmetry (N6) and possible double-count remain, both safe-direction |
| tests | 8/10 | 7.5/10 | good breadth, but the decisive "older finished build shields" case is untested, which is why N1 survived the C1 fixes |
| driver integration | 9/10 | 9/10 | guard before router, skip writes NOTHING_NEW only, fail-closed on code-read errors |

## 5. FINAL PRIORITY LIST

- **[P1] N1 — proof_ledger.py, `nothing_new`, diff lines 106–117 (esp. 116):** `return None` inside the loop; only the newest finished build is ever consulted; readable-but-mismatched builds shield older matches, contradicting the docstring (lines 103–105) and the consensus's own mutation claim. Fix: `continue` + a test where the newest finished build mismatches and an older one matches.
- **[P2] — test_ruling_107_guard.py, lines 288–311:** add the missing case to `test_only_the_newest_finished_build_counts` (newest = "G", older = "F" → expect the older returned). This is the test that would have caught N1.
- **[P3] N3 — proof_ledger.py, lines 67–70:** hash pre-check result *contents*, not (size, mtime).
- **[P3] N6 — proof_ledger.py, line 96:** held-102 in `sp` should be located structurally, like verdicts.
- **[P3] N4 — proof_ledger.py, lines 52–54:** decide deliberately whether a code-read OSError should crash (fail-closed) or degrade to "run the build."

No P0s: the guard never skips a build that has new work (Q1 — every input that constitutes new work is hashed, and the coming-due/ET-day/precheck tests pin it), and no model call precedes the decision (Q2 — the guard sits after inputs.json, before `build_router`, and the driver test makes building a router an error, lines 331–352, 358–365).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Make `nothing_new`'s loop `continue` past a readable-but-mismatched newest build (one word, line 116) and pin it with the missing "older finished build matches" test — that is the only place where the code, the docstring, and the consensus's own mutation record disagree.

## 7. PRODUCTION READY?

**Yes with conditions.** Conditions: (a) apply the one-word `continue` fix at line 116 (or, failing that, amend the docstring to say "only the newest ledger directory is consulted" and accept the shielding); (b) add the newest-mismatches-older-matches test; (c) confirm the "an older match counting" mutation actually exercised a fixture where the newest finished build mismatches — if it did, show it, because the shipped code says it cannot.

P1_OR_WORSE: 1