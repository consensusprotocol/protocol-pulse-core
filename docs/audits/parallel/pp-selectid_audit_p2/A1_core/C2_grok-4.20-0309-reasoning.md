# grok-4.20-0309-reasoning (xAI, medley key) 33 s usage=46467

**CYCLE 2 AUDIT — pp-selectid-p2 (post-fix review of A1_core/STEP.diff)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**  
Cycle 1 (my own output) focused on the optional second-pass, empty-claims fidelity verdict, and pin asserting literals. I completely missed: (a) the double-subtraction bug in runtime estimation (sonnet P1-1 / opus arithmetic note), (b) Router.down being permanent and content-triggered (sonnet P1-3), (c) _title_case suppression defeating NAME on headlines (grok P2), and (d) the one-directional negation comparison in transcript_truth (all three Claudes). The consensus correctly flagged that exclusion_verdict was only wired through the adapter while production used miner self-report. Those were material.

**2. WHERE DO YOU AGREE OR DISAGREE?**  
- **Strong agreement on C1/C2 (pin literals + empty claims):** Fully fixed. `inventory()` now emits a sealed per-gate row with measured/replayed flags; `package_pin.gate_problems()` and `to_pin()` refuse anything but exact PASS + replayed=False; `seal()` binds the gated bytes. `package_pin` no longer hard-codes True.  
- **Agreement on second-pass optionality / one-directional comparison:** Fixed. `build()` now requires `work_dir`, submits `truth_for()` for every segment in the background, treats any error as `ok=False` (NOT RUN in inventory), and drops the package. Trigger is still numbers/negations only (names still skipped), but the plain-VO path is gone from the main flow.  
- **Partial agreement on vendor separation (L-x):** The JSON-driven chains, explicit `avoid_vendor`/`avoid_family` in every verdict call, `_writers()` lookup, and Router._skip() logic are excellent. Hard-coded `"openai"` is gone. I still see `OpenAITranscribe` and `XAIBackend` classes naming their vendors, but that is implementation, not role code; the law is satisfied. Minor remaining leak: Heimdall tripwire is Heimdall-specific.  
- **Disagreement on Q4 severity:** Title-case suppression and PRICE_NOW tolerance holes remain in `vo_fidelity` (not in this chunk but referenced). However, they are now explicitly in the deterministic inventory row and will block the pin. False-reject on "both agree" same-video case is mitigated by the new `a_use` step-A reuse. Net safer than Cycle 1.  
- **Exclusion gate:** Now correctly run in `exclusion_for()` + background pool + inventory row. Miner `m.get("excluded")` is only an early filter; L-v 2 / exclusion failures now reline. Consensus verified.

**3. NEW FINDINGS FROM THIS REVIEW**  
- **P2: inventory() can emit "NOT RUN" yet still reach `out["package"]`** (`package.inventory:1137-1140`, `build:1082`). If any exclusion or second_pass returns measured=False, the row status becomes NOT RUN, but the coherence gate can still win the race and ship the package before the background futures are fully checked in all paths. The `lost = {mid for mid, (e,t) in got.items() if ...}` check only happens *after* paid gates, not before coherence. A late exclusion failure can be ignored if coherence already passed.  
- **P2: seal() rounds start/end to 3 decimals but moments may have higher precision** (`package_pin.seal:1183`). YouTube t= parameters and transcript_sha256 are preserved, but any downstream sentence-law lookup that relies on exact float equality could diverge.  
- **P1: Router.down is still permanent for the entire build() run** (`providers:1910`). A single oversized prompt on local:gemma3 marks it down for all subsequent angles/writes/verdicts even though the orchestrator wants "Ultron first". A transient GPU lease loss would collapse the whole cycle.  
- Minor: `current_levels()` only uses sentences that name Bitcoin + present-tense; does not catch "right now" or "currently" variants that vo_fidelity accepts. Edge-case desync between deterministic PRICE_NOW and the levels passed to the verdict.

**4. REVISED SCORES**

| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Q1 Fail-open           | 42      | 88      | Empty-claims, optional truth pass, and pin literals fixed; measured flags and GateNotMeasured now enforced everywhere. Residual NOT-RUN race is narrow. |
| Q2 Vendor separation / L-x | 78   | 93      | JSON-only config, avoid_vendor/family on every verdict call, no role hard-codes models. Only permanent .down and Heimdall-specific tripwire remain. |
| Q3 Verbatim / model text | 82    | 91      | Clip text is source verbatim; all writer output now runs through sealed inventory + fidelity + context before pin. Angle text stays forensic. |
| Q4 Deterministic rules | 48      | 72      | Title-case and tolerance holes still exist but are now inventory-gated and block the pin. False-reject "both agree" improved. |
| Q5 Tests / R7 / wiring | 25      | 80      | Adapter, inventory, seal(), gate_problems(), and pinned.py contract are present. Full end-to-end R7 test not in diff, but wiring is no longer vacuous. |

**5. FINAL PRIORITY LIST**  
**P0 CRITICAL** (must fix before ship): None — the previous P0s are closed.  
**P1 HIGH:**  
- `package.build:1066` / `inventory:1134`: move exclusion + second_pass future checks *before* coherence verdict so a late failure cannot ship (add explicit `if any(not e.get("measured") for e in exc.values())` guard).  
- `providers.Router:1909`: make .down role-specific or add a reset mechanism; permanent down after one local context error violates "Ultron first".  
**P2 MEDIUM:**  
- `package_pin.seal:1183` + `assemble:560`: canonicalise floats to same precision as transcript store.  
- Extend `critical_tokens` trigger to names (L-v 1/2).  
- Add test that a replayed gate blocks the pin (currently only checked in gate_problems).

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The sealed GATE INVENTORY + recomputed `package.seal()` / `gate_problems()` + R7 refusal on any mismatch is the highest-leverage change; it cryptographically binds every deterministic and model verdict to the artefact that ships, turning the previous vacuous pin into an enforceable chain of custody.

**7. PRODUCTION READY?**  
**Yes with conditions.** Conditions: (1) the P1 race between background exclusion/second-pass and coherence must be closed, (2) full end-to-end test of a pin through the downstream factory (validate → render → sentence-law) must pass with the new moments_package schema, (3) at least one live run must exercise every role's failover under the new JSON config, and (4) the remaining deterministic holes (title-case, price tolerance) must be tightened or explicitly documented as accepted residual risk now that they live in the inventory. With those four items closed, the package is safer than any prior version and meets the L-j / L-m / L-x standard.