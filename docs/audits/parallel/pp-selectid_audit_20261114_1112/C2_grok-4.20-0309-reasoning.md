# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 20 s finish=stop usage in 9751 / out 1219 usd~0.079 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261114_1112**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's H1 on the narrow `ValueError` catch (only `ValueError`; `TypeError`/`AttributeError` on a non-dict manifest would propagate out of `check_deterministic`) and the Python 3.10 `fromisoformat` behavior for plausible ISO datetimes with time components. Qwen's decoupling concern for `SNAP_MAX_S` (hard-coded 35.0 vs. `spotlight.SPOT_S[1]`) and the test asserting equality only at test time. Grok's LAW-20/M2 framing (even though ultimately refuted). I had flagged the regex lookahead and chunk-boundary consistency but missed the locale-driven month name risk that GLM surfaced and that the `MONTHS` table now fixes.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM H1: partially agree — the `TypeError` propagation is real (`manifest=[...]`) but unverifiable downstream without caller source; the "malformed date leaves text unchanged" behavior matches the ruling and is now explicitly tested (line 114).  
   - GLM H2 / Qwen regex analysis: agree — the lookaheads and backtracking correctly protect "November 120", "2026-11-120", and "November 12, 2025"; tests at :110-116 confirm exact detail tokens. Withdrawn as bug.  
   - Grok <critical>: disagree — this change *implements* the 10:48 ruling (3); it does not retroactively alter LAW 20. The prior must-pass cases now correctly pass for the intended reason.  
   - Qwen <high> on SNAP_MAX_S: agree on fragility of the hard-coded value, but the new test (ledger_build:138-139) and updated comment + consensus verification that no other code assumes 20 s make it acceptable.  
   - Qwen on `strict_features` and test coverage: fully agree — the three call sites now read identical post-removal text; missing-date case is explicitly re-tested.  
   - Claude consensus on medley isolation, locale fix, and manifest format: fully agree; all verifiable from the diff + static background facts.

3. **NEW FINDINGS FROM THIS REVIEW**  
   <medium> vo_fidelity.py:56 (`re.sub(..., flags=re.I)`) + :54 (`month` pattern uses English literals): concrete input `{"date": "2026-11-12"}`, text=`"pulse check for november 12."` (lowercase) now correctly strips under `re.I`, but a future non-English manifest date string would still be rejected by `fromisoformat` before the month table is reached. Not a violation of current ruling but a latent locale assumption.  
   <medium> ledger_build.py:10 (hard-coded `35.0`) + test_ledger_build.py:138: the test imports `spotlight` and asserts equality, but production `ledger_build` still has no import and would silently diverge if `SPOT_S[1]` ever changes. Matches Qwen's concern; the test catches it but does not enforce single source of truth at runtime.  
   No criticals; nothing that lets a non-manifest date escape or lets a >20 s moment reach a medley.

4. **REVISED SCORES**  
   | Subsystem          | Cycle 1     | Cycle 2     | Why changed |
   |--------------------|-------------|-------------|-------------|
   | SNAP_MAX_S / reanchor | <medium>   | <medium>   | Test now verifies spotlight parity; medley isolation confirmed by package.usable facts. |
   | without_manifest_date + NUMBER/NEEDS_SOURCE | <high> | <medium> | MONTHS table + exhaustive test cases (9 mutations killed, 5 ok/7 bad forms) resolve locale and edge-case gaps I and GLM initially flagged. |
   | strict_features consistency | <low> | <low> | Unchanged; still correct. |
   | Overall risk       | High       | Medium     | Cycle 1 gaps closed by fixes and cross-review consensus. |

5. **FINAL PRIORITY LIST**  
   **P2 MEDIUM**  
   - ledger_build.py:10 — replace hard-coded `35.0` with `import spotlight as SPOT; SNAP_MAX_S = SPOT.SPOT_S[1]` (single source of truth).  
   - vo_fidelity.py:49 — move `from datetime import date` to top of file (style; also makes the 3.10 `fromisoformat` limitation more visible).  
   - tests/package/test_gates.py:114 — add one explicit malformed manifest case (`"date": "2026/11/12"`) to document that digits remain and trigger NUMBER (already implied but not concrete).

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   The `MONTHS` table + `without_manifest_date` centralization (vo_fidelity:39-56) — it simultaneously fixes locale, prevents bare-number leakage, keeps the three readers (NEEDS_SOURCE, NUMBER loop, strict_features) consistent, and is exhaustively tested.

7. **PRODUCTION READY?**  
   Yes with conditions: (1) import `spotlight` at top of ledger_build.py instead of hard-coding 35.0 (or keep constant but add runtime `assert LB.SNAP_MAX_S == SPOT.SPOT_S[1]`), (2) move the inner `import date` to module level. These are the only remaining medium items; all attack vectors (a–c) are closed by the updated tests, package.usable facts, and `_governed` chunking behavior. SHIP after those two edits.