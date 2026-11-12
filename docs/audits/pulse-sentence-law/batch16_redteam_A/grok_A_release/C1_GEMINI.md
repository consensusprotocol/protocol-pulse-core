Excellent. This is a substantial and critical change to the pipeline's quality and release process. I will review it against the provided laws and context.

---

### Q1: CORRECTNESS

The changed functions appear to do what their docstrings and the governing laws state. The design philosophy is clearly "fail-closed," and this is implemented robustly.

*   **`release_auth.py` (new file):** This module is the centerpiece.
    *   `blockers()` (line 580): Correctly implements the inventory check. It fails on missing required rows, non-`PASS` verdicts for required rows, unexpected rows, and invalid verdicts. It also correctly treats `MONITORING` rows as needing to be present but not deciding the outcome (lines 598-600). The check for execution evidence (lines 604-611), requiring `executed: True` and `samples >= 1`, is a strong guard against vacuous passes.
    *   `attest()` (line 638): This function correctly creates a verifiable snapshot. It reads from disk, calculates current hashes, and compares against what the gates measured (lines 662-665). It correctly includes the run state (`run_state.get("ok") is True`, line 668), ensuring that a run with any `holds` cannot be attested as passing. The atomic write via `os.replace` is good practice.
    *   `authorise()` (line 683): This is a correct and paranoid re-verification. It doesn't trust the verdict in `ATTESTATION.json`; instead, it re-runs `blockers()` on the attested rows (line 702). It re-hashes every bound file and compares it to the attested digest (lines 719-727). This function correctly ensures that what is being authorized for delivery is *exactly* what was checked and approved, moment-by-moment.

*   **`run_fresh.py`:**
    *   `stage_gates()` has been refactored for clarity and safety. The new `put()` helper function (line 87) ensures gate results are stored in a structured way, separating the verdict from notes and evidence. This is much safer than parsing string prefixes like `"PASS(L-c: ...)"`.
    *   The implementation of Law L-c (lines 215-249) is updated to use `L.edges_on_final`, directly matching the amended law's text which requires measuring on the final deliverable. This is a crucial correctness fix.
    *   The new `verdict_for()` (line 303) correctly delegates the verdict logic to `release_auth.blockers`, removing the old, fragile string-prefix-based logic. This is a huge improvement.
    *   `record_assets()` (line 311) is now more robust. It correctly checks for modifications against the *launch* revision (`launch`), not `HEAD` (line 343), which prevents race conditions in a busy repository.
    *   `attest_run()` (line 357) is the final checkpoint. It correctly aggregates all potential failure reasons (existing holds, non-candidate verdict, dirty code) and creates a final attestation. Line 377 is critical: `if att["verdict"] != "ALL_PASS" and run.status.get("verdict") == VERDICT_CANDIDATE: run.status["verdict"] = VERDICT_HOLD`. This ensures the run's final saved state can never disagree with the attestation, creating a single source of truth.

No obvious off-by-one errors, unit mismatches, or silent exceptions were found. The entire change is geared towards preventing a `PASS` on missing or failed data, in compliance with M12.

### Q2: LAW COMPLIANCE

The code appears to be compliant with all applicable laws.

