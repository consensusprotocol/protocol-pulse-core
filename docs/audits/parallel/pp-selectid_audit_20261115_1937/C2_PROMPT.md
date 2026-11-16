# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_1937
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## DEEPSEEK-V4.1-FLASH — CYCLE 1 OUTPUT
# deepseek-v4.1-flash (deepseek/deepseek-v4.1-flash) 215 s finish=stop usage in 6091 / out 10504 usd_reported=0.002331 usd~0.176 (upper-bound price)

[P1] The change moves `SPEND` to `SPEND_B4.json` unconditionally. The order states BATCH 4 starts at 21:10 ET Nov 15, but this audit is generated at 19:37 UTC (14:37 ET). If this branch is merged/deployed before 21:10 ET, any batch‑3 build that starts before then will charge `SPEND_B4.json`, violating the order and corrupting batch‑3 accounting. The code must either be held until 21:10 ET or gated by a time check. The description’s “It LANDS AT 21:10 ET” is a process claim, not enforced by the code.

[P1] `tests/package/test_ruling_102.py` now uses `os.path.basename(...)`, but the diff does not add `import os`. The previous test used only `str.endswith`, so `os` may not already be imported. If it is not, the test will raise `NameError` and fail. Verify the import exists; if not, add it.

[P2] The diff does not demonstrate that no other code path still writes `SPEND_B3.json`. The prompt says `proof_ledger.py:221` is the only reader, but writers or test fixtures may still reference the old filename. A repository‑wide grep for `SPEND_B3.json` is required to confirm no stale writer remains.

[P3] The new `assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))` is redundant after the preceding `assertEqual(..., "SPEND_B4.json")`. It adds no coverage and can be removed.

P1_OR_WORSE: 2

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 27 s finish=stop usage in 5981 / out 723 usd_reported=0.014844 usd~0.048 (upper-bound price)

**CODE AUDIT REPORT — pp-selectid-20261115_1937 (C1_STEP.diff)**

**Summary**  
The diff performs a narrowly scoped rename of the active proof ledger from `SPEND_B3.json` (batch 3, closed 21:10 ET Nov 15) to `SPEND_B4.json` (batch 4, running on identical terms: $4.50 limit / $4.00 stop, "reported" basis, same ruling set through 117). Only constants, comments, and one test assertion are touched. No logic, limits, or guard conditions are altered. The change matches the verbatim order supplied ("batch 3 closes at 21:10 ET … BATCH 4 starts 21:10 ET Nov 15 … on the same terms").

**Detailed Findings**

- **[P3]** Ledger filename is the *only* item that moves (proof_ly.py:20, test_ruling_102.py:44). No functional code, limit values, basis, or Router call sites were altered. Compliant with "Smallest diff" (M1) and the explicit "PLEASE CHECK (1)" directive.
- **[P2]** The updated test now uses `os.path.basename(...)` plus an explicit `assertNotIn` blacklist for the two closed ledgers (`SPEND_LY.json`, `SPEND_B3.json`). This is strictly stronger than the previous `endswith` check. Good hygiene, but the test still hard-codes the new magic filename; a tiny helper (e.g. `current_spend_file()`) would reduce future batch churn.
- **[P3]** Comments are voluminous and contain precise timestamps/ruling citations that will rot at the next batch boundary. While accurate for the current hand-off, they increase long-term maintenance load. Consider a single source-of-truth constant block that generates the comment text.
- **[P1]** The diff touches *none* of the pipeline files that implement the governing laws listed at the top of the package (sentence_law.py, editorial_select, run_fresh.stage_gates, G17c, L-a through L-l, regression.sh, release_auth.py, canon.py, etc.). The feature description claims this branch delivers fixes for D1–D6, protected-preview enforcement, punctuated-before-read, channel-cluster ordering, claim-is-the-event, edge-word fidelity on final bytes, and the three-clean-video gate. None of that appears in the supplied code. If this is truly the *only* diff for branch `pp-selectid`, the pre-merge quality gate cannot pass; the new laws are not enforced by these changes. (Violates "this code MUST comply with every law below", LAW 20, M12, and the explicit purpose statement.)

**Compliance spot-check against key LAWS**  
- L-j / L-k / release_auth: untouched — no evidence provided that ATTESTATION.json or gate inventory changed.  
- L-d protected preview & LAW 22 (v2f byte-identical render): untouched.  
- All sentence-boundary, fade-placement, edge-word, and credit-avatar rules: untouched.  
- Spending guard logic itself (start_refused, LY_LIMIT_*, basis="reported") is correctly left alone.

**Conclusion**  
The ledger-rotation mechanics are correct and isolated. However, the complete absence of any implementation or test coverage for the massive set of editorial, acoustic, and release-authorization rules that the feature claims to deliver constitutes a blocking defect.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 22 s finish=stop usage in 6368 / out 1470 usd_reported=0.001344 usd~0.041 (upper-bound price)

I’ll audit the provided diff against the stated change, the governing laws, and the specific checks requested.

### Analysis

**1. Scope and Intent Verification**
The stated intent is to move the build ledger from `SPEND_B3.json` to `SPEND_B4.json` for "Batch 4" while keeping all financial limits (`LY_LIMIT_USD`, `LY_STOP_USD`, `LY_LIMIT_BASIS`) unchanged.

*   **`proof_ly.py`**:
    *   `SPEND` variable changes from `os.path.join(OUT, "SPEND_B3.json")` to `os.path.join(OUT, "SPEND_B4.json")`.
    *   Comments are updated to reflect Batch 4 terms and the closure of Batch 3.
    *   `LY_LIMIT_USD` remains `4.50`.
    *   `LY_STOP_USD` remains `4.00`.
    *   `LY_LIMIT_BASIS` remains `"reported"`.
    *   *Verdict*: Matches intent. No logic changes, only configuration path and documentation.

*   **`test_ruling_102.py`**:
    *   The test `test_no_build_starts_at_the_stop_and_one_starts_below` is updated.
    *   Old assertion: `self.assertTrue(PLG.PL.SPEND.endswith("SPEND_B3.json"))`.
    *   New assertions:
        *   `self.assertEqual(os.path.basename(PLG.PL.SPEND), "SPEND_B4.json")`
        *   `self.assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))`
    *   *Verdict*: The test correctly verifies the new path and explicitly guards against regression to the closed ledgers. This is a robust improvement over the previous `endswith` check.

**2. Governing Laws Compliance**
*   **LAW 20 / M2 (Gate Thresholds/Constants)**: The constants `LY_LIMIT_USD` and `LY_STOP_USD` are unchanged. The change is purely a file path pointer. No gate logic is altered.
*   **M12 (Fail Closed)**: The code relies on `proof_ledger.py` (not shown, but referenced) to handle the missing file case. The diff notes: "A missing SPEND_B4.json starts at $0 (the Router's own ledger creation, unchanged)." This implies the underlying infrastructure handles initialization safely. Since the diff does not modify the initialization logic, and the previous behavior for `SPEND_B3.json` was presumably safe, this change does not introduce a new fail-open risk.
*   **Smallest Diff**: The diff is minimal. It touches only the necessary variable and its associated test assertions.

**3. Specific Checks Requested**
*   **(1) That nothing but the ledger's file name moves**:
    *   `SPEND` path changes.
    *   Comments change.
    *   Test assertions change to match the new path.
    *   Financial constants (`LY_LIMIT_USD`, `LY_STOP_USD`, `LY_LIMIT_BASIS`) do **not** change.
    *   *Result*: Pass.

*   **(2) That no other code path still writes SPEND_B3.json**:
    *   The diff only shows `proof_ly.py` and `test_ruling_102.py`.
    *   `proof_ly.py` defines `SPEND` which is used by `proof_ledger.py` (via `PL.SPEND`).
    *   If `proof_ledger.py` or any other module hardcoded `SPEND_B3.json`, it would not be visible here. However, the prompt states: "Files: tests/package/proof_ly.py ... tests/package/test_ruling_102.py". It implies these are the *only* modified files.
    *   The description says: "proof_ledger.py:221, spend_path=PL.SPEND, the only code that reads it". This suggests `PL.SPEND` is the single source of truth for the path.
    *   *Risk*: If any *other* script (e.g., a cron job, a separate audit script, or a manual tool) hardcodes `SPEND_B3.json`, it would continue to write to the old file. However, based *strictly* on the provided code and the assertion that `PL.SPEND` is the only reader/writer path in the active pipeline, this is compliant.
    *   *Result*: Pass (with the caveat that external hardcoded references are out of scope for this diff, but the internal architecture described supports this change).

*   **(3) The test**:
    *   The test now uses `os.path.basename` for precise matching.
    *   It explicitly asserts the new name is `SPEND_B4.json`.
    *   It explicitly asserts the new name is *not* the closed ledgers.
    *   It still verifies the stop/limit logic (`start_refused`).
    *   *Result*: Pass. The test is stronger than before.

**4. Potential Issues**
*   **None found in the diff itself.** The change is a clean configuration update.
*   **Documentation**: The comments in `proof_ly.py` are updated to reflect the new batch. This is good practice.
*   **Backwards Compatibility**: The test ensures that if someone accidentally reverts `SPEND` to `SPEND_B3.json`, the test will fail. This is a good guard.

### Findings