*   **SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS:** The implementation of these laws is not in the diff, but their enforcement is significantly strengthened. Gates like `G16_sentence_boundary`, `G17_onset_tail`, and `G15_credits` are now listed as `REQUIRED` in `release_auth.py` (lines 556-557). Any verdict other than exactly `PASS` will block the release. **COMPLIANT**.
*   **L-a SIGN-OFF NAMES ALL:** `G20_signoff_names_all` is a `REQUIRED` gate (line 557). **COMPLIANT**.
*   **L-b EDGE WORDS WHOLE:** Enforced via the `G17_onset_tail` required gate. **COMPLIANT**.
*   **L-c DISSENT IS RIGHT UNTIL DISPROVED:** The diff contains a direct and correct implementation of the amended law. `run_fresh.py:235` calls `L.edges_on_final` to get proof from the bytes being approved, and this proof is used to adjudicate G3b/G3c disagreements (lines 237-247). **COMPLIANT**.
*   **L-d PROTECTED PREVIEW:** No changes in the diff relate to this law. **CANNOT VERIFY**.
*   **L-e to L-i, L-k:** The code implementing these laws is not in the diff. However, the new framework ensures that if any of these laws are violated in a way that causes a gate to return a non-`PASS` verdict, the release will be blocked. The enforcement mechanism is compliant. **PARTIAL (enforcement mechanism is compliant)**.
*   **L-j RELEASE IS AUTHORISED ON THESE BYTES:** This is the primary focus of the diff. The new `release_auth.py` module, its comprehensive tests, and its integration as the final step in `run_fresh.py` and the first step of delivery (as implied by docstrings) is a robust and complete implementation of this law. The removal of the legacy send path in `run.py:35-39` further strengthens this. **COMPLIANT**.
*   **LAW 20 / M2 (thresholds constant, failure is a hard stop):** The new `release_auth.py` module hard-codes the required gates and the `PASS` verdict. It is no longer possible for a prefixed pass (e.g., `PASS(waiver)`) to be accepted. This enforces the law strictly. **COMPLIANT**.
*   **M12 FAIL CLOSED:** The entire architecture of `release_auth.py` is built on this principle. A missing file, a missing gate row, missing evidence, an unreadable report, or a corrupted attestation all result in a failure to authorize. **COMPLIANT**.
*   **LAW 22 (v2f reference):** No changes in the diff appear to alter rendering or selection logic that would affect the v2f reference render. **COMPLIANT**.

### Q3: TESTS

The new tests in `pipeline/test_release_auth.py` are excellent and directly prove the claims of the `release_auth.py` module.

*   **`TestPassingRun` (line 841):** Correctly establishes a baseline that a well-formed, clean run is authorized.
*   **`TestInventory` (line 850):** Systematically proves that mutations to the gate report cause failure.
    *   It correctly tests deleting every single required row (line 856).
    *   It tests a comprehensive list of non-`PASS` verdicts (line 861).
    *   It correctly confirms that a `FAIL` in a `MONITORING` row *does not* block release, while a missing `MONITORING` row *does* (lines 870-880). This precisely matches the law's addendum.
*   **`TestEvidence` (line 890):** Proves that missing or malformed execution evidence (e.g., `samples: 0`) is a blocker. The list of `bad` evidence formats is thorough.
*   **`TestBytes` (line 911):** Crucially proves the core of law L-j. It tests that a file changed *after* gating but *before* attestation is caught (line 912), and that a file changed *after* attestation is also caught (line 919). The assertions are specific and not vacuous.
*   **`TestPackAndRun` (line 944):** Covers failures related to the verification pack and the overall run state (e.g., a run with holds, a non-deliverable replay). The test for an edited attestation being refused (line 982) is particularly good, proving that `authorise()` re-validates the data instead of trusting the file's "verdict" field.

The tests are not vacuous and provide high confidence in the new release authorization mechanism.

### Q4: VERDICT

The changes are a dramatic improvement to the pipeline's safety and reliability. The introduction of a strict, verifiable, and centralized release authorization mechanism directly addresses the root cause of the problem described: gates that passed editorially incorrect content. This change ensures that what the gates measure is what gets delivered, and that the definition of "pass" is non-negotiable.

There are no severe defects. One minor point for consideration:

*   **LOW** | `run_fresh.py:104` | Comment is slightly out of date | The comment `G11_parity(run_gates) ... see G11 below` is now less relevant because an unexpected row like `G11_parity(run_gates)` would be a hard failure in `release_auth`. The old `rows` dictionary was more of a human-readable report; now it's a machine-checked contract. The code is correct (the row is not added), but the comment refers to an old behavior. | Suggest removing the comment line `rows[fmt]["G11_parity(run_gates)"] = ...` and its new counterpart `put("9x16", "G11_parity", ...)` is handled at line 113-114. The old line 104 `rows[fmt]["G11_parity(run_gates)"] = "NOT RUN BY run_gates (no horiz) — see G11 below"` has been removed from the code, but the intent of the comment should be clarified or removed. *Correction upon re-reading: The original line was removed. My point is moot as the code no longer contains this. The change is correct as is.*

My apologies, upon re-reviewing the diff, I see the line I was referring to (`rows[fmt]["G11_parity(run_gates)"] = ...`) has indeed been removed. The new code is correct and my point is invalid. The code is clean.

This is a well-engineered, thoroughly tested, and compliant solution to a critical problem.

**VERDICT: READY**