No P0, P1, P2, or P3 findings were identified in the provided diff. The change is minimal, correct, and well-tested.

1.  **[P3] Nit**: The comment in `proof_ly.py` line 23-25 is slightly dense. "BATCH 4 (orchestrator 19:40 ET Nov 15: 21:10 ET Nov 15 to 21:10 ET Nov 16, batch 3's terms) keeps its own ledger, as batch 3 did (ruling 108)." It is accurate but could be clearer. However, this is a style nit, not a defect.
2.  **[P3] Nit**: The test `test_no_b

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 CONSENSUS — pp-selectid audit 20261115_1937 (BATCH 4's own build ledger)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and deepseek-v4.1-flash (2); they disagree on a P1, so Grok was asked (1).
glm's breaker is open. Cycle 1: $0.0185 vendor-reported. Each P1 checked against the code: none is a defect.

1. deepseek [P1] "SPEND moves to SPEND_B4.json unconditionally; landed before 21:10 ET, a batch-3 build would charge
   batch 4; hold it until 21:10 or gate it by time": HELD, its own first remedy. The change is not in the worktree
   until 21:10 ET; it lands then, in one commit whose time shows it. Every build is started by this builder (the
   ledger watcher only notifies), and none starts between 21:10 and the landing. A build started before 21:10 has
   already imported proof_ly with SPEND_B3.json and keeps charging batch 3 to its end. A time gate would leave code
   that is dead from 21:10 on; holding needs none.
2. deepseek [P1] "os may not be imported in test_ruling_102.py": REFUTED: tests/package/test_ruling_102.py:10
   `import os`; the test passes (18 in the file; all 40 suite files, 813 tests).
3. Grok [P1] "the diff implements none of the governing laws (D1-D6, the protected preview, ...)": OUT OF SCOPE: this
   audit is the one-file-name ledger switch the QUESTION names; the laws' gates live in code this diff does not
   touch, and nothing here claims to change them.

P2s / P3s noted, not changed: deepseek "grep for any other SPEND_B3.json writer": done before the audit (git grep:
only proof_ly.py and this test name it; proof_ledger.py:221 is the only reader of PL.SPEND). The redundant
assertNotIn (deepseek, qwen): kept: it states the closed ledgers by name. Grok: a helper for the file name, and the
dated comments: left as they are (one constant per batch, as ruling 108 did).

CHANGED AFTER CYCLE 1: nothing.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261115_1937/C2_STEP.diff (49 lines)
```
   1 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
   2 | index 080be63..138301d 100644
   3 | --- a/tests/package/proof_ly.py
   4 | +++ b/tests/package/proof_ly.py
   5 | @@ -17,8 +17,8 @@ is out too. What is left:
   6 |  - the second recogniser is ElevenLabs scribe_v1.
   7 |  CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
   8 |  
   9 | -SPEND: a ledger of this order's own (tests/package/proof/SPEND_B3.json since ruling 108; SPEND_LY.json is the closed
  10 | -$20 order's) holds the price-table estimate beside the
  11 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_B4.json for BATCH 4, the orchestrator's 19:40 ET Nov 15
  12 | +order; SPEND_B3.json is batch 3's and SPEND_LY.json the $20 order's, both closed) holds the price-table estimate beside the
  13 |  vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). RULING 48 (orchestrator 07:02 Nov 13):
  14 |  its guard is LY_LIMIT_USD on VENDOR-REPORTED dollars, the estimate counted only for a call whose vendor reports none
  15 |  (Router limit_basis="reported"); at LY_STOP_USD no new build starts (proof_ledger) and the orchestrator is told.
  16 | @@ -47,9 +47,10 @@ import speakers as SP  # noqa: E402
  17 |  
  18 |  REPLIES = os.path.join(HERE, "fixtures", "replies")
  19 |  OUT = os.path.join(HERE, "proof")
  20 | -SPEND = os.path.join(OUT, "SPEND_B3.json")   # RULING 108 (orchestrator 21:20 ET Nov 14): BATCH 3 (to 21:10 ET Nov 15)
  21 | -#   keeps its own ledger. The $20 order's SPEND_LY.json is CLOSED at $11.47 (restated on ruling 107 Q1's basis, e7f68e11).
  22 | -LY_LIMIT_USD = 4.50                # RULING 108: builds + sealing's share of batch 3's $8.00 ALL-IN cap (audits $2.50,
  23 | +SPEND = os.path.join(OUT, "SPEND_B4.json")   # BATCH 4 (orchestrator 19:40 ET Nov 15: 21:10 ET Nov 15 to 21:10 ET Nov
  24 | +#   16, batch 3's terms) keeps its own ledger, as batch 3 did (ruling 108). CLOSED: batch 3's SPEND_B3.json at 21:10 ET
  25 | +#   Nov 15; the $20 order's SPEND_LY.json at $11.47 (restated on ruling 107 Q1's basis, e7f68e11).
  26 | +LY_LIMIT_USD = 4.50                # RULING 108, batch 4 on its terms: builds + sealing's share of the $8.00 cap (audits $2.50,
  27 |  LY_LIMIT_BASIS = "reported"        # mining and checks $1.00), VENDOR-REPORTED; an abandoned call at the model's own
  28 |  LY_STOP_USD = 4.00                 # rate (ruling 107 Q1). No build starts at or over $4.00 (a build runs $0.15-0.50, so
  29 |                                     # none ends over $4.50: each paid call still RESERVES its upper bound while in
  30 | diff --git a/tests/package/test_ruling_102.py b/tests/package/test_ruling_102.py
  31 | index eccb74d..0889c09 100644
  32 | --- a/tests/package/test_ruling_102.py
  33 | +++ b/tests/package/test_ruling_102.py
  34 | @@ -306,11 +306,12 @@ class TestOnThePinAndOnState(unittest.TestCase):
  35 |  
  36 |      def test_no_build_starts_at_the_stop_and_one_starts_below(self):
  37 |          """The orchestrator 13:02 Nov 14: at the stop no build starts, and STATE line 1 says so in capitals. RULING 108
  38 | -        (21:20 Nov 14): batch 3's builds stop at $4.00 of their $4.50 share."""
  39 | +        (21:20 Nov 14): batch 3's builds stop at $4.00 of their $4.50 share; batch 4 (19:40 Nov 15) on the same terms."""
  40 |          self.assertEqual((PLG.PL.LY_STOP_USD, PLG.PL.LY_LIMIT_USD), (4.00, 4.50))
  41 |          self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")               # vendor-reported (audit 2114 C1, glm)
  42 |          self.assertGreaterEqual(PLG.PL.LY_LIMIT_USD - PLG.PL.LY_STOP_USD, 0.50)   # one build's headroom (C1, glm)
  43 | -        self.assertTrue(PLG.PL.SPEND.endswith("SPEND_B3.json"))          # never the closed $20 ledger again
  44 | +        self.assertEqual(os.path.basename(PLG.PL.SPEND), "SPEND_B4.json")   # batch 4's own; never a closed ledger
  45 | +        self.assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))
  46 |          self.assertIsNone(PLG.start_refused(3.99))
  47 |          why = PLG.start_refused(4.0)
  48 |          self.assertIn("at or over the $4.00 stop: no build starts", why)
  49 | 
```

---

pp-selectid: BATCH 4's own build ledger (orchestrator 19:40 ET Nov 15). Files: tests/package/proof_ly.py (SPEND and
its comments), tests/package/test_ruling_102.py.

THE ORDER, verbatim: "batch 3 closes at 21:10 ET ... BATCH 4 starts 21:10 ET Nov 15 and runs to 21:10 ET Nov 16 on
the same terms: all-in cap $8.00 (tell at $6, alarm at $7.50), every ruling to 117 in force, the calibrated bars, the
join search, the 30-minute fallback poll."

THE CHANGE: proof_ly.SPEND, the ledger the ledger build's router charges (tests/package/proof_ledger.py:221,
spend_path=PL.SPEND, the only code that reads it), moves from SPEND_B3.json to SPEND_B4.json, exactly as ruling 108
moved it from SPEND_LY.json to SPEND_B3.json for batch 3 (audit 20261114_2114). LY_LIMIT_USD 4.50, LY_STOP_USD 4.00,
LY_LIMIT_BASIS "reported" and RESERVE_WAIT_S are unchanged ("the same terms"). It LANDS AT 21:10 ET, when batch 3
closes, so no build that starts before then charges batch 4. A missing SPEND_B4.json starts at $0 (the Router's own
ledger creation, unchanged). The batch-4 STATE figure is kept outside this code, as batch 3's was.

UNCHANGED GUARDS (not in the diff): proof_ledger.start_refused (no build starts at or over LY_STOP_USD); the Router's
limit (limit_usd=PL.LY_LIMIT_USD, limit_basis=PL.LY_LIMIT_BASIS, tests/package/proof_ledger.py:221-227); ruling 41's
per-build cap; ruling 107 (1)'s fingerprint.

TESTS: test_ruling_102 test_no_build_starts_at_the_stop_and_one_starts_below: the ledger is SPEND_B4.json and never a
closed one (SPEND_LY.json, SPEND_B3.json); the stop, the limit and its basis unchanged. All suite files pass.

PLEASE CHECK: (1) that nothing but the ledger's file name moves; (2) that no other code path still writes
SPEND_B3.json; (3) the test.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